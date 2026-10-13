# Числа для презентации из v13 (vector/*_v13.gpkg, audit_v12/v13_results.pkl) -> deck_data.json
import os, json, warnings
import pandas as pd, geopandas as gpd
warnings.filterwarnings("ignore")
H = os.path.dirname(os.path.abspath(__file__)); V = os.path.join(H, "..", "vector")
K, A, P = (os.path.join(V, f"{n}_v13.gpkg") for n in ("konkovo", "analiz", "problems"))
rd = lambda f, l: gpd.read_file(f, layer=l)
R = pd.read_pickle(os.path.join(H, "..", "audit_v12", "v13_results.pkl"))
D = {}
c = rd(K, "cells"); v = rd(P, "viol_cells"); S = v[v.in_scope == 1].copy()
cs = c.merge(v[["num", "in_scope"]], on="num"); cs = cs[cs.in_scope == 1]
D["cells"] = dict(total=len(c), area_ha=round(c.area.sum() / 1e4, 1), anal=int((c.is_anal == 1).sum()), scope=len(S), added=sorted(S[S.is_anal == 0].num.astype(int).tolist()),
                  outside=int((c.is_anal == 0).sum()), scope_area_ha=round(cs.area.sum() / 1e4, 1))
D["comfort"] = dict(vertical=cs.vertical.value_counts().to_dict(), isolation=cs.isolation.value_counts().to_dict(), size=cs.planning.value_counts().to_dict(),
                    comfortable=int((S.comfort_score >= 0.665).sum()),
                    cells=[dict(num=int(r.num), score=float(r.comfort_score), v=r.vertical, i=r.isolation, s=r.planning) for r in cs.merge(S[["num", "comfort_score"]], on="num").sort_values("comfort_score", ascending=False).itertuples()])
b = rd(K, "buildings"); D["buildings"] = dict(n=len(b), typed=int(b.id.notna().sum()), types=b["Тип здания"].value_counts().to_dict())
w = rd(P, "p1_4_wear"); D["wear"] = dict(n=len(w), src=w.src.value_counts().to_dict(), list=[dict(addr=r.addr, wear=round(float(r.wear) * 100), src=r.src) for r in w.sort_values("wear", ascending=False).itertuples()])
bz = rd(K, "business"); D["business"] = dict(n=len(bz), placement=bz.placement.value_counts().to_dict(), danger=bz.danger.value_counts().to_dict(), function=bz.function.value_counts().to_dict())
f = rd(K, "fences"); D["fences"] = dict(n=len(f), podtip=f.podtip.value_counts().to_dict()); D["arches"] = len(rd(K, "arches"))
e = rd(K, "entries_territory"); ext = e[e.in_12 == "да"]; org = ext.degree.isin(["высокая", "средняя"])
D["entries"] = dict(ext=len(ext), org=int(org.sum()), non=int((~org).sum()), internal=int((e.in_12 != "да").sum()),
                    by_type={k.replace("Вход — ", ""): [int(g.degree.isin(["высокая", "средняя"]).sum()), int((~g.degree.isin(["высокая", "средняя"])).sum())] for k, g in ext.groupby("podtip")},
                    nodes_ext=54, nodes_org=27, nodes_non=27, from_flows=int(((e.src == "замер потока") & (e.in_12 == "да")).sum()))
gr = rd(K, "green"); g12 = gpd.read_file(os.path.join(V, "konkovo_v12.gpkg"), layer="green"); pk = rd(K, "parking")
D["green"] = dict(v13={k: round(x) for k, x in gr.assign(a=gr.area).groupby("type").a.sum().items()}, v12={k: round(x) for k, x in g12.assign(a=g12.area).groupby("type").a.sum().items()},
                  parking_n=len(pk), parking_m2=round(pk.area.sum()), parking_status=pk.status.value_counts().to_dict(), parking_kind=pk.kind.value_counts().to_dict(),
                  playgrounds=rd(K, "playgrounds")["type"].value_counts().to_dict(), pg_m2=round(rd(K, "playgrounds").area.sum()))
lz = rd(K, "loading_zones"); D["loading"] = dict(n=len(lz), m2=round(lz.area.sum())); D["garbage"] = len(rd(K, "garbage"))
net = rd(A, "network"); net["L"] = net.length
D["network"] = dict(ped={k: round(x / 1000, 2) for k, x in net.groupby("group").L.sum().items()}, veh={k: round(x / 1000, 2) for k, x in net.groupby("vgroup").L.sum().items()},
                    razdel={k: int(x) for k, x in net.razdel.value_counts().items()}, razdel_km={k: round(x / 1000, 2) for k, x in net.groupby("razdel").L.sum().items()}, total_km=round(net.L.sum() / 1000, 1))
