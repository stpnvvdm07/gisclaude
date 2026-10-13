# Карта «озеленение стоянки» для презентации. Запуск: python3 05_озеленение_стоянки.py
import os, sys; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from mapkit import *

def m_green(key="c_green", w=1280, h=720):
    m = Map(key, w, h); m.base()
    g = L(K, "green"); pk = L(K, "parking"); lz = L(K, "loading_zones")
    m.poly(list(g[g["type"] == "трава"].geometry), "#CFE7BE", z=3); m.poly(list(g[g["type"] == "деревья"].geometry), "#9ACD8A", z=3)
    for kind, col in (("открытая", C["lblue"]), ("гаражи", C["lilac"]), ("здание-паркинг", C["purple"])):
        d = pk[pk.kind.str.contains(kind, na=False)]; m.poly(list(d.geometry), col, C["edge"], 0.4, z=11)
    m.poly(list(lz.geometry), C["orange"], C["edge"], 0.4, z=12)
    m.add_legend("газон", "fill", fill="#CFE7BE", fa=1); m.add_legend("деревья", "fill", fill="#9ACD8A", fa=1)
    m.add_legend("открытая стоянка", "fill", fill=C["lblue"], fa=1); m.add_legend("гаражи", "fill", fill=C["lilac"], fa=1)
    m.add_legend("многоуровневый паркинг", "fill", fill=C["purple"], fa=1); m.add_legend("зона загрузки", "fill", fill=C["orange"], fa=1)
    m.save()

if __name__ == "__main__": m_green()
