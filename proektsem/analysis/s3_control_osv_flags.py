# Анализ v15, шаг 3 (основа — analysis_v14/c_control_osv_flags.py): контроль без дыр и с меньшим активным публичным контролем,
# освоенность шестиугольниками 12 м со сглаживанием, 11 пунктов, слои проблем и предпосылок, устойчивость -> problems_v15.gpkg.
# v14, часть C: социальный контроль (с тротуарами граничных улиц и остановками у метро), места поведения, освоенность
# (сеткой 10 м, правило «обустроено × используется»), 11 пунктов, счёт, слои проблем и предпосылок -> problems_v14.gpkg.
import os, shutil, warnings, math
import numpy as np, pandas as pd, geopandas as gpd, pyogrio
from shapely.geometry import box
from shapely.ops import unary_union, linemerge
warnings.filterwarnings("ignore")
HERE = os.path.dirname(os.path.abspath(__file__)); V = os.path.join(HERE, "..", "vector")
K14, A14, A13, P13, P14 = (os.path.join(V, f) for f in ("konkovo_v15.gpkg", "analiz_v15.gpkg", "analiz_v13.gpkg", "problems_v13.gpkg", "problems_v15.gpkg"))
rd = lambda f, l: gpd.read_file(f, layer=l)
def wr(df, f, l): pyogrio.write_dataframe(df, f, layer=l, driver="GPKG", append=False)
U = lambda gs: unary_union([g for g in gs if g is not None and not g.is_empty])
LOG = []
def log(*a): s = " ".join(str(x) for x in a); LOG.append(s); print(s)
shutil.copyfile(P13, P14)

BLD = U(rd(K14, "buildings").buffer(0))
TER = U(list(rd(K14, "cells").geometry) + list(rd(K14, "cells_excluded").geometry)).buffer(0.5).buffer(-0.5)   # жилое образование без проезжей части улиц
FREE = TER.difference(BLD)
net = rd(A14, "network"); cz = rd(A13, "control_zones"); cz["geometry"] = cz.buffer(0)
ex = rd(K14, "cells_excluded"); EXC = U(ex.buffer(0)); biz = rd(K14, "business"); fl = rd(A13, "flows")
tp = gpd.read_file(os.path.join(V, "basemap", "Moscow_transport_points.gpkg")).to_crs(32637)
stops = tp[(tp.distance(TER) <= 40) & tp.fclass.isin(["bus_stop", "railway_station"])]
metro = tp[(tp.name == "Беляево") & (tp.fclass == "railway_station")]

# ---------------- зоны контроля
AJ = U(cz[cz["type"] == "АЖ"].geometry); PJ = U(cz[cz["type"] == "ПЖ"].geometry)
side = net[net.street_side == 1]
HI = fl[fl.cls == "высокий"]; MID = fl[fl.cls == "средний"]
side_hi = side[side.geometry.apply(lambda g: HI.distance(g).min() <= 120 if len(HI) else False)]
side_lo = side.drop(side_hi.index)
from shapely.geometry import Polygon, Point
import sys; sys.path.insert(0, HERE); from plan import world_xy, METRO_SQUARE_PLAN, METRO_EXIT_PLAN, MALL_CROSSING_PLAN
MSQ = Polygon([world_xy(*p) for p in METRO_SQUARE_PLAN]).intersection(TER); MEX = Point(*world_xy(*METRO_EXIT_PLAN))
MALL = Point(*world_xy(*MALL_CROSSING_PLAN))
wr(gpd.GeoDataFrame({"what": ["площадь у выхода метро", "выход метро «Беляево»", "переход к ТЦ с «Ашаном»"]}, geometry=[MSQ, MEX.buffer(6), MALL.buffer(6)], crs=32637), A14, "metro")
# интенсивность по всем используемым путям: пешеходные пути к входам + пути к метро; транспорт; транзит
net["load"] = net.ped.fillna(0)
tr13 = rd(A13, "transit"); TRH_ = U(tr13[tr13.cls == "высокая"].geometry).buffer(2); TRA_ = U(tr13.geometry).buffer(2)
on = lambda Z: net.geometry.apply(lambda g: g.intersection(Z).length / g.length > 0.5 if g.length else False)
net["tr_hi"] = on(TRH_); net["tr_any"] = on(TRA_)
# вариант Б (по заданию, п. 3.2): активный — оси с относительно высокой интенсивностью; пассивный — с относительно низкой; 1 путь — исключается
# публичный контроль по общей пешеходной нагрузке участка (пути к входам во двор + к метро + к переходу к ТЦ):
# относительно высокая — 20 и больше путей (главные оси), относительно низкая — 2–19; транспорт — 4+ / 2–3 пути
HIE = net[(net.lgroup == "высокая") | (net.vgroup == "высокая")]
USED = net[~net.index.isin(HIE.index) & ((net.lgroup == "низкая") | (net.vgroup == "низкая"))]
log("участки сети: активный публичный (интенсивные)", len(HIE), round(HIE.length.sum() / 1000, 2), "км | пассивный (низкая интенсивность)", len(USED),
    round(USED.length.sum() / 1000, 2), "км | без публичного контроля", len(net) - len(HIE) - len(USED), round(net.length.sum() / 1000 - HIE.length.sum() / 1000 - USED.length.sum() / 1000, 2), "км")
