# Библиотека разметки слайдов 1920x1080: примитивы (rect/text/img/path/arc/line), фирменные элементы (шапка, мазок кисти,
# знак севера, масштабная линейка, легенды-мазки), графики. Одна разметка -> HTML (PDF/PNG) и код Figma.
import math, random, re, json, os
from PIL import ImageFont

H = os.path.dirname(os.path.abspath(__file__))
FONTDIR = os.path.join(H, "..", "design", "san-francisco-pro-display")
FONTS = {w: os.path.join(FONTDIR, f"SF-Pro-Display-{w}.otf") for w in ("Regular", "Medium", "Semibold", "Bold", "Light")}
C = dict(pink="#DA71D7", pinkl="#F3D7F2", pinkd="#B04FAD", dark="#14131A", dark2="#1F1E26", cream="#F4F3EA", paper="#F9F3E7",
         white="#FFFFFF", grey="#8C8A93", mid="#56545E", line="#DAD6CB", green="#5EC46E", yellow="#D9C35B", red="#B13840",
         purple="#6852A0", blue="#94ACD6", teal="#8BB0B0", orange="#E08A2B", beige="#E6D9C2")
_fc = {}
def font(w, s):
    k = (w, int(round(s * 4)))
    if k not in _fc: _fc[k] = ImageFont.truetype(FONTS[w], max(1, int(round(s * 4))))
    return _fc[k]
def tw(text, size, w="Regular"):
    return font(w, size).getlength(text) / 4.0
NB = re.compile(r"(?<=\d) (?=%|м\b|м²|га\b|км\b|мин\b|\d{3}\b)|(?<=№) ")
PREP = re.compile(r"(^|[\s(«])(до|от|в|во|на|и|с|к|у|по|за|не|из|о|а|но|без|под|над|при|для|через) ", re.I)   # предлоги — к следующему слову
def wrap(text, size, w, width):
    lines = []
    for para in str(text).split("\n"):
        cur = ""
        for word in para.split(" "):
            t = (cur + " " + word).strip()
            if tw(t, size, w) <= width or not cur: cur = t
            else: lines.append(cur); cur = word
        lines.append(cur)
    return lines
def fmt(n, d=0):
    s = f"{n:,.{d}f}".replace(",", " ").replace(".", ",")
    return s

class Slide:
    def __init__(self, bg=C["cream"], name=""):
        self.bg = bg; self.els = []; self.name = name
    def add(self, **e): self.els.append(e); return e
    def rect(self, x, y, w, h, fill, op=1.0, r=0, stroke=None, sw=0, dash=False):
        return self.add(t="rect", x=x, y=y, w=w, h=h, fill=fill, op=op, r=r, stroke=stroke, sw=sw, dash=dash)
    def text(self, x, y, w, txt, size=24, wt="Regular", color=C["dark"], lh=1.25, align="left", op=1.0, ls=0):
        txt = NB.sub("\u00a0", str(txt))
        for _ in range(2): txt = PREP.sub(lambda m: m.group(1) + m.group(2) + "\u00a0", txt)
        txt = txt.replace(" —", "\u00a0—")     # неразрывные пробелы: «3 %», «605 м», «№ 2», «76 413»
        lines = wrap(txt, size, wt, w)
        e = self.add(t="text", x=x, y=y, w=w, txt=str(txt), size=size, wt=wt, color=color, lh=lh, align=align, op=op, ls=ls)
        e["h"] = round(len(lines) * size * lh); e["nl"] = len(lines); return e
    def img(self, x, y, w, h, src, fit="cover", circle=False, op=1.0):
        return self.add(t="img", x=x, y=y, w=w, h=h, src=src, fit=fit, circle=circle, op=op)
    def path(self, x, y, w, h, d, fill=None, stroke=None, sw=0, op=1.0, dash=False):
        return self.add(t="path", x=x, y=y, w=w, h=h, d=d, fill=fill, stroke=stroke, sw=sw, op=op, dash=dash)
    def line(self, x1, y1, x2, y2, stroke, sw=2, dash=False, op=1.0):
        return self.add(t="line", x1=x1, y1=y1, x2=x2, y2=y2, stroke=stroke, sw=sw, dash=dash, op=op)
    def arc(self, cx, cy, r, ir, a0, a1, fill, op=1.0):
        return self.add(t="arc", cx=cx, cy=cy, r=r, ir=ir, a0=a0, a1=a1, fill=fill, op=op)
    def ellipse(self, x, y, w, h, fill, op=1.0, stroke=None, sw=0):
        return self.add(t="ellipse", x=x, y=y, w=w, h=h, fill=fill, op=op, stroke=stroke, sw=sw)

