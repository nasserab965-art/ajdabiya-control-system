"""
ملف الدوال المشتركة (shared.py)
"""
import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
import os

def check_login():
    if 'logged_in' not in st.session_state:
        st.session_state.logged_in = False
    if not st.session_state.logged_in:
        st.error("⚠️ يجب تسجيل الدخول أولاً")
        if st.button("🏠 العودة للرئيسية", type="primary", key="back_login_shared"):
            st.switch_page("app_main.py")
        st.stop()

def apply_common_css():
    """تطبيق التنسيقات المشتركة + التكبير عبر JavaScript"""
    
    # 1. كود CSS الأساسي (للاتجاه وإخفاء الهيدر)
    st.markdown("""
    <style>
        header[data-testid="stHeader"] { display: none !important; }
        [data-testid="stToolbar"] { display: none !important; }
        [data-testid="manage-app-button"] { display: none !important; }
        footer { display: none !important; }
        .stApp { direction: ltr !important; }
        [data-testid="stSidebar"] { left: 0 !important; right: auto !important; direction: ltr !important; }
        .stMarkdown { text-align: left !important; }
        [data-testid="collapsedControl"] { display: none !important; }
    </style>
    """, unsafe_allow_html=True)

    # 2. كود JavaScript (لتكبير الخطوط واختراق Shadow DOM)
    components.html(
        """
        <script>
            function applyZoom() {
                var parentDoc = window.parent.document;
                
                // إزالة أي تنسيق قديم
                var oldStyle = parentDoc.getElementById('custom-zoom-style');
                if (oldStyle) oldStyle.remove();

                // إنشاء وسم التنسيق الجديد
                var style = parentDoc.createElement('style');
                style.id = 'custom-zoom-style';
                style.innerHTML = `
                    /* تكبير الخط الأساسي */
                    html, body, .stApp { font-size: 22px !important; }
                    
                    /* تكبير العناوين */
                    h1 { font-size: 3rem !important; }
                    h2 { font-size: 2.5rem !important; }
                    h3 { font-size: 2rem !important; }
                    h4 { font-size: 1.6rem !important; }
                    
                    /* تكبير الأزرار */
                    button { font-size: 24px !important; font-weight: bold !important; min-height: 55px !important; }
                    button * { font-size: 24px !important; }
                    
                    /* تكبير القوائم المنسدلة */
                    div[data-baseweb="select"] * { font-size: 20px !important; }
                    
                    /* تكبير مربعات الاختيار والنصوص التابعة لها */
                    label[data-testid="stWidgetLabel"] p { font-size: 22px !important; font-weight: bold !important; }
                    div[data-testid="stCheckbox"] label p { font-size: 22px !important; }
                    div[role="checkbox"] { transform: scale(1.5); margin: 5px; }
                    
                    /* تكبير الجداول والتنبيهات */
                    div[data-testid="stDataFrame"] * { font-size: 18px !important; }
                    div[data-testid="stNotification"] * { font-size: 20px !important; }
                `;
                parentDoc.head.appendChild(style);
            }

            // تطبيق التكبير فوراً، ومراقبة أي تغييرات في الصفحة لتطبيقه مجدداً
            applyZoom();
            setTimeout(applyZoom, 500);
            setTimeout(applyZoom, 1500);
            
            // مراقبة إضافة عناصر جديدة (مثل فتح القوائم)
            var observer = new MutationObserver(function(mutations) {
                applyZoom();
            });
            observer.observe(window.parent.document.body, { childList: true, subtree: true });
        </script>
        """,
        height=0, width=0
    )

def back_to_home_button():
    st.markdown("---")
    col1, col2, col3 = st.columns([1, 2, 1])
    with col3:
        if st.button("🏠 العودة للرئيسية", width="stretch", type="primary", key="back_home_shared_btn"):
            st.switch_page("app_main.py")

@st.cache_data(ttl=60)
def load_table(table_name):
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
