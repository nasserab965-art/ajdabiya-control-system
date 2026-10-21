"""
الصفحة 1: التقرير اليومي + الكاميرات + قراءات الخطوط
"""
import sys
import os

# ⚠️ يجب أن يكون هذا السطر في البداية وقبل أي استيراد آخر
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import streamlit as st
import io
import shutil
import base64
import requests
from datetime import datetime, date
from PIL import Image, ImageDraw, ImageFont
import cv2
import av
import numpy as np
import pandas as pd
import plotly.graph_objects as go
from streamlit_webrtc import webrtc_streamer, VideoTransformerBase, RTCConfiguration

# الآن يمكنك استيراد الملف المشترك بأمان
from shared import check_login, apply_common_css, back_to_home_button, load_table

# إعداد الصفحة
st.set_page_config(
    page_title="التقرير اليومي",
    page_icon="📋",
    layout="wide"
)

apply_common_css()

# ═══════════════════════════════════════════════════════════
# إعدادات
# ═══════════════════════════════════════════════════════════
MAINJOB_PATH = 'mainjob.xlsx'

MAINJOB_SHEETS = [
    'my_job - 2025',
    'my_job2 - 2026',
    'my_job - 2027',
    'my_job - 2028',
    'my_job - 2029',
    'my_job - 2030',
]

MIN_DATE = '2025-01-01'

# رابط ملف الـ PDF في مستودعك (تأكد من اسم المستخدم الصحيح)
PDF_URL = "https://raw.githubusercontent.com/nasserab965-art/ajdabiya-control-system/main/Daily_rep.pdf"


# ═══════════════════════════════════════════════════════════
# 📊 دوال قراءات الخطوط - متعدد السنوات
# ═══════════════════════════════════════════════════════════
DATE_COL = ' اليوم'

VALUE_COLS = {
    '(S/S TOT) AJD': {'label': 'S/S TOT AJD', 'color': '#F9CA24'},
    '(T/B TOT) AJD': {'label': 'T/B TOT AJD', 'color': '#AFFF00'},
    '(A/B TOT) AJD': {'label': 'A/B TOT AJD', 'color': '#4A90D9'},
    '(A/S TOT) AJD': {'label': 'A/S TOT AJD', 'color': '#FF6B6B'},
}


@st.cache_data(ttl=300, show_spinner=False)
def load_tank_data(path, sheet_names):
    if isinstance(sheet_names, str):
        sheet_names = [sheet_names]

    frames = []
    info_lines = []
    loaded_sheets = []

    for sheet in sheet_names:
        try:
            df = pd.read_excel(path, sheet_name=sheet)

            missing = [c for c in [DATE_COL] + list(VALUE_COLS.keys())
                       if c not in df.columns]
            if missing:
                info_lines.append(f"⚠️ شيت '{sheet}': أعمدة مفقودة → تم التخطي")
                continue

            df[DATE_COL] = pd.to_datetime(df[DATE_COL], errors='coerce')
            df = df.dropna(subset=[DATE_COL])

            for col in VALUE_COLS.keys():
                df[col] = pd.to_numeric(df[col], errors='coerce')

            df = df.dropna(how='all', subset=list(VALUE_COLS.keys()))

            if df.empty:
                info_lines.append(f"ℹ️ شيت '{sheet}': فارغ → تم التخطي")
                continue

            df['_sheet'] = sheet
            frames.append(df)
            loaded_sheets.append(f"{sheet} ({len(df)})")

        except ValueError:
            info_lines.append(f"⚠️ شيت '{sheet}': غير موجود في الملف")
        except Exception as e:
            info_lines.append(f"❌ شيت '{sheet}': {e}")

    if not frames:
        return None, "❌ لم يتم تحميل أي شيت.\n" + "\n".join(info_lines)

    combined = pd.concat(frames, ignore_index=True)
    combined = combined[combined[DATE_COL] >= pd.to_datetime(MIN_DATE)]

    if combined.empty:
        return None, f"ℹ️ لا توجد بيانات بعد تاريخ {MIN_DATE}."

    combined = (combined
                .sort_values([DATE_COL, '_sheet'])
                .drop_duplicates(subset=[DATE_COL], keep='last')
                .drop(columns=['_sheet'])
                .sort_values(DATE_COL)
                .reset_index(drop=True))

    header = f"✅ تم تحميل {len(combined)} صف من: " + " | ".join(loaded_sheets)
    msg = header + ("\n" + "\n".join(info_lines) if info_lines else "")

    return combined, msg


