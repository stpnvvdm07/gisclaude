# Сборка v13: konkovo_v13 / analiz_v13 / problems_v13 со всеми исправлениями аудита v12 (AUDIT_v12.md).
#  konkovo: зелень и стоянки по DWG v9 (build_konkovo_v13.py), make_valid зданий, классы размеров ячеек 7 и 32,
#           вертикаль ячейки 1, площади/коэффициенты ячеек по геометрии, тип ограждений, bld_id бизнеса 55с3,
#           привязка узлов входа к ячейкам строго по 8 м.
#  analiz:  дубль фасада, make_valid, освоенность заново на новой зелени/стоянках (правила v12, площади по геометрии,
#           «полоса уже 5 м» = после эрозии на 2,5 м остаётся < 30 % участка), osv_cells.
#  problems: 11 флагов по геометрии + подпункты 3.4а/б/в и счёт без 1.3; слои пунктов и предпосылок.
# Запуск: python build_v13.py   (пути относительно папки скрипта; v12 и v10 не меняются)
import os, runpy, shutil, warnings
import numpy as np, pandas as pd, geopandas as gpd, pyogrio
from shapely.geometry import Polygon, MultiPolygon
from shapely.ops import unary_union
from shapely.validation import make_valid
warnings.filterwarnings("ignore")
HERE = os.path.dirname(os.path.abspath(__file__)); V = os.path.join(HERE, "..", "vector")
K12, A12, P12 = (os.path.join(V, f"{n}_v12.gpkg") for n in ("konkovo", "analiz", "problems"))
K13, A13, P13 = (os.path.join(V, f"{n}_v13.gpkg") for n in ("konkovo", "analiz", "problems"))
SLOPES = os.path.join(V, "proektbase", "slopesandwalls.gpkg")
rd = lambda f, l: gpd.read_file(f, layer=l)
def wr(df, f, l): pyogrio.write_dataframe(df, f, layer=l, driver="GPKG", append=False)
def polys(g):
    g = make_valid(g)
    if isinstance(g, (Polygon, MultiPolygon)): return g
    return unary_union([p for p in getattr(g, "geoms", []) if isinstance(p, (Polygon, MultiPolygon))])
def fix_layer(df):
    if len(df) and df.geom_type.str.contains("Polygon").any():
        df["geometry"] = df.geometry.apply(lambda g: g if g is None or g.is_valid else polys(g))
    return df
LOG = []
def log(*a): s = " ".join(str(x) for x in a); LOG.append(s); print(s)

# ======================= konkovo_v13
runpy.run_path(os.path.join(HERE, "build_konkovo_v13.py"))          # копия v12 + green/parking из DWG v9
b = rd(K13, "buildings"); inv = ~b.is_valid
log("здания: исправлены самопересечения", int(inv.sum()), "ids", b.id[inv].dropna().astype(int).tolist())
b.loc[inv, "geometry"] = b.geometry[inv].apply(polys); wr(b, K13, "buildings")

c = rd(K13, "cells")
c.loc[c.num == 7, "planning"] = "Комфортная"; c.loc[c.num == 32, "planning"] = "Некомфортная"
c["area"] = c.area.round().astype(int); c["perimeter"] = c.length.round().astype(int)
c["vert_koef"] = (c.fasad_area / c.area).round(2); c["iso_koef"] = (c.fasad_len / c.perimeter).round(4)
vk = c.fasad_area / c.geometry.area; ik = c.fasad_len / c.geometry.length
VC = {2: "Высокий", 1: "Средний", 0: "Низкий"}
c["vertical"] = vk.apply(lambda x: VC[2 if 1.3 <= x <= 2 else (1 if 0.6 <= x < 1.3 else 0)])
c["isolation"] = ik.apply(lambda x: VC[2 if x >= 0.65 else (1 if x > 0.35 else 0)])
pts = {"Высокий": 2, "Средний": 1, "Низкий": 0}
c["score"] = ((c.vertical.map(pts) + c.isolation.map(pts) + (c.planning == "Комфортная") * 2) / 6).round(2)
c["comfort"] = np.where(c.score >= 0.67 - 0.005, "Комфортная", "Некомфортная")
wr(c, K13, "cells"); log("ячейки: размеры 7/32 исправлены; комфортных в 52:", int((c.comfort == "Комфортная").sum()))
f = rd(K13, "fences"); f.loc[f.podtip.isna(), "podtip"] = "Ограждение — тип не указан"; wr(f, K13, "fences")
bz = rd(K13, "business"); m = bz.adress.str.contains("55с3", na=False) & (bz.bld_id != 36)
bz.loc[m, "edit_note"] = (bz.edit_note[m].fillna("") + "; bld_id " + bz.bld_id[m].astype(str) + " -> 36 (адрес 55с3)").str.strip("; ")
bz.loc[m, "bld_id"] = 36; wr(bz, K13, "business"); log("бизнес: bld_id по адресу 55с3 исправлен у", int(m.sum()))

