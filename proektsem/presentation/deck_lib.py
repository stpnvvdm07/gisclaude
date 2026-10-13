# Библиотека разметки слайдов 1920x1080 (v3): примитивы (rect/text/img/path/line/ellipse/arc), фирменные элементы команды
# (мазки из design/brush, знак севера, масштабная линейка, легенды), шапка/подвал как в презентациях «Торжок» и «Красная Пресня».
# Одна разметка -> HTML (PDF/PNG) и код Figma.
import math, re, json, os
from PIL import Image, ImageFont

H = os.path.dirname(os.path.abspath(__file__))
FONTDIR = os.path.join(H, "..", "design", "san-francisco-pro-display")
FONTS = {w: os.path.join(FONTDIR, f"SF-Pro-Display-{w}.otf") for w in ("Regular", "Medium", "Semibold", "Bold", "Light")}
# Четыре цвета команды + служебные серые. Тематические цвета — только внутри карт и их легенд.
C = dict(dark="#14131A", pink="#DA71D7", cream="#F4F3EA", white="#FFFFFF",
         grey="#D9D9D9", row="#F2F2F2", line="#DADADA", mid="#6E6C75", soft="#A9A7AF", light="#E4E3E8",
         wm_w="#F0F0F0", wm_g="#E6E6E6", wm_d="#25242D", dark2="#22212A")
PAD = 24
_fc = {}
def font(w, s):
    k = (w, int(round(s * 4)))
    if k not in _fc: _fc[k] = ImageFont.truetype(FONTS[w], max(1, int(round(s * 4))))
    return _fc[k]
def tw(text, size, w="Regular"):
    return font(w, size).getlength(text) / 4.0
NB = re.compile(r"(?<=\d) (?=%|м\b|м²|га\b|км\b|мин\b|чел\b|\d{3}\b)|(?<=№) ")
PREP = re.compile(r"(^|[\s(«])(до|от|в|во|на|и|с|к|у|по|за|не|из|о|а|но|без|под|над|при|для|что|как|или) ", re.I)   # короткие слова к следующему
def typo(txt):
    txt = NB.sub(" ", str(txt))
    for _ in range(2): txt = PREP.sub(lambda m: m.group(1) + m.group(2) + " ", txt)
    return txt.replace(" —", " —")
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
    return f"{n:,.{d}f}".replace(",", " ").replace(".", ",")
def lum(hexc):
    h = hexc.lstrip("#"); r, g, b = (int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)); return 0.2126 * r + 0.7152 * g + 0.0722 * b

class Slide:
    def __init__(self, bg=C["white"], name=""):
        self.bg = bg; self.els = []; self.name = name
    def add(self, **e): self.els.append(e); return e
    def rect(self, x, y, w, h, fill, op=1.0, r=0, stroke=None, sw=0, dash=False):
        return self.add(t="rect", x=x, y=y, w=w, h=h, fill=fill, op=op, r=r, stroke=stroke, sw=sw, dash=dash)
    def text(self, x, y, w, txt, size=26, wt="Regular", color=C["dark"], lh=1.12, align="left", op=1.0, ls=0, wm=False, rot=0):
        txt = typo(txt); lines = wrap(txt, size, wt, w)
        e = self.add(t="text", x=x, y=y, w=w, txt=txt, size=size, wt=wt, color=color, lh=lh, align=align, op=op, ls=ls, rot=rot)
        if wm: e["wm"] = True
        e["h"] = round(len(lines) * size * lh); e["nl"] = len(lines)
        e["tw"] = max((tw(l, size, wt) for l in lines), default=0); return e
    def img(self, x, y, w, h, src, fit="cover", circle=False, op=1.0, tone=None):
        e = self.add(t="img", x=x, y=y, w=w, h=h, src=src, fit=fit, circle=circle, op=op)
        if tone: e["tone"] = tone
        return e
    def path(self, x, y, w, h, d, fill=None, stroke=None, sw=0, op=1.0, dash=False):
        return self.add(t="path", x=x, y=y, w=w, h=h, d=d, fill=fill, stroke=stroke, sw=sw, op=op, dash=dash)
    def line(self, x1, y1, x2, y2, stroke, sw=2, dash=False, op=1.0):
        return self.add(t="line", x1=x1, y1=y1, x2=x2, y2=y2, stroke=stroke, sw=sw, dash=dash, op=op)
    def arc(self, cx, cy, r, ir, a0, a1, fill, op=1.0):
        return self.add(t="arc", cx=cx, cy=cy, r=r, ir=ir, a0=a0, a1=a1, fill=fill, op=op)
    def ellipse(self, x, y, w, h, fill, op=1.0, stroke=None, sw=0):
        return self.add(t="ellipse", x=x, y=y, w=w, h=h, fill=fill, op=op, stroke=stroke, sw=sw)

