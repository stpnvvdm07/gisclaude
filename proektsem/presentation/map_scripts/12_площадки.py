# Карта «площадки» для презентации. Запуск: python3 12_площадки.py
import os, sys; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from mapkit import *

def m_playgrounds(key="c_pg", w=1280, h=720):
    m = Map(key, w, h); m.base()
    pz = L(A, "playgrounds_zones"); pod = L(K, "entrances_buildings")
    m.poly([unary_union(pod.buffer(100))], "#F2EBDD", z=2, alpha=0.6); m.poly([unary_union(pod.buffer(30))], "#E7DCC4", z=3, alpha=0.8)
    for zn, col in (("ближняя", C["orange"]), ("средняя", C["green"]), ("периферийная", C["blue"])):
        m.poly(pz[pz.zone == zn].geometry.tolist(), col, C["edge"], 0.6, z=12)
    pr = pz[pz.problem.notna()]; m.poly(pr.geometry.tolist(), "none", C["red"], 3, z=13)
    m.pts([(p.x, p.y) for p in pod.geometry], C["dark"], 6, "o", "white", 0.6)
    m.add_legend(f"площадка в ближней зоне (до 30 м) — {int((pz.zone == 'ближняя').sum())}", "fill", fill=C["orange"], fa=1)
    m.add_legend(f"в средней зоне (30–100 м) — {int((pz.zone == 'средняя').sum())}", "fill", fill=C["green"], fa=1)
    m.add_legend(f"ближняя вне активного контроля (п. 3.3) — {len(pr)}", "fill", fill="#ffffff", fa=0, stroke=C["red"])
    m.add_legend("подъезд", "marker", fill="#16161c", shape="circle")
    m.save()

if __name__ == "__main__": m_playgrounds()