viol12 = rd(P12, "viol_cells").set_index("num")
ent_b = rd(K13, "entrances_buildings")
cg = c.set_index("num").geometry
pod = pd.Series({n: int(ent_b.distance(g).le(8).sum()) for n, g in cg.items()})
scope = (c.set_index("num").is_anal == 1) | (pod > 0)
nodes = rd(K13, "entry_nodes")
def node_cells(pt):
    near = [n for n, g in cg.items() if g.distance(pt) <= 8]
    fixed = [n for n in near if c.set_index("num").is_anal[n] == 1]
    return fixed if fixed else [n for n in near if scope[n]]
nodes["cells"] = nodes.geometry.apply(lambda p: ",".join(str(n) for n in node_cells(p)))
wr(nodes, K13, "entry_nodes"); log("узлы: привязка к ячейкам строго 8 м")

# ======================= analiz_v13
shutil.copyfile(A12, A13)
for name, _ in pyogrio.list_layers(A13):
    d = rd(A13, name); n0 = (~d.is_valid).sum() if len(d) else 0
    if name == "facades":
        w = d.geometry.apply(lambda g: g.normalize().wkb); d = d[~w.duplicated()].copy()
        log("фасады: удалено дублей", int(w.duplicated().sum()))
    if n0: d = fix_layer(d); log(f"{name}: make_valid {int(n0)}")
    if n0 or name == "facades": wr(d, A13, name)

o12 = rd(A12, "osvoennost"); o12["geometry"] = o12.buffer(0)
bld = unary_union(rd(K13, "buildings").geometry)
pk12 = unary_union(rd(K12, "parking").buffer(0)); pk13 = unary_union(rd(K13, "parking").buffer(0))
F = unary_union(o12.geometry).union(pk12).difference(pk13).difference(bld)          # свободная территория без дорог, стоянок, зданий
pg = rd(K13, "playgrounds"); pg["geometry"] = pg.buffer(0); PG = unary_union(pg.geometry)
gr = rd(K13, "green")
kinds = [gpd.GeoDataFrame({"kind": "площадка:" + pg["type"]}, geometry=pg.geometry.intersection(F), crs=32637)]
for t in ("деревья", "трава"):
    kinds.append(gpd.GeoDataFrame({"kind": [t]}, geometry=[unary_union(gr[gr["type"] == t].geometry).difference(PG).intersection(F)], crs=32637))
used = unary_union([g for k in kinds for g in k.geometry])
kinds.append(gpd.GeoDataFrame({"kind": ["прочее"]}, geometry=[F.difference(used)], crs=32637))
KD = pd.concat(kinds, ignore_index=True).explode(index_parts=False)
KD = KD[KD.area > 0.5].reset_index(drop=True)
pdn = rd(K13, "people_dens"); man = rd(K13, "osv_manual"); excl = rd(K13, "cells_excluded")
cut = pd.concat([c[["num", "geometry"]].rename(columns={"num": "cell"}),], ignore_index=True)
O = gpd.overlay(KD, cut, how="identity", keep_geom_type=True)
for lay in (pdn[["geometry"]], man[["geometry"]], excl[["geometry"]]):
    O = gpd.overlay(O, lay.assign(_c=1)[["_c", "geometry"]], how="identity", keep_geom_type=True).drop(columns="_c")