AP_parts = [MSQ, MALL.buffer(25), U(HIE.buffer(15)), U(net[net.vgroup == "высокая"].buffer(15)),
            U(biz[~biz.within(EXC)].buffer(15))]
PP_parts = [U(USED.buffer(7.5)), EXC]
AP = U(AP_parts).intersection(TER).difference(BLD); PP = U(PP_parts).intersection(TER).difference(BLD)
AJ = AJ.intersection(FREE); PJ = PJ.intersection(FREE)
AJ = AJ.intersection(FREE); PJ = PJ.intersection(FREE)
zones = gpd.GeoDataFrame({"type": ["АЖ", "ПЖ", "АП", "ПП"],
                          "source": ["фасады с подъездами, 30 м", "фасады без подъездов и торцы, 15 м",
                                     "площадь у выхода метро, переход к ТЦ; главные пешеходные оси (20+ путей к входам, метро и ТЦ), проезды 4+ путей, входы в организации, 15 м",
                                     "прочие используемые пути (2–19 путей), проезды 2–3 пути, 7,5 м; огороженные участки школ и детсадов"]},
                         geometry=[AJ, PJ, AP, PP], crs=32637)
zones["area"] = zones.area.round()
wr(zones, A14, "control_zones")
from shapely.geometry import Polygon as _Poly, MultiPolygon as _MP
def fill(g, hole=400, sliver=2.0):
    """Без дыр и щелей: закрыть щели до 4 м и залить дыры площадью до hole м²."""
    g = g.buffer(sliver).buffer(-sliver)
    ps = []
    for p in getattr(g, "geoms", [g]):
        if p.geom_type != "Polygon": continue
        ps.append(_Poly(p.exterior, [r for r in p.interiors if _Poly(r).area > hole]))
    return unary_union(ps)
AJ = fill(AJ).intersection(FREE); PJ = fill(PJ).intersection(FREE); AP = fill(AP).intersection(FREE); PP = fill(PP).intersection(FREE)
CTL = fill(U([AJ, AP])).intersection(FREE); PART = fill(U([PJ, PP, CTL])).intersection(FREE).difference(CTL)
UNC = FREE.difference(CTL).difference(PART)
# мелкие острова (< 150 м²) любого класса присоединяются к окружению
def absorb(a, b, lim=150):
    small = [p for p in getattr(a, "geoms", [a]) if p.area < lim]
    return a.difference(unary_union(small)) if small else a, unary_union([b] + small) if small else b
UNC, PART = absorb(UNC, PART); PART, CTL = absorb(PART, CTL)
COMP = AJ.intersection(AP)
ctl = gpd.GeoDataFrame({"type": ["контролируемая", "частично контролируемая", "неконтролируемая"]}, geometry=[CTL, PART, UNC], crs=32637)
ctl = ctl.explode(index_parts=False); ctl = ctl[ctl.area > 2]; ctl["area"] = ctl.area.round()
wr(ctl, A14, "control"); comp = gpd.GeoDataFrame(geometry=[COMP], crs=32637).explode(index_parts=False); comp = comp[comp.area > 2]
wr(comp, A14, "competition")
ar = ctl.groupby("type").area.sum(); log("контролируемость v14, га:", (ar / 1e4).round(2).to_dict(), "| доли:", (100 * ar / ar.sum()).round(0).to_dict(),
                                          "| конкуренция", round(COMP.area / 1e4, 2), "га")

