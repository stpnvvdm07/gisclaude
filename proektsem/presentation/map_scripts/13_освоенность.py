# Карта «освоенность» для презентации. Запуск: python3 13_освоенность.py
import os, sys; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from mapkit import *

def m_osv(key="c_osv", w=1280, h=720):
    m = Map(key, w, h); m.base()
    o = L(A, "osvoennost")
    for t, col in (("освоенная", "#7DCB86"), ("частично освоенная", "#EBDC9C"), ("неосвоенная", C["dred"]), ("не оценивается", "#E6E2DA")):
        m.poly(o[o.cls == t].geometry.tolist(), col, "#FFFFFF", 0.4, z=4)
    pg = L(K, "playgrounds"); m.poly(pg.geometry.tolist(), "none", C["dark"], 1.0, z=6)
    a = o[o.cls != "не оценивается"].groupby("cls").area.sum(); t = a.sum()
    for k, col in (("освоенная", "#7DCB86"), ("частично освоенная", "#EBDC9C"), ("неосвоенная", C["dred"])): m.add_legend(f"{k} — {100 * a[k] / t:.0f} %", "fill", fill=col, fa=1)
    m.add_legend("не оценивается (школы, детсады, вне ячеек)", "fill", fill="#E6E2DA", fa=1); m.add_legend("площадки", "fill", fill="#ffffff", fa=0, stroke=C["dark"])
    m.save()

if __name__ == "__main__": m_osv()
