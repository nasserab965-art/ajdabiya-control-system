"""
الصفحة 1: التقرير اليومي + الكاميرات + قراءات الخطوط (نسخة ذكية مع الصلاحيات)
"""
import sys
import os
import platform
import time
import base64
from datetime import datetime, date, timedelta
from io import BytesIO
import streamlit as st

# ═══════════════════════════════════════════════════════════
# 🛡️ حماية الصفحة (يجب أن تكون في البداية)
# ═══════════════════════════════════════════════════════════
if 'user_level' not in st.session_state or st.session_state.user_level == 0:
    st.error("⛔ غير مصرح لك بالدخول. يرجى تسجيل الدخول أولاً.")
    st.stop()

# صلاحية التقرير اليومى (مسموح للمستويات 1 ,2 ,3)
if st.session_state.user_level not in [1, 2, 3]:
    st.error("⛔ عذراً، حسابك لا يملك الصلاحية لعرض هذه الصفحة.")
    st.stop()

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
import plotly.graph_objects as go
import fitz
import requests
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from streamlit_autorefresh import st_autorefresh

from shared import check_login, apply_common_css, back_to_home_button, load_table

st.set_page_config(
    page_title="التقرير اليومي",
    page_icon="📋",
    layout="wide"
)

apply_common_css()

# ═══════════════════════════════════════════════════════════
# 🛑 إخفاء الشريط وتقليل المسافات العلوية + تكبير الأيقونات
# ═══════════════════════════════════════════════════════════
st.markdown("""
<style>
    header[data-testid="stHeader"] { display: none !important; }
    [data-testid="stToolbar"] { display: none !important; }
    [data-testid="stDecoration"] { display: none !important; }
    #MainMenu { visibility: hidden !important; }
    footer { visibility: hidden !important; }

    .block-container {
        padding-top: 1rem !important;
        padding-bottom: 0rem !important;
    }

    div[data-testid="stTabs"] {
        margin-top: -10px !important;
    }

    /* ⬇️ تكبير أيقونات شريط أدوات Plotly (Modebar) وتباعدها ⬇️ */
    .modebar-container {
        top: 15px !important;
        right: 15px !important;
    }
    
    .modebar-btn {
        padding: 10px !important;
        margin: 4px 2px !important;
    }
    
    .modebar-btn svg {
        width: 24px !important;
        height: 24px !important;
        transform: scale(1.3) !important;
    }
    
    .modebar-group {
        padding: 5px !important;
        margin-bottom: 12px !important;
    }
    
    .modebar {
        padding: 8px !important;
        border-radius: 8px !important;
    }
</style>
""", unsafe_allow_html=True)

is_local_network = platform.system() == "Windows"

NETWORK_PDF_PATH = r'\\CTRL-ROOM\ctsh\Daily_rep.pdf'
LOCAL_IMAGE_PATH = 'Daily_rep.png'
LOCAL_CAMERA_PATH = 'live_camera.jpg'
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
# 🖼️ دوال معالجة الصور
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

def is_valid_image(image_path):
    try:
        if not os.path.exists(image_path) or os.path.getsize(image_path) == 0:
            return False
        with Image.open(image_path) as img:
            img.verify()
        return True
    except Exception:
        try:
            os.remove(image_path)
        except Exception:
            pass
        return False

