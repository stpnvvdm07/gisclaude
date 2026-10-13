# Анализ, шаг 1 — базовые слои: ячейки и комфорт, входы во дворы, зоны загрузки.
# Вход: vector/source_data.gpkg (ячейки с ручным расчётом комфорта команды, здания, подъезды, бизнес, ограждения, арки, ворота,
#       зелень, сеть, зоны загрузки команды). Выход: vector/konkovo_v16.gpkg.
#
# Правила:
#  * ячейки анализа — 40 дворов в зафиксированных границах; ячейки без подъездов и за границами — вне анализа (п. 1.3);
#  * комфорт — по таблице команды (xlsx): вертикальные пропорции по Макарову (фасад × этажность × 3 м / площадь),
#    планировочный размер 25–140 м, замкнутость = длина фасадов / периметр; итог «комфортная» — как в таблице;
#    для сверки — комфорт по баллам (низкий 0, средний 1, высокий 2; размер 0 / 2; комфортно от 4 из 6);
#  * вход во двор — место, где путь с улицы проходит в жилой массив: в арке, между домами, в воротах или калитке ограждения;
#    ищется: (1) по каждому пути, пересекающему внешний край дворов, на первых 120 м внутрь (дома по обе стороны не дальше 60 м, просвет до 90 м);
#    (2) каждая арка с путём; (3) пересечение пути с просветом между соседними домами внешнего ряда;
#    типы с полевого обследования переносятся на найденные места (до 25 м); разрыв между домами до 30 м — организованный вход
#    (средняя фиксация), шире — неорганизованный (низкая);
#  * зоны загрузки — слой команды (competitions_2): 20 участков у торцов и фасадов с магазинами и сервисами.
import os, sys, math, warnings
import numpy as np, pandas as pd, geopandas as gpd, pyogrio
from shapely.geometry import Point, LineString
from shapely.ops import unary_union, substring
warnings.filterwarnings("ignore")
HERE = os.path.dirname(os.path.abspath(__file__)); V = os.path.join(HERE, "..", "vector")
SRC, K15 = os.path.join(V, "source_data.gpkg"), os.path.join(V, "konkovo_v16.gpkg")
K14 = A13 = SRC
rd = lambda f, l: gpd.read_file(f, layer=l)
def wr(df, f, l): pyogrio.write_dataframe(df, f, layer=l, driver="GPKG", append=False)
U = lambda gs: unary_union([g for g in gs if g is not None and not g.is_empty])
LOG = []
def log(*a): s = " ".join(str(x) for x in a); LOG.append(s); print(s)
if os.path.exists(K15): os.remove(K15)
# исходные слои, которые нужны дальше и на картах, — без изменений
for n in ("boundary", "buildings", "business", "entrances_buildings", "playgrounds", "garbage", "green", "trees", "parking", "fences", "arches",
          "gates", "crossings", "cells_excluded", "people_dens", "osv_manual"):
    wr(rd(SRC, n), K15, n)

# ---------------- ячейки и комфорт (таблица команды)
c = rd(SRC, "cells"); c["in_scope"] = (c.is_anal == 1).astype(int)
c["vert_koef"], c["vertical"], c["iso_koef"], c["isolation"], c["size"], c["planning"] = c.t_vert_koef, c.t_vertical.replace("Нет", "Низкий"), c.t_iso_koef, c.t_isolation, c.t_size, c.t_planning
c["fasad_area"], c["fasad_len"] = c.t_fasad_m2, c.t_fasad_len
P_ = {"Высокий": 2, "Средний": 1, "Низкий": 0}
c["score"] = ((c.vertical.map(P_) + c.isolation.map(P_) + np.where(c.planning == "Комфортная", 2, 0)) / 6).round(2)
c["comfort"] = c.t_comfort
c["comfort_rule"] = np.where(c.score >= 0.665, "Комфортная", "Некомфортная")
c = c[["num", "is_anal", "in_scope", "area", "perimeter", "fasad_area", "vert_koef", "vertical", "fasad_len", "iso_koef", "isolation", "size", "planning",
       "comfort", "score", "comfort_rule", "geometry"]]
S_ = c[c.in_scope == 1]
log("комфорт (таблица команды): комфортных", int((S_.comfort == "Комфортная").sum()), "из", len(S_), sorted(S_[S_.comfort == "Комфортная"].num.tolist()),
    "| по баллам:", int((S_.comfort_rule == "Комфортная").sum()), "| расходятся:", sorted(S_[S_.comfort != S_.comfort_rule].num.tolist()))
