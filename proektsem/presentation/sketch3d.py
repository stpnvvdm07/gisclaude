# 3D-вид ячеек в духе SketchUp (как «Расчёты вертикальных пропорций» команды), данные v13.
# Ячейки — заливка по классу вертикальных пропорций (vert_koef = площадь фасадов / площадь ячейки), дома выдавлены:
# этажность x 3 м (условно), без паспорта — 1 этаж. На выходе:
#   maps/sketch_vert.png + maps/sketch_vert.json (координаты подписей в пикселях картинки) — для слайда;
#   ../vector/3d/cells_vert_v15.dae — модель Collada для SketchUp (метры, начало координат в центре территории).
import os, json, math
import numpy as np, geopandas as gpd, shapely
from shapely.geometry import Polygon, MultiPolygon
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.collections import PolyCollection, LineCollection

H = os.path.dirname(os.path.abspath(__file__)); V = os.path.join(H, "..", "vector")
FLOOR = 3.0; CENTER = (407724.5, 6167314.9); ROT = math.radians(26.75)
W, HPX = 1920, 896                                    # размер картинки на слайде, px
K_TILT = 0.80; EX = (0.32, 0.92)                      # сжатие плана по глубине и направление «вверх» для высоты
COL = {"Высокий": "#C35BC0", "Средний": "#E3A6E1", "Низкий": "#F4DDF3"}; OUT_C = "#E6E4E9"
ROOF, WALL_L, WALL_F, EDGE = "#FFFFFF", "#9E9CA6", "#C9C7CF", "#14131A"

cells = gpd.read_file(os.path.join(V, "konkovo_v15.gpkg"), layer="cells")
bld = gpd.read_file(os.path.join(V, "konkovo_v15.gpkg"), layer="buildings")
bnd = gpd.read_file(os.path.join(V, "konkovo_v15.gpkg"), layer="boundary")
viol = gpd.read_file(os.path.join(V, "problems_v15.gpkg"), layer="viol_cells")[["num", "in_scope"]]
cells = cells.drop(columns=["in_scope"], errors="ignore").merge(viol, on="num", how="left")
ctx = gpd.read_file(os.path.join(V, "basemap", "dwg_context_lines.gpkg"))
bld["h"] = bld["Этажность"].fillna(1).clip(lower=1) * FLOOR
bld["geometry"] = bld.geometry.simplify(1.0)          # без мелких уступов фасада — иначе стены идут полосками

def plan(x, y):
    """Мир (м) -> план, повёрнутый как карты команды (территория горизонтально)."""
    dx, dy = x - CENTER[0], y - CENTER[1]
    return dx * math.cos(ROT) - dy * math.sin(ROT), dx * math.sin(ROT) + dy * math.cos(ROT)
def proj(px, py, z=0.0):
    return px + EX[0] * z, py * K_TILT + EX[1] * z
def rings(g):
    for p in (g.geoms if isinstance(g, MultiPolygon) else [g]): yield p
def pts(ring): return [plan(x, y) for x, y in ring.coords]

# проверка ориентации: территория должна лечь горизонтально
bx = np.array(pts(next(rings(bnd.geometry.iloc[0])).exterior))
assert np.ptp(bx[:, 0]) > np.ptp(bx[:, 1]), "территория не горизонтальна — сменить знак ROT"

fig = plt.figure(figsize=(W / 100, HPX / 100), dpi=200); ax = fig.add_axes([0, 0, 1, 1]); ax.set_axis_off()
fig.patch.set_facecolor("#F9F3E7")
# подложка: линии чертежа
segs = []
for g in ctx.geometry:
    for ln in (g.geoms if g.geom_type.startswith("Multi") else [g]):
        segs.append([proj(*plan(x, y)) for x, y in ln.coords])
ax.add_collection(LineCollection(segs, colors="#FFFFFF", linewidths=1.4, zorder=1))
# ячейки
polys, cols = [], []
for r in cells.itertuples():
    for p in rings(r.geometry):
        polys.append([proj(*q) for q in pts(p.exterior)])
        cols.append(COL.get(r.vertical, OUT_C) if r.in_scope == 1 else OUT_C)