# ---------------- мазки: присланные элементы design/brush/1..5.png (белые на прозрачном), перекрашиваются в нужный цвет
BR_SRC = os.path.join(H, "..", "design", "brush")
BR_OUT = os.path.join(H, "assets", "brush")
def brush_src(k, color):
    os.makedirs(BR_OUT, exist_ok=True)
    fn = os.path.join(BR_OUT, f"b{k}_{color.lstrip('#').lower()}.png")
    if not os.path.exists(fn):
        a = Image.open(os.path.join(BR_SRC, f"{k}.png")).convert("RGBA").getchannel("A")
        h = color.lstrip("#"); rgb = tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))
        im = Image.new("RGBA", a.size, rgb + (0,)); im.putalpha(a); im.save(fn)
    return os.path.relpath(fn, H)
def brush(s, x, y, w, h, color=C["pink"], k=2, op=1.0):
    """k: 1 — каракуля, 2 — длинный мазок, 3 — волна, 4/5 — короткие мазки (значки легенды)."""
    return s.img(x, y, w, h, brush_src(k, color), fit="fill", op=op)
def under(s, e, color=C["pink"], k=2, op=0.85, line=0, pad=(14, 22), hk=0.62):
    """Мазок под строкой текста e (как в «Митино»/«Торжке»): по ширине строки, по нижним 2/3 кегля."""
    lines = wrap(e["txt"], e["size"], e["wt"], e["w"]); L = lines[min(line, len(lines) - 1)]
    w = tw(L, e["size"], e["wt"]); y = e["y"] + e["size"] * e["lh"] * line + e["size"] * (1.0 - hk) * 0.9
    x = e["x"] + {"left": 0, "right": e["w"] - w, "center": (e["w"] - w) / 2}[e["align"]]
    el = brush(s, x - pad[0], y, w + pad[0] + pad[1], e["size"] * hk, color, k, op)
    s.els.remove(el); s.els.insert(s.els.index(e), el); return el

# ---------------- знак севера (как Frame 667 команды), масштабная линейка
NORTH = [("M50 0 C60 28 86 48 100 96 C84 70 68 56 50 52 C32 56 16 70 0 96 C14 48 40 28 50 0 Z", "pink"),
         ("M24 82 L36 82 L64 124 L64 82 L76 82 L76 146 L64 146 L36 104 L36 146 L24 146 Z", "dark")]
def _xform(d, f):
    toks = re.findall(r"[MLCZ]|-?\d+\.?\d*", d); out = []; i = 0
    while i < len(toks):
        t = toks[i]
        if t in "MLCZ": out.append(t); i += 1; continue
        x, y = f(float(toks[i]), float(toks[i + 1])); out.append(f"{x:.2f} {y:.2f}"); i += 2
    return " ".join(out)
def north(s, x, y, size=72, rot=-26.75, ncolor=C["dark"]):
    k = size / 150.0; a = math.radians(rot); cx, cy = 50, 75
    def f(px, py):
        dx, dy = (px - cx) * k, (py - cy) * k
        return dx * math.cos(a) - dy * math.sin(a), dx * math.sin(a) + dy * math.cos(a)
    ds = [(_xform(d, f), col) for d, col in NORTH]
    allp = [tuple(map(float, m)) for d, _ in ds for m in re.findall(r"(-?\d+\.?\d*) (-?\d+\.?\d*)", d)]
    mx, my = min(p[0] for p in allp), min(p[1] for p in allp); Mx, My = max(p[0] for p in allp), max(p[1] for p in allp)
    for d, col in ds:
        s.path(x, y, Mx - mx, My - my, _xform(d, lambda px, py: (px - mx, py - my)), fill=C["pink"] if col == "pink" else ncolor)
