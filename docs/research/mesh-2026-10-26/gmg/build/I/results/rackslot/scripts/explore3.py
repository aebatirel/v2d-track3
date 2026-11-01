import numpy as np, trimesh, time
from scipy.spatial import ConvexHull, Delaunay
import rs_lib as L
t0=time.time()
rack=L.load_mesh(L.RACK_MESH); H=L.load_hulls(L.RACK_PACKED); G=L.Grid(H)
z0=np.load('../grid_base.npz'); M=z0['M']
print('rack area m2', rack.area)
S=np.asarray(trimesh.sample.sample_surface_even(rack, int(rack.area/(0.0003**2)), seed=0)[0]); print('samples', len(S), time.time()-t0)
Mc=G.centres(M)
for ep in ['30','14']:
    F=np.load(f'../rest_ep{ep}.npz')['F']; Fc=G.centres(F)
    for i,V in enumerate(H):
        e=ConvexHull(V).equations
        fin=np.all(Fc@e[:,:3].T+e[:,3]<=1e-9,1)
        if fin.sum()<10: continue
        lo,hi=V.min(0)-1e-3,V.max(0)+1e-3
        Ks=S[np.all((S>=lo)&(S<=hi),1)]; Ks=Ks[np.all(Ks@e[:,:3].T+e[:,3]<=1e-9,1)]
        Km=Mc[np.all((Mc>=lo)&(Mc<=hi),1)]; Km=Km[np.all(Km@e[:,:3].T+e[:,3]<=1e-9,1)]
        K=np.vstack([Ks,Km])
        d=Delaunay(K[ConvexHull(K).vertices])
        inK=d.find_simplex(Fc[fin])>=0
        print(f'ep{ep} piece {i}: F {fin.sum()} vox, K {len(K)} pts, hull(K) vol {ConvexHull(K).volume*1e6:.1f} vs piece {ConvexHull(V).volume*1e6:.1f} cm3; F inside hull(K): {inK.sum()} ({inK.mean()*100:.0f}%)')
print(time.time()-t0)