ax.add_collection(PolyCollection(polys, facecolors=cols, edgecolors=EDGE, linewidths=0.9, linestyles=(0, (4, 3)), zorder=2))
# граница территории
for p in rings(bnd.geometry.iloc[0]):
    q = [proj(*a) for a in pts(p.exterior)]; ax.plot(*zip(*q), color="#DA71D7", lw=2.6, ls=(0, (6, 4)), zorder=3)
# дома: стены, видимые со стороны камеры, затем крыша; дальние первыми
def depth(g): c = g.centroid; return plan(c.x, c.y)[1]
for r in sorted(bld.itertuples(), key=lambda r: -depth(r.geometry)):
    for p in rings(r.geometry):
        ring = pts(p.exterior); h = r.h
        if Polygon(ring).exterior.is_ccw is False: ring = ring[::-1]           # обход против часовой
        walls = []
        for (x1, y1), (x2, y2) in zip(ring[:-1], ring[1:]):
            nx, ny = (y2 - y1), -(x2 - x1)                                       # внешняя нормаль (обход CCW)
            sx, sy = nx, ny * K_TILT
            if sx * EX[0] + sy * EX[1] < 0:                                      # стена смотрит на камеру
                quad = [proj(x1, y1, 0), proj(x2, y2, 0), proj(x2, y2, h), proj(x1, y1, h)]
                walls.append((min(y1, y2), quad, WALL_F if abs(ny) > abs(nx) else WALL_L))
        for _, quad, c in sorted(walls, key=lambda w: -w[0]):
            ax.add_patch(plt.Polygon(quad, closed=True, fc=c, ec=EDGE, lw=0.5, zorder=4))
        ax.add_patch(plt.Polygon([proj(x, y, h) for x, y in ring], closed=True, fc=ROOF, ec=EDGE, lw=0.9, zorder=4))
# кадр
allp = np.array([q for pl in polys for q in pl]); x0, x1 = allp[:, 0].min(), allp[:, 0].max(); y0, y1 = allp[:, 1].min(), allp[:, 1].max()
cx, cy = (x0 + x1) / 2, (y0 + y1) / 2 + 30; span = max((x1 - x0) * 1.10, (y1 - y0) * 1.32 * W / HPX)
ax.set_xlim(cx - span / 2, cx + span / 2); ax.set_ylim(cy - span / 2 * HPX / W, cy + span / 2 * HPX / W); ax.set_aspect("equal")
out = os.path.join(H, "maps", "sketch_vert.png"); fig.savefig(out, dpi=200, facecolor=fig.get_facecolor()); plt.close(fig)
# подписи: значение vert_koef в точке внутри ячейки (пиксели картинки W x HPX)
def to_px(px, py):
    X = (px - (cx - span / 2)) / span * W; Y = HPX - (py - (cy - span / 2 * HPX / W)) / (span * HPX / W) * HPX
    return round(X, 1), round(Y, 1)
labels = []
for r in cells.itertuples():
    if r.in_scope != 1: continue
    p = r.geometry.representative_point(); X, Y = to_px(*proj(*plan(p.x, p.y)))
    labels.append(dict(num=int(r.num), v=float(r.vert_koef), cls=r.vertical, area=float(r.geometry.area), x=X, y=Y))
