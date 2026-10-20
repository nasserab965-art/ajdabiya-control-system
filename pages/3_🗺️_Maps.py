"""
🗺️ الخطوط والمحطات
"""
import sys
import os

# هذا السطر يخبر بايثون بالرجوع خطوة واحدة للخلف (إلى المجلد الرئيسي حيث يوجد siggmra_module.py)
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
if parent_dir not in sys.path:
    sys.path.append(parent_dir)

import streamlit as st
import sqlite3
import pandas as pd
import io
import base64
import zipfile
from datetime import datetime

# استيراد الدوال المشتركة من ملف shared.py
from shared import check_login, apply_common_css, back_to_home_button

try:
    import plotly.graph_objects as go
    PLOTLY_AVAILABLE = True
except ImportError:
    PLOTLY_AVAILABLE = False

try:
    import folium
    from streamlit_folium import st_folium
    from pyproj import Transformer
    FOLIUM_AVAILABLE = True
except ImportError:
    FOLIUM_AVAILABLE = False

try:
    import siggmra_module as sgm
    SGM_AVAILABLE = True
except ImportError:
    SGM_AVAILABLE = False

# ═══════════════════════════════════════════════════════════
# 🚀 الإعداد الأولي
# ═══════════════════════════════════════════════════════════
st.set_page_config(page_title="الخطوط والمحطات", page_icon="🗺️", layout="wide")

# تطبيق التنسيقات المشتركة (RTL وغيره)
apply_common_css()

# التحقق من تسجيل الدخول
check_login()

# ═══════════════════════════════════════════════════════════
# 🎨 CSS خاص بالأزرار فقط
# ═══════════════════════════════════════════════════════════
GLOBAL_BUTTON_CSS = """
<style>
    .stButton > button, .stButton > button *, div[data-testid="stButton"] > button, div[data-testid="stButton"] > button * {
        font-size: 25px !important;
        font-weight: bold !important;
    }
    .stButton > button, div[data-testid="stButton"] > button {
        min-height: 50px !important;
        border-radius: 10px !important;
    }
</style>
"""
st.markdown(GLOBAL_BUTTON_CSS, unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════
# 🏠 زر العودة للرئيسية (أعلى الصفحة)
# ═══════════════════════════════════════════════════════════
col1, col2, col3 = st.columns([1, 2, 1])
with col3:
    if st.button("🏠 العودة للرئيسية", width="stretch", type="primary", key="back_top"):
        st.switch_page("app_main.py")

st.markdown("---")

# ═══════════════════════════════════════════════════════════
# ⭐⭐ دالة KMZ ⭐⭐
# ═══════════════════════════════════════════════════════════
def kml_to_kmz_bytes(kml_content: str, doc_name: str = "doc.kml") -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, 'w', zipfile.ZIP_DEFLATED) as zf:
        zf.writestr(doc_name, kml_content.encode('utf-8'))
    return buf.getvalue()

