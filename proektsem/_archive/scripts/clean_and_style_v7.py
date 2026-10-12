# Убирает дубли и лишние слои, расставляет слои по группам и задаёт стили в палитре команды.
# Запуск: Модули - Консоль Python - Показать редактор - Открыть скрипт - Запустить. Можно запускать повторно.
import os
from qgis.core import (QgsProject, QgsVectorLayer, QgsFillSymbol, QgsLineSymbol, QgsMarkerSymbol,
                       QgsCategorizedSymbolRenderer, QgsRendererCategory, QgsSingleSymbolRenderer,
                       QgsPalLayerSettings, QgsTextFormat, QgsTextBufferSettings, QgsVectorLayerSimpleLabeling)
from qgis.PyQt.QtGui import QColor

prj = QgsProject.instance(); root = prj.layerTreeRoot(); home = prj.homePath()
A = os.path.join(home, "vector", "analiz.gpkg"); K = os.path.join(home, "vector", "konkovo.gpkg")

# ---------- палитра команды
C = dict(water="#5bbccf", green_l="#dde9d0", green_m="#8ed0ad", green_s="#bddaae", cream="#f7f0e6", beige="#e1d8c7",
         white="#ffffff", brown="#a39279", teal="#8bb0b0", yellow="#d9c35b", purple="#6852a0", red="#b13840",
         green="#5ec46e", blue="#94acd6", lavender="#a68cc6", grey="#333338", black="#16161c", pink="#c978d3")

def rgba(hex_, a=255):
    c = QColor(hex_); return "%d,%d,%d,%d" % (c.red(), c.green(), c.blue(), a)
def fill(col, a=255, outline=None, ow=0.3, ostyle="solid"):
    d = {"color": rgba(col, a), "outline_style": "no" if outline is None else ostyle}
    if outline: d.update(outline_color=rgba(outline), outline_width=str(ow))
    return QgsFillSymbol.createSimple(d)
def line(col, w=0.5, style="solid", a=255):
    return QgsLineSymbol.createSimple({"line_color": rgba(col, a), "line_width": str(w), "line_style": style, "capstyle": "round", "joinstyle": "round"})
def mark(col, size=1.6, shape="circle", outline=None):
    d = {"name": shape, "color": rgba(col), "size": str(size), "outline_style": "no" if outline is None else "solid"}
    if outline: d.update(outline_color=rgba(outline), outline_width="0.2")
    return QgsMarkerSymbol.createSimple(d)
def single(sym):
    return lambda l: l.setRenderer(QgsSingleSymbolRenderer(sym.clone()))
def cats(expr, items, other=None):
    def f(l):
        cs = [QgsRendererCategory(v, s.clone(), lab or str(v)) for v, s, lab in items]
        if other is not None: cs.append(QgsRendererCategory(None, other.clone(), "прочее"))
        l.setRenderer(QgsCategorizedSymbolRenderer(expr, cs))
    return f
def labels(field, size=7, col=C["black"], expr=False):
    def f(l):
        s = QgsPalLayerSettings(); s.fieldName = field; s.isExpression = expr; s.enabled = True
        t = QgsTextFormat(); t.setSize(size); t.setColor(QColor(col))
        b = QgsTextBufferSettings(); b.setEnabled(True); b.setSize(0.7); b.setColor(QColor(C["white"])); t.setBuffer(b)
        s.setFormat(t); l.setLabeling(QgsVectorLayerSimpleLabeling(s)); l.setLabelsEnabled(True)
    return f
def nolabels(l): l.setLabelsEnabled(False)
def combo(*fs):
    def f(l):
        for x in fs: x(l)
    return f
def opacity(v): return lambda l: l.setOpacity(v)

# ---------- стили (первый вариант - основной, остальные доступны в Стили - выбор стиля слоя)
CLS = [("Высокий", fill(C["green"], 200), "высокий"), ("Средний", fill(C["yellow"], 200), "средний"),
       ("Низкий", fill(C["red"], 200), "низкий"), ("нет фасадов", fill(C["grey"], 120), "нет фасадов"),
       ("вне анализа", fill(C["beige"], 200), "вне анализа")]
