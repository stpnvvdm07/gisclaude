# Слои площадок, стоянок и естественных покрытий из чертежа yacheiki_1_v9.dwg -> EPSG:32637, проверка и исправление геометрии.
# Вход: ents.jsonl (выгрузка ezdwg), konkovo_v12.gpkg / analiz_v12.gpkg (только чтение). Выход: pokrytiya_v9.gpkg + qa_v9.csv
import json, sys, math, functools, warnings
import numpy as np, pandas as pd, geopandas as gpd
from shapely.geometry import Polygon, MultiPolygon, LineString, Point
from shapely.ops import unary_union
from shapely.validation import make_valid
from pyproj import Transformer
warnings.filterwarnings("ignore")
import os
HERE = os.path.dirname(os.path.abspath(__file__))
# аргументы: [выгрузка ents.jsonl] [папка vector] [выходной gpkg]; по умолчанию - рядом со скриптом и в proektsem/vector
ENTS = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "dwg_v9_ents.jsonl")
VDIR = sys.argv[2] if len(sys.argv) > 2 else os.path.join(HERE, "..", "vector")
OUT = sys.argv[3] if len(sys.argv) > 3 else os.path.join(VDIR, "pokrytiya_v9.gpkg")
K, A = VDIR + "/konkovo_v12.gpkg", VDIR + "/analiz_v12.gpkg"
SRC = ("+proj=tmerc +lat_0=55.66666666667 +lon_0=37.5 +k=1 +x_0=12.268 +y_0=11.964 +ellps=bessel "
       "+towgs84=316.151,78.924,589.65,-1.57273,2.69209,2.34693,8.4507 +units=m +no_defs")   # строка чертежа из Методики, разд. 2
tr = Transformer.from_crs(SRC, "EPSG:32637", always_xy=True)
def T(cs):
    x, y = tr.transform([c[0] for c in cs], [c[1] for c in cs]); return list(zip(x, y))
def polys_only(g):
    g = make_valid(g)
    if isinstance(g, Polygon): return g
    parts = [p for p in getattr(g, "geoms", []) if isinstance(p, (Polygon, MultiPolygon))]
    return unary_union(parts) if parts else Polygon()
recs = [json.loads(l) for l in open(ENTS, encoding="utf-8")]
qa = []
def note(layer, what, n, m2=None, how=""):
    qa.append(dict(слой=layer, проверка=what, объектов=n, площадь_м2=None if m2 is None else round(m2), исправление=how))

blds = gpd.read_file(K, layer="buildings"); BLD = blds.buffer(0).union_all()
pg_gis = gpd.read_file(K, layer="playgrounds"); pk_gis = gpd.read_file(K, layer="parking"); gr_gis = gpd.read_file(K, layer="green")
cells = gpd.read_file(K, layer="cells"); bnd = gpd.read_file(K, layer="boundary").union_all()

# ---------------- 1. Площадки (PL_DETSKAYA, PL_SPORT, PL_VORKAUT, PL_SOBAKI)
TMAP = {"PL_DETSKAYA": "детская", "PL_SPORT": "спортивная", "PL_VORKAUT": "воркаут", "PL_SOBAKI": "для собак"}
rows = []
for r in recs:
    if r["layer"] not in TMAP: continue
    fix = ""
    if r["type"] == "LWPOLYLINE":
        cs = T(r["coords"])
        if not r["closed"]:
            gap = math.dist(cs[0], cs[-1]); fix = f"незамкнутая полилиния замкнута (разрыв {gap:.2f} м)"
        g = Polygon(cs)
    elif r["type"] == "CIRCLE":
        c = T([r["center"]])[0]; g = Point(c).buffer(r["r"], 32); fix = "круг -> полигон (32 сегмента на четверть)"
    else: continue
    if not g.is_valid: g = polys_only(g); fix = (fix + "; " if fix else "") + "make_valid"
    rows.append(dict(type=TMAP[r["layer"]], dwg_layer=r["layer"], dwg_handle=r["handle"], fix=fix, geometry=g))
PG = gpd.GeoDataFrame(rows, crs=32637)
# перенос атрибутов из ГИС по наибольшему перекрытию
for c in ["function", "danger", "isolation"]: PG[c] = None
PG["gis_fid"] = None; PG["iou_gis"] = 0.0
for i, g in PG.geometry.items():
    best = max(((j, g.intersection(q.buffer(0)).area / g.union(q.buffer(0)).area) for j, q in pg_gis.geometry.items()), key=lambda x: x[1])
    if best[1] > 0.5:
        PG.loc[i, ["function", "danger", "isolation"]] = pg_gis.loc[best[0], ["function", "danger", "isolation"]].values
        PG.loc[i, "gis_fid"] = int(best[0]); PG.loc[i, "iou_gis"] = round(best[1], 3)
