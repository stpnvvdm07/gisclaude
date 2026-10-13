# Карта «контроль x освоенность» для презентации. Запуск: python3 14_контроль_x_освоенность.py
import os, sys; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from mapkit import *

def m_ctl_osv(key="c_ctl_osv", w=1280, h=720):
    m = Map(key, w, h); m.base()
    o = L(A, "osvoennost"); o = o[o.cls != "не оценивается"].copy(); c = L(A, "control")
    cc = o.geometry.centroid
    def cls_of(z): return cc.within(unary_union(c[c["type"] == z].geometry))
    o["ctl"] = np.select([cls_of("контролируемая"), cls_of("частично контролируемая")], ["к", "ч"], default="н")
    cat = {("освоенная", "к"): ("#3FA35A", "освоено, под контролем"), ("освоенная", "ч"): ("#8FCB8F", "освоено, присмотр слабый"),
           ("освоенная", "н"): ("#CFE7C4", "освоено без присмотра"), ("частично освоенная", "к"): ("#E9D68A", "частично освоено"),
           ("частично освоенная", "ч"): ("#E9D68A", "частично освоено"), ("частично освоенная", "н"): ("#F2E6B8", "частично, без присмотра"),
           ("неосвоенная", "к"): ("#E8A29B", "заброшено при контроле"), ("неосвоенная", "ч"): ("#D9786E", "заброшено, присмотр слабый"),
           ("неосвоенная", "н"): (C["dred"], "заброшено и без контроля")}
    seen = {}
    for (cl, ct), (col, lab) in cat.items():
        d = o[(o.cls == cl) & (o.ctl == ct)]
        if len(d): m.poly(d.geometry.tolist(), col, "#FFFFFF", 0.4, z=4); seen.setdefault(lab, (col, d.area.sum()))
    for lab, (col, a_) in seen.items(): m.add_legend(f"{lab} — {a_ / 1e4:.1f} га".replace(".", ","), "fill", fill=col, fa=1)
    m.save()

# ---------------- проблемы

if __name__ == "__main__": m_ctl_osv()