# ═══════════════════════════════════════════════════════════
# 🌟 دالة التحويل الذكية
# ═══════════════════════════════════════════════════════════
def convert_pdf_to_image():
    if not is_local_network:
        GITHUB_TOKEN = st.secrets.get("GITHUB_TOKEN", "")
        if not GITHUB_TOKEN:
            return False, "❌ لم يتم العثور على GITHUB_TOKEN في إعدادات Streamlit Cloud."
        try:
            headers = {"Authorization": f"token {GITHUB_TOKEN}"}
            url = "https://api.github.com/repos/nasserab965-art/ajdabiya-control-system/contents/Daily_rep.pdf"
            response = requests.get(url, headers=headers, timeout=10)
            if response.status_code == 200:
                file_data = response.json()
                content_b64 = file_data.get("content")
                if content_b64:
                    pdf_bytes = base64.b64decode(content_b64)
                    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
                    page = doc[0]
                    mat = fitz.Matrix(3, 3)
                    pix = page.get_pixmap(matrix=mat, alpha=False)
                    pix.save(LOCAL_IMAGE_PATH)
                    doc.close()
                    optimize_image(LOCAL_IMAGE_PATH, max_width=2500)
                    add_timestamp_to_image(LOCAL_IMAGE_PATH)
                    add_watermark_to_image(LOCAL_IMAGE_PATH, text="غرفة تحكم اجدابيا")
                    return True, "✅ تم تحديث التقرير من GitHub بنجاح!"
                return False, "⚠️ ملف الـ PDF موجود في GitHub لكنه فارغ."
            return False, f"⚠️ فشل جلب الـ PDF من GitHub. كود الخطأ: {response.status_code}"
        except Exception as e:
            return False, f"❌ حدث خطأ أثناء جلب الـ PDF: {e}"
    else:
        if not os.path.exists(NETWORK_PDF_PATH):
            return False, f"❌ لا يمكن الوصول لملف الـ PDF في المسار:\n`{NETWORK_PDF_PATH}`"
        try:
            doc = fitz.open(NETWORK_PDF_PATH)
            page = doc[0]
            mat = fitz.Matrix(3, 3)
            pix = page.get_pixmap(matrix=mat, alpha=False)
            pix.save(LOCAL_IMAGE_PATH)
            doc.close()
            optimize_image(LOCAL_IMAGE_PATH, max_width=2500)
            add_timestamp_to_image(LOCAL_IMAGE_PATH)
            add_watermark_to_image(LOCAL_IMAGE_PATH, text="غرفة تحكم اجدابيا")
            return True, "✅ تم تحديث صورة التقرير من الشبكة بنجاح!"
        except Exception as e:
            return False, f"❌ خطأ أثناء التحويل: {e}"

# ═══════════════════════════════════════════════════════════
# 🌟 تعريف الأعمدة بالاعتماد على الترتيب (index) وليس الاسم
# ═══════════════════════════════════════════════════════════
DATE_COL_INDEX = 0
DATE_COL = 'DATE_INTERNAL'

VALUE_COLS = {
    'COL_SS':  {'label': 'S/S TOT AJD',    'color': '#F9CA24', 'index': 14},
    'COL_TB':  {'label': 'T/B TOT AJD',    'color': '#AFFF00', 'index': 16},
    'COL_AB':  {'label': 'A/B TOT AJD',    'color': '#4A90D9', 'index': 20},
    'COL_AS':  {'label': 'A/S TOT AJD',    'color': '#FF6B6B', 'index': 21},
    'COL_LOS': {'label': 'الفاقد',          'color': '#FFFB6B', 'index': 29},
    'COL_RES': {'label': 'RES. LEVEL AJD', 'color': '#FFFFFF', 'index': 24},
}

