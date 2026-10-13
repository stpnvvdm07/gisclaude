# Карта «деревья путей» для презентации. Запуск: python3 07_деревья_путей.py
import os, sys; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from mapkit import *

def m_networks(w=960, h=540):
    m = Map("c_ped", w, h, margin=40); m.base(street=False); n = net_all(m)
    for g, c, lw in (("один путь", "#8B877F", 1.4), ("низкая", C["orange"], 2.8), ("высокая", C["dred"], 4.2)): m.line(list(n[n.group == g].geometry), c, lw, z=14)
    for g, c, lw, lab in (("высокая", C["dred"], 4.2, "4 пути и больше"), ("низкая", C["orange"], 2.8, "2–3 пути"), ("один путь", "#8B877F", 1.4, "один путь")):
        m.add_legend(f"{lab} — {n[n.group == g].length.sum() / 1000:.1f} км".replace(".", ","), "line", stroke=c, sw=lw / 4)
    m.add_legend("прочие дорожки и проезды", "line", stroke="#B9B4AA", sw=0.25)
    m.streets(14); m.save()
    m = Map("c_veh", w, h, margin=40); m.base(street=False); n = net_all(m)
    for g, c, lw in (("низкая", C["lblue"], 2.8), ("высокая", C["purple"], 4.2)): m.line(list(n[n.vgroup == g].geometry), c, lw, z=14)
    for g, c, lw, lab in (("высокая", C["purple"], 4.2, "4 пути и больше"), ("низкая", C["lblue"], 2.8, "2–3 пути")):
        m.add_legend(f"{lab} — {n[n.vgroup == g].length.sum() / 1000:.1f} км".replace(".", ","), "line", stroke=c, sw=lw / 4)
    m.add_legend("прочие проезды и дорожки", "line", stroke="#B9B4AA", sw=0.25)
    m.streets(14); m.save()

if __name__ == "__main__": m_networks()
