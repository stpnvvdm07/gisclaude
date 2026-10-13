# Карты для презентации: слои и стили из maps/NN_*.py (данные v13), единая подложка (OSM landuse/здания + линии DWG v9),
# поворот -26,75, без макета. На выходе: PNG карты нужного размера + JSON легенды (иконки символов PNG) + метры на пиксель.
# Запуск: QT_QPA_PLATFORM=offscreen python3 deck_maps.py <папка проекта proektsem> <папка вывода> [ключи карт]
import sys, os, json, glob, io, contextlib, math, types
from qgis.core import (QgsApplication, QgsProject, QgsVectorLayer, QgsMapSettings, QgsMapRendererCustomPainterJob, QgsRectangle,
                       QgsPointXY, QgsCoordinateReferenceSystem, QgsSymbolLayerUtils, QgsFillSymbol, QgsLineSymbol, QgsMarkerSymbol,
                       QgsSingleSymbolRenderer, QgsCategorizedSymbolRenderer, QgsRendererCategory, QgsPalLayerSettings, QgsTextFormat,
                       QgsTextBufferSettings, QgsVectorLayerSimpleLabeling, QgsUnitTypes)
from qgis.PyQt.QtCore import QSize, Qt
from qgis.PyQt.QtGui import QColor, QImage, QPainter, QFont

PROJ, OUT = sys.argv[1], sys.argv[2]; ONLY = set(sys.argv[3:]); os.makedirs(os.path.join(OUT, "icons"), exist_ok=True)
app = QgsApplication([], True); app.initQgis()
from qgis.gui import QgsMapCanvas
import qgis.utils
class IfaceStub:
    def __init__(self): self.canvas = QgsMapCanvas()
    def mapCanvas(self): return self.canvas
    def openLayoutDesigner(self, lay): return None
qgis.utils.iface = IfaceStub()
prj = QgsProject.instance(); prj.read(os.path.join(PROJ, "proektsem.qgz"))
V = os.path.join(PROJ, "vector"); BM = os.path.join(V, "basemap")
ROT = -26.75; CENTER = (407724.5, 6167314.9); TERR = (868.0, 486.0)        # повёрнутый габарит территории, м
SCALE = 2                                                                 # рендер x2 к пикселям слайда
BASE_TITLES = {"Вода", "Застройка вне территории", "Дороги (OSM)", "Номера ячеек анализа", "Номера ячеек"}

def rgba(h, a=255): c = QColor(h); return f"{c.red()},{c.green()},{c.blue()},{a}"
def lay(uri, name, renderer=None, subset=None):
    l = QgsVectorLayer(uri, name, "ogr")
    if subset: l.setSubsetString(subset)
    if renderer: l.setRenderer(renderer)
    return l
def basemap(extra_scale=1.0):
    land = lay(os.path.join(BM, "Moscow_landuse.gpkg"), "landuse",
               QgsSingleSymbolRenderer(QgsFillSymbol.createSimple({"color": rgba("#d7ebc6"), "outline_style": "no"})),
               "\"fclass\" IN ('forest','park','grass','meadow','scrub','recreation_ground','cemetery','allotments')")
    lines = lay(os.path.join(BM, "dwg_context_lines.gpkg"), "context",
                QgsSingleSymbolRenderer(QgsLineSymbol.createSimple({"line_color": rgba("#ffffff"), "line_width": str(0.45 * extra_scale), "capstyle": "round"})))
    return [land, lines]       # снизу вверх

def frame_extent(wpx, hpx, terr_k=1.0):
    a = wpx / hpx
    Wm = max(TERR[0] * 1.18 * terr_k, TERR[1] * 1.22 * terr_k * a); Hm = Wm / a
    return QgsRectangle(CENTER[0] - Wm / 2, CENTER[1] - Hm / 2, CENTER[0] + Wm / 2, CENTER[1] + Hm / 2), Wm / wpx

