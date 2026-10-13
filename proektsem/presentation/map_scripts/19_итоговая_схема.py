# Карта «итоговая схема» для презентации. Запуск: python3 19_итоговая_схема.py
import os, sys; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from mapkit import *

def m_final(key="c_final", w=1180, h=740):
    """Итоговая схема в духе прошлогоднего примера: сгруппированные проблемы, ячейки-лидеры обведены."""
    m = Map(key, w, h, margin=40); m.base(cells="thin"); v = cells_in()
    for cl_, col_ in (("средняя", "#F5EBC8"), ("высокая", "#F3C9C3")): m.poly(v[v.cls == cl_].geometry.tolist(), col_, z=2.5)
    un = L(P, "p3_4_uncontrolled"); m.poly(un.geometry.tolist(), "none", "#C98B84", 0.6, z=3, hatch="....")
    cp = L(P, "p3_4_competition"); m.poly(cp.geometry.tolist(), "#C9B7E3", z=4)
    ab = L(P, "p3_4_abandoned"); m.poly(ab.geometry.tolist(), C["dred"], z=5, hatch="////")
    w4 = L(P, "p1_4_wear"); m.poly(w4.geometry.tolist(), C["dred"], C["edge"], 0.5, z=12)
    lz = L(K, "loading_zones"); m.poly(lz.geometry.tolist(), C["purple"], z=12)
    cm = L(P, "p2_3_combined"); m.line(list(cm.geometry), C["orange"], 5, z=13)
    nd = L(P, "p1_2_nodes"); m.pts([(p.x, p.y) for p in nd.geometry], C["red"], 14, "^", "white", 1.3)
    pl = L(P, "p3_3_places"); m.poly(pl.geometry.tolist(), C["yellow"], C["red"], 2, z=15)
    gb = L(K, "garbage"); m.pts([(p.x, p.y) for p in gb.geometry], C["dark"], 12, "X", "white", 1)
    top = v[v.score >= 5]
    for r in top.itertuples():
        m.poly(r.geometry, "none", C["pink"], 3.2, z=20)
        p = r.geometry.representative_point(); m.text(p.x, p.y, str(r.num), 17, C["dark"], "bold", z=26, halo="white")
        m.marks[f"cell{r.num}"] = m.px(p.x, p.y)
    for nm, (x, y) in (("metro", METRO_EXIT_PLAN), ("mall", MALL_CROSSING_PLAN)): m.marks[nm] = m.px(x, y)
    m.add_legend("ячейка с 5+ нарушениями (обведена)", "fill", fill="#ffffff", fa=0, stroke=C["pink"])
    m.add_legend("высокий счёт (6+)", "fill", fill="#F3C9C3", fa=1); m.add_legend("средний счёт (4–5)", "fill", fill="#F5EBC8", fa=1)
    m.add_legend("неконтролируемая территория", "fill", fill="#ffffff", fa=1, stroke="#C98B84", hatch=True); m.add_legend("конкуренция активных контролей", "fill", fill="#C9B7E3", fa=1)
    m.add_legend("заброшенная территория", "fill", fill=C["dred"], fa=0.6, hatch=True)
    m.add_legend("изношенное здание (от 40 %)", "fill", fill=C["dred"], fa=1); m.add_legend("зона загрузки", "fill", fill=C["purple"], fa=1)
    m.add_legend("пешеходы на проезде", "line", stroke=C["orange"], sw=1.2); m.add_legend("неорганизованный вход", "marker", fill="#d62828", shape="triangle")
    m.add_legend("мусорная площадка", "marker", fill="#16161c", shape="cross_fill"); m.add_legend("площадка без нужного контроля", "fill", fill=C["yellow"], fa=1, stroke=C["red"])
    m.save()
    # фрагменты ячеек-лидеров для круглых врезок
    for r in top.itertuples():
        c0 = r.geometry.centroid; z = Map(f"c_zoom_{r.num}", 480, 480, center=(c0.x, c0.y), extent=230)
        z.base(cells="thin", street=False)
        z.poly(un.geometry.tolist(), "#F6D3CE", z=3); z.poly(cp.geometry.tolist(), "#C9B7E3", z=4); z.poly(ab.geometry.tolist(), C["dred"], z=5, hatch="////")
        z.poly(w4.geometry.tolist(), C["dred"], C["edge"], 0.5, z=12); z.poly(lz.geometry.tolist(), C["purple"], z=12)
        z.line(list(cm.geometry), C["orange"], 5, z=13); z.pts([(p.x, p.y) for p in nd.geometry], C["red"], 16, "^", "white", 1.3)
        z.pts([(p.x, p.y) for p in gb.geometry], C["dark"], 14, "X", "white", 1)
        z.poly(r.geometry, "none", C["pink"], 4, z=20); z.save()

if __name__ == "__main__": m_final()
