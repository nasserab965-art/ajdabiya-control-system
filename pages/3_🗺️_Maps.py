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

                    # ═══ الصف الثاني: أزرار الخرائط ═══
                    col_map1, col_map2 = st.columns(2)

                    with col_map1:
                        # فتح نقطة البداية في Google Maps
                        first_lat = result_df['Latitude'].iloc[0]
                        first_lon = result_df['Longitude'].iloc[0]
                        maps_url = f"https://www.google.com/maps?q={first_lat},{first_lon}"
                        
                        st.markdown(
                            f'<a href="{maps_url}" target="_blank" style="text-decoration:none;">'
                            '<button style="width:100%; padding:15px; '
                            'background:linear-gradient(135deg, #4285F4 0%, #34A853 100%); '
                            'color:white; border:none; border-radius:8px; '
                            'font-size:20px; font-weight:bold; cursor:pointer; '
                            'box-shadow: 0 4px 10px rgba(66, 133, 244, 0.3);">'
                            '📍 فتح موقع البداية في Google Maps</button></a>',
                            unsafe_allow_html=True
                        )

                    with col_map2:
                        # فتح Google My Maps لعرض كل النقاط
                        mymaps_url = "https://www.google.com/maps/d/u/0/"
                        
                        st.markdown(
                            f'<a href="{mymaps_url}" target="_blank" style="text-decoration:none;">'
                            '<button style="width:100%; padding:15px; '
                            'background:linear-gradient(135deg, #EA4335 0%, #FBBC05 100%); '
                            'color:white; border:none; border-radius:8px; '
                            'font-size:20px; font-weight:bold; cursor:pointer; '
                            'box-shadow: 0 4px 10px rgba(234, 67, 53, 0.3);">'
                            '🗺️ عرض كل النقاط في My Maps</button></a>',
                            unsafe_allow_html=True
                        )

                # ═══ عرض الجدول الكامل ═══
                with st.expander("📊 عرض الجدول الكامل (Excel Style)"):
                    st.dataframe(result_df, width="stretch", height=400)

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
# 🏠
