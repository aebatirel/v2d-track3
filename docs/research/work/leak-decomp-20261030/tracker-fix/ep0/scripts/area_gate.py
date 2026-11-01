"""GT-free rule check on the public frame-0 detection dumps (refine/in, our templates): a proposal's metric silhouette
area (sum over mask pixels of (z/f)^2) vs the template's largest silhouette area (convex hull of the mesh projected on
162 view directions; an upper bound). Chosen proposals of the 25 Oct runs vs the ep0 table-top decoys. No GT read."""
import sys, glob, os
import numpy as np, trimesh
from scipy.spatial import ConvexHull
S = '/tmp/claude-0/-home-user-v2d-track3/68c88876-77c0-55d9-bea4-03de8a3f6ee7/scratchpad'
LIB = '/home/user/v2d-track3/meshes/library_v3'; T3D = S + '/map/scoring/t3'
def max_sil(path):
    m = trimesh.load(path, force='mesh'); P = np.asarray(m.sample(6000)); P -= P.mean(0); best = 0
    for d in trimesh.creation.icosphere(subdivisions=2).vertices:
        d = d / np.linalg.norm(d); a = np.cross(d, [0, 0, 1.0] if abs(d[2]) < 0.9 else [0, 1.0, 0]); a /= np.linalg.norm(a); b = np.cross(d, a)
        Q = np.stack([P @ a, P @ b], 1); best = max(best, ConvexHull(Q).volume)
    return best
def scanp(n):
    p = f'{T3D}/mesh/{n}/{n}.glb'; return p if os.path.exists(p) else f'{T3D}/mesh/{n}/{n}_visual.glb'
cache = {}
res = []
for f in sorted(glob.glob(f'{S}/refine/in/ep*/det_f0.npz'), key=lambda p: int(p.split('/ep')[1].split('/')[0])):
    ep = int(f.split('/ep')[1].split('/')[0]); d = np.load(f)
    sh = d['mask_shape']; mk = np.unpackbits(d['masks'], axis=-1)[:, :, :sh[2]].astype(bool)
    dep = d['depth'].astype(np.float32); fh = d['K'][0, 0] * 0.5
    def area(j):
        z = dep[mk[j] & (dep > 0)]; n_all = mk[j].sum(); n_ok = len(z)
        return float(((z / fh) ** 2).sum() * (n_all / max(n_ok, 1)))
    for a, n in enumerate([str(x) for x in d['names']]):
        if n not in cache: cache[n] = (max_sil(f'{LIB}/{n}.glb'), max_sil(scanp(n)))
        j = int(d['chosen'][a]); A = area(j)
        res.append(A / cache[n][0])
        print(f'ep{ep:2d} {n:18s} chosen {j:3d} area {A*1e4:6.0f} cm2  tpl max sil ours {cache[n][0]*1e4:5.0f} scan {cache[n][1]*1e4:5.0f}  ratio ours {A/cache[n][0]:.2f}')
    if ep == 0:
        for j in (0, 1, 25, 45, 48, 53):
            A = area(j); print(f'   ep0 proposal {j:2d} area {A*1e4:6.0f} cm2  / pot ours {A/cache["white_pot"][0]:.2f}  / pot scan {A/cache["white_pot"][1]:.2f}  / lid ours {A/cache["white_pot_lid"][0]:.2f}')
print('chosen ratio (ours) min/max', round(min(res), 2), round(max(res), 2))