# ---------------- фирменные элементы
def brush_d(w, h, seed=1, taper=0.12):
    """Мазок кисти: залитый контур с рваными краями (координаты от 0,0)."""
    rnd = random.Random(seed); n = 28
    top, bot = [], []
    for i in range(n + 1):
        t = i / n; x = t * w
        env = min(1, t / taper, (1 - t) / taper) if taper else 1
        env = max(0.25, env)
        mid = h / 2 + math.sin(t * math.pi * 1.3 + seed) * h * 0.06
        top.append((x, mid - h / 2 * env + rnd.uniform(-0.08, 0.1) * h))
        bot.append((x, mid + h / 2 * env + rnd.uniform(-0.1, 0.08) * h))
    pts = top + bot[::-1]
    d = "M" + " L".join(f"{p[0]:.1f} {max(0, min(h, p[1])):.1f}" for p in pts) + " Z"
    # «сухие» прожилки
    for k in range(3):
        y0 = h * (0.25 + 0.25 * k) + rnd.uniform(-2, 2); x0 = w * rnd.uniform(0.0, 0.2); x1 = w * rnd.uniform(0.75, 1.0); th = max(1.0, h * 0.05)
        d += f" M{x0:.1f} {y0:.1f} L{x1:.1f} {y0 + rnd.uniform(-2, 2):.1f} L{x1:.1f} {y0 + th:.1f} L{x0:.1f} {y0 + th:.1f} Z"
    return d

def brush(s, x, y, w, h, color=C["pink"], op=0.55, seed=1):
    return s.path(x, y, w, h, brush_d(w, h, seed), fill=color, op=op)

def title(s, x, y, txt, size=72, color=C["dark"], w=1100, brush_color=C["pink"], brush_op=0.5, seed=3, wt="Semibold", brush_line=0):
    lines = wrap(txt, size, wt, w)
    if brush_color is not None and brush_line < len(lines):
        lw = tw(lines[brush_line], size, wt)
        brush(s, x - 18, y + size * 1.05 * brush_line + size * 0.28, lw + 46, size * 0.62, brush_color, brush_op, seed)
    return s.text(x, y, w, txt, size, wt, color, lh=1.05)

def header(s, n, colors=None, left="Средовой анализ придомовых территорий жилой застройки"):
    cols = colors or [C["dark"]] * 4
    s.text(40, 26, 760, left, 17, "Medium", cols[0])
    s.text(960, 26, 300, "Команда 2", 17, "Medium", cols[1])
    s.text(1290, 26, 300, "Москва 2026", 17, "Medium", cols[2])
    s.text(1680, 26, 200, f"сл. {n}", 17, "Medium", cols[3], align="right")

NORTH = [("M50 0 C60 28 86 48 100 96 C84 70 68 56 50 52 C32 56 16 70 0 96 C14 48 40 28 50 0 Z", "pink"),
         ("M24 82 L36 82 L64 124 L64 82 L76 82 L76 146 L64 146 L36 104 L36 146 L24 146 Z", "dark")]
def _xform(d, f):
    toks = re.findall(r"[MLCZ]|-?\d+\.?\d*", d); out = []; i = 0
    while i < len(toks):
        t = toks[i]
        if t in "MLCZ": out.append(t); i += 1; continue
        x, y = f(float(toks[i]), float(toks[i + 1])); out.append(f"{x:.2f} {y:.2f}"); i += 2
    return " ".join(out)
