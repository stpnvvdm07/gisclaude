# -*- coding: utf-8 -*-
# КАРТА 14 - Транспортная сеть: загруженность
# Что делает скрипт: (1) запоминает, какие слои были включены; (2) отключает всё лишнее; (3) собирает слои этой карты в группу «МАП 14»
# со стилями; (4) поворачивает холст так, чтобы южная граница территории лежала горизонтально, ставит общий для всех карт центр и масштаб 1:3000;
# (5) создаёт макет печати A3 «14 Транспортная сеть: загруженность» с картой, легендой, заголовком, масштабной линейкой и стрелкой севера и открывает его в редакторе.
# Запуск: Модули - Консоль Python - Показать редактор - Открыть скрипт - Запустить. Повторный запуск пересоздаёт группу и макет; прежний макет сохраняется с пометкой «старый».
# Вернуть проект в обычный режим: скрипт 00_вернуть_режим.py.
import os, json, datetime
from qgis.core import (QgsProject, QgsVectorLayer, QgsFillSymbol, QgsLineSymbol, QgsMarkerSymbol, QgsCategorizedSymbolRenderer, QgsRendererCategory,
                       QgsSingleSymbolRenderer, QgsPalLayerSettings, QgsTextFormat, QgsTextBufferSettings, QgsVectorLayerSimpleLabeling, QgsRectangle,
                       QgsPointXY, QgsCoordinateReferenceSystem, QgsPrintLayout, QgsLayoutItemMap, QgsLayoutItemLabel, QgsLayoutItemLegend,
                       QgsLayoutItemScaleBar, QgsLayoutItemPicture, QgsLayoutItemPage, QgsLayoutPoint, QgsLayoutSize, QgsUnitTypes,
                       QgsSymbolLayer, QgsProperty)
from qgis.PyQt.QtGui import QColor, QFont, QFontDatabase
from qgis.utils import iface
try:
    from qgis.core import Qgis
    MM = Qgis.LayoutUnit.Millimeters
except Exception:
    MM = QgsUnitTypes.LayoutMillimeters

# ---------- общие параметры всех карт (менять только здесь и во всех скриптах сразу)
ROT = -26.75                    # поворот карты, градусы: южная граница территории (азимут -26,75 градуса) становится горизонтальной
CENTER = (407724.5, 6167314.9)  # центр территории, EPSG:32637
EXT_W, EXT_H = 900.0, 540.0     # видимая область, м (900 x 540 при масштабе 1:3000 = 300 x 180 мм)
SCALE = 3000
MAP_X, MAP_Y, MAP_W, MAP_H = 10, 28, 300, 180     # положение карты на листе A3 (альбомная, 420 x 297 мм), мм
NUM, TITLE, SUBTITLE = "14", "Транспортная сеть: загруженность", "Группы сети по загруженности транспортом"
NOTE = """Группы: высокая, низкая, один путь. Проезды — основа для анализа совмещения потоков."""
FOOT = "Проектный семинар, БГП251, команда 2. Коньково №2, EPSG:32637. Данные: konkovo_v12, analiz_v12, problems_v12."

prj = QgsProject.instance(); root = prj.layerTreeRoot(); home = prj.homePath()
V = os.path.join(home, "vector")
SRC = {"K": os.path.join(V, "konkovo_v12.gpkg"), "A": os.path.join(V, "analiz_v12.gpkg"), "P": os.path.join(V, "problems_v12.gpkg"),
       "S": os.path.join(V, "proektbase", "slopesandwalls.gpkg"), "BM": os.path.join(V, "basemap")}

# ---------- шрифт (SF Pro, если установлен)
FAM = [f for f in ("SF Pro", "SF Pro Text", "SF Pro Display") if f in QFontDatabase().families()]
FONT_FAMILY = FAM[0] if FAM else None
def sf_font(size):
    f = QFont(FONT_FAMILY) if FONT_FAMILY else QFont(); f.setPointSizeF(size); f.setItalic(False)
    try: f.setWeight(QFont.Weight.Normal)
    except AttributeError: f.setWeight(QFont.Normal)
    return f
