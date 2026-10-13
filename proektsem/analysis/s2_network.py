# Анализ, шаг 2 — деревья путей (занятие 3, п. I.1а).
# Пешеходное дерево: от каждой двери (подъезд, вход в организацию) и площадки — кратчайший путь по сети дорожек, тротуаров и проездов
# до места входа на территорию (точки сети у границы квартала, до 20 м от неё: тротуары и переходы граничных улиц).
# Каждый путь непрерывен — от двери до улицы. Дополнительно — пути жителей от каждого подъезда к выходу метро «Беляево»
# и к переходу к ТЦ с «Ашаном». Число путей на участке — потенциальная интенсивность: 1 путь — исключается из оценки,
# 2–3 — низкая, 4 и более — высокая; общая нагрузка (двери + метро + ТЦ): 2–19 — низкая, 20 и более — высокая.
# Транспортное дерево — слой команды roads_counts (workload — число путей от подъездов по участку проезда), переносится на сеть.
# Вход: vector/source_data.gpkg, vector/konkovo_v16.gpkg. Выход: vector/analiz_v16.gpkg (пишется заново).
import os, warnings
import numpy as np, pandas as pd, geopandas as gpd, pyogrio
from shapely.geometry import Point
from shapely.ops import substring
from shapely.strtree import STRtree
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import dijkstra
warnings.filterwarnings("ignore")
HERE = os.path.dirname(os.path.abspath(__file__)); V = os.path.join(HERE, "..", "vector")
SRC, K14, A14 = (os.path.join(V, f) for f in ("source_data.gpkg", "konkovo_v16.gpkg", "analiz_v16.gpkg"))
rd = lambda f, l: gpd.read_file(f, layer=l)
def wr(df, f, l): pyogrio.write_dataframe(df, f, layer=l, driver="GPKG", append=False)
LOG = []
def log(*a): s = " ".join(str(x) for x in a); LOG.append(s); print(s)
if os.path.exists(A14): os.remove(A14)

net = rd(SRC, "network").reset_index(drop=True); net["eid"] = net.index
ent = rd(K14, "entries_territory"); pod = rd(K14, "entrances_buildings"); biz = rd(K14, "business"); pg = rd(K14, "playgrounds")
pts = pd.concat([gpd.GeoDataFrame({"kind": "подъезд", "ref": pod.id}, geometry=pod.geometry),
                 gpd.GeoDataFrame({"kind": "вход в организацию", "ref": biz.index}, geometry=biz.geometry),
                 gpd.GeoDataFrame({"kind": "площадка", "ref": pg.index}, geometry=pg.geometry.apply(lambda g: g.representative_point()))],
                ignore_index=True).set_crs(32637)
# привязка точек к ближайшему участку сети (разрезаем участок в точке проекции)
tree = STRtree(list(net.geometry)); cuts = {}
pts["eid"] = [int(tree.nearest(p)) for p in pts.geometry]
pts["snap"] = [net.geometry[e].distance(p) for e, p in zip(pts.eid, pts.geometry)]
for i, (e, p) in enumerate(zip(pts.eid, pts.geometry)):
    cuts.setdefault(e, []).append((net.geometry[e].project(p), i))
key = lambda x, y: (round(x * 2) / 2, round(y * 2) / 2)
segs = []; pnode = {}
for r in net.itertuples():
    g = r.geometry; L = g.length; ds = sorted(set([0.0, L] + [round(d, 2) for d, _ in cuts.get(r.eid, [])]))
    pos = {}; d0 = ds[0]; pos[d0] = key(*g.coords[0])
    for d1 in ds[1:]:
        if d1 - d0 < 0.05 and d1 != L: continue
        s = substring(g, d0, d1); segs.append(dict(eid=r.eid, geometry=s, a=pos[d0], b=key(*s.coords[-1]))); pos[d1] = segs[-1]["b"]; d0 = d1
    for d, i in cuts.get(r.eid, []):
        pnode[i] = pos[min(pos, key=lambda z: abs(z - d))]