def scalebar(s, x, y, mpp, color=C["dark"], step=100, n=2, size=22):
    """Как на картах команды: чёрный и белый отрезки, подписи над ними."""
    L = step / mpp
    for i in range(n): s.rect(x + i * L, y, L, 6, color if i % 2 == 0 else C["white"], stroke=color, sw=1.5)
    for i in range(n + 1):
        s.text(x + i * L - 40, y - size * 1.35, 80, f"{i * step}" + (" м" if i == n else ""), size, "Regular", color, align="center")

# ---------------- значки легенды
SHAPES = {"square": [(0, 0), (1, 0), (1, 1), (0, 1)], "diamond": [(.5, 0), (1, .5), (.5, 1), (0, .5)],
          "triangle": [(.5, 0), (1, 1), (0, 1)], "pentagon": [(.5, 0), (1, .38), (.81, 1), (.19, 1), (0, .38)],
          "hexagon": [(.25, 0), (.75, 0), (1, .5), (.75, 1), (.25, 1), (0, .5)],
          "octagon": [(.3, 0), (.7, 0), (1, .3), (1, .7), (.7, 1), (.3, 1), (0, .7), (0, .3)],
          "cross_fill": [(.35, 0), (.65, 0), (.65, .35), (1, .35), (1, .65), (.65, .65), (.65, 1), (.35, 1), (.35, .65), (0, .65), (0, .35), (.35, .35)]}
def shape_icon(s, x, y, shape, fill, size=22):
    if shape == "circle" or shape not in SHAPES: return s.ellipse(x, y, size, size, fill)
    d = "M" + " L".join(f"{px * size:.1f} {py * size:.1f}" for px, py in SHAPES[shape]) + " Z"
    return s.path(x, y, size, size, d, fill=fill)
def legend_icon(s, x, y, sym, k=4, w=48, h=28, dark=False):
    fix = lambda c: "#B9B4AA" if dark and c and lum(c) < 0.25 else c
    kind = sym.get("kind")
    if kind == "marker":
        sh = sym.get("shape", "circle"); return shape_icon(s, x + 12, y + 3, sh, fix(sym.get("fill", "#333")), 22)
    if kind == "line":
        sw = max(3, min(8, sym.get("sw", 0.4) * 5))
        return s.line(x + 2, y + h / 2, x + w - 2, y + h / 2, fix(sym.get("stroke", "#333")), sw, sym.get("dash", False), sym.get("sa", 1))
    col = sym.get("fill", "#ccc"); op = sym.get("fa", 1) or 0
    if op < 0.15:
        return s.rect(x + 3, y + 3, w - 6, h - 6, "transparent", stroke=fix(sym.get("stroke", col)), sw=3, dash=sym.get("dash", False))
    if sym.get("hatch"): op = min(op, 0.6)
    return brush(s, x, y, w, h, fix(col), k, max(0.75 if dark else 0.45, op))

SKIP = {"Здания", "Ячейки", "Граница территории", "Ячейка анализа", "Застройка вне территории", "Озеленение", "Границы ячеек",
        "Номера", "Номер и балл", "Номер / счёт", "Номера ячеек анализа", "Номера ячеек"}
def legend_items(groups, skip=SKIP, keep=(), rename=None, drop=()):
    out = []
    for g in groups:
        if g["title"] in skip and g["title"] not in keep: continue
        for it in g["items"]:
            lab = (rename or {}).get(it["label"], it["label"])
            if lab in drop or it["label"] in drop: continue
            out.append(dict(label=lab, sym=it["sym"]))
    return out
