import sys, time, numpy as np, json
import rs_lib as L
t0=time.time()
rack=L.load_mesh(L.RACK_MESH); H=L.load_hulls(L.RACK_PACKED)
G=L.Grid(H); print('grid', G.n, G.lo)
z0=np.load('../grid_base.npz'); M,PK=z0['M'],z0['PK']
v=1e-3**3*1e6
print('mesh cm3', M.sum()*v, 'packed', PK.sum()*v, 'packed&~mesh', (PK&~M).sum()*v, 'mesh&~packed', (M&~PK).sum()*v, time.time()-t0)
piece_occ=[G.hull_occ(V) for V in H]
for ep in ['30','14']:
    R, info = L.rest_frames(ep); print(ep, len(R), info)
    P=L.poses(ep); gh=L.load_hulls(L.GUEST[ep]['packed'])
    RV=L.rest_volume(G, gh, P['rel'], R, PK)
    F=RV & PK & ~M
    print(ep, 'restvol', RV.sum()*v, 'in packed', (RV&PK).sum()*v, 'F (in packed beyond mesh)', F.sum()*v, 'restvol&mesh', (RV&M).sum()*v)
    rows=[]
    for i,o in enumerate(piece_occ):
        f=(o&F).sum()*v
        if f>0.01: rows.append((i, round(f,2), round(o.sum()*v,1), round((o&M).sum()*v,1)))
    print('  pieces touching F (i, F cm3, piece cm3, mesh-in-piece cm3):', rows)
    np.savez_compressed(f'../rest_ep{ep}.npz', RV=RV, F=F, R=np.array(R))
print(time.time()-t0)
