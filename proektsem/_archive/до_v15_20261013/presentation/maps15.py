# Карты v14 для презентации (matplotlib, без QGIS): стиль карт команды (кремовый фон, белые линии чертежа, зелень OSM,
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
H = os.path.dirname(os.path.abspath(__file__)); PR = os.path.join(H, ".."); V = os.path.join(PR, "vector")
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
def m_cells(key="c_cells", w=1480, h=888):
    m = Map(key, w, h); m.base(numbers=False)
    c = L(K, "cells"); ex = L(K, "cells_excluded")
    an = c[c.in_scope == 1]; out_ = c[c.num.isin([14, 28])]; rest = c[(c.in_scope != 1) & ~c.num.isin([14, 28])]
    m.poly(list(an.geometry), "#CFE8C8", C["edge"], 0.8, z=5)
    m.poly(list(out_.geometry), "#F0D9A8", C["edge"], 0.8, z=5, hatch="////"); m.poly(list(rest.geometry), "#E6E2DA", C["edge"], 0.8, z=5)
    m.poly(list(ex.geometry), "#E6E2DA", C["grey"], 0.8, z=6, hatch="xx")
    for r in c.itertuples():
        p = r.geometry.representative_point(); m.text(p.x, p.y, str(r.num), 15, C["dark"], "semibold" if r.in_scope == 1 else "regular", z=25)
    m.add_legend(f"дворы в анализе — {len(an)}", "fill", fill="#CFE8C8", fa=1)
    m.add_legend("вне зафиксированных границ (14, 28), п. 1.3", "fill", fill="#F0D9A8", fa=1, hatch=True)
    m.add_legend(f"краевые полосы у улиц — {len(rest)}", "fill", fill="#E6E2DA", fa=1)
    m.add_legend("участки школ и детсадов", "fill", fill="#C9C4BA", fa=1, hatch=True)
    m.save()

ENT = {"арка": "square", "ворота": "diamond", "калитка": "octagon", "разрыв в застройке": "circle", "въезд": "pentagon",
       "разрыв в насаждениях": "hexagon", "не зафиксирован": "cross_fill"}
MK = {"square": "s", "diamond": "D", "octagon": "8", "circle": "o", "pentagon": "p", "hexagon": "h", "cross_fill": "P", "triangle": "^"}
def m_entries(key="c_entries", w=1280, h=720):
    m = Map(key, w, h); m.base()
    f = L(K, "fences"); hi = f[f.podtip.str.contains("высокое", na=False)]
    m.line(list(hi.geometry), C["purple"], 1.6, z=12); m.line(list(f.drop(hi.index).geometry), C["lilac"], 1.0, z=12, ls=(0, (2, 2)))
    e = L(K, "entries_territory"); e["t"] = e.podtip.str.replace("Вход — ", "")
    oe = L(K, "open_edge"); m.line(list(oe.geometry), C["red"], 3.0, z=13, ls=(0, (2, 2)))
    for t, sh in ENT.items():
        d = e[e.t == t]
        for org, col in (("организован", "#2A9D4B"), ("не организован", C["red"])):
            dd = d[d.fix_class == org]
            if len(dd): m.pts([(p.x, p.y) for p in dd.geometry], col, 15, MK[sh], "white", 1.4)
    m.add_legend(f"организован — {int((e.fix_class == 'организован').sum())}", "marker", fill="#2a9d4b", shape="circle")
    m.add_legend(f"не организован — {int((e.fix_class != 'организован').sum())}", "marker", fill="#d62828", shape="circle")
    for t, sh in ENT.items(): m.add_legend(f"{t} — {int((e.t == t).sum())}", "marker", fill="#8b877f", shape=sh)
    m.add_legend("высокое ограждение", "line", stroke=C["purple"], sw=0.5)
    m.add_legend(f"открытый фронт: войти можно где угодно — {oe.length.sum():.0f} м", "line", stroke=C["red"], sw=0.6, dash=True)
    m.save()

def m_comfort(key="c_comfort", w=1280, h=720):
    m = Map(key, w, h); m.base(cells=False)
    v = cells_in(); c = L(K, "cells"); rest = c[~c.num.isin(v.num)]
    m.poly(list(rest.geometry), "#E6E2DA", C["edge"], 0.6, z=5)
    for r in v.itertuples():
        col = C["green"] if r.comfort_score >= 0.665 else (C["yellow"] if r.comfort_score >= 0.5 else "#E58F86")
        m.poly(r.geometry, col, C["edge"], 0.8, z=5, alpha=0.9)
        p = r.geometry.representative_point(); m.text(p.x, p.y, f"{r.num}\n{r.comfort_score:.2f}".replace(".", ","), 12, C["dark"], "medium", z=25)
    m.add_legend("комфортная, балл от 0,67", "fill", fill=C["green"], fa=1)
    m.add_legend("почти: 0,50–0,66", "fill", fill=C["yellow"], fa=1)
    m.add_legend("некомфортная, ниже 0,50", "fill", fill="#E58F86", fa=1)
    m.add_legend("вне анализа", "fill", fill="#E6E2DA", fa=1)
    m.save()

