# Карта «сводный счёт» для презентации. Запуск: python3 18_сводный_счёт.py
import os, sys; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from mapkit import *

def m_score(key="c_score", w=1280, h=720):
    m = Map(key, w, h); m.base(cells=False); v = cells_in(); c = L(K, "cells")
    m.poly(c[~c.num.isin(v.num)].geometry.tolist(), "#EEEAE2", "#9C978E", 0.5, z=4)
    col = {"высокая": "#E0675E", "средняя": "#EBCB72", "низкая": "#A9D9A0"}
    for r in v.itertuples():
        m.poly(r.geometry, col[r.cls], C["edge"], 0.7, z=5)
        p = r.geometry.representative_point(); m.text(p.x, p.y, f"{r.num}\n{r.score}", 13, C["dark"], "semibold" if r.cls == "высокая" else "regular", z=25)
        m.marks[f"cell{r.num}"] = m.px(p.x, p.y)
    for k, lab in (("высокая", "высокий счёт, 6+"), ("средняя", "средний, 4–5"), ("низкая", "низкий, 0–3")):
        m.add_legend(f"{lab} — {int((v.cls == k).sum())}", "fill", fill=col[k], fa=1)
    m.add_legend("номер ячейки / число нарушенных пунктов", "fill", fill="#ffffff", fa=1, stroke=C["edge"])
    m.save()

if __name__ == "__main__": m_score()
