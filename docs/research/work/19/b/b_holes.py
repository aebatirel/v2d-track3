# Stage B: hole/fragment structure of the position-welded scans (boundary loops, loop diameters, body sizes).
import sys, os, re, numpy as np, trimesh, networkx as nx
R='/Users/aebatirel/Documents/Code/v2d-research/data/track_3/public'
def load(u):
    x=open(f'{R}/urdf/{u}_rigid.urdf').read()
    fn=re.search(r'<collision>.*?filename="([^"]+)"',x,re.S).group(1); f=os.path.normpath(os.path.join(R,'urdf',fn))
    m=trimesh.load(f,force='mesh'); m=trimesh.Trimesh(np.asarray(m.vertices),np.asarray(m.faces),process=False)
    m.merge_vertices(merge_tex=True,merge_norm=True); return m
for u in sys.argv[1:]:
    m=load(u); e=m.edges_sorted; ue,cnt=np.unique(e,axis=0,return_counts=True); b=ue[cnt==1]
    g=nx.Graph(); g.add_edges_from(b.tolist())
    loops=[]
    for c in nx.connected_components(g):
        p=m.vertices[list(c)]; loops.append((len(c),np.ptp(p,0).max()*1e3))
    loops.sort(key=lambda t:-t[1])
    bodies=m.split(only_watertight=False); bs=sorted([(len(x.faces),round(float(np.ptp(x.vertices,0).max()*1e3),1)) for x in bodies],key=lambda t:-t[0])
    print(f'{u}: loops={len(loops)} largest(nverts,diam_mm)={[(n,round(d,1)) for n,d in loops[:6]]} bodies(F,ext_mm)={bs[:5]}',flush=True)
