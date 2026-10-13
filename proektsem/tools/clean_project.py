# Перевод proektsem.qgz на последнюю версию данных без запуска QGIS (правка XML внутри .qgz, всё остальное в проекте не трогается):
#   konkovo/analiz/problems_vNN.gpkg -> самая свежая версия в vector/, если в ней есть слой с тем же именем.
# Также печатает слои с источниками, которых нет на диске (их удаляет плагин «Коньково» в QGIS, если они правда не нужны).
#   python3 tools/clean_project.py [proektsem.qgz]
import os, re, sys, zipfile, shutil, tempfile
import pyogrio
H = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
QGZ = sys.argv[1] if len(sys.argv) > 1 else os.path.join(H, "proektsem.qgz")
V = os.path.join(H, "vector"); PAT = re.compile(r"^([a-z_]+)_v(\d+)\.gpkg$")
best = {}
for f in os.listdir(V):
    m = PAT.match(f)
    if m and int(m.group(2)) > best.get(m.group(1), (0,))[0]: best[m.group(1)] = (int(m.group(2)), f)
layers = {f: {n for n, _ in pyogrio.list_layers(os.path.join(V, f))} for _, f in best.values()}
with zipfile.ZipFile(QGZ) as z: names = z.namelist(); data = {n: z.read(n) for n in names}
qgs = next(n for n in names if n.endswith(".qgs")); x = data[qgs].decode("utf-8")
cnt = {}
def sub(m):
    base, ver, lname = m.group(1), int(m.group(2)), m.group(3)
    b = best.get(base)
    if not b or b[0] <= ver or lname not in layers[b[1]]: return m.group(0)
    cnt[f"{base} v{ver} → v{b[0]}"] = cnt.get(f"{base} v{ver} → v{b[0]}", 0) + 1
    return f"{base}_v{b[0]}.gpkg|layername={lname}"
x = re.sub(r"([a-z_]+)_v(\d+)\.gpkg\|layername=([A-Za-z0-9_]+)", sub, x)
for k, v in cnt.items(): print("заменено:", k, "—", v, "ссылок")
missing = sorted({s for s in re.findall(r'source="\./([^"|]+)', x) if not os.path.exists(os.path.join(H, s))})
for s in missing: print("нет файла на этом компьютере (оставлен):", s)
data[qgs] = x.encode("utf-8")
tmp = QGZ + ".tmp"
with zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as z:
    for n in names: z.writestr(n, data[n])
shutil.move(tmp, QGZ); print("сохранено:", QGZ)
