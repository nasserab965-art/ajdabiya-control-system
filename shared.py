"""
ملف الدوال المشتركة (shared.py)
"""
import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
import os

def check_login():
    """التحقق من تسجيل الدخول"""
    if 'logged_in' not in st.session_state:
        st.session_state.logged_in = False
    
    if not st.session_state.logged_in:
        st.error("⚠️ يجب تسجيل الدخول أولاً")
        st.info("🏠 يرجى العودة للصفحة الرئيسية")
        if st.button("🏠 العودة للرئيسية", type="primary", key="back_login_shared"):
            st.switch_page("app_main.py")
        st.stop()

def apply_common_css():
    """تنسيقات CSS مشتركة + إجبار الخطوط على التكبير عبر JavaScript"""
    
    # كود JavaScript (يجبر المتصفح على تغيير الخطوط)
    components.html(
        """
        <script>
            setTimeout(function() {
                var doc = window.parent.document;
                
                // 1. إجبار الاتجاه لليسار
                doc.documentElement.setAttribute('dir', 'ltr');
                doc.body.setAttribute('dir', 'ltr');
                var sidebar = doc.querySelector('[data-testid="stSidebar"]');
                if (sidebar) {
                    sidebar.setAttribute('dir', 'ltr');
                }

                // 2. إجبار الخطوط على التكبير
                var style = doc.createElement('style');
                style.innerHTML = `
                    /* تكبير الخط الأساسي */
                    html, body, [class*="css"] { font-size: 22px !important; }
                    
                    /* تكبير العناوين */
                    h1 { font-size: 3rem !important; }
                    h2 { font-size: 2.5rem !important; }
                    h3 { font-size: 2rem !important; }
                    h4 { font-size: 1.6rem !important; }
                    
                    /* تكبير الأزرار */
                    .stButton > button, div[data-testid="stButton"] > button { font-size: 24px !important; font-weight: bold !important; min-height: 55px !important; }
                    .stButton > button *, div[data-testid="stButton"] > button * { font-size: 24px !important; }
                    
                    /* تكبير القوائم المنسدلة */
                    div[data-baseweb="select"] * { font-size: 20px !important; }
                    
                    /* تكبير الجداول والتنبيهات */
                    div[data-testid="stDataFrame"] * { font-size: 18px !important; }
                    div[data-testid="stNotification"] * { font-size: 20px !important; }
                    
                    /* إخفاء الهيدر */
                    header[data-testid="stHeader"] { display: none !important; }
                    [data-testid="stToolbar"] { display: none !important; }
                    [data-testid="manage-app-button"] { display: none !important; }
                    footer { display: none !important; }
                `;
                doc.head.appendChild(style);
            }, 500); // تأخير نصف ثانية لضمان تحميل الصفحة
        </script>
        """,
        height=0, width=0
    )

    # كود CSS احتياطي
    st.markdown("""
    <style>
        .stApp { direction: ltr !important; }
        [data-testid="stSidebar"] { left: 0 !important; right: auto !important; direction: ltr !important; }
        .stMarkdown { text-align: left !important; }
    </style>
    """, unsafe_allow_html=True)

def back_to_home_button():
    """زر العودة للرئيسية في أسفل الصفحة"""
    st.markdown("---")
    col1, col2, col3 = st.columns([1, 2, 1])
    with col3:
        if st.button("🏠 العودة للرئيسية", width="stretch", type="primary", key="back_home_shared_btn"):
            st.switch_page("app_main.py")

@st.cache_data(ttl=60)
def load_table(table_name):
    """تحميل البيانات من الإكسيل مباشرة"""
    try:
        excel_path = 'mainjob.xlsx'
        if not os.path.exists(excel_path):
            return None
            
        all_sheets = pd.read_excel(excel_path, sheet_name=None)
        target_year = str(table_name).replace('main_job_', '').replace('main_job', '2025')
        
        for sheet_name, df in all_sheets.items():
            if target_year in sheet_name or sheet_name == table_name:
                df.columns = [str(c).strip().replace('\n', '').replace('\r', '') for c in df.columns]
                return df
        return None
    except Exception:
        return None