@st.cache_data(ttl=10, show_spinner=False)
def load_tank_data(path, sheet_names):
    if isinstance(sheet_names, str):
        sheet_names = [sheet_names]

    frames = []
    info_lines = []
    loaded_sheets = []

    needed_indices = [DATE_COL_INDEX] + [m['index'] for m in VALUE_COLS.values()]
    max_needed = max(needed_indices)

    for sheet in sheet_names:
        try:
            raw = pd.read_excel(path, sheet_name=sheet, header=None)

            if raw.empty or raw.shape[1] <= max_needed:
                info_lines.append(f"⚠️ شيت '{sheet}': عدد الأعمدة غير كافٍ ({raw.shape[1]} < {max_needed + 1}) → تم التخطي")
                continue

            data = pd.DataFrame()
            data[DATE_COL] = pd.to_datetime(raw.iloc[:, DATE_COL_INDEX], errors='coerce')

            for key, meta in VALUE_COLS.items():
                data[key] = pd.to_numeric(raw.iloc[:, meta['index']], errors='coerce')

            data = data.dropna(subset=[DATE_COL])
            data = data.dropna(how='all', subset=list(VALUE_COLS.keys()))

            if data.empty:
                info_lines.append(f"ℹ️ شيت '{sheet}': فارغ → تم التخطي")
                continue

            data['_sheet'] = sheet
            frames.append(data)
            loaded_sheets.append(f"{sheet} ({len(data)})")

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
        
        modebar=dict(
            orientation='v',
            bgcolor='rgba(11, 30, 63, 0.7)',
            color='#FFFFFF',
            activecolor='#F9CA24'
        )
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
        total_sum = series.sum()

        if delta > 0: delta_color = '#AFFF00'; delta_icon = '▲'
        elif delta < 0: delta_color = '#FF6B6B'; delta_icon = '▼'
        else: delta_color = '#E8F4FD'; delta_icon = '●'

        with stat_cols[idx]:
            st.markdown(f"""
            <div style="background: linear-gradient(135deg, #0B1E3F 0%, #163A6B 100%); border-radius: 12px; padding: 20px 15px; border-right: 5px solid {meta['color']}; direction: rtl; text-align: center; min-height: 280px; box-shadow: 0 0 15px rgba(74, 144, 217, 0.2);">
                <div style="color: {meta['color']}; font-size: 18px; font-weight: bold; margin-bottom: 12px; padding-bottom: 8px; border-bottom: 1px solid #4A90D9;">
                    🛢️ خط {meta['label']}
                </div>
                <div style="color: #FFFFFF; font-size: 28px; font-weight: bold; margin: 10px 0;">
                    {last_val:,.2f}
                </div>
                <div style="color: #AFFF00; font-size: 14px; margin-bottom: 8px;">
                    ⏱️ آخر قراءة
                </div>
                <div style="color: {delta_color}; font-size: 16px; font-weight: bold; margin-bottom: 15px; background: rgba(0,0,0,0.2); border-radius: 6px; padding: 6px 10px; display: inline-block;">
                    {delta_icon} {abs(delta):,.2f} عن الأمس
                </div>
                <div style="color: #E8F4FD; font-size: 16px; line-height: 2; text-align: right; padding: 0 10px;">
                    📊 <b>المتوسط:</b> {series.mean():,.2f}<br>
                    📈 <b>الأعلى:</b> {series.max():,.2f}<br>
                    📉 <b>الأدنى:</b> {series.min():,.2f}
                </div>
            """, unsafe_allow_html=True)

            if col != 'COL_RES':
                st.markdown(f"""
                <div style="color: #FFFFFF; font-size: 20px; font-weight: bold; margin-top: 15px; background-color: #1E5A96; border-radius: 8px; padding: 8px;">
                    الإجمالي: <span style="color: {meta['color']}; font-size: 22px;">{total_sum:,.2f}</span>
                </div>
                """, unsafe_allow_html=True)

            st.markdown("</div>", unsafe_allow_html=True)

col_title, col_btn = st.columns([3, 1])
with col_title:
    st.markdown("""
    <h2 style='margin: 0; padding-bottom: 5px; font-family: Arial; font-size: 24px; color: #1A5276;'>
        📋 التقرير اليومي + 📹 المباشر
    </h2>
    """, unsafe_allow_html=True)
with col_btn:
    if st.button("🏠 العودة للرئيسية", width="stretch", type="primary", key="back_top"):
        st.switch_page("app_main.py")

# ═══════════════════════════════════════════════════════════
# 🎯 بناء التبويبات بناءً على الصلاحيات
# ═══════════════════════════════════════════════════════════
# صلاحية عرض الكاميرات المباشرة (اجعلها 1 فقط للمدير، أو 1 و 3 للفنيين)
can_view_camera = st.session_state.user_level in [1] 

if can_view_camera:
    tab1, tab2 = st.tabs(["📋 التقرير اليومي", "📹 المباشر | لقطة كل 30 ثانية"])
else:
    tab1, = st.tabs(["📋 التقرير اليومي"])