# ═══════════════════════════════════════════════════════════
# 🖨️ دالة فتح نافذة الطباعة
# ═══════════════════════════════════════════════════════════
def open_print_window(df, title, rows_per_column=30):
    total_rows = len(df)
    if total_rows <= rows_per_column:
        num_columns_display = 1
        rows_per_column_actual = total_rows
    else:
        num_columns_display = (total_rows + rows_per_column - 1) // rows_per_column
        rows_per_column_actual = rows_per_column
    
    import re
    clean_title = re.sub(r'[^\w\s\-]', '', title).replace(' ', '_')
    html_parts = []
    
    html_parts.append(f"""
    <!DOCTYPE html><html dir="rtl"><head><meta charset="UTF-8"><title>{title}</title>
    <style>
        body {{ font-family: Arial, sans-serif; padding: 20px; }}
        h1 {{ text-align: center; color: #333; border-bottom: 3px solid #667eea; padding-bottom: 10px; }}
        .print-container {{ display: flex; flex-wrap: wrap; gap: 20px; direction: rtl; }}
        .print-column {{ flex: 1; min-width: 250px; max-width: 350px; border: 1px solid #ddd; border-radius: 8px; padding: 10px; background: #f9f9f9; }}
        table {{ width: 100%; border-collapse: collapse; font-size: 10px; direction: rtl; }}
        th {{ background: #667eea; color: white; padding: 5px; border: 1px solid #ddd; text-align: center; }}
        td {{ padding: 4px; border: 1px solid #ddd; text-align: center; font-size: 9px; }}
        tr:nth-child(even) {{ background: #f2f2f2; }}
        .no-print {{ text-align: center; margin: 20px 0; }}
        .no-print button {{ padding: 12px 30px; background: #667eea; color: white; border: none; border-radius: 8px; font-size: 18px; cursor: pointer; }}
        @media print {{ .no-print {{ display: none !important; }} }}
    </style></head><body>
    <h1>🖨️ {title}</h1>
    <div class="no-print"><button onclick="window.print()">🖨️ طباعة</button></div>
    <hr><div class="print-container">
    """)
    
    for i in range(num_columns_display):
        start_idx = i * rows_per_column_actual
        end_idx = min((i + 1) * rows_per_column_actual, total_rows)
        if start_idx >= total_rows: break
        subset = df.iloc[start_idx:end_idx]
        
        html_parts.append(f'''
            <div class="print-column">
                <h3>📌 {start_idx + 1} - {end_idx}</h3>
                <table><thead><tr><th>م</th>
        ''')
        for col in subset.columns:
            html_parts.append(f"<th>{col}</th>")
        html_parts.append("</tr></thead><tbody>")
        
        for idx, (_, row) in enumerate(subset.iterrows()):
            html_parts.append(f"<tr><td>{start_idx + idx + 1}</td>")
            for col in subset.columns:
                val = str(row[col])[:22].replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
                html_parts.append(f"<td>{val}</td>")
            html_parts.append("</tr>")
        
        html_parts.append("</tbody></table></div>")
    
    html_parts.append("</div></body></html>")
    html_content = ''.join(html_parts)
    html_base64 = base64.b64encode(html_content.encode('utf-8')).decode('utf-8')
    
    st.markdown(f'''
    <div style="text-align: center; padding: 20px; direction: rtl; border: 2px solid #667eea; border-radius: 10px; background: #f8f9ff;">
        <p style="font-size: 18px;">📄 {title}</p>
        <p>📊 إجمالي الصفوف: <strong>{total_rows}</strong></p>
        <a href="data:text/html;base64,{html_base64}" download="{clean_title}.html" 
           style="display: inline-block; padding: 15px 40px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
           color: white; border-radius: 12px; font-size: 20px; text-decoration: none; font-weight: bold;">
            📥 تحميل ملف الطباعة
        </a>
    </div>
    ''', unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════
# 📊 دالة إنشاء رسوم GMRALINES
# ═══════════════════════════════════════════════════════════
def create_gmr_chart(df, x_cols, y_col, title, chart_id, color='#667eea', sort_col=None):
    if not PLOTLY_AVAILABLE:
        st.error("❌ مكتبة Plotly غير مثبتة. الرجاء تشغيل: pip install plotly")
        return
    
    st.markdown(f'<div id="{chart_id}"></div>', unsafe_allow_html=True)
    st.markdown(f"<h4 style='margin: 5px 0;'>📊 {title}</h4>", unsafe_allow_html=True)
    
    try:
        missing_cols = [col for col in x_cols + [y_col] if col not in df.columns]
        if missing_cols:
            st.warning(f"⚠️ الأعمدة التالية غير موجودة: {', '.join(missing_cols)}")
            return
        
        df_clean = df.copy()
        for col in x_cols:
            if col in df_clean.columns:
                df_clean[col] = df_clean[col].astype(str)
        
        df_clean = df_clean.dropna(subset=x_cols + [y_col])
        if df_clean.empty:
            st.warning("⚠️ لا توجد بيانات كافية!")
            return
        
        def _shorten(v, max_len=12):
               s = str(v).strip()
               return s if len(s) <= max_len else s[:max_len] + '…'
        df_clean['X_Axis'] = (
        df_clean[x_cols[0]].astype(str).apply(_shorten) + ' - ' +
        df_clean[x_cols[1]].astype(str).apply(_shorten) + ' - ' +
        df_clean[x_cols[2]].astype(str).apply(_shorten)
        )
        df_clean[y_col] = pd.to_numeric(df_clean[y_col], errors='coerce')
        df_clean = df_clean.dropna(subset=[y_col])
        
        if df_clean.empty:
            st.warning("⚠️ لا توجد قيم رقمية صالحة!")
            return
        
        if len(df_clean) > 500:
            step = max(1, len(df_clean) // 500)
            df_clean = df_clean.iloc[::step]
        
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=df_clean['X_Axis'], y=df_clean[y_col],
            mode='lines+markers', name=y_col,
            line=dict(color=color, width=3),
            marker=dict(size=6, color=color)
        ))
        
        fig.update_layout(
            title=None, xaxis_title='الموقع', yaxis_title='م.ف.م.س.ب',
            hovermode='x unified', height=380,
            plot_bgcolor='rgba(255,255,255,0.95)', paper_bgcolor='rgba(0,0,0,0)',
            margin=dict(l=50, r=20, t=20, b=100)
        )
        fig.update_xaxes(
            showgrid=True, gridcolor='lightgray', tickangle=30,
            tickfont=dict(size=11, color="#0B450E", family="Arial Black, Helvetica, sans-serif"),
            nticks=60, tickmode='auto', ticklabelstep=2, automargin=True,
            showspikes=True, spikemode='across', spikesnap='cursor', spikecolor='gray', spikethickness=1, spikedash='dot',
        )
        fig.update_yaxes(showgrid=True, gridcolor='lightgray', tickfont=dict(size=12))
        
        st.plotly_chart(fig, width="stretch")
        
        with st.expander("📋 عرض البيانات"):
            display_df = df_clean[['X_Axis'] + [y_col]].rename(columns={'X_Axis': 'الموقع'}).reset_index(drop=True)
            display_df.index += 1
            st.dataframe(display_df, width="stretch", height=300)
            
            if st.button(f"🖨️ طباعة - {chart_id}", key=f"print_{chart_id}", width="stretch"):
                open_print_window(display_df, title)
        
        if sort_col is not None:
            with st.expander("📊 عرض مرتب تصاعدياً"):
                sorted_df = df_clean[['X_Axis'] + [y_col]].copy()
                sorted_df[y_col] = pd.to_numeric(sorted_df[y_col], errors='coerce')
                sorted_df = sorted_df.dropna().sort_values(by=y_col, ascending=True)
                sorted_df['الترتيب'] = range(1, len(sorted_df) + 1)
                sorted_df = sorted_df.rename(columns={'X_Axis': 'الموقع', y_col: 'القيمة'})
                sorted_df = sorted_df[['الترتيب', 'الموقع', 'القيمة']].reset_index(drop=True)
                
                st.dataframe(sorted_df, width="stretch", height=300)
                st.info(f"📊 أقل = **{sorted_df['القيمة'].min():.2f}** | أعلى = **{sorted_df['القيمة'].max():.2f}**")
                
                if st.button(f"🖨️ طباعة (مرتب) - {chart_id}", key=f"print_sorted_{chart_id}", width="stretch"):
                    open_print_window(sorted_df, f"{title} - مرتب")
        
        st.download_button(
            label="📥 تحميل الرسم HTML",
            data=fig.to_html(),
            file_name=f"{chart_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html",
            mime="text/html", width="stretch"
        )
        
    except Exception as e:
        st.error(f"❌ خطأ: {e}")
        import traceback
        st.code(traceback.format_exc())