S = gpd.GeoDataFrame(segs, crs=32637)
nodes = {k: n for n, k in enumerate(sorted(set(S.a) | set(S.b)))}
S["u"] = S.a.map(nodes); S["v"] = S.b.map(nodes); S["len"] = S.length
N = len(nodes); W = coo_matrix((np.r_[S.len, S.len], (np.r_[S.u, S.v], np.r_[S.v, S.u])), shape=(N, N)).tocsr()
pts["node"] = [nodes[pnode[i]] for i in range(len(pts))]
# места входа на территорию: узлы сети не дальше 20 м от границы квартала
TB = rd(SRC, "boundary").geometry.iloc[0].exterior
NXY = np.array(list(nodes.keys()))
src = np.array([n for k, n in nodes.items() if TB.distance(Point(k)) <= 20])
dist, pred, srcs = dijkstra(W, directed=False, indices=src, min_only=True, return_predecessors=True)
ekey = {}
for i, (u, v) in enumerate(zip(S.u, S.v)): ekey.setdefault((min(u, v), max(u, v)), []).append(i)
cnt = np.zeros(len(S), int); unreached = 0
O = pts; exit_used = {}
for n in O.node:
    if not np.isfinite(dist[n]): unreached += 1; continue
    x = n
    while pred[x] >= 0:
        y = pred[x]; ids = ekey[(min(x, y), max(x, y))]; j = min(ids, key=lambda k: S.len[k]); cnt[j] += 1; x = y
    exit_used[x] = exit_used.get(x, 0) + 1
S["ped"] = cnt
# второе дерево: от каждого подъезда до метро «Беляево» (точка сети, ближайшая к станции) — путь жителей к метро
tp = gpd.read_file(os.path.join(V, "basemap", "Moscow_transport_points.gpkg")).to_crs(32637)
import sys; sys.path.insert(0, HERE); from plan import world_xy, METRO_EXIT_PLAN
mp = Point(*world_xy(*METRO_EXIT_PLAN))                                   # выход метро на территорию
mnode = int(np.argmin(np.hypot(NXY[:, 0] - mp.x, NXY[:, 1] - mp.y)))
def tree_to(node):
    dm, pm = dijkstra(W, directed=False, indices=node, return_predecessors=True); out = np.zeros(len(S), int)
    for n in pts[pts.kind == "подъезд"].node:
        x = n
        while pm[x] >= 0:
            y = pm[x]; ids = ekey[(min(x, y), max(x, y))]; j = min(ids, key=lambda k: S.len[k]); out[j] += 1; x = y
    return out
mc = tree_to(mnode); S["metro"] = mc
from plan import MALL_CROSSING_PLAN
mall = Point(*world_xy(*MALL_CROSSING_PLAN)); mlnode = int(np.argmin(np.hypot(NXY[:, 0] - mall.x, NXY[:, 1] - mall.y)))
S["mall"] = tree_to(mlnode)
log("пути к переходу к ТЦ: узел в", round(float(np.hypot(NXY[mlnode, 0] - mall.x, NXY[mlnode, 1] - mall.y))), "м | участков", int((S.mall > 0).sum()))
log("выход метро (UTM):", round(mp.x), round(mp.y)); log("пути к метро: подъездов", int((pts.kind == "подъезд").sum()), "| участков", int((mc > 0).sum()), "| длина с 10+ путями, км", round(S[mc >= 10].len.sum() / 1000, 2),
    "| узел у станции в", round(float(np.hypot(NXY[mnode, 0] - mp.x, NXY[mnode, 1] - mp.y))), "м от неё")