def clusters(gdf, d=28):
    if not len(gdf): return []
    zones = unary_union(gdf.buffer(d / 2)); zones = list(getattr(zones, "geoms", [zones])); out = []
    for z in zones:
        s = gdf[gdf.within(z)]
        if len(s): out.append((s.geometry.x.mean(), s.geometry.y.mean(), s))
    return out
def m_buildings(key="c_wear", w=960, h=540):
    m = Map(key, w, h, margin=40); m.base(bld=False, street=False)
    b = L(K, "buildings"); w4 = L(P, "p1_4_wear")
    m.poly(list(b.geometry), C["bld"], C["edge"], 0.4, z=10)
    hi = w4.geometry; m.poly(list(hi), C["dred"], C["edge"], 0.5, z=11)
    for r in w4.itertuples():
        p = r.geometry.representative_point(); m.text(p.x, p.y, f"{round(r.wear * 100)}%", 11, "white", "semibold", halo=C["dred"], z=26)
    m.add_legend(f"износ 40 % и больше — {len(w4)}", "fill", fill=C["dred"], fa=1); m.add_legend("износ меньше 40 % или нет данных", "fill", fill=C["bld"], fa=1)
    m.streets(14); m.save()
    m = Map("c_business", w, h, margin=40); m.base(street=False)
    bz = L(K, "business"); col = {"благоприятный": C["green"], "индифферентный": C["grey"], "опасный": C["red"]}
    for x, y, s in clusters(bz):
        # кластер — «соты» из точек: каждая точка — один объект своего цвета, сложены плотной спиралью вокруг центра
        n = len(s); d = 9 * m.mpp; pts_ = [(0, 0)]; ring_ = 1
        while len(pts_) < n:
            for k in range(6 * ring_):
                a_ = 2 * math.pi * k / (6 * ring_); pts_.append((ring_ * d * math.cos(a_), ring_ * d * math.sin(a_)))
            ring_ += 1
        for (dx, dy), dg in zip(pts_, s.sort_values("danger").danger):
            m.ax.add_patch(Circle((x + dx, y + dy), 4.2 * m.mpp, facecolor=col[dg], edgecolor="white", lw=m.lw(0.8), zorder=30))
    for k, cc in col.items(): m.add_legend(f"{k}: {int((bz.danger == k).sum())}", "marker", fill=cc, shape="circle")
    m.add_legend("одна точка — один объект; группа — кластер", "marker", fill="#8b877f", shape="circle")
    m.streets(14); m.save()

def m_green(key="c_green", w=1280, h=720):
    m = Map(key, w, h); m.base()
    g = L(K, "green"); pk = L(K, "parking"); lz = L(K, "loading_zones")
    m.poly(list(g[g["type"] == "трава"].geometry), "#CFE7BE", z=3); m.poly(list(g[g["type"] == "деревья"].geometry), "#9ACD8A", z=3)
    for kind, col in (("открытая", C["lblue"]), ("гаражи", C["lilac"]), ("здание-паркинг", C["purple"])):
        d = pk[pk.kind.str.contains(kind, na=False)]; m.poly(list(d.geometry), col, C["edge"], 0.4, z=11)
    m.poly(list(lz.geometry), C["orange"], C["edge"], 0.4, z=12)
    m.add_legend("газон", "fill", fill="#CFE7BE", fa=1); m.add_legend("деревья", "fill", fill="#9ACD8A", fa=1)
    m.add_legend("открытая стоянка", "fill", fill=C["lblue"], fa=1); m.add_legend("гаражи", "fill", fill=C["lilac"], fa=1)
    m.add_legend("многоуровневый паркинг", "fill", fill=C["purple"], fa=1); m.add_legend("зона загрузки", "fill", fill=C["orange"], fa=1)
    m.save()

