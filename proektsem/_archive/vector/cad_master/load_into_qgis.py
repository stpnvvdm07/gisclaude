# Вставить в консоль Python QGIS (Модули - Консоль Python) при открытом проекте proektsem.qgz
import os
from qgis.core import QgsProject, QgsVectorLayer
base = os.path.join(QgsProject.instance().homePath(), "vector", "cad_master")
layers = [("basemap_cad.gpkg","green"),("basemap_cad.gpkg","paths"),("basemap_cad.gpkg","playgrounds"),("basemap_cad.gpkg","boundary"),
          ("cells.gpkg","cells_excluded"),("cells.gpkg","cells"),("buildings.gpkg","buildings"),("fences.gpkg","fences"),
          ("entrances_buildings.gpkg","entrances_buildings"),("entries_territory.gpkg","entries_territory")]
grp = QgsProject.instance().layerTreeRoot().insertGroup(0, "cad_master")
for f, name in layers:
    lyr = QgsVectorLayer(os.path.join(base, f) + "|layername=" + name, name, "ogr")
    if lyr.isValid():
        QgsProject.instance().addMapLayer(lyr, False); grp.addLayer(lyr)
    else:
        print("не открылся:", f, name)
