"""
ملف الدوال المشتركة (shared.py)
"""
import streamlit as st
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
    """تطبيق التنسيقات المشتركة وتكبير كل التفاصيل الصغيرة"""
    st.markdown("""
    <style>
        /* 1. إخفاء الهيدر */
        header[data-testid="stHeader"] { display: none !important; }
        [data-testid="stToolbar"] { display: none !important; }
        [data-testid="manage-app-button"] { display: none !important; }
        footer { display: none !important; }

        /* 2. تكبير النصوص الأساسية */
        html, body, .stApp, [class*="css"] {
            font-size: 20px !important; 
        }

        /* 3. تكبير النصوص داخل الـ Markdown (التي نستخدمها في البطاقات والرسائل) */
        .stMarkdown p, .stMarkdown li, .stMarkdown div {
            font-size: 20px !important;
        }

        /* 4. تكبير مربعات الاختيار (Checkboxes) والنصوص التابعة لها */
        div[data-testid="stCheckbox"] label p {
            font-size: 22px !important;
            font-weight: bold !important;
        }
        div[role="checkbox"] {
            transform: scale(1.3); /* تكبير المربع نفسه */
        }

        /* 5. تكبير أسماء الأعمدة والقوائم المنسدلة (Selectbox/Multiselect) */
        div[data-baseweb="select"] * {
            font-size: 20px !important;
        }

        /* 6. تكبير النصوص داخل الجداول (DataFrame) */
        div[data-testid="stDataFrame"] * {
            font-size: 18px !important;
        }

        /* 7. تكبير التنبيهات والملاحظات */
        div[data-testid="stNotification"] * {
            font-size: 20px !important;
        }

        /* 8. تكبير العناوين الفرعية (Expander) */
        details > summary {
            font-size: 20px !important;
            font-weight: bold !important;
        }

        /* 9. تكبير الأزرار ونصوصها */
        .stButton > button, div[data-testid="stButton"] > button {
            font-size: 20px !important;
            font-weight: bold !important;
        }
        .stButton > button *, div[data-testid="stButton"] > button * {
            font-size: 20px !important;
        }
    </style>
    """, unsafe_allow_html=True)

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
