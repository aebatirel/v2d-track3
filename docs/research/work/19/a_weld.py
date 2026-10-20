# Is the scanned geometry closed once welded by position? (Newton itself does NOT do this weld.)
import sys, os, re, numpy as np, trimesh
R='/Users/aebatirel/Documents/Code/v2d-research/data/track_3/public'
u=sys.argv[1]; x=open(f'{R}/urdf/{u}_rigid.urdf').read()
fn=re.search(r'<collision>.*?filename="([^"]+)"',x,re.S).group(1); f=os.path.normpath(os.path.join(R,'urdf',fn))
m=trimesh.load(f,force='mesh'); m=trimesh.Trimesh(np.asarray(m.vertices),np.asarray(m.faces),process=False)
m.merge_vertices(merge_tex=True,merge_norm=True)
e=m.edges_sorted; _,cnt=np.unique(e,axis=0,return_counts=True)
print(f'{u:20s} weldedV={len(m.vertices)} F={len(m.faces)} watertight={m.is_watertight} boundary_edges={(cnt==1).sum()} nonmanifold_edges={(cnt>2).sum()} bodies={m.body_count} ext_mm={np.round(m.extents*1000,1)}',flush=True)
