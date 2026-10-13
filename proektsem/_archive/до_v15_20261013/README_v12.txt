proektsem — структура (v12, 13.10.2026)
vector/konkovo_v12.gpkg   исходные слои (здания, ограждения, ячейки, входы, зоны контроля и др.)
vector/analiz_v12.gpkg    освоенность v12, ячейки освоенности
vector/problems_v12.gpkg  нарушения 1.1-3.4 по ячейкам, viol_cells (score, cls), предпосылки
vector/*_v10.gpkg         предыдущая версия, на неё ссылается proektsem.qgz
vector/basemap, proektbase, people_dens.gpkg  исходные данные - не менять
tables/                   xlsx: v10 и v12 (сводный счёт, чувствительность, аудит)
prev/                     превью карт 03, 22, 28, 29
maps/                     PyQGIS-скрипты 00-29 (в QGIS не запускались - проверить поворот -26.75 и маркеры)
raster/, dxf/             топооснова, исходные DWG/DXF
_archive/до_v12_20261013  версии v8, v9, без номера, старые DXF и скрипты карт
