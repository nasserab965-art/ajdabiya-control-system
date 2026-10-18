"""
ملف الدوال المشتركة (shared.py)
يجب أن يكون موجوداً في المجلد الرئيسي (E:\firstpy)
"""
import streamlit as st
import pandas as pd
import sqlite3

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
    """تنسيقات CSS مشتركة لكل الصفحات"""
    st.markdown("""
    <style>
        .stApp { direction: rtl; }
        .stMarkdown { text-align: right; }
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
    """تحميل جدول من قاعدة البيانات"""
    try:
        conn = sqlite3.connect('app_data.db')
        df = pd.read_sql_query(f"SELECT * FROM {table_name}", conn)
        conn.close()
        return df
    except Exception:
        return None