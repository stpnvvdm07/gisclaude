# Подложка из чертежа AutoCAD (топосъёмка в МСК-77) -> лёгкая картинка с привязкой GIS/data/0_basemap/dwg_topo.tif (EPSG:32637).
# Линии чертежа рисуются тонко и светло на кремовом фоне (стиль карт команды); внутри границы нашей территории чертёж закрыт фоном —
# там актуальны наши слои ГИС. Охват — территория ± 700 м, 0,4 м на пиксель, сжатие JPEG и уменьшенные копии (пирамиды).
# Нужны: ezdwg==0.12.9 (чтение DWG), numpy, pyproj, matplotlib, shapely, geopandas; GDAL (gdal_translate) — для GeoTIFF,
# без него пишется PNG с файлом привязки .pgw.
#   python3 tools/dwg_basemap.py [чертёж.dwg]
import os, sys, math, subprocess, shutil
import numpy as np, geopandas as gpd
from pyproj import Transformer
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.collections import LineCollection, PolyCollection
import ezdwg

H = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DWG = sys.argv[1] if len(sys.argv) > 1 else os.path.join(H, "raster", "topo_konkovo.dwg")
OUT = os.path.join(H, "GIS", "data", "0_basemap", "dwg_topo.tif")
# система координат чертежа (Методика, разд. 2)
MSK77 = ("+proj=tmerc +lat_0=55.66666666667 +lon_0=37.5 +k=1 +x_0=12.268 +y_0=11.964 +ellps=bessel "
         "+towgs84=316.151,78.924,589.65,-1.57273,2.69209,2.34693,8.4507 +units=m +no_defs")
RES, PAD = 0.4, 700                                                 # м на пиксель, запас вокруг территории, м
BG, INK, FILL = "#F9F3E7", "#857C6F", "#E3DCCF"                     # фон, линии, заливки (SOLID)

tb = gpd.read_file(os.path.join(H, "vector", "konkovo_v16.gpkg"), layer="boundary").geometry.iloc[0]
x0, y0, x1, y1 = tb.bounds; x0, y0, x1, y1 = x0 - PAD, y0 - PAD, x1 + PAD, y1 + PAD
x0, y0 = math.floor(x0 / RES) * RES, math.floor(y0 / RES) * RES
W, Hh = int(round((x1 - x0) / RES)), int(round((y1 - y0) / RES)); x1, y1 = x0 + W * RES, y0 + Hh * RES
tr = Transformer.from_crs(MSK77, "EPSG:32637", always_xy=True)
inv = Transformer.from_crs("EPSG:32637", MSK77, always_xy=True)
lx, ly = inv.transform([x0, x1, x1, x0], [y0, y0, y1, y1]); LB = (min(lx) - 50, min(ly) - 50, max(lx) + 50, max(ly) + 50)


def arc_pts(pts, bulges, closed):
    out, m = [], len(pts)
    for i in range(m if closed else m - 1):
        p, q = pts[i], pts[(i + 1) % m]; b = bulges[i] if bulges and i < len(bulges) else 0
        out.append((p[0], p[1]))
        if b and abs(b) > 1e-9:
            th = 4 * math.atan(b); dx, dy = q[0] - p[0], q[1] - p[1]; c = math.hypot(dx, dy)
            if c == 0: continue
            r = c / (2 * math.sin(th / 2)); mx, my = (p[0] + q[0]) / 2, (p[1] + q[1]) / 2; h = r * math.cos(th / 2)
            cx, cy = mx - h * dy / c, my + h * dx / c; a0 = math.atan2(p[1] - cy, p[0] - cx); seg = max(2, int(abs(th) / 0.2))
            for k in range(1, seg):
                a = a0 + th * k / seg; out.append((cx + abs(r) * math.cos(a), cy + abs(r) * math.sin(a)))
    if closed and out: out.append(out[0])
    elif pts: out.append((pts[-1][0], pts[-1][1]))
    return out


def circle(c, r, a0=0.0, a1=2 * math.pi):
    if a1 < a0: a1 += 2 * math.pi
    n = max(8, int((a1 - a0) * max(r, 0.5) / 0.5)); n = min(n, 180)
    return [(c[0] + r * math.cos(a0 + (a1 - a0) * k / n), c[1] + r * math.sin(a0 + (a1 - a0) * k / n)) for k in range(n + 1)]