def north(s, x, y, size=70, rot=-26.75, ncolor=C["dark"]):
    """Фирменный знак севера (розовый наконечник + N), повёрнут вместе с картой."""
    k = size / 150.0; a = math.radians(rot); cx, cy = 50, 75
    pts = []
    def f(px, py):
        dx, dy = (px - cx) * k, (py - cy) * k
        return dx * math.cos(a) - dy * math.sin(a), dx * math.sin(a) + dy * math.cos(a)
    ds = [(_xform(d, f), col) for d, col in NORTH]
    allp = [tuple(map(float, m)) for d, _ in ds for m in re.findall(r"(-?\d+\.?\d*) (-?\d+\.?\d*)", d)]
    mx, my = min(p[0] for p in allp), min(p[1] for p in allp); Mx, My = max(p[0] for p in allp), max(p[1] for p in allp)
    for d, col in ds:
        d2 = _xform(d, lambda px, py: (px - mx, py - my))
        s.path(x, y, Mx - mx, My - my, d2, fill=C["pink"] if col == "pink" else ncolor)

def scalebar(s, x, y, mpp, color=C["dark"], step=100, n=2):
    L = step / mpp
    for i in range(n):
        s.rect(x + i * L, y, L, 8, color if i % 2 == 0 else C["white"], stroke=color, sw=1.5)
    for i in range(n + 1):
        s.text(x + i * L - 40, y - 30, 80, f"{i * step}" + (" м" if i == n else ""), 18, "Medium", color, align="center")

SHAPES = {"square": [(0, 0), (1, 0), (1, 1), (0, 1)], "diamond": [(.5, 0), (1, .5), (.5, 1), (0, .5)],
          "triangle": [(.5, 0), (1, 1), (0, 1)], "pentagon": [(.5, 0), (1, .38), (.81, 1), (.19, 1), (0, .38)],
          "hexagon": [(.25, 0), (.75, 0), (1, .5), (.75, 1), (.25, 1), (0, .5)],
          "octagon": [(.3, 0), (.7, 0), (1, .3), (1, .7), (.7, 1), (.3, 1), (0, .7), (0, .3)],
          "cross_fill": [(.35, 0), (.65, 0), (.65, .35), (1, .35), (1, .65), (.65, .65), (.65, 1), (.35, 1), (.35, .65), (0, .65), (0, .35), (.35, .35)]}
def shape_icon(s, x, y, shape, fill, size=20):
    if shape == "circle" or shape not in SHAPES: return s.ellipse(x, y, size, size, fill)
    d = "M" + " L".join(f"{px * size:.1f} {py * size:.1f}" for px, py in SHAPES[shape]) + " Z"
    return s.path(x, y, size, size, d, fill=fill)
def legend_icon(s, x, y, sym, seed=1, w=44, h=22, dark=False):
    fix = lambda c: "#B9B4AA" if dark and c and lum(c) < 0.25 else c      # почти чёрное на тёмной плашке - светло-серым
    k = sym.get("kind")
    if k == "marker" and sym.get("shape", "circle") != "circle" and sym.get("fill", "").lower() in ("#8b877f", "#16161c", "#d62828", "#2a9d4b"):
        shape_icon(s, x + 12, y + 1, sym["shape"], fix(sym["fill"])); return
    if k == "line":
        sw = max(2.5, min(8, sym.get("sw", 0.4) * 5)); s.line(x + 2, y + h / 2, x + w - 2, y + h / 2, fix(sym.get("stroke", "#333")), sw, sym.get("dash", False), sym.get("sa", 1))
        return
    col = sym.get("fill", "#ccc"); op = sym.get("fa", 1)
    if (op or 0) < 0.15:                     # только контур - рамка цвета контура
        s.rect(x + 2, y + 2, w - 4, h - 4, "transparent", stroke=fix(sym.get("stroke", col)), sw=2.5, dash=sym.get("dash", False)); return
    if sym.get("hatch"): op = min(op, 0.55)
    brush(s, x, y, w, h, fix(col), max(0.7 if dark and fix(col) != col else 0.35, op), seed)

