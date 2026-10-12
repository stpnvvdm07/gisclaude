# Переводит проект на единый файл vector/konkovo.gpkg. Запуск из консоли Python QGIS.
import os, shutil
from qgis.core import QgsProject, QgsVectorLayer, QgsMapLayerStyle

prj = QgsProject.instance(); home = prj.homePath(); root = prj.layerTreeRoot()
gpkg = os.path.join(home, "vector", "konkovo.gpkg")
names = ["green", "playgrounds", "roads", "paths", "roads_tree", "roads_tree_start", "boundary", "cells_excluded", "cells",
         "buildings", "fences", "trees", "entrances_buildings", "entries_territory"]

old = {}
for lyr in prj.mapLayers().values():
    src = lyr.source().replace("\\", "/")
    if "/vector/layers/" in src and "layername=" in src:
        old[src.split("layername=")[1].split("|")[0]] = lyr

grp = root.findGroup("слои") or root.insertGroup(0, "слои")
for name in names:
    lyr = QgsVectorLayer(gpkg + "|layername=" + name, name, "ogr")
    if not lyr.isValid():
        print("не открылся:", name); continue
    o = old.get(name)
    if o is not None and o.geometryType() == lyr.geometryType() and name != "green":
        st = QgsMapLayerStyle(); st.readFromLayer(o); st.writeToLayer(lyr)
    prj.addMapLayer(lyr, False); grp.addLayer(lyr)
for lyr in list(old.values()):
    prj.removeMapLayer(lyr.id())

arch = os.path.join(home, "_archive"); os.makedirs(arch, exist_ok=True)
for rel in ["vector/layers", "dxf/konkovo_kvartal_v_yacheiki_v3.dxf", "tables/cells_metrics.csv", "switch_layers.py"]:
    src = os.path.join(home, *rel.split("/")); dst = os.path.join(arch, *rel.split("/"))
    if os.path.exists(src):
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        try: shutil.move(src, dst)
        except Exception as e: print("не перенесён:", rel, e)
prj.write()
print("Готово. Слоёв в проекте:", len(prj.mapLayers()))
