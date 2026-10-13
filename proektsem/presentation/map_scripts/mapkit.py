# Общая библиотека карт презентации (v15) (matplotlib, без QGIS): стиль карт команды (кремовый фон, белые линии чертежа, зелень OSM,
# розовая пунктирная граница), поворот как на картах команды, названия улиц со всех сторон, легенды -> maps/maps14.json.
# Запуск: python3 maps14.py [ключи]
import os, sys, json, math, warnings
import numpy as np, pandas as pd, geopandas as gpd
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager as fm
from matplotlib.patches import PathPatch, Circle
from matplotlib.path import Path
import matplotlib.patheffects as pe
from shapely.geometry import Point, Polygon, MultiPolygon, LineString, MultiLineString, box
from shapely.ops import unary_union, linemerge
warnings.filterwarnings("ignore")
H = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); PR = os.path.join(H, ".."); V = os.path.join(PR, "vector")
sys.path.insert(0, os.path.join(PR, "analysis")); from plan import to_plan, plan_xy, world_xy, METRO_EXIT_PLAN, MALL_CROSSING_PLAN
OUT = os.path.join(H, "maps"); META = os.path.join(OUT, "maps15.json")
for w in ("Regular", "Medium", "Semibold", "Bold"):
    fm.fontManager.addfont(os.path.join(PR, "design", "san-francisco-pro-display", f"SF-Pro-Display-{w}.otf"))
plt.rcParams["font.family"] = "SF Pro Display"
K, A, P = (os.path.join(V, f) for f in ("konkovo_v15.gpkg", "analiz_v15.gpkg", "problems_v15.gpkg"))
_cache = {}
def L(f, l):
    k = (f, l)
    if k not in _cache:
        d = gpd.read_file(f, layer=l) if l else gpd.read_file(f)
        d = d[d.geometry.notna()].copy(); d["geometry"] = d.geometry.apply(to_plan); _cache[k] = d
    return _cache[k].copy()
def LB(name, bbox=(406700, 6166500, 408800, 6168100)):
    k = ("bm", name)
    if k not in _cache:
        d = gpd.read_file(os.path.join(V, "basemap", name), bbox=bbox); d["geometry"] = d.geometry.apply(to_plan); _cache[k] = d
    return _cache[k].copy()

C = dict(bg="#F9F3E7", land="#D7EBC6", outb="#E7DCC8", bld="#D3CABD", edge="#3A3842", pink="#DA71D7", dark="#14131A",
         green="#5EC46E", lgreen="#BFE3B4", yellow="#E9D68A", red="#D62828", dred="#B13840", orange="#E08A2B", purple="#6852A0",
         lilac="#A68CC6", blue="#4A74C9", lblue="#94ACD6", grey="#8B877F", lgrey="#C9C4BA", water="#8FD3E0", brown="#6B4A3A")
PT = 0.72                                                         # пикселей слайда -> пунктов (dpi = 100 * S)
S = 2

