# Карта «комфорт» для презентации. Запуск: python3 03_комфорт.py
import os, sys; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from mapkit import *

def m_comfort(key="c_comfort", w=1280, h=720):
    m = Map(key, w, h); m.base(cells=False)
    v = cells_in(); c = L(K, "cells"); rest = c[~c.num.isin(v.num)]
    m.poly(list(rest.geometry), "#E6E2DA", C["edge"], 0.6, z=5)
    for r in v.itertuples():
        col = C["green"] if r.comfort_score >= 0.665 else (C["yellow"] if r.comfort_score >= 0.5 else "#E58F86")
        m.poly(r.geometry, col, C["edge"], 0.8, z=5, alpha=0.9)
        p = r.geometry.representative_point(); m.text(p.x, p.y, f"{r.num}\n{r.comfort_score:.2f}".replace(".", ","), 12, C["dark"], "medium", z=25)
    m.add_legend("комфортная, балл от 0,67", "fill", fill=C["green"], fa=1)
    m.add_legend("почти: 0,50–0,66", "fill", fill=C["yellow"], fa=1)
    m.add_legend("некомфортная, ниже 0,50", "fill", fill="#E58F86", fa=1)
    m.add_legend("вне анализа", "fill", fill="#E6E2DA", fa=1)
    m.save()

if __name__ == "__main__": m_comfort()
