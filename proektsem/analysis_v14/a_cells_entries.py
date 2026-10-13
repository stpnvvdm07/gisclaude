# v14, часть A: ячейки (6 краевых ячеек включены в анализ), комфорт заново по геометрии, входы во дворы заново.
# Пишет vector/konkovo_v14.gpkg (копия v13 + новые cells, entries_territory, entry_nodes). v13 не меняется.
import os, shutil, warnings
import numpy as np, pandas as pd, geopandas as gpd, pyogrio
from shapely.geometry import Point, LineString
from shapely.ops import unary_union, nearest_points
warnings.filterwarnings("ignore")
HERE = os.path.dirname(os.path.abspath(__file__)); V = os.path.join(HERE, "..", "vector")
K13, A13, K14 = (os.path.join(V, f) for f in ("konkovo_v13.gpkg", "analiz_v13.gpkg", "konkovo_v14.gpkg"))
rd = lambda f, l: gpd.read_file(f, layer=l)
def wr(df, f, l): pyogrio.write_dataframe(df, f, layer=l, driver="GPKG", append=False)
LOG = []
def log(*a): s = " ".join(str(x) for x in a); LOG.append(s); print(s)
shutil.copyfile(K13, K14)

# ---------------- ячейки
NEW = [15, 22, 29, 39, 47, 51]
c = rd(K13, "cells"); b = rd(K13, "buildings"); f = rd(K13, "fences")
sl = gpd.read_file(os.path.join(V, "proektbase", "slopesandwalls.gpkg"))
c["is_anal_v13"] = c.is_anal; c.loc[c.num.isin(NEW), "is_anal"] = 1
log("в анализ включены ячейки", NEW, "-> ячеек в анализе:", int(c.is_anal.sum()))
b["fl"] = b["Этажность"].fillna(1).clip(lower=1)
HIGH = f[f.podtip.str.contains("высокое", na=False)]
FIX = unary_union(list(b.geometry.boundary) + list(HIGH.geometry) + list(sl.geometry))      # закреплённые границы
rows = []
for r in c.itertuples():
    g = r.geometry; z = g.buffer(2.5); near = b[b.intersects(z)]
    fa = sum(x.geometry.boundary.intersection(z).length * x.fl * 3.0 for x in near.itertuples())
    fixed = g.exterior.intersection(FIX.buffer(2.0)).length
    xy = np.array(g.minimum_rotated_rectangle.exterior.coords); size = float(np.hypot(*np.diff(xy, axis=0).T).max())
    rows.append((fa, fixed, size))
c["fasad_area_v13"], c["iso_koef_v13"], c["size_v13"] = c.fasad_area, c.iso_koef, c["size"]
c["fasad_area"] = [round(r[0]) for r in rows]; c["fixed_len"] = [round(r[1]) for r in rows]; c["size"] = [round(r[2]) for r in rows]
c["area"] = c.area.round().astype(int); c["perimeter"] = c.geometry.exterior.length.round().astype(int)
c["vert_koef"] = (c.fasad_area / c.area).round(2); c["iso_koef"] = (c.fixed_len / c.perimeter).round(2)
LV = {2: "Высокий", 1: "Средний", 0: "Низкий"}
c["vertical"] = c.vert_koef.apply(lambda x: LV[2 if 1.3 <= x <= 2.0 else (1 if 0.6 <= x < 1.3 else 0)])
c["isolation"] = c.iso_koef.apply(lambda x: LV[2 if x >= 0.65 else (1 if x > 0.35 else 0)])
c["planning"] = np.where((c["size"] >= 25) & (c["size"] <= 140), "Комфортная", "Некомфортная")
P = {"Высокий": 2, "Средний": 1, "Низкий": 0}
c["score"] = ((c.vertical.map(P) + c.isolation.map(P) + (c.planning == "Комфортная") * 2) / 6).round(2)
c["comfort"] = np.where(c.score >= 0.665, "Комфортная", "Некомфортная")
A = c[c.is_anal == 1]
log("комфорт v14 (ячейки анализа):", A.comfort.value_counts().to_dict(), "| вертикаль", A.vertical.value_counts().to_dict(),
    "| замкнутость", A.isolation.value_counts().to_dict(), "| размер", A.planning.value_counts().to_dict())
wr(c, K14, "cells")

# ---------------- входы: на внешнем крае дворов анализа
ex = rd(K13, "cells_excluded")
core = unary_union(list(A.geometry) + list(b.geometry) + list(ex.geometry)).buffer(1.5).buffer(-1.5)
core = max(core.geoms, key=lambda g: g.area) if core.geom_type == "MultiPolygon" else core
ring = core.exterior
e = rd(K13, "entries_territory"); e["d_core"] = e.distance(ring).round(1); e["in_core"] = e.within(core)
arch = e.podtip.eq("Вход — арка")
keep = (e.d_core <= 20) | (arch & (e.d_core <= 40))
e["v14"] = np.where(keep, "оставлен", np.where(e.in_core, "убран: внутренний проход", "перенесён на край дворов"))
log("входы v13:", len(e), "| оставлены", int(keep.sum()), "| внутренние убраны", int((~keep & e.in_core).sum()),
    "| уличные (перенос на край дворов)", int((~keep & ~e.in_core).sum()))
