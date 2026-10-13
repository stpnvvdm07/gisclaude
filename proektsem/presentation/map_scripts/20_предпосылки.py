# Карта «предпосылки» для презентации. Запуск: python3 20_предпосылки.py
import os, sys; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from mapkit import *

def m_pre(key="c_pre", w=1480, h=888):
    m = Map(key, w, h); m.base(cells="thin")
    cf = L(P, "pre_comfort_cells"); m.poly(cf.geometry.tolist(), "#E3F1DC", "#5EC46E", 1.6, z=3)
    po = L(P, "pre_osv_ctl"); m.poly([unary_union(po.geometry).buffer(0.6).buffer(-0.6)], "#7DCB86", z=4)
    ax_ = L(P, "pre_axes"); m.line(list(ax_.geometry), C["dark"], 3.2, z=14)
    nd = L(P, "pre_nodes"); m.pts([(p.x, p.y) for p in nd.geometry], "#2A9D4B", 15, "^", "white", 1.4)
    fav = L(os.path.join(V, "problems_v13.gpkg"), "pre_fav_closed"); m.pts([(p.x, p.y) for p in fav.geometry], C["blue"], 14, "*", "white", 0.8)
    mt = L(A, "metro"); m.poly([mt.geometry.iloc[0]], "#F3D7F2", C["pink"], 1.4, z=6)
    m.add_legend(f"комфортный двор — {len(cf)}", "fill", fill="#E3F1DC", fa=1, stroke="#5EC46E")
    m.add_legend(f"освоено и под контролем — {po.area.sum() / 1e4:.1f} га".replace(".", ","), "fill", fill="#7DCB86", fa=1)
    m.add_legend("людная пешеходная ось (4+ путей)", "line", stroke=C["dark"], sw=0.7)
    m.add_legend(f"организованный вход — {len(nd)}", "marker", fill="#2a9d4b", shape="triangle")
    m.add_legend(f"благоприятный закрытый объект — {len(fav)}", "marker", fill=C["blue"], shape="circle")
    m.add_legend("площадь у выхода метро", "fill", fill="#F3D7F2", fa=1, stroke=C["pink"])
    m.save()

if __name__ == "__main__": m_pre()
