# Независимый пересчёт флагов 1.1-3.4 по правилам листа «Методика счёта» (v12) из исходных слоёв.
import os, re, sys, warnings, json
import numpy as np, pandas as pd, geopandas as gpd
from shapely.ops import unary_union
warnings.filterwarnings("ignore")
V = os.environ.get("VDIR", os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "vector"))
K, A, P = (os.path.join(V, f) for f in ("konkovo_v12.gpkg", "analiz_v12.gpkg", "problems_v12.gpkg"))
rd = lambda f, l: gpd.read_file(f, layer=l)

cells = rd(K, "cells").set_index("num").sort_index()
cells["geometry"] = cells.buffer(0)
CA = cells.area
viol = rd(P, "viol_cells").set_index("num").sort_index()
ent_b = rd(K, "entrances_buildings")
blds = rd(K, "buildings"); blds["geometry"] = blds.buffer(0)

# --- набор ячеек: is_anal = 1 или подъезд в 8 м
pod = pd.Series({n: int(ent_b.distance(g).le(8).sum()) for n, g in cells.geometry.items()})
pod_in = pd.Series({n: int(ent_b.within(g).sum()) for n, g in cells.geometry.items()})
scope = (cells.is_anal == 1) | (pod > 0)

# --- 1.1 комфорт (поля ячейки; классы по методике, размеры - по полю size)
def vcls(x, hi=1.3, lo=0.6, up=2.0):
    return 2 if hi <= x <= up else (1 if lo <= x < hi else 0)
def icls(x, lo=0.35, hi=0.65):
    return 2 if x >= hi else (1 if x > lo else 0)
def comfort(vh=1.3, vl=0.6, vu=2.0, il=0.35, ih=0.65, sizeT=140, size_from="size"):
    vk = (cells.fasad_area / CA).fillna(0)
    ik = cells.fasad_len / cells.length
    v = vk.apply(lambda x: vcls(x, vh, vl, vu)); i = ik.apply(lambda x: icls(x, il, ih))
    if size_from == "size":
        s = ((cells["size"] >= 25) & (cells["size"] <= sizeT)).astype(int) * 2
    else:  # как в данных (поле planning)
        s = (cells.planning == "Комфортная").astype(int) * 2
    return (v + i + s) / 6

# --- 1.2 узлы входов
nodes = rd(K, "entry_nodes")
ext_non = nodes[(nodes.in_12 == "да") & (nodes.fix_class == "не организован")]
def node_cells(pt, d=8):
    near = [n for n, g in cells.geometry.items() if g.distance(pt) <= d]
    fixed = [n for n in near if cells.is_anal[n] == 1]
    return fixed if fixed else [n for n in near if scope[n]]
nodes_non = pd.Series(0, index=cells.index)
for pt in ext_non.geometry:
    for n in node_cells(pt): nodes_non[n] += 1

# --- 1.4 износ
def wear_val(r):
    w = r["Степень изношенности"]
    if pd.notna(w): return float(w), "указан"
    t = r["Наша оценка изношенности"]
    if isinstance(t, str) and re.search(r"\d", t):
        a = [float(x) for x in re.findall(r"\d+", t)]
        return sum(a) / len(a) / 100, "оценка команды"
    return np.nan, None
bw = blds[blds.id.notna()].copy()
bw[["wear", "wsrc"]] = bw.apply(lambda r: pd.Series(wear_val(r)), axis=1)
def wear40(exclude_team=False, d=8, thr=0.40):
    w = bw[(bw.wear >= thr - 1e-9) & (~(bw.wsrc == "оценка команды") if exclude_team else True)]
    return pd.Series({n: int(w.distance(g).le(d).sum()) for n, g in cells.geometry.items()}), w

# --- 2.1 загрузка
lz = rd(K, "loading_zones"); lz["geometry"] = lz.buffer(0); LZ = lz.union_all()
loading_m2 = pd.Series({n: g.intersection(LZ).area for n, g in cells.geometry.items()})

