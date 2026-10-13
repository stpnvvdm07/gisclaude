# Прогон PyQGIS-скриптов maps/00-29 без GUI: заглушка iface (настоящий QgsMapCanvas), экспорт макетов в PNG, проверки.
# Запуск (Linux, без экрана): QT_QPA_PLATFORM=offscreen python3 run_maps.py <папка проекта proektsem> <папка вывода> [номера карт]
# Работает на копии проекта: скрипты карт меняют дерево слоёв и макеты (проект не сохраняется).
import sys, os, glob, json, traceback, io, contextlib, types, math
from qgis.core import (QgsApplication, QgsProject, QgsLayoutExporter, QgsLayoutItemMap, QgsLayoutItemLegend, QgsVectorLayer,
                       QgsCategorizedSymbolRenderer, QgsFeatureRequest, QgsExpression, QgsExpressionContext,
                       QgsExpressionContextUtils, QgsMapSettings, QgsPointXY, QgsRectangle, QgsSymbolLayer, QgsRenderContext)
from qgis.PyQt.QtCore import QSize, QSizeF

PROJ, OUT = sys.argv[1], sys.argv[2]
ONLY = set(sys.argv[3:])
os.makedirs(OUT, exist_ok=True)
app = QgsApplication([], True); app.initQgis()
from qgis.gui import QgsMapCanvas
import qgis.utils

class IfaceStub:
    def __init__(self): self.canvas = QgsMapCanvas(); self.canvas.resize(1200, 800); self.opened = []
    def mapCanvas(self): return self.canvas
    def openLayoutDesigner(self, lay): self.opened.append(lay.name()); return None
    def messageBar(self):
        return types.SimpleNamespace(pushMessage=lambda *a, **k: None, pushWarning=lambda *a, **k: None, pushInfo=lambda *a, **k: None)
iface = IfaceStub(); qgis.utils.iface = iface

prj = QgsProject.instance()
ok = prj.read(os.path.join(PROJ, "proektsem.qgz"))
print("проект открыт:", ok, "homePath:", prj.homePath(), "слоёв:", len(prj.mapLayers()))
bad_proj = [l.name() + " -> " + l.source() for l in prj.mapLayers().values() if not l.isValid()]
print("недоступные слои проекта:", len(bad_proj)); [print("   ", b) for b in bad_proj[:40]]

south = (QgsPointXY(407475.0, 6167163.0), QgsPointXY(407784.0, 6167017.0))  # точки на южной границе (рёбра под -26.6 град.)

