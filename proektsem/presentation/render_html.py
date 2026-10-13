# Разметка слайдов (deck.json) -> deck.html (1920x1080 на слайд). Экспорт PDF/PNG - export.py (Chromium).
import json, math, os, html
H = os.path.dirname(os.path.abspath(__file__))
W8 = {"Light": 300, "Regular": 400, "Medium": 500, "Semibold": 600, "Bold": 700}

def arc_d(cx, cy, r, ir, a0, a1):
    large = 1 if (a1 - a0) > math.pi else 0
    p = lambda a, rr: (cx + rr * math.cos(a), cy + rr * math.sin(a))
    (x0, y0), (x1, y1) = p(a0, r), p(a1, r)
    if ir <= 0: return f"M{cx} {cy} L{x0:.2f} {y0:.2f} A{r} {r} 0 {large} 1 {x1:.2f} {y1:.2f} Z"
    (u0, v0), (u1, v1) = p(a1, ir), p(a0, ir)
    return f"M{x0:.2f} {y0:.2f} A{r} {r} 0 {large} 1 {x1:.2f} {y1:.2f} L{u0:.2f} {v0:.2f} A{ir} {ir} 0 {large} 0 {u1:.2f} {v1:.2f} Z"

def el_html(e):
    t = e["t"]; op = e.get("op", 1)
    if t == "rect":
        b = f"border:{e['sw']}px {'dashed' if e.get('dash') else 'solid'} {e['stroke']};box-sizing:border-box;" if e.get("stroke") else ""
        return f'<div style="position:absolute;left:{e["x"]}px;top:{e["y"]}px;width:{e["w"]}px;height:{e["h"]}px;background:{e["fill"]};opacity:{op};border-radius:{e.get("r",0)}px;{b}"></div>'
    if t == "ellipse":
        b = f"border:{e['sw']}px solid {e['stroke']};box-sizing:border-box;" if e.get("stroke") else ""
        return f'<div style="position:absolute;left:{e["x"]}px;top:{e["y"]}px;width:{e["w"]}px;height:{e["h"]}px;background:{e["fill"] or "transparent"};opacity:{op};border-radius:50%;{b}"></div>'
    if t == "text":
        rot = f'transform-origin:0 0;transform:rotate({e["rot"]}deg);white-space:nowrap;' if e.get("rot") else ""
        return (f'<div style="position:absolute;left:{e["x"]}px;top:{e["y"]}px;width:{e["w"]}px;font-size:{e["size"]}px;'
                f'font-weight:{W8[e["wt"]]};color:{e["color"]};line-height:{e["size"]*e["lh"]:.1f}px;text-align:{e["align"]};opacity:{op};'
                f'letter-spacing:{e.get("ls",0)}px;white-space:pre-wrap;{rot}">{html.escape(e["txt"])}</div>')
    if t == "img":
        r = "border-radius:50%;" if e.get("circle") else ""
        return f'<img src="{e["src"]}" style="position:absolute;left:{e["x"]}px;top:{e["y"]}px;width:{e["w"]}px;height:{e["h"]}px;object-fit:{e["fit"]};{r}opacity:{op};">'
    if t == "path":
        f = e["fill"] or "none"; st = f'stroke="{e["stroke"]}" stroke-width="{e["sw"]}"' if e.get("stroke") else ""
        return (f'<svg style="position:absolute;left:{e["x"]}px;top:{e["y"]}px;overflow:visible" width="{e["w"]:.1f}" height="{e["h"]:.1f}">'
                f'<path d="{e["d"]}" fill="{f}" {st} fill-opacity="{op}" stroke-opacity="{op}"/></svg>')
    if t == "line":
        x0, y0 = min(e["x1"], e["x2"]), min(e["y1"], e["y2"]); da = 'stroke-dasharray="10 7"' if e.get("dash") else ""
        return (f'<svg style="position:absolute;left:{x0}px;top:{y0}px;overflow:visible" width="1" height="1">'
                f'<line x1="{e["x1"]-x0}" y1="{e["y1"]-y0}" x2="{e["x2"]-x0}" y2="{e["y2"]-y0}" stroke="{e["stroke"]}" stroke-width="{e["sw"]}" {da} opacity="{op}" stroke-linecap="butt"/></svg>')
    if t == "arc":
        return (f'<svg style="position:absolute;left:0;top:0;overflow:visible" width="1" height="1"><path d="{arc_d(e["cx"],e["cy"],e["r"],e["ir"],e["a0"],e["a1"])}" fill="{e["fill"]}" opacity="{op}"/></svg>')
    return ""

def render(deck, out):
    fonts = "".join(f'@font-face{{font-family:"SF Pro Display";font-weight:{w};src:url("../design/san-francisco-pro-display/SF-Pro-Display-{n}.otf");}}' for n, w in W8.items())
    css = (f"{fonts} html,body{{margin:0;padding:0;background:#777;}} .s{{position:relative;width:1920px;height:1080px;overflow:hidden;margin:0 auto 24px;"
           f"font-family:'SF Pro Display',sans-serif;}} @media print{{body{{background:none}} .s{{margin:0;page-break-after:always}}}} @page{{size:1920px 1080px;margin:0}}")
    body = "".join(f'<section class="s" id="s{i+1}" style="background:{s["bg"]}">' + "".join(el_html(e) for e in s["els"]) + "</section>" for i, s in enumerate(deck))
    open(out, "w", encoding="utf-8").write(f'<!doctype html><html lang="ru"><head><meta charset="utf-8"><title>Коньково №2: проблемы и предпосылки</title><style>{css}</style></head><body>{body}</body></html>')

if __name__ == "__main__":
    deck = json.load(open(os.path.join(H, "deck.json"), encoding="utf-8"))
    render(deck, os.path.join(H, "deck.html")); print("deck.html", len(deck), "слайдов")
