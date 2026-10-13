# Карта «ячейки» для презентации. Запуск: python3 01_ячейки.py
import os, sys; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from mapkit import *

def m_cells(key="c_cells", w=1480, h=888):
    m = Map(key, w, h); m.base(numbers=False)
    c = L(K, "cells"); ex = L(K, "cells_excluded")
    an = c[c.in_scope == 1]; out_ = c[c.num.isin([14, 28])]; rest = c[(c.in_scope != 1) & ~c.num.isin([14, 28])]
    m.poly(list(an.geometry), "#CFE8C8", C["edge"], 0.8, z=5)
    m.poly(list(out_.geometry), "#F0D9A8", C["edge"], 0.8, z=5, hatch="////"); m.poly(list(rest.geometry), "#E6E2DA", C["edge"], 0.8, z=5)
    m.poly(list(ex.geometry), "#E6E2DA", C["grey"], 0.8, z=6, hatch="xx")
    for r in c.itertuples():
        p = r.geometry.representative_point(); m.text(p.x, p.y, str(r.num), 15, C["dark"], "semibold" if r.in_scope == 1 else "regular", z=25)
    m.add_legend(f"дворы в анализе — {len(an)}", "fill", fill="#CFE8C8", fa=1)
    m.add_legend("вне зафиксированных границ (14, 28), п. 1.3", "fill", fill="#F0D9A8", fa=1, hatch=True)
    m.add_legend(f"краевые полосы у улиц — {len(rest)}", "fill", fill="#E6E2DA", fa=1)
    m.add_legend("участки школ и детсадов", "fill", fill="#C9C4BA", fa=1, hatch=True)
    m.save()

ENT = {"арка": "square", "ворота": "diamond", "калитка": "octagon", "разрыв в застройке": "circle", "въезд": "pentagon",
       "разрыв в насаждениях": "hexagon", "не зафиксирован": "cross_fill"}
MK = {"square": "s", "diamond": "D", "octagon": "8", "circle": "o", "pentagon": "p", "hexagon": "h", "cross_fill": "P", "triangle": "^"}

if __name__ == "__main__": m_cells()
