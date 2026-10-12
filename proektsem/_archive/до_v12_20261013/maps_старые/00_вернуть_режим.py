# -*- coding: utf-8 -*-
# Возврат проекта в обычный режим после сборки карты: удаляет группы «МАП NN» (вместе с их слоями),
# возвращает видимость слоёв и групп, какой она была перед первым запуском скрипта карты, и снимает поворот холста.
# Макеты печати не удаляются.
import json
from qgis.core import QgsProject
from qgis.utils import iface
prj = QgsProject.instance(); root = prj.layerTreeRoot()
for g in [g for g in root.findGroups() if g.name().startswith("МАП ")]:
    for n in g.findLayers():
        if n.layer() is not None: prj.removeMapLayer(n.layer().id())
    root.removeChildNode(g)
raw = prj.readEntry("mapbuild", "vis", "")[0]
if raw:
    st = json.loads(raw)
    for n in root.findLayers():
        if n.layerId() in st["layers"]: n.setItemVisibilityChecked(st["layers"][n.layerId()])
    for g in root.findGroups():
        if g.name() in st["groups"]: g.setItemVisibilityChecked(st["groups"][g.name()])
    prj.removeEntry("mapbuild", "vis")
else:
    print("Сохранённого состояния нет: видимость слоёв не менялась скриптами карт.")
iface.mapCanvas().setRotation(0); iface.mapCanvas().refresh()
print("Проект возвращён в обычный режим.")
