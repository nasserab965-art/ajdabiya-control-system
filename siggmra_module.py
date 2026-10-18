# -*- coding: utf-8 -*-
"""
وحدة إسقاط نقاط خطوط الأنابيب على خرائط KML
مع دعم المعايرة المستقلة لكل خط
+ دمج المسار والنقاط في ملف KML واحد
+ أيقونات مخصصة حسب النوع
+ نقاط بداية/نهاية بارزة
+ تصفية حسب النوع

⚠️ قاعدة ثابتة:
   - كل الخطوط الأربعة تبدأ من الجنوب وتنتهي شمالاً.
   - الترقيم من الأصغر (009+xxx) إلى الأكبر (391+xxx).
   - SSAS فقط هو الذي يحتاج قلباً (reverse_kml = True).
"""

import pandas as pd
import xml.etree.ElementTree as ET
from shapely.geometry import LineString
from pyproj import Transformer
import re

# ============================================================
# 1. إعدادات الخطوط الأربعة
# ============================================================
LINES_CONFIG = {
    "SSSA": {
        "name": "مقطع السرير - اجدابيا (S/A) S/S",
        "kml_file": "KML_FILES/SSSA_LINE.kml",
        "station_col": 0,
        "type_col": 1,
        "color": "#00008B",
        "start_station": 10076,
        "end_station": 391243,
        "calibration_station": None,
        "calibration_offset_m": 0,
        "offset_type": "constant",
        "reverse_kml": True,
    },
    "SSAS": {
        "name": "مقطع اجدابيا - سرت (A/S) S/S",
        "kml_file": "KML_FILES/SSAS_LINE.kml",
        "station_col": 2,
        "type_col": 3,
        "color": "#114E5C",
        "start_station": 9710,
        "end_station": 402427,
        "calibration_station": None,
        "calibration_offset_m": 0,
        "offset_type": "constant",
        "reverse_kml": False,
    },
    "TBSA": {
        "name": "مقطع السرير - اجدابيا (S/A) T/B",
        "kml_file": "KML_FILES/TBSA_LINE.kml",
        "station_col": 4,
        "type_col": 5,
        "color": "#C0960E",
        "start_station": 9838,
        "end_station": 391243,
        "calibration_station": None,
        "calibration_offset_m": 0,
        "offset_type": "constant",
        "reverse_kml": True,
    },
    "TBAB": {
        "name": "مقطع اجدابيا - بنغازي (A/B) T/B",
        "kml_file": "KML_FILES/TBAB_LINE.kml",
        "station_col": 6,
        "type_col": 7,
        "color": "#DDA0DD",
        "start_station": 9713,
        "end_station": 150386,
        "calibration_station": 25801,
        "calibration_offset_m": 184,
        "offset_type": "linear_decreasing",
        "reverse_kml": False,
    },
}


# ============================================================
# 2. تحويل أرقام المحطات إلى متر
# ============================================================
def station_to_meters(s):
    """تحويل أي صيغة محطة إلى متر"""
    if pd.isna(s):
        return None

    s = str(s).strip()

    if any(kw in s.lower() for kw in
           ['invert', 'shaft', 'standard', '*', 'sop buried']):
        return None

    s = re.sub(r'\++', '+', s)

    if re.fullmatch(r'\d{6}', s):
        return float(s[:3]) * 1000 + float(s[3:])

    if '+' in s:
        try:
            parts = s.split('+')
            if len(parts) == 2 and parts[0] and parts[1]:
                return float(parts[0]) * 1000 + float(parts[1])
        except:
            return None

    try:
        val = float(s)
        if 100 < val < 500_000:
            return val
        return None
    except:
        return None