O = O.explode(index_parts=False); O = O[O.area >= 1].reset_index(drop=True)
O["cell"] = O.cell.fillna(0).astype(int)
SL = unary_union(rd(SLOPES, "slopesandwalls").geometry).buffer(6)
MANY = unary_union(pdn[pdn.dens == "много"].geometry); FEW = unary_union(pdn[pdn.dens == "мало"].geometry)
MAN = unary_union(man.buffer(0)); EXC = unary_union(excl.buffer(0))
net = rd(A13, "network"); LINK = unary_union(net[net.ped >= 2].geometry).buffer(10)
POD = unary_union(ent_b.geometry).buffer(30)
sc_cells = set(scope[scope].index)
def sh(g, z): return g.intersection(z).area / g.area if g.area else 0
rows = []
for g, k, cell in zip(O.geometry, O.kind, O.cell):
    core = g.buffer(-2.5).area / g.area
    slope = sh(g, SL); m_ = sh(g, MAN); dm, dl = sh(g, MANY), sh(g, FEW); path, podp = sh(g, LINK), sh(g, POD)
    if cell not in sc_cells: note = "вне ячеек анализа"
    elif sh(g, EXC) > 0.5: note = "территория учреждения (школа, детсад)"
    elif k == "прочее" and core < 0.3: note = "полоса уже 5 м (отмостка, обочина)"
    else: note = None
    if m_ >= 0.5: B, bw = 0, "контур команды «неосвоенная»"
    elif slope >= 0.3: B, bw = 0, "откос / подпорная стенка (≥30 % площади)"
    elif k.startswith("площадка"): B, bw = 1, "площадка"
    elif k in ("деревья", "трава"): B, bw = 1, "озеленение"
    else: B, bw = 1, "покрытие (принято)"
    if m_ >= 0.5: U, uw = 0, "контур команды «неосвоенная»"
    elif dl >= 0.5: U, uw = 0, "наблюдение: мало людей"
    elif dm >= 0.5: U, uw = 1, "наблюдение: много людей"
    elif k.startswith("площадка"): U, uw = 1, "место поведения (площадка)"
    elif path >= 0.25: U, uw = 1, "у пешеходной связи (≥2 путей дерева)"
    elif podp >= 0.25: U, uw = 1, "ближняя зона подъезда (30 м)"
    else: U, uw = 0, "нет признаков использования"
    if note: cls = "не оценивается"
    elif m_ >= 0.5 and not k.startswith("площадка"): cls = "неосвоенная"
    else: cls = "освоенная" if B and U else ("частично освоенная" if B or U else "неосвоенная")
    rows.append(dict(kind=k, area=round(g.area, 1), cell=cell, in_scope=int(cell in sc_cells), B=B, B_why=bw, U=U, U_why=uw,
                     slope_pct=round(100 * slope), path_pct=round(100 * path), pod_pct=round(100 * podp), cls=cls, note=note, geometry=g))
OSV = gpd.GeoDataFrame(rows, crs=32637); wr(OSV, A13, "osvoennost")
tot = OSV.groupby("cls").area.sum(); ass = tot.drop("не оценивается").sum()
log("освоенность v13 (м²):", tot.round().to_dict(), "доли:", (100 * tot.drop("не оценивается") / ass).round(1).to_dict())

LZ = unary_union(rd(K13, "loading_zones").buffer(0)); oc12 = rd(A12, "osv_cells").set_index("num")
ocr = []
for n, g in cg.items():
    s = OSV[(OSV.cell == n) & (OSV.cls != "не оценивается")]; a = s.area.sum()
    v = {k: s[s.cls == k].area.sum() for k in ("освоенная", "частично освоенная", "неосвоенная")}
    ocr.append(dict(num=n, is_anal=int(c.set_index("num").is_anal[n]), in_scope=int(scope[n]), area=round(g.area), assessed_m2=round(a),
                    osv_m2=round(v["освоенная"]), part_m2=round(v["частично освоенная"]), unosv_m2=round(v["неосвоенная"]),
                    osv_pct=round(100 * v["освоенная"] / a, 1) if a else None, part_pct=round(100 * v["частично освоенная"] / a, 1) if a else None,
                    unosv_pct=round(100 * v["неосвоенная"] / a, 1) if a else None, parking_m2=round(g.intersection(pk13).area),
                    loading_m2=round(g.intersection(LZ).area), nodes_n=oc12.nodes_n[n], nodes_org=oc12.nodes_org[n], nodes_non=oc12.nodes_non[n], geometry=g))
