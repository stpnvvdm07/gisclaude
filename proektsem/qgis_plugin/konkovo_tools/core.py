# Логика плагина без интерфейса — работает и в QGIS, и в скрипте (python3 / PyQGIS без экрана).
import os, re, glob
from qgis.core import QgsProject, QgsVectorLayer, QgsLayerTreeGroup, QgsProviderRegistry

PAT = re.compile(r"^(?P<base>[a-z_]+)_v(?P<ver>\d+)\.gpkg$", re.I)

def _parts(layer):
    if not isinstance(layer, QgsVectorLayer) or layer.providerType() != "ogr": return None
    d = QgsProviderRegistry.instance().decodeUri("ogr", layer.source())
    path = d.get("path") or ""; m = PAT.match(os.path.basename(path))
    if not m: return None
    return path, m.group("base"), int(m.group("ver")), d.get("layerName"), d.get("subset")

def _layers_in(path):
    try:
        from osgeo import ogr
        ds = ogr.Open(path); return {ds.GetLayer(i).GetName() for i in range(ds.GetLayerCount())} if ds else set()
    except Exception:
        return set()

def latest_versions(folder):
    best = {}
    for p in glob.glob(os.path.join(folder, "*_v*.gpkg")):
        m = PAT.match(os.path.basename(p))
        if m and int(m.group("ver")) > best.get(m.group("base"), (0, ""))[0]: best[m.group("base")] = (int(m.group("ver")), p)
    return best

def update_layers(project=None, log=print):
    """Перевести слои konkovo/analiz/problems_vNN на последнюю версию, если в ней есть слой с тем же именем."""
    pr = project or QgsProject.instance(); done, missing = [], []
    for lyr in list(pr.mapLayers().values()):
        p = _parts(lyr)
        if not p: continue
        path, base, ver, lname, subset = p
        best = latest_versions(os.path.dirname(path)).get(base)
        if not best or best[0] <= ver: continue
        if lname and lname not in _layers_in(best[1]): missing.append((lyr.name(), base, lname)); continue
        src = best[1] + (f"|layername={lname}" if lname else "") + (f"|subset={subset}" if subset else "")
        rel = os.path.relpath(best[1], pr.homePath()) if pr.homePath() else best[1]
        lyr.setDataSource(src, lyr.name(), "ogr"); done.append((lyr.name(), f"v{ver} → v{best[0]}"))
    for n, v in done: log(f"обновлён: {n} ({v})")
    for n, b, l in missing: log(f"нет в последней версии {b}: {n} (слой {l}) — оставлен как есть")
    return done, missing

def find_unneeded(project=None):
    """Битые слои, дубли (тот же источник), слои устаревших версий gpkg, пустые группы."""
    pr = project or QgsProject.instance(); out = []; seen = {}
    for lyr in pr.mapLayers().values():
        if not lyr.isValid(): out.append((lyr, "источник не найден")); continue
        p = _parts(lyr)
        if p:
            path, base, ver, lname, subset = p; best = latest_versions(os.path.dirname(path)).get(base)
            if best and best[0] > ver: out.append((lyr, f"устаревшая версия v{ver} (есть v{best[0]})")); continue
        key = (lyr.source(), lyr.renderer().type() if hasattr(lyr, "renderer") and lyr.renderer() else "")
        if key in seen and lyr.name() == seen[key].name(): out.append((lyr, "дубль слоя"))
        else: seen[key] = lyr
    return out

def empty_groups(group):
    res = []
    for ch in group.children():
        if isinstance(ch, QgsLayerTreeGroup):
            res += empty_groups(ch)
            if not ch.findLayers(): res.append(ch)
    return res

def remove_unneeded(project=None, log=print, items=None):
    pr = project or QgsProject.instance(); items = find_unneeded(pr) if items is None else items
    for lyr, why in items: log(f"удалён: {lyr.name()} — {why}"); pr.removeMapLayer(lyr.id())
    root = pr.layerTreeRoot(); n = 0
    for g in empty_groups(root):
        par = g.parent()
        if par is not None: par.removeChildNode(g); n += 1
    log(f"удалено пустых групп: {n}")
    return len(items), n
