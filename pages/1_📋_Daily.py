"""
الصفحة 1: التقرير اليومي + الكاميرات + قراءات الخطوط
"""
import sys
import os
import glob

# ⚠️ يجب أن يكون هذا السطر في البداية وقبل أي استيراد آخر
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import streamlit as st
import io
import shutil
from datetime import datetime, date
from PIL import Image, ImageDraw, ImageFont
import cv2
import av
import numpy as np
import pandas as pd
import plotly.graph_objects as go
from streamlit_webrtc import webrtc_streamer, VideoTransformerBase, RTCConfiguration
import fitz  # PyMuPDF
import requests
from dateutil import parser

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
# 🛑 إخفاء شريط الأدوات العلوي
# ═══════════════════════════════════════════════════════════
st.markdown("""
<style>
    header[data-testid="stHeader"] { display: none !important; }
    [data-testid="stToolbar"] { display: none !important; }
    [data-testid="stDecoration"] { display: none !important; }
    #MainMenu { visibility: hidden !important; }
    footer { visibility: hidden !important; }
</style>
""", unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════
# إعدادات
# ═══════════════════════════════════════════════════════════
PDF_FILE_PATH = "Daily_rep.pdf"
SHEET_NAME = None
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

# ═══════════════════════════════════════════════════════════
# دوال التحويل
# ═══════════════════════════════════════════════════════════
def optimize_image(image_path, max_width=2500):
    try:
        img = Image.open(image_path)
        if img.width > max_width:
            ratio = max_width / img.width
            new_size = (max_width, int(img.height * ratio))
            img = img.resize(new_size, Image.LANCZOS)
        img.save(image_path, optimize=True, quality=92)
    except Exception:
        pass

def add_timestamp_to_image(image_path):
    try:
        img = Image.open(image_path).convert("RGB")
        draw = ImageDraw.Draw(img)
        ts = datetime.now().strftime("%Y-%m-%d  %H:%M")
        x, y = 12, 12
        try:
            bbox = draw.textbbox((x, y), ts)
            draw.rectangle([bbox[0]-4, bbox[1]-4, bbox[2]+4, bbox[3]+4], fill=(255,255,255))
        except Exception:
            pass
        draw.text((x, y), ts, fill=(200, 0, 0))
        img.save(image_path, optimize=True, quality=92)
    except Exception:
        pass

def add_watermark_to_image(image_path, text="غرفة تحكم اجدابيا"):
    try:
        img = Image.open(image_path).convert("RGBA")
        overlay = Image.new("RGBA", img.size, (0,0,0,0))
        draw = ImageDraw.Draw(overlay)
        font_size = max(14, img.width // 60)
        font = None
        for fn in ["arial.ttf", "tahoma.ttf", "segoeui.ttf"]:
            try:
                font = ImageFont.truetype(fn, font_size)
                break
            except Exception:
                continue
        if font is None:
            font = ImageFont.load_default()
        try:
            bbox = draw.textbbox((0,0), text, font=font)
            tw, th = bbox[2]-bbox[0], bbox[3]-bbox[1]
        except Exception:
            tw, th = font_size*len(text)//2, font_size
        margin = 15
        x = img.width - tw - margin
        y = img.height - th - margin
        pad = 6
        draw.rectangle([x-pad, y-pad, x+tw+pad, y+th+pad], fill=(255,255,255,180))
        draw.text((x, y), text, fill=(180,0,0,220), font=font)
        combined = Image.alpha_composite(img, overlay)
        combined.convert("RGB").save(image_path, optimize=True, quality=92)
    except Exception:
        pass

def convert_pdf_to_image(pdf_path, scale=3):
    """تحويل الـ PDF إلى صورة جديدة باسم فريد وإرجاع اسم الملف"""
    # إنشاء اسم فريد للصورة يعتمد على الوقت الحالي لتجنب الكاش
    timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
    new_image_path = f'Daily_rep_{timestamp_str}.png'
    
    try:
        doc = fitz.open(pdf_path)
        page = doc[0]
        mat = fitz.Matrix(scale, scale)
        pix = page.get_pixmap(matrix=mat, alpha=False)
        pix.save(new_image_path)
        doc.close()
        
        optimize_image(new_image_path, max_width=2500)
        add_timestamp_to_image(new_image_path)
        add_watermark_to_image(new_image_path, text="غرفة تحكم اجدابيا")
        
        # حذف الصور القديمة لتوفير المساحة
        for old_img in glob.glob('Daily_rep_*.png'):
            if old_img != new_image_path:
                try:
                    os.remove(old_img)
                except:
                    pass
                    
        return True, "✅ تم تحويل التقرير اليومي إلى صورة بنجاح!", new_image_path
    except Exception as e:
        return False, f"❌ خطأ أثناء تحويل الـ PDF: {e}", None


# ═══════════════════════════════════════════════════════════
# 🔄 دالة التجديد التلقائي
# ═══════════════════════════════════════════════════════════
@st.cache_data(ttl=60, show_spinner=False)
def get_latest_pdf_commit_date():
    """جلب تاريخ آخر تحديث لملف الـ PDF من GitHub"""
    try:
        url = "https://api.github.com/repos/nasserab965-art/ajdabiya-control-system/commits?path=Daily_rep.pdf&page=1&per_page=1"
        response = requests.get(url)
        if response.status_code == 200 and len(response.json()) > 0:
            last_commit_date_str = response.json()[0]['commit']['committer']['date']
            return parser.parse(last_commit_date_str).replace(tzinfo=None)
    except Exception:
        pass
    return None

# ═══════════════════════════════════════════════════════════
# 📊 دوال قراءات الخطوط
# ═══════════════════════════════════════════════════════════
DATE_COL = ' اليوم'

VALUE_COLS = {
    '(S/S TOT) AJD': {'label': 'S/S TOT AJD', 'color': '#F9CA24'},
    '(T/B TOT) AJD': {'label': 'T/B TOT AJD', 'color': '#AFFF00'},
    '(A/B TOT) AJD': {'label': 'A/B TOT AJD', 'color': '#4A90D9'},
    '(A/S TOT) AJD': {'label': 'A/S TOT AJD', 'color': '#FF6B6B'},
    '(RES. LEVEL) AJD': {'label': 'RES. LEVEL AJD', 'color': '#FFFFFF'},
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
            missing = [c for c in [DATE_COL] + list(VALUE_COLS.keys()) if c not in df.columns]
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
                    x=df[DATE_COL], y=df[col], name=meta['label'],
                    marker=dict(color=meta['color']),
                    hovertemplate=f"<b>{meta['label']}</b><br>التاريخ: %{{x|%Y-%m-%d}}<br>القيمة: %{{y:,.2f}}<extra></extra>",
                ))
            else:
                fig.add_trace(go.Scatter(
                    x=df[DATE_COL], y=df[col], mode=chart_type, name=meta['label'],
                    line=dict(color=meta['color'], width=2.5),
                    marker=dict(size=6, color=meta['color']),
                    hovertemplate=f"<b>{meta['label']}</b><br>التاريخ: %{{x|%Y-%m-%d}}<br>القيمة: %{{y:,.2f}}<extra></extra>",
                ))
    
    barmode = 'group' if chart_type == 'bar' else None
    title_text = f'📊 قراءات الخطوط - {year_label}' if year_label else '📊 قراءات الخطوط'
    
    fig.update_layout(
        title=dict(text=title_text, font=dict(size=24, color='#F9CA24', family='Arial'), x=0.5, xanchor='center'),
        paper_bgcolor='#0B1E3F', plot_bgcolor='#163A6B',
        font=dict(color='#E8F4FD', size=14, family='Arial'),
        xaxis=dict(title='📅 التاريخ', gridcolor='rgba(74, 144, 217, 0.25)', showline=True, linecolor='#4A90D9', linewidth=2, tickformat='%Y-%m-%d'),
        yaxis=dict(title='📈 القراءة', gridcolor='rgba(74, 144, 217, 0.25)', showline=True, linecolor='#4A90D9', linewidth=2, tickformat=',.0f'),
        hovermode='x unified', barmode=barmode,
        legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='center', x=0.5, bgcolor='rgba(11, 30, 63, 0.9)', bordercolor='#4A90D9', borderwidth=2, font=dict(size=14, color='#FFFFFF')),
        margin=dict(l=70, r=30, t=100, b=70), height=550, dragmode='pan',
    )
    return fig