S["group"] = np.select([cnt >= 4, cnt >= 2, cnt == 1], ["высокая", "низкая", "один путь"], default=None)
log("пешеходное дерево: путей от дверей и площадок", len(O), "| недостижимо", unreached, "| участков с путями", int((cnt > 0).sum()),
    "| длина, км:", {k: round(S[S.group == k].len.sum() / 1000, 2) for k in ("высокая", "низкая", "один путь")},
    "| вся сеть", round(S.len.sum() / 1000, 1))
# тип участка — от исходного; транспортная нагрузка — из дерева команды (участок проезда лежит на линии roads_counts)
S = S.join(net.set_index("eid")[["type"]], on="eid")
rc = rd(SRC, "roads_counts"); rc["geometry"] = rc.geometry
rtree_ = STRtree(list(rc.geometry))
def veh_of(g):
    best = 0
    for j in rtree_.query(g.buffer(5)):
        if g.length and g.intersection(rc.geometry[j].buffer(5)).length / g.length >= 0.6: best = max(best, int(rc.workload[j]))
    return best
S["veh"] = [veh_of(g) if t_ == "проезд" else 0 for g, t_ in zip(S.geometry, S["type"])]
S["vgroup"] = np.select([S.veh >= 4, S.veh >= 2, S.veh == 1], ["высокая", "низкая", "один путь"], default=None)
rc["group"] = np.select([rc.workload >= 4, rc.workload >= 2], ["высокая", "низкая"], default="один путь"); rc["length"] = rc.length.round(1)
log("транспортное дерево (команда):", len(rc), "участков,", round(rc.length.sum() / 1000, 2), "км | по группам, км:",
    rc.groupby("group").length.sum().div(1000).round(2).to_dict(), "| перенесено на сеть, км:", round(S[S.veh > 0].len.sum() / 1000, 2))
S["razdel"] = S["type"].map({"дорожка": "отдельно от проезда", "лестница": "отдельно от проезда", "тропа": "отдельно от проезда",
                             "переход": "отдельно от проезда", "тротуар": "по тротуару", "проезд": "по проезжей части"})
S["length"] = S.len.round(1)
S["street_side"] = (S.distance(TB) <= 20).astype(int)                 # тротуары граничных улиц
# общая пешеходная нагрузка участка: пути к входам во двор + пути жителей к метро и к переходу к ТЦ
S["load"] = S.ped + S.metro + S.mall
S["lgroup"] = np.select([S.load >= 20, S.load >= 2, S.load == 1], ["высокая", "низкая", "один путь"], default=None)
S["mgroup"] = np.select([(S.metro >= 20) | (S.mall >= 20), (S.metro >= 5) | (S.mall >= 5)], ["высокая", "низкая"], default=None)
log("общая нагрузка (входы + метро + ТЦ), км:", {k: round(S[S.lgroup == k].len.sum() / 1000, 2) for k in ("высокая", "низкая", "один путь")},
    "| без путей:", round(S[S.load == 0].len.sum() / 1000, 2))
OUT = gpd.GeoDataFrame(S[["eid", "type", "ped", "group", "metro", "mall", "load", "lgroup", "mgroup", "veh", "vgroup", "razdel", "street_side", "length", "geometry"]], crs=32637)
wr(OUT, A14, "network")
pts["dist_m"] = [round(float(dist[n]), 1) if np.isfinite(dist[n]) else None for n in pts.node]
wr(pts.drop(columns=["eid", "snap", "node"]), A14, "ped_origins")
ex_ = gpd.GeoDataFrame({"paths": list(exit_used.values())}, geometry=[Point(*NXY[k]) for k in exit_used], crs=32637)
wr(ex_, A14, "ped_exits")
wr(rc[["workload", "group", "length", "geometry"]], A14, "roads_tree")
for n in ("flows", "transit"): wr(rd(SRC, n), A14, n)
log("места входа на территорию, через которые идут пути:", len(ex_), "| самые нагруженные:", sorted(exit_used.values(), reverse=True)[:8])
log("разделённость (участки с путями, км):", OUT[OUT.ped > 0].groupby("razdel").length.sum().div(1000).round(2).to_dict())
