# Карта «контролируемость» для презентации. Запуск: python3 11_контролируемость.py
import os, sys; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from mapkit import *

def m_controllability(key="c_control", w=1280, h=720):
    m = Map(key, w, h); m.base(cells="thin")
    c = L(A, "control"); cp = L(A, "competition")
    for t, col in (("контролируемая", "#7DCB86"), ("частично контролируемая", "#EBDC9C"), ("неконтролируемая", "#E8A29B")): m.poly(c[c["type"] == t].geometry.tolist(), col, z=4)
    m.poly(cp.geometry.tolist(), "#A68CC6", z=5, alpha=0.9)
    mt = L(A, "metro"); m.poly([mt.geometry.iloc[0]], "none", C["dark"], 1.4, z=20, ls=(0, (3, 2)))
    a = c.groupby("type").area.sum(); t = a.sum()
    for k, col in (("контролируемая", "#7DCB86"), ("частично контролируемая", "#EBDC9C"), ("неконтролируемая", "#E8A29B")):
        m.add_legend(f"{k} — {100 * a[k] / t:.0f} %", "fill", fill=col, fa=1)
    m.add_legend(f"конкуренция активных контролей — {cp.area.sum() / 1e4:.1f} га".replace(".", ","), "fill", fill="#A68CC6", fa=1)
    m.add_legend("площадь у выхода метро", "fill", fill="#ffffff", fa=0, stroke=C["dark"], dash=True)
    m.save()

if __name__ == "__main__": m_controllability()
