# Независимая проверка освоенности v12 (B x U) по правилам из листа «Аудит v12» / HANDOFF §2
import os, warnings
import numpy as np, pandas as pd, geopandas as gpd
warnings.filterwarnings("ignore")
V = os.environ.get("VDIR", os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "vector"))
K, A = os.path.join(V, "konkovo_v12.gpkg"), os.path.join(V, "analiz_v12.gpkg")
rd = lambda f, l=None: gpd.read_file(f, layer=l) if l else gpd.read_file(f)
o = rd(A, "osvoennost"); o["geometry"] = o.buffer(0); o["ga"] = o.area
cells = rd(K, "cells").set_index("num"); viol = rd(os.path.join(V, "problems_v12.gpkg"), "viol_cells").set_index("num")
scope_cells = set(viol.index[viol.in_scope == 1])
excl = rd(K, "cells_excluded").buffer(0).union_all()
slopes = rd(os.path.join(V, "proektbase/slopesandwalls.gpkg")).union_all().buffer(6)
manual = rd(K, "osv_manual").buffer(0).union_all()
pdn = rd(K, "people_dens"); many = pdn[pdn.dens == "много"].union_all(); few = pdn[pdn.dens == "мало"].union_all()
pg = rd(K, "playgrounds").buffer(0).union_all()
net = rd(A, "network"); links = net[net.ped >= 2].union_all().buffer(10)
pod = rd(K, "entrances_buildings").union_all().buffer(30)

def share(g, z): return g.intersection(z).area / g.area if g.area > 0 else 0
rows = []
for i, r in o.iterrows():
    g = r.geometry
    # охват
    narrow = g.buffer(-2.5).is_empty
    if r.cell not in scope_cells: ns = "вне ячеек анализа"
    elif share(g, excl) > 0.5: ns = "территория учреждения (школа, детсад)"
    elif narrow: ns = "полоса уже 5 м (отмостка, обочина)"
    else: ns = None
    inman = share(g, manual) > 0.5
    B = not (share(g, slopes) >= 0.30 or inman)
    if inman: U, uw = False, "контур команды «неосвоенная»"
    elif share(g, many) > 0.5: U, uw = True, "наблюдение: много людей"
    elif share(g, few) > 0.5: U, uw = False, "наблюдение: мало людей"
    elif share(g, pg) > 0.5: U, uw = True, "место поведения (площадка)"
    elif share(g, links) >= 0.25: U, uw = True, "у пешеходной связи (≥2 путей дерева)"
    elif share(g, pod) >= 0.25: U, uw = True, "ближняя зона подъезда (30 м)"
    else: U, uw = False, "нет признаков использования"
    cls = "не оценивается" if ns else ("освоенная" if B and U else ("неосвоенная" if not B and not U else "частично освоенная"))
    rows.append((ns, B, U, uw, cls))
o[["ns", "B2", "U2", "uw2", "cls2"]] = pd.DataFrame(rows, index=o.index)
pd.set_option("display.width", 220)
print("класс: совпадает", (o.cls == o.cls2).sum(), "из", len(o))
print(pd.crosstab(o.cls, o.cls2, values=o.ga, aggfunc="sum").round(0))
print("основание охвата (сохр. note vs пересчёт):"); print(pd.crosstab(o.note.fillna("-"), o.ns.fillna("-")))
ass = o[o.cls != "не оценивается"]
print("B: сохр B>=1 vs пересчёт", pd.crosstab(ass.B >= 1, ass.B2).to_dict())
print("U: сохр U>=1 vs пересчёт", pd.crosstab(ass.U >= 1, ass.U2).to_dict())
print(pd.crosstab(ass.U_why, ass.uw2))
print("Итог по сохранённому классу, геометрическая площадь:", o.groupby("cls").ga.sum().round(0).to_dict())
print("Итог по пересчёту, геометрическая площадь:", o.groupby("cls2").ga.sum().round(0).to_dict())
tot = o[o.cls != "не оценивается"].ga.sum()
print("доли (сохр. класс, геом. площадь):", (o[o.cls != "не оценивается"].groupby("cls").ga.sum() / tot * 100).round(1).to_dict())
mtx = ass.assign(Bb=ass.B >= 1, Ub=ass.U >= 1).pivot_table(index="Bb", columns="Ub", values="ga", aggfunc="sum").round(0)
print("матрица B x U (геом.):"); print(mtx)
print("матрица B x U (поле area):"); print(ass.assign(Bb=ass.B >= 1, Ub=ass.U >= 1).pivot_table(index="Bb", columns="Ub", values="area", aggfunc="sum"))
print("U_why по полю area:", ass.groupby("U_why")["area"].sum().to_dict())
print("крупнейшие «покрытие (принято)» освоенные:", ass[ass.B_why == "покрытие (принято)"].groupby("cls").ga.sum().round(0).to_dict())
o.drop(columns="geometry").to_csv(os.path.join(os.path.dirname(__file__), "osv_recalc.csv"))