def check_layout(lay, num):
    res = {}
    maps = [i for i in lay.items() if isinstance(i, QgsLayoutItemMap)]
    legs = [i for i in lay.items() if isinstance(i, QgsLayoutItemLegend)]
    if not maps: return {"err": "нет карты в макете"}
    mp = maps[0]
    ext = mp.extent(); c = ext.center()
    res.update(rot=round(mp.mapRotation(), 2), scale=round(mp.scale()), center=(round(c.x(), 1), round(c.y(), 1)),
               ext_wh=(round(ext.width()), round(ext.height())), size_mm=(round(mp.rect().width()), round(mp.rect().height())),
               layers=len(mp.layers()), legend_items=(legs[0].model().rowCount() if legs else 0))
    # проверка ориентации: южная граница в координатах листа
    ms = mp.mapSettings(mp.extent(), QSizeF(mp.rect().width(), mp.rect().height()), 100, False)
    m2p = ms.mapToPixel()
    a, b = m2p.transform(south[0]), m2p.transform(south[1])
    res["south_angle_on_sheet"] = round(math.degrees(math.atan2(-(b.y() - a.y()), b.x() - a.x())), 2)
    # слои: пустые после фильтра, категории без объектов / объекты вне категорий, ошибки выражений
    lay_issues = []
    for l in mp.layers():
        if not isinstance(l, QgsVectorLayer): continue
        n = l.featureCount()
        if n == 0: lay_issues.append(f"{l.name()}: 0 объектов (фильтр {l.subsetString()!r})")
        r = l.renderer()
        ctx = QgsExpressionContext(QgsExpressionContextUtils.globalProjectLayerScopes(l))
        if isinstance(r, QgsCategorizedSymbolRenderer):
            e = QgsExpression(r.classAttribute())
            if e.hasParserError(): lay_issues.append(f"{l.name()}: ошибка выражения категорий {e.parserErrorString()}"); continue
            vals = {}
            for f in l.getFeatures():
                ctx.setFeature(f); v = e.evaluate(ctx)
                if e.hasEvalError(): lay_issues.append(f"{l.name()}: {e.evalErrorString()}"); break
                vals[v] = vals.get(v, 0) + 1
            cats = {c.value(): c.label() for c in r.categories()}
            miss = {k: v for k, v in vals.items() if k not in cats and not ("" in cats and k in (None, ""))}
            if miss: lay_issues.append(f"{l.name()}: объекты вне категорий {miss}")
            empty = [cats[k] for k in cats if k not in vals and k != ""]
            if empty: lay_issues.append(f"{l.name()}: пустые категории в легенде {empty}")
            # data-defined форма маркера
            cats_keep = r.categories()
            for c in cats_keep:
                sym_keep = c.symbol(); sl = sym_keep.symbolLayer(0)
                try: key = QgsSymbolLayer.Property.Name
                except AttributeError: key = QgsSymbolLayer.PropertyName
                p = sl.dataDefinedProperties().property(key)
                if p and p.isActive():
                    res.setdefault("shape_dd", set()).add(l.name())
                    ex = QgsExpression(p.expressionString())
                    shapes = set()
                    for f in l.getFeatures():
                        ctx.setFeature(f); shapes.add(ex.evaluate(ctx))
                    badsh = [s for s in shapes if s not in ("square", "diamond", "octagon", "circle", "pentagon", "hexagon", "cross2", "triangle", "star", "cross", "cross_fill", "x")]
                    if badsh: lay_issues.append(f"{l.name()}: неверные формы {badsh}")
    if "shape_dd" in res: res["shape_dd"] = sorted(res["shape_dd"])
    res["issues"] = lay_issues
    # экспорт
    exp = QgsLayoutExporter(lay); s = QgsLayoutExporter.ImageExportSettings(); s.dpi = 60
    r = exp.exportToImage(os.path.join(OUT, f"{num}.png"), s); res["export"] = "ok" if r == QgsLayoutExporter.Success else f"ошибка {r}"
    return res

report = {}
scripts = sorted(glob.glob(os.path.join(PROJ, "maps", "*.py")))
for path in scripts:
    num = os.path.basename(path)[:2]
    if ONLY and num not in ONLY: continue
    buf = io.StringIO(); err = None
    before = set(l.name() for l in prj.layoutManager().layouts())
    with contextlib.redirect_stdout(buf):
        try:
            with open(path, encoding="utf-8") as fh: code = fh.read()
            exec(compile(code, path, "exec"), {"__name__": "__main__", "__file__": path})
        except Exception:
            err = traceback.format_exc(limit=3)
    out = buf.getvalue().strip()
    rec = {"stdout": out[-1500:]}
    if err: rec["exception"] = err[-1500:]
    new = [l for l in prj.layoutManager().layouts() if l.name().startswith(num + " ") and "(старый" not in l.name()]
    if num != "00":
        if new:
            try: rec.update(check_layout(new[-1], num))
            except Exception: rec["check_exc"] = traceback.format_exc(limit=3)
        else: rec["layout"] = "макет не создан"
    rec["canvas_rot"] = iface.canvas.rotation()
    report[num] = rec
    print("=" * 8, os.path.basename(path)); print(json.dumps(rec, ensure_ascii=False, indent=1, default=str))
json.dump(report, open(os.path.join(OUT, "report.json"), "w"), ensure_ascii=False, indent=1, default=str)
