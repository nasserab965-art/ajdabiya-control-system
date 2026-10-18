"""
الصفحة 2: أرشيف القراءات 2030 → 2025
"""
import sys
import os

# ⚠️ يجب أن يكون هذا السطر في البداية وقبل أي استيراد آخر
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import streamlit as st
import pandas as pd
import sqlite3
import plotly.graph_objects as go
import time

# الآن يمكنك استيراد الملف المشترك بأمان
from shared import check_login, apply_common_css, back_to_home_button, load_table

st.set_page_config(page_title="أرشيف القراءات", page_icon="📈", layout="wide")

# ═══════════════════════════════════════════════════════════
# 🏠 زر العودة للرئيسية (أعلى الصفحة)
# ═══════════════════════════════════════════════════════════
col1, col2, col3 = st.columns([1, 2, 1])
with col3:
    if st.button("🏠 العودة للرئيسية", width="stretch", type="primary", key="back_top"):
        st.switch_page("app_main.py")

st.markdown("---")

if not st.session_state.get('logged_in', False):
    st.error("⚠️ يجب تسجيل الدخول أولاً")
    if st.button("🏠 العودة للرئيسية", type="primary", key="login_back"):
        st.switch_page("app_main.py")
    st.stop()

apply_common_css()
st.title("📈 أرشيف القراءات 2030 → 2025 م")

