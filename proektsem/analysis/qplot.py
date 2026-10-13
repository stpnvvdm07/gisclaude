# Быстрый просмотр слоёв в плане (для проверки, не для презентации)
import sys; sys.path.insert(0, 'analysis')
import geopandas as gpd, matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
from plan import to_plan
SP = '/tmp/claude-0/-home-user-gisclaude/98167342-a537-5003-ba2c-47c48924461e/scratchpad/'
def P(d): return d.set_geometry(d.geometry.apply(to_plan))
def base(K='vector/konkovo_v15.gpkg', net=True):
    fig, ax = plt.subplots(figsize=(24, 14)); ax.set_aspect('equal'); ax.axis('off')
    c = P(gpd.read_file(K, layer='cells')); b = P(gpd.read_file(K, layer='buildings'))
    c[c.is_anal == 1].plot(ax=ax, color='#e3efdc', ec='#555', lw=.5); c[c.is_anal == 0].plot(ax=ax, color='#eee', ec='#555', lw=.5)
    b.plot(ax=ax, color='#a39279')
    if net: P(gpd.read_file('vector/analiz_v13.gpkg', layer='network')).plot(ax=ax, color='#aaa', lw=.6)
    for r in c.itertuples(): p = r.geometry.representative_point(); ax.text(p.x, p.y, str(r.num), fontsize=9, ha='center', color='#777')
    return fig, ax
def save(fig, name): fig.savefig(SP + name, dpi=80, bbox_inches='tight'); plt.close(fig)