OC = gpd.GeoDataFrame(ocr, crs=32637); wr(OC, A13, "osv_cells")

# ======================= problems_v13
shutil.copyfile(P12, P13)
for name, _ in pyogrio.list_layers(P13):
    d = rd(P13, name)
    if len(d) and (~d.is_valid).any(): wr(fix_layer(d), P13, name)
cs = c.set_index("num").score
ext_non = nodes[(nodes.in_12 == "да") & (nodes.fix_class == "не организован")]
nodes_non = pd.Series(0, index=cg.index)
for cl in ext_non.cells:
    for n in [int(x) for x in str(cl).split(",") if x.strip()]: nodes_non[n] += 1
bb = rd(K13, "buildings"); bb = bb[bb.id.notna()].copy()
def wv(r):
    if pd.notna(r["Степень изношенности"]): return float(r["Степень изношенности"]), "указан"
    t = r["Наша оценка изношенности"]
    if isinstance(t, str):
        import re; a = [float(x) for x in re.findall(r"\d+", t)]
        if a: return sum(a) / len(a) / 100, "оценка команды"
    return np.nan, None
bb[["wear", "wsrc"]] = bb.apply(lambda r: pd.Series(wv(r)), axis=1)
W40 = bb[bb.wear >= 0.40 - 1e-9]
wear40 = pd.Series({n: int(W40.distance(g).le(8).sum()) for n, g in cg.items()})
loading_m2 = pd.Series({n: g.intersection(LZ).area for n, g in cg.items()})
bzn = rd(K13, "business"); garb = rd(K13, "garbage")
dz = pd.concat([bzn[(bzn.danger == "опасный") & (bzn.isolation == "открытый")].geometry, garb.geometry])
danger_obj = pd.Series({n: int(dz.distance(g).le(6).sum()) for n, g in cg.items()})
COMB = unary_union(net[(net.razdel == "по проезжей части") & ((net.group == "высокая") | (net.vgroup == "высокая"))].geometry)
combined_m = pd.Series({n: g.intersection(COMB).length for n, g in cg.items()})
tr = rd(A13, "transit"); cz = rd(A13, "control_zones"); cz["geometry"] = cz.buffer(0)
RES = unary_union(cz[cz["type"].isin(["АЖ", "ПЖ"])].geometry); TRH = unary_union(tr[tr.cls == "высокая"].geometry).intersection(RES)
transit_res_m = pd.Series({n: g.intersection(TRH).length for n, g in cg.items()})
TRP = unary_union(tr[(tr.cls == "высокая") & (tr["mode"] == "пешеходный")].geometry)
serv = bzn[(bzn.function == "обслуживающий")]; serv = serv[serv.distance(TRP) <= 15]
biz_transit = pd.Series({n: int(serv.distance(g).le(6).sum()) for n, g in cg.items()})
pz = rd(A13, "playgrounds_zones"); pgo = pz[pz.problem.notna()]
pg_out = pd.Series({n: int(pgo.intersects(g).sum()) for n, g in cg.items()})
COMP = unary_union(rd(A13, "competition").buffer(0)); ctl = rd(A13, "control"); ctl["geometry"] = ctl.buffer(0)
UNC = unary_union(ctl[ctl["type"] == "неконтролируемая"].geometry); CTL = unary_union(ctl[ctl["type"] == "контролируемая"].geometry)
comp_pct = pd.Series({n: 100 * g.intersection(COMP).area / g.area for n, g in cg.items()})
unc_pct = pd.Series({n: 100 * g.intersection(UNC).area / g.area for n, g in cg.items()})
unosv_pct = OC.set_index("num").unosv_pct
fav = rd(P12, "pre_fav_closed")
fav_closed = pd.Series({n: int(fav.distance(g).le(6).sum()) for n, g in cg.items()})