log("ячеек:", len(c), "| в анализе:", int(c.in_scope.sum()), "| вне границ без подъездов (только п. 1.3):", sorted(c[c.num.isin([14, 28])].num.tolist()))
wr(c, K15, "cells")

# ---------------- входы во дворы
b = rd(K14, "buildings"); b["geometry"] = b.buffer(0); BLD = U(b.geometry); BIG = U(b[b.area >= 120].geometry)
f = rd(K14, "fences"); HIGH = U(f[f.podtip.str.contains("высокое", na=False)].geometry)
arches = rd(K14, "arches"); ARCH = U(arches.buffer(4)); gates = rd(K14, "gates")
ex = rd(K14, "cells_excluded"); SC = c[c.in_scope == 1]
core = U(list(SC.geometry) + list(b.geometry) + list(ex.geometry)).buffer(1.5).buffer(-1.5)
core = max(core.geoms, key=lambda g: g.area) if core.geom_type == "MultiPolygon" else core
ring = core.exterior; TB = rd(K14, "boundary").geometry.iloc[0].exterior
TREES = U(rd(K14, "green").query("type == 'деревья'").geometry)
net = rd(A13, "network")
def side_hits(p, d, L=60):
    """Есть ли по обе стороны от пути (перпендикулярно направлению d) здание / высокое ограждение / арка в пределах L м."""
    nx, ny = -d[1], d[0]; out = []
    for s in (1, -1):
        ray = LineString([(p.x, p.y), (p.x + s * nx * L, p.y + s * ny * L)])
        hb = ray.intersection(BIG); hf = ray.intersection(HIGH)
        db = p.distance(hb) if not hb.is_empty else 99; df = p.distance(hf) if not hf.is_empty else 99
        out.append((min(db, df), "здание" if db <= df else "ограждение"))
    return out
FIXED = U([BIG.buffer(12), HIGH.buffer(4)])
# старты: пересечения пути с краем дворов и концы путей у края (до 8 м), от которых путь уходит внутрь
starts = []
for r in net.itertuples():
    g = r.geometry; L = g.length
    xs = g.intersection(ring)
    for x in getattr(xs, "geoms", [xs]):
        if x.geom_type == "Point":
            d0 = g.project(x); starts.append((r, d0, 1 if g.interpolate(min(L, d0 + 3)).within(core) else -1))
    for d0, inward in ((0.0, 1), (L, -1)):
        e_ = g.interpolate(d0)
        if e_.distance(ring) <= 8 and g.interpolate(min(L, max(0, d0 + inward * min(10, L)))).within(core.buffer(-1)):
            starts.append((r, d0, inward))
# граф сети для продолжения пути внутрь (по самому «прямому» соседнему ребру)
from collections import defaultdict
KEY = lambda xy: (round(xy[0], 1), round(xy[1], 1)); ADJ = defaultdict(list)
for i_, gg in enumerate(net.geometry):
    ADJ[KEY(gg.coords[0])].append(i_); ADJ[KEY(gg.coords[-1])].append(i_)
def walk(g, d0, inward, need):
    """Линия от точки d0 по ребру g в сторону inward и далее по сети (выбирая продолжение без резкого поворота) длиной need м."""
    seg = substring(g, d0, g.length) if inward > 0 else substring(g, d0, 0)
    coords = list(seg.coords) if seg.geom_type == "LineString" else [g.interpolate(d0).coords[0]]
    used = {id(g)}; total = LineString(coords).length if len(coords) > 1 else 0
    while total < need:
        end = coords[-1]; prev = coords[-2] if len(coords) > 1 else end
        v0 = np.array(end) - np.array(prev); best = None
        for j in ADJ[KEY(end)]:
            gj = net.geometry.iloc[j]
            if id(gj) in used: continue
            cs = list(gj.coords) if KEY(gj.coords[0]) == KEY(end) else list(gj.coords)[::-1]
            v1 = np.array(cs[min(2, len(cs) - 1)]) - np.array(cs[0]); den = np.linalg.norm(v0) * np.linalg.norm(v1)
            cos = float(v0 @ v1 / den) if den else 0
            if best is None or cos > best[0]: best = (cos, cs, gj)
        if best is None or best[0] < 0.3: break
        used.add(id(best[2])); coords += best[1][1:]; total = LineString(coords).length
    return LineString(coords) if len(coords) > 1 else LineString([coords[0], coords[0]])