with tab1:
    st.markdown("""
    <div style="background: linear-gradient(135deg, #0B1E3F 0%, #163A6B 50%, #1E5A96 100%); border-radius: 22px; padding: 45px 50px; margin: 20px 0 30px 0; border: 2px solid #4A90D9; box-shadow: 0 0 25px rgba(74, 144, 217, 0.35), 0 0 70px rgba(74, 144, 217, 0.15), inset 0 0 50px rgba(74, 144, 217, 0.08); direction: rtl; text-align: center;">
        <h1 style="color: #F9CA24; font-size: 48px; margin: 0 0 25px 0; text-shadow: 2px 2px 10px rgba(0,0,0,0.5); font-weight: bold; font-family: Arial, sans-serif;">🌟 مشروع النهر الصناعى - المرحلة الأولى 🌟</h1>
        <h2 style="color: #FFFFFF; font-size: 38px; margin: 0 0 35px 0; text-shadow: 1px 1px 5px rgba(0,0,0,0.5); font-weight: bold; font-family: Arial, sans-serif;">📍 غرفة تحكم اجدابيا</h2>
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
        <code style="color: #AFFF00; font-size: 15px; background: rgba(0,0,0,0.3); padding: 2px 8px; border-radius: 4px; margin-right: 10px;">{NETWORK_PDF_PATH}</code>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("### 📋 التقرير اليومي - Daily_rep")

    if not is_valid_image(LOCAL_IMAGE_PATH):
        if os.path.exists(LOCAL_IMAGE_PATH):
            os.remove(LOCAL_IMAGE_PATH)
            
    if os.path.exists(LOCAL_IMAGE_PATH) and is_local_network:
        if os.path.exists(NETWORK_PDF_PATH):
            net_mtime = os.path.getmtime(NETWORK_PDF_PATH)
            img_mtime = os.path.getmtime(LOCAL_IMAGE_PATH)
            if net_mtime > img_mtime:
                with st.spinner('🔄 تم اكتشاف تحديث جديد، جاري التحديث...'):
                    convert_pdf_to_image()
    elif not is_local_network and not os.path.exists(LOCAL_IMAGE_PATH):
        with st.spinner('🔄 جاري تجهيز التقرير...'):
            convert_pdf_to_image()

    col1, col2 = st.columns([1, 1])
    with col1:
        if st.button("🔄 إعادة توليد التقرير", width="stretch", type="primary"):
            with st.spinner('⏳ جاري التحويل...'):
                ok, msg = convert_pdf_to_image()
                if ok:
                    st.success(msg)
                    st.rerun()
                else:
                    st.error(msg)

    with col2:
        if os.path.exists(LOCAL_IMAGE_PATH):
            mtime = datetime.fromtimestamp(os.path.getmtime(LOCAL_IMAGE_PATH))
            st.info(f"📅 آخر تحديث للصورة: {mtime.strftime('%Y-%m-%d %H:%M')}")

    st.markdown("---")

    if os.path.exists(LOCAL_IMAGE_PATH):
        try:
            img_width = st.slider("🔍 حجم العرض:", 600, 2500, 2200, 100, key="img_w")
            st.image(LOCAL_IMAGE_PATH, width=img_width)

            with open(LOCAL_IMAGE_PATH, "rb") as f:
                st.download_button(
                    "🖼️ تحميل الصورة PNG", data=f.read(),
                    file_name=f'Daily_rep_{datetime.now().strftime("%Y%m%d_%H%M%S")}.png',
                    mime='image/png', width="stretch"
                )
        except Exception as e:
            st.error(f"❌ حدث خطأ أثناء قراءة الصورة: {e}. جاري محاولة إعادة توليدها...")
            os.remove(LOCAL_IMAGE_PATH)
            convert_pdf_to_image()
            st.rerun()
    else:
        st.warning("⏳ جاري تحضير التقرير... اضغط زر إعادة التوليد")

    st.markdown("---")
    st.markdown("## 📊 قراءات الخطوط - 2026 فما بعد")

    df_tank, load_info = load_tank_data(MAINJOB_PATH, MAINJOB_SHEETS)

    if df_tank is None or df_tank.empty:
        st.warning(load_info)
    else:
        st.caption(load_info)

        with st.expander("🔍 فحص أعمدة الإكسل (للمراجعة فقط)"):
            try:
                _raw = pd.read_excel(MAINJOB_PATH, sheet_name=MAINJOB_SHEETS[0], header=None, nrows=8)
                st.write(f"**عدد الأعمدة:** {_raw.shape[1]}")
                st.dataframe(_raw, use_container_width=True)
                st.caption("تأكد من أرقام `index` في `VALUE_COLS` إن اختلف الترتيب.")
            except Exception as _e:
                st.info(f"تعذر قراءة الشيت للمراجعة: {_e}")

        ctrl_col1, ctrl_col2, ctrl_col3 = st.columns([2, 2, 1])

        with ctrl_col1:
            chart_type_map = {'📈 خطي + نقاط': 'lines+markers', '📉 خط فقط': 'lines', '📊 أعمدة': 'bar'}
            selected_label = st.radio("🎨 نوع الرسم:", options=list(chart_type_map.keys()), index=0, horizontal=True, key="chart_type_selector")
            chart_type = chart_type_map[selected_label]

        with ctrl_col2:
            min_date = df_tank[DATE_COL].min().date()
            max_available_date = df_tank[DATE_COL].max().date()

            today = datetime.now().date()
            max_date = min(today, max_available_date)

            if today.day <= 7:
                default_start = date(today.year, today.month, 1)
            else:
                default_start = max_date - pd.Timedelta(days=30)
                if isinstance(default_start, pd.Timestamp):
                    default_start = default_start.date()

            default_start = max(min_date, default_start)

            if default_start > max_date:
                default_start = min_date

            date_range = st.date_input(
                "📅 الفترة:",
                value=(default_start, max_date),
                min_value=min_date,
                max_value=max_available_date,
                key="date_range_filter",
            )

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
            start_date = df_tank[DATE_COL].min().date()
            end_date = df_tank[DATE_COL].max().date()

        if df_filtered.empty:
            st.warning("⚠️ لا توجد بيانات في الفترة المحددة")
        else:
            years = sorted(df_filtered[DATE_COL].dt.year.unique())
            year_label = " / ".join(str(y) for y in years)

            st.plotly_chart(
                plot_tank_data(df_filtered, chart_type, year_label),
                use_container_width=True,
                theme=None, 
                config={'displayModeBar': True, 'scrollZoom': True, 'toImageButtonOptions': {'format': 'png', 'filename': f'tank_readings_{year_label.replace(" / ", "_")}_{datetime.now().strftime("%Y%m%d")}', 'height': 800, 'width': 1600, 'scale': 2}}
            )

            if show_stats:
                st.markdown("### 📈 إحصائيات سريعة لكل خط")
                render_tank_stats(df_filtered)

            st.markdown("---")
            with st.expander(f"📋 جدول قراءات الخطوط للفترة المختارة ({start_date} → {end_date}) — {len(df_filtered)} صف", expanded=False):
                table_df = df_filtered.copy()
                rename_map = {DATE_COL: 'اليوم'}
                for key, meta in VALUE_COLS.items():
                    if key in table_df.columns:
                        rename_map[key] = meta['label']
                table_df = table_df.rename(columns=rename_map)

                if 'اليوم' in table_df.columns:
                    table_df['اليوم'] = pd.to_datetime(table_df['اليوم']).dt.strftime('%Y-%m-%d')

                ordered_cols = ['اليوم'] + [m['label'] for m in VALUE_COLS.values() if m['label'] in table_df.columns]
                table_df = table_df[ordered_cols]

                st.dataframe(
                    table_df.style
                    .format({col: '{:,.2f}' for col in ordered_cols if col != 'اليوم'})
                    .set_properties(**{'text-align': 'center'})
                    .set_table_styles([dict(selector='th', props=[('text-align', 'center')])]),
                    use_container_width=True,
                    hide_index=True,
                    height=min(600, 40 + 35 * len(table_df)),
                )

                st.caption(f"📊 عدد الصفوف: {len(table_df)}