VAL = pd.DataFrame(dict(pod=pod, nodes_non=nodes_non, wear40=wear40, loading_m2=loading_m2.round(), danger_obj=danger_obj,
                        combined_m=combined_m.round(), transit_res_m=transit_res_m.round(), biz_transit=biz_transit, pg_out=pg_out,
                        comp_pct=comp_pct.round(1), unc_pct=unc_pct.round(1), unosv_pct=unosv_pct, fav_closed=fav_closed))
BASE = dict(comfort_cut=0.67, ent_non=1, wear_n=1, loading_m2=50, danger_obj=1, combined_m=20, transit_res_m=20,
            biz_transit=1, comp_pct=5, unc_pct=50, unos_pct=25)
def flags(d, p=None, score=None):
    p = {**BASE, **(p or {})}; s_ = cs if score is None else score
    f = pd.DataFrame(index=cg.index)
    f["p1_1"] = s_ < p["comfort_cut"] - 0.005; f["p1_2"] = d.nodes_non >= p["ent_non"]
    f["p1_3"] = c.set_index("num").is_anal == 0; f["p1_4"] = d.wear40 >= p["wear_n"]
    f["p2_1"] = d.loading_m2 >= p["loading_m2"]; f["p2_2"] = d.danger_obj >= p["danger_obj"]
    f["p2_3"] = d.combined_m >= p["combined_m"]; f["p3_1"] = (d.transit_res_m >= p["transit_res_m"]) & (d.pod > 0)
    f["p3_2"] = d.biz_transit >= p["biz_transit"]; f["p3_3"] = d.pg_out >= 1
    f["p3_4a"] = d.comp_pct >= p["comp_pct"]; f["p3_4b"] = d.unc_pct >= p["unc_pct"]; f["p3_4c"] = d.unosv_pct.fillna(0) >= p["unos_pct"]
    f["p3_4"] = f.p3_4a | f.p3_4b | f.p3_4c
    return f.astype(int)
FL = ["p1_1", "p1_2", "p1_3", "p1_4", "p2_1", "p2_2", "p2_3", "p3_1", "p3_2", "p3_3", "p3_4"]
def classify(s): return pd.cut(s, [-1, 3, 5, 99], labels=["низкая", "средняя", "высокая"]).astype(str)
F0 = flags(VAL); sc_ = F0[FL].sum(axis=1)
VC_ = pd.DataFrame(index=cg.index); VC_["num"] = cg.index; VC_["in_scope"] = scope.astype(int); VC_["is_anal"] = c.set_index("num").is_anal
VC_ = VC_.join(VAL)
VC_["comfort_score"] = cs
for col in F0.columns: VC_[col] = F0[col]
VC_["score"] = sc_; VC_["cls"] = classify(sc_); VC_["score_wo13"] = sc_ - F0.p1_3; VC_["cls_wo13"] = classify(VC_.score_wo13)
out_cols = [x for x in VC_.columns if x not in ("num",)]
VC_.loc[~scope, ["score", "cls", "comfort_score", "score_wo13", "cls_wo13"] + list(F0.columns)] = None
VC_.loc[~scope, "p1_3"] = (c.set_index("num").is_anal == 0)[~scope].astype(int)
VG = gpd.GeoDataFrame(VC_.reset_index(drop=True), geometry=list(cg.values), crs=32637)
wr(VG, P13, "viol_cells")
S = VG[VG.in_scope == 1]
log("флаги v13:", int(S[FL].sum().sum()), S[FL].sum().astype(int).to_dict())
log("классы:", S.cls.value_counts().to_dict(), "| без 1.3:", S.cls_wo13.value_counts().to_dict())
log("лидеры:", S.sort_values("score", ascending=False)[["num", "score"]].head(9).values.tolist())
log("3.4а/б/в:", int(S.p3_4a.sum()), int(S.p3_4b.sum()), int(S.p3_4c.sum()))
# слои пунктов
wr(gpd.GeoDataFrame(S[S.p1_1 == 1][["num", "comfort_score", "geometry"]], crs=32637), P13, "p1_1_cells")
wr(gpd.GeoDataFrame(S[S.comfort_score >= 0.665][["num", "comfort_score", "geometry"]], crs=32637), P13, "pre_comfort_cells")
wr(ext_non.copy(), P13, "p1_2_nodes")
SC = unary_union(S.geometry)
ab = OSV[(OSV.cls == "неосвоенная") & (OSV.in_scope == 1)][["geometry"]].copy(); ab["area"] = ab.area.round(1); wr(ab, P13, "p3_4_abandoned")
un = gpd.GeoDataFrame(geometry=[UNC.intersection(SC)], crs=32637).explode(index_parts=False); un = un[un.area > 1]; un["area"] = un.area.round(1); wr(un, P13, "p3_4_uncontrolled")
po = OSV[(OSV.cls == "освоенная") & (OSV.in_scope == 1)].geometry.intersection(CTL)
po = gpd.GeoDataFrame(geometry=po, crs=32637).explode(index_parts=False); po = po[po.area > 1]; po["area"] = po.area.round(1); wr(po, P13, "pre_osv_ctl")
w4 = W40[["id", "Адрес / ориентир", "wear", "wsrc", "geometry"]].rename(columns={"Адрес / ориентир": "addr", "wsrc": "src"}); wr(w4, P13, "p1_4_wear")
log("неосвоенная в ячейках:", round(ab.area.sum()), "| неконтр. в ячейках:", round(un.area.sum()), "| освоенная+контр.:", round(po.area.sum()))
# кросс-таблица контроль × освоенность
x = []
for t in ("контролируемая", "частично контролируемая", "неконтролируемая"):
    z = unary_union(ctl[ctl["type"] == t].geometry); a = OSV[(OSV.in_scope == 1) & (OSV.cls != "не оценивается")]
    x.append({"контроль": t, **{k: round(a[a.cls == k].geometry.intersection(z).area.sum()) for k in ("освоенная", "частично освоенная", "неосвоенная")}})
