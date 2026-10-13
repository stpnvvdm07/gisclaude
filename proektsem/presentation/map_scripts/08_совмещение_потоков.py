# Карта «совмещение потоков» для презентации. Запуск: python3 08_совмещение_потоков.py
import os, sys; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from mapkit import *

def m_combined(key="c_combined", w=1480, h=888):
    m = Map(key, w, h); m.base(); n = net_all(m)
    road = n[n["type"] == "проезд"]; m.line(list(road.geometry), "#9C978E", 2.2, z=10)
    used = n[n.ped >= 1]
    for rz, c in (("отдельно от проезда", C["green"]), ("по тротуару", C["blue"]), ("по проезжей части", C["red"])):
        m.line(list(used[used.razdel == rz].geometry), c, 2.6, z=14)
    cm = L(P, "p2_3_combined"); m.line(list(cm.geometry), C["orange"], 7.5, z=13, alpha=0.9)
    m.add_legend(f"совмещение потоков — {cm.length.sum():.0f} м", "line", stroke=C["orange"], sw=1.5)
    for rz, c in (("отдельно от проезда", C["green"]), ("по тротуару", C["blue"]), ("по проезжей части", C["red"])):
        m.add_legend(f"путь {rz} — {used[used.razdel == rz].length.sum() / 1000:.1f} км".replace(".", ","), "line", stroke=c, sw=0.6)
    m.add_legend("проезды", "line", stroke="#9C978E", sw=0.45)
    m.save()

if __name__ == "__main__": m_combined()
