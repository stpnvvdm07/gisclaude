import sys; sys.path.insert(0,'analysis'); from qplot import *
K='vector/konkovo_v15.gpkg'
fig,ax=base(K=K)
P(gpd.read_file(K,layer='core_edge')).plot(ax=ax,color='orange',lw=1.5)
P(gpd.read_file(K,layer='fences')).plot(ax=ax,color='purple',lw=.8); P(gpd.read_file(K,layer='arches')).plot(ax=ax,color='red',lw=2)
e=P(gpd.read_file(K,layer='entries_territory'))
for r in e.itertuples():
    col='green' if r.fix_class=='организован' else 'red'
    ax.plot(r.geometry.x,r.geometry.y,'o',color=col,ms=9,mec='w'); ax.text(r.geometry.x+3,r.geometry.y+4,r.podtip[7:17],fontsize=8)
P(gpd.read_file(K,layer='loading_zones')).plot(ax=ax,color='#6852a0'); P(gpd.read_file(K,layer='business')).plot(ax=ax,color='blue',markersize=8)
save(fig,'v15_entries.png')
