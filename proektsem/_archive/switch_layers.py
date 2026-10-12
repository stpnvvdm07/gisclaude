# Заменяет в проекте слои из vector/cad_master на слои из vector/layers. Запуск из консоли Python QGIS.
import os, shutil
from qgis.core import QgsProject, QgsVectorLayer, QgsMapLayerStyle

prj = QgsProject.instance(); home = prj.homePath(); root = prj.layerTreeRoot()
base = os.path.join(home, "vector", "layers")
new = [("basemap.gpkg", "green"), ("basemap.gpkg", "playgrounds"), ("basemap.gpkg", "roads"), ("basemap.gpkg", "paths"),
       ("basemap.gpkg", "boundary"), ("cells.gpkg", "cells_excluded"), ("cells.gpkg", "cells"), ("buildings.gpkg", "buildings"),
       ("fences.gpkg", "fences"), ("entrances_buildings.gpkg", "entrances_buildings"), ("entries_territory.gpkg", "entries_territory")]

old = {}
for lyr in prj.mapLayers().values():
    src = lyr.source().replace("\\", "/")
    if "cad_master" in src and "layername=" in src:
        old[src.split("layername=")[1].split("|")[0]] = lyr

grp = root.findGroup("слои") or root.insertGroup(0, "слои")
for f, name in new:
    lyr = QgsVectorLayer(os.path.join(base, f) + "|layername=" + name, name, "ogr")
    if not lyr.isValid():
        print("не открылся:", f, name); continue
    o = old.get(name)
    if o is not None and o.geometryType() == lyr.geometryType():      # перенести стиль со старого слоя
        st = QgsMapLayerStyle(); st.readFromLayer(o); st.writeToLayer(lyr)
    prj.addMapLayer(lyr, False); grp.addLayer(lyr)

for lyr in list(old.values()):
    prj.removeMapLayer(lyr.id())
g = root.findGroup("cad_master")
if g is not None and not g.children():
    root.removeChildNode(g)

arch = os.path.join(home, "_archive"); os.makedirs(arch, exist_ok=True)
for rel in ["vector/cad_master", "tables/buildings_table.csv", "dxf/konkovo_kvartal_v_yacheiki_v2.dxf", "clean_project.py"]:
    src = os.path.join(home, *rel.split("/")); dst = os.path.join(arch, *rel.split("/"))
    if os.path.exists(src):
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        try: shutil.move(src, dst)
        except Exception as e: print("не перенесён:", rel, e)
prj.write()
print("Готово. Слоёв в проекте:", len(prj.mapLayers()))
