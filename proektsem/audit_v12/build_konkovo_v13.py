# konkovo_v13.gpkg = konkovo_v12.gpkg с заменой слоёв green и parking на слои из чертежа yacheiki_1_v9.dwg (vector/pokrytiya_v9.gpkg).
# Деление зелени на траву / деревья - по правилу Методики (разд. 5): деревья = кроны (полигоны «деревья» green v12, со спутника),
# массивы деревьев съёмки (радиус кроны 3,5 м, соседние кроны слиты; одиночная крона массивом не считается) и древесные полигоны
# OSM (слой чертежа ZEL_LES_DREVESNYE); трава - остальное естественное покрытие. Деревья берутся только в пределах покрытия v9.
# Запуск: python build_konkovo_v13.py   (пути - относительно папки скрипта)
import os, json, shutil, warnings
import pandas as pd, geopandas as gpd, pyogrio
from shapely.geometry import Polygon
from shapely.ops import unary_union
from pyproj import Transformer
warnings.filterwarnings("ignore")
HERE = os.path.dirname(os.path.abspath(__file__)); V = os.path.join(HERE, "..", "vector")
K12, K13, PV9 = os.path.join(V, "konkovo_v12.gpkg"), os.path.join(V, "konkovo_v13.gpkg"), os.path.join(V, "pokrytiya_v9.gpkg")
ENTS = os.path.join(HERE, "dwg_v9_ents.jsonl")

nat = gpd.read_file(PV9, layer="natural_v9"); N = unary_union(nat.geometry)
pk9 = gpd.read_file(PV9, layer="parking_v9")
gr12 = gpd.read_file(K12, layer="green"); trees = gpd.read_file(K12, layer="trees")

# 1) кроны v12
crowns = unary_union(gr12[gr12["type"] == "деревья"].buffer(0))
# 2) массивы деревьев съёмки: буфер 3,5 м, компонента из >= 2 деревьев
buf = unary_union(trees.buffer(3.5)); comps = list(buf.geoms) if hasattr(buf, "geoms") else [buf]
massifs = unary_union([c for c in comps if trees.within(c).sum() >= 2])
# 3) древесные полигоны OSM из чертежа (слой ZEL_LES_DREVESNYE в выгрузке dwg_extract.py)
osm_wood = Polygon()
SRC = ("+proj=tmerc +lat_0=55.66666666667 +lon_0=37.5 +k=1 +x_0=12.268 +y_0=11.964 +ellps=bessel "
       "+towgs84=316.151,78.924,589.65,-1.57273,2.69209,2.34693,8.4507 +units=m +no_defs")
tr = Transformer.from_crs(SRC, "EPSG:32637", always_xy=True)
ps = []
for l in open(ENTS, encoding="utf-8"):
    r = json.loads(l)
    if r["layer"] == "ZEL_LES_DREVESNYE" and r["type"] == "LWPOLYLINE":
        x, y = tr.transform([c[0] for c in r["coords"]], [c[1] for c in r["coords"]])
        if len(x) >= 3: ps.append(Polygon(zip(x, y)).buffer(0))
osm_wood = unary_union(ps) if ps else Polygon()
print("древесных полигонов OSM:", len(ps))
TREES = unary_union([crowns, massifs, osm_wood])

rows = []
for g in nat.geometry:
    for geom, typ in ((g.intersection(TREES), "деревья"), (g.difference(TREES), "трава")):
        for p in (geom.geoms if hasattr(geom, "geoms") else [geom]):
            if isinstance(p, Polygon) and p.area >= 2:
                rows.append(dict(type=typ, area=round(p.area), src="dwg_v9 GREEN_AREAS", geometry=p))
GN = gpd.GeoDataFrame(rows, crs=32637)
# слить соседние куски одного типа (после разрезки)
GN = GN.dissolve(by="type", as_index=False).explode(index_parts=False).reset_index(drop=True)
GN = GN[GN.area >= 2].copy(); GN["area"] = GN.area.round().astype(int); GN["src"] = "dwg_v9 GREEN_AREAS"
GN = GN[["type", "area", "src", "geometry"]]

PK = pk9[["kind", "status", "dwg_handle", "geometry"]].copy()
PK["area"] = PK.area.round().astype(int); PK = PK[["kind", "area", "status", "dwg_handle", "geometry"]]

shutil.copyfile(K12, K13)
for name, df in (("green", GN), ("parking", PK)):
    pyogrio.write_dataframe(df, K13, layer=name, driver="GPKG", append=False)   # перезапись слоя
# проверка
for name in ("green", "parking"):
    d = gpd.read_file(K13, layer=name); print(name, len(d), "valid", d.is_valid.all(), "crs", d.crs.to_epsg(), d.columns.tolist())
print("остальные слои без изменений:", [n for n, _ in pyogrio.list_layers(K13)])
cmp = pd.DataFrame({"v12": gr12.assign(a=gr12.area).groupby("type").a.sum().round(), "v13": GN.groupby("type").area.sum()})
print(cmp, "\nвсего v12", round(gr12.area.sum()), "v13", GN.area.sum())
print("деревья v13 по источнику: кроны v12", round(N.intersection(crowns).area), "| + массивы съёмки", round(N.intersection(massifs).difference(crowns).area),
      "| + лес OSM", round(N.intersection(osm_wood).difference(crowns).difference(massifs).area))
print("стоянки v12", round(gpd.read_file(K12, layer="parking").area.sum()), "v13", PK.area.sum(), PK.status.value_counts().to_dict())