def m_danger(key="c_danger", w=1280, h=720):
    m = Map(key, w, h); m.base()
    lz = L(K, "loading_zones"); m.poly(list(lz.geometry), C["orange"], C["edge"], 0.4, z=12)
    gb = L(K, "garbage"); bz = L(K, "business"); pg = L(K, "playgrounds")
    m.poly(list(pg.geometry), "#D9E6F2", "#6B8BB0", 0.8, z=9)
    dang = bz[(bz.danger == "опасный") & (bz.isolation == "открытый")]
    m.pts([(p.x, p.y) for p in gb.geometry], C["dark"], 13, "s", "white", 1.2)
    m.pts([(p.x, p.y) for p in dang.geometry], C["red"], 17, "P", "white", 1.2)
    fav = bz[(bz.danger == "благоприятный")]; m.pts([(p.x, p.y) for p in fav.geometry], C["green"], 10, "o", "white", 1)
    m.add_legend(f"мусорная площадка — {len(gb)}", "marker", fill="#16161c", shape="square")
    m.add_legend(f"опасный открытый бизнес — {len(dang)}", "marker", fill="#d62828", shape="cross_fill")
    m.add_legend(f"благоприятный бизнес — {len(fav)}", "marker", fill="#2a9d4b", shape="circle")
    m.add_legend(f"зона загрузки — {len(lz)}", "fill", fill=C["orange"], fa=1); m.add_legend("площадки (для ориентира)", "fill", fill="#D9E6F2", fa=1, stroke="#6B8BB0")
    m.save()

def net_all(m, color="#B9B4AA", lw=0.8):
    n = L(A, "network"); m.line(list(n.geometry), color, lw, z=9); return n
def m_networks(w=960, h=540):
    m = Map("c_ped", w, h, margin=40); m.base(street=False); n = net_all(m)
    for g, c, lw in (("один путь", "#8B877F", 1.4), ("низкая", C["orange"], 2.8), ("высокая", C["dred"], 4.2)): m.line(list(n[n.group == g].geometry), c, lw, z=14)
    for g, c, lw, lab in (("высокая", C["dred"], 4.2, "4 пути и больше"), ("низкая", C["orange"], 2.8, "2–3 пути"), ("один путь", "#8B877F", 1.4, "один путь")):
        m.add_legend(f"{lab} — {n[n.group == g].length.sum() / 1000:.1f} км".replace(".", ","), "line", stroke=c, sw=lw / 4)
    m.add_legend("прочие дорожки и проезды", "line", stroke="#B9B4AA", sw=0.25)
    m.streets(14); m.save()
    m = Map("c_veh", w, h, margin=40); m.base(street=False); n = net_all(m)
    for g, c, lw in (("низкая", C["lblue"], 2.8), ("высокая", C["purple"], 4.2)): m.line(list(n[n.vgroup == g].geometry), c, lw, z=14)
    for g, c, lw, lab in (("высокая", C["purple"], 4.2, "4 пути и больше"), ("низкая", C["lblue"], 2.8, "2–3 пути")):
        m.add_legend(f"{lab} — {n[n.vgroup == g].length.sum() / 1000:.1f} км".replace(".", ","), "line", stroke=c, sw=lw / 4)
    m.add_legend("прочие проезды и дорожки", "line", stroke="#B9B4AA", sw=0.25)
    m.streets(14); m.save()

def m_combined(key="c_combined", w=1480, h=888):
    m = Map(key, w, h); m.base(); n = net_all(m)
    road = n[n["type"] == "проезд"]; m.line(list(road.geometry), "#9C978E", 2.2, z=10)
    used = n[n.ped >= 1]
    for rz, c in (("отдельно от проезда", C["green"]), ("по тротуару", C["blue"]), ("по проезжей части", C["red"])):
        m.line(list(used[used.razdel == rz].geometry), c, 2.6, z=14)
    cm = L(P, "p2_3_combined"); m.line(list(cm.geometry), C["orange"], 7.5, z=13, alpha=0.9)
    m.add_legend(f"совмещение потоков — {cm.length.sum():.0f} м", "line", stroke=C["orange"], sw=1.5)
    for rz, c in (("отдельно от проезда", C["green"]), ("по тротуару", C["blue"]), ("по проезжей части", C["red"])):
        m.add_legend(f"путь {rz} — {used[used.razdel == rz].length.sum() / 1000:.1f} км".replace(".", ","), "line", stroke=c, sw=0.6)
    m.add_legend("проезды", "line", stroke="#9C978E", sw=0.45)
    m.save()