# ============================================================
# 3. استخراج نقاط خط محدد من ALLINES.xlsx
# ============================================================
def extract_line_points(line_key, allines_path="ALLINES.xlsx"):
    """يستخرج نقاط خط محدد — مرتبة تصاعدياً (من الأصغر إلى الأكبر)"""
    if line_key not in LINES_CONFIG:
        raise ValueError(f"خط غير معروف: {line_key}")

    cfg = LINES_CONFIG[line_key]
    st_idx = cfg["station_col"]
    tp_idx = cfg["type_col"]

    df_raw = pd.read_excel(allines_path, sheet_name="Sheet1", header=None)

    if st_idx >= len(df_raw.columns) or tp_idx >= len(df_raw.columns):
        raise ValueError(f"أعمدة غير موجودة للخط {line_key}")

    sub = df_raw.iloc[:, [st_idx, tp_idx]].copy()
    sub.columns = ['الرقم', 'النوع']

    sub = sub.dropna(subset=['الرقم'])
    sub = sub[sub['الرقم'].astype(str).str.strip() != '']

    sub['الخط'] = line_key
    sub['اسم_الخط'] = cfg['name']
    sub['station_m'] = sub['الرقم'].apply(station_to_meters)
    sub = sub.dropna(subset=['station_m']).reset_index(drop=True)

    sub = sub.sort_values('station_m').reset_index(drop=True)

    return sub


# ============================================================
# 4. تحميل LineString من ملف KML (مع خيار القلب اليدوي)
# ============================================================
def load_line_from_kml(kml_path, reverse=False):
    """
    يقرأ المسار من KML ويعيده كـ LineString في UTM 34N.

    Parameters:
        kml_path : مسار ملف KML
        reverse  : إذا True، يقلب ترتيب الإحداثيات
                   (يُستخدم فقط للخطوط التي ملفها معكوس — SSAS حالياً)
    """
    tree = ET.parse(kml_path)
    root = tree.getroot()
    ns = {'kml': 'http://www.opengis.net/kml/2.2'}

    ct = root.find('.//kml:LineString/kml:coordinates', ns)
    if ct is None:
        raise ValueError(f"لا يوجد LineString في: {kml_path}")

    coords_text = ct.text.strip()
    coords = [tuple(map(float, c.split(',')[:2]))
              for c in coords_text.split()]

    if reverse:
        coords = coords[::-1]

    t_utm = Transformer.from_crs("EPSG:4326", "EPSG:32634", always_xy=True)
    cu = [t_utm.transform(lon, lat) for lon, lat in coords]

    return LineString(cu)


# ============================================================
# 5. حساب الإزاحة حسب نوع المعايرة
# ============================================================
def compute_offset(ratio, cfg):
    """يحسب الإزاحة عند نسبة معينة على المسار"""
    offset_m = cfg["calibration_offset_m"]
    off_type = cfg["offset_type"]
    cal_st = cfg["calibration_station"]

    if cal_st is None or offset_m == 0:
        return 0

    start_st = cfg["start_station"]
    end_st = cfg["end_station"]
    total_range = end_st - start_st

    if total_range <= 0:
        return 0

    ratio_cal = (cal_st - start_st) / total_range

    if off_type == 'constant':
        return offset_m

    if off_type == 'linear_increasing':
        if ratio_cal <= 0:
            return 0
        return (offset_m / ratio_cal) * ratio

    if off_type == 'linear_decreasing':
        if ratio_cal <= 0 or ratio_cal >= 1:
            return 0
        if ratio <= ratio_cal:
            return (ratio / ratio_cal) * offset_m
        remaining = 1 - ratio_cal
        progress = (ratio - ratio_cal) / remaining
        return offset_m * (1 - progress)

    return 0


