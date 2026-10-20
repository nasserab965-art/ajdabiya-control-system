"""
🖼️ معرض الصور
"""
import sys
import os

# ⚠️ يجب أن يكون هذا السطر في البداية وقبل أي استيراد آخر
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import streamlit as st

# استيراد الدوال المشتركة
from shared import check_login, apply_common_css, back_to_home_button

# ═══════════════════════════════════════════════════════════
# 🚀 الإعداد الأولي
# ═══════════════════════════════════════════════════════════
st.set_page_config(page_title="معرض الصور", page_icon="🖼️", layout="wide")

# تطبيق التنسيقات المشتركة
apply_common_css()

# التحقق من تسجيل الدخول
check_login()

# ═══════════════════════════════════════════════════════════
# 🎨 CSS خاص بالأزرار (نظراً لوجود أزرار تحميل تحتاج لتنسيق)
# ═══════════════════════════════════════════════════════════
GLOBAL_BUTTON_CSS = """
<style>
    .stButton > button, .stButton > button *, .stDownloadButton > button, .stDownloadButton > button * {
        font-size: 18px !important;
        font-weight: bold !important;
    }
    .stButton > button, .stDownloadButton > button {
        min-height: 50px !important;
        border-radius: 10px !important;
    }
</style>
"""
st.markdown(GLOBAL_BUTTON_CSS, unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════
# 🏠 أزرار التنقل (أعلى الصفحة)
# ═══════════════════════════════════════════════════════════
col_left, col_right = st.columns([1, 1])

with col_right:
    if st.button("🏠 العودة للرئيسية", width="stretch", type="primary", key="back_top_album"):
        st.switch_page("app_main.py")

with col_left:
    if st.button("⬅️ رجوع", width="stretch", type="primary", key="back_to_maps_from_album"):
        # العودة إلى صفحة الخرائط
        st.switch_page("pages/3_🗺️_Maps.py")

st.markdown("---")



# ═══════════════════════════════════════════════════════════
# 🖼️ معرض الصور
# ═══════════════════════════════════════════════════════════
st.title("🖼️ معرض الصور")
st.markdown("تصفح صور المشروع والمواقع")
st.markdown("---")

# 📁 مسار مجلد الصور
ALBUM_PATH = os.path.join(os.path.dirname(__file__), "album")

SUPPORTED_EXTS = (
    '.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp',
    '.tiff', '.tif', '.ico', '.svg', '.jfif',
    '.avif', '.heic', '.heif',
)

MIME_MAP = {
    '.jpg': 'image/jpeg', '.jpeg': 'image/jpeg', '.jfif': 'image/jpeg',
    '.png': 'image/png', '.gif': 'image/gif', '.bmp': 'image/bmp',
    '.webp': 'image/webp', '.tiff': 'image/tiff', '.tif': 'image/tiff',
    '.ico': 'image/x-icon', '.svg': 'image/svg+xml',
    '.avif': 'image/avif', '.heic': 'image/heic', '.heif': 'image/heif',
}

if not os.path.exists(ALBUM_PATH):
    st.warning(f"⚠️ مجلد الصور غير موجود: {ALBUM_PATH}")
    st.info("💡 أنشئ المجلد وضع فيه صورك")
else:
    # ─── جمع كل الصور ───
    image_files = []
    for root, dirs, files in os.walk(ALBUM_PATH):
        dirs[:] = [d for d in dirs if not d.startswith('.')]
        for f in files:
            if f.startswith('.'):
                continue
            if f.lower().endswith(SUPPORTED_EXTS):
                image_files.append(os.path.join(root, f))
    image_files.sort()

    if not image_files:
        st.info("📭 لا توجد صور في المجلد حالياً")
        st.info(f"💡 ضع صورك في: {ALBUM_PATH}")
    else:
        st.success(f"✅ تم العثور على {len(image_files)} صورة")

        # ─── إعدادات العرض ───
        col1, col2 = st.columns([1, 3])
        with col1:
            columns_count = st.selectbox(
                "📐 عدد الأعمدة:",
                [1, 2, 3, 4, 5],
                index=2,
                key="album_cols"
            )
        with col2:
            img_height = st.slider(
                "📏 ارتفاع الصورة (بكسل):",
                min_value=150,
                max_value=600,
                value=280,
                step=10,
                key="album_h"
            )

        st.markdown("---")
        st.info("💡 اضغط على أي صورة لعرضها بالحجم الكامل")

        # ─── عرض الصور في شبكة ───
        cols = st.columns(columns_count)
        for idx, img_path in enumerate(image_files):
            with cols[idx % columns_count]:
                try:
                    ext = os.path.splitext(img_path)[1].lower()
                    img_name = os.path.basename(img_path)

                    if ext == '.svg':
                        with open(img_path, 'r', encoding='utf-8') as f:
                            svg_content = f.read()
                        st.markdown(
                            f'<div style="background:#fff;padding:8px;'
                            f'border-radius:8px;height:{img_height}px;'
                            f'display:flex;align-items:center;justify-content:center;">'
                            f'{svg_content}</div>',
                            unsafe_allow_html=True
                        )
                        st.caption(img_name)
                    else:
                        st.image(img_path, caption=img_name, use_container_width=True)

                    # ─── زر التحميل ───
                    mime = MIME_MAP.get(ext, 'application/octet-stream')
                    with open(img_path, "rb") as f:
                        st.download_button(
                            label="📥 تحميل",
                            data=f.read(),
                            file_name=img_name,
                            mime=mime,
                            key=f"dl_img_{idx}",
                            use_container_width=True,
                        )
                except Exception as e:
                    st.error(f"❌ خطأ في عرض {os.path.basename(img_path)}: {e}")

        st.markdown("---")
        st.caption(f"📊 إجمالي الصور: {len(image_files)}")

# ═══════════════════════════════════════════════════════════
# 🏠 أزرار التنقل السفلية
# ═══════════════════════════════════════════════════════════
st.markdown("---")

col1, col2, col3 = st.columns([1, 1, 1])
with col1:
    if st.button("⬅️ العودة إلى الخطوط والمحطات", width="stretch", type="secondary", key="back_to_maps"):
        st.switch_page("pages/3_🗺️_Maps.py")
with col3:
    if st.button("🏠 العودة للرئيسية", width="stretch", type="primary", key="back_bottom"):
        st.switch_page("app_main.py")