def m_flows(key="c_flows", w=1480, h=888):
    m = Map(key, w, h); m.base(); n = net_all(m, "#C9C4BA", 0.7)
    hi = n[n.lgroup == "высокая"]; lo = n[n.lgroup == "низкая"]
    m.line(list(lo.geometry), "#E3A6E1", 1.6, z=12); m.line(list(hi.geometry), C["pink"], 4.5, z=12)
    m.add_legend(f"главные пешеходные оси (20+ путей) — {hi.length.sum() / 1000:.1f} км".replace(".", ","), "line", stroke=C["pink"], sw=1.1)
    m.add_legend(f"прочие используемые пути — {lo.length.sum() / 1000:.1f} км".replace(".", ","), "line", stroke="#E3A6E1", sw=0.4)
    fl = L(os.path.join(V, "analiz_v13.gpkg"), "flows"); col = {"высокий": C["dred"], "средний": C["orange"], "низкий": C["grey"]}
    for r in fl.sort_values("sat_human").itertuples():
        x, y = r.geometry.x, r.geometry.y; rad = (9 + 2.2 * math.sqrt(r.sat_human)) * m.mpp
        m.ax.add_patch(Circle((x, y), rad, facecolor=col[r.cls], edgecolor="white", lw=m.lw(1.5), zorder=32, alpha=0.95))
        m.text(x, y, str(r.id), 11 if r.sat_human < 20 else 13, "white", "semibold", halo=False, z=33)
        dx = 1 if x < m.cx else -1; m.text(x + dx * (rad + 4 * m.mpp), y, f"{r.sat_human}", 14, C["dark"], "bold", ha="left" if dx > 0 else "right", z=34)
        m.marks[f"flow{r.id}"] = m.px(x, y)
    mx, my = METRO_EXIT_PLAN; m.pts([(mx, my)], C["pink"], 22, "o", "white", 2); m.text(mx + 8, my + 10, "М", 13, "white", "bold", halo=False, z=50)
    m.ax.text(mx, my, "M", fontsize=12 * PT, color="white", fontweight="bold", ha="center", va="center", zorder=60)
    ax_, ay_ = MALL_CROSSING_PLAN; m.pts([(ax_, ay_ + 4)], C["purple"], 18, "s", "white", 2)
    m.text(mx + 16, my - 18, "выход метро", 14, C["dark"], "semibold", ha="left"); m.text(ax_, ay_ + 22, "переход к ТЦ", 14, C["dark"], "semibold")
    for k, cc in col.items(): m.add_legend(f"поток {k}", "marker", fill=cc, shape="circle")
    m.add_legend("номер точки в кружке, рядом — человек в час (суббота)", "marker", fill="#8b877f", shape="circle")
    m.save()

def m_control_zones(w=960, h=540):
    z = L(A, "control_zones")
    m = Map("c_ctl_pers", w, h, margin=40); m.base(street=False)
    m.poly(z[z["type"] == "ПЖ"].geometry.tolist(), "#BFE3B4", z=4); m.poly(z[z["type"] == "АЖ"].geometry.tolist(), "#5EC46E", z=5, alpha=0.85)
    m.add_legend("активный: фасады с подъездами, 30 м", "fill", fill="#5ec46e", fa=1); m.add_legend("пассивный: торцы и фасады без подъездов, 15 м", "fill", fill="#bfe3b4", fa=1)
    m.streets(14); m.save()
    m = Map("c_ctl_pub", w, h, margin=40); m.base(street=False)
    m.poly(z[z["type"] == "ПП"].geometry.tolist(), "#DDD3EE", z=4); m.poly(z[z["type"] == "АП"].geometry.tolist(), "#B19FD8", z=5, alpha=0.9)
    m.add_legend("активный: людные пути, метро, переход, входы в организации, 15 м", "fill", fill="#B19FD8", fa=1)
    m.add_legend("пассивный: пути 2–3, участки школ, 7,5 м", "fill", fill="#DDD3EE", fa=1)
    m.streets(14); m.save()

def m_controllability(key="c_control", w=1280, h=720):
    m = Map(key, w, h); m.base(cells="thin")
    c = L(A, "control"); cp = L(A, "competition")
    for t, col in (("контролируемая", "#7DCB86"), ("частично контролируемая", "#EBDC9C"), ("неконтролируемая", "#E8A29B")): m.poly(c[c["type"] == t].geometry.tolist(), col, z=4)
    m.poly(cp.geometry.tolist(), "#A68CC6", z=5, alpha=0.9)
    mt = L(A, "metro"); m.poly([mt.geometry.iloc[0]], "none", C["dark"], 1.4, z=20, ls=(0, (3, 2)))
    a = c.groupby("type").area.sum(); t = a.sum()
    for k, col in (("контролируемая", "#7DCB86"), ("частично контролируемая", "#EBDC9C"), ("неконтролируемая", "#E8A29B")):
        m.add_legend(f"{k} — {100 * a[k] / t:.0f} %", "fill", fill=col, fa=1)
    m.add_legend(f"конкуренция активных контролей — {cp.area.sum() / 1e4:.1f} га".replace(".", ","), "fill", fill="#A68CC6", fa=1)
    m.add_legend("площадь у выхода метро", "fill", fill="#ffffff", fa=0, stroke=C["dark"], dash=True)
    m.save()

