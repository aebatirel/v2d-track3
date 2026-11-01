"""GT-free: score margin between each object's chosen frame-0 proposal and its best 'oversized' proposal (metric area
> 1.5 x the template's largest silhouette), public refine dumps (our templates). No GT read."""
import glob, sys
import numpy as np, trimesh
from scipy.spatial import ConvexHull
S = '/tmp/claude-0/-home-user-v2d-track3/68c88876-77c0-55d9-bea4-03de8a3f6ee7/scratchpad'; LIB = '/home/user/v2d-track3/meshes/library_v3'
def max_sil(path):
    m = trimesh.load(path, force='mesh'); P = np.asarray(m.sample(6000)); P -= P.mean(0); best = 0
    for d in trimesh.creation.icosphere(subdivisions=2).vertices:
        d = d / np.linalg.norm(d); a = np.cross(d, [0, 0, 1.0] if abs(d[2]) < 0.9 else [0, 1.0, 0]); a /= np.linalg.norm(a); b = np.cross(d, a)
        best = max(best, ConvexHull(np.stack([P @ a, P @ b], 1)).volume)
    return best
C = {}; n_bar = 0
for f in sorted(glob.glob(f'{S}/refine/in/ep*/det_f0.npz'), key=lambda p: int(p.split('/ep')[1].split('/')[0])):
    ep = int(f.split('/ep')[1].split('/')[0]); d = np.load(f)
    sh = d['mask_shape']; mk = np.unpackbits(d['masks'], axis=-1)[:, :, :sh[2]].astype(bool)
    dep = d['depth'].astype(np.float32); fh = d['K'][0, 0] * 0.5
    A = np.array([float(((dep[m & (dep > 0)] / fh) ** 2).sum() * (m.sum() / max((m & (dep > 0)).sum(), 1))) for m in mk])
    Sr = d['score_rules']
    for a, n in enumerate([str(x) for x in d['names']]):
        if n not in C: C[n] = max_sil(f'{LIB}/{n}.glb')
        big = A / C[n] > 1.5; j = int(d['chosen'][a]); n_bar += int((big & (Sr[a] > -10)).sum())
        best_big = Sr[a][big].max() if big.any() else -10
        print(f'ep{ep:2d} {n:18s} chosen {j:3d} score {Sr[a, j]:+.3f}  best oversized {best_big:+.3f}  margin {Sr[a, j] - best_big:+.3f}  oversized-and-eligible {int((big & (Sr[a] > -10)).sum())}')
print('eligible proposals the gate would bar (all objects, 20 eps):', n_bar)