def cells_by(field):
    return combo(cats('CASE WHEN "is_anal"=0 THEN \'вне анализа\' WHEN "%s" IS NULL THEN \'нет фасадов\' ELSE "%s" END' % (field, field), CLS),
                 labels("num"), opacity(1))
COMF = [("Комфортная", fill(C["green"], 200), "комфортная"), ("Некомфортная", fill(C["red"], 200), "некомфортная"),
        ("вне анализа", fill(C["beige"], 200), "вне анализа")]
def cells_comf(field):
    return combo(cats('CASE WHEN "is_anal"=0 THEN \'вне анализа\' ELSE trim("%s") END' % field, COMF), labels("num"))
WEAR = ('CASE WHEN coalesce("Степень изношенности"*100, to_real(regexp_substr("Наша оценка изношенности",\'(\\\\d+)\'))) >= 40 THEN \'40% и более\' '
        'WHEN coalesce("Степень изношенности"*100, to_real(regexp_substr("Наша оценка изношенности",\'(\\\\d+)\'))) IS NOT NULL THEN \'менее 40%\' ELSE \'нет данных\' END')
FIX = ('CASE WHEN "podtip" LIKE \'%не зафиксирован%\' OR "podtip" LIKE \'%насаждени%\' THEN \'не организован\' ELSE \'организован\' END')
PGZ = 'CASE WHEN "problem" IS NOT NULL OR "conflict"=\'да\' THEN \'конфликт\' ELSE "zone" END'