# ---------------- места поведения (площадки): зоны по удалённости от подъезда и контроль
pod = rd(K14, "entrances_buildings"); pg = rd(K14, "playgrounds"); pg["geometry"] = pg.buffer(0)
pg["d_pod"] = pg.geometry.apply(lambda g: pod.distance(g).min()).round(1)
pg["zone"] = np.select([pg.d_pod <= 30, pg.d_pod <= 100], ["ближняя", "средняя"], default="периферийная")
pg["in_AJ"] = pg.geometry.apply(lambda g: g.intersection(AJ).area / g.area >= 0.5)
pg["in_PASS"] = pg.geometry.apply(lambda g: g.intersection(U([PJ, PP, AJ, AP])).area / g.area >= 0.5)
pg["control"] = pg.geometry.apply(lambda g: max(((g.intersection(z).area, t) for z, t in ((CTL, "контролируемая"), (PART, "частично контролируемая"), (UNC, "неконтролируемая"))))[1])
pg["problem"] = np.where((pg.zone == "ближняя") & ~pg.in_AJ, "ближняя зона вне активного персонального контроля",
                         np.where((pg.zone == "периферийная") & ~pg.in_PASS, "периферийная зона вне пассивного контроля", None))
wr(pg, A14, "playgrounds_zones")
log("площадки: зоны", pg.zone.value_counts().to_dict(), "| нарушение 3.3:", int(pg.problem.notna().sum()), "| по контролю", pg.control.value_counts().to_dict())

# ---------------- освоенность: сетка 10 м по свободной территории (без проездов и стоянок)
o13 = rd(A13, "osvoennost"); o13["geometry"] = o13.buffer(0)
OPEN = U(o13.geometry)                                     # свободная от зданий, проездов и стоянок территория v13
GR = rd(K14, "green"); GREEN = U(GR.buffer(0)); PGU = U(pg.geometry)
pdn = rd(K14, "people_dens"); MANY = U(pdn[pdn.dens == "много"].geometry); FEW = U(pdn[pdn.dens == "мало"].geometry)
MAN = U(rd(K14, "osv_manual").buffer(0))
SL = U(gpd.read_file(os.path.join(V, "proektbase", "slopesandwalls.gpkg")).geometry).buffer(6)
WALK = U(net[net["type"].isin(["дорожка", "тротуар", "тропа", "лестница", "переход"])].geometry)
DRIVE = U(net[net["type"] == "проезд"].geometry)
LINK = U(net[net.ped >= 2].geometry)
PODZ = U(pod.geometry)
cells = rd(K14, "cells")
SCOPE = U(cells[cells.in_scope == 1].geometry)
import sys; sys.path.insert(0, HERE); from plan import CENTER, ROT
from shapely import affinity
OP = affinity.rotate(OPEN, np.degrees(ROT), origin=CENTER)          # в плане (улицы по осям)
x0, y0, x1, y1 = OP.bounds; R6 = 7.0                           # шестиугольник: радиус 7 м (ширина 12 м, площадь ~127 м²)
hw = math.sqrt(3) * R6; grid = []
for j, y in enumerate(np.arange(y0, y1 + R6, 1.5 * R6)):
    for x in np.arange(x0 + (hw / 2 if j % 2 else 0), x1 + hw, hw):
        hx = _Poly([(x + R6 * math.cos(math.radians(30 + 60 * k)), y + R6 * math.sin(math.radians(30 + 60 * k))) for k in range(6)])
        grid.append(affinity.rotate(hx, -np.degrees(ROT), origin=CENTER))