# ---------- палитра команды и стили
C = dict(water="#5bbccf", green_l="#dde9d0", green_m="#8ed0ad", green_s="#bddaae", cream="#f7f0e6", beige="#e1d8c7",
         white="#ffffff", brown="#a39279", teal="#8bb0b0", yellow="#d9c35b", purple="#6852a0", red="#b13840",
         green="#5ec46e", blue="#94acd6", lavender="#a68cc6", grey="#333338", black="#16161c", pink="#c978d3", orange="#e08a2b", dark="#5a3d2b")
def rgba(hex_, a=255):
    c = QColor(hex_); return "%d,%d,%d,%d" % (c.red(), c.green(), c.blue(), a)
def fill(col, a=255, outline=None, ow=0.3, ostyle="solid"):
    d = {"color": rgba(col, a), "outline_style": "no" if outline is None else ostyle}
    if outline: d.update(outline_color=rgba(outline), outline_width=str(ow))
    return QgsFillSymbol.createSimple(d)
def hatch(col, a=255, style="b_diagonal", outline=None):
    d = {"style": style, "color": rgba(col, a), "outline_color": rgba(outline or col, a), "outline_width": "0.2"}
    return QgsFillSymbol.createSimple(d)
def line(col, w=0.5, style="solid", a=255):
    return QgsLineSymbol.createSimple({"line_color": rgba(col, a), "line_width": str(w), "line_style": style, "capstyle": "round", "joinstyle": "round"})
def mark(col, size=1.6, shape="circle", outline=None, a=255):
    d = {"name": shape, "color": rgba(col, a), "size": str(size), "outline_style": "no" if outline is None else "solid"}
    if outline: d.update(outline_color=rgba(outline), outline_width="0.2")
    return QgsMarkerSymbol.createSimple(d)
def ring(col, size=3.2, w=0.5):
    return QgsMarkerSymbol.createSimple({"name": "circle", "color": "0,0,0,0", "size": str(size), "outline_color": rgba(col), "outline_width": str(w)})
def shape_dd(sym, expr):
    # форма маркера из выражения (имя формы QGIS: square, diamond, octagon, circle, pentagon, hexagon, cross2, triangle)
    try: key = QgsSymbolLayer.Property.Name
    except AttributeError: key = QgsSymbolLayer.PropertyName
    sym.symbolLayer(0).setDataDefinedProperty(key, QgsProperty.fromExpression(expr)); return sym
def single(sym): return lambda l: l.setRenderer(QgsSingleSymbolRenderer(sym.clone()))
def cats(expr, items, other=None):
    def f(l):
        cs = [QgsRendererCategory(v, s.clone(), lab or str(v)) for v, s, lab in items]
        if other is not None: cs.append(QgsRendererCategory("", other[0].clone(), other[1] if len(other) > 1 else "прочее"))
        l.setRenderer(QgsCategorizedSymbolRenderer(expr, cs))
    return f
def labels(field, size=7, col=C["black"], expr=False):
    def f(l):
        s = QgsPalLayerSettings(); s.fieldName = field; s.isExpression = expr; s.enabled = True
        t = QgsTextFormat(); t.setFont(sf_font(size)); t.setSize(size); t.setColor(QColor(col))
        b = QgsTextBufferSettings(); b.setEnabled(True); b.setSize(0.7); b.setColor(QColor(C["white"])); t.setBuffer(b)
        s.setFormat(t); l.setLabeling(QgsVectorLayerSimpleLabeling(s)); l.setLabelsEnabled(True)
    return f
def combo(*fs):
    def f(l):
        for x in fs: x(l)
    return f
def opacity(v): return lambda l: l.setOpacity(v)
CLS = [("Высокий", fill(C["green"], 200), "высокий"), ("Средний", fill(C["yellow"], 200), "средний"), ("Низкий", fill(C["red"], 200), "низкий"),
       ("нет фасадов", fill(C["grey"], 120), "нет фасадов"), ("вне анализа", fill(C["beige"], 200), "вне анализа")]
def cells_by(field):
    return cats('CASE WHEN "is_anal"=0 THEN \'вне анализа\' WHEN "%s" IS NULL THEN \'нет фасадов\' ELSE "%s" END' % (field, field), CLS)