if 'active_line_map' not in st.session_state:
    st.session_state.active_line_map = None

# ═══════════════════════════════════════════════════════════
# 🗺️ صفحة عرض خريطة الخط (ملء الشاشة)
# ═══════════════════════════════════════════════════════════
if st.session_state.active_line_map is not None:
    line_key = st.session_state.active_line_map
    cfg = sgm.LINES_CONFIG[line_key]

    if not FOLIUM_AVAILABLE:
        st.error("❌ مكتبات الخرائط (folium / streamlit-folium) غير مثبتة. الرجاء إضافتها إلى requirements.txt وإعادة التشغيل.")
        st.stop()

    st.markdown("""
    <style>
        section[data-testid="stSidebar"] { display: none !important; }
        header[data-testid="stHeader"] { display: none !important; }
        [data-testid="stToolbar"] { display: none !important; }
        [data-testid="collapsedControl"] { display: none !important; }
        footer { display: none !important; }
        .block-container {
            padding: 1rem !important;
            max-width: 100vw !important;
        }
    </style>
    """, unsafe_allow_html=True)

    col_top1, col_top2 = st.columns([4, 1])
    with col_top1:
        st.markdown(f"""
        <h2 style="color: #1A5276; margin: 0;">
            🗺️ خريطة {line_key} — {cfg['name']}
        </h2>
        """, unsafe_allow_html=True)
    with col_top2:
        if st.button("⬅️ رجوع", width='stretch', type="primary", key="back_from_line_map"):
            st.session_state.active_line_map = None
            st.rerun()

    st.markdown("---")

    with st.spinner(f"⏳ جاري تحميل نقاط {line_key}..."):
        try:
            result_df = sgm.project_line_points(
                line_key=line_key,
                allines_path="ALLINES.xlsx"
            )

            if result_df.empty:
                st.warning(f"⚠️ لا توجد نقاط للخط {line_key}")
            else:
                col_i1, col_i2, col_i3, col_i4 = st.columns(4)
                with col_i1:
                    st.metric("عدد النقاط", len(result_df))
                with col_i2:
                    st.metric("أول محطة", str(result_df['Station'].iloc[0]))
                with col_i3:
                    st.metric("آخر محطة", str(result_df['Station'].iloc[-1]))
                with col_i4:
                    st.metric("طول الخط",
                              f"{result_df['Distance_m'].max()/1000:.1f} كم")

                st.markdown("---")

                st.markdown("### ⚙️ خيارات التصدير")

                col_f1, col_f2 = st.columns([2, 1])
                with col_f1:
                    all_types = sorted(
                        result_df['Type'].astype(str).str.upper()
                        .str.extract(r'(AV|MH|PW|BO|TO|VA|TEE|FM|BV)')[0]
                        .dropna().unique().tolist()
                    )
                    selected_types = st.multiselect(
                        "🎯 اختر الأنواع للتصدير (اترك فارغاً = الكل):",
                        options=all_types,
                        default=[],
                        key=f"filter_types_{line_key}",
                        help="مثلاً: اختر MH فقط لعرض غرف التفتيش"
                    )

                with col_f2:
                    add_start_end = st.checkbox(
                        "⭐ إضافة نقاط البداية/النهاية",
                        value=True,
                        key=f"add_se_{line_key}"
                    )

                filter_types = selected_types if selected_types else None

                lat_min = result_df['Latitude'].min()
                lat_max = result_df['Latitude'].max()
                lon_min = result_df['Longitude'].min()
                lon_max = result_df['Longitude'].max()

                center_lat = (lat_min + lat_max) / 2
                center_lon = (lon_min + lon_max) / 2

                m = folium.Map(
                    location=[center_lat, center_lon],
                    zoom_start=8,
                    tiles='OpenStreetMap',
                    prefer_canvas=True
                )

                m.fit_bounds([
                    [lat_min - 0.05, lon_min - 0.05],
                    [lat_max + 0.05, lon_max + 0.05]
                ])

                try:
                    line_geom = sgm.load_line_from_kml(
                        cfg["kml_file"],
                        reverse=cfg.get("reverse_kml", False)
                    )
                    line_geom_simple = line_geom.simplify(0.001)

                    t_wgs = sgm.Transformer.from_crs(
                        "EPSG:32634", "EPSG:4326", always_xy=True
                    )
                    line_coords = [
                        t_wgs.transform(x, y)
                        for x, y in line_geom_simple.coords
                    ]

                    folium.PolyLine(
                        locations=[(lat, lon) for lon, lat in line_coords],
                        color=cfg.get('color', '#00008B'),
                        weight=4,
                        opacity=0.8,
                        tooltip=f"مسار {line_key}"
                    ).add_to(m)

                    if line_coords:
                        start_lon, start_lat = line_coords[0]
                        end_lon, end_lat = line_coords[-1]

                        folium.Marker(
                            [start_lat, start_lon],
                            popup=f"🟢 بداية {line_key}",
                            icon=folium.Icon(color='green', icon='play')
                        ).add_to(m)

                        folium.Marker(
                            [end_lat, end_lon],
                            popup=f"🔴 نهاية {line_key}",
                            icon=folium.Icon(color='red', icon='stop')
                        ).add_to(m)
                except Exception as e:
                    st.warning(f"⚠️ لم يتم رسم المسار: {e}")

                if len(result_df) > 0:
                    df_sorted = result_df.sort_values('Station_m').reset_index(drop=True)
                    first = df_sorted.iloc[0]
                    last = df_sorted.iloc[-1]

                    folium.Marker(
                        location=[first['Latitude'], first['Longitude']],
                        popup=folium.Popup(
                            f"<b>🟢 بداية {line_key}</b><br>"
                            f"المحطة: {first['Station']}<br>"
                            f"النوع: {first['Type']}<br>"
                            f"الموقع: {first['Distance_m']/1000:.3f} كم",
                            max_width=250
                        ),
                        tooltip=f"🟢 بداية — {first['Station']}",
                        icon=folium.Icon(color='green', icon='play', prefix='fa')
                    ).add_to(m)

                    folium.Marker(
                        location=[last['Latitude'], last['Longitude']],
                        popup=folium.Popup(
                            f"<b>🔴 نهاية {line_key}</b><br>"
                            f"المحطة: {last['Station']}<br>"
                            f"النوع: {last['Type']}<br>"
                            f"الموقع: {last['Distance_m']/1000:.3f} كم",
                            max_width=250
                        ),
                        tooltip=f"🔴 نهاية — {last['Station']}",
                        icon=folium.Icon(color='red', icon='stop', prefix='fa')
                    ).add_to(m)

                folium.LayerControl().add_to(m)

                st_folium(
                    m,
                    width=None,
                    height=650,
                    key=f"full_map_{line_key}",
                    returned_objects=[]
                )

                st.markdown("---")

                kml_content = sgm.build_kml_enhanced(
                    result_df,
                    line_key,
                    include_path=True,
                    filter_types=filter_types,
                    add_start_end=add_start_end
                )

                if kml_content is None:
                    st.warning("⚠️ لا توجد نقاط بعد التصفية — عدّل الفلتر")
                else:
                    # ═══ الصف الأول: أزرار التحميل ═══
                    col_dl1, col_dl2, col_dl3 = st.columns(3)

                    with col_dl1:
                        st.download_button(
                            "📥 تنزيل KML",
                            data=kml_content.encode('utf-8'),
                            file_name=f"{line_key}_full.kml",
                            mime="application/vnd.google-earth.kml+xml",
                            key=f"dl_kml_{line_key}",
                            width="stretch"
                        )

                    with col_dl2:
                        kmz_bytes = kml_to_kmz_bytes(
                            kml_content,
                            doc_name=f"{line_key}.kml"
                        )
                        st.download_button(
                            "📦 تنزيل KMZ (موصى به)",
                            data=kmz_bytes,
                            file_name=f"{line_key}_full.kmz",
                            mime="application/vnd.google-earth.kmz",
                            key=f"dl_kmz_{line_key}",
                            width="stretch"
                        )

                    with col_dl3:
                        output = io.BytesIO()
                        with pd.ExcelWriter(output, engine='openpyxl') as w:
                            result_df.to_excel(w, index=False)
                        st.download_button(
                            "📥 تنزيل Excel",
                            data=output.getvalue(),
                            file_name=f"{line_key}_points.xlsx",
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                            key=f"dl_xlsx_{line_key}",
                            width="stretch"
                        )

                    st.markdown("<div style='margin-top: 10px;'></div>", unsafe_allow_html=True)

                    # ═══ الصف الثاني: زر Google Earth (بعرض كامل) ═══
                    st.markdown("<div style='margin-top: 10px;'></div>", unsafe_allow_html=True)
                    
                    earth_url = "https://earth.google.com/web/"
                    
                    st.markdown(
                        f'<a href="{earth_url}" target="_blank" style="text-decoration:none;">'
                        '<button style="width:100%; padding:15px; '
                        'background:linear-gradient(135deg, #0F9D58 0%, #34A853 100%); '
                        'color:white; border:none; border-radius:8px; '
                        'font-size:22px; font-weight:bold; cursor:pointer; '
                        'box-shadow: 0 4px 10px rgba(15, 157, 88, 0.3);">'
                        '🌍 فتح Google Earth</button></a>',
                        unsafe_allow_html=True
                    )

                # ═══ مسافة للفصل بين الزر والجدول ═══
                st.markdown("<div style='margin-top: 25px;'></div>", unsafe_allow_html=True)

                # ═══ عرض الجدول الكامل ═══
                with st.expander("📊 عرض الجدول الكامل (Excel Style)"):
                    st.dataframe(result_df, width="stretch", height=400)
                    
                # ═══ مسافة في نهاية الصفحة ═══
                st.markdown("<div style='margin-bottom: 30px;'></div>", unsafe_allow_html=True)

        except FileNotFoundError as e:
            st.error(f"❌ ملف غير موجود: {e}")
            st.info(f"💡 تأكد من وجود `{cfg['kml_file']}` في مجلد التطبيق")
        except Exception as e:
            st.error(f"❌ خطأ: {e}")
            import traceback
            st.code(traceback.format_exc())

    st.stop()


