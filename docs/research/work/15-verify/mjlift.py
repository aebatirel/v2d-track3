# Hull-aware projection test: lift the upper object along world z until it clears the other object's hulls, then settle.
import os, numpy as np
import mjsettle as S, penv as P
import trimesh
def maxdepth(a,Ra,ta,b,Rb,tb,Pa):
    Eb=[P.planes(v) for v,_ in P.load_hulls(b)]
    return P.depth_in(P.to_b(Pa,Ra,ta,Rb,tb),Eb).max()
sol=os.environ.get('SOLREF','0.02 1')
for ep,a,b in [(31,'mini_sweeper','plastic_dish_rack'),(0,'white_pot_lid','white_pot')]:
    O=S.gt(ep,0,[a,b]); (_,Ra,ta),(_,Rb,tb)=O; zt=S.minz(b,Rb,tb)
    Pa=np.vstack([v for v,_ in P.load_hulls(a)])   # hull vertices of A
    hm=trimesh.util.concatenate([trimesh.Trimesh(v,f) for v,f in P.load_hulls(a)]); Pa=np.vstack([Pa,hm.sample(20000,seed=4)])
    dz=0.0
    while maxdepth(a,Ra,ta+[0,0,dz],b,Rb,tb,Pa)>0.0005 and dz<0.06: dz+=0.001
    print(f'ep{ep} {a}: lift needed to clear {b} hulls = {dz*1e3:.0f} mm')
    S.run(f'ep{ep} f0 {a} lifted {dz*1e3:.0f} mm',[(a,Ra,ta+[0,0,dz]),(b,Rb,tb)],zt,sol)
