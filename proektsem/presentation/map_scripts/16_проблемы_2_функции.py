# Карта «проблемы 2 функции» для презентации. Запуск: python3 16_проблемы_2_функции.py
import os, sys; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from mapkit import *

def m_prob2(key="c_p2", w=1480, h=888):
    m = Map(key, w, h); m.base(); v = cells_in()
    n = L(A, "network"); road = n[n["type"] == "проезд"]; m.line(list(road.geometry), "#AAA49A", 2.4, z=9)
    lz = L(K, "loading_zones"); m.poly(lz.geometry.tolist(), C["purple"], C["edge"], 0.4, z=12)
    cm = L(P, "p2_3_combined"); m.line(list(cm.geometry), C["orange"], 7, z=13)
    gb = L(K, "garbage"); bz = L(K, "business"); dang = bz[(bz.danger == "опасный") & (bz.isolation == "открытый")]
    m.pts([(p.x, p.y) for p in pd.concat([gb.geometry, dang.geometry])], C["dark"], 16, "X", "white", 1.4)
    for r in v[(v.p2_1 + v.p2_2 + v.p2_3) > 0].itertuples():
        p = r.geometry.representative_point(); m.text(p.x, p.y, str(r.num), 13, C["dark"], "semibold", z=25)
    m.add_legend(f"2.1 загрузка с заездом грузовиков — {len(lz)} зон, {int(v.p2_1.sum())} ячеек", "fill", fill=C["purple"], fa=1)
    m.add_legend(f"2.2 опасный открытый объект — {len(gb) + len(dang)}, {int(v.p2_2.sum())} ячеек", "marker", fill="#16161c", shape="cross_fill")
    m.add_legend(f"2.3 пешеходы и машины на одном проезде — {cm.length.sum():.0f} м, {int(v.p2_3.sum())} ячеек", "line", stroke=C["orange"], sw=1.4)
    m.add_legend("внутриквартальные проезды", "line", stroke="#AAA49A", sw=0.5)
    m.save()

if __name__ == "__main__": m_prob2()