XT = pd.DataFrame(x); log(XT.to_string(index=False))

# ======================= чувствительность и допущения
from scipy.stats import spearmanr
def comfort_var(vh=1.3, vl=0.6, vu=2.0, il=0.35, ih=0.65, sizeT=140):
    v = vk.fillna(0).apply(lambda q: 2 if vh <= q <= vu else (1 if vl <= q < vh else 0)); i = ik.apply(lambda q: 2 if q >= ih else (1 if q > il else 0))
    s = ((c["size"] >= 25) & (c["size"] <= sizeT)).astype(int) * 2
    return pd.Series(((v + i + s) / 6).values, index=c.num)
VARS = [("базовые пороги", {}, {})] + [(f"comfort_cut = {v}", {"comfort_cut": v}, {}) for v in (0.5, 0.83)] + \
    [("ent_non = 2", {"ent_non": 2}, {}), ("wear_n = 2", {"wear_n": 2}, {})] + [(f"loading_m2 = {v}", {"loading_m2": v}, {}) for v in (25, 100)] + \
    [("danger_obj = 2", {"danger_obj": 2}, {})] + [(f"combined_m = {v}", {"combined_m": v}, {}) for v in (10, 40)] + \
    [(f"transit_res_m = {v}", {"transit_res_m": v}, {}) for v in (10, 40)] + [("biz_transit = 2", {"biz_transit": 2}, {})] + \
    [(f"comp_pct = {v}", {"comp_pct": v}, {}) for v in (2, 10)] + [(f"unc_pct = {v}", {"unc_pct": v}, {}) for v in (30, 70)] + \
    [(f"unos_pct = {v}", {"unos_pct": v}, {}) for v in (10, 50)] + [(f"vl = {v}", {}, {"vl": v}) for v in (0.5, 0.7)] + \
    [(f"vh = {v}", {}, {"vh": v}) for v in (1.2, 1.4)] + [(f"vu = {v}", {}, {"vu": v}) for v in (1.8, 2.2)] + \
    [(f"il = {v}", {}, {"il": v}) for v in (0.3, 0.4)] + [(f"ih = {v}", {}, {"ih": v}) for v in (0.6, 0.7)] + \
    [(f"size_T = {v}", {}, {"sizeT": v}) for v in (130, 150)]