st.markdown("""
<style>
    /* تكبير خط العناوين الفرعية (مثل أسماء السنوات) */
    h3 {
        font-size: 1.6rem !important;
        font-weight: bold !important;
    }
    /* تكبير نصوص القوائم المنسدلة (Selectbox) */
    div[data-baseweb="select"] > div {
        font-size: 18px !important;
    }
    /* تكبير نصوص خانات الاختيار (Checkboxes) */
    .stCheckbox label span {
        font-size: 18px !important;
        font-weight: bold !important;
    }
    /* تكبير العناوين داخل الشريط الجانبي */
    [data-testid="stSidebar"] h3 {
        font-size: 1.4rem !important;
    }
    /* تكبير نصوص الأزرار */
    button p {
        font-size: 16px !important;
    }
    /* تقليل الفراغات الجانبية لتوسيع الصفحة */
    .block-container {
        padding-left: 2rem !important;
        padding-right: 2rem !important;
        max-width: 95% !important;
    }
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────
# دوال المزامنة والفحص
# ─────────────────────────────────────────────────────────────
def sync_all_excel_to_db():
    excel_path = 'mainjob.xlsx'
    db_path = 'app_data.db'
    if not os.path.exists(excel_path):
        return False, f"❌ الملف غير موجود في المسار: {os.path.abspath(excel_path)}"
    
    try:
        all_sheets = pd.read_excel(excel_path, sheet_name=None)
    except Exception as e:
        return False, f"❌ خطأ في قراءة ملف الإكسل: {e}"

    conn = sqlite3.connect(db_path)
    updated = []

    for sheet_name, df in all_sheets.items():
        if df.empty or df.dropna(how='all').empty:
            continue
        
        # تنظيف أسماء الأعمدة من المسافات
        df.columns = [str(c).strip() for c in df.columns]
        df = df.dropna(how='all').reset_index(drop=True)

        # البحث عن عمود التاريخ
        date_col = None
        for col in df.columns:
            if 'اليوم' in col or 'date' in col.lower() or 'تاريخ' in col:
                date_col = col
                break
        
        if not date_col:
            continue

        try:
            dates = pd.to_datetime(df[date_col], errors='coerce')
            valid_mask = dates.notna()
            if not valid_mask.any():
                continue
                
            df = df[valid_mask].copy()
            year = dates[valid_mask].dt.year.mode()[0]
            table_name = f"main_job_{year}" if year != 2025 else "main_job"
            
            df.to_sql(table_name, conn, if_exists='replace', index=False)
            updated.append(f"سنة {year} (جدول: {table_name} | {len(df)} صف)")
        except Exception as e:
            pass

    conn.close()
    if not updated:
        return False, "⚠️ لم يتم العثور على بيانات صالحة (تأكد من وجود عمود 'اليوم' وتواريخ صحيحة)."
    return True, "✅ تم التحديث:\n" + "\n".join(updated)

# ─────────────────────────────────────────────────────────────
# الشريط الجانبي
# ─────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### ⚙️ إدارة البيانات")
    
    # زر المزامنة
    if st.button("🔄 تحديث البيانات من الإكسل", use_container_width=True, type="primary"):
        with st.spinner("جاري المزامنة..."):
            success, msg = sync_all_excel_to_db()
            if success:
                st.success(msg)
                st.cache_data.clear()
                time.sleep(1.5)
                st.rerun()
            else:
                st.error(msg)
                
    st.markdown("---")
    
    # زر الفحص
    if st.button("🔍 فحص قاعدة البيانات (2027)", use_container_width=True):
        try:
            conn = sqlite3.connect('app_data.db')
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
            tables = [row[0] for row in cursor.fetchall()]
            
            if 'main_job_2027' in tables:
                df_check = pd.read_sql("SELECT * FROM main_job_2027", conn)
                st.success(f"✅ جدول 2027 موجود ويحتوي على {len(df_check)} صف.")
                st.write("**أول 5 أعمدة:**", df_check.columns.tolist()[:5])
            else:
                st.error("❌ جدول 2027 غير موجود بعد! اضغط على زر التحديث أولاً.")
                st.write("الجداول الموجودة:", tables)
            conn.close()
        except Exception as e:
            st.error(f"خطأ: {e}")

# ─────────────────────────────────────────────────────────────
# 1. تحميل البيانات
# ─────────────────────────────────────────────────────────────
YEAR_TABLES = {2025: "main_job", 2026: "main_job_2026", 2027: "main_job_2027", 2028: "main_job_2028", 2029: "main_job_2029", 2030: "main_job_2030"}
YEARS_DESC = sorted(YEAR_TABLES.keys(), reverse=True)

years_data = {}
for year, table_name in YEAR_TABLES.items():
    try:
        df = load_table(table_name)
        if df is not None and not df.empty:
            years_data[year] = df
    except Exception:
        pass

if not years_data:
    st.error("❌ لا توجد بيانات في أي عام! يرجى استخدام زر التحديث.")
    back_to_home_button()
    st.stop()

available_years = [y for y in YEARS_DESC if y in years_data]

# ─────────────────────────────────────────────────────────────
# 2. التحكم بالأعمدة (مرن - يجمع الأعمدة من كل السنوات)
# ─────────────────────────────────────────────────────────────
st.markdown("---")
col1, col2 = st.columns([1, 3])

# جلب الأعمدة من أحدث سنة متاحة للحفاظ على الترتيب الأصلي للإكسل
reference_year = available_years[0] # 2026 أو 2025
ref_df = years_data[reference_year]

# 1. ترتيب أعمدة المحور X (حسب ترتيب السنة المرجعية ثم أي إضافات)
common_all = [str(c) for c in ref_df.columns]
for y in available_years:
    for c in years_data[y].columns:
        if str(c) not in common_all:
            common_all.append(str(c))

# 2. ترتيب أعمدة المحور Y (الرقمية) حسب ترتيب السنة المرجعية
ref_numeric = [str(c) for c in ref_df.select_dtypes(include=['number']).columns]
common_numeric = list(ref_numeric) # نبدأ بأعمدة السنة المرجعية بالترتيب

# نضيف أي أعمدة رقمية جديدة موجودة في سنوات أخرى ولم تكن في السنة المرجعية
for y in available_years:
    for c in years_data[y].select_dtypes(include=['number']).columns:
        if str(c) not in common_numeric:
            common_numeric.append(str(c))

with col1:
    # محاولة العثور على عمود التاريخ لجعله الاختيار الافتراضي
    default_x_index = 0
    for i, col in enumerate(common_all):
        if 'اليوم' in col or 'تاريخ' in col or 'date' in col.lower():
            default_x_index = i
            break

    x_axis = st.selectbox("📌 العمود المحوري (X)", common_all, index=default_x_index, key="x_axis_multi")

with col2:
    y_cols = st.multiselect(
        "📊 الأعمدة المراد عرضها (Y)",
        common_numeric,
        default=common_numeric[:3] if len(common_numeric) >= 3 else common_numeric,
        key="y_cols_multi"
    )

# ─────────────────────────────────────────────────────────────
# 3. اختيار الأعوام
# ─────────────────────────────────────────────────────────────
st.markdown("**👁️ اختر الأعوام لعرضها:**")
year_cols = st.columns(len(available_years))
visible_years = []

for i, y in enumerate(available_years):
    with year_cols[i]:
        valid_rows = len(years_data[y].dropna(how='all')) 
        has_data = valid_rows > 0
        if st.checkbox(f"{y} ({valid_rows} صف)", value=has_data, key=f"show_year_{y}"):
            visible_years.append(y)

# ─────────────────────────────────────────────────────────────
# 4. إعدادات المحاور
# ─────────────────────────────────────────────────────────────
with st.expander("⚙️ إعدادات توضيح المحاور (Axes Settings)"):
    ax_col1, ax_col2 = st.columns(2)
    with ax_col1:
        custom_x_title = st.text_input("عنوان محور X", value="", placeholder="مثال: التاريخ")
    with ax_col2:
        custom_y_title = st.text_input("عنوان محور Y", value="القيمة", placeholder="مثال: الكمية (م³)")
    st.markdown("---")
    f_col1, f_col2, f_col3 = st.columns(3)
    with f_col1: tick_font = st.slider("حجم أرقام المحاور", 10, 24, 14)
    with f_col2: title_font = st.slider("حجم عناوين المحاور", 12, 28, 18)
    with f_col3: show_grid = st.checkbox("إظهار الشبكة", value=True)

if not y_cols:
    st.info("👆 اختر عمودًا واحدًا على الأقل للرسم.")
    back_to_home_button()
    st.stop()

if not visible_years:
    st.warning("⚠️ لم تختر أي عام للعرض.")
    back_to_home_button()
    st.stop()

# ─────────────────────────────────────────────────────────────
# 5. الرسم البياني
# ─────────────────────────────────────────────────────────────
st.markdown("---")
COLORS = ['#00008B', '#221E2A', "#114E5C", "#0E1A14", "#C0960E", '#DDA0DD', "#3E665C", '#F7DC6F']

y_min_global, y_max_global = float('inf'), float('-inf')
for y in visible_years:
    for col in y_cols:
        if col in years_data[y].columns and not years_data[y][col].dropna().empty:
            y_min_global = min(y_min_global, years_data[y][col].min())
            y_max_global = max(y_max_global, years_data[y][col].max())

final_x_title = custom_x_title if custom_x_title.strip() else x_axis
final_y_title = custom_y_title if custom_y_title.strip() else "القيمة"

for y in visible_years:
    df = years_data[y]
    if df[y_cols].dropna(how='all').empty: continue
        
    st.markdown(
    f"<h2 style='font-size: 32px; color: {'#2ca02c' if y == available_years[0] else '#00008B'}; margin-bottom: 10px;'>"
    f"{'🟢' if y == available_years[0] else '🔵'} {y}"
    f"</h2>", 
    unsafe_allow_html=True
     )
    fig = go.Figure()
    
    for i, col in enumerate(y_cols):
        if col not in df.columns: continue
        color = COLORS[i % len(COLORS)]
        fig.add_trace(go.Scatter(
            x=df[x_axis] if x_axis in df.columns else df.index,
            y=df[col], mode='lines+markers', name=f"{col} ({y})",
            line=dict(color=color, width=2.5), marker=dict(size=5, color=color),
            connectgaps=False
        ))
        
    fig.update_layout(
        height=400, hovermode='x unified',
        xaxis_title=dict(text=final_x_title, font=dict(size=title_font)),
        yaxis_title=dict(text=final_y_title, font=dict(size=title_font)),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        margin=dict(l=10, r=10, t=30, b=10),
        yaxis=dict(range=[y_min_global, y_max_global], showgrid=show_grid, gridcolor='lightgray', zeroline=False, tickfont=dict(size=tick_font)),
        xaxis=dict(showgrid=show_grid, gridcolor='lightgray', tickfont=dict(size=tick_font), showspikes=True, spikemode="across", spikesnap="cursor", spikedash="dot", spikecolor="gray", spikethickness=1)
    )
    try: fig.update_xaxes(type='date')
    except Exception: pass
    st.plotly_chart(fig, width="stretch", key=f"chart_year_{y}")

# ═══════════════════════════════════════════════════════════
# 🏠 زر العودة للرئيسية (أسفل الصفحة)
# ═══════════════════════════════════════════════════════════
st.markdown("---")
col1, col2, col3 = st.columns([1, 2, 1])
with col3:
    if st.button("🏠 العودة للرئيسية", width="stretch", type="primary", key="back_bottom"):
        st.switch_page("app_main.py")