json.dump(dict(w=W, h=HPX, labels=labels, floor=FLOOR, n_bld=len(bld), n_nofloor=int(bld["Этажность"].isna().sum())),
          open(os.path.join(H, "maps", "sketch_vert.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("png:", out, "подписей:", len(labels))

# ---------------- Collada для SketchUp
def tris(poly):
    t = shapely.constrained_delaunay_triangles(poly)
    return [list(g.exterior.coords)[:3] for g in t.geoms]
groups = {}
def add(mat, tri): groups.setdefault(mat, []).append(tri)
for r in cells.itertuples():
    mat = ("cell_" + {"Высокий": "high", "Средний": "mid", "Низкий": "low"}.get(r.vertical, "out")) if r.in_scope == 1 else "cell_out"
    for p in rings(r.geometry):
        for tr in tris(p): add(mat, [(x - CENTER[0], y - CENTER[1], 0.05) for x, y in tr])
for r in bld.itertuples():
    for p in rings(r.geometry):
        h = r.h
        for tr in tris(p): add("roof", [(x - CENTER[0], y - CENTER[1], h) for x, y in tr])
        c = list(p.exterior.coords)
        for (x1, y1), (x2, y2) in zip(c[:-1], c[1:]):
            a, b = (x1 - CENTER[0], y1 - CENTER[1]), (x2 - CENTER[0], y2 - CENTER[1])
            add("wall", [(*a, 0), (*b, 0), (*b, h)]); add("wall", [(*a, 0), (*b, h), (*a, h)])
MAT = {"cell_high": COL["Высокий"], "cell_mid": COL["Средний"], "cell_low": COL["Низкий"], "cell_out": OUT_C, "roof": "#FFFFFF", "wall": "#C9C7CF"}
def rgb(h): h = h.lstrip("#"); return " ".join(f"{int(h[i:i + 2], 16) / 255:.3f}" for i in (0, 2, 4))
eff = "".join(f'<effect id="e_{m}"><profile_COMMON><technique sid="common"><lambert><diffuse><color>{rgb(c)} 1</color></diffuse></lambert></technique></profile_COMMON></effect>' for m, c in MAT.items())
mats = "".join(f'<material id="m_{m}" name="{m}"><instance_effect url="#e_{m}"/></material>' for m in MAT)
geos, nodes = [], []
for m, tl in groups.items():
    flat = [f"{v:.2f}" for tr in tl for p in tr for v in p]; n = len(flat)
    idx = " ".join(str(i) for i in range(len(tl) * 3))
    geos.append(f'<geometry id="g_{m}" name="{m}"><mesh><source id="g_{m}_p"><float_array id="g_{m}_a" count="{n}">{" ".join(flat)}</float_array>'
                f'<technique_common><accessor source="#g_{m}_a" count="{n // 3}" stride="3"><param name="X" type="float"/><param name="Y" type="float"/><param name="Z" type="float"/></accessor></technique_common></source>'
                f'<vertices id="g_{m}_v"><input semantic="POSITION" source="#g_{m}_p"/></vertices><triangles material="m_{m}" count="{len(tl)}"><input semantic="VERTEX" source="#g_{m}_v" offset="0"/><p>{idx}</p></triangles></mesh></geometry>')
    nodes.append(f'<node id="n_{m}" name="{m}"><instance_geometry url="#g_{m}"><bind_material><technique_common><instance_material symbol="m_{m}" target="#m_{m}"/></technique_common></bind_material></instance_geometry></node>')
dae = ('<?xml version="1.0" encoding="utf-8"?>\n<COLLADA xmlns="http://www.collada.org/2005/11/COLLADASchema" version="1.4.1">'
       '<asset><contributor><authoring_tool>sketch3d.py</authoring_tool></contributor><unit name="meter" meter="1"/><up_axis>Z_UP</up_axis></asset>'
       f'<library_effects>{eff}</library_effects><library_materials>{mats}</library_materials><library_geometries>{"".join(geos)}</library_geometries>'
       f'<library_visual_scenes><visual_scene id="scene" name="cells_v15">{"".join(nodes)}</visual_scene></library_visual_scenes>'
       '<scene><instance_visual_scene url="#scene"/></scene></COLLADA>\n')
os.makedirs(os.path.join(V, "3d"), exist_ok=True)
fn = os.path.join(V, "3d", "cells_vert_v15.dae"); open(fn, "w", encoding="utf-8").write(dae)
print("dae:", fn, {m: len(t) for m, t in groups.items()})