COMF = [("Комфортная", fill(C["green"], 200), "комфортная"), ("Некомфортная", fill(C["red"], 200), "некомфортная"), ("вне анализа", fill(C["beige"], 200), "вне анализа")]
def cells_comf(field):
    return cats('CASE WHEN "is_anal"=0 THEN \'вне анализа\' ELSE trim("%s") END' % field, COMF)
WEAR = ('CASE WHEN coalesce("Степень изношенности"*100, to_real(regexp_substr("Наша оценка изношенности",\'(\\\\d+)\'))) >= 40 THEN \'40% и более\' '
        'WHEN coalesce("Степень изношенности"*100, to_real(regexp_substr("Наша оценка изношенности",\'(\\\\d+)\'))) IS NOT NULL THEN \'менее 40%\' ELSE \'нет данных\' END')
BLD = single(fill(C["brown"]))
BND = single(fill(C["white"], 0, C["pink"], 1.2, "dash"))
GREEN = cats('"type"', [("трава", fill(C["green_l"]), "трава"), ("деревья", fill(C["green_s"]), "деревья")])
CELL_LINES = single(fill(C["white"], 0, C["black"], 0.3))
def PTHICK(w): return w

# ---------- 1. запомнить состояние слоёв (один раз) и отключить всё лишнее
if not prj.readEntry("mapbuild", "vis", "")[0]:
    state = {"layers": {n.layerId(): bool(n.itemVisibilityChecked()) for n in root.findLayers()},
             "groups": {g.name(): bool(g.itemVisibilityChecked()) for g in root.findGroups()},
             "rot": iface.mapCanvas().rotation()}
    prj.writeEntry("mapbuild", "vis", json.dumps(state))
gname = "МАП " + NUM
old = root.findGroup(gname)
if old is not None:
    for n in old.findLayers():
        if n.layer() is not None: prj.removeMapLayer(n.layer().id())
    root.removeChildNode(old)
for n in root.findLayers(): n.setItemVisibilityChecked(False)
for g in root.findGroups(): g.setItemVisibilityChecked(False)

# ---------- 2. слои карты (снизу вверх), стили
LAYERS = [
    ('BM', 'Moscow_water', 'Вода', single(fill(C["water"])), None),
    ('BM', 'Moscow_building', 'Застройка вне территории', single(fill(C["beige"])), None),
    ('BM', 'Moscow_roads', 'Дороги (OSM)', single(line(C["white"], 0.6)), None),
    ('K', 'green', 'Озеленение', GREEN, None),
    ('K', 'buildings', 'Здания', BLD, None),
    ('K', 'cells', 'Границы ячеек', CELL_LINES, None),
    ('A', 'network', 'Транспортная сеть', cats('"vgroup"', [("высокая", line(C["red"],1.8), "высокая"), ("низкая", line(C["orange"],1.0), "низкая"), ("один путь", line(C["grey"],0.5,"dash"), "один путь")]), '"vgroup" IS NOT NULL'),
    ('K', 'boundary', 'Граница территории', BND, None),
]
def make(src, name, title, style, subset=None):
    uri = os.path.join(SRC["BM"], name + ".gpkg") if src == "BM" else SRC[src] + "|layername=" + name
    l = QgsVectorLayer(uri, title, "ogr")
    if not l.isValid(): print("слой не открылся:", uri); return None
    if subset: l.setSubsetString(subset)
    try: style(l)
    except Exception as e: print("стиль не задан:", title, e)
    l.setName(title); prj.addMapLayer(l, False); return l
made = [make(*spec) for spec in LAYERS]
made = [l for l in made if l is not None]
grp = root.insertGroup(0, gname)
for l in reversed(made): grp.addLayer(l)          # верхний слой списка (последний) - первым в дереве
for n in grp.findLayers(): n.setItemVisibilityChecked(True)
grp.setItemVisibilityChecked(True)
top_first = list(reversed(made))
prj.setCrs(QgsCoordinateReferenceSystem("EPSG:32637"))

