# Карта «входы» для презентации. Запуск: python3 02_входы.py
import os, sys; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from mapkit import *

def m_entries(key="c_entries", w=1280, h=720):
    m = Map(key, w, h); m.base()
    f = L(K, "fences"); hi = f[f.podtip.str.contains("высокое", na=False)]
    m.line(list(hi.geometry), C["purple"], 1.6, z=12); m.line(list(f.drop(hi.index).geometry), C["lilac"], 1.0, z=12, ls=(0, (2, 2)))
    e = L(K, "entries_territory"); e["t"] = e.podtip.str.replace("Вход — ", "")
    oe = L(K, "open_edge"); m.line(list(oe.geometry), C["red"], 3.0, z=13, ls=(0, (2, 2)))
    for t, sh in ENT.items():
        d = e[e.t == t]
        for org, col in (("организован", "#2A9D4B"), ("не организован", C["red"])):
            dd = d[d.fix_class == org]
            if len(dd): m.pts([(p.x, p.y) for p in dd.geometry], col, 15, MK[sh], "white", 1.4)
    m.add_legend(f"организован — {int((e.fix_class == 'организован').sum())}", "marker", fill="#2a9d4b", shape="circle")
    m.add_legend(f"не организован — {int((e.fix_class != 'организован').sum())}", "marker", fill="#d62828", shape="circle")
    for t, sh in ENT.items(): m.add_legend(f"{t} — {int((e.t == t).sum())}", "marker", fill="#8b877f", shape=sh)
    m.add_legend("высокое ограждение", "line", stroke=C["purple"], sw=0.5)
    m.add_legend(f"открытый фронт: войти можно где угодно — {oe.length.sum():.0f} м", "line", stroke=C["red"], sw=0.6, dash=True)
    m.save()

if __name__ == "__main__": m_entries()