# --- 2.2 опасные открытые объекты
bz = rd(K, "business"); garb = rd(K, "garbage")
dz = bz[(bz.danger == "опасный") & (bz.isolation == "открытый")]
def danger_obj(with_garbage=True, d=6):
    objs = list(dz.geometry) + (list(garb.geometry) if with_garbage else [])
    s = gpd.GeoSeries(objs, crs=cells.crs)
    return pd.Series({n: int(s.distance(g).le(d).sum()) for n, g in cells.geometry.items()})

# --- 2.3 совмещение (по проезжей части, высокая интенсивность)
net = rd(A, "network")
comb = net[(net.razdel == "по проезжей части") & ((net.group == "высокая") | (net.vgroup == "высокая"))]
COMB = comb.union_all()
combined_m = pd.Series({n: g.intersection(COMB).length for n, g in cells.geometry.items()})

# --- 3.1 высокий транзит в зонах АЖ/ПЖ (ячейки с подъездами)
tr = rd(A, "transit"); cz = rd(A, "control_zones"); cz["geometry"] = cz.buffer(0)
TRH = tr[tr.cls == "высокая"].union_all()
RES = cz[cz["type"].isin(["АЖ", "ПЖ"])].union_all()
trh_res = TRH.intersection(RES)
transit_res_m = pd.Series({n: g.intersection(trh_res).length for n, g in cells.geometry.items()})
# вариант с суммой по режимам (дубли пешеходный+транспортный на одном участке)
th = tr[tr.cls == "высокая"]
transit_res_sum = pd.Series({n: sum(x.intersection(RES).intersection(g).length for x in th.geometry) for n, g in cells.geometry.items()})

# --- 3.2 обслуживающий объект в 6 м от ячейки и в 15 м от высокого пешеходного транзита
TRP = tr[(tr.cls == "высокая") & (tr["mode"] == "пешеходный")].union_all()
serv = bz[(bz.function == "обслуживающий")]
serv_t = serv[serv.distance(TRP) <= 15]
biz_transit = pd.Series({n: int(serv_t.distance(g).le(6).sum()) for n, g in cells.geometry.items()})

# --- 3.3 места поведения
pz = rd(A, "playgrounds_zones")
pg_out_rows = pz[pz.problem.notna()]
pg_out = pd.Series({n: int(pg_out_rows.intersects(g).sum()) for n, g in cells.geometry.items()})

# --- 3.4 конкуренция / неконтролируемость / неосвоенность
comp = rd(A, "competition"); comp["geometry"] = comp.buffer(0); COMP = comp.union_all()
ctl = rd(A, "control"); ctl["geometry"] = ctl.buffer(0); UNC = ctl[ctl["type"] == "неконтролируемая"].union_all()
comp_pct = pd.Series({n: 100 * g.intersection(COMP).area / g.area for n, g in cells.geometry.items()})
unc_pct = pd.Series({n: 100 * g.intersection(UNC).area / g.area for n, g in cells.geometry.items()})
osv = rd(A, "osvoennost"); osv["geometry"] = osv.buffer(0); osv["ga"] = osv.area
ass = osv[osv.cls != "не оценивается"]
def unosv(area_col):
    a = ass.groupby("cell")[area_col].sum(); u = ass[ass.cls == "неосвоенная"].groupby("cell")[area_col].sum()
    return (100 * u.reindex(cells.index).fillna(0) / a.reindex(cells.index)).where(a.reindex(cells.index) > 0)
unosv_pct = unosv("ga"); unosv_pct_field = unosv("area")

