# Числа для презентации v5 из анализа v14 (vector/*_v14.gpkg, analysis_v14/v14_results.pkl) -> deck_data14.json
import os, json, warnings
import pandas as pd, geopandas as gpd
warnings.filterwarnings("ignore")
H = os.path.dirname(os.path.abspath(__file__)); V = os.path.join(H, "..", "vector")
K, A, P = (os.path.join(V, f"{n}_v14.gpkg") for n in ("konkovo", "analiz", "problems"))
K13, A13 = os.path.join(V, "konkovo_v13.gpkg"), os.path.join(V, "analiz_v13.gpkg")
rd = lambda f, l: gpd.read_file(f, layer=l)
R = pd.read_pickle(os.path.join(H, "..", "analysis_v14", "v14_results.pkl"))
D = {}
c = rd(K, "cells"); v = rd(P, "viol_cells")
D["cells"] = dict(total=len(c), anal=int((c.is_anal == 1).sum()), scope=len(v), out_fixed=sorted(v[v.is_anal == 0].num.astype(int).tolist()),
                  added=[15, 22, 29, 39, 47, 51], area_ha=round(c.area.sum() / 1e4, 1))
D["comfort"] = dict(comfortable=int((v.comfort_score >= 0.665).sum()), n=len(v),
                    vertical=v.vertical.value_counts().to_dict(), isolation=v.isolation.value_counts().to_dict(), size=v.planning.value_counts().to_dict(),
                    cells=[dict(num=int(r.num), score=float(r.comfort_score)) for r in v.sort_values("comfort_score", ascending=False).itertuples()])
e = rd(K, "entries_territory"); e13 = rd(K13, "entries_territory")
D["entries"] = dict(n=len(e), org=int((e.fix_class == "организован").sum()), non=int((e.fix_class != "организован").sum()),
                    added=int(e.src.astype(str).str.startswith("v14").sum()), v13=len(e13), removed=len(e13) - int((~e.src.astype(str).str.startswith("v14")).sum()),
                    by_type={k.replace("Вход — ", ""): [int(((e.podtip == k) & (e.fix_class == "организован")).sum()), int(((e.podtip == k) & (e.fix_class != "организован")).sum())]
                             for k in e.podtip.unique()})
net = rd(A, "network")
D["network"] = dict(total_km=round(net.length.sum() / 1000, 1), paths=192,
                    ped={g: round(net[net.group == g].length.sum() / 1000, 2) for g in ("высокая", "низкая", "один путь")},
                    veh={g: round(net[net.vgroup == g].length.sum() / 1000, 2) for g in ("высокая", "низкая")},
                    razdel={k: round(x / 1000, 2) for k, x in net[net.ped > 0].groupby("razdel").length.sum().items()},
                    metro_hi_km=round(net[net.metro >= 20].length.sum() / 1000, 2), mall_hi_km=round(net[net.mall >= 20].length.sum() / 1000, 2))
D["combined_m"] = round(rd(P, "p2_3_combined").length.sum())
fl = rd(A13, "flows"); D["flows"] = dict(n=len(fl), cls=fl.cls.value_counts().to_dict(),
                                         top=[dict(id=int(r.id), sat=int(r.sat_human)) for r in fl.sort_values("sat_human", ascending=False).head(6).itertuples()])
tr = rd(A13, "transit"); D["transit"] = dict(n=len(tr), high=int((tr.cls == "высокая").sum()))
ctl = rd(A, "control"); a = ctl.groupby("type").area.sum()
cz = rd(A, "control_zones"); D["control"] = dict(area_ha={k: round(x / 1e4, 1) for k, x in a.items()}, pct={k: round(100 * x / a.sum()) for k, x in a.items()},
                                                 competition_ha=round(rd(A, "competition").area.sum() / 1e4, 1), zones_ha={r.type: round(r.area / 1e4, 1) for r in cz.itertuples()})
pz = rd(A, "playgrounds_zones"); D["pg"] = dict(n=len(pz), zone=pz.zone.value_counts().to_dict(), problem=int(pz.problem.notna().sum()),
                                                 control=pz.control.value_counts().to_dict(), types=pz["type"].value_counts().to_dict())
o = rd(A, "osvoennost"); oa = o[o.cls != "не оценивается"].groupby("cls").area.sum()
D["osv"] = dict(ha={k: round(x / 1e4, 1) for k, x in oa.items()}, pct={k: round(100 * x / oa.sum()) for k, x in oa.items()},
                B=o[o.cls != "не оценивается"].groupby("B_why").area.sum().div(1e4).round(1).to_dict(), U=o[o.cls != "не оценивается"].groupby("U_why").area.sum().div(1e4).round(1).to_dict())
D["xt"] = R["XT"].to_dict(orient="records")
FL = ["p1_1", "p1_2", "p1_3", "p1_4", "p2_1", "p2_2", "p2_3", "p3_1", "p3_2", "p3_3", "p3_4"]
D["flags"] = dict(total=int(v[FL].sum().sum()), by={k: int(v[k].sum()) for k in FL}, p34={k: int(v[k].sum()) for k in ("p3_4a", "p3_4b", "p3_4c")},
                  cls=v.cls.value_counts().to_dict(),
                  leaders=[dict(num=int(r.num), score=int(r.score), flags=[int(getattr(r, k)) for k in FL]) for r in v.sort_values(["score", "num"], ascending=[False, True]).head(8).itertuples()],
                  core=[int(x) for x in R["ALWAYS"]])
D["sens"] = R["SENS"].to_dict(orient="records"); D["ass"] = R["ASS"].to_dict(orient="records")
D["wear"] = dict(n=len(rd(P, "p1_4_wear")), src=rd(P, "p1_4_wear").src.value_counts().to_dict())
D["loading"] = dict(n=len(rd(K, "loading_zones")), m2=round(rd(K, "loading_zones").area.sum())); D["garbage"] = len(rd(K, "garbage"))
bz = rd(K, "business"); D["business"] = dict(n=len(bz), placement=bz.placement.value_counts().to_dict(), danger=bz.danger.value_counts().to_dict())
g = rd(K, "green"); D["green"] = {k: round(x) for k, x in g.assign(a=g.area).groupby("type").a.sum().items()}
pk = rd(K, "parking"); D["parking"] = dict(n=len(pk), m2=round(pk.area.sum()))
D["pre"] = dict(osv_ctl_ha=round(rd(P, "pre_osv_ctl").area.sum() / 1e4, 1), comfort=len(rd(P, "pre_comfort_cells")), nodes=len(rd(P, "pre_nodes")),
                fav=len(rd(os.path.join(V, "problems_v13.gpkg"), "pre_fav_closed")), axes_km=round(rd(P, "pre_axes").length.sum() / 1000, 1))
json.dump(D, open(os.path.join(H, "deck_data14.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=str)
for k in ("cells", "comfort", "entries", "network", "control", "pg", "osv", "flags", "pre"):
    print(k, json.dumps(D[k], ensure_ascii=False, default=str)[:600])