net = rd(A13, "network")
PED = net[net["type"].isin(["дорожка", "тротуар", "проезд", "лестница", "тропа", "переход"])]
cr = []
for r in PED.itertuples():
    x = r.geometry.intersection(ring)
    for p in (getattr(x, "geoms", [x])):
        if p.geom_type == "Point": cr.append((p, r.type))
# там, где дворы подходят к улице вплотную: примыкания внутренних путей к уличному тротуару (конец ребра у границы территории)
TB = rd(K13, "boundary").geometry.iloc[0].exterior; ALONG = ring.intersection(TB.buffer(15))
for r in PED.itertuples():
    cs = list(r.geometry.coords)
    for p0, p1 in ((cs[0], cs[-1]), (cs[-1], cs[0])):
        a, z = Point(p0), Point(p1)
        if TB.distance(a) <= 14 and TB.distance(z) > 18 and ALONG.distance(a) <= 15 and core.buffer(-3).intersects(LineString([a, z])):
            cr.append((a, r.type))
crs_ = gpd.GeoDataFrame({"etype": [t for _, t in cr]}, geometry=[p for p, _ in cr], crs=32637)
# слить пересечения ближе 15 м в один узел
groups = []; used = set()
for i, p in enumerate(crs_.geometry):
    if i in used: continue
    g = [j for j, q in enumerate(crs_.geometry) if j not in used and p.distance(q) <= 15]; used |= set(g); groups.append(g)
kept = e[keep]; moved = e[~keep & ~e.in_core]
GB = unary_union(b.geometry); TR = unary_union(rd(K14, "green").query("type == 'деревья'").geometry)
def classify(p, et):
    m = moved[moved.distance(p) <= 60]
    if len(m):
        r = m.loc[m.distance(p).idxmin()]; return r.podtip, r.degree, "перенос с улицы: " + r.podtip
    nb = sum(1 for d in (8, 15) if GB.intersects(p.buffer(d)))
    if et == "проезд": return "Вход — въезд", "низкая", "по сети: проезд"
    if GB.distance(p) <= 15: return "Вход — разрыв в застройке", "средняя", "по сети: между зданиями"
    if HIGH.distance(p).min() <= 4: return "Вход — калитка", "высокая", "по сети: проход в высоком ограждении"
    if TR.distance(p) <= 5: return "Вход — разрыв в насаждениях", "низкая", "по сети: через насаждения"
    return "Вход — не зафиксирован", "нет", "по сети: ничем не обозначен"
new = []
for g in groups:
    pts = crs_.iloc[g]; p = Point(np.mean([q.x for q in pts.geometry]), np.mean([q.y for q in pts.geometry]))
    if len(kept) and kept.distance(p).min() <= 20: continue
    et = "проезд" if "проезд" in pts.etype.values else pts.etype.iloc[0]
    pt, dg, why = classify(p, et)
    new.append(dict(podtip=pt, degree=dg, src="v14: " + why, in_12="да", level="внешний", geometry=p))
NE = gpd.GeoDataFrame(new, crs=32637)
E = pd.concat([kept.assign(src=kept.src), NE], ignore_index=True)
E["fix_class"] = np.where(E.degree.isin(["высокая", "средняя"]), "организован", "не организован")
E["in_12"] = "да"; E["node"] = range(1, len(E) + 1)
E = gpd.GeoDataFrame(E[["node", "podtip", "fix_class", "degree", "src", "survey_id", "comment", "photo", "geometry"]], crs=32637)
log("входы v14:", len(E), "| из обследования", len(kept), "| добавлены на краю дворов", len(NE), "| организованы", int((E.fix_class == "организован").sum()))
log("  по типу:", E.podtip.str.replace("Вход — ", "").value_counts().to_dict())
wr(E, K14, "entries_territory")
wr(gpd.GeoDataFrame({"what": ["край дворов анализа"]}, geometry=[LineString(ring.coords)], crs=32637), K14, "core_edge")
cg = A.set_index("num").geometry
E["cells"] = E.geometry.apply(lambda p: ",".join(str(n) for n, g in cg.items() if g.distance(p) <= 8))
wr(E.rename(columns={}), K14, "entry_nodes")
open(os.path.join(HERE, "log_a.txt"), "w", encoding="utf-8").write("\n".join(LOG) + "\n")