SKIP_ALWAYS = {"Озеленение", "Номера", "Номер и балл", "Номер / счёт", "Номера ячеек анализа"}
def legend(s, x, y, groups, w=420, color=C["dark"], size=19, skip=(), titles=True, col_gap=30, max_h=None, cols=1, keep=(), short=None, row=26, gap=8):
    """Легенда: мазки кисти + подписи. groups из maps.json. Возвращает высоту."""
    items = []
    SKIP_ITEMS = {"нет фасадов", "без данных"}
    for g in groups:
        single = len(g["items"]) == 1 and g["items"][0]["label"] == g["title"]
        if g["title"] in skip and g["title"] not in keep and (single or g["title"] in SKIP_ALWAYS): continue
        g = dict(g, items=[i for i in g["items"] if i["label"] not in SKIP_ITEMS])
        if titles and len(g["items"]) > 1: items.append(("title", g["title"]))
        for it in g["items"]: items.append(("item", dict(it, label=(short or {}).get(it["label"], it["label"]))))
    if short: items.sort(key=lambda k: k[1]["label"] if k[0] == "item" else "")
    cw = (w - col_gap * (cols - 1)) / cols; per = math.ceil(len(items) / cols); yy = y; col = 0; seed = 1; hmax = 0
    for i, (kind, it) in enumerate(items):
        if i and i % per == 0 and cols > 1: col += 1; hmax = max(hmax, yy - y); yy = y
        xx = x + col * (cw + col_gap)
        if kind == "title":
            e = s.text(xx, yy + 4, cw, it, size - 3, "Semibold", color, op=0.6); yy += e["h"] + 6
        else:
            legend_icon(s, xx, yy + 2, it["sym"], seed, dark=lum(color) > 0.5); seed += 1
            e = s.text(xx + 58, yy, cw - 58, it["label"], size, "Regular", color, lh=1.15); yy += max(e["h"], row) + gap
    return max(hmax, yy - y)

# ---------------- графики (нативные примитивы)
def hbar(s, x, y, w, rows, colors, maxv=None, bar_h=26, gap=16, label_w=250, size=20, color=C["dark"], fmtv=lambda v: fmt(v), stacked=True):
    """rows: [(label, [v1, v2, ...])] — горизонтальные (составные) столбцы."""
    maxv = maxv or max(sum(v) for _, v in rows); yy = y; bw = w - label_w - (180 if len(rows[0][1]) > 1 else 90)
    for lab, vals in rows:
        s.text(x, yy + (bar_h - size * 1.2) / 2, label_w - 12, lab, size, "Regular", color)
        xx = x + label_w
        for v, c in zip(vals, colors):
            L = bw * v / maxv if maxv else 0
            if L > 0: s.rect(xx, yy, L, bar_h, c, r=0)
            xx += L
        s.text(xx + 10, yy + (bar_h - size * 1.2) / 2, 260, " / ".join(fmtv(v) for v in vals) if len(vals) > 1 else fmtv(vals[0]), size, "Semibold", color)
        yy += bar_h + gap
    return yy - y

def donut(s, cx, cy, r, ir, vals, colors, start=-90):
    tot = sum(vals); a = math.radians(start)
    for v, c in zip(vals, colors):
        a1 = a + 2 * math.pi * v / tot; s.arc(cx, cy, r, ir, a, a1 - 0.012, c); a = a1

def bignum(s, x, y, num, cap, color=C["dark"], ncolor=None, size=96, w=380, cap_size=22, brush_c=None, seed=5):
    if brush_c: brush(s, x - 10, y + size * 0.35, tw(num, size, "Semibold") + 30, size * 0.55, brush_c, 0.5, seed)
    s.text(x, y, w, num, size, "Semibold", ncolor or color, lh=1.0)
    e = s.text(x, y + size * 1.02, w, cap, cap_size, "Regular", color, lh=1.2)
    return size * 1.02 + e["h"]

