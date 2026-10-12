# Чистка проекта proektsem. Запуск: QGIS -> Модули -> Консоль Python -> Показать редактор -> Открыть скрипт -> Запустить.
# Ничего не удаляет: лишние слои убирает из проекта, их файлы переносит в папку _archive.
# Перед изменениями кладёт копию proektsem.qgz в _archive. Можно запускать повторно.
import os, shutil, datetime
from qgis.core import QgsProject, QgsVectorLayer

prj = QgsProject.instance()
home = prj.homePath()
arch = os.path.join(home, "_archive")
os.makedirs(arch, exist_ok=True)

# 0. копия файла проекта
if prj.fileName() and os.path.exists(prj.fileName()):
    stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M")
    shutil.copy2(prj.fileName(), os.path.join(arch, "proektsem_do_chistki_%s.qgz" % stamp))

# 1. слои, которые убираем из проекта (по куску пути к файлу)
REMOVE = [
    "zone_from_raster", "buildings_from_raster", "building_vadim", "buildings_features",
    "spatialcells", "spatial_cells_final", "spatial_units", "spatials_units",
    "proektbase/yacheiki", "proektbase/fences.gpkg", "vector/fences1.gpkg",
    "подьезды.gpkg", "entrances_points", "proektbase/entrances_buildings.gpkg",
    "Moscow_protected_areas", "Moscow_temples", "Moscow_traffic_areas",
    "Moscow_traffic_points", "Moscow_railways", "Moscow_waterways",
]
removed, kept = [], []
for lyr in list(prj.mapLayers().values()):
    src = lyr.source().replace("\\", "/")
    if "cad_master" not in src and any(t in src for t in REMOVE):
        removed.append(lyr.name()); prj.removeMapLayer(lyr.id())
    else:
        kept.append(lyr)

# 2. слой коммерции: переключить с "Загрузок" на файл внутри проекта
local_biz = os.path.join(home, "vector", "proektbase", "businessss.geojson")
for lyr in kept:
    if "businessss" in lyr.source() and "Downloads" in lyr.source() and os.path.exists(local_biz):
        lyr.setDataSource(local_biz, "businessss", "ogr")

# 3. разложить оставшиеся слои по группам
root = prj.layerTreeRoot()
def group(name, index):
    g = root.findGroup(name)
    return g if g else root.insertGroup(index, name)
g_work = group("полевые и рабочие", 1)
g_base = group("подложка", 2)
def move(lyr, grp):
    node = root.findLayer(lyr.id())
    if node is None or node.parent() == grp:
        return
    clone = node.clone(); grp.addChildNode(clone); node.parent().removeChildNode(node)
for lyr in kept:
    src = lyr.source().replace("\\", "/")
    if "cad_master" in src:
        continue
    if "/basemap/Moscow" in src or lyr.providerType() == "wms":
        move(lyr, g_base)
    else:
        move(lyr, g_work)

# 4. файлы, которые больше не нужны -> _archive (структура папок сохраняется)
ARCHIVE = [
    "vector/proektbase/building_vadim.gpkg", "vector/proektbase/buildings_features.gpkg",
    "vector/proektbase/buildings_features2.gpkg", "vector/proektbase/entrances_buildings.gpkg",
    "vector/proektbase/fences.gpkg", "vector/proektbase/spatial_cells_final_ttts.gpkg",
    "vector/proektbase/spatialcells.gpkg", "vector/proektbase/yacheiki.gpkg",
    "vector/proektbase/yacheiki610.gpkg", "vector/proektbase/yacheiki1700.gpkg",
    "vector/proektbase/подьезды.gpkg", "vector/fences1.gpkg", "vector/fromraster",
    "dxf.zip", "dxf/konkovo_kvartal_v_yacheiki.dxf",
    "raster/privyazka.tif", "raster/Общая_топоснова_Коньково-джепег_modified.tif",
    "raster/Общая_топоснова_Коньково-джепег_modified.tif.aux.xml",
    "Ячейки - Вертикальные Пропорции (Макаров).csv", "Ячейки - Планировачные размеры .csv",
    "Ячейки - Степень замкнутости.csv",
]
moved, failed = [], []
for rel in ARCHIVE:
    for extra in ("", "-wal", "-shm"):
        src = os.path.join(home, *rel.split("/")) + extra
        if not os.path.exists(src):
            continue
        dst = os.path.join(arch, *rel.split("/")) + extra
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        try:
            if os.path.exists(dst):
                dst += "_" + datetime.datetime.now().strftime("%H%M%S")
            shutil.move(src, dst); moved.append(rel + extra)
        except Exception as e:
            failed.append((rel + extra, str(e)))

# 5. сохранить проект и отчитаться
prj.write()
print("Убрано из проекта слоёв: %d" % len(removed))
for n in removed: print("   -", n)
print("Осталось слоёв: %d" % len(prj.mapLayers()))
print("Перенесено в _archive: %d" % len(moved))
for n in failed: print("   НЕ перенесён:", n)
bad = [l.name() for l in prj.mapLayers().values() if not l.isValid()]
print("Слои с битым источником:", bad if bad else "нет")