G = gpd.GeoDataFrame(geometry=grid, crs=32637); G = G[G.intersects(OPEN)].copy()
G["geometry"] = G.geometry.intersection(OPEN); G = G[G.area >= 5].copy()
c = G.geometry.centroid
def share(z): return G.geometry.apply(lambda g: g.intersection(z).area / g.area if g.area else 0)
G["pg"] = share(PGU); G["green"] = share(GREEN); G["man"] = share(MAN); G["slope"] = share(SL)
G["many"] = share(MANY); G["few"] = share(FEW); G["exc"] = share(EXC); G["scope"] = share(SCOPE)
G["d_walk"] = c.distance(WALK); G["d_drive"] = c.distance(DRIVE); G["d_link"] = c.distance(LINK)
G["d_pod"] = c.distance(PODZ); G["d_pg"] = c.distance(PGU)
G["kind"] = np.select([G.pg >= 0.5, G.green >= 0.5], ["площадка", "озеленение"], default="покрытие")
near_path = (G.d_walk <= 12) | (G.d_drive <= 6)
B = np.select([G.man >= 0.5, G.slope >= 0.3, G.kind == "площадка", G.kind == "покрытие",
               near_path | (G.d_pod <= 30) | (G.d_pg <= 20)], [0, 0, 1, 1, 1], default=0)
B_why = np.select([G.man >= 0.5, G.slope >= 0.3, G.kind == "площадка", G.kind == "покрытие", near_path, G.d_pod <= 30, G.d_pg <= 20],
                  ["контур команды «неосвоенная»", "откос / подпорная стенка", "площадка", "твёрдое покрытие", "газон у дорожки", "газон у подъезда",
                   "газон у площадки"], default="зелёный массив без дорожек")
Uu = np.select([G.kind == "площадка", G.few >= 0.5, G.man >= 0.5, G.many >= 0.5, G.d_link <= 15, G.d_pod <= 20, G.d_pg <= 15],
               [1, 0, 0, 1, 1, 1, 1], default=0)
U_why = np.select([G.kind == "площадка", G.few >= 0.5, G.man >= 0.5, G.many >= 0.5, G.d_link <= 15, G.d_pod <= 20, G.d_pg <= 15],
                  ["площадка", "наблюдение: мало людей", "контур команды «неосвоенная»", "наблюдение: много людей",
                   "у пешеходной связи", "у подъезда", "у площадки"], default="нет признаков использования")
G["B"], G["B_why"], G["U"], G["U_why"] = B, B_why, Uu, U_why
G["cls"] = np.select([G.exc >= 0.5, G.scope < 0.5, (G.B == 1) & (G.U == 1), (G.B == 1) | (G.U == 1)],
                     ["не оценивается", "не оценивается", "освоенная", "частично освоенная"], default="неосвоенная")
G["note"] = np.select([G.exc >= 0.5, G.scope < 0.5], ["участок школы или детсада", "вне ячеек анализа"], default=None)
# сглаживание: класс шестиугольника с 4+ соседями (из 6) другого одного класса меняется на него — без «шахматки»
from shapely.strtree import STRtree
G = G.reset_index(drop=True); tr_ = STRtree(list(G.geometry)); ev = G.cls != "не оценивается"
for _ in range(2):
    new = G.cls.copy()
    for i in G.index[ev]:
        nb = [j for j in tr_.query(G.geometry[i].buffer(1.5)) if j != i and ev[j]]
        if len(nb) < 4: continue
        vc = G.cls[nb].value_counts()
        if vc.iloc[0] >= 4 and vc.index[0] != G.cls[i]: new[i] = vc.index[0]
    G["cls"] = new
G["area"] = G.area.round(1)
G = G.drop(columns=["pg", "green", "man", "slope", "many", "few", "exc", "scope"])
wr(G, A14, "osvoennost")
t = G[G.cls != "не оценивается"].groupby("cls").area.sum(); log("освоенность v15 (шестиугольники, сглажено), га:", (t / 1e4).round(2).to_dict(), "| доли:", (100 * t / t.sum()).round(0).to_dict())
OSV = {k: U(G[G.cls == k].geometry) for k in ("освоенная", "частично освоенная", "неосвоенная")}