STYLES = {
 ("konkovo", "boundary"): [("граница", single(fill(C["white"], 0, C["pink"], 1.2, "dash")))],
 ("konkovo", "green"): [("зелень", cats('"type"', [("трава", fill(C["green_l"]), "трава"), ("деревья", fill(C["green_s"]), "деревья")]))],
 ("konkovo", "trees"): [("деревья", single(mark(C["green_m"], 1.4)))],
 ("konkovo", "playgrounds"): [("площадки", cats('"type"', [("детская", fill(C["yellow"]), "детская"), ("спортивная", fill(C["blue"]), "спортивная"),
                                                          ("воркаут", fill(C["lavender"]), "воркаут"), ("для собак", fill(C["teal"]), "для собак")]))],
 ("konkovo", "cells_excluded"): [("вне ячеек", single(fill(C["beige"], 255)))],
 ("konkovo", "cells"): [("контур", combo(single(fill(C["white"], 0, C["black"], 0.3)), labels("num"))),
                        ("вертикальные пропорции", cells_by("vertical")), ("замкнутость", cells_by("isolation")),
                        ("размеры", cells_comf("planning")), ("комфортность", cells_comf("comfort"))],
 ("konkovo", "buildings"): [("здания", combo(single(fill(C["brown"])), nolabels)),
                            ("износ", combo(cats(WEAR, [("40% и более", fill(C["red"]), "износ 40% и более"), ("менее 40%", fill(C["brown"]), "износ менее 40%"),
                                                        ("нет данных", fill(C["beige"], 255, C["brown"], 0.2), "нет данных")]), nolabels)),
                            ("номера", combo(single(fill(C["brown"])), labels("id", 6)))],
 ("konkovo", "fences"): [("ограждения", cats('"podtip"', [("Ограждение — высокое решётчатое", line(C["blue"], 0.6), "высокое решётчатое"),
                                                          ("Ограждение — высокое сплошное", line(C["purple"], 0.7), "высокое сплошное"),
                                                          ("Ограждение — низкое", line(C["teal"], 0.4, "dash"), "низкое")], line(C["grey"], 0.4)))],
 ("konkovo", "entrances_buildings"): [("подъезды", single(mark(C["red"], 1.4, "triangle")))],
 ("konkovo", "entries_territory"): [("входы", cats(FIX, [("организован", mark(C["red"], 2.6, "triangle"), "организованный вход"),
                                                         ("не организован", mark(C["yellow"], 2.6, "triangle", C["black"]), "неорганизованный вход")]))],
 ("konkovo", "roads_tree"): [("дерево путей", cats('"group"', [("высокая", line(C["red"], 1.8), "высокая интенсивность"), ("низкая", line(C["yellow"], 1.2), "низкая интенсивность"),
                                                               ("один путь", line(C["teal"], 0.7), "один путь"), ("нет путей", line(C["beige"], 0.5), "нет путей")]))],
 ("konkovo", "roads_tree_start"): [("начала путей", single(mark(C["black"], 1.2)))],
 ("analiz", "network"): [("сеть", cats('"type"', [("проезд", line(C["white"], 1.6), "проезд"), ("тротуар", line(C["white"], 1.0), "тротуар"),
                                                 ("дорожка", line(C["white"], 0.8), "дорожка"), ("переход", line(C["white"], 1.0, "dash"), "переход"),
                                                 ("лестница", line(C["grey"], 0.6, "dash"), "лестница"), ("тропа", line(C["brown"], 0.6, "dot"), "тропа")])),
                         ("пешеходные пути", cats('coalesce("group", \'нет путей\')', [("высокая", line(C["red"], 1.6), "высокая интенсивность"),
                                                 ("низкая", line(C["yellow"], 1.0), "низкая интенсивность"), ("один путь", line(C["teal"], 0.6), "один путь"),
                                                 ("нет путей", line(C["beige"], 0.4), "нет путей")])),
                         ("разделённость", cats('coalesce("razdel", \'нет путей\')', [("по проезжей части", line(C["red"], 1.2), "по проезжей части"),
                                                 ("по тротуару", line(C["yellow"], 1.0), "по тротуару"), ("отдельно от проезда", line(C["green"], 0.8), "отдельно от проезда"),
                                                 ("нет путей", line(C["beige"], 0.4), "нет путей")]))],
 ("analiz", "control"): [("контролируемость", combo(cats('"type"', [("контролируемая", fill(C["green"]), "контролируемая"),
                                                 ("частично контролируемая", fill(C["yellow"]), "частично контролируемая"),
                                                 ("неконтролируемая", fill(C["red"]), "неконтролируемая")]), opacity(0.6)))],
 ("analiz", "control_zones"): [("зоны контроля", combo(cats('"type"', [("АЖ", fill(C["purple"]), "активный персональный"), ("ПЖ", fill(C["lavender"]), "пассивный персональный"),
                                                 ("АП", fill(C["pink"]), "активный публичный"), ("ПП", fill(C["blue"]), "пассивный публичный")]), opacity(0.45)))],
 ("analiz", "competition"): [("конкуренция", single(fill(C["purple"], 200, C["purple"], 0.4)))],
 ("analiz", "playgrounds_zones"): [("места поведения", cats(PGZ, [("ближняя", fill(C["yellow"]), "ближняя зона, 30 м"), ("средняя", fill(C["blue"]), "средняя зона, 100 м"),
                                                 ("периферийная", fill(C["teal"]), "периферийная зона, 200 м"), ("конфликт", fill(C["red"]), "конфликт размещения")]))],
 ("analiz", "heights"): [("отметки", combo(single(mark(C["black"], 0.8)), labels("z", 5, C["grey"])))],
}
BASEMAP = {"moscow_water": single(fill(C["water"])), "moscow_buildings": single(fill(C["beige"])), "Moscow_roads": single(line(C["white"], 0.6))}