inside = lambda pts: any(LB[0] <= p[0] <= LB[2] and LB[1] <= p[1] <= LB[3] for p in pts)
lines, solids = [], []
for e in ezdwg.read(DWG).modelspace().query("LINE LWPOLYLINE CIRCLE ARC SOLID"):
    d = e.dxf; t = e.dxftype
    try:
        if t == "LINE": p = [d["start"][:2], d["end"][:2]]
        elif t == "LWPOLYLINE":
            pts = [(q[0], q[1]) for q in d["points"]]
            p = arc_pts(pts, d.get("bulges"), bool(d.get("closed")) or (int(d.get("flags") or 0) & 1) == 1)
        elif t == "CIRCLE": p = circle(d["center"][:2], d["radius"])
        elif t == "ARC":
            a0, a1 = d["start_angle"], d["end_angle"]
            if max(abs(a0), abs(a1)) > 7: a0, a1 = math.radians(a0), math.radians(a1)
            p = circle(d["center"][:2], d["radius"], a0, a1)
        else:
            q = [tuple(v[:2]) for v in d["points"]]; p = [q[0], q[1], q[3], q[2]] if len(q) == 4 else q
    except Exception:
        continue
    if len(p) < 2 or not inside(p): continue
    (solids if t == "SOLID" else lines).append(np.asarray(p, float))
print("линий:", len(lines), "| заливок:", len(solids))


def to_utm(geoms):
    if not geoms: return []
    a = np.vstack(geoms); x, y = tr.transform(a[:, 0], a[:, 1]); out, i = [], 0
    for g in geoms: out.append(np.c_[x[i:i + len(g)], y[i:i + len(g)]]); i += len(g)
    return out


fig = plt.figure(figsize=(W / 100, Hh / 100), dpi=100); ax = fig.add_axes([0, 0, 1, 1]); ax.set_axis_off()
ax.set_xlim(x0, x1); ax.set_ylim(y0, y1); fig.patch.set_facecolor(BG); ax.set_facecolor(BG)
ax.add_collection(PolyCollection(to_utm(solids), facecolors=FILL, edgecolors="none", zorder=1))
ax.add_collection(LineCollection(to_utm(lines), colors=INK, linewidths=0.6, zorder=2))
for g in getattr(tb, "geoms", [tb]):                                  # внутри территории — только фон
    ax.fill(*g.exterior.xy, color=BG, lw=0, zorder=3)
os.makedirs(os.path.dirname(OUT), exist_ok=True)
png = OUT[:-4] + "_tmp.png"; fig.savefig(png, dpi=100, facecolor=BG); plt.close(fig)

gt, ga = shutil.which("gdal_translate"), shutil.which("gdaladdo")
if gt:
    subprocess.run([gt, "-q", "-of", "GTiff", "-a_srs", "EPSG:32637", "-a_ullr", str(x0), str(y1), str(x1), str(y0), "-b", "1", "-b", "2", "-b", "3",
                    "-co", "COMPRESS=JPEG", "-co", "JPEG_QUALITY=85", "-co", "PHOTOMETRIC=YCBCR", "-co", "TILED=YES", png, OUT], check=True)
    if ga: subprocess.run([ga, "-q", "-r", "average", "--config", "COMPRESS_OVERVIEW", "JPEG", "--config", "PHOTOMETRIC_OVERVIEW", "YCBCR",
                           "--config", "INTERLEAVE_OVERVIEW", "PIXEL", OUT, "2", "4", "8", "16"], check=True)
    os.remove(png); print("готово:", OUT, f"{W}×{Hh} px,", round(os.path.getsize(OUT) / 1e6, 1), "МБ")
else:                                                                  # без GDAL: PNG + файл привязки
    out_png = OUT[:-4] + ".png"; os.replace(png, out_png)
    open(out_png[:-4] + ".pgw", "w").write(f"{RES}\n0\n0\n{-RES}\n{x0 + RES / 2}\n{y1 - RES / 2}\n")
    print("готово:", out_png, "(+ .pgw; система координат EPSG:32637)")