PG["area"] = PG.area.round(1)
note("playgrounds_v9", "всего объектов (ГИС v12: 30)", len(PG), PG.area.sum())
note("playgrounds_v9", "незамкнутые полилинии", int(PG.fix.str.contains("незамкнут").sum()), None, "замкнуты")
note("playgrounds_v9", "совпадают с ГИС (IoU > 0,95)", int((PG.iou_gis > 0.95).sum()))
note("playgrounds_v9", "тип не совпал с ГИС", int(sum(PG["type"][i] != pg_gis["type"][PG.gis_fid[i]] for i in PG.index if PG.gis_fid[i] is not None)))
ovb = PG.geometry.intersection(BLD).area; note("playgrounds_v9", "перекрытие со зданиями", int((ovb > 1).sum()), ovb.sum())

# ---------------- 2. Стоянки (AVTOSTOYANKI)
rows = []
for r in recs:
    if r["layer"] != "AVTOSTOYANKI" or r["type"] != "LWPOLYLINE": continue
    g = Polygon(T(r["coords"])); g = g if g.is_valid else polys_only(g)
    rows.append(dict(dwg_handle=r["handle"], geometry=g))
PK = gpd.GeoDataFrame(rows, crs=32637)
n0 = len(PK)
# 2.1 точные дубли
wkb = PK.geometry.apply(lambda g: g.normalize().wkb); dup = wkb.duplicated()
note("parking_v9", "точные дубли", int(dup.sum()), PK[dup].area.sum(), "удалены")
PK = PK[~dup].reset_index(drop=True)
# 2.2 вложенные полигоны: контур, содержащий другой стоянку целиком -> вычитаем вложенный (паркинг-здание внутри открытой площадки)
PK["fix"] = ""
for i in PK.index:
    for j in PK.index:
        if i != j and PK.geometry[i].area > PK.geometry[j].area and PK.geometry[i].buffer(0.5).contains(PK.geometry[j]):
            a0 = PK.geometry[i].area
            PK.loc[i, "geometry"] = polys_only(PK.geometry[i].difference(PK.geometry[j]))
            PK.loc[i, "fix"] = f"вычтен вложенный контур handle {PK.dwg_handle[j]} ({a0 - PK.geometry[i].area:.0f} м²)"
            note("parking_v9", "контур содержит другой контур стоянки", 1, a0 - PK.geometry[i].area, "вложенный контур вычтен (как в ГИС: паркинг + открытая вокруг)")
# 2.3 атрибуты kind из ГИС по наибольшему перекрытию; новые - «открытая (новая в v9)»
PK["kind"] = None; PK["gis_fid"] = None; PK["iou_gis"] = 0.0; PK["status"] = None
for i, g in PK.geometry.items():
    cand = [(j, g.intersection(q.buffer(0)).area / g.union(q.buffer(0)).area) for j, q in pk_gis.geometry.items() if g.intersects(q.buffer(0))]
    if cand:
        j, iou = max(cand, key=lambda x: x[1])
        PK.loc[i, ["kind", "gis_fid", "iou_gis"]] = [pk_gis.kind[j], int(j), round(iou, 3)]
        PK.loc[i, "status"] = "как в ГИС" if iou > 0.9 else "контур изменён в v9"
    else:
        PK.loc[i, ["kind", "status"]] = ["открытая (вид не указан, допущение)", "новая в v9"]
# 2.4 перекрытие со зданиями: для открытых стоянок вычитаем здания, для гаражей и паркинга - оставляем (это и есть здания)
for i in PK.index:
    ov = PK.geometry[i].intersection(BLD).area
    if ov > 1:
        if str(PK.kind[i]).startswith(("гаражи", "здание-паркинг")):
            note("parking_v9", f"перекрытие со зданием (вид «{PK.kind[i]}»)", 1, ov, "оставлено: стоянка в здании / гаражные боксы")
        else:
            PK.loc[i, "geometry"] = polys_only(PK.geometry[i].difference(BLD))
            PK.loc[i, "fix"] = (PK.fix[i] + "; " if PK.fix[i] else "") + f"вычтены здания ({ov:.0f} м²)"
            note("parking_v9", "открытая стоянка заходит на здание", 1, ov, "здания вычтены")