# ============================================================
# 6. الدالة الرئيسية: إسقاط نقاط خط على KML
# ============================================================
def project_line_points(line_key, allines_path="ALLINES.xlsx"):
    """يربط بين ALLINES.xlsx وملف KML — الأصغر أولاً (جنوب → شمال)"""
    cfg = LINES_CONFIG[line_key]

    df_points = extract_line_points(line_key, allines_path)
    if df_points.empty:
        return pd.DataFrame()

    line = load_line_from_kml(
        cfg["kml_file"],
        reverse=cfg.get("reverse_kml", False)
    )

    t_wgs = Transformer.from_crs("EPSG:32634", "EPSG:4326", always_xy=True)

    start_st = cfg["start_station"]
    end_st = cfg["end_station"]
    total_range = end_st - start_st

    results = []

    for _, row in df_points.iterrows():
        station = row['station_m']

        if station < start_st or station > end_st:
            continue

        ratio = (station - start_st) / total_range if total_range > 0 else 0
        offset = compute_offset(ratio, cfg)

        dist_on_line = (ratio * line.length) + offset
        dist_on_line = max(0, min(dist_on_line, line.length))

        p = line.interpolate(dist_on_line)
        lon, lat = t_wgs.transform(p.x, p.y)

        results.append({
            'الخط': line_key,
            'اسم_الخط': cfg['name'],
            'Station': row['الرقم'],
            'Type': row['النوع'],
            'Station_m': station,
            'Ratio': round(ratio, 5),
            'Offset_m': round(offset, 1),
            'Distance_m': round(dist_on_line, 1),
            'Longitude': round(lon, 7),
            'Latitude': round(lat, 7),
        })

    df = pd.DataFrame(results)
    if not df.empty:
        df = df.sort_values('Station_m').reset_index(drop=True)
    return df