def render_tank_stats(df):
    valid_items = []
    for col, meta in VALUE_COLS.items():
        if col not in df.columns: continue
        series = df[col].dropna()
        if series.empty: continue
        valid_items.append((col, meta, series))

    if not valid_items:
        st.info("ℹ️ لا توجد بيانات كافية لعرض الإحصائيات في الفترة المحددة.")
        return

    stat_cols = st.columns(len(valid_items))
    for idx, (col, meta, series) in enumerate(valid_items):
        last_val = series.iloc[-1]
        prev_val = series.iloc[-2] if len(series) > 1 else last_val
        delta = last_val - prev_val
        
        if delta > 0: delta_color = '#AFFF00'; delta_icon = '▲'
        elif delta < 0: delta_color = '#FF6B6B'; delta_icon = '▼'
        else: delta_color = '#E8F4FD'; delta_icon = '●'
        
        with stat_cols[idx]:
            st.markdown(f"""
            <div style="background: linear-gradient(135deg, #0B1E3F 0%, #163A6B 100%); border-radius: 12px; padding: 20px 15px; border-right: 5px solid {meta['color']}; direction: rtl; text-align: center; min-height: 240px; box-shadow: 0 0 15px rgba(74, 144, 217, 0.2);">
                <div style="color: {meta['color']}; font-size: 18px; font-weight: bold; margin-bottom: 12px; padding-bottom: 8px; border-bottom: 1px solid rgba(74, 144, 217, 0.3);">🛢️ خط {meta['label']}</div>
                <div style="color: #FFFFFF; font-size: 28px; font-weight: bold; margin: 10px 0;">{last_val:,.2f}</div>
                <div style="color: #AFFF00; font-size: 14px; margin-bottom: 8px;">⏱️ آخر قراءة</div>
                <div style="color: {delta_color}; font-size: 16px; font-weight: bold; margin-bottom: 15px; background: rgba(0,0,0,0.2); border-radius: 6px; padding: 6px 10px; display: inline-block;">{delta_icon} {abs(delta):,.2f} عن الأمس</div>
                <div style="color: #E8F4FD; font-size: 16px; line-height: 2; text-align: right; padding: 0 10px;">📊 <b>المتوسط:</b> {series.mean():,.2f}<br>📈 <b>الأعلى:</b> {series.max():,.2f}<br>📉 <b>الأدنى:</b> {series.min():,.2f}</div>
            </div>
            """, unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════
# 🏠 زر العودة للرئيسية
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
    <div style="background: linear-gradient(135deg, #0B1E3F 0%, #163A6B 50%, #1E5A96 100%); border-radius: 22px; padding: 45px 50px; margin: 20px 0 30px 0; border: 2px solid #4A90D9; box-shadow: 0 0 25px rgba(74, 144, 217, 0.35), 0 0 70px rgba(74, 144, 217, 0.15), inset 0 0 50px rgba(74, 144, 217, 0.08); direction: rtl; text-align: center;">
        <h1 style="color: #F9CA24; font-size: 48px; margin: 0 0 25px 0; text-shadow: 2px 2px 10px rgba(0,0,0,0.5); font-weight: bold; font-family: Arial, sans-serif;">🌟 مشروع النهر الصناعى - المرحلة الأولى 🌟</h1>
        <h2 style="color: #F9CA24; font-size: 48px; margin: 0 0 25px 0; text-shadow: 2px 2px 10px rgba(0,0,0,0.5); font-weight: bold; font-family: Arial, sans-serif;">🌟 الإدارة العامة للإتصالات والتحكم وتقنية المعلومات 🌟</h2>
        <h3 style="color: #F9CA24; font-size: 48px; margin: 0 0 25px 0; text-shadow: 2px 2px 10px rgba(0,0,0,0.5); font-weight: bold; font-family: Arial, sans-serif;">إدارة الإتصالات والتحكم</h3>
        <h4 style="color: #FFFFFF; font-size: 38px; margin: 0 0 35px 0; text-shadow: 1px 1px 5px rgba(0,0,0,0.5); font-weight: bold; font-family: Arial, sans-serif;">📍 غرفة تحكم اجدابيا</h4>
        <p style="font-size: 28px; color: #E8F4FD; line-height: 2.3; margin: 0 auto; font-weight: 400; font-family: Arial, sans-serif; max-width: 1100px;">
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
        <p style="font-size: 26px; color: #FFFFFF; margin: 35px 0 0 0; font-style: italic; text-shadow: 1px 1px 4px rgba(0,0,0,0.4); font-family: Arial, sans-serif;"><strong> ❤️ مثلما يعكس نبض القلب صحة الجسد، تعكس قراءاتي صحة شبكة توزيع المياه بأكملها ❤️ </strong></p>
        <p style="text-align: left; color: #F9CA24; font-size: 24px; margin: 30px 0 0 0; font-weight: bold; font-family: Arial, sans-serif;">✍️ م. ناصر</p>
    </div>
    """, unsafe_allow_html=True)

    st.markdown(f"""
    <div style="background: rgba(74, 144, 217, 0.1); border-right: 4px solid #4A90D9; border-radius: 8px; padding: 12px 20px; margin-bottom: 15px; direction: rtl; font-family: Arial, sans-serif;">
        <span style="color: #4A90D9; font-size: 16px; font-weight: bold;">📡 المصدر:</span>
        <code style="color: #AFFF00; font-size: 15px; background: rgba(0,0,0,0.3); padding: 2px 8px; border-radius: 4px; margin-right: 10px;">{PDF_FILE_PATH}</code>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("### 📋 التقرير اليومي - Daily_rep")
    
    # ═══════════════════════════════════════════════════════════
    # 🌟 التجديد التلقائي (الحل النهائي) 🌟
    # ═══════════════════════════════════════════════════════════
    # جلب تاريخ آخر تحديث من GitHub
    last_commit_date = get_latest_pdf_commit_date()
    
    # البحث عن أحدث صورة محلية متاحة
    existing_images = sorted(glob.glob('Daily_rep_*.png'), reverse=True)
    current_image_path = existing_images[0] if existing_images else None
    
    trigger_conversion = False
    
    if not current_image_path:
        trigger_conversion = True # لا توجد صورة أساساً
    elif last_commit_date:
        # استخراج التاريخ من اسم الصورة (لأننا نسميها Daily_rep_20231025_153000.png)
        try:
            img_time_str = current_image_path.replace('Daily_rep_', '').replace('.png', '')
            img_time = datetime.strptime(img_time_str, "%Y%m%d_%H%M%S")
            
            # إذا كان تاريخ الـ PDF في GitHub أحدث من الصورة، نحوله
            if last_commit_date > img_time:
                trigger_conversion = True
        except:
            trigger_conversion = True

    # تنفيذ التحويل إذا لزم الأمر
    if trigger_conversion and os.path.exists(PDF_FILE_PATH):
        with st.spinner('🔄 تم اكتشاف تحديث جديد، جاري تجهيز التقرير...'):
            success, msg, new_img = convert_pdf_to_image(PDF_FILE_PATH)
            if success:
                current_image_path = new_img
                st.toast(msg, icon="✅")
            else:
                st.error(msg)
                
    # أزرار التحكم
    col1, col2 = st.columns([1, 1])
    with col1:
        if st.button("🔄 إعادة توليد التقرير", width="stretch", type="primary"):
            with st.spinner('⏳ جاري تحويل الـ PDF إلى صورة...'):
                if os.path.exists(PDF_FILE_PATH):
                    success, msg, new_img = convert_pdf_to_image(PDF_FILE_PATH)
                    if success:
                        current_image_path = new_img
                        st.success(msg)
                        st.rerun()
                    else:
                        st.error(msg)
                else:
                    st.error(f"❌ لم يتم العثور على الملف {PDF_FILE_PATH}")
    
    with col2:
        if current_image_path and os.path.exists(current_image_path):
            # استخراج التاريخ من اسم الملف
            try:
                img_time_str = current_image_path.replace('Daily_rep_', '').replace('.png', '')
                img_time = datetime.strptime(img_time_str, "%Y%m%d_%H%M%S")
                st.info(f"📅 آخر تحديث للصورة: {img_time.strftime('%Y-%m-%d %H:%M')}")
            except:
                st.info("📅 الصورة جاهزة")
    
    st.markdown("---")
    
    # عرض الصورة
    if current_image_path and os.path.exists(current_image_path):
        img_width = st.slider("🔍 حجم العرض:", 600, 2500, 1400, 100, key="img_w")
        # استخدام مسار الصورة الفريد لمنع المتصفح من الكاش
        st.image(current_image_path, width=img_width)
        
        with open(current_image_path, "rb") as f:
            st.download_button(
                "🖼️ تحميل الصورة PNG", data=f.read(),
                file_name=current_image_path,
                mime='image/png', width="stretch"
            )
    else:
        st.warning("⏳ الصورة غير موجودة. اضغط زر إعادة التوليد لإنشائها من ملف الـ PDF.")

    st.markdown("---")
    st.markdown("## 📊 قراءات الخطوط - 2026 فما بعد")

    df_tank, load_info = load_tank_data(MAINJOB_PATH, MAINJOB_SHEETS)

    if df_tank is None or df_tank.empty:
        st.warning(load_info)
    else:
        st.caption(load_info)

        ctrl_col1, ctrl_col2, ctrl_col3 = st.columns([2, 2, 1])
        
        with ctrl_col1:
            chart_type_map = {'📈 خطي + نقاط': 'lines+markers', '📉 خط فقط': 'lines', '📊 أعمدة': 'bar'}
            selected_label = st.radio("🎨 نوع الرسم:", options=list(chart_type_map.keys()), index=0, horizontal=True, key="chart_type_selector")
            chart_type = chart_type_map[selected_label]
        
        with ctrl_col2:
            min_date = df_tank[DATE_COL].min().date()
            max_date = df_tank[DATE_COL].max().date()
            default_start = max(min_date, (max_date - pd.Timedelta(days=30)))
            if isinstance(default_start, pd.Timestamp): default_start = default_start.date()
            date_range = st.date_input("📅 الفترة:", value=(default_start, max_date), min_value=min_date, max_value=max_date, key="date_range_filter")
        
        with ctrl_col3:
            st.write("")
            st.write("")
            show_stats = st.checkbox("📊 إحصائيات", value=True, key="show_stats_cb")
        
        if isinstance(date_range, tuple) and len(date_range) == 2:
            start_date, end_date = date_range
            mask = (df_tank[DATE_COL].dt.date >= start_date) & (df_tank[DATE_COL].dt.date <= end_date)
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
                config={'displayModeBar': True, 'scrollZoom': True, 'toImageButtonOptions': {'format': 'png', 'filename': f'tank_readings_{year_label.replace(" / ", "_")}_{datetime.now().strftime("%Y%m%d")}', 'height': 800, 'width': 1600, 'scale': 2}}
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
                    cv2.putText(img, "❌ لا يمكن الاتصال", (50, 240), cv2.FONT_HERSHEY_SIMPLEX, 1, (0,0,255), 2)
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
    
    CAMERAS = {"كاميرا 1 - المدخل": "rtsp://admin:password@192.168.1.100:554/stream1"}
    
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
                    rtc_configuration=RTCConfiguration({"iceServers": [{"urls": ["stun:stun.l.google.com:19302"]}]}),
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
