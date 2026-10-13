# Карта «опасные объекты» для презентации. Запуск: python3 06_опасные_объекты.py
import os, sys; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from mapkit import *

def m_danger(key="c_danger", w=1280, h=720):
    m = Map(key, w, h); m.base()
    lz = L(K, "loading_zones"); m.poly(list(lz.geometry), C["orange"], C["edge"], 0.4, z=12)
    gb = L(K, "garbage"); bz = L(K, "business"); pg = L(K, "playgrounds")
    m.poly(list(pg.geometry), "#D9E6F2", "#6B8BB0", 0.8, z=9)
    dang = bz[(bz.danger == "опасный") & (bz.isolation == "открытый")]
    m.pts([(p.x, p.y) for p in gb.geometry], C["dark"], 13, "s", "white", 1.2)
    m.pts([(p.x, p.y) for p in dang.geometry], C["red"], 17, "P", "white", 1.2)
    fav = bz[(bz.danger == "благоприятный")]; m.pts([(p.x, p.y) for p in fav.geometry], C["green"], 10, "o", "white", 1)
    m.add_legend(f"мусорная площадка — {len(gb)}", "marker", fill="#16161c", shape="square")
    m.add_legend(f"опасный открытый бизнес — {len(dang)}", "marker", fill="#d62828", shape="cross_fill")
    m.add_legend(f"благоприятный бизнес — {len(fav)}", "marker", fill="#2a9d4b", shape="circle")
    m.add_legend(f"зона загрузки — {len(lz)}", "fill", fill=C["orange"], fa=1); m.add_legend("площадки (для ориентира)", "fill", fill="#D9E6F2", fa=1, stroke="#6B8BB0")
    m.save()

if __name__ == "__main__": m_danger()