def m_playgrounds(key="c_pg", w=1280, h=720):
    m = Map(key, w, h); m.base()
    pz = L(A, "playgrounds_zones"); pod = L(K, "entrances_buildings")
    m.poly([unary_union(pod.buffer(100))], "#F2EBDD", z=2, alpha=0.6); m.poly([unary_union(pod.buffer(30))], "#E7DCC4", z=3, alpha=0.8)
    for zn, col in (("ближняя", C["orange"]), ("средняя", C["green"]), ("периферийная", C["blue"])):
        m.poly(pz[pz.zone == zn].geometry.tolist(), col, C["edge"], 0.6, z=12)
    pr = pz[pz.problem.notna()]; m.poly(pr.geometry.tolist(), "none", C["red"], 3, z=13)
    m.pts([(p.x, p.y) for p in pod.geometry], C["dark"], 6, "o", "white", 0.6)
    m.add_legend(f"площадка в ближней зоне (до 30 м) — {int((pz.zone == 'ближняя').sum())}", "fill", fill=C["orange"], fa=1)
    m.add_legend(f"в средней зоне (30–100 м) — {int((pz.zone == 'средняя').sum())}", "fill", fill=C["green"], fa=1)
    m.add_legend(f"ближняя вне активного контроля (п. 3.3) — {len(pr)}", "fill", fill="#ffffff", fa=0, stroke=C["red"])
    m.add_legend("подъезд", "marker", fill="#16161c", shape="circle")
    m.save()

def m_osv(key="c_osv", w=1280, h=720):
    m = Map(key, w, h); m.base()
    o = L(A, "osvoennost")
    for t, col in (("освоенная", "#7DCB86"), ("частично освоенная", "#EBDC9C"), ("неосвоенная", C["dred"]), ("не оценивается", "#E6E2DA")):
        m.poly(o[o.cls == t].geometry.tolist(), col, "#FFFFFF", 0.4, z=4)
    pg = L(K, "playgrounds"); m.poly(pg.geometry.tolist(), "none", C["dark"], 1.0, z=6)
    a = o[o.cls != "не оценивается"].groupby("cls").area.sum(); t = a.sum()
    for k, col in (("освоенная", "#7DCB86"), ("частично освоенная", "#EBDC9C"), ("неосвоенная", C["dred"])): m.add_legend(f"{k} — {100 * a[k] / t:.0f} %", "fill", fill=col, fa=1)
    m.add_legend("не оценивается (школы, детсады, вне ячеек)", "fill", fill="#E6E2DA", fa=1); m.add_legend("площадки", "fill", fill="#ffffff", fa=0, stroke=C["dark"])
    m.save()

def m_ctl_osv(key="c_ctl_osv", w=1280, h=720):
    m = Map(key, w, h); m.base()
    o = L(A, "osvoennost"); o = o[o.cls != "не оценивается"].copy(); c = L(A, "control")
    cc = o.geometry.centroid
    def cls_of(z): return cc.within(unary_union(c[c["type"] == z].geometry))
    o["ctl"] = np.select([cls_of("контролируемая"), cls_of("частично контролируемая")], ["к", "ч"], default="н")
    cat = {("освоенная", "к"): ("#3FA35A", "освоено, под контролем"), ("освоенная", "ч"): ("#8FCB8F", "освоено, присмотр слабый"),
           ("освоенная", "н"): ("#CFE7C4", "освоено без присмотра"), ("частично освоенная", "к"): ("#E9D68A", "частично освоено"),
           ("частично освоенная", "ч"): ("#E9D68A", "частично освоено"), ("частично освоенная", "н"): ("#F2E6B8", "частично, без присмотра"),
           ("неосвоенная", "к"): ("#E8A29B", "заброшено при контроле"), ("неосвоенная", "ч"): ("#D9786E", "заброшено, присмотр слабый"),
           ("неосвоенная", "н"): (C["dred"], "заброшено и без контроля")}
    seen = {}
    for (cl, ct), (col, lab) in cat.items():
        d = o[(o.cls == cl) & (o.ctl == ct)]
        if len(d): m.poly(d.geometry.tolist(), col, "#FFFFFF", 0.4, z=4); seen.setdefault(lab, (col, d.area.sum()))
    for lab, (col, a_) in seen.items(): m.add_legend(f"{lab} — {a_ / 1e4:.1f} га".replace(".", ","), "fill", fill=col, fa=1)
    m.save()

