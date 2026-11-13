import sys, numpy as np, trimesh
sys.path.insert(0, '/home/user/v2d-track3/docs/research/mesh-2026-10-26/cdo-sprint/C1/T3-gen-fit/scripts')
import fit
from scipy.spatial import cKDTree
cfg = dict(fit.DEFAULT)
obs, grid = fit.load_obs(sys.argv[2], cfg)
m = trimesh.load(sys.argv[1], process=False)
V, F = np.asarray(m.vertices), np.asarray(m.faces)
P, U = obs['train']['p'], obs['train']['u']
S, fid, b = fit.sample_bary(V, F, 300000, 0)
fn = fit.face_normals(V, F)
d, k = cKDTree(S).query(P)
n = fn[fid[k]]
vis = np.einsum('ni,ni->n', n, U)
side = np.einsum('ni,ni->n', P - S[k], n)
print('n obs', len(P))
for lo, hi in [(0,0.003),(0.003,0.006),(0.006,0.01),(0.01,1)]:
    s = (d>=lo)&(d<hi)
    print(f'd [{lo*1e3:.0f},{hi*1e3:.0f}) frac {s.mean():.3f} vis>=0.1 {np.mean(vis[s]>=0.1):.3f} vis<=-0.1 {np.mean(vis[s]<=-0.1):.3f} outside(side>0) {np.mean(side[s]>0):.3f}')
# camera spread: how far is cam from point
cd = np.linalg.norm(obs['train']['p'] - (obs['train']['p'] + U), axis=1)
print('U norm check', np.quantile(np.linalg.norm(U,axis=1),[0,1]))
