import sys, numpy as np, trimesh
sys.path.insert(0, '/home/user/v2d-track3/docs/research/mesh-2026-10-26/cdo-sprint/C1/T3-gen-fit/scripts')
import fit
from scipy.spatial import cKDTree
z = np.load(sys.argv[2])
P = z['pts'].astype(float); C = z['cam'].astype(float)
u = C - P; u /= np.linalg.norm(u, axis=1, keepdims=True)
key = np.floor(P / 0.002).astype(np.int64)
_, inv, cnt = np.unique(key, axis=0, return_inverse=True, return_counts=True); inv = inv.ravel()
pm = np.stack([np.bincount(inv, P[:, k]) / cnt for k in range(3)], 1)
um = np.stack([np.bincount(inv, u[:, k]) / cnt for k in range(3)], 1)
Rl = np.linalg.norm(um, axis=1)
print('mean resultant length q', np.quantile(Rl, [.05, .25, .5, .75]).round(3), 'n', len(Rl))
um = um / np.maximum(Rl[:, None], 1e-9)
m = trimesh.load(sys.argv[1], process=False)
V, F = np.asarray(m.vertices), np.asarray(m.faces)
S, fid, b = fit.sample_bary(V, F, 300000, 0)
fn = fit.face_normals(V, F)
d, k = cKDTree(S).query(pm)
vis = np.einsum('ni,ni->n', fn[fid[k]], um)
for lo, hi in [(0,0.003),(0.003,0.006),(0.006,0.01)]:
    s = (d>=lo)&(d<hi)
    print(f'd [{lo*1e3:.0f},{hi*1e3:.0f}) frac {s.mean():.3f} vis>=0.2 {np.mean(vis[s]>=0.2):.3f} vis<=-0.2 {np.mean(vis[s]<=-0.2):.3f}  (R>0.8: vis>=0.2 {np.mean(vis[s & (Rl>0.8)]>=0.2):.3f})')
