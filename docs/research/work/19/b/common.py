# Shared helpers for Stage B (own code; mirrors the loading used by newton 1.2.0 / note-15 pen2.py).
import os, re, numpy as np, trimesh
from scipy.spatial.transform import Rotation as R_
P='/Users/aebatirel/Documents/Code/v2d-research/data/track_3/public'
W='/Users/aebatirel/Documents/Code/v2d-research/work/19/b'
def scan_path(n):
    u=open(f'{P}/urdf/{n}_rigid.urdf').read()
    return os.path.normpath(os.path.join(P,'urdf',re.search(r'<collision>.*?filename="([^"]+)"',u,re.S).group(1)))
def scan_newton(n):           # as newton.load_meshes_from_file sees it (trimesh default processing, force='mesh')
    return trimesh.load(scan_path(n),force='mesh')
def scan_welded(n):           # position-welded copy (UV/normal seams merged)
    m=scan_newton(n); m=trimesh.Trimesh(np.asarray(m.vertices),np.asarray(m.faces),process=False)
    m.merge_vertices(merge_tex=True,merge_norm=True); return m
def T(pose):
    x,y,z,qw,qx,qy,qz=pose; M=np.eye(4); M[:3,:3]=R_.from_quat([qx,qy,qz,qw]).as_matrix(); M[:3,3]=[x,y,z]; return M
def tr(M,p): return p@M[:3,:3].T+M[:3,3]
def save_hulls(path,parts):
    np.savez(path,n=len(parts),**{f'v{i}':np.asarray(p[0]) for i,p in enumerate(parts)},**{f'f{i}':np.asarray(p[1]) for i,p in enumerate(parts)})
def load_hulls(path):
    d=np.load(path); return [d[f'v{i}'] for i in range(int(d['n']))]
def cap_hull(v,k=64):
    # [E] emulation of MuJoCo's maxhullvert (qhull 'Qt TA<k-4>': stop after k vertices -> inner hull of a vertex
    # subset). Greedy: initial large simplex, then repeatedly add the input point furthest outside the current hull.
    # qhull adds points facet by facet, so the real subset is likely no better than this (this is optimistic).
    from scipy.spatial import ConvexHull
    hv=v[ConvexHull(v).vertices]
    if len(hv)<=k: return hv
    i0=np.argmax(hv[:,0]); i1=np.argmax(np.linalg.norm(hv-hv[i0],axis=1))
    d=hv[i1]-hv[i0]; d/=np.linalg.norm(d); w=hv-hv[i0]; i2=np.argmax(np.linalg.norm(w-np.outer(w@d,d),axis=1))
    nrm=np.cross(hv[i1]-hv[i0],hv[i2]-hv[i0]); nrm/=np.linalg.norm(nrm); i3=np.argmax(np.abs(w@nrm))
    sel=[i0,i1,i2,i3]
    while len(sel)<k:
        e=ConvexHull(hv[sel]).equations; s=(hv@e[:,:3].T+e[:,3]).max(1); s[sel]=-1
        j=int(np.argmax(s))
        if s[j]<=1e-12: break
        sel.append(j)
    return hv[sel]
