"""
🏠 الصفحة الرئيسية — حل نهائي مخصص
"""
import streamlit as st
import os
import hashlib
import base64

USER_PASSWORD_HASH = "03ac674216f3e15c761ee1a5e255f067953623c8b388b4459e13f978d7c846f4"
BACKGROUND_IMAGE_PATH = "gmmra1.jpg"

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

st.set_page_config(
    page_title="قراءات غرف التحكم-PH1",
    page_icon="🏠",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# ═══════════════════════════════════════════════════════════
# 🔐 تسجيل الدخول
# ═══════════════════════════════════════════════════════════
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False

if not st.session_state.logged_in:
    st.markdown("""
    <style>
        section[data-testid="stSidebar"] { display: none !important; }
        header[data-testid="stHeader"] { display: none !important; }
    </style>
    """, unsafe_allow_html=True)
    
    if os.path.exists(BACKGROUND_IMAGE_PATH):
        with open(BACKGROUND_IMAGE_PATH, "rb") as f:
            img_data = base64.b64encode(f.read()).decode()
        st.markdown(f"""
        <style>
            .stApp {{
                background-image: url("data:image/jpeg;base64,{img_data}");
                background-size: cover;
                background-position: center;
            }}
            .stApp::before {{
                content: ""; position: fixed; top:0; left:0;
                width:100%; height:100%; background: rgba(0,0,0,0.35); z-index:0;
            }}
            .stApp > * {{ position: relative; z-index: 1; }}
        </style>
        """, unsafe_allow_html=True)
    
    col1, col2 = st.columns([3, 1])
    with col2:
        st.markdown("<br><br><br><br>", unsafe_allow_html=True)
        st.markdown("""
        <div style="background: rgba(255,255,255,0.95); padding: 20px;
            border-radius: 15px; text-align: center;
            box-shadow: 0 10px 40px rgba(0,0,0,0.5);">
            <h3 style="color: #1A5276; margin: 0;">🔐 الدخول</h3>
        </div>
        """, unsafe_allow_html=True)
        
        pwd = st.text_input("🔑 الرقم السري", type="password", key="pwd_main")
        if st.button("🚪 دخول", use_container_width=True, type="primary", key="login_main"):
            if hash_password(pwd) == USER_PASSWORD_HASH:
                st.session_state.logged_in = True
                st.rerun()
            else:
                st.error("❌ الرقم غير صحيح")
    st.stop()

# ═══════════════════════════════════════════════════════════
# 🎨 CSS العام (إخفاء الشريط و Manage app)
# ═══════════════════════════════════════════════════════════
st.markdown("""
<style>
    section[data-testid="stSidebar"] { display: none !important; }
    header[data-testid="stHeader"] { display: none !important; }
    [data-testid="stToolbar"] { display: none !important; }
    [data-testid="collapsedControl"] { display: none !important; }
    
    /* 🛑 إخفاء زر Manage app */
    [data-testid="manage-app-button"] { display: none !important; }
    
    footer { display: none !important; }
    
    html, body {
        overflow: hidden !important;
        height: 100vh !important;
        width: 100vw !important;
        margin: 0 !important;
        padding: 0 !important;
    }
    
    .stApp {
        background: #000 !important;
        overflow: hidden !important;
        height: 100vh !important;
        width: 100vw !important;
        margin: 0 !important;
        padding: 0 !important;
    }
    
    .block-container {
        padding: 0 !important;
        margin: 0 !important;
        max-width: 100vw !important;
        width: 100vw !important;
    }
    
    [data-testid="stAppViewContainer"],
    [data-testid="stVerticalBlock"],
    [data-testid="stVerticalBlockBorderWrapper"],
    section.main,
    .main {
        padding: 0 !important;
        margin: 0 !important;
        gap: 0 !important;
    }
    
    .map-bg {
        position: fixed;
        top: 0;
        left: 0;
        width: 100vw;
        height: 100vh;
        min-width: 100vw;
        min-height: 100vh;
        object-fit: cover;
        object-position: center center;
        z-index: 0;
        margin: 0;
        padding: 0;
        border: none;
        display: block;
    }

    /* شريط الأدوات المخصص */
    .custom-toolbar {
        position: fixed;
        top: 15px;
        right: 20px;
        z-index: 9999;
        display: flex;
        align-items: center;
        gap: 15px;
        background: rgba(0, 0, 0, 0.4);
        padding: 8px 18px;
        border-radius: 30px;
        backdrop-filter: blur(5px);
        direction: ltr;
        box-shadow: 0 4px 15px rgba(0,0,0,0.3);
    }
    
    .custom-toolbar a, .custom-toolbar span {
        color: #FFFFFF !important;
        text-decoration: none;
        font-size: 20px;
        cursor: pointer;
        transition: 0.2s;
        display: flex;
        align-items: center;
        justify-content: center;
        font-weight: normal;
    }
    
    .custom-toolbar a:hover, .custom-toolbar span:hover {
        color: #F9CA24 !important;
        transform: scale(1.15);
    }
</style>
""", unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════
# 🗺️ الخريطة كخلفية
# ═══════════════════════════════════════════════════════════
if os.path.exists(BACKGROUND_IMAGE_PATH):
    with open(BACKGROUND_IMAGE_PATH, "rb") as f:
        img_data = base64.b64encode(f.read()).decode()
    st.markdown(
        f'<img src="data:image/jpeg;base64,{img_data}" class="map-bg"/>',
        unsafe_allow_html=True
    )

# ═══════════════════════════════════════════════════════════
# 🎨 شريط الأدوات المخصص (بدون GitHub وبدون القلم)
# ═══════════════════════════════════════════════════════════
toolbar_html = """
<div class="custom-toolbar">
    <!-- النجمة -->
   # <a href="https://github.com/nasserab965-art/ajdabiya-control-system" target="_blank" title="النجمة">☆</a>
    
    <!-- المشاركة -->
    <span title="مشاركة الرابط" onclick="navigator.clipboard.writeText(window.location.href); alert('تم نسخ الرابط بنجاح!')">🔗</span>

    <!-- النقاط الثلاث -->
    <span title="القائمة" style="letter-spacing: 2px; font-size: 24px; margin-left: 5px;">⋮</span>
</div>
"""
# استخدام st.html لضمان تنفيذ الكود كـ HTML وليس كنص
st.html(toolbar_html)

# ═══════════════════════════════════════════════════════════
# 🎨 CSS للأزرار — تصميم متدرج
# ═══════════════════════════════════════════════════════════
st.html("""
<style>
    div[data-testid="stButton"] > button {
        min-height: 85px !important;
        font-family: Arial, sans-serif !important;
        font-weight: 900 !important;
        font-size: 22px !important;
        border-radius: 14px !important;
        border: 3px solid #FFFFFF !important;
        color: #FFFFFF !important;
        text-shadow: 2px 2px 8px rgba(0,0,0,0.85) !important;
        letter-spacing: 0.4px !important;
        transition: all 0.3s ease !important;
        padding: 20px 22px !important;
        width: 100% !important;
        line-height: 1.3 !important;
        box-shadow: 0 8px 25px rgba(0,0,0,0.6) !important;
        margin-bottom: 22px !important;
    }
    
    div[data-testid="stButton"] > button:hover {
        transform: translateY(-4px) scale(1.03) !important;
        box-shadow: 0 14px 35px rgba(0,0,0,0.9) !important;
    }
    
    div[data-testid="stButton"] > button *,
    div[data-testid="stButton"] > button p,
    div[data-testid="stButton"] > button span,
    div[data-testid="stButton"] > button div {
        color: #000000 !important;
        font-family: Arial, sans-serif !important;
        font-size: 22px !important;
        font-weight: 900 !important;
        text-shadow: 2px 2px 8px rgba(0,0,0,0.85) !important;
    }
    
    button[key="go_daily"] {
        background: linear-gradient(135deg, #FF416C 0%, #FF4B2B 50%, #E74C3C 100%) !important;
        box-shadow: 0 8px 25px rgba(231, 76, 60, 0.7) !important;
    }
    button[key="go_daily"]:hover {
        box-shadow: 0 14px 35px rgba(231, 76, 60, 1) !important;
    }
    
    button[key="go_archive"] {
        background: linear-gradient(135deg, #8E2DE2 0%, #A569BD 50%, #7D3C98 100%) !important;
        box-shadow: 0 8px 25px rgba(125, 60, 152, 0.7) !important;
    }
    button[key="go_archive"]:hover {
        box-shadow: 0 14px 35px rgba(125, 60, 152, 1) !important;
    }
    
    button[key="go_maps"] {
        background: linear-gradient(135deg, #11998E 0%, #38EF7D 50%, #1E8449 100%) !important;
        box-shadow: 0 8px 25px rgba(30, 132, 73, 0.7) !important;
    }
    button[key="go_maps"]:hover {
        box-shadow: 0 14px 35px rgba(30, 132, 73, 1) !important;
    }
    
    button[key="logout_main"] {
        background: linear-gradient(135deg, #C0392B 0%, #E74C3C 100%) !important;
        min-height: 55px !important;
        font-size: 18px !important;
    }
    button[key="logout_main"] * {
        font-size: 18px !important;
    }
</style>
""")

# ═══════════════════════════════════════════════════════════
# 🎯 الأزرار الرئيسية
# ═══════════════════════════════════════════════════════════
st.markdown("<br>" * 12, unsafe_allow_html=True)

col_left, col_spacer = st.columns([1, 3])

with col_left:
    if st.button("📋  التقرير اليومي + الكاميرات", key="go_daily", use_container_width=True):
        st.switch_page("pages/1_📋_Daily.py")
    
    if st.button("📈  أرشيف القراءات 2025 + 2026", key="go_archive", use_container_width=True):
        st.switch_page("pages/2_📈_Archive.py")
    
    if st.button("🗺️  الخطوط والمحطات وخرائط Google", key="go_maps", use_container_width=True):
        st.switch_page("pages/3_🗺️_Maps.py")
    
    if st.button("🚪  تسجيل الخروج", key="logout_main", use_container_width=True):
        st.session_state.logged_in = False
        st.query_params.clear()
        st.rerun()
