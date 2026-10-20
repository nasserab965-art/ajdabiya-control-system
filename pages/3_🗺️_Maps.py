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
