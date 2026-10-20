import sys, os, re, numpy as np, trimesh, networkx as nx
R='/Users/aebatirel/Documents/Code/v2d-research/data/track_3/public'
def load(u):
    x=open(f'{R}/urdf/{u}_rigid.urdf').read()
    fn=re.search(r'<collision>.*?filename="([^"]+)"',x,re.S).group(1); f=os.path.normpath(os.path.join(R,'urdf',fn))
    m=trimesh.load(f,force='mesh'); m=trimesh.Trimesh(np.asarray(m.vertices),np.asarray(m.faces),process=False)
    m.merge_vertices(merge_tex=True,merge_norm=True); return m
for u in sys.argv[1:]:
    m=load(u); print(u,'bounds_mm',np.round(m.bounds*1e3,1).tolist(),'area_m2 %.4f'%m.area)
    e=m.edges_sorted; ue,cnt=np.unique(e,axis=0,return_counts=True); b=ue[cnt==1]
    g=nx.Graph(); g.add_edges_from(b.tolist())
    for c in sorted(nx.connected_components(g),key=len,reverse=True)[:3]:
        p=m.vertices[list(c)]*1e3; print('  loop n',len(c),'min',np.round(p.min(0),1).tolist(),'max',np.round(p.max(0),1).tolist())
    for x in sorted(m.split(only_watertight=False),key=lambda t:-len(t.faces))[:3]:
        print('  body F',len(x.faces),'bounds',np.round(x.bounds*1e3,1).tolist(),'wt',x.is_watertight,'vol_cm3 %.1f'%(x.volume*1e6) if x.is_watertight else '')
    # ray along the vertical axis through the bbox centre: count crossings
    c=m.bounds.mean(0)
    for ax in range(3):
        o=c.copy(); o[ax]=m.bounds[0,ax]-0.01; d=np.zeros(3); d[ax]=1
        loc,_,_=m.ray.intersects_location([o],[d]); print('  ray axis',ax,'hits_mm',np.round(np.sort(loc[:,ax])*1e3,1).tolist())
