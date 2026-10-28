"""
ملف الدوال المشتركة (shared.py)
يجب أن يكون موجوداً في المجلد الرئيسي (E:\firstpy)
"""
import streamlit as st
import streamlit.components.v1 as components
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
    """تنسيقات CSS مشتركة لكل الصفحات + إجبار الاتجاه لليسار"""
    
    # ═══════════════════════════════════════════════════════════
    # 🌟 الحل الجذري: استخدام JavaScript لإجبار الاتجاه LTR
    # ═══════════════════════════════════════════════════════════
    components.html(
        """
        <script>
            // انتظر حتى يتم تحميل الصفحة بالكامل
            setTimeout(function() {
                // تغيير اتجاه الصفحة الرئيسية
                var doc = window.parent.document;
                doc.documentElement.setAttribute('dir', 'ltr');
                doc.body.setAttribute('dir', 'ltr');
                
                // تغيير اتجاه القائمة الجانبية
                var sidebar = doc.querySelector('[data-testid="stSidebar"]');
                if (sidebar) {
                    sidebar.setAttribute('dir', 'ltr');
                }
            }, 1000); // تأخير بسيط لضمان تحميل العناصر
        </script>
        """,
        height=0,
        width=0
    )

    # ═══════════════════════════════════════════════════════════
    # 🎨 أكواد الـ CSS (تم تعديلها لتتوافق مع الاتجاه الجديد)
    # ═══════════════════════════════════════════════════════════
    st.markdown("""
    <style>
        /* إجبار اتجاه الصفحة لليسار في الـ CSS أيضاً (كطبقة إضافية) */
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