# ============================================================
# 7. إنشاء KML أساسي (بدون إضافات)
# ============================================================
def build_kml(result_df, line_key, include_path=True):
    """
    النسخة الأساسية: مسار + نقاط فقط.
    (للاستخدام العام — راجع build_kml_enhanced للميزات الإضافية)
    """
    cfg = LINES_CONFIG[line_key]

    kml = ['<?xml version="1.0" encoding="UTF-8"?>',
           '<kml xmlns="http://www.opengis.net/kml/2.2">',
           '<Document>',
           f'<name>{cfg["name"]}</name>',
           f'<description>ملف موحّد: المسار + النقاط (جنوب ← شمال)</description>']

    styles = {
        'AV':      ('ff0000ff', 'http://maps.google.com/mapfiles/kml/paddle/red-circle.png'),
        'MH':      ('ff00ff00', 'http://maps.google.com/mapfiles/kml/paddle/grn-square.png'),
        'PW':      ('ffff0000', 'http://maps.google.com/mapfiles/kml/paddle/orange-circle.png'),
        'BO':      ('ff00ffff', 'http://maps.google.com/mapfiles/kml/paddle/ylw-circle.png'),
        'TO':      ('ffff00ff', 'http://maps.google.com/mapfiles/kml/paddle/purple-circle.png'),
        'VA':      ('ffffffff', 'http://maps.google.com/mapfiles/kml/paddle/wht-circle.png'),
        'TEE':     ('ff00ffff', 'http://maps.google.com/mapfiles/kml/paddle/ltblu-circle.png'),
        'default': ('ff808080', 'http://maps.google.com/mapfiles/kml/paddle/wht-blank.png'),
    }

    def get_key(t):
        t = str(t).upper()
        for k in ['AV', 'MH', 'PW', 'BO', 'TO', 'VA', 'TEE']:
            if k in t:
                return k
        return 'default'

    for key, (color, icon) in styles.items():
        kml.append(
            f'<Style id="s_{key}">'
            f'<IconStyle><color>{color}</color><scale>0.9</scale>'
            f'<Icon><href>{icon}</href></Icon></IconStyle>'
            f'<LabelStyle><scale>0.7</scale></LabelStyle>'
            f'</Style>'
        )

    line_color = cfg.get('color', '#00008B').lstrip('#')
    r, g, b = line_color[0:2], line_color[2:4], line_color[4:6]
    kml_color = f'ff{b}{g}{r}'

    kml.append(
        f'<Style id="line_style">'
        f'<LineStyle><color>{kml_color}</color><width>4</width></LineStyle>'
        f'</Style>'
    )

    if include_path:
        try:
            line_geom = load_line_from_kml(
                cfg["kml_file"],
                reverse=cfg.get("reverse_kml", False)
            )
            t_wgs = Transformer.from_crs("EPSG:32634", "EPSG:4326", always_xy=True)
            line_simple = line_geom.simplify(0.5)

            coords_str = ' '.join(
                f'{lon:.7f},{lat:.7f},0'
                for x, y in line_simple.coords
                for lon, lat in [t_wgs.transform(x, y)]
            )

            kml.append(
                '<Folder>'
                f'<name>🛤️ مسار {line_key} (جنوب ← شمال)</name>'
                '<open>1</open>'
                '<Placemark>'
                f'<name>{cfg["name"]}</name>'
                f'<description>مسار الخط {line_key}</description>'
                '<styleUrl>#line_style</styleUrl>'
                '<LineString>'
                '<tessellate>1</tessellate>'
                f'<coordinates>{coords_str}</coordinates>'
                '</LineString>'
                '</Placemark>'
                '</Folder>'
            )
        except Exception as e:
            kml.append(f'<!-- ⚠️ لم يتم تحميل المسار: {e} -->')

    if not result_df.empty:
        df_sorted = result_df.sort_values('Station_m').reset_index(drop=True)

        kml.append(
            '<Folder>'
            f'<name>📍 نقاط {line_key} ({len(df_sorted)} نقطة)</name>'
            '<open>1</open>'
        )

        for _, r in df_sorted.iterrows():
            s = get_key(r['Type'])
            lat = r['Latitude']
            lon = r['Longitude']

            placemark = (
                '<Placemark>'
                f'<name>{r["Station"]}</name>'
                '<description><![CDATA['
                f'<b>Station:</b> {r["Station"]}<br>'
                f'<b>Type:</b> {r["Type"]}<br>'
                f'<b>Offset:</b> {r["Offset_m"]} m<br>'
                f'<b>Position:</b> {r["Distance_m"]/1000:.3f} km'
                ']]></description>'
                f'<styleUrl>#s_{s}</styleUrl>'
                '<LookAt>'
                f'<longitude>{lon}</longitude>'
                f'<latitude>{lat}</latitude>'
                '<altitude>0</altitude><heading>0</heading>'
                '<tilt>45</tilt><range>2000</range>'
                '<altitudeMode>relativeToGround</altitudeMode>'
                '</LookAt>'
                '<Point>'
                f'<coordinates>{lon},{lat},0</coordinates>'
                '</Point>'
                '</Placemark>'
            )
            kml.append(placemark)

        kml.append('</Folder>')

    kml.append('</Document></kml>')
    return '\n'.join(kml)