PK["area"] = PK.area.round(1)
note("parking_v9", f"итого объектов (в чертеже {n0}, в ГИС v12: {len(pk_gis)})", len(PK), PK.area.sum())
for st in ["как в ГИС", "контур изменён в v9", "новая в v9"]:
    s = PK[PK.status == st]; note("parking_v9", f"статус: {st}", len(s), s.area.sum())

# ---------------- 3. Естественные покрытия (GREEN_AREAS, штриховки)
rows = []
for r in recs:
    if r["layer"] != "GREEN_AREAS" or r["type"] != "HATCH": continue
    rings = [Polygon(T(p["coords"])) for p in r["paths"] if len(p["coords"]) >= 3]
    rings = [polys_only(x) for x in rings]
    g = functools.reduce(lambda a, b: a.symmetric_difference(b), rings) if rings else Polygon()   # правило чёт-нечет, как у штриховки
    g = polys_only(g)
    rows.append(dict(dwg_handle=r["handle"], n_paths=len(rings), geometry=g))
NA = gpd.GeoDataFrame(rows, crs=32637)
raw_sum = NA.area.sum()
note("natural_v9", "штриховок (контуры чёт-нечет)", len(NA), raw_sum)
inv = sum(1 for r in recs if r["layer"] == "GREEN_AREAS" and r["type"] == "HATCH" and not functools.reduce(lambda a, b: a.symmetric_difference(b), [Polygon(T(p["coords"])) for p in r["paths"] if len(p["coords"]) >= 3]).is_valid)
note("natural_v9", "невалидные контуры (самопересечения)", inv, None, "make_valid")
U = unary_union(NA.geometry)
note("natural_v9", "взаимные перекрытия штриховок", int(len(NA)), raw_sum - U.area, "объединены (dissolve)")
pg_u = PG.union_all(); pk_u = PK.union_all()
ov_b, ov_pg, ov_pk = U.intersection(BLD).area, U.intersection(pg_u).area, U.intersection(pk_u).area
U2 = U.difference(BLD); note("natural_v9", "заходят на здания", None, ov_b, "здания вычтены")
U3 = U2.difference(pg_u); note("natural_v9", "заходят на площадки v9", None, ov_pg, "площадки вычтены (покрытие площадки - не естественное)")
U4 = U3.difference(pk_u); note("natural_v9", "заходят на стоянки v9", None, ov_pk, "стоянки вычтены")
parts = [p for p in (U4.geoms if hasattr(U4, "geoms") else [U4]) if isinstance(p, Polygon)]
sl = [p for p in parts if p.area < 2]; parts = [p for p in parts if p.area >= 2]
note("natural_v9", "осколки < 2 м² после вычитания", len(sl), sum(p.area for p in sl), "удалены")
NV = gpd.GeoDataFrame(geometry=parts, crs=32637)
# тип: в чертеже не различается; деревья - по кронам слоя green (ГИС, со спутника/съёмки), остальное - трава (допущение)
TREES = gr_gis[gr_gis["type"] == "деревья"].buffer(0).union_all()
tparts = []
for g in NV.geometry:
    t = g.intersection(TREES); o = g.difference(TREES)
    for geom, typ in ((t, "деревья"), (o, "трава")):
        for p in (geom.geoms if hasattr(geom, "geoms") else [geom]):
            if isinstance(p, Polygon) and p.area >= 2: tparts.append(dict(type=typ, type_src="кроны слоя green v12" if typ == "деревья" else "остальное (допущение: газон)", geometry=p))
NV = gpd.GeoDataFrame(tparts, crs=32637); NV["area"] = NV.area.round(1)
NV["in_boundary"] = NV.geometry.apply(lambda g: g.intersection(bnd).area / g.area > 0.5).astype(int)
note("natural_v9", "итог (после исправлений)", len(NV), NV.area.sum())
for t in ("деревья", "трава"): note("natural_v9", f"  в т.ч. {t}", int((NV["type"] == t).sum()), NV[NV["type"] == t].area.sum())
# сравнение с ГИС
G = gr_gis.buffer(0).union_all(); N = NV.union_all()
note("natural_v9 vs green v12", "площадь green v12", len(gr_gis), G.area)
note("natural_v9 vs green v12", "совпадает", None, N.intersection(G).area)
note("natural_v9 vs green v12", "есть только в v9 (добавлено)", None, N.difference(G).area)
note("natural_v9 vs green v12", "есть только в v12 (в v9 нет)", None, G.difference(N).area)
# по ячейкам анализа
viol = gpd.read_file(VDIR + "/problems_v12.gpkg", layer="viol_cells")
sc = cells.merge(viol[["num", "in_scope"]], on="num")
pc = []
for _, c in sc.iterrows():
    g = c.geometry.buffer(0); a12 = g.intersection(G).area; a9 = g.intersection(N).area
    pc.append(dict(num=c.num, in_scope=c.in_scope, area=round(g.area), green_v12_m2=round(a12), natural_v9_m2=round(a9),
                   delta_m2=round(a9 - a12), share_v12=round(100 * a12 / g.area, 1), share_v9=round(100 * a9 / g.area, 1)))