# ═══════════════════════════════════════════════════════════
# 🏠 الصفحة الرئيسية
# ═══════════════════════════════════════════════════════════
st.title("🗺️ الخطوط والمحطات وخرائط Google")
st.markdown("---")

# ═══════════════════════════════════════════════════════════
# 📊 تحميل بيانات GMRALINES
# ═══════════════════════════════════════════════════════════
st.header("📊 بيانات GMRALINES")


@st.cache_data
def load_gmr():
    try:
        conn = sqlite3.connect('app_data.db')
        df = pd.read_sql_query("SELECT * FROM gmr_lines", conn)
        conn.close()
        return None if df.empty else df
    except Exception:
        return None


df_gmr = load_gmr()
if df_gmr is not None:
    st.success(f"✅ تم تحميل {len(df_gmr)} صف")
else:
    st.warning("⚠️ لا توجد بيانات GMRALINES")

st.markdown("---")


# ═══════════════════════════════════════════════════════════
# 🗺️📊 خرائط الخطوط + رسوم GMRALINES (مدمجة)
# ═══════════════════════════════════════════════════════════
st.header("🗺️📊 خرائط الخطوط ورسوم GMRALINES")

LINE_TO_CHART = {
    'SSSA': {
        'x_cols': ['B', 'C', 'D'],
        'y_col': 'E',
        'title': 'منظومة السرير / سرت (S/S) - مقطع السرير / اجدابيا (S/A)',
        'color': '#00008B',
        'sort_col': 'E',
    },
    'SSAS': {
        'x_cols': ['H', 'I', 'J'],
        'y_col': 'K',
        'title': 'منظومة السرير / سرت (S/S) - مقطع اجدابيا / سرت (A/S)',
        'color': '#114E5C',
        'sort_col': 'K',
    },
    'TBSA': {
        'x_cols': ['N', 'O', 'P'],
        'y_col': 'Q',
        'title': 'منظومة تازربو / بنغازى (T/B) - مقطع السرير / اجدابيا (S/A)',
        'color': '#C0960E',
        'sort_col': 'Q',
    },
    'TBAB': {
        'x_cols': ['T', 'U', 'V'],
        'y_col': 'W',
        'title': 'منظومة تازربو / بنغازى (T/B) - مقطع اجدابيا / بنغازى (A/B)',
        'color': '#DDA0DD',
        'sort_col': 'W',
    },
}

