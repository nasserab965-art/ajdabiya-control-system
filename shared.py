"""
ملف الدوال المشتركة (shared.py)
يجب أن يكون موجوداً في المجلد الرئيسي (E:\firstpy)
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
    """تنسيقات CSS مشتركة لكل الصفحات + إجبار الاتجاه لليسار + إخفاء الهيدر"""
    
    # كود JavaScript لإجبار الاتجاه LTR
    components.html(
        """
        <script>
            setTimeout(function() {
                var doc = window.parent.document;
                doc.documentElement.setAttribute('dir', 'ltr');
                doc.body.setAttribute('dir', 'ltr');
                var sidebar = doc.querySelector('[data-testid="stSidebar"]');
                if (sidebar) {
                    sidebar.setAttribute('dir', 'ltr');
                }
            }, 1000);
        </script>
        """,
        height=0, width=0
    )

    # كود CSS
    st.markdown("""
    <style>
        /* 🛑 إخفاء الشريط العلوي (الذي يحتوي على GitHub و Fork و Manage app) */
        header[data-testid="stHeader"] { display: none !important; }
        [data-testid="stToolbar"] { display: none !important; }
        [data-testid="manage-app-button"] { display: none !important; }
        
        /* إجبار الاتجاه لليسار */
        .stApp { direction: ltr !important; }
        
        /* إجبار القائمة الجانبية على اليسار */
        [data-testid="stSidebar"] {
            left: 0 !important;
            right: auto !important;
            direction: ltr !important;
        }
        
        /* محاذاة النصوص لليسار */
        .stMarkdown { text-align: left !important; }
        
        /* إخفاء أزرار إضافية */
        [data-testid="collapsedControl"] { display: none !important; }
        footer { display: none !important; }
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