PC = pd.DataFrame(pc)
# освоенность: какая часть «иной поверхности, принятой как покрытие» по v9 - естественное покрытие
osv = gpd.read_file(A, layer="osvoennost"); osv["geometry"] = osv.buffer(0)
pk_ = osv[(osv.B_why == "покрытие (принято)")]
note("освоенность v12", "«иная поверхность ≥5 м = покрытие» (B_why), геом. площадь", len(pk_), pk_.area.sum())
note("освоенность v12", "  из неё по v9 - естественное покрытие", None, pk_.geometry.intersection(N).area.sum())
note("освоенность v12", "  из неё по v9 - стоянки", None, pk_.geometry.intersection(pk_u).area.sum())


# ---------------- 4. слои для ручной проверки (расхождения v9 / v12 >= 200 м²) и наложение на дорожки
trees = gpd.read_file(K, layer="trees")
def parts_of(g, min_a=200):
    out = []
    for p in (g.geoms if hasattr(g, "geoms") else [g]):
        if isinstance(p, Polygon) and p.area >= min_a: out.append(p)
    return out
chk = []
for kind, geom in (("только в green v12 (в v9 нет покрытия)", G.difference(N).intersection(bnd)), ("только в natural v9 (в v12 нет)", N.difference(G).intersection(bnd))):
    for p in parts_of(geom):
        nt = int(trees.within(p).sum())
        cn = [int(n) for n, cg in zip(cells.num, cells.geometry) if cg.intersection(p).area > 0.5 * p.area]
        chk.append(dict(kind=kind, area=round(p.area), trees_survey=nt, trees_per_100m2=round(100 * nt / p.area, 2), cell=cn[0] if cn else None, geometry=p))
CHK = gpd.GeoDataFrame(chk, crs=32637)
CHK.to_file(OUT, layer="check_v9_vs_v12", driver="GPKG")
for kind, g in CHK.groupby("kind"):
    note("проверка", kind + " (участки >= 200 м²)", len(g), g.area.sum(), "проверить по фото/спутнику")
net = gpd.read_file(A, layer="network")
HW = {"дорожка": 0.75, "тротуар": 0.75, "тропа": 0.75, "лестница": 0.75, "переход": 2.0, "проезд": 2.0}
paths = unary_union([g.buffer(HW.get(t, 0.75), cap_style=2) for g, t in zip(net.geometry, net["type"])])
note("natural_v9", "наложение на оси дорожек/проездов (полуширина по типу, проезд 2 м)", None, N.intersection(paths).area, "не исправлялось: ширины условные (Методика, разд. 3)")
note("green v12", "наложение на оси дорожек/проездов (то же правило)", None, G.intersection(paths).area, "")
PG.to_file(OUT, layer="playgrounds_v9", driver="GPKG")
PK.to_file(OUT, layer="parking_v9", driver="GPKG")
NV.to_file(OUT, layer="natural_v9", driver="GPKG")
cells_out = sc[["num", "in_scope", "geometry"]].merge(PC.drop(columns=["in_scope"]), on="num")
gpd.GeoDataFrame(cells_out, crs=32637).to_file(OUT, layer="cells_natural_compare", driver="GPKG")
pd.DataFrame(qa).to_csv(os.path.join(HERE, "pokrytiya_v9_qa.csv"), index=False, encoding="utf-8-sig")
PC.to_csv(os.path.join(HERE, "pokrytiya_v9_cells.csv"), index=False, encoding="utf-8-sig")
pd.set_option("display.width", 250); pd.set_option("display.max_colwidth", 90)
print(pd.DataFrame(qa).to_string(index=False))
print(PK[["dwg_handle", "kind", "status", "iou_gis", "area", "fix"]].to_string())
big = PC[(PC.in_scope == 1) & (PC.delta_m2.abs() >= 500)].sort_values("delta_m2")
print("ячейки анализа с |Δ| ≥ 500 м²:\n", big.to_string(index=False))