def render(layers_top_first, wpx, hpx, path, terr_k=1.0, rot=ROT, center=None, extent_m=None, shift_px=0):
    ms = QgsMapSettings(); ms.setDestinationCrs(QgsCoordinateReferenceSystem("EPSG:32637"))
    if shift_px:                                     # сдвиг территории влево на shift_px пикселей слайда (место под карточку справа)
        _, mpp0 = frame_extent(wpx, hpx, terr_k); a = math.radians(rot); d = shift_px * mpp0
        center = (CENTER[0] + d * math.cos(a), CENTER[1] + d * math.sin(a)); extent_m = mpp0 * wpx
    if extent_m:
        cx, cy = center or CENTER; Wm = extent_m; Hm = Wm * hpx / wpx
        rect = QgsRectangle(cx - Wm / 2, cy - Hm / 2, cx + Wm / 2, cy + Hm / 2); mpp = Wm / wpx
    else:
        rect, mpp = frame_extent(wpx, hpx, terr_k)
    ms.setOutputSize(QSize(wpx * SCALE, hpx * SCALE)); ms.setOutputDpi(96 * SCALE)
    ms.setRotation(rot); ms.setExtent(rect); ms.setBackgroundColor(QColor("#f9f3e7"))
    ms.setLayers(layers_top_first); ms.setFlag(QgsMapSettings.Antialiasing, True)
    img = QImage(wpx * SCALE, hpx * SCALE, QImage.Format_ARGB32); img.fill(QColor("#f9f3e7"))
    p = QPainter(img); job = QgsMapRendererCustomPainterJob(ms, p); job.start(); job.waitForFinished(); p.end()
    img.save(path)
    return mpp

def col(c): return "#%02x%02x%02x" % (c.red(), c.green(), c.blue()), round(c.alpha() / 255, 2)
def sym_spec(sym):
    """Упрощённое описание символа для легенды (HTML/Figma): fill / line / marker."""
    try:
        sl = sym.symbolLayer(0); t = sym.__class__.__name__
        if t == "QgsFillSymbol":
            f, fa = col(sl.color()) if hasattr(sl, "color") else ("#cccccc", 1)
            d = dict(kind="fill", fill=f, fa=fa)
            if hasattr(sl, "strokeColor"):
                sc, sa = col(sl.strokeColor()); d.update(stroke=sc, sa=sa if sl.strokeStyle() != Qt.NoPen else 0,
                                                         sw=round(sl.strokeWidth(), 2), dash=sl.strokeStyle() not in (Qt.SolidLine, Qt.NoPen))
            if hasattr(sl, "brushStyle") and sl.brushStyle() not in (Qt.SolidPattern, Qt.NoBrush): d["hatch"] = True
            if hasattr(sl, "brushStyle") and sl.brushStyle() == Qt.NoBrush: d["fa"] = 0
            if sl.__class__.__name__ == "QgsLinePatternFillSymbolLayer": d.update(hatch=True, fill=col(sl.color())[0], fa=1)
            return d
        if t == "QgsLineSymbol":
            c_, a_ = col(sl.color()); return dict(kind="line", stroke=c_, sa=a_, sw=round(sl.width(), 2), dash=getattr(sl, "penStyle", lambda: Qt.SolidLine)() != Qt.SolidLine)
        if t == "QgsMarkerSymbol":
            c_, a_ = col(sl.color()); d = dict(kind="marker", fill=c_, fa=a_, size=round(sl.size(), 2))
            try:
                from qgis.core import QgsSimpleMarkerSymbolLayerBase
                d["shape"] = QgsSimpleMarkerSymbolLayerBase.encodeShape(sl.shape())
            except Exception: d["shape"] = "circle"
            if hasattr(sl, "strokeColor"): d["stroke"], d["sa"] = col(sl.strokeColor())
            return d
    except Exception as e:
        return dict(kind="fill", fill="#cccccc", fa=1, err=str(e))
    return dict(kind="fill", fill="#cccccc", fa=1)

