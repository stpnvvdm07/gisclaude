# Карта «зоны контроля» для презентации. Запуск: python3 10_зоны_контроля.py
import os, sys; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from mapkit import *

def m_control_zones(w=960, h=540):
    z = L(A, "control_zones")
    m = Map("c_ctl_pers", w, h, margin=40); m.base(street=False)
    m.poly(z[z["type"] == "ПЖ"].geometry.tolist(), "#BFE3B4", z=4); m.poly(z[z["type"] == "АЖ"].geometry.tolist(), "#5EC46E", z=5, alpha=0.85)
    m.add_legend("активный: фасады с подъездами, 30 м", "fill", fill="#5ec46e", fa=1); m.add_legend("пассивный: торцы и фасады без подъездов, 15 м", "fill", fill="#bfe3b4", fa=1)
    m.streets(14); m.save()
    m = Map("c_ctl_pub", w, h, margin=40); m.base(street=False)
    m.poly(z[z["type"] == "ПП"].geometry.tolist(), "#DDD3EE", z=4); m.poly(z[z["type"] == "АП"].geometry.tolist(), "#B19FD8", z=5, alpha=0.9)
    m.add_legend("активный: людные пути, метро, переход, входы в организации, 15 м", "fill", fill="#B19FD8", fa=1)
    m.add_legend("пассивный: пути 2–3, участки школ, 7,5 м", "fill", fill="#DDD3EE", fa=1)
    m.streets(14); m.save()

if __name__ == "__main__": m_control_zones()