cm = rd(P, "p2_3_combined"); D["combined"] = dict(n=len(cm), m=round(cm.length.sum()))
fl = rd(A, "flows"); D["flows"] = dict(n=len(fl), cls=fl.cls.value_counts().to_dict(), top=[dict(id=int(r.id), sat=int(r.sat_human), lo=int(r.mon_low), hi=int(r.mon_high), est=int(r.mon_est)) for r in fl.sort_values("sat_human", ascending=False).head(6).itertuples()])
tr = rd(A, "transit"); D["transit"] = dict(n=len(tr), mode=tr["mode"].value_counts().to_dict(), high=int((tr.cls == "высокая").sum()), p31_m=round(rd(P, "p3_1_transit").length.sum()))
cz = rd(A, "control_zones"); ct = rd(A, "control"); ct["a"] = ct.buffer(0).area
D["control"] = dict(zones=cz["type"].value_counts().to_dict(), polys=ct["type"].value_counts().to_dict(), area={k: round(x) for k, x in ct.groupby("type").a.sum().items()},
                    competition_n=len(rd(A, "competition")), competition_m2=round(rd(A, "competition").buffer(0).area.sum()))
pz = rd(A, "playgrounds_zones"); D["pg_zones"] = dict(zone=pz.zone.value_counts().to_dict(), problem=int(pz.problem.notna().sum()), unctl=int((pz.control == "неконтролируемая").sum()))
o = rd(A, "osvoennost"); ass = o[o.cls != "не оценивается"]
D["osv"] = dict(cls={k: round(x) for k, x in o.groupby("cls").area.sum().items()},
                BU={f"{int(a)}{int(u)}": round(x) for (a, u), x in ass.groupby(["B", "U"]).area.sum().items()},
                U_why={k: round(x) for k, x in ass.groupby("U_why").area.sum().sort_values(ascending=False).items()},
                B_why={k: round(x) for k, x in ass.groupby("B_why").area.sum().sort_values(ascending=False).items()},
                note={k: round(x) for k, x in o[o.cls == "не оценивается"].groupby("note").area.sum().items()})
D["xt"] = R["XT"].to_dict(orient="records")
FL = ["p1_1", "p1_2", "p1_3", "p1_4", "p2_1", "p2_2", "p2_3", "p3_1", "p3_2", "p3_3", "p3_4"]
D["flags"] = dict(total=int(S[FL].sum().sum()), by={k: int(S[k].sum()) for k in FL}, p34={k: int(S[k].sum()) for k in ("p3_4a", "p3_4b", "p3_4c")},
                  cls=S.cls.value_counts().to_dict(), cls_wo13=S.cls_wo13.value_counts().to_dict(),
                  leaders=[dict(num=int(r.num), score=int(r.score), flags=[int(getattr(r, k)) for k in FL]) for r in S.sort_values(["score", "num"], ascending=[False, True]).head(8).itertuples()],
                  cells=[dict(num=int(r.num), score=int(r.score), cls=r.cls) for r in S.sort_values("num").itertuples()])
for nm in ("p1_2_nodes", "p2_1_loading", "p2_2_objects", "p3_2_objects", "p3_3_places", "pre_fav_closed"):
    D.setdefault("layers", {})[nm] = len(rd(P, nm))
D["pre"] = dict(osv_ctl=round(rd(P, "pre_osv_ctl").area.sum()), comfort=len(rd(P, "pre_comfort_cells")), nodes=27, fav=len(rd(P, "pre_fav_closed")))
D["abandoned"] = round(rd(P, "p3_4_abandoned").area.sum()); D["unctl_cells"] = round(rd(P, "p3_4_uncontrolled").area.sum())
D["sens"] = R["SENS"].to_dict(orient="records"); D["stab"] = R["STAB"].to_dict(orient="records"); D["ass"] = R["ASS"].to_dict(orient="records")
json.dump(D, open(os.path.join(H, "deck_data.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=str)
print(json.dumps({k: D[k] for k in ("cells", "entries", "green", "osv", "flags", "pre", "control", "network", "flows")}, ensure_ascii=False, default=str)[:6000])