s0 = sc_[scope]; c0 = classify(s0); sens = []; allc = []
for name, p, cf in VARS:
    scv = comfort_var(**cf) if cf else cs
    f = flags(VAL, p, scv)[FL][scope]; s = f.sum(axis=1); cl = classify(s); allc.append(cl)
    sens.append(dict(вариант=name, флагов=int(f.values.sum()), высоких=int((cl == "высокая").sum()), сменили_класс=int((cl != c0).sum()),
                     rho=round(spearmanr(s0, s).correlation, 3), комфортных=int((scv[scope] >= p.get("comfort_cut", 0.67) - 0.005).sum())))
SENS = pd.DataFrame(sens); CC = pd.concat(allc, axis=1)
SC_ALL = pd.concat([flags(VAL, p, comfort_var(**cf) if cf else cs)[FL][scope].sum(axis=1) for _, p, cf in VARS], axis=1)
STAB = pd.DataFrame({"Ячейка": s0.index, "Счёт": s0.values, "Минимум": SC_ALL.min(axis=1).values, "Максимум": SC_ALL.max(axis=1).values})
STAB["Размах"] = STAB.Максимум - STAB.Минимум; STAB["Класс устойчив"] = np.where(CC.nunique(axis=1).values > 1, "нет", "да")
log("чувствительность: ρ min", SENS.rho.min(), "сменили max", SENS.сменили_класс.max(), "высоких", SENS.высоких.min(), "-", SENS.высоких.max())
log("неустойчивы:", STAB[STAB["Класс устойчив"] == "нет"].Ячейка.tolist())
# допущения
def summ(name, d, score=None):
    f = flags(d, None, score)[FL][scope]; s = f.sum(axis=1); cl = classify(s)
    return dict(вариант=name, флагов=int(f.values.sum()), **{k: int(f[k].sum()) for k in ("p1_2", "p1_4", "p2_2")},
                низк=int((cl == "низкая").sum()), сред=int((cl == "средняя").sum()), выс=int((cl == "высокая").sum()),
                высокие=", ".join(f"{n} ({s[n]})" for n in s[cl == "высокая"].sort_values(ascending=False).index))
e = rd(K13, "entries_territory")
def nn_with(org):
    ee = e.assign(org=org); no = ee[ee.in_12 == "да"].groupby("node").org.all(); out = pd.Series(0, index=cg.index)
    for _, r in nodes[nodes.in_12 == "да"].iterrows():
        if not no[r.node]:
            for n in [int(x) for x in str(r.cells).split(",") if x.strip()]: out[n] += 1
    return out
org = e.degree.isin(["высокая", "средняя"]); vj = (e.podtip == "Вход — въезд") & (e.degree == "низкая") & (e.in_12 == "да"); fl = e.src == "замер потока"
dz2 = bzn[(bzn.danger == "опасный") & (bzn.isolation == "открытый")].geometry
d_nog = VAL.copy(); d_nog["danger_obj"] = pd.Series({n: int(dz2.distance(g).le(6).sum()) for n, g in cg.items()})
W40p = W40[W40.wsrc == "указан"]; d_now = VAL.copy(); d_now["wear40"] = pd.Series({n: int(W40p.distance(g).le(8).sum()) for n, g in cg.items()})
d_vj = VAL.copy(); d_vj["nodes_non"] = nn_with(org | vj); d_fl = VAL.copy(); d_fl["nodes_non"] = nn_with(org | fl)
d_all = d_nog.copy(); d_all["wear40"] = d_now.wear40; d_all["nodes_non"] = d_vj.nodes_non
ASS = pd.DataFrame([summ("база v13", VAL), summ("без 14 мусорных площадок", d_nog), summ("износ только опубликованный", d_now),
                    summ("16 въездов — организованы", d_vj), summ("без 6 входов из замеров потока", d_fl), summ("все три допущения сняты", d_all)])
log(ASS.to_string(index=False))
pd.to_pickle(dict(VAL=VAL, FLAGS=F0, VC=VC_, SENS=SENS, STAB=STAB, ASS=ASS, XT=XT, OSVT=tot, LOG=LOG), os.path.join(HERE, "v13_results.pkl"))
open(os.path.join(HERE, "build_v13_log.txt"), "w", encoding="utf-8").write("\n".join(LOG) + "\n")
