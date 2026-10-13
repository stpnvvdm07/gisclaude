# Карта «износ и бизнес» для презентации. Запуск: python3 04_износ_и_бизнес.py
import os, sys; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from mapkit import *

def m_buildings(key="c_wear", w=960, h=540):
    m = Map(key, w, h, margin=40); m.base(bld=False, street=False)
    b = L(K, "buildings"); w4 = L(P, "p1_4_wear")
    m.poly(list(b.geometry), C["bld"], C["edge"], 0.4, z=10)
    hi = w4.geometry; m.poly(list(hi), C["dred"], C["edge"], 0.5, z=11)
    for r in w4.itertuples():
        p = r.geometry.representative_point(); m.text(p.x, p.y, f"{round(r.wear * 100)}%", 11, "white", "semibold", halo=C["dred"], z=26)
    m.add_legend(f"износ 40 % и больше — {len(w4)}", "fill", fill=C["dred"], fa=1); m.add_legend("износ меньше 40 % или нет данных", "fill", fill=C["bld"], fa=1)
    m.streets(14); m.save()
    m = Map("c_business", w, h, margin=40); m.base(street=False)
    bz = L(K, "business"); col = {"благоприятный": C["green"], "индифферентный": C["grey"], "опасный": C["red"]}
    for x, y, s in clusters(bz):
        # кластер — «соты» из точек: каждая точка — один объект своего цвета, сложены плотной спиралью вокруг центра
        n = len(s); d = 9 * m.mpp; pts_ = [(0, 0)]; ring_ = 1
        while len(pts_) < n:
            for k in range(6 * ring_):
                a_ = 2 * math.pi * k / (6 * ring_); pts_.append((ring_ * d * math.cos(a_), ring_ * d * math.sin(a_)))
            ring_ += 1
        for (dx, dy), dg in zip(pts_, s.sort_values("danger").danger):
            m.ax.add_patch(Circle((x + dx, y + dy), 4.2 * m.mpp, facecolor=col[dg], edgecolor="white", lw=m.lw(0.8), zorder=30))
    for k, cc in col.items(): m.add_legend(f"{k}: {int((bz.danger == k).sum())}", "marker", fill=cc, shape="circle")
    m.add_legend("одна точка — один объект; группа — кластер", "marker", fill="#8b877f", shape="circle")
    m.streets(14); m.save()

if __name__ == "__main__": m_buildings()
