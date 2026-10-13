# Карта «потоки людей» для презентации. Запуск: python3 09_потоки_людей.py
import os, sys; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from mapkit import *

def m_flows(key="c_flows", w=1480, h=888):
    m = Map(key, w, h); m.base(); n = net_all(m, "#C9C4BA", 0.7)
    hi = n[n.lgroup == "высокая"]; lo = n[n.lgroup == "низкая"]
    m.line(list(lo.geometry), "#E3A6E1", 1.6, z=12); m.line(list(hi.geometry), C["pink"], 4.5, z=12)
    m.add_legend(f"главные пешеходные оси (20+ путей) — {hi.length.sum() / 1000:.1f} км".replace(".", ","), "line", stroke=C["pink"], sw=1.1)
    m.add_legend(f"прочие используемые пути — {lo.length.sum() / 1000:.1f} км".replace(".", ","), "line", stroke="#E3A6E1", sw=0.4)
    fl = L(os.path.join(V, "analiz_v13.gpkg"), "flows"); col = {"высокий": C["dred"], "средний": C["orange"], "низкий": C["grey"]}
    for r in fl.sort_values("sat_human").itertuples():
        x, y = r.geometry.x, r.geometry.y; rad = (9 + 2.2 * math.sqrt(r.sat_human)) * m.mpp
        m.ax.add_patch(Circle((x, y), rad, facecolor=col[r.cls], edgecolor="white", lw=m.lw(1.5), zorder=32, alpha=0.95))
        m.text(x, y, str(r.id), 11 if r.sat_human < 20 else 13, "white", "semibold", halo=False, z=33)
        dx = 1 if x < m.cx else -1; m.text(x + dx * (rad + 4 * m.mpp), y, f"{r.sat_human}", 14, C["dark"], "bold", ha="left" if dx > 0 else "right", z=34)
        m.marks[f"flow{r.id}"] = m.px(x, y)
    mx, my = METRO_EXIT_PLAN; m.pts([(mx, my)], C["pink"], 22, "o", "white", 2); m.text(mx + 8, my + 10, "М", 13, "white", "bold", halo=False, z=50)
    m.ax.text(mx, my, "M", fontsize=12 * PT, color="white", fontweight="bold", ha="center", va="center", zorder=60)
    ax_, ay_ = MALL_CROSSING_PLAN; m.pts([(ax_, ay_ + 4)], C["purple"], 18, "s", "white", 2)
    m.text(mx + 16, my - 18, "выход метро", 14, C["dark"], "semibold", ha="left"); m.text(ax_, ay_ + 22, "переход к ТЦ", 14, C["dark"], "semibold")
    for k, cc in col.items(): m.add_legend(f"поток {k}", "marker", fill=cc, shape="circle")
    m.add_legend("номер точки в кружке, рядом — человек в час (суббота)", "marker", fill="#8b877f", shape="circle")
    m.save()

if __name__ == "__main__": m_flows()
