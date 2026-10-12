# -*- coding: utf-8 -*-
# Возврат проекта в обычный режим после сборки карты: скрывает группы «МАП NN», возвращает видимость слоёв и групп,
# какой она была перед первым запуском скрипта карты, и поворот холста.
# Макеты печати не удаляются. Слои групп «МАП NN» по умолчанию остаются в проекте (свёрнуты и выключены):
# карты макетов ссылаются именно на эти слои, и при их удалении макеты становятся пустыми.
# Удалить группы вместе со слоями - REMOVE_LAYERS = True (сначала экспортируйте макеты в PDF/PNG).
import json
from qgis.core import QgsProject
from qgis.utils import iface
REMOVE_LAYERS = False
prj = QgsProject.instance(); root = prj.layerTreeRoot()
for g in [g for g in root.findGroups() if g.name().startswith("МАП ")]:
    if REMOVE_LAYERS:
        for n in g.findLayers():
            if n.layer() is not None: prj.removeMapLayer(n.layer().id())
        root.removeChildNode(g)
    else:
        g.setItemVisibilityChecked(False); g.setExpanded(False)
raw = prj.readEntry("mapbuild", "vis", "")[0]
rot = 0
if raw:
    st = json.loads(raw)
    for n in root.findLayers():
        if n.layerId() in st["layers"]: n.setItemVisibilityChecked(st["layers"][n.layerId()])
    for g in root.findGroups():
        if g.name() in st["groups"]: g.setItemVisibilityChecked(st["groups"][g.name()])
    rot = st.get("rot", 0)
    prj.removeEntry("mapbuild", "vis")
else:
    print("Сохранённого состояния нет: видимость слоёв не менялась скриптами карт.")
iface.mapCanvas().setRotation(rot); iface.mapCanvas().refresh()
print("Проект возвращён в обычный режим." + ("" if REMOVE_LAYERS else " Группы «МАП NN» скрыты, макеты сохраняют свои слои."))