def flags(p=None, wear_excl_team=False, garbage=True, entries_override=None, size_from="size"):
    p = dict(comfort_cut=0.67, ent_non=1, wear_n=1, loading_m2=50, danger_obj=1, combined_m=20,
             transit_res_m=20, biz_transit=1, comp_pct=5, unc_pct=50, unos_pct=25, **(p or {}))
    cs = comfort(size_from=size_from)
    w, _ = wear40(wear_excl_team)
    nn = nodes_non if entries_override is None else entries_override
    f = pd.DataFrame(index=cells.index)
    f["p1_1"] = (cs < p["comfort_cut"] - 0.005).astype(int)
    f["p1_2"] = (nn >= p["ent_non"]).astype(int)
    f["p1_3"] = (cells.is_anal == 0).astype(int)
    f["p1_4"] = (w >= p["wear_n"]).astype(int)
    f["p2_1"] = (loading_m2 >= p["loading_m2"]).astype(int)
    f["p2_2"] = (danger_obj(garbage) >= p["danger_obj"]).astype(int)
    f["p2_3"] = (combined_m >= p["combined_m"]).astype(int)
    f["p3_1"] = ((transit_res_m >= p["transit_res_m"]) & (pod > 0)).astype(int)
    f["p3_2"] = (biz_transit >= p["biz_transit"]).astype(int)
    f["p3_3"] = (pg_out >= 1).astype(int)
    f["p3_4"] = ((comp_pct >= p["comp_pct"]) | (unc_pct >= p["unc_pct"]) | (unosv_pct.fillna(0) >= p["unos_pct"])).astype(int)
    f = f[scope]
    f["score"] = f.sum(axis=1)
    f["cls"] = pd.cut(f.score, [-1, 3, 5, 99], labels=["низкая", "средняя", "высокая"])
    f["comfort"] = cs[scope]
    return f

if __name__ == "__main__":
    pd.set_option("display.width", 250); pd.set_option("display.max_rows", 100)
    print("scope:", int(scope.sum()), "added:", sorted(cells.index[scope & (cells.is_anal == 0)]))
    print("pod (8 м) vs stored:", dict(pod[scope][pod[scope] != viol.pod[scope]]) or "OK",
          "| stored pod = подъезды внутри ячейки?", (pod_in[scope] == viol.pod[scope]).all())
    base = flags(size_from="planning")   # как в данных (с ошибками размеров 7 и 32)
    meth = flags(size_from="size")       # по методике (размер <= 140 м)
    cols = [c for c in base.columns if c.startswith("p")]
    st = viol.loc[scope, cols].astype(int)
    diff = (base[cols] != st)
    print("расхождения флагов с viol_cells:", {c: list(base.index[diff[c]]) for c in cols if diff[c].any()} or "нет")
    print("сумма флагов:", int(base[cols].values.sum()), base[cols].sum().to_dict())
    print("классы:", base.cls.value_counts().to_dict())
    print("лидеры:", base.score.sort_values(ascending=False).head(8).to_dict())
    print("по методике (размеры 7 и 32 исправлены): сумма", int(meth[cols].values.sum()), "классы", meth.cls.value_counts().to_dict(),
          "изменились баллы:", {n: (round(base.comfort[n], 2), round(meth.comfort[n], 2)) for n in base.index if abs(base.comfort[n] - meth.comfort[n]) > 0.01})
    # сверка промежуточных величин
    chk = pd.DataFrame({"nodes_non": nodes_non, "wear40": wear40()[0], "loading_m2": loading_m2.round(), "danger_obj": danger_obj(),
                        "combined_m": combined_m.round(), "transit_res_m": transit_res_m.round(), "biz_transit": biz_transit, "pg_out": pg_out,
                        "comp_pct": comp_pct.round(1), "unc_pct": unc_pct.round(1), "unosv_pct": unosv_pct.round(1)})
    for c in chk.columns:
        s = viol[c]; d = (chk[c] - s).abs()
        tol = {"loading_m2": 2, "combined_m": 2, "transit_res_m": 2, "comp_pct": 0.3, "unc_pct": 0.3, "unosv_pct": 0.5}.get(c, 0)
        bad = d[(d > tol) & scope]
        print(f"  {c:14s}", "OK" if bad.empty else {n: (chk[c][n], s[n]) for n in bad.index})
    print("transit_res: сумма по режимам vs объединение, ячейки где порог 20 м меняется:",
          [n for n in cells.index[scope] if (transit_res_sum[n] >= 20) != (transit_res_m[n] >= 20)])
    print("unosv_pct по полю area vs геометрии, ячейки где порог 25 % меняется:",
          [n for n in cells.index[scope] if (unosv_pct_field.fillna(0)[n] >= 25) != (unosv_pct.fillna(0)[n] >= 25)])
    base.to_csv(os.path.join(os.path.dirname(__file__), "flags_recalc.csv"))