# ---------------- проблемы
def m_prob1(key="c_p1", w=1480, h=888):
    m = Map(key, w, h); m.base(cells=False)
    v = cells_in(); c = L(K, "cells"); p13 = L(P, "p1_3_cells"); rest = c[~c.num.isin(v.num) & ~c.num.isin(p13.num)]
    m.poly(rest.geometry.tolist(), "#EEEAE2", "#9C978E", 0.5, z=4)
    ok = v[v.p1_1 == 0]; m.poly(ok.geometry.tolist(), "#FFFFFF", "#9C978E", 0.6, z=4)
    p11 = v[v.p1_1 == 1]; m.poly(p11.geometry.tolist(), "#F4C9C4", "#9C978E", 0.6, z=5)
    m.poly(p13.geometry.tolist(), "#F3EEE4", "#B9B2A6", 0.5, z=6, hatch="//")
    oe = L(K, "open_edge"); m.line(list(oe.geometry), C["red"], 3.0, z=13, ls=(0, (2, 2)))
    for r in v.itertuples():
        p = r.geometry.representative_point(); m.text(p.x, p.y, str(r.num), 13, C["dark"], "semibold" if r.p1_1 else "regular", z=25)
    w4 = L(P, "p1_4_wear"); m.poly(w4.geometry.tolist(), C["dred"], C["edge"], 0.5, z=12)
    nd = L(P, "p1_2_nodes"); m.pts([(p.x, p.y) for p in nd.geometry], C["red"], 18, "^", "white", 1.6)
    m.add_legend(f"1.1 неудачная форма двора (комфорт ниже 0,67) — {len(p11)} ячеек", "fill", fill="#F4C9C4", fa=1)
    m.add_legend(f"1.2 неорганизованный вход — {len(nd)} (в {int(v.p1_2.sum())} ячейках)", "marker", fill="#d62828", shape="triangle")
    m.add_legend("1.2 открытый фронт без фиксации входа", "line", stroke=C["red"], sw=0.6, dash=True)
    m.add_legend(f"1.3 территории вне зафиксированных границ дворов — {len(p13)} участков", "fill", fill="#F3EEE4", fa=1, hatch=True, stroke="#B9B2A6")
    m.add_legend(f"1.4 здание с износом от 40 % — {len(w4)} (рядом с {int(v.p1_4.sum())} ячейками)", "fill", fill=C["dred"], fa=1)
    m.save()

def m_prob2(key="c_p2", w=1480, h=888):
    m = Map(key, w, h); m.base(); v = cells_in()
    n = L(A, "network"); road = n[n["type"] == "проезд"]; m.line(list(road.geometry), "#AAA49A", 2.4, z=9)
    lz = L(K, "loading_zones"); m.poly(lz.geometry.tolist(), C["purple"], C["edge"], 0.4, z=12)
    cm = L(P, "p2_3_combined"); m.line(list(cm.geometry), C["orange"], 7, z=13)
    gb = L(K, "garbage"); bz = L(K, "business"); dang = bz[(bz.danger == "опасный") & (bz.isolation == "открытый")]
    m.pts([(p.x, p.y) for p in pd.concat([gb.geometry, dang.geometry])], C["dark"], 16, "X", "white", 1.4)
    for r in v[(v.p2_1 + v.p2_2 + v.p2_3) > 0].itertuples():
        p = r.geometry.representative_point(); m.text(p.x, p.y, str(r.num), 13, C["dark"], "semibold", z=25)
    m.add_legend(f"2.1 загрузка с заездом грузовиков — {len(lz)} зон, {int(v.p2_1.sum())} ячеек", "fill", fill=C["purple"], fa=1)
    m.add_legend(f"2.2 опасный открытый объект — {len(gb) + len(dang)}, {int(v.p2_2.sum())} ячеек", "marker", fill="#16161c", shape="cross_fill")
    m.add_legend(f"2.3 пешеходы и машины на одном проезде — {cm.length.sum():.0f} м, {int(v.p2_3.sum())} ячеек", "line", stroke=C["orange"], sw=1.4)
    m.add_legend("внутриквартальные проезды", "line", stroke="#AAA49A", sw=0.5)
    m.save()

def m_prob3(key="c_p3", w=1480, h=888):
    m = Map(key, w, h); m.base(); v = cells_in(); SC = unary_union(v.geometry)
    un = L(P, "p3_4_uncontrolled"); cp = L(P, "p3_4_competition"); ab = L(P, "p3_4_abandoned")
    m.poly(un.geometry.tolist(), "#F2C6C0", z=4); m.poly(cp.geometry.tolist(), "#B9A3D9", z=5); m.poly(ab.geometry.tolist(), C["dred"], z=6)
    tr = L(os.path.join(V, "analiz_v13.gpkg"), "transit"); cz = L(A, "control_zones")
    RES = unary_union(cz[cz["type"].isin(["АЖ", "ПЖ"])].geometry); TRH = unary_union(tr[tr.cls == "высокая"].geometry).intersection(RES).intersection(SC)
    m.line([TRH], C["dark"], 3.0, z=14, ls=(0, (3, 1.5)))
    pl = L(P, "p3_3_places"); m.poly(pl.geometry.tolist(), C["yellow"], C["red"], 2.4, z=15)
    bz = L(K, "business"); serv = bz[bz.function == "обслуживающий"]; TRP = unary_union(tr[(tr.cls == "высокая") & (tr["mode"] == "пешеходный")].geometry)
    s32 = serv[serv.distance(TRP) <= 15]; s32 = s32[s32.geometry.apply(lambda p: SC.distance(p) <= 6)]
    m.pts([(p.x, p.y) for p in s32.geometry], C["blue"], 16, "D", "white", 1.4)
    for r in v[(v.p3_1 + v.p3_2 + v.p3_3 + v.p3_4) > 0].itertuples():
        p = r.geometry.representative_point(); m.text(p.x, p.y, str(r.num), 13, C["dark"], "semibold", z=25)
    m.add_legend(f"3.1 транзит под окнами — {TRH.length:.0f} м, {int(v.p3_1.sum())} ячеек", "line", stroke=C["dark"], sw=0.6, dash=True)
    m.add_legend(f"3.2 сервис с внешним транзитом — {int(v.p3_2.sum())} ячейка", "marker", fill=C["blue"], shape="diamond")
    m.add_legend(f"3.3 площадка без нужного контроля — {len(pl)}", "fill", fill=C["yellow"], fa=1, stroke=C["red"])
    m.add_legend(f"3.4 неконтролируемая территория", "fill", fill="#F2C6C0", fa=1)
    m.add_legend(f"3.4 конкуренция активных контролей", "fill", fill="#B9A3D9", fa=1)
    m.add_legend(f"3.4 заброшенная территория", "fill", fill=C["dred"], fa=1)
    m.save()

