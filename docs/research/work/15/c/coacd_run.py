# Stage C: run CoACD (threshold 0.05, defaults otherwise) on public collision meshes; save hulls per object.
import sys, os, time, numpy as np, trimesh
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'pylib'))
import coacd
coacd.set_log_level('error')
R='/Users/aebatirel/Documents/Code/v2d-research/data/track_3/public/mesh'
O=os.path.join(os.path.dirname(__file__),'hulls'); os.makedirs(O,exist_ok=True)
objs=sys.argv[1:] or ['wooden_piece_1','blue_cup','plastic_dish_rack','white_pot','mini_sweeper','beige_cup','mini_dust_pan','white_pot_lid','water_pitcher','wooden_piece_2']
for n in objs:
    out=f'{O}/{n}.npz'
    if os.path.exists(out): print(n,'done already'); continue
    f=f'{R}/{n}/{n}_collision.glb' if os.path.exists(f'{R}/{n}/{n}_collision.glb') else f'{R}/{n}/{n}.glb'
    m=trimesh.load(f,force='mesh'); m.merge_vertices()
    t=time.time()
    parts=coacd.run_coacd(coacd.Mesh(m.vertices,m.faces),threshold=0.05,max_convex_hull=-1,seed=0)
    V=[np.asarray(p[0]) for p in parts]; F=[np.asarray(p[1]) for p in parts]
    np.savez(out,n=len(V),**{f'v{i}':V[i] for i in range(len(V))},**{f'f{i}':F[i] for i in range(len(F))})
    print(n,os.path.basename(f),'hulls',len(V),'sec %.0f'%(time.time()-t),'watertight_in',m.is_watertight,flush=True)
