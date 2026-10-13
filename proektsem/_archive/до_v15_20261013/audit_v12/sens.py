# Чувствительность и устойчивость: (а) по промежуточным значениям viol_cells (как в v12), (б) по независимому геометрическому пересчёту
import pandas as pd, numpy as np
from scipy.stats import spearmanr
import recalc as R

S = R.scope
viol = R.viol

def comfort_score(vh=1.3, vl=0.6, vu=2.0, il=0.35, ih=0.65, sizeT=140, size_mode="planning"):
    vk = (R.cells.fasad_area / R.CA).fillna(0); ik = R.cells.fasad_len / R.cells.length
    v = vk.apply(lambda x: R.vcls(x, vh, vl, vu)); i = ik.apply(lambda x: R.icls(x, il, ih))
    if size_mode == "planning" and sizeT == 140:
        s = (R.cells.planning == "Комфортная").astype(int) * 2
    elif size_mode == "planning":   # как в v12: сдвиг порога применяется к полю size, но базовые 7 и 32 - по planning
        s = ((R.cells["size"] >= 25) & (R.cells["size"] <= sizeT)).astype(int) * 2
    else:
        s = ((R.cells["size"] >= 25) & (R.cells["size"] <= sizeT)).astype(int) * 2
    return (v + i + s) / 6

def values(mode):
    if mode == "stored":
        cols = ["nodes_non", "wear40", "loading_m2", "danger_obj", "combined_m", "transit_res_m", "biz_transit", "pg_out", "comp_pct", "unc_pct", "unosv_pct"]
        d = viol[cols].copy(); d["pod"] = viol.pod
    else:
        d = pd.DataFrame({"nodes_non": R.nodes_non, "wear40": R.wear40()[0], "loading_m2": R.loading_m2, "danger_obj": R.danger_obj(),
                          "combined_m": R.combined_m, "transit_res_m": R.transit_res_m, "biz_transit": R.biz_transit, "pg_out": R.pg_out,
                          "comp_pct": R.comp_pct, "unc_pct": R.unc_pct, "unosv_pct": R.unosv_pct, "pod": R.pod})
    return d

BASE = dict(comfort_cut=0.67, ent_non=1, wear_n=1, loading_m2=50, danger_obj=1, combined_m=20, transit_res_m=20,
            biz_transit=1, comp_pct=5, unc_pct=50, unos_pct=25)
def score(d, p=None, cf=None, size_mode="planning"):
    p = {**BASE, **(p or {})}
    cs = comfort_score(size_mode=size_mode, **(cf or {}))
    f = pd.DataFrame(index=R.cells.index)
    f["p1_1"] = cs < p["comfort_cut"] - 0.005
    f["p1_2"] = d.nodes_non >= p["ent_non"]
    f["p1_3"] = R.cells.is_anal == 0
    f["p1_4"] = d.wear40 >= p["wear_n"]
    f["p2_1"] = d.loading_m2 >= p["loading_m2"]
    f["p2_2"] = d.danger_obj >= p["danger_obj"]
    f["p2_3"] = d.combined_m >= p["combined_m"]
    f["p3_1"] = (d.transit_res_m >= p["transit_res_m"]) & (d.pod > 0)
    f["p3_2"] = d.biz_transit >= p["biz_transit"]
    f["p3_3"] = d.pg_out >= 1
    f["p3_4"] = (d.comp_pct >= p["comp_pct"]) | (d.unc_pct >= p["unc_pct"]) | (d.unosv_pct.fillna(0) >= p["unos_pct"])
    f = f[S].astype(int); sc = f.sum(axis=1)
    cl = pd.cut(sc, [-1, 3, 5, 99], labels=[0, 1, 2]).astype(int)
    return f, sc, cl, int((cs[S] >= p["comfort_cut"] - 0.005).sum())

VARIANTS = [("базовые пороги", {}, {})] + \
    [(f"comfort_cut = {v}", {"comfort_cut": v}, {}) for v in (0.5, 0.83)] + \
    [("ent_non = 2", {"ent_non": 2}, {}), ("wear_n = 2", {"wear_n": 2}, {})] + \
    [(f"loading_m2 = {v}", {"loading_m2": v}, {}) for v in (25, 100)] + [("danger_obj = 2", {"danger_obj": 2}, {})] + \
    [(f"combined_m = {v}", {"combined_m": v}, {}) for v in (10, 40)] + [(f"transit_res_m = {v}", {"transit_res_m": v}, {}) for v in (10, 40)] + \
    [("biz_transit = 2", {"biz_transit": 2}, {})] + [(f"comp_pct = {v}", {"comp_pct": v}, {}) for v in (2, 10)] + \
    [(f"unc_pct = {v}", {"unc_pct": v}, {}) for v in (30, 70)] + [(f"unos_pct = {v}", {"unos_pct": v}, {}) for v in (10, 50)] + \
    [(f"vl = {v}", {}, {"vl": v}) for v in (0.5, 0.7)] + [(f"vh = {v}", {}, {"vh": v}) for v in (1.2, 1.6)] + \
    [(f"vu = {v}", {}, {"vu": v}) for v in (1.8, 2.2)] + [(f"il = {v}", {}, {"il": v}) for v in (0.3, 0.4)] + \
    [(f"ih = {v}", {}, {"ih": v}) for v in (0.6, 0.7)] + [(f"size_T = {v}", {}, {"sizeT": v}) for v in (130, 140, 150)]

def run(mode, size_mode="planning", vh_base=1.3):
    d = values(mode)
    rows = []; f0, s0, c0, k0 = score(d, cf={"vh": vh_base}, size_mode=size_mode)
    allsc = []
    for name, p, cf in VARIANTS:
        cf = {"vh": vh_base, **cf}
        f, s, c, k = score(d, p, cf, size_mode)
        rho = spearmanr(s0, s).correlation if s.std() > 0 else np.nan
        rows.append((name, int(f.values.sum()), int((c == 2).sum()), int((c != c0).sum()), round(rho, 3), k))
        allsc.append(c)
    t = pd.DataFrame(rows, columns=["вариант", "флагов", "высоких", "сменили класс", "rho", "комфортных"])
    C = pd.concat(allsc, axis=1)
    unstable = sorted(C.index[C.nunique(axis=1) > 1])
    return t, unstable, f0, s0, c0

if __name__ == "__main__":
    pd.set_option("display.width", 200); pd.set_option("display.max_rows", 100)
    for mode, sm, vh in (("stored", "planning", 1.4), ("stored", "planning", 1.3), ("geom", "planning", 1.4), ("geom", "size", 1.4)):
        t, u, f0, s0, c0 = run(mode, sm, vh)
        print(f"===== режим {mode}, размеры {sm}, vh база {vh}: флагов {int(f0.values.sum())}, классы {c0.value_counts().sort_index().to_dict()}")
        print(t.to_string(index=False))
        print("неустойчивы:", len(u), u)
        print("rho min", t.rho.min(), "max сменили", t["сменили класс"].max(), "высоких от", t["высоких"].min(), "до", t["высоких"].max())