# ============================================================
# 8. النسخة المحسّنة: أيقونات + بداية/نهاية + تصفية
# ============================================================
def build_kml_enhanced(result_df, line_key, include_path=True,
                       filter_types=None,
                       add_start_end=True):
    """
    نسخة محسّنة من build_kml مع ميزات إضافية:

    Parameters:
        result_df      : DataFrame ناتج project_line_points
        line_key       : مفتاح الخط
        include_path   : تضمين المسار
        filter_types   : قائمة أنواع للتصفية (None = الكل)
                         مثال: ['MH', 'AV'] لعرض هذه الأنواع فقط
        add_start_end  : إضافة نقاط بداية/نهاية بارزة
    """
    cfg = LINES_CONFIG[line_key]

    # ⭐ تصفية حسب النوع
    df = result_df.copy()
    if filter_types and len(filter_types) > 0:
        pattern = '|'.join(filter_types)
        df = df[df['Type'].astype(str).str.upper().str.contains(
            pattern, case=False, na=False, regex=True
        )]

    if df.empty:
        return None

    kml = ['<?xml version="1.0" encoding="UTF-8"?>',
           '<kml xmlns="http://www.opengis.net/kml/2.2">',
           '<Document>',
           f'<name>{cfg["name"]}</name>',
           f'<description>ملف موحّد: المسار + النقاط (جنوب ← شمال)</description>']

    # ── أنماط النقاط (مع أيقونات مخصصة)
    styles = {
        'AV':      ('ff0000ff', 'http://maps.google.com/mapfiles/kml/paddle/red-circle.png'),
        'MH':      ('ff00ff00', 'http://maps.google.com/mapfiles/kml/paddle/grn-square.png'),
        'PW':      ('ffff0000', 'http://maps.google.com/mapfiles/kml/paddle/orange-circle.png'),
        'BO':      ('ff00ffff', 'http://maps.google.com/mapfiles/kml/paddle/ylw-circle.png'),
        'TO':      ('ffff00ff', 'http://maps.google.com/mapfiles/kml/paddle/purple-circle.png'),
        'VA':      ('ffffffff', 'http://maps.google.com/mapfiles/kml/paddle/wht-circle.png'),
        'TEE':     ('ff00ffff', 'http://maps.google.com/mapfiles/kml/paddle/ltblu-circle.png'),
        'FM':      ('ff00a5ff', 'http://maps.google.com/mapfiles/kml/paddle/blu-circle.png'),
        'BV':      ('ff800080', 'http://maps.google.com/mapfiles/kml/paddle/pink-circle.png'),
        'default': ('ff808080', 'http://maps.google.com/mapfiles/kml/paddle/wht-blank.png'),
    }

    def get_key(t):
        t = str(t).upper()
        for k in ['AV', 'MH', 'PW', 'BO', 'TO', 'VA', 'TEE', 'FM', 'BV']:
            if k in t:
                return k
        return 'default'

    for key, (color, icon) in styles.items():
        kml.append(
            f'<Style id="s_{key}">'
            f'<IconStyle><color>{color}</color><scale>0.9</scale>'
            f'<Icon><href>{icon}</href></Icon></IconStyle>'
            f'<LabelStyle><scale>0.7</scale></LabelStyle>'
            f'</Style>'
        )

    # ── أنماط بداية/نهاية بارزة
    if add_start_end:
        kml.append(
            '<Style id="start_point">'
            '<IconStyle><color>ff00ff00</color><scale>1.4</scale>'
            '<Icon><href>http://maps.google.com/mapfiles/kml/paddle/grn-stars.png</href></Icon>'
            '</IconStyle>'
            '<LabelStyle><scale>1.1</scale></LabelStyle>'
            '</Style>'
        )
        kml.append(
            '<Style id="end_point">'
            '<IconStyle><color>ff0000ff</color><scale>1.4</scale>'
            '<Icon><href>http://maps.google.com/mapfiles/kml/paddle/red-stars.png</href></Icon>'
            '</IconStyle>'
            '<LabelStyle><scale>1.1</scale></LabelStyle>'
            '</Style>'
        )

    # ── نمط المسار
    line_color = cfg.get('color', '#00008B').lstrip('#')
    r, g, b = line_color[0:2], line_color[2:4], line_color[4:6]
    kml_color = f'ff{b}{g}{r}'

    kml.append(
        f'<Style id="line_style">'
        f'<LineStyle><color>{kml_color}</color><width>4</width></LineStyle>'
        f'</Style>'
    )

    # ── مجلد المسار
    if include_path:
        try:
            line_geom = load_line_from_kml(
                cfg["kml_file"],
                reverse=cfg.get("reverse_kml", False)
            )
            t_wgs = Transformer.from_crs("EPSG:32634", "EPSG:4326", always_xy=True)
            line_simple = line_geom.simplify(0.5)

            coords_str = ' '.join(
                f'{lon:.7f},{lat:.7f},0'
                for x, y in line_simple.coords
                for lon, lat in [t_wgs.transform(x, y)]
            )

            kml.append(
                '<Folder>'
                f'<name>🛤️ مسار {line_key} (جنوب ← شمال)</name>'
                '<open>1</open>'
                '<Placemark>'
                f'<name>{cfg["name"]}</name>'
                '<styleUrl>#line_style</styleUrl>'
                '<LineString>'
                '<tessellate>1</tessellate>'
                f'<coordinates>{coords_str}</coordinates>'
                '</LineString>'
                '</Placemark>'
                '</Folder>'
            )
        except Exception as e:
            kml.append(f'<!-- ⚠️ لم يتم تحميل المسار: {e} -->')

    # ── مجلد النقاط
    if not df.empty:
        df_sorted = df.sort_values('Station_m').reset_index(drop=True)

        kml.append(
            '<Folder>'
            f'<name>📍 نقاط {line_key} ({len(df_sorted)} نقطة)</name>'
            '<open>1</open>'
        )

        for _, r in df_sorted.iterrows():
            s = get_key(r['Type'])
            lat = r['Latitude']
            lon = r['Longitude']

            placemark = (
                '<Placemark>'
                f'<name>{r["Station"]}</name>'
                '<description><![CDATA['
                f'<b>Station:</b> {r["Station"]}<br>'
                f'<b>Type:</b> {r["Type"]}<br>'
                f'<b>Offset:</b> {r["Offset_m"]} m<br>'
                f'<b>Position:</b> {r["Distance_m"]/1000:.3f} km'
                ']]></description>'
                f'<styleUrl>#s_{s}</styleUrl>'
                '<LookAt>'
                f'<longitude>{lon}</longitude>'
                f'<latitude>{lat}</latitude>'
                '<altitude>0</altitude><heading>0</heading>'
                '<tilt>45</tilt><range>2000</range>'
                '<altitudeMode>relativeToGround</altitudeMode>'
                '</LookAt>'
                '<Point>'
                f'<coordinates>{lon},{lat},0</coordinates>'
                '</Point>'
                '</Placemark>'
            )
            kml.append(placemark)

        kml.append('</Folder>')

    # ── نقاط البداية والنهاية البارزة
    if add_start_end and not df.empty:
        df_sorted = df.sort_values('Station_m').reset_index(drop=True)
        first = df_sorted.iloc[0]
        last  = df_sorted.iloc[-1]

        kml.append(
            '<Folder>'
            '<name>⭐ نقاط بارزة</name>'
            '<open>1</open>'
            # نقطة البداية
            '<Placemark>'
            f'<name>🟢 بداية — {first["Station"]}</name>'
            '<description><![CDATA['
            '<b>بداية الخط</b><br>'
            f'<b>Station:</b> {first["Station"]}<br>'
            f'<b>Type:</b> {first["Type"]}<br>'
            f'<b>Position:</b> {first["Distance_m"]/1000:.3f} km'
            ']]></description>'
            '<styleUrl>#start_point</styleUrl>'
            '<Point>'
            f'<coordinates>{first["Longitude"]},{first["Latitude"]},0</coordinates>'
            '</Point>'
            '</Placemark>'
            # نقطة النهاية
            '<Placemark>'
            f'<name>🔴 نهاية — {last["Station"]}</name>'
            '<description><![CDATA['
            '<b>نهاية الخط</b><br>'
            f'<b>Station:</b> {last["Station"]}<br>'
            f'<b>Type:</b> {last["Type"]}<br>'
            f'<b>Position:</b> {last["Distance_m"]/1000:.3f} km'
            ']]></description>'
            '<styleUrl>#end_point</styleUrl>'
            '<Point>'
            f'<coordinates>{last["Longitude"]},{last["Latitude"]},0</coordinates>'
            '</Point>'
            '</Placemark>'
            '</Folder>'
        )

    kml.append('</Document></kml>')
    return '\n'.join(kml)