# ---------------- 11 пунктов
S = cells[cells.in_scope == 1].copy().set_index("num"); cg = S.geometry
ent = rd(K14, "entries_territory"); NON = ent[ent.fix_class == "не организован"]
nodes_non = pd.Series({n: int(NON.distance(g).le(8).sum()) for n, g in cg.items()})
bb = rd(K14, "buildings"); w4 = rd(P13, "p1_4_wear")
wear40 = pd.Series({n: int(w4.distance(g).le(8).sum()) for n, g in cg.items()})
LZ = U(rd(K14, "loading_zones").buffer(0)); loading_m2 = pd.Series({n: g.intersection(LZ).area for n, g in cg.items()})
garb = rd(K14, "garbage"); dz = pd.concat([biz[(biz.danger == "опасный") & (biz.isolation == "открытый")].geometry, garb.geometry])
danger_obj = pd.Series({n: int(dz.distance(g).le(6).sum()) for n, g in cg.items()})
road = net[net["type"] == "проезд"]
comb = road[(road.ped >= 2) & (road.vgroup.isin(["низкая", "высокая"])) & ((road.group == "высокая") | (road.vgroup == "высокая"))]
CM = U(comb.geometry)
# заполнить разрывы: короткие (до 25 м) участки проезда между двумя участками совмещения
gap = road[(~road.index.isin(comb.index)) & (road.length <= 25)]
fill = gap[gap.geometry.apply(lambda g: CM.distance(__import__("shapely").geometry.Point(g.coords[0])) < 1 and CM.distance(__import__("shapely").geometry.Point(g.coords[-1])) < 1)]
CM = linemerge(U(list(comb.geometry) + list(fill.geometry)))
combined_m = pd.Series({n: g.intersection(CM).length for n, g in cg.items()})
tr = rd(A13, "transit"); RES = U([AJ, PJ]); TRH = U(tr[tr.cls == "высокая"].geometry).intersection(RES)
transit_res_m = pd.Series({n: g.intersection(TRH).length for n, g in cg.items()})
pod_n = pd.Series({n: int(pod.distance(g).le(8).sum()) for n, g in cg.items()})
TRP = U(tr[(tr.cls == "высокая") & (tr["mode"] == "пешеходный")].geometry)
serv = biz[(biz.function == "обслуживающий")]; serv = serv[serv.distance(TRP) <= 15]
biz_transit = pd.Series({n: int(serv.distance(g).le(6).sum()) for n, g in cg.items()})
pgp = pg[pg.problem.notna()]; pg_out = pd.Series({n: int(pgp.intersects(g).sum()) for n, g in cg.items()})
comp_pct = pd.Series({n: 100 * g.intersection(COMP).area / g.area for n, g in cg.items()})
unc_pct = pd.Series({n: 100 * g.intersection(UNC).area / g.area for n, g in cg.items()})
def osv_pct(k): return pd.Series({n: (lambda a: 100 * g.intersection(OSV[k]).area / a if a else 0)(g.intersection(U(OSV.values())).area) for n, g in cg.items()})
unosv_pct = osv_pct("неосвоенная")
VAL = pd.DataFrame(dict(pod=pod_n, nodes_non=nodes_non, wear40=wear40, loading_m2=loading_m2.round(), danger_obj=danger_obj, combined_m=combined_m.round(),
                        transit_res_m=transit_res_m.round(), biz_transit=biz_transit, pg_out=pg_out, comp_pct=comp_pct.round(1), unc_pct=unc_pct.round(1),
                        unosv_pct=unosv_pct.round(1)))
BASE = dict(comfort_cut=0.67, ent_non=1, wear_n=1, loading_m2=50, danger_obj=1, combined_m=20, transit_res_m=20, biz_transit=1, comp_pct=5, unc_pct=50, unos_pct=25)
FL = ["p1_1", "p1_2", "p1_3", "p1_4", "p2_1", "p2_2", "p2_3", "p3_1", "p3_2", "p3_3", "p3_4"]
def flags(d, p=None, score=None):
    p = {**BASE, **(p or {})}; s_ = S.score if score is None else score; f = pd.DataFrame(index=cg.index)
    f["p1_1"] = s_ < p["comfort_cut"] - 0.005; f["p1_2"] = d.nodes_non >= p["ent_non"]; f["p1_3"] = pd.Series(False, index=S.index)                 # в анализе только дворы в зафиксированных границах
    f["p1_4"] = d.wear40 >= p["wear_n"]; f["p2_1"] = d.loading_m2 >= p["loading_m2"]; f["p2_2"] = d.danger_obj >= p["danger_obj"]
    f["p2_3"] = d.combined_m >= p["combined_m"]; f["p3_1"] = (d.transit_res_m >= p["transit_res_m"]) & (d.pod > 0)
    f["p3_2"] = d.biz_transit >= p["biz_transit"]; f["p3_3"] = d.pg_out >= 1
    f["p3_4a"] = d.comp_pct >= p["comp_pct"]; f["p3_4b"] = d.unc_pct >= p["unc_pct"]; f["p3_4c"] = d.unosv_pct >= p["unos_pct"]
    f["p3_4"] = f.p3_4a | f.p3_4b | f.p3_4c
    return f.astype(int)