if not SGM_AVAILABLE:
    st.error("❌ وحدة siggmra_module غير متوفرة — تحقق من وجود الملف")
else:
    lines_list = list(sgm.LINES_CONFIG.items())

    for line_key, cfg in lines_list:
        chart_cfg = LINE_TO_CHART.get(line_key)

        col_left, col_right = st.columns([1, 4], gap="medium")

        # ═══ العمود الأيسر: زر العرض فقط ═══
        with col_left:
            st.markdown("<div style='margin-top: 35px;'></div>", unsafe_allow_html=True)
            if st.button(
                f"🗺️ عرض {line_key}",
                key=f"merged_show_map_{line_key}",
                use_container_width=True,
                type="primary"
            ):
                st.session_state.active_line_map = line_key
                st.rerun()

        # ═══ العمود الأيمن: الرسم البياني ═══
        with col_right:
            if df_gmr is not None and chart_cfg is not None:
                create_gmr_chart(
                    df_gmr,
                    x_cols=chart_cfg['x_cols'],
                    y_col=chart_cfg['y_col'],
                    title=chart_cfg['title'],
                    chart_id=f"gmr_chart_{line_key}",
                    color=chart_cfg['color'],
                    sort_col=chart_cfg['sort_col'],
                )
            elif df_gmr is None:
                st.warning("⚠️ لا توجد بيانات GMRALINES")

        st.markdown("---")
        
