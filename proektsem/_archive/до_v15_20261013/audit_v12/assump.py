# Влияние допущений команды на счёт (относительно значений v12)
import pandas as pd, numpy as np, geopandas as gpd
import recalc as R, sens as Sx

S = R.scope; viol = R.viol
e = R.rd(R.K, "entries_territory"); nodes = R.rd(R.K, "entry_nodes")

def nodes_non_from(org_series, assign="stored"):
    """org_series: организован ли вход (index как e). Узел организован, если организованы все входы."""
    ee = e.assign(org=org_series)
    ext = ee[ee.in_12 == "да"]
    nodeorg = ext.groupby("node").org.all()
    out = pd.Series(0, index=R.cells.index)
    for _, r in nodes[nodes.in_12 == "да"].iterrows():
        if nodeorg[r.node]: continue
        if assign == "stored":
            cl = [int(x) for x in str(r.cells).split(",") if x.strip()]
        else:
            cl = R.node_cells(r.geometry)
        for n in cl: out[n] += 1
    return out, int((~nodeorg).sum()), int(len(nodeorg))

org_v12 = e.degree.isin(["высокая", "средняя"])
vjezd16 = (e.podtip == "Вход — въезд") & (e.degree == "низкая") & (e.in_12 == "да")
from_flows = (e.src == "замер потока")

def summary(name, d):
    f, s, c, k = Sx.score(d, cf={"vh": 1.4})
    hi = sorted(s[c == 2].index, key=lambda n: -s[n])
    return dict(вариант=name, флагов=int(f.values.sum()), **{p: int(f[p].sum()) for p in ["p1_2", "p1_4", "p2_2"]},
                низк=int((c == 0).sum()), сред=int((c == 1).sum()), выс=int((c == 2).sum()),
                высокие=", ".join(f"{n}({s[n]})" for n in hi))

rows = []
for assign in ("stored", "rule8"):
    base = Sx.values("stored").copy()
    nn0, nnon0, nall = nodes_non_from(org_v12, assign)
    base["nodes_non"] = nn0
    tag = "привязка узлов как в v12" if assign == "stored" else "привязка узлов строго 8 м"
    rows.append(summary(f"[{tag}] база v12 (узлов неорг. {nnon0}/{nall})", base))
    d = base.copy(); d["danger_obj"] = R.danger_obj(with_garbage=False); rows.append(summary(f"[{tag}] без 14 мусорных площадок", d))
    d = base.copy(); d["wear40"] = R.wear40(exclude_team=True)[0]; rows.append(summary(f"[{tag}] износ только опубликованный (без 8 оценок)", d))
    nn, k, _ = nodes_non_from(org_v12 | vjezd16, assign); d = base.copy(); d["nodes_non"] = nn
    rows.append(summary(f"[{tag}] 16 въездов = организованы (неорг. узлов {k})", d))
    nn, k, _ = nodes_non_from(org_v12 | (from_flows & (e.in_12 == "да")), assign); d = base.copy(); d["nodes_non"] = nn
    rows.append(summary(f"[{tag}] 6 входов из замеров потока не учитывать (неорг. узлов {k})", d))
    d = base.copy(); d["danger_obj"] = R.danger_obj(with_garbage=False); d["wear40"] = R.wear40(exclude_team=True)[0]
    nn, k, _ = nodes_non_from(org_v12 | vjezd16, assign); d["nodes_non"] = nn
    rows.append(summary(f"[{tag}] все три допущения сняты", d))
pd.set_option("display.width", 250); pd.set_option("display.max_colwidth", 120)
print(pd.DataFrame(rows).to_string(index=False))