# ---------- 3. холст: поворот, центр, масштаб
rect = QgsRectangle(CENTER[0] - EXT_W / 2, CENTER[1] - EXT_H / 2, CENTER[0] + EXT_W / 2, CENTER[1] + EXT_H / 2)
cv = iface.mapCanvas(); cv.setRotation(ROT); cv.setExtent(rect); cv.setCenter(QgsPointXY(*CENTER)); cv.zoomScale(SCALE); cv.refresh()

# ---------- 4. макет печати
lname = NUM + " " + TITLE; lm = prj.layoutManager(); prev = lm.layoutByName(lname)
if prev is not None: prev.setName(lname + " (старый " + datetime.datetime.now().strftime("%d.%m %H:%M") + ")")
lay = QgsPrintLayout(prj); lay.initializeDefaults(); lay.setName(lname); lm.addLayout(lay)
try: orient = QgsLayoutItemPage.Orientation.Landscape
except AttributeError: orient = QgsLayoutItemPage.Landscape
lay.pageCollection().page(0).setPageSize("A3", orient)
def place(it, x, y, w, h):
    it.attemptMove(QgsLayoutPoint(x, y, MM)); it.attemptResize(QgsLayoutSize(w, h, MM)); lay.addLayoutItem(it); return it
def text(t, x, y, w, h, size, col=C["black"]):
    lab = QgsLayoutItemLabel(lay); lab.setText(t)
    try:
        tf = QgsTextFormat(); tf.setFont(sf_font(size)); tf.setSize(size); tf.setColor(QColor(col)); lab.setTextFormat(tf)
    except Exception: lab.setFont(sf_font(size))
    return place(lab, x, y, w, h)
mp = QgsLayoutItemMap(lay); place(mp, MAP_X, MAP_Y, MAP_W, MAP_H)
mp.setCrs(prj.crs()); mp.setExtent(rect); mp.setMapRotation(ROT); mp.setScale(SCALE)
mp.setLayers(top_first); mp.setKeepLayerSet(True); mp.setFrameEnabled(True); mp.setBackgroundColor(QColor(C["cream"])); mp.setBackgroundEnabled(True)
text(TITLE, 10, 8, 300, 10, 20); text(SUBTITLE, 10, 18, 300, 8, 10, C["grey"])
leg = QgsLayoutItemLegend(lay); leg.setLinkedMap(mp); leg.setTitle("Условные обозначения"); leg.setAutoUpdateModel(False)
lg = leg.model().rootGroup(); lg.clear()
for l in top_first:
    if '(фон)' in l.name() or l.name().startswith('Номера'): continue   # служебные слои в легенду не выводятся
    lg.addLayer(l)
leg.setLegendFilterByMapEnabled(False); place(leg, 315, 28, 95, 150)
if NOTE.strip(): text(NOTE, 315, 190, 95, 70, 9)
sb = QgsLayoutItemScaleBar(lay); sb.setLinkedMap(mp); sb.setStyle("Single Box"); sb.setUnits(QgsUnitTypes.DistanceMeters)
sb.setNumberOfSegments(4); sb.setNumberOfSegmentsLeft(0); sb.setUnitsPerSegment(100); sb.setUnitLabel("м"); place(sb, 10, 214, 80, 14)
try:
    pic = QgsLayoutItemPicture(lay); pic.setPicturePath(":/images/north_arrows/layout_default_north_arrow.svg"); pic.setLinkedMap(mp)
    try: pic.setNorthMode(QgsLayoutItemPicture.GridNorth)
    except Exception: pass
    place(pic, 292, 30, 14, 14)
except Exception as e: print("стрелка севера не добавлена:", e)
text("Масштаб 1:%d. Карта повёрнута на %.2f град.: южная граница территории горизонтальна" % (SCALE, ROT), 100, 214, 210, 6, 8, C["grey"])
text(FOOT, 10, 284, 400, 6, 7, C["grey"])
iface.openLayoutDesigner(lay)
print("Карта %s собрана: слоёв %d, макет «%s», поворот %.2f, масштаб 1:%d" % (NUM, len(made), lname, ROT, SCALE))
