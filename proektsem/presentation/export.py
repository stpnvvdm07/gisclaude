# deck.html -> deck.pdf + png/sNN.png (Chromium через Playwright)
import os, sys, asyncio
from playwright.async_api import async_playwright
H = os.path.dirname(os.path.abspath(__file__))
async def main(only=None):
    os.makedirs(os.path.join(H, "png"), exist_ok=True)
    async with async_playwright() as p:
        b = await p.chromium.launch(executable_path="/opt/pw-browsers/chromium-1194/chrome-linux/chrome")
        pg = await b.new_page(viewport={"width": 1920, "height": 1080})
        await pg.goto("file://" + os.path.join(H, "deck.html")); await pg.wait_for_load_state("networkidle")
        await pg.evaluate("document.fonts.ready")
        secs = await pg.query_selector_all("section.s")
        for i, sec in enumerate(secs):
            if only and (i + 1) not in only: continue
            await sec.screenshot(path=os.path.join(H, "png", f"s{i+1:02d}.png"))
        if not only:
            await pg.pdf(path=os.path.join(H, "deck.pdf"), width="1920px", height="1080px", print_background=True, prefer_css_page_size=True)
        await b.close()
asyncio.run(main({int(x) for x in sys.argv[1:]} or None))