def legend(s, x, y, items, w, color=C["dark"], size=24, cols=1, gap=24, row=34):
    """items: [{label, sym, (count)}]. Возвращает высоту."""
    dark = lum(color) > 0.5; cw = (w - gap * (cols - 1)) / cols; per = math.ceil(len(items) / cols)
    yy = y; hmax = 0
    for i, it in enumerate(items):
        if i and i % per == 0: hmax = max(hmax, yy - y); yy = y
        xx = x + (i // per) * (cw + gap)
        legend_icon(s, xx, yy + (size * 1.2 - 28) / 2 + 1, it["sym"], 4 + i % 2, dark=dark)
        rw = 0
        if it.get("count") is not None:
            s.text(xx + cw - 90, yy, 90, str(it["count"]), size, "Semibold", color, align="right"); rw = 100
        e = s.text(xx + 64, yy, cw - 64 - rw, it["label"], size, "Regular", color, lh=1.1)
        yy += max(e["h"], row - 8) + 8
    return max(hmax, yy - y)

# ---------------- шапка и подвал (как в «Торжке»/«Красной Пресне», колонки 24 / 960 / 1282 / справа)
def bg_at(s, x, y):
    col = s.bg
    for e in s.els:
        if e["t"] in ("rect", "img") and e["x"] <= x <= e["x"] + e["w"] and e["y"] <= y <= e["y"] + e["h"]:
            if e["t"] == "rect" and e.get("op", 1) > 0.6 and str(e["fill"]).startswith("#"): col = e["fill"]
            elif e["t"] == "img" and "brush" not in e["src"]: col = e.get("tone", "#F9F3E7")
    return col
def ink(s, x, y): return C["dark"] if lum(bg_at(s, x, y)) > 0.45 else C["white"]
TITLE = "Средовой анализ придомовых территорий жилой застройки"
def chrome(s, n, section="", footer=True, left=True):
    for x, t, w in ((PAD, TITLE, 900), (960, "Команда 2", 300), (1282, "Москва 2026", 300)):
        if x == PAD and not left: continue
        s.text(x, 14, w, t, 20, "Regular", ink(s, x + 4, 24))
    if section: s.text(1596, 14, 300, section, 20, "Regular", ink(s, 1890, 24), align="right")
    if footer:
        for x, t, w, al in ((PAD, "Проектный семинар · модуль 1", 600, "left"), (1282, "Занятие 4", 300, "left"),
                            (1696, f"сл.{n}", 200, "right")):
            s.text(x, 1046, w, t, 20, "Regular", ink(s, x + (w - 6 if al == "right" else 4), 1056), align=al)

def photo(s, x, y, w, h, label, circle=False):
    """Место под фото (как «место для карт» в шаблоне команды): серая плашка с подписью."""
    e = s.ellipse(x, y, w, h, C["grey"]) if circle else s.rect(x, y, w, h, C["grey"])
    e["name"] = "ФОТО: " + label; e["photo"] = True
    s.text(x + PAD, y + h / 2 - 16, w - 2 * PAD, "фото: " + label, 26, "Medium", C["dark"], align="center", lh=1.15)
    return e

# ---------------- графики
def donut(s, cx, cy, r, ir, vals, colors, start=-90):
    tot = sum(vals); a = math.radians(start)
    for v, c in zip(vals, colors):
        a1 = a + 2 * math.pi * v / tot; s.arc(cx, cy, r, ir, a, a1 - 0.012, c); a = a1

# ---------------- проверка
def text_box(e):
    lines = wrap(e["txt"], e["size"], e["wt"], e["w"])
    wmax = max(tw(l, e["size"], e["wt"]) for l in lines) if lines else 0
    x = e["x"] if e["align"] == "left" else (e["x"] + e["w"] - wmax if e["align"] == "right" else e["x"] + (e["w"] - wmax) / 2)
    if e.get("rot"): return e["x"], e["y"] - wmax, len(lines) * e["size"] * e["lh"], wmax
    return x, e["y"], wmax, len(lines) * e["size"] * e["lh"]
def check(deck_slides):
    """Наложения текста, выход текста за край слайда и слова шире своей рамки."""
    issues = []
    for i, s in enumerate(deck_slides, 1):
        texts = [e for e in s.els if e["t"] == "text" and e["txt"].strip() and not e.get("wm")]
        boxes = [(e, text_box(e)) for e in texts]
        for a in range(len(boxes)):
            ea, (x1, y1, w1, h1) = boxes[a]
            if x1 < -0.5 or y1 < -0.5 or x1 + w1 > 1920.5 or y1 + h1 > 1080.5: issues.append((i, "за краем", ea["txt"][:40]))
            if not ea.get("rot") and any(tw(w_, ea["size"], ea["wt"]) > ea["w"] + 1 for w_ in ea["txt"].replace("\n", " ").split(" ")):
                issues.append((i, "слово шире рамки", ea["txt"][:40]))
            for b in range(a + 1, len(boxes)):
                eb, (x2, y2, w2, h2) = boxes[b]
                ox = min(x1 + w1, x2 + w2) - max(x1, x2); oy = min(y1 + h1, y2 + h2) - max(y1, y2)
                if ox > 2 and oy > 2: issues.append((i, "наложение", ea["txt"][:30] + " | " + eb["txt"][:30]))
    return issues