def plot_tank_data(df, chart_type='lines+markers', year_label=''):
    fig = go.Figure()
    
    for col, meta in VALUE_COLS.items():
        if col in df.columns:
            if chart_type == 'bar':
                fig.add_trace(go.Bar(
                    x=df[DATE_COL],
                    y=df[col],
                    name=meta['label'],
                    marker=dict(color=meta['color']),
                    hovertemplate=f"<b>{meta['label']}</b><br>" +
                                  "التاريخ: %{x|%Y-%m-%d}<br>" +
                                  "القيمة: %{y:,.2f}<extra></extra>",
                ))
            else:
                fig.add_trace(go.Scatter(
                    x=df[DATE_COL],
                    y=df[col],
                    mode=chart_type,
                    name=meta['label'],
                    line=dict(color=meta['color'], width=2.5),
                    marker=dict(size=6, color=meta['color']),
                    hovertemplate=f"<b>{meta['label']}</b><br>" +
                                  "التاريخ: %{x|%Y-%m-%d}<br>" +
                                  "القيمة: %{y:,.2f}<extra></extra>",
                ))
    
    barmode = 'group' if chart_type == 'bar' else None
    title_text = f'📊قراءات الخطوط الأربعة لخزان التجميع والموازنة - اجدابيا - {year_label}' if year_label else '📊 قراءات الخطوط'
    
    fig.update_layout(
        title=dict(
            text=title_text,
            font=dict(size=24, color='#F9CA24', family='Arial'),
            x=0.5, xanchor='center',
        ),
        paper_bgcolor='#0B1E3F',
        plot_bgcolor='#163A6B',
        font=dict(color='#E8F4FD', size=14, family='Arial'),
        xaxis=dict(
            title='📅 التاريخ',
            gridcolor='rgba(74, 144, 217, 0.25)',
            showline=True, linecolor='#4A90D9', linewidth=2,
            tickformat='%Y-%m-%d',
        ),
        yaxis=dict(
            title='📈 القراءة',
            gridcolor='rgba(74, 144, 217, 0.25)',
            showline=True, linecolor='#4A90D9', linewidth=2,
            tickformat=',.0f',
        ),
        hovermode='x unified',
        barmode=barmode,
        legend=dict(
            orientation='h',
            yanchor='bottom', y=1.02,
            xanchor='center', x=0.5,
            bgcolor='rgba(11, 30, 63, 0.9)',
            bordercolor='#4A90D9', borderwidth=2,
            font=dict(size=14, color='#FFFFFF'),
        ),
        margin=dict(l=70, r=30, t=100, b=70),
        height=550,
        dragmode='pan',
    )
    
    return fig