class Map:
    def __init__(self, key, w, h, margin=46, center=None, extent=None):
        self.key, self.w, self.h = key, w, h
        tb = L(K, "boundary").geometry.iloc[0]; x0, y0, x1, y1 = tb.bounds
        cx, cy = center or ((x0 + x1) / 2, (y0 + y1) / 2)
        if extent: sx = extent
        else: sx = max(x1 - x0 + 2 * margin, (y1 - y0 + 2 * margin) * w / h)
        sy = sx * h / w; self.cx, self.cy, self.sx, self.sy = cx, cy, sx, sy; self.mpp = sx / w
        self.fig = plt.figure(figsize=(w / 100, h / 100), dpi=100 * S); self.ax = self.fig.add_axes([0, 0, 1, 1]); self.ax.set_axis_off()
        self.ax.set_xlim(cx - sx / 2, cx + sx / 2); self.ax.set_ylim(cy - sy / 2, cy + sy / 2); self.ax.set_aspect("equal")
        self.fig.patch.set_facecolor(C["bg"]); self.ax.set_facecolor(C["bg"]); self.legend = []; self.z = 1; self.marks = {}
        self.frame = box(cx - sx / 2, cy - sy / 2, cx + sx / 2, cy + sy / 2)
    def px(self, x, y):                                        # план -> пиксели слайда
        return (x - (self.cx - self.sx / 2)) / self.mpp, (self.cy + self.sy / 2 - y) / self.mpp
    def lw(self, px): return px * PT
    # ---------- примитивы
    def poly(self, geoms, fc, ec="none", lw=0, alpha=1, hatch=None, z=None, ls="-"):
        z = z or self.z; self.z += 0.01
        for g in geoms if isinstance(geoms, (list, gpd.GeoSeries, pd.Series)) else [geoms]:
            if g is None or g.is_empty: continue
            for p in (g.geoms if hasattr(g, "geoms") else [g]):
                if p.geom_type != "Polygon": continue
                verts, codes = [], []
                for ring in [p.exterior] + list(p.interiors):
                    cs = list(ring.coords); verts += cs; codes += [Path.MOVETO] + [Path.LINETO] * (len(cs) - 2) + [Path.CLOSEPOLY]
                pp = PathPatch(Path(verts, codes), facecolor=fc, edgecolor=ec, lw=self.lw(lw), alpha=alpha, zorder=z, hatch=hatch, ls=ls)
                if hatch: pp.set_edgecolor(ec if ec != "none" else fc); plt.rcParams["hatch.linewidth"] = 0.9
                self.ax.add_patch(pp)
    def line(self, geoms, color, lw=1.5, ls="-", z=None, alpha=1, cap="round"):
        z = z or self.z; self.z += 0.01
        for g in geoms if isinstance(geoms, (list, gpd.GeoSeries, pd.Series)) else [geoms]:
            if g is None or g.is_empty: continue
            for l in (g.geoms if hasattr(g, "geoms") else [g]):
                if l.geom_type == "Polygon": l = l.exterior
                if not hasattr(l, "coords"): continue
                xy = np.array(l.coords)
                self.ax.plot(xy[:, 0], xy[:, 1], color=color, lw=self.lw(lw), ls=ls, zorder=z, alpha=alpha, solid_capstyle=cap, dash_capstyle="butt")
    def pts(self, xy, color, size=10, marker="o", ec="white", ew=1.2, z=None):
        z = z or self.z + 5; self.z += 0.01
        xy = np.array(xy).reshape(-1, 2)
        self.ax.scatter(xy[:, 0], xy[:, 1], s=(size * PT * S / 1.0) ** 2 / 4, c=color, marker=marker, edgecolors=ec, linewidths=self.lw(ew), zorder=z)
    def text(self, x, y, s, size=14, color=None, weight="regular", ha="center", va="center", rot=0, halo=True, z=40):
        t = self.ax.text(x, y, s, fontsize=size * PT, color=color or C["dark"], fontweight=weight, ha=ha, va=va, rotation=rot, zorder=z,
                         rotation_mode="anchor", linespacing=1.0)
        if halo: t.set_path_effects([pe.withStroke(linewidth=self.lw(3.2), foreground=C["bg"] if halo is True else halo)])
        return t
    # ---------- общая подложка
    def base(self, bld=True, cells="thin", numbers=False, numsize=11, street=True, ctx=True):
        fr = self.frame.buffer(30)
        lu = LB("Moscow_landuse.gpkg"); lu = lu[lu.fclass.isin(["forest", "park", "grass", "meadow", "scrub", "recreation_ground", "cemetery", "allotments"])]
        self.poly([g.intersection(fr) for g in lu.geometry], C["land"], z=0.2)
        self.poly(list(LB("Moscow_water.gpkg").geometry), C["water"], z=0.25)
        ob = LB("Moscow_building.gpkg"); tb = L(K, "boundary").geometry.iloc[0]
        self.poly([g for g in ob.geometry if not g.centroid.within(tb)], C["outb"], z=0.3)
        if ctx:
            cl = LB("dwg_context_lines.gpkg"); cl = cl[cl.intersects(fr)]
            self.line(list(cl.geometry), "#FFFFFF", 1.0, z=0.4)
        self.boundary_z = 30
        self.poly(tb, "none", C["pink"], 2.6, z=30, ls=(0, (5, 3)))
        if cells:
            c = L(K, "cells")
            self.line([g.exterior for g in c.geometry], "#5D5A63", 0.6 if cells == "thin" else 1.0, z=8)
        if bld: self.poly(list(L(K, "buildings").geometry), C["bld"], C["edge"], 0.5, z=10)
        if numbers:
            for r in L(K, "cells").itertuples():
                p = r.geometry.representative_point(); self.text(p.x, p.y, str(r.num), numsize, "#4B4852", "medium", z=25)
        if street: self.streets()
    def streets(self, size=17):
        tb = L(K, "boundary").geometry.iloc[0]; ring = tb.exterior
        def at(x=None, y=None):
            ln = LineString([(x, -900), (x, 900)]) if x is not None else LineString([(-900, y), (900, y)])
            return [(p.x, p.y) for p in ln.intersection(ring).geoms]
        top = max(at(x=0), key=lambda p: p[1]); bot = min(at(x=0), key=lambda p: p[1])
        lef = min(at(y=0), key=lambda p: p[0]); rig = max(at(y=0), key=lambda p: p[0])
        a1, a2 = max(at(x=-200), key=lambda p: p[1]), max(at(x=200), key=lambda p: p[1]); ang = math.degrees(math.atan2(a2[1] - a1[1], a2[0] - a1[0]))
        off = 14 * self.mpp + 6
        for (x, y), s, r in (((top[0], top[1] + off), "ул. Генерала Антонова", ang), ((bot[0], bot[1] - off), "ул. Миклухо-Маклая", 0),
                             ((lef[0] - off, lef[1]), "Профсоюзная ул.", 90), ((rig[0] + off, rig[1]), "ул. Введенского", -90)):
            self.text(x, y, s, size, "#3A3842", "medium", rot=r, z=45)
    def add_legend(self, label, kind, **sym):
        self.legend.append(dict(label=label, sym=dict(kind=kind, **sym)))
    def save(self, extra=None):
        fn = os.path.join(OUT, self.key + ".png"); self.fig.savefig(fn, dpi=100 * S, facecolor=C["bg"]); plt.close(self.fig)
        meta = json.load(open(META, encoding="utf-8")) if os.path.exists(META) else {}
        meta[self.key] = dict(w=self.w, h=self.h, mpp=self.mpp, cx=self.cx, cy=self.cy, sx=self.sx, sy=self.sy, legend=self.legend, marks=self.marks, **(extra or {}))
        json.dump(meta, open(META, "w", encoding="utf-8"), ensure_ascii=False, indent=1); print(self.key, round(self.mpp, 3), "м/px", len(self.legend), "в легенде")

# ======================================================================= карты
def cells_in(): c = L(P, "viol_cells"); return c

def clusters(gdf, d=28):
    if not len(gdf): return []
    zones = unary_union(gdf.buffer(d / 2)); zones = list(getattr(zones, "geoms", [zones])); out = []
    for z in zones:
        s = gdf[gdf.within(z)]
        if len(s): out.append((s.geometry.x.mean(), s.geometry.y.mean(), s))
    return out
def net_all(m, color="#B9B4AA", lw=0.8):
    n = L(A, "network"); m.line(list(n.geometry), color, lw, z=9); return n