# ═══════════════════════════════════════════════════════════
# 📍 مواقع غرف التحكم
# ═══════════════════════════════════════════════════════════
st.header("📍 مواقع غرف التحكم - Google Maps")

locations = {
    "خزان التجميع و الموازنة اجدابيا": (30.582070, 20.349818),
    "خزان سرت النهائى": (31.163098, 16.681146),
    "خزان بنغازى النهائى": (31.729474, 20.266646),
    "حقل آبار السرير": (27.591483, 21.601081),
    "حقل آبار تازربو": (25.553332, 21.606476),
}

locations_list = list(locations.items())
cols_per_row = 3

for i in range(0, len(locations_list), cols_per_row):
    row_items = locations_list[i:i + cols_per_row]
    cols = st.columns(cols_per_row)
    for col, (name, (lat, lon)) in zip(cols, row_items):
        url = f"https://www.google.com/maps?q={lat},{lon}"
        with col:
            st.markdown(f"""
            <a href="{url}" target="_blank" style="text-decoration:none; display:block;">
                <button style="width:100%; padding:14px 10px;
                    background:linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
                    color:white; border:none; border-radius:12px;
                    font-size:30px; font-weight:bold; cursor:pointer;
                    box-shadow:0 4px 12px rgba(245,87,108,0.4); text-align:center;
                    min-height:70px; line-height:1.4;">
                    <span style="font-size:16px;">📍</span> {name}
                    <span style="font-size:12px; opacity:0.9; display:block; margin-top:4px;">
                        ({lat:.4f}, {lon:.4f})
                    </span>
                </button>
            </a>
            """, unsafe_allow_html=True)

st.markdown("---")       

# ═══════════════════════════════════════════════════════════
# 🖼️ زر الانتقال لمعرض الصور
# ═══════════════════════════════════════════════════════════
st.markdown("---")
col1, col2, col3 = st.columns([1, 2, 1])
with col2:
    if st.button("🖼️ الذهاب إلى معرض الصور", width="stretch", type="primary", key="go_to_album"):
        st.switch_page("pages/4_🖼️_Album.py")

# ═══════════════════════════════════════════════════════════
# 🏠 زر العودة للرئيسية (أسفل الصفحة)
# ═══════════════════════════════════════════════════════════
st.markdown("---")
col1, col2, col3 = st.columns([1, 2, 1])
with col3:
    if st.button("🏠 العودة للرئيسية", width="stretch", type="primary", key="back_bottom"):
        st.switch_page("app_main.py")
