Слои собраны из чертежа AutoCAD (dxf/yacheiki.dxf), EPSG:32637.

Проекция чертежа для QGIS (Настройки - Пользовательские проекции - Proj String):
+proj=tmerc +lat_0=55.66666666667 +lon_0=37.5 +k=1 +x_0=12.268 +y_0=11.964 +ellps=bessel +towgs84=316.151,78.924,589.65,-1.57273,2.69209,2.34693,8.4507 +units=m +no_defs

cells       ячейки: area, perimeter - м2 и м; size - наибольший размер, м;
            fasad_len, fasad_area - длина и площадь фасадов; vert_koef = fasad_area / area;
            fix_len - закреплённый периметр (фасады, высокие ограждения, откосы); iso_koef = fix_len / perimeter
buildings   здания, поля как в таблице tables/Таблица зданий.xlsx, ключ id = FID
basemap     paths - пешеходные линии OSM (11.10.2026), roads - проезды OSM, green, playgrounds, boundary
