# Выгрузка объектов нужных слоёв из чертежа yacheiki_1_v9.dwg (AutoCAD 2018, AC1032) в JSONL (координаты чертежа).
# Нужен пакет ezdwg (pip install "ezdwg==0.12.9"; читатель DWG только для чтения). Кириллические имена слоёв ezdwg 0.12.9
# декодирует со сдвигом бит - эти слои (районный набор: ПЛОЩАДКИ, ЛЕС, ПЕШЕХОДНЫЕ ...) внутри территории объектов не имеют и не выгружаются.
# Запуск: python dwg_extract.py [путь к dwg] [выход jsonl]
import sys, os, json, math
import ezdwg
HERE = os.path.dirname(os.path.abspath(__file__))
DWG = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "..", "raster", "yacheiki_1_v9.dwg")
OUT = sys.argv[2] if len(sys.argv) > 2 else os.path.join(HERE, "dwg_v9_ents.jsonl")
LAYERS = {"PL_DETSKAYA", "PL_SOBAKI", "PL_SPORT", "PL_VORKAUT", "AVTOSTOYANKI", "GREEN_AREAS"}   # площадки, стоянки, естественные покрытия

def arc_pts(pts, bulges, closed):
    """LWPOLYLINE с дугами (bulge) -> ломаная."""
    out, m = [], len(pts)
    for i in range(m if closed else m - 1):
        p, q = pts[i], pts[(i + 1) % m]; b = bulges[i] if bulges and i < len(bulges) else 0
        out.append((p[0], p[1]))
        if b and abs(b) > 1e-9:
            th = 4 * math.atan(b); dx, dy = q[0] - p[0], q[1] - p[1]; c = math.hypot(dx, dy)
            if c == 0: continue
            r = c / (2 * math.sin(th / 2)); mx, my = (p[0] + q[0]) / 2, (p[1] + q[1]) / 2; h = r * math.cos(th / 2)
            cx, cy = mx - h * dy / c, my + h * dx / c; a0 = math.atan2(p[1] - cy, p[0] - cx); seg = max(2, int(abs(th) / 0.15))
            for k in range(1, seg):
                a = a0 + th * k / seg; out.append((cx + abs(r) * math.cos(a), cy + abs(r) * math.sin(a)))
    if not closed: out.append((pts[-1][0], pts[-1][1]))
    return out

names = dict(ezdwg.raw.decode_layer_names(DWG))
doc = ezdwg.read(DWG); n = 0
with open(OUT, "w", encoding="utf-8") as f:
    for e in doc.modelspace().query("LWPOLYLINE HATCH CIRCLE"):
        d = e.dxf; ln = names.get(int(d.get("layer_handle")))
        if ln not in LAYERS: continue
        rec = {"layer": ln, "type": e.dxftype, "handle": e.handle, "color": d.get("resolved_color_index")}
        if e.dxftype == "LWPOLYLINE":
            pts = [(p[0], p[1]) for p in d["points"]]; closed = bool(d.get("closed")) or (int(d.get("flags") or 0) & 1) == 1
            rec.update(closed=closed, coords=arc_pts(pts, d.get("bulges"), closed))
        elif e.dxftype == "HATCH":
            rec.update(paths=[{"closed": p.get("closed"), "coords": [(x[0], x[1]) for x in p.get("points", [])]} for p in d["paths"]],
                       solid=d.get("solid_fill"), pattern=d.get("pattern_name"))
        else:
            rec.update(center=list(d["center"])[:2], r=d["radius"])
        f.write(json.dumps(rec, ensure_ascii=False) + "\n"); n += 1
print("выгружено объектов:", n, "->", OUT)