def classify(s): return pd.cut(s, [-1, 3, 5, 99], labels=["низкая", "средняя", "высокая"]).astype(str)
F0 = flags(VAL); sc = F0[FL].sum(axis=1)
VC = S[["is_anal", "score", "comfort", "vertical", "isolation", "planning"]].rename(columns={"score": "comfort_score"}).join(VAL).join(F0)
VC["score"] = sc; VC["cls"] = classify(sc); VC["in_scope"] = 1
VG = gpd.GeoDataFrame(VC.reset_index(), geometry=list(cg.values), crs=32637); wr(VG, P14, "viol_cells")
log("ячеек в счёте:", len(VG), "| флагов:", int(VG[FL].sum().sum()), VG[FL].sum().astype(int).to_dict())
log("классы:", VG.cls.value_counts().to_dict(), "| лидеры:", VG.sort_values(["score", "num"], ascending=[False, True])[["num", "score"]].head(10).values.tolist())
log("3.4 а/б/в:", int(VG.p3_4a.sum()), int(VG.p3_4b.sum()), int(VG.p3_4c.sum()))
# слои пунктов
wr(VG[VG.p1_1 == 1][["num", "comfort_score", "vertical", "isolation", "planning", "geometry"]], P14, "p1_1_cells")
wr(NON[["node", "podtip", "geometry"]], P14, "p1_2_nodes")
c_all = rd(K14, "cells"); wr(c_all[c_all.is_anal == 0][["num", "geometry"]], P14, "p1_3_cells")   # территории вне зафиксированных границ
wr(gpd.GeoDataFrame({"what": ["совмещение потоков"]}, geometry=[CM], crs=32637).explode(index_parts=False), P14, "p2_3_combined")
wr(pgp[["type", "zone", "problem", "geometry"]], P14, "p3_3_places")
SC = U(VG.geometry)
for nm, z in (("p3_4_competition", COMP), ("p3_4_uncontrolled", UNC), ("p3_4_abandoned", OSV["неосвоенная"])):
    d = gpd.GeoDataFrame(geometry=[z.intersection(SC)], crs=32637).explode(index_parts=False); d = d[d.area > 2]; d["area"] = d.area.round(1); wr(d, P14, nm)
pre = gpd.GeoDataFrame(geometry=[OSV["освоенная"].intersection(CTL).intersection(SC)], crs=32637).explode(index_parts=False); pre = pre[pre.area > 2]
pre["area"] = pre.area.round(1); wr(pre, P14, "pre_osv_ctl")
wr(VG[VG.comfort_score >= 0.665][["num", "comfort_score", "geometry"]], P14, "pre_comfort_cells")
wr(ent[ent.fix_class == "организован"][["node", "podtip", "geometry"]], P14, "pre_nodes")
wr(net[net.group == "высокая"][["ped", "geometry"]], P14, "pre_axes")
log("предпосылки: освоено и под контролем", round(pre.area.sum() / 1e4, 2), "га | комфортных", int((VG.comfort_score >= 0.665).sum()),
    "| организованных входов", int((ent.fix_class == "организован").sum()))
x = []
for k, z in (("контролируемая", CTL), ("частично контролируемая", PART), ("неконтролируемая", UNC)):
    x.append({"контроль": k, **{kk: round(OSV[kk].intersection(z).intersection(SC).area) for kk in OSV}})
XT = pd.DataFrame(x); log(XT.to_string(index=False))
pd.to_pickle(dict(VAL=VAL, FLAGS=F0, VC=VC, XT=XT, LOG=LOG, BASE=BASE), os.path.join(HERE, "results.pkl"))
open(os.path.join(HERE, "log_s3.txt"), "w", encoding="utf-8").write("\n".join(LOG) + "\n")

# ---------------- устойчивость: пороги и допущения
from scipy.stats import spearmanr
cc = rd(K14, "cells").set_index("num").loc[cg.index]
def comfort_var(vh=1.3, vl=0.6, vu=2.0, il=0.35, ih=0.65, sizeT=140):
    v = cc.vert_koef.apply(lambda q: 2 if vh <= q <= vu else (1 if vl <= q < vh else 0)); i = cc.iso_koef.apply(lambda q: 2 if q >= ih else (1 if q > il else 0))
    s = ((cc["size"] >= 25) & (cc["size"] <= sizeT)).astype(int) * 2
    return (v + i + s) / 6
