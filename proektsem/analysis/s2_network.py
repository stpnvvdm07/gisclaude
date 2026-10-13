# Анализ v15, шаг 2 (основа — analysis_v14/b_network.py): пешеходное «дерево путей» по заданию (занятие 3, п. I.1а): пути от мест входа на территорию (входы v14)
# к входам в здания (подъезды, входы в организации) и к площадкам, по всей сети дорожек и проездов.
# Для каждого подъезда / входа / площадки строится кратчайший путь до ближайшего входа во двор; число путей на участке —
# потенциальная интенсивность: 1 путь — исключается, 2–3 — низкая, 4 и более — высокая (по аналогии с транспортом).
# Пишет vector/analiz_v15.gpkg (копия analiz_v13 + network с полями v15: ped, metro, mall, load, group).
import os, shutil, warnings
import numpy as np, pandas as pd, geopandas as gpd, pyogrio
from shapely.geometry import Point
from shapely.ops import substring
from shapely.strtree import STRtree
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import dijkstra
warnings.filterwarnings("ignore")
HERE = os.path.dirname(os.path.abspath(__file__)); V = os.path.join(HERE, "..", "vector")
K14, A13, A14 = (os.path.join(V, f) for f in ("konkovo_v15.gpkg", "analiz_v13.gpkg", "analiz_v15.gpkg"))
rd = lambda f, l: gpd.read_file(f, layer=l)
def wr(df, f, l): pyogrio.write_dataframe(df, f, layer=l, driver="GPKG", append=False)
LOG = []
def log(*a): s = " ".join(str(x) for x in a); LOG.append(s); print(s)
shutil.copyfile(A13, A14)

net = rd(A13, "network").reset_index(drop=True); net["eid"] = net.index
ent = rd(K14, "entries_territory"); pod = rd(K14, "entrances_buildings"); biz = rd(K14, "business"); pg = rd(K14, "playgrounds")
pts = pd.concat([gpd.GeoDataFrame({"kind": "вход во двор", "ref": ent.node}, geometry=ent.geometry),
                 gpd.GeoDataFrame({"kind": "подъезд", "ref": pod.id}, geometry=pod.geometry),
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
src = pts[pts.kind == "вход во двор"].node.unique()
dist, pred, srcs = dijkstra(W, directed=False, indices=src, min_only=True, return_predecessors=True)
ekey = {}
for i, (u, v) in enumerate(zip(S.u, S.v)): ekey.setdefault((min(u, v), max(u, v)), []).append(i)
cnt = np.zeros(len(S), int); unreached = 0
O = pts[pts.kind != "вход во двор"]
for n in O.node:
    if not np.isfinite(dist[n]): unreached += 1; continue
    x = n
    while pred[x] >= 0:
        y = pred[x]; ids = ekey[(min(x, y), max(x, y))]; j = min(ids, key=lambda k: S.len[k]); cnt[j] += 1; x = y
S["ped"] = cnt
# второе дерево: от каждого подъезда до метро «Беляево» (точка сети, ближайшая к станции) — путь жителей к метро
tp = gpd.read_file(os.path.join(V, "basemap", "Moscow_transport_points.gpkg")).to_crs(32637)
import sys; sys.path.insert(0, HERE); from plan import world_xy, METRO_EXIT_PLAN
mp = Point(*world_xy(*METRO_EXIT_PLAN))                                   # выход метро на территорию
NXY = np.array(list(nodes.keys())); mnode = int(np.argmin(np.hypot(NXY[:, 0] - mp.x, NXY[:, 1] - mp.y)))
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
log("пешеходное дерево v14: путей", len(O), "| недостижимо", unreached, "| участков с путями", int((cnt > 0).sum()),
    "| длина, км:", {k: round(S[S.group == k].len.sum() / 1000, 2) for k in ("высокая", "низкая", "один путь")},
    "| вся сеть", round(S.len.sum() / 1000, 1))
# поля v13 (тип, транспорт, разделённость) — от исходного участка
keep = net.set_index("eid")[["type", "veh", "vgroup", "razdel"]]
S = S.join(keep, on="eid")
S["razdel"] = S["type"].map({"дорожка": "отдельно от проезда", "лестница": "отдельно от проезда", "тропа": "отдельно от проезда",
                             "переход": "отдельно от проезда", "тротуар": "по тротуару", "проезд": "по проезжей части"})
S["length"] = S.len.round(1)
TB = rd(K14, "boundary").geometry.iloc[0].exterior
S["street_side"] = (S.distance(TB) <= 20).astype(int)                 # тротуары граничных улиц
# общая пешеходная нагрузка участка: пути к входам во двор + пути жителей к метро и к переходу к ТЦ
S["load"] = S.ped + S.metro + S.mall
S["lgroup"] = np.select([S.load >= 20, S.load >= 2, S.load == 1], ["высокая", "низкая", "один путь"], default=None)
S["mgroup"] = np.select([(S.metro >= 20) | (S.mall >= 20), (S.metro >= 5) | (S.mall >= 5)], ["высокая", "низкая"], default=None)
log("общая нагрузка (входы + метро + ТЦ), км:", {k: round(S[S.lgroup == k].len.sum() / 1000, 2) for k in ("высокая", "низкая", "один путь")},
    "| без путей:", round(S[S.load == 0].len.sum() / 1000, 2))
OUT = gpd.GeoDataFrame(S[["eid", "type", "ped", "group", "metro", "mall", "load", "lgroup", "mgroup", "veh", "vgroup", "razdel", "street_side", "length", "geometry"]], crs=32637)
wr(OUT, A14, "network")
pts["dist_to_entry"] = [round(float(dist[n]), 1) if np.isfinite(dist[n]) else None for n in pts.node]
wr(pts.drop(columns=["eid"]), A14, "ped_origins")
log("разделённость (участки с путями, км):", OUT[OUT.ped > 0].groupby("razdel").length.sum().div(1000).round(2).to_dict())
open(os.path.join(HERE, "log_s2.txt"), "w", encoding="utf-8").write("\n".join(LOG) + "\n")