def render_tank_stats(df):
    stat_cols = st.columns(4)
    for idx, (col, meta) in enumerate(VALUE_COLS.items()):
        if col not in df.columns:
            continue
        series = df[col].dropna()
        if series.empty:
            continue
        
        last_val = series.iloc[-1]
        prev_val = series.iloc[-2] if len(series) > 1 else last_val
        delta = last_val - prev_val
        
        if delta > 0:
            delta_color = '#AFFF00'
            delta_icon = '▲'
        elif delta < 0:
            delta_color = '#FF6B6B'
            delta_icon = '▼'
        else:
            delta_color = '#E8F4FD'
            delta_icon = '●'
        
        with stat_cols[idx]:
            st.markdown(f"""
            <div style="
                background: linear-gradient(135deg, #0B1E3F 0%, #163A6B 100%);
                border-radius: 12px;
                padding: 20px 15px;
                border-right: 5px solid {meta['color']};
                direction: rtl;
                text-align: center;
                min-height: 240px;
                box-shadow: 0 0 15px rgba(74, 144, 217, 0.2);
            ">
                <div style="
                    color: {meta['color']}; 
                    font-size: 18px; 
                    font-weight: bold; 
                    margin-bottom: 12px;
                    padding-bottom: 8px;
                    border-bottom: 1px solid rgba(74, 144, 217, 0.3);
                ">
                    🛢️ خط {meta['label']}
                </div>
                <div style="color: #FFFFFF; font-size: 28px; font-weight: bold; margin: 10px 0;">
                    {last_val:,.2f}
                </div>
                <div style="color: #AFFF00; font-size: 14px; margin-bottom: 8px;">
                    ⏱️ آخر قراءة
                </div>
                <div style="
                    color: {delta_color}; 
                    font-size: 16px; 
                    font-weight: bold;
                    margin-bottom: 15px;
                    background: rgba(0,0,0,0.2);
                    border-radius: 6px;
                    padding: 6px 10px;
                    display: inline-block;
                ">
                    {delta_icon} {abs(delta):,.2f} عن الأمس
                </div>
                <div style="
                    color: #E8F4FD; 
                    font-size: 16px;
                    line-height: 2;
                    text-align: right;
                    padding: 0 10px;
                ">
                    📊 <b>المتوسط:</b> {series.mean():,.2f}<br>
                    📈 <b>الأعلى:</b> {series.max():,.2f}<br>
                    📉 <b>الأدنى:</b> {series.min():,.2f}
                </div>
            </div>
            """, unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════
# 🏠 زر العودة للرئيسية (أعلى الصفحة)
# ═══════════════════════════════════════════════════════════
col1, col2, col3 = st.columns([1, 2, 1])
with col3:
    if st.button("🏠 العودة للرئيسية", width="stretch", type="primary", key="back_top"):
        st.switch_page("app_main.py")

st.markdown("---")

# ═══════════════════════════════════════════════════════════
# التقرير اليومي
# ═══════════════════════════════════════════════════════════
st.title("📋 التقرير اليومي + 📹 المباشر")

tab1, tab2 = st.tabs(["📋 التقرير اليومي", "📹 المباشر"])

with tab1:
    st.markdown("""
    <div style="
        background: linear-gradient(135deg, #0B1E3F 0%, #163A6B 50%, #1E5A96 100%);
        border-radius: 22px;
        padding: 45px 50px;
        margin: 20px 0 30px 0;
        border: 2px solid #4A90D9;
        box-shadow: 
            0 0 25px rgba(74, 144, 217, 0.35),
            0 0 70px rgba(74, 144, 217, 0.15),
            inset 0 0 50px rgba(74, 144, 217, 0.08);
        direction: rtl;
        text-align: center;
    ">
        <h1 style="
            color: #FFFFFF; 
            font-size: 48px; 
            margin: 0 0 25px 0;
            text-shadow: 2px 2px 10px rgba(0,0,0,0.5);
            font-weight: bold;
            font-family: Arial, sans-serif;
        ">🌟 مشروع النهر الصناعى - المرحلة الأولى 🌟</h1>
         <h2 style="
            color: #F9CA24; 
            font-size: 48px; 
            margin: 0 0 25px 0;
            text-shadow: 2px 2px 10px rgba(0,0,0,0.5);
            font-weight: bold;
            font-family: Arial, sans-serif;
        ">الإدارة العامة للإتصالات والتحكم وتقنية المعلومات </h2> 
        <h3 style="
            color: #F9CA24; 
            font-size: 48px; 
            margin: 0 0 25px 0;
            text-shadow: 2px 2px 10px rgba(0,0,0,0.5);
            font-weight: bold;
            font-family: Arial, sans-serif;
        "> إدارة الإتصالات والتحكم  </h3> 
        <h4 style="
            color: #FFFFFF; 
            font-size: 38px; 
            margin: 0 0 35px 0;
            text-shadow: 1px 1px 5px rgba(0,0,0,0.5);
            font-weight: bold;
            font-family: Arial, sans-serif;
        ">📍 غرفة تحكم اجدابيا</h4>
        <p style="
            font-size: 28px;
            color: #E8F4FD;
            line-height: 2.3;
            margin: 0 auto;
            font-weight: 400;
            font-family: Arial, sans-serif;
            max-width: 1100px;
        ">
            <strong style="color: #AFFF00; font-size: 32px;">بمشيئة الله وفضله</strong> 
            في هذا المشروع الضخم 
            <strong style="color: #F9CA24; font-size: 30px;">( مشروع النهر الصناعى - المرحلة الأولى )</strong>، 
            " فأنا <strong style="color: #F9CA24; font-size: 30px;">( موقع خزان التجميع والموازنة - اجدابيا )</strong> 
            <strong style="color: #AFFF00; font-size: 28px;">
            النقطة التي تتلاقى فيها كل الإمدادات، والعين التي ترى أول خيط من خلل في شبكة التوزيع. 
            مكاني ليس مجرد موقع عمل، بل هو غرفة التحكم التي تبدأ منها رحلة استقرار المياه، 
            وتنتهي إليها أي إشارة خطر.
            </strong>"
        </p>
        <p style="
            font-size: 26px;
            color: #FFFFFF;
            margin: 35px 0 0 0;
            font-style: italic;
            text-shadow: 1px 1px 4px rgba(0,0,0,0.4);
            font-family: Arial, sans-serif;
        ">
           <strong> ❤️ مثلما يعكس نبض القلب صحة الجسد، تعكس قراءاتي صحة شبكة توزيع المياه بأكملها ❤️ </strong> 
        </p>
        <p style="
            text-align: left;
            color: #F9CA24;
            font-size: 24px;
            margin: 30px 0 0 0;
            font-weight: bold;
            font-family: Arial, sans-serif;
        ">✍️ م. ناصر</p>
    </div>
    """, unsafe_allow_html=True)

    #st.markdown("### 📋 التقرير اليومي - Daily_rep")
    
    st.markdown("### 📋 التقرير اليومي - Daily_rep")
    
    # محاولة جلب الملف من GitHub
    try:
        # إضافة وقت للرابط لتجاوز الكاش وجلب أحدث نسخة دائماً
        response = requests.get(f"{PDF_URL}?t={datetime.now().timestamp()}")
        
        if response.status_code == 200:
            # حفظ الملف مؤقتاً لعرضه باستخدام مكون Streamlit
            temp_pdf_path = "temp_daily_rep.pdf"
            with open(temp_pdf_path, "wb") as f:
                f.write(response.content)
            
            # استخدام مكون Streamlit لعرض الـ PDF (أكثر أماناً ولا يحظره المتصفح)
            st.pdf(temp_pdf_path, height=850)
            
            # إضافة زر للتحميل كخيار إضافي للمستخدم
            st.download_button(
                label="📥 تحميل التقرير كملف PDF",
                data=response.content,
                file_name=f'Daily_rep_{datetime.now().strftime("%Y-%m-%d")}.pdf',
                mime='application/pdf',
                type="primary"
            )
            
            # عرض وقت آخر تحديث
            st.caption("🔄 تم جلب أحدث نسخة من السحابة (GitHub).")
            
            # تنظيف الملف المؤقت
            import os
            if os.path.exists(temp_pdf_path):
                os.remove(temp_pdf_path)

        elif response.status_code == 404:
            st.warning("⏳ لم يتم العثور على التقرير في المستودع بعد. يرجى التأكد من رفع الملف.")
        else:
            st.error(f"❌ حدث خطأ أثناء الاتصال بالخادم. كود الخطأ: {response.status_code}")

    except Exception as e:
        st.error(f"❌ حدث خطأ أثناء محاولة عرض التقرير: {e}")
    st.markdown("## 📊 قراءات الخطوط - 2026 فما بعد")

    df_tank, load_info = load_tank_data(MAINJOB_PATH, MAINJOB_SHEETS)

    if df_tank is None or df_tank.empty:
        st.warning(load_info)
    else:
        st.caption(load_info)

        ctrl_col1, ctrl_col2, ctrl_col3 = st.columns([2, 2, 1])
        
        with ctrl_col1:
            chart_type_map = {
                '📈 خطي + نقاط': 'lines+markers',
                '📉 خط فقط': 'lines',
                '📊 أعمدة': 'bar',
            }
            selected_label = st.radio(
                "🎨 نوع الرسم:",
                options=list(chart_type_map.keys()),
                index=0,
                horizontal=True,
                key="chart_type_selector",
            )
            chart_type = chart_type_map[selected_label]
        
        with ctrl_col2:
            min_date = df_tank[DATE_COL].min().date()
            max_date = df_tank[DATE_COL].max().date()
            
            date_range = st.date_input(
                "📅 الفترة:",
                value=(min_date, max_date),
                min_value=min_date,
                max_value=max_date,
                key="date_range_filter",
            )
        
        with ctrl_col3:
            st.write("")
            st.write("")
            show_stats = st.checkbox("📊 إحصائيات", value=True, key="show_stats_cb")
        
        if isinstance(date_range, tuple) and len(date_range) == 2:
            start_date, end_date = date_range
            mask = (df_tank[DATE_COL].dt.date >= start_date) & \
                   (df_tank[DATE_COL].dt.date <= end_date)
            df_filtered = df_tank[mask].copy()
        else:
            df_filtered = df_tank.copy()
        
        if df_filtered.empty:
            st.warning("⚠️ لا توجد بيانات في الفترة المحددة")
        else:
            years = sorted(df_filtered[DATE_COL].dt.year.unique())
            year_label = " / ".join(str(y) for y in years)

            st.plotly_chart(
                plot_tank_data(df_filtered, chart_type, year_label),
                width='stretch',
                config={
                    'displayModeBar': True,
                    'scrollZoom': True,
                    'toImageButtonOptions': {
                        'format': 'png',
                        'filename': f'tank_readings_{year_label.replace(" / ", "_")}_{datetime.now().strftime("%Y%m%d")}',
                        'height': 800,
                        'width': 1600,
                        'scale': 2,
                    },
                }
            )
            
            if show_stats:
                st.markdown("### 📈 إحصائيات سريعة لكل خط")
                render_tank_stats(df_filtered)
                 
with tab2:
    st.markdown("### 📹 كاميرات المراقبة")
    
    class VideoTransformer(VideoTransformerBase):
        def __init__(self, camera_url):
            self.camera_url = camera_url
            self.cap = None
        
        def recv(self, frame):
            img = frame.to_ndarray(format="bgr24")
            if self.cap is None or not self.cap.isOpened():
                self.cap = cv2.VideoCapture(self.camera_url)
                if not self.cap.isOpened():
                    img = np.zeros((480, 640, 3), dtype=np.uint8)
                    cv2.putText(img, "❌ لا يمكن الاتصال", (50, 240),
                                cv2.FONT_HERSHEY_SIMPLEX, 1, (0,0,255), 2)
                    return av.VideoFrame.from_ndarray(img, format="bgr24")
            ret, frame = self.cap.read()
            if not ret:
                self.cap.release()
                self.cap = cv2.VideoCapture(self.camera_url)
                return frame
            return av.VideoFrame.from_ndarray(frame, format="bgr24")
        
        def __del__(self):
            if self.cap is not None:
                self.cap.release()
    
    CAMERAS = {
        "كاميرا 1 - المدخل": "rtsp://admin:password@192.168.1.100:554/stream1"
    }
    
    if st.button("🔄 تحديث البث", width='stretch'):
        st.rerun()
    
    cols = st.columns(2)
    for idx, (name, url) in enumerate(CAMERAS.items()):
        with cols[idx % 2]:
            st.subheader(f"📷 {name}")
            try:
                webrtc_streamer(
                    key=f"cam_{idx}",
                    video_processor_factory=lambda: VideoTransformer(url),
                    rtc_configuration=RTCConfiguration(
                        {"iceServers": [{"urls": ["stun:stun.l.google.com:19302"]}]}
                    ),
                    media_stream_constraints={"video": True, "audio": False},
                )
            except Exception as e:
                st.error(f"❌ {e}")
            
# ═══════════════════════════════════════════════════════════
# 🏠 زر العودة للرئيسية (أسفل الصفحة)
# ═══════════════════════════════════════════════════════════
st.markdown("---")
col1, col2, col3 = st.columns([1, 2, 1])
with col3:
    if st.button("🏠 العودة للرئيسية", width="stretch", type="primary", key="back_bottom"):
        st.switch_page("app_main.py")
