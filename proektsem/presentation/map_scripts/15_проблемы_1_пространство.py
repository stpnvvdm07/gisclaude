# Карта «проблемы 1 пространство» для презентации. Запуск: python3 15_проблемы_1_пространство.py
import os, sys; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from mapkit import *

def m_prob1(key="c_p1", w=1480, h=888):
    m = Map(key, w, h); m.base(cells=False)
    v = cells_in(); c = L(K, "cells"); p13 = L(P, "p1_3_cells"); rest = c[~c.num.isin(v.num) & ~c.num.isin(p13.num)]
    m.poly(rest.geometry.tolist(), "#EEEAE2", "#9C978E", 0.5, z=4)
    ok = v[v.p1_1 == 0]; m.poly(ok.geometry.tolist(), "#FFFFFF", "#9C978E", 0.6, z=4)
    p11 = v[v.p1_1 == 1]; m.poly(p11.geometry.tolist(), "#F4C9C4", "#9C978E", 0.6, z=5)
    m.poly(p13.geometry.tolist(), "#F3EEE4", "#B9B2A6", 0.5, z=6, hatch="//")
    oe = L(K, "open_edge"); m.line(list(oe.geometry), C["red"], 3.0, z=13, ls=(0, (2, 2)))
    for r in v.itertuples():
        p = r.geometry.representative_point(); m.text(p.x, p.y, str(r.num), 13, C["dark"], "semibold" if r.p1_1 else "regular", z=25)
    w4 = L(P, "p1_4_wear"); m.poly(w4.geometry.tolist(), C["dred"], C["edge"], 0.5, z=12)
    nd = L(P, "p1_2_nodes"); m.pts([(p.x, p.y) for p in nd.geometry], C["red"], 18, "^", "white", 1.6)
    m.add_legend(f"1.1 неудачная форма двора (комфорт ниже 0,67) — {len(p11)} ячеек", "fill", fill="#F4C9C4", fa=1)
    m.add_legend(f"1.2 неорганизованный вход — {len(nd)} (в {int(v.p1_2.sum())} ячейках)", "marker", fill="#d62828", shape="triangle")
    m.add_legend("1.2 открытый фронт без фиксации входа", "line", stroke=C["red"], sw=0.6, dash=True)
    m.add_legend(f"1.3 территории вне зафиксированных границ дворов — {len(p13)} участков", "fill", fill="#F3EEE4", fa=1, hatch=True, stroke="#B9B2A6")
    m.add_legend(f"1.4 здание с износом от 40 % — {len(w4)} (рядом с {int(v.p1_4.sum())} ячейками)", "fill", fill=C["dred"], fa=1)
    m.save()

if __name__ == "__main__": m_prob1()
