"""Locate mocap-marker spheres in scans via texture brightness (grey-white) + geometry; fit sphere radius."""
import sys, numpy as np, trimesh
sys.path.insert(0,"scripts"); from render_scan import load, face_colors
from scipy.optimize import least_squares
from scipy.sparse.csgraph import connected_components
for name in sys.argv[1].split(","):
    m=load(name); fc=face_colors(m); V=np.asarray(m.vertices); F=np.asarray(m.faces)
    T=V[F]; area=0.5*np.linalg.norm(np.cross(T[:,1]-T[:,0],T[:,2]-T[:,0]),axis=1)
    c=(area[:,None]*T.mean(1)).sum(0)/area.sum()
    hsv_s=(fc.max(1)-fc.min(1))/(fc.max(1)+1e-6); bright=fc.mean(1)
    sel=(hsv_s<0.18)&(bright>120)   # grey/white low-saturation
    idx=np.where(sel)[0]
    if len(idx)==0: print(name,"none"); continue
    # face adjacency components among selected faces
    adj=m.face_adjacency
    keep=sel[adj[:,0]]&sel[adj[:,1]]
    import scipy.sparse as sp
    A=sp.coo_matrix((np.ones(keep.sum()),(adj[keep,0],adj[keep,1])),shape=(len(F),len(F)))
    n,lab=connected_components(A,directed=False)
    out=[]
    for L in np.unique(lab[idx]):
        f=idx[lab[idx]==L]
        a=area[f].sum()
        if a<5e-5: continue   # <0.5 cm^2
        P=T[f].reshape(-1,3)
        def r(p): return np.linalg.norm(P-p[:3],axis=1)-p[3]
        p0=np.r_[P.mean(0),0.007]
        s=least_squares(r,p0)
        out.append((a*1e4, (s.x[:3]-c)*1000, s.x[3]*1000, np.sqrt(np.mean(s.fun**2))*1000))
    out.sort(key=lambda t:-t[0])
    print(f"{name}: {len(out)} grey patches >0.5cm2 (area cm2, centre mm in published frame, radius mm, rms mm)")
    for o in out[:10]: print(f"   {o[0]:6.2f}  [{o[1][0]:+7.1f} {o[1][1]:+7.1f} {o[1][2]:+7.1f}]  r={o[2]:5.1f}  rms={o[3]:4.2f}")