# ======================= v2: сетка, шапка/подвал как в «Митино», заглушки фото, проверка наложений
PAD = 24                       # внутренний отступ модуля (как в исходной презентации)
T = dict(h1=88, h2=64, h3=40, num=96, body=28, small=22, cap=20)     # шкала кеглей
def lum(hexc):
    h = hexc.lstrip("#"); r, g, b = (int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)); return 0.2126 * r + 0.7152 * g + 0.0722 * b
def bg_at(s, x, y):
    """Цвет фона в точке: последний перекрывающий rect/img (img карты/фото считаем светлыми, кроме заглушек)."""
    col = s.bg
    for e in s.els:
        if e["t"] in ("rect", "img") and e["x"] <= x <= e["x"] + e["w"] and e["y"] <= y <= e["y"] + e["h"]:
            if e["t"] == "rect" and e.get("op", 1) > 0.6 and e["fill"].startswith("#"): col = e["fill"]
            elif e["t"] == "img": col = e.get("tone", "#F9F3E7")
    return col
def ink(s, x, y): return C["dark"] if lum(bg_at(s, x, y)) > 0.5 else C["white"]
def chrome(s, n, mid="Модуль 1 · занятие 4"):
    """Шапка и подвал (кегль 20, колонки 24 / 960 / 1282 / справа) — цвет по фону под текстом."""
    for x, t, al in ((24, "Средовой анализ придомовых территорий жилой застройки", "left"), (960, "Команда 2", "left"), (1282, "Москва 2026", "left")):
        s.text(x, 14, 640 if x == 24 else 300, t, 20, "Regular", ink(s, x + 4, 24), align=al)
    for x, t, al, w in ((24, "Проектный семинар", "left", 600), (1282, mid, "left", 400), (1576, f"сл. {n}", "right", 320)):
        s.text(x, 1040, w, t, 20, "Regular", ink(s, x + (w - 4 if al == "right" else 4), 1052), align=al)
def photo(s, x, y, w, h, label, circle=False, dark=False):
    fill = "#2A2930" if dark else "#DCD6CA"; fg = C["grey"] if dark else C["mid"]
    if circle: e = s.ellipse(x, y, w, h, fill)
    else: e = s.rect(x, y, w, h, fill)
    e["name"] = "ФОТО: " + label; e["photo"] = True
    s.path(x + w / 2 - 22, y + h / 2 - 46, 44, 32, "M0 8 L12 8 L16 0 L28 0 L32 8 L44 8 L44 32 L0 32 Z M22 10 A8 8 0 1 0 22.01 10 Z", fill=fg, op=0.6)
    s.text(x + PAD, y + h / 2 - 2, w - 2 * PAD, "фото: " + label, 20, "Medium", fg, align="center", lh=1.2)
    return e
def text_box(e):
    lines = wrap(e["txt"], e["size"], e["wt"], e["w"])
    wmax = max(tw(l, e["size"], e["wt"]) for l in lines) if lines else 0
    x = e["x"] if e["align"] == "left" else (e["x"] + e["w"] - wmax if e["align"] == "right" else e["x"] + (e["w"] - wmax) / 2)
    return x, e["y"], wmax, len(lines) * e["size"] * e["lh"]
def check(deck_slides):
    """Наложения текст/текст, выход за край слайда, текст на карте без подложки."""
    issues = []
    for i, s in enumerate(deck_slides, 1):
        texts = [e for e in s.els if e["t"] == "text" and e["txt"].strip() and e.get("op", 1) >= 0.3]   # водяные номера не считаем
        boxes = [(e, text_box(e)) for e in texts]
        for a in range(len(boxes)):
            ea, (x1, y1, w1, h1) = boxes[a]
            if x1 < 0 or y1 < 0 or x1 + w1 > 1920.5 or y1 + h1 > 1080.5: issues.append((i, "за краем", ea["txt"][:40]))
            for b in range(a + 1, len(boxes)):
                eb, (x2, y2, w2, h2) = boxes[b]
                ox = min(x1 + w1, x2 + w2) - max(x1, x2); oy = min(y1 + h1, y2 + h2) - max(y1, y2)
                if ox > 2 and oy > 2: issues.append((i, "наложение", ea["txt"][:30] + " | " + eb["txt"][:30]))
    return issues