VARS = [("базовые пороги", {}, {}), ("comfort_cut = 0.5", {"comfort_cut": 0.5}, {}), ("comfort_cut = 0.83", {"comfort_cut": 0.83}, {}),
        ("ent_non = 2", {"ent_non": 2}, {}), ("wear_n = 2", {"wear_n": 2}, {}), ("loading_m2 = 100", {"loading_m2": 100}, {}),
        ("danger_obj = 2", {"danger_obj": 2}, {}), ("combined_m = 40", {"combined_m": 40}, {}), ("transit_res_m = 40", {"transit_res_m": 40}, {}),
        ("comp_pct = 10", {"comp_pct": 10}, {}), ("unc_pct = 30", {"unc_pct": 30}, {}), ("unc_pct = 70", {"unc_pct": 70}, {}),
        ("unos_pct = 50", {"unos_pct": 50}, {}), ("size_T = 150", {}, {"sizeT": 150}), ("ih = 0.7", {}, {"ih": 0.7}), ("vl = 0.5", {}, {"vl": 0.5})]
c0 = classify(sc); sens = []; allsc = []
for name, p, cf in VARS:
    scv = comfort_var(**cf) if cf else S.score
    f = flags(VAL, p, scv)[FL]; s = f.sum(axis=1); cl = classify(s); allsc.append(s)
    sens.append(dict(вариант=name, флагов=int(f.values.sum()), высоких=int((cl == "высокая").sum()), сменили_класс=int((cl != c0).sum()),
                     rho=round(spearmanr(sc, s).correlation, 3), комфортных=int((scv >= p.get("comfort_cut", 0.67) - 0.005).sum()),
                     высокие=", ".join(str(n) for n in s[cl == "высокая"].sort_values(ascending=False).index)))
SENS = pd.DataFrame(sens); log(SENS[["вариант", "высоких", "сменили_класс", "rho", "высокие"]].to_string(index=False))
SA = pd.concat(allsc, axis=1); always = [n for n in sc.index if (SA.loc[n] >= 6).sum() >= len(VARS) - 2]
log("в высоком классе почти при всех вариантах (≥ N-2):", always)
biz2 = biz[(biz.danger == "опасный") & (biz.isolation == "открытый")].geometry
d_nog = VAL.copy(); d_nog["danger_obj"] = pd.Series({n: int(biz2.distance(g).le(6).sum()) for n, g in cg.items()})
w4p = w4[w4.src == "указан"]; d_now = VAL.copy(); d_now["wear40"] = pd.Series({n: int(w4p.distance(g).le(8).sum()) for n, g in cg.items()})
NONp = NON[NON.src.astype(str).str.startswith("обслед")]; d_ent = VAL.copy(); d_ent["nodes_non"] = pd.Series({n: int(NONp.distance(g).le(8).sum()) for n, g in cg.items()})
d_all = d_nog.copy(); d_all["wear40"] = d_now.wear40
def summ(name, d):
    f = flags(d)[FL]; s = f.sum(axis=1); cl = classify(s)
    return dict(вариант=name, флагов=int(f.values.sum()), выс=int((cl == "высокая").sum()), сред=int((cl == "средняя").sum()), низк=int((cl == "низкая").sum()),
                высокие=", ".join(f"{n} ({s[n]})" for n in s[cl == "высокая"].sort_values(ascending=False).index))
ASS = pd.DataFrame([summ("как есть", VAL), summ("мусорные площадки не опасны", d_nog), summ("износ только по данным", d_now),
                    summ("только входы с обследования", d_ent), summ("мусорки и износ вместе", d_all)])
log(ASS.to_string(index=False))
R = pd.read_pickle(os.path.join(HERE, "results.pkl")); R.update(SENS=SENS, ASS=ASS, ALWAYS=always, LOG=LOG); R.pop("flags", None)
pd.to_pickle(R, os.path.join(HERE, "results.pkl"))
open(os.path.join(HERE, "log_s3.txt"), "w", encoding="utf-8").write("\n".join(LOG) + "\n")
