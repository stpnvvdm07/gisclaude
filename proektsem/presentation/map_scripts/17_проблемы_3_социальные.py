# Карта «проблемы 3 социальные» для презентации. Запуск: python3 17_проблемы_3_социальные.py
import os, sys; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from mapkit import *

def m_prob3(key="c_p3", w=1480, h=888):
    m = Map(key, w, h); m.base(); v = cells_in(); SC = unary_union(v.geometry)
    un = L(P, "p3_4_uncontrolled"); cp = L(P, "p3_4_competition"); ab = L(P, "p3_4_abandoned")
    m.poly(un.geometry.tolist(), "#F2C6C0", z=4); m.poly(cp.geometry.tolist(), "#B9A3D9", z=5); m.poly(ab.geometry.tolist(), C["dred"], z=6)
    tr = L(os.path.join(V, "analiz_v13.gpkg"), "transit"); cz = L(A, "control_zones")
    RES = unary_union(cz[cz["type"].isin(["АЖ", "ПЖ"])].geometry); TRH = unary_union(tr[tr.cls == "высокая"].geometry).intersection(RES).intersection(SC)
    m.line([TRH], C["dark"], 3.0, z=14, ls=(0, (3, 1.5)))
    pl = L(P, "p3_3_places"); m.poly(pl.geometry.tolist(), C["yellow"], C["red"], 2.4, z=15)
    bz = L(K, "business"); serv = bz[bz.function == "обслуживающий"]; TRP = unary_union(tr[(tr.cls == "высокая") & (tr["mode"] == "пешеходный")].geometry)
    s32 = serv[serv.distance(TRP) <= 15]; s32 = s32[s32.geometry.apply(lambda p: SC.distance(p) <= 6)]
    m.pts([(p.x, p.y) for p in s32.geometry], C["blue"], 16, "D", "white", 1.4)
    for r in v[(v.p3_1 + v.p3_2 + v.p3_3 + v.p3_4) > 0].itertuples():
        p = r.geometry.representative_point(); m.text(p.x, p.y, str(r.num), 13, C["dark"], "semibold", z=25)
    m.add_legend(f"3.1 транзит под окнами — {TRH.length:.0f} м, {int(v.p3_1.sum())} ячеек", "line", stroke=C["dark"], sw=0.6, dash=True)
    m.add_legend(f"3.2 сервис с внешним транзитом — {int(v.p3_2.sum())} ячейка", "marker", fill=C["blue"], shape="diamond")
    m.add_legend(f"3.3 площадка без нужного контроля — {len(pl)}", "fill", fill=C["yellow"], fa=1, stroke=C["red"])
    m.add_legend(f"3.4 неконтролируемая территория", "fill", fill="#F2C6C0", fa=1)
    m.add_legend(f"3.4 конкуренция активных контролей", "fill", fill="#B9A3D9", fa=1)
    m.add_legend(f"3.4 заброшенная территория", "fill", fill=C["dred"], fa=1)
    m.save()

if __name__ == "__main__": m_prob3()