cands = []
for r, d0, inward in starts:
        g = r.geometry; L = g.length; x = g.interpolate(d0)
        found = None
        path = walk(g, d0, inward, 120)
        for k in range(0, int(path.length) + 1, 2):
            p = path.interpolate(k); q = path.interpolate(min(path.length, k + 1.5))
            v = np.array([q.x - p.x, q.y - p.y]); n_ = np.linalg.norm(v)
            if n_ == 0: continue
            if p.within(ARCH.buffer(2)): found = (p, "Вход — арка", "высокая", 0); break
            gt = gates[gates.distance(p) <= 6]
            if len(gt): found = (gt.geometry.iloc[0], "Вход — ворота" if r.type == "проезд" else "Вход — калитка", "высокая", 0); break
            (d1, t1), (d2, t2) = side_hits(p, v / n_)
            if d1 + d2 <= 90 and d1 < 60 and d2 < 60:
                if "здание" in (t1, t2):
                    # узкий разрыв (до 30 м) держит вход — средняя фиксация; широкий — низкая (вход не организован)
                    found = (p, "Вход — разрыв в застройке", "средняя" if d1 + d2 <= 30 else "низкая")
                else: found = (p, "Вход — ворота" if r.type == "проезд" else "Вход — калитка", "высокая")
                found = found + (round(d1 + d2),); break
        if found is None:
            # путь так и не прошёл между домами: вход на краю двора есть, только если фасад двора здесь закреплён
            # (дом или высокое ограждение по обе стороны вдоль края, до 25 м); на открытом фронте отдельного входа нет
            p = x; s0 = ring.project(p); sides = [ring.interpolate((s0 + dl) % ring.length) for dl in (-25, 25)]
            if not all(FIXED.distance(q) <= 3 for q in sides): continue
            kind = "Вход — въезд" if r.type == "проезд" else ("Вход — разрыв в насаждениях" if TREES.distance(p) <= 6 else "Вход — не зафиксирован")
            found = (p, kind, "низкая" if kind != "Вход — не зафиксирован" else "нет", None)
        cands.append(dict(podtip=found[1], degree=found[2], gap_m=found[3], path_type=r.type, geometry=found[0]))
# 2) арки: каждая арка, через которую идёт путь сети, — вход (смешанная арка в доме — тоже)
for g_ in arches.geometry:
    hit = net[net.distance(g_) <= 4]
    if not len(hit): continue
    p = hit.geometry.iloc[0].interpolate(hit.geometry.iloc[0].project(g_.centroid))
    cands.append(dict(podtip="Вход — арка", degree="высокая", gap_m=0, path_type="арка", geometry=p))
# 3) просветы во внешнем ряду домов: отрезок между соседними домами внешнего ряда (до 90 м, без других зданий на нём);
#    путь сети, пересекающий такой отрезок, — вход «разрыв в застройке» в месте пересечения
OUTER = b[(b.area >= 300) & (b.distance(ring) <= 45)].reset_index(drop=True)
from shapely.ops import nearest_points
gaps = []
for i_ in range(len(OUTER)):
    for j_ in range(i_ + 1, len(OUTER)):
        gi, gj = OUTER.geometry[i_], OUTER.geometry[j_]
        if gi.distance(gj) > 90 or gi.distance(gj) < 2: continue
        pa, pb = nearest_points(gi, gj); seg = LineString([pa, pb])
        if seg.buffer(-0.01).length if False else seg.difference(gi.buffer(0.5)).difference(gj.buffer(0.5)).intersects(BLD.difference(gi.buffer(0.5)).difference(gj.buffer(0.5))): continue
        mid = seg.interpolate(0.5, normalized=True)
        if not mid.within(core) or mid.distance(ring) > 45: continue
        # просвет — часть фронта: отрезок примерно параллелен ближайшему участку внешнего края (до 35°)
        s_ = ring.project(mid); q1, q2 = ring.interpolate(s_ - 10), ring.interpolate(s_ + 10)
        a1 = math.atan2(q2.y - q1.y, q2.x - q1.x); a2 = math.atan2(pb.y - pa.y, pb.x - pa.x)
        dang = abs((math.degrees(a1 - a2) + 90) % 180 - 90)
        if dang > 35: continue
        gaps.append(seg)
# у каждого дома — только просветы к ближайшим соседям по фронту (не больше двух)
keep_g = []
for i_, gi in enumerate(OUTER.geometry):
    mine = sorted([s for s in gaps if s.distance(gi) < 1], key=lambda s: s.length)[:2]; keep_g += mine
gaps = list({s.wkt: s for s in keep_g}.values())
for seg in gaps:
    for r in net.itertuples():
        x_ = r.geometry.intersection(seg)
        for p in getattr(x_, "geoms", [x_]):
            if p.geom_type == "Point":
                cands.append(dict(podtip="Вход — разрыв в застройке", degree="средняя" if seg.length <= 30 else "низкая", gap_m=round(seg.length), path_type=r.type, geometry=p))