def legend_of(layers_top_first, key):
    out = []; k = 0
    for l in layers_top_first:
        if l.name() in BASE_TITLES or "(фон)" in l.name() or l.name() in ("landuse", "context"): continue
        r = l.renderer(); items = []
        for it in r.legendSymbolItems():
            sym = it.symbol()
            if sym is None: continue
            k += 1; fn = f"icons/{key}_{k}.png"
            pm = QgsSymbolLayerUtils.symbolPreviewPixmap(sym, QSize(64, 40), 4)
            pm.save(os.path.join(OUT, fn))
            items.append(dict(label=it.label() or l.name(), icon=fn, sym=sym_spec(sym)))
        if items: out.append(dict(title=l.name(), items=items))
    return out

def from_script(num):
    path = glob.glob(os.path.join(PROJ, "maps", num + "_*.py"))[0]; g = {"__name__": "__main__"}
    with contextlib.redirect_stdout(io.StringIO()):
        with open(path, encoding="utf-8") as fh: exec(compile(fh.read(), path, "exec"), g)
    return list(g["top_first"]), g.get("TITLE", "")

# ---------- карты: ключ -> (скрипт, ширина, высота в px слайда, исключить слои по имени, коэффициент охвата)
SPECS = {
    # полноэкранные (тёмная плашка снизу)
    "m28": ("28", 1920, 864, set(), 1.0),
    # шаблон команды «место для карт»: 1480x888 справа от колонки легенды
    **{f"s{n}": (n, 1480, 888, set(), 1.0) for n in ("04", "15", "24", "25", "26")},
    # плитка 1280x720 (справа сверху)
    **{f"m{n}": (n, 1280, 720, set(), 1.0) for n in ("03", "08", "11", "12", "18", "22", "23", "27", "29")},
    # пары 960x540
    **{f"m{n}": (n, 960, 540, set(), 1.0) for n in ("09", "10", "13", "14", "16", "17", "19", "20", "21")},
    # тройка 640x400
    **{f"m{n}": (n, 640, 400, set(), 1.0) for n in ("05", "06", "07")},
    # малые для оглавления 480x360
    **{f"b{n}": (n, 480, 360, set(), 1.0) for n in ("04", "12", "22", "28")},
}
SHIFT = {}
meta = {}
mp = os.path.join(OUT, "maps.json")
if os.path.exists(mp): meta = json.load(open(mp, encoding="utf-8"))
for key, (num, w, h, excl, k) in SPECS.items():
    if ONLY and key not in ONLY: continue
    top, title = from_script(num)
    top = [l for l in top if l.name() not in excl and l.isValid()]
    bnd = lay(os.path.join(V, "konkovo_v13.gpkg") + "|layername=boundary", "Граница территории",
              QgsSingleSymbolRenderer(QgsFillSymbol.createSimple({"color": "0,0,0,0", "outline_color": rgba("#da71d7"), "outline_width": "1.1",
                                                                  "outline_style": "dash", "joinstyle": "round"})))
    top = [l for l in top if l.name() != "Граница территории"]
    full = [bnd] + top + list(reversed(basemap()))      # граница сверху, подложка снизу
    mpp = render(full, w, h, os.path.join(OUT, key + ".png"), k, shift_px=SHIFT.get(key, 0))
    meta[key] = dict(title=title, w=w, h=h, mpp=mpp, legend=legend_of(top, key))
    print(key, title, round(mpp, 3), "м/px", len(meta[key]["legend"]), "групп легенды", flush=True)