def m_score(key="c_score", w=1280, h=720):
    m = Map(key, w, h); m.base(cells=False); v = cells_in(); c = L(K, "cells")
    m.poly(c[~c.num.isin(v.num)].geometry.tolist(), "#EEEAE2", "#9C978E", 0.5, z=4)
    col = {"высокая": "#E0675E", "средняя": "#EBCB72", "низкая": "#A9D9A0"}
    for r in v.itertuples():
        m.poly(r.geometry, col[r.cls], C["edge"], 0.7, z=5)
        p = r.geometry.representative_point(); m.text(p.x, p.y, f"{r.num}\n{r.score}", 13, C["dark"], "semibold" if r.cls == "высокая" else "regular", z=25)
        m.marks[f"cell{r.num}"] = m.px(p.x, p.y)
    for k, lab in (("высокая", "высокий счёт, 6+"), ("средняя", "средний, 4–5"), ("низкая", "низкий, 0–3")):
        m.add_legend(f"{lab} — {int((v.cls == k).sum())}", "fill", fill=col[k], fa=1)
    m.add_legend("номер ячейки / число нарушенных пунктов", "fill", fill="#ffffff", fa=1, stroke=C["edge"])
    m.save()

def m_final(key="c_final", w=1180, h=740):
    """Итоговая схема в духе прошлогоднего примера: сгруппированные проблемы, ячейки-лидеры обведены."""
    m = Map(key, w, h, margin=40); m.base(cells="thin"); v = cells_in()
    for cl_, col_ in (("средняя", "#F5EBC8"), ("высокая", "#F3C9C3")): m.poly(v[v.cls == cl_].geometry.tolist(), col_, z=2.5)
    un = L(P, "p3_4_uncontrolled"); m.poly(un.geometry.tolist(), "none", "#C98B84", 0.6, z=3, hatch="....")
    cp = L(P, "p3_4_competition"); m.poly(cp.geometry.tolist(), "#C9B7E3", z=4)
    ab = L(P, "p3_4_abandoned"); m.poly(ab.geometry.tolist(), C["dred"], z=5, hatch="////")
    w4 = L(P, "p1_4_wear"); m.poly(w4.geometry.tolist(), C["dred"], C["edge"], 0.5, z=12)
    lz = L(K, "loading_zones"); m.poly(lz.geometry.tolist(), C["purple"], z=12)
    cm = L(P, "p2_3_combined"); m.line(list(cm.geometry), C["orange"], 5, z=13)
    nd = L(P, "p1_2_nodes"); m.pts([(p.x, p.y) for p in nd.geometry], C["red"], 14, "^", "white", 1.3)
    pl = L(P, "p3_3_places"); m.poly(pl.geometry.tolist(), C["yellow"], C["red"], 2, z=15)
    gb = L(K, "garbage"); m.pts([(p.x, p.y) for p in gb.geometry], C["dark"], 12, "X", "white", 1)
    top = v[v.score >= 5]
    for r in top.itertuples():
        m.poly(r.geometry, "none", C["pink"], 3.2, z=20)
        p = r.geometry.representative_point(); m.text(p.x, p.y, str(r.num), 17, C["dark"], "bold", z=26, halo="white")
        m.marks[f"cell{r.num}"] = m.px(p.x, p.y)
    for nm, (x, y) in (("metro", METRO_EXIT_PLAN), ("mall", MALL_CROSSING_PLAN)): m.marks[nm] = m.px(x, y)
    m.add_legend("ячейка с 5+ нарушениями (обведена)", "fill", fill="#ffffff", fa=0, stroke=C["pink"])
    m.add_legend("высокий счёт (6+)", "fill", fill="#F3C9C3", fa=1); m.add_legend("средний счёт (4–5)", "fill", fill="#F5EBC8", fa=1)
    m.add_legend("неконтролируемая территория", "fill", fill="#ffffff", fa=1, stroke="#C98B84", hatch=True); m.add_legend("конкуренция активных контролей", "fill", fill="#C9B7E3", fa=1)
    m.add_legend("заброшенная территория", "fill", fill=C["dred"], fa=0.6, hatch=True)
    m.add_legend("изношенное здание (от 40 %)", "fill", fill=C["dred"], fa=1); m.add_legend("зона загрузки", "fill", fill=C["purple"], fa=1)
    m.add_legend("пешеходы на проезде", "line", stroke=C["orange"], sw=1.2); m.add_legend("неорганизованный вход", "marker", fill="#d62828", shape="triangle")
    m.add_legend("мусорная площадка", "marker", fill="#16161c", shape="cross_fill"); m.add_legend("площадка без нужного контроля", "fill", fill=C["yellow"], fa=1, stroke=C["red"])
    m.save()
    # фрагменты ячеек-лидеров для круглых врезок
    for r in top.itertuples():
        c0 = r.geometry.centroid; z = Map(f"c_zoom_{r.num}", 480, 480, center=(c0.x, c0.y), extent=230)
        z.base(cells="thin", street=False)
        z.poly(un.geometry.tolist(), "#F6D3CE", z=3); z.poly(cp.geometry.tolist(), "#C9B7E3", z=4); z.poly(ab.geometry.tolist(), C["dred"], z=5, hatch="////")
        z.poly(w4.geometry.tolist(), C["dred"], C["edge"], 0.5, z=12); z.poly(lz.geometry.tolist(), C["purple"], z=12)
        z.line(list(cm.geometry), C["orange"], 5, z=13); z.pts([(p.x, p.y) for p in nd.geometry], C["red"], 16, "^", "white", 1.3)
        z.pts([(p.x, p.y) for p in gb.geometry], C["dark"], 14, "X", "white", 1)
        z.poly(r.geometry, "none", C["pink"], 4, z=20); z.save()