C_ = gpd.GeoDataFrame(cands, crs=32637)
# слить кандидаты ближе 18 м (один вход — один узел), приоритет: арка > ворота/калитка > разрыв > въезд > прочие
PR = {"Вход — арка": 0, "Вход — ворота": 1, "Вход — калитка": 1, "Вход — разрыв в застройке": 2, "Вход — въезд": 3, "Вход — разрыв в насаждениях": 4, "Вход — не зафиксирован": 5}
C_["pr"] = C_.podtip.map(PR); C_ = C_.sort_values("pr").reset_index(drop=True); keep = []; used = set()
for i, p in enumerate(C_.geometry):
    if i in used: continue
    grp = [j for j, q in enumerate(C_.geometry) if j not in used and p.distance(q) <= 18]; used |= set(grp); keep.append(i)
E = C_.loc[keep].copy()
# вход — на внешнем фронте дворов: не дальше 45 м от края (арка — 60 м); глубже — проходы между дворами, это не вход в жилое образование
E["d_edge"] = E.distance(ring).round(1)
E = E[(E.d_edge <= 45) | ((E.podtip == "Вход — арка") & (E.d_edge <= 60))].copy()
# типы и фото с полевого обследования (до 25 м)
sv = rd(K14, "entries_territory"); sv = sv[sv.src.astype(str).str.startswith(("обследование", "замер", "слой arches"))]
E["src"] = "по сети и застройке"; E["photo"] = None
for i, r in E.iterrows():
    m = sv[sv.distance(r.geometry) <= 25]
    if len(m):
        s_ = m.loc[m.distance(r.geometry).idxmin()]
        # тип обследования, кроме «въезд/не зафиксирован», если геометрия нашла арку или разрыв между домами
        if s_.podtip in ("Вход — арка", "Вход — ворота", "Вход — калитка") or r.pr > 2:
            E.loc[i, ["podtip", "degree"]] = [s_.podtip, s_.degree]
        E.loc[i, "src"] = "обследование + место по застройке"; E.loc[i, "photo"] = s_.photo
E["fix_class"] = np.where(E.degree.isin(["высокая", "средняя"]), "организован", "не организован")
E = E.drop(columns=["pr"]).reset_index(drop=True); E["node"] = E.index + 1
E["cells"] = E.geometry.apply(lambda p: ",".join(str(n) for n, g in SC.set_index("num").geometry.items() if g.distance(p) <= 8))
E = gpd.GeoDataFrame(E, crs=32637)
log("входы:", len(E), "| организованы:", int((E.fix_class == "организован").sum()), "| по типу:", E.podtip.str.replace("Вход — ", "").value_counts().to_dict(),
    "| с данными обследования:", int(E.src.str.startswith("обслед").sum()))
wr(E, K15, "entries_territory")
wr(gpd.GeoDataFrame({"what": ["внешний край дворов"]}, geometry=[LineString(ring.coords)], crs=32637), K15, "core_edge")

# ---------------- зоны загрузки (слой команды competitions_2)
bz = rd(K14, "business")
LOAD_KINDS = {"магазин", "общепит", "аптека", "пункт выдачи", "торговый центр", "для питомцев", "секон-хэнд", "почта"}
src = bz[bz["Назначение"].isin(LOAD_KINDS)]
LZ = rd(SRC, "loading_zones").reset_index(drop=True); LZ["geometry"] = LZ.buffer(0); LZ["area"] = LZ.area.round()
LZ["objects"] = LZ.geometry.apply(lambda g: ", ".join(sorted(set(src[src.distance(g) <= 40]["Назначение"]))))
LZ = LZ[["area", "function", "danger", "isolation", "objects", "geometry"]]
log("зоны загрузки (команда):", len(LZ), "| площадь, м²:", int(LZ.area.sum()), "| закрытых:", int((LZ.isolation == "закрытый").sum()))
wr(LZ, K15, "loading_zones")

# открытый фронт двора: участки внешнего края без зданий и высоких ограждений рядом (вход «везде») — для карты и п. 1.1
OPEN_EDGE = LineString(ring.coords).difference(FIXED.buffer(3))
oe = gpd.GeoDataFrame(geometry=[g for g in getattr(OPEN_EDGE, "geoms", [OPEN_EDGE]) if g.length >= 15], crs=32637); oe["length"] = oe.length.round()
log("открытый фронт дворов (без закрепления, вход с любого места):", len(oe), "участков,", int(oe.length.sum()), "м")
wr(oe, K15, "open_edge")