# ---------- 1. дубли, битые и заменённые слои
def key(l): return l.source().replace("\\", "/").split("/vector/")[-1].split("|subset")[0].lower()
DROP = ["konkovo.gpkg|layername=paths", "konkovo.gpkg|layername=roads"]
seen, removed = {}, 0
for node in root.findLayers():                      # порядок дерева: оставляем первый экземпляр
    l = node.layer()
    if l is None or not l.isValid() or any(d in key(l) for d in DROP):
        if l is not None: prj.removeMapLayer(l.id()); removed += 1
        else: node.parent().removeChildNode(node)
        continue
    k = (key(l), l.subsetString())
    if k in seen: prj.removeMapLayer(l.id()); removed += 1
    else: seen[k] = l
for l in list(prj.mapLayers().values()):          # слои вне дерева
    if root.findLayer(l.id()) is None: prj.removeMapLayer(l.id()); removed += 1

# ---------- 2. порядок и группы
ORDER = [("анализ", A, "heights", False), ("анализ", A, "playgrounds_zones", True), ("анализ", A, "network", True),
         ("анализ", K, "roads_tree_start", False), ("анализ", K, "roads_tree", False), ("анализ", A, "competition", True),
         ("анализ", A, "control_zones", False), ("анализ", A, "control", True),
         ("слои", K, "entries_territory", True), ("слои", K, "entrances_buildings", True), ("слои", K, "trees", True),
         ("слои", K, "fences", True), ("слои", K, "buildings", True), ("слои", K, "cells", True), ("слои", K, "cells_excluded", True),
         ("слои", K, "playgrounds", True), ("слои", K, "green", True), ("слои", K, "boundary", True)]
def find(path, name):
    k = (os.path.basename(path) + "|layername=" + name).lower()
    for l in prj.mapLayers().values():
        if key(l) == k: return l
def group(name, idx):
    g = root.findGroup(name)
    if g is None: return root.insertGroup(idx, name)
    if root.children().index(g) != idx:
        c = g.clone(); root.insertChildNode(idx, c); root.removeChildNode(g); g = root.findGroup(name)
    return g
G = {"анализ": group("анализ", 0), "слои": group("слои", 1)}
pos = {"анализ": 0, "слои": 0}
for gname, path, name, on in ORDER:
    l = find(path, name)
    if l is None:
        l = QgsVectorLayer(path + "|layername=" + name, name, "ogr")
        if not l.isValid(): print("не открылся:", name); continue
        prj.addMapLayer(l, False); G[gname].insertLayer(pos[gname], l)
    else:
        node = root.findLayer(l.id()); c = node.clone(); G[gname].insertChildNode(pos[gname], c); node.parent().removeChildNode(node)
    l.setName(name); root.findLayer(l.id()).setItemVisibilityChecked(on); pos[gname] += 1
for g in list(root.findGroups()):                     # пустые и безымянные группы
    if not g.findLayers() or g.name() in ("", "cad_master"):
        for n in g.findLayers():
            c = n.clone(); root.addChildNode(c)
        root.removeChildNode(g)

# ---------- 3. стили
def apply(l, variants):
    sm = l.styleManager(); cur = sm.currentStyle()
    for nm in list(sm.styles()):
        if nm != cur: sm.removeStyle(nm)
    for nm, fn in variants[1:]:
        fn(l); sm.addStyleFromLayer(nm)
    variants[0][1](l); sm.renameStyle(cur, variants[0][0]); l.triggerRepaint()
done, failed = 0, []
for (f, name), variants in STYLES.items():
    l = find(A if f == "analiz" else K, name)
    if l is None: failed.append(name); continue
    try: apply(l, variants); done += 1
    except Exception as e: failed.append("%s: %s" % (name, e))
for l in prj.mapLayers().values():
    for n, fn in BASEMAP.items():
        if l.name() == n:
            try: fn(l); l.triggerRepaint()
            except Exception as e: failed.append("%s: %s" % (n, e))
prj.write()
print("Убрано слоёв: %d. Стилей задано: %d. Слоёв в проекте: %d" % (removed, done, len(prj.mapLayers())))
if failed: print("Не удалось:", failed)
