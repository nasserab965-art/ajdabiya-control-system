"""
الصفحة 2: أرشيف القراءات 2030 → 2025
"""
import streamlit as st
import os
import sys
import pandas as pd
import sqlite3
import plotly.graph_objects as go
import time
import io
from datetime import datetime

# حماية الصفحة
if 'user_level' not in st.session_state or st.session_state.user_level == 0:
    st.error("⛔ غير مصرح لك بالدخول. يرجى تسجيل الدخول أولاً.")
    st.stop()

# صلاحية الأرشيف (مثلاً: 1, 2, 4 فقط)
if st.session_state.user_level not in [1, 2, 4]:
    st.error("⛔ عذراً، حسابك لا يملك الصلاحية لعرض هذه الصفحة.")
    st.stop()
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from shared import check_login, apply_common_css, back_to_home_button, load_table

st.set_page_config(page_title="أرشيف القراءات", page_icon="📈", layout="wide")

# ═══════════════════════════════════════════════════════════
# 🏠 زر العودة للرئيسية (أعلى الصفحة)
# ═══════════════════════════════════════════════════════════
col1, col2, col3 = st.columns([1, 2, 1])
with col3:
    if st.button("🏠 العودة للرئيسية", use_container_width=True, type="primary", key="back_top"):
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
    h3 { font-size: 1.6rem !important; font-weight: bold !important; }
    div[data-baseweb="select"] > div { font-size: 18px !important; }
    .stCheckbox label span { font-size: 18px !important; font-weight: bold !important; }
    [data-testid="stSidebar"] h3 { font-size: 1.4rem !important; }
    button p { font-size: 16px !important; }
    .block-container { padding-left: 2rem !important; padding-right: 2rem !important; max-width: 95% !important; }

    /* ⬇️ تكبير أيقونات شريط أدوات Plotly (Modebar) ⬇️ */
    .modebar-container .modebar-btn svg {
        width: 26px !important;
        height: 26px !important;
    }
    .modebar-container .modebar-btn {
        padding: 6px !important;
    }
    .modebar-group {
        padding: 4px !important;
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
        
        df.columns = [str(c).strip() for c in df.columns]
        df = df.dropna(how='all').reset_index(drop=True)

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

def df_to_excel_bytes(sheets: dict) -> bytes:
    """تحويل قاموس {اسم_الورقة: DataFrame} إلى ملف Excel في الذاكرة."""
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        for sheet_name, sheet_df in sheets.items():
            sheet_df.to_excel(writer, sheet_name=str(sheet_name)[:31], index=False)
    buffer.seek(0)
    return buffer.getvalue()

def format_date_column(df, col_name):
    """تحويل العمود إلى تاريخ فقط بدون وقت إن كان datetime."""
    if col_name in df.columns:
        try:
            df[col_name] = pd.to_datetime(df[col_name], errors="coerce").dt.date
        except Exception:
            pass
    return df

# ─────────────────────────────────────────────────────────────
# الشريط الجانبي
# ─────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### ⚙️ إدارة البيانات")
    
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
# 2. التحكم بالأعمدة
# ─────────────────────────────────────────────────────────────
st.markdown("---")
col1, col2 = st.columns([1, 3])

reference_year = available_years[0]
ref_df = years_data[reference_year]

common_all = [str(c) for c in ref_df.columns]
for y in available_years:
    for c in years_data[y].columns:
        if str(c) not in common_all:
            common_all.append(str(c))

ref_numeric = [str(c) for c in ref_df.select_dtypes(include=['number']).columns]
common_numeric = list(ref_numeric)

for y in available_years:
    for c in years_data[y].select_dtypes(include=['number']).columns:
        if str(c) not in common_numeric:
            common_numeric.append(str(c))

with col1:
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

current_year = datetime.now().year
default_selected_year = current_year if current_year in available_years else available_years[0]

for i, y in enumerate(available_years):
    with year_cols[i]:
        valid_rows = len(years_data[y].dropna(how='all')) 
        is_checked = (y == default_selected_year)
        
        if st.checkbox(f"{y} ({valid_rows} صف)", value=is_checked, key=f"show_year_{y}"):
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
    st.markdown("**تخصيص نطاق المحور Y (اختياري):**")
    range_col1, range_col2 = st.columns(2)
    
    y_min_global, y_max_global = float('inf'), float('-inf')
    for y in visible_years:
        for col in y_cols:
            if col in years_data[y].columns and not years_data[y][col].dropna().empty:
                y_min_global = min(y_min_global, years_data[y][col].min())
                y_max_global = max(y_max_global, years_data[y][col].max())
    
    if y_min_global == float('inf'): y_min_global = 0
    if y_max_global == float('-inf'): y_max_global = 100

    with range_col1:
        y_min_custom = st.number_input("الحد الأدنى للمحور Y", value=float(y_min_global), format="%.2f")
    with range_col2:
        y_max_custom = st.number_input("الحد الأعلى للمحور Y", value=float(y_max_global), format="%.2f")

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
COLORS = ['#1f77b4', '#2ca02c', '#ff7f0e', '#9467bd', '#d62728', '#17becf', '#e377c2', '#8c564b']

final_x_title = custom_x_title if custom_x_title.strip() else x_axis
final_y_title = custom_y_title if custom_y_title.strip() else "القيمة"

for y in visible_years:
    df = years_data[y]
    if df[y_cols].dropna(how='all').empty: continue
        
    st.markdown(
    f"<h2 style='font-size: 28px; color: {'#2ca02c' if y == default_selected_year else '#1f77b4'}; margin-bottom: 15px; text-shadow: 1px 1px 2px rgba(0,0,0,0.1);'>"
    f"{'🟢' if y == default_selected_year else '🔵'} {y}"
    f"</h2>", 
    unsafe_allow_html=True
     )
    
    fig = go.Figure()
    
    for i, col in enumerate(y_cols):
        if col not in df.columns: continue
        color = COLORS[i % len(COLORS)]
        
        fig.add_trace(go.Scatter(
            x=df[x_axis] if x_axis in df.columns else df.index,
            y=df[col], 
            mode='lines+markers', 
            name=f"{col} ({y})",
            line=dict(color=color, width=3, shape='spline'),
            marker=dict(size=7, color=color, line=dict(width=1, color='white')),
            fill='tozeroy',
            fillcolor=f'rgba({int(color[1:3], 16)}, {int(color[3:5], 16)}, {int(color[5:7], 16)}, 0.1)',
            connectgaps=False,
            hovertemplate="<b>%{y:,.2f}</b><br>%{x}<extra></extra>"
        ))
        
    fig.update_layout(
        height=450, 
        hovermode='x unified',
        plot_bgcolor='rgba(250,250,252,1)', 
        paper_bgcolor='rgba(255,255,255,1)',
        xaxis_title=dict(text=final_x_title, font=dict(size=title_font, color='#333')),
        yaxis_title=dict(text=final_y_title, font=dict(size=title_font, color='#333')),
        legend=dict(
            orientation="h", yanchor="bottom", y=1.05, xanchor="center", x=0.5, 
            bgcolor='rgba(255,255,255,0.8)', bordercolor='rgba(0,0,0,0.1)', borderwidth=1
        ),
        margin=dict(l=20, r=20, t=50, b=20),
        
        yaxis=dict(
            range=[y_min_custom, y_max_custom],
            showgrid=show_grid, 
            gridcolor='rgba(0,0,0,0.08)',
            gridwidth=1,
            griddash='dot',
            zeroline=True,
            zerolinecolor='rgba(0,0,0,0.2)',
            zerolinewidth=2,
            tickfont=dict(size=tick_font, color='#444'),
            tickformat=',.0f', 
            title_font=dict(size=title_font, color='#333'),
            showline=True,
            linewidth=2,
            linecolor='rgba(0,0,0,0.2)'
        ),
        xaxis=dict(
            showgrid=show_grid, 
            gridcolor='rgba(0,0,0,0.08)', 
            gridwidth=1,
            griddash='dot',
            tickfont=dict(size=tick_font, color='#444'), 
            showspikes=True, spikemode="across", spikesnap="cursor", spikedash="dot", spikecolor="gray", spikethickness=1,
            showline=True,
            linewidth=2,
            linecolor='rgba(0,0,0,0.2)'
        ),
        hoverlabel=dict(bgcolor="white", font_size=14, font_family="Arial")
    )
    
    try: 
        fig.update_xaxes(type='date')
    except Exception: 
        pass
        
    st.plotly_chart(
        fig, 
        use_container_width=True, 
        key=f"chart_year_{y}",
        config={'displayModeBar': True, 'toImageButtonOptions': {'format': 'png', 'filename': f'Archive_{y}', 'scale': 2}}
    )

# ═══════════════════════════════════════════════════════════
# 📋 جدول القراءات المختارة + تحميل CSV/Excel (أسفل الصفحة)
# ═══════════════════════════════════════════════════════════
st.markdown("---")
st.markdown("## 📋 جدول القراءات المختارة")

table_mode = st.radio(
    "طريقة العرض:",
    ["جدول مدمج (مقارنة الأعوام جنبًا إلى جنب)", "جدول منفصل لكل عام"],
    horizontal=True,
    key="table_mode"
)

if table_mode.startswith("جدول مدمج"):
    merged = None
    for y in visible_years:
        df = years_data[y]
        cols_present = [c for c in y_cols if c in df.columns]
        if not cols_present:
            continue
        x_vals = df[x_axis] if x_axis in df.columns else df.index
        temp = df[cols_present].copy()
        temp.insert(0, final_x_title, x_vals)
        temp = temp.rename(columns={c: f"{c} ({y})" for c in cols_present})
        
        if merged is None:
            merged = temp
        else:
            merged = pd.merge(merged, temp, on=final_x_title, how="outer")

    if merged is not None and not merged.empty:
        merged = merged.sort_values(final_x_title).reset_index(drop=True)
        merged = format_date_column(merged, final_x_title)  # إزالة الساعة من التاريخ

        st.dataframe(
            merged,
            use_container_width=True,
            height=min(600, 40 + 35 * len(merged)),
            hide_index=True
        )
        st.caption(
            f"عدد الصفوف: {len(merged)} | الأعوام: {', '.join(map(str, visible_years))} "
            f"| الأعمدة: {', '.join(y_cols)}"
        )

        # أزرار التحميل
        dl_col1, dl_col2, _ = st.columns([1, 1, 2])
        with dl_col1:
            st.download_button(
                "⬇️ تحميل CSV",
                data=merged.to_csv(index=False).encode("utf-8-sig"),
                file_name=f"archive_readings_{datetime.now():%Y%m%d_%H%M}.csv",
                mime="text/csv",
                use_container_width=True,
                key="dl_csv_merged"
            )
        with dl_col2:
            st.download_button(
                "⬇️ تحميل Excel",
                data=df_to_excel_bytes({f"Archive_{datetime.now():%Y%m%d}": merged}),
                file_name=f"archive_readings_{datetime.now():%Y%m%d_%H%M}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True,
                key="dl_xlsx_merged"
            )
    else:
        st.info("لا توجد بيانات لعرضها في الجدول.")

else:
    # وضع "جدول منفصل لكل عام"
    export_sheets = {}
    any_table = False

    for y in visible_years:
        df = years_data[y]
        cols_present = [c for c in y_cols if c in df.columns]
        if not cols_present:
            continue

        if x_axis in df.columns:
            show_df = df[[x_axis] + cols_present].copy()
        else:
            show_df = df[cols_present].copy()
            
        show_df = show_df.dropna(how="all", subset=cols_present)

        if show_df.empty:
            continue
            
        show_df = format_date_column(show_df, x_axis)  # إزالة الساعة من التاريخ

        any_table = True
        export_sheets[str(y)] = show_df

        st.markdown(f"### 🔵 {y} — {len(show_df)} صف")
        st.dataframe(
            show_df,
            use_container_width=True,
            height=min(400, 40 + 35 * len(show_df)),
            hide_index=True
        )

    if any_table:
        # أزرار التحميل
        dl_col1, dl_col2, _ = st.columns([1, 1, 2])
        with dl_col1:
            first_year = list(export_sheets.keys())[0]
            st.download_button(
                f"⬇️ تحميل CSV ({first_year})",
                data=export_sheets[first_year].to_csv(index=False).encode("utf-8-sig"),
                file_name=f"archive_{first_year}_{datetime.now():%Y%m%d_%H%M}.csv",
                mime="text/csv",
                use_container_width=True,
                key="dl_csv_separate"
            )
        with dl_col2:
            st.download_button(
                "⬇️ تحميل Excel (كل الأعوام)",
                data=df_to_excel_bytes(export_sheets),
                file_name=f"archive_readings_{datetime.now():%Y%m%d_%H%M}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True,
                key="dl_xlsx_separate"
            )
    else:
        st.info("لا توجد بيانات لعرضها في الجداول.")

# ═══════════════════════════════════════════════════════════
# 🏠 زر العودة للرئيسية (أسفل الصفحة)
# ═══════════════════════════════════════════════════════════
st.markdown("---")
col1, col2, col3 = st.columns([1, 2, 1])
with col3:
    if st.button("🏠 العودة للرئيسية", use_container_width=True, type="primary", key="back_bottom"):
        st.switch_page("app_main.py")
