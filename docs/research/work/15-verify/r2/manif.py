# Is the URDF collision mesh manifold as trimesh loads it (process True/False)? CoACD 'auto' remeshes non-manifold input.
import trimesh, numpy as np, re, sys
R='/Users/aebatirel/Documents/Code/v2d-research/data/track_3/public'
for n in ['white_pot_lid','white_pot','plastic_dish_rack','mini_sweeper','blue_cup','beige_cup']:
    u=open(f'{R}/urdf/{n}_rigid.urdf').read()
    f=R+'/urdf/'+re.search(r'<collision>.*?filename="([^"]+)"',u,re.S).group(1)
    for p in (True,False):
        m=trimesh.load(f,force='mesh',process=p)
        e=m.edges_sorted; _,c=np.unique(e,axis=0,return_counts=True)
        print(n, 'process',p,'V',len(m.vertices),'F',len(m.faces),'watertight',m.is_watertight,
              'edges used !=2:',int((c!=2).sum()),'of',len(c), 'ext mm', np.round(m.extents*1000).astype(int))