# ---------- увеличенные фрагменты (линзы) по ячейкам-лидерам: карта 28 (финальная схема), круг 520 px
if not ONLY or "zooms" in ONLY:
    top, _ = from_script("28")
    cells = QgsVectorLayer(os.path.join(V, "konkovo_v13.gpkg") + "|layername=cells", "c", "ogr")
    for num in (28, 35, 14, 11):
        f = next(cells.getFeatures(f'"num" = {num}')); c = f.geometry().centroid().asPoint()
        bnd = lay(os.path.join(V, "konkovo_v13.gpkg") + "|layername=boundary", "Граница территории",
                  QgsSingleSymbolRenderer(QgsFillSymbol.createSimple({"color": "0,0,0,0", "outline_color": rgba("#da71d7"), "outline_width": "1.1", "outline_style": "dash"})))
        hl = lay(os.path.join(V, "konkovo_v13.gpkg") + "|layername=cells", "hl",
                 QgsSingleSymbolRenderer(QgsFillSymbol.createSimple({"color": "0,0,0,0", "outline_color": rgba("#da71d7"), "outline_width": "1.6"})), f'"num" = {num}')
        full = [hl, bnd] + [l for l in top if l.isValid()] + list(reversed(basemap()))
        render(full, 480, 480, os.path.join(OUT, f"zoom_{num}.png"), center=(c.x(), c.y()), extent_m=230)
        meta[f"zoom_{num}"] = dict(title=f"Ячейка {num}", w=480, h=480, mpp=230 / 480, legend=[])
        print("zoom", num, flush=True)

# ---------- ситуационная схема района
if not ONLY or "situation" in ONLY:
    st = lay(os.path.join(BM, "Moscow_transport_points.gpkg"), "Метро", None, "\"fclass\" = 'railway_station'")
    sy = QgsMarkerSymbol.createSimple({"name": "circle", "color": rgba("#14131a"), "size": "3.2", "outline_color": rgba("#ffffff"), "outline_width": "0.6"})
    st.setRenderer(QgsSingleSymbolRenderer(sy))
    s = QgsPalLayerSettings(); s.fieldName = "name"; s.enabled = True
    tf = QgsTextFormat(); tf.setFont(QFont("SF Pro Display")); tf.setSize(11); tf.setColor(QColor("#14131a"))
    bf = QgsTextBufferSettings(); bf.setEnabled(True); bf.setSize(1.2); bf.setColor(QColor("#f9f3e7")); tf.setBuffer(bf); s.setFormat(tf)
    try: s.placement = QgsPalLayerSettings.OverPoint
    except Exception: pass
    s.dist = 3; st.setLabeling(QgsVectorLayerSimpleLabeling(s)); st.setLabelsEnabled(True)
    sub = lay(os.path.join(BM, "Moscow_railways.gpkg"), "subway", QgsSingleSymbolRenderer(QgsLineSymbol.createSimple({"line_color": rgba("#14131a", 120), "line_width": "0.8", "line_style": "dash"})), "\"fclass\" = 'subway'")
    bld = lay(os.path.join(BM, "Moscow_building.gpkg"), "bld", QgsSingleSymbolRenderer(QgsFillSymbol.createSimple({"color": rgba("#e6d9c2"), "outline_style": "no"})))
    wat = lay(os.path.join(BM, "Moscow_water.gpkg"), "water", QgsSingleSymbolRenderer(QgsFillSymbol.createSimple({"color": rgba("#5bbccf"), "outline_style": "no"})))
    ter = lay(os.path.join(V, "konkovo_v13.gpkg") + "|layername=boundary", "Территория", QgsSingleSymbolRenderer(QgsFillSymbol.createSimple({"color": rgba("#da71d7", 170), "outline_color": rgba("#da71d7"), "outline_width": "1.2"})))
    top = [st, ter, sub, wat, bld] + list(reversed(basemap(1.4)))
    mpp = render(top, 960, 1080, os.path.join(OUT, "situation.png"), rot=0, center=(407550, 6167250), extent_m=3000)
    meta["situation"] = dict(title="Ситуационная схема", w=960, h=1080, mpp=mpp, legend=[])
    print("situation", round(mpp, 3))
with open(mp, "w", encoding="utf-8") as fh: json.dump(meta, fh, ensure_ascii=False, indent=1)
