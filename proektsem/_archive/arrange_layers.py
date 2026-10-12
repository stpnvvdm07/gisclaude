# Расставляет слои проекта по группам и порядку. Недостающие слои подгружает. Запуск из консоли Python QGIS.
import os, shutil
from qgis.core import QgsProject, QgsVectorLayer

prj = QgsProject.instance(); home = prj.homePath(); root = prj.layerTreeRoot()
A = os.path.join(home, "vector", "analiz.gpkg"); K = os.path.join(home, "vector", "konkovo.gpkg")
# (группа, файл, слой, включён) сверху вниз
ORDER = [
    ("анализ", A, "heights", False), ("анализ", A, "playgrounds_zones", True), ("анализ", A, "network", True),
    ("анализ", K, "roads_tree_start", False), ("анализ", K, "roads_tree", False), ("анализ", A, "competition", True),
    ("анализ", A, "control_zones", False), ("анализ", A, "control", True),
    ("слои", K, "entries_territory", True), ("слои", K, "entrances_buildings", True), ("слои", K, "trees", False),
    ("слои", K, "fences", True), ("слои", K, "buildings", True), ("слои", K, "cells", True), ("слои", K, "cells_excluded", True),
    ("слои", K, "playgrounds", False), ("слои", K, "green", True), ("слои", K, "boundary", True),
]
DROP = ["paths", "roads"]          # заменены слоем network

def find(path, name):
    for lyr in prj.mapLayers().values():
        src = lyr.source().replace("\\", "/")
        if os.path.basename(path) in src and ("layername=" + name) in src:
            return lyr
    return None

for name in DROP:
    lyr = find(K, name)
    if lyr is not None: prj.removeMapLayer(lyr.id())

groups = {}
for i, gname in enumerate(["анализ", "слои"]):
    g = root.findGroup(gname)
    if g is None: g = root.insertGroup(i, gname)
    else:
        c = g.clone(); root.insertChildNode(i, c); root.removeChildNode(g); g = root.findGroup(gname)
    groups[gname] = g

for pos_by_group in [dict()]:
    for gname, path, name, on in ORDER:
        lyr = find(path, name)
        if lyr is None:
            lyr = QgsVectorLayer(path + "|layername=" + name, name, "ogr")
            if not lyr.isValid():
                print("не открылся:", name); continue
            prj.addMapLayer(lyr, False)
        node = root.findLayer(lyr.id()); g = groups[gname]; i = pos_by_group.get(gname, 0)
        if node is None:
            new = g.insertLayer(i, lyr)
        else:
            new = node.clone(); g.insertChildNode(i, new); node.parent().removeChildNode(node)
        new.setItemVisibilityChecked(on); pos_by_group[gname] = i + 1

arch = os.path.join(home, "_archive"); os.makedirs(arch, exist_ok=True)
for rel in ["dxf/konkovo_kvartal_v_yacheiki_v4.dxf", "update_layers.py"]:
    src = os.path.join(home, *rel.split("/")); dst = os.path.join(arch, *rel.split("/"))
    if os.path.exists(src):
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        try: shutil.move(src, dst)
        except Exception as e: print("не перенесён:", rel, e)
prj.write()
print("Готово. Слоёв в проекте:", len(prj.mapLayers()))