def m_pre(key="c_pre", w=1480, h=888):
    m = Map(key, w, h); m.base(cells="thin")
    cf = L(P, "pre_comfort_cells"); m.poly(cf.geometry.tolist(), "#E3F1DC", "#5EC46E", 1.6, z=3)
    po = L(P, "pre_osv_ctl"); m.poly([unary_union(po.geometry).buffer(0.6).buffer(-0.6)], "#7DCB86", z=4)
    ax_ = L(P, "pre_axes"); m.line(list(ax_.geometry), C["dark"], 3.2, z=14)
    nd = L(P, "pre_nodes"); m.pts([(p.x, p.y) for p in nd.geometry], "#2A9D4B", 15, "^", "white", 1.4)
    fav = L(os.path.join(V, "problems_v13.gpkg"), "pre_fav_closed"); m.pts([(p.x, p.y) for p in fav.geometry], C["blue"], 14, "*", "white", 0.8)
    mt = L(A, "metro"); m.poly([mt.geometry.iloc[0]], "#F3D7F2", C["pink"], 1.4, z=6)
    m.add_legend(f"комфортный двор — {len(cf)}", "fill", fill="#E3F1DC", fa=1, stroke="#5EC46E")
    m.add_legend(f"освоено и под контролем — {po.area.sum() / 1e4:.1f} га".replace(".", ","), "fill", fill="#7DCB86", fa=1)
    m.add_legend("людная пешеходная ось (4+ путей)", "line", stroke=C["dark"], sw=0.7)
    m.add_legend(f"организованный вход — {len(nd)}", "marker", fill="#2a9d4b", shape="triangle")
    m.add_legend(f"благоприятный закрытый объект — {len(fav)}", "marker", fill=C["blue"], shape="circle")
    m.add_legend("площадь у выхода метро", "fill", fill="#F3D7F2", fa=1, stroke=C["pink"])
    m.save()

ALL = dict(cells=m_cells, entries=m_entries, comfort=m_comfort, buildings=m_buildings, green=m_green, danger=m_danger, networks=m_networks,
           combined=m_combined, flows=m_flows, ctlzones=m_control_zones, control=m_controllability, pg=m_playgrounds, osv=m_osv,
           ctlosv=m_ctl_osv, p1=m_prob1, p2=m_prob2, p3=m_prob3, score=m_score, final=m_final, pre=m_pre)
if __name__ == "__main__":
    for k in (sys.argv[1:] or ALL): ALL[k]()
