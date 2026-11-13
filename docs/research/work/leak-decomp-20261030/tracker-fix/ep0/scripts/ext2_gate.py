"""GT-free rule check on the public frame-0 detection dumps (refine/in, our library_v2 templates): three principal 3-D
extents of each proposal vs the template's OBB extents. Reports the chosen proposals' ratios (all 20 episodes) and the
ep0 decoys (table top). No ground truth is read."""
import sys, glob, os
import numpy as np, trimesh
sys.path.insert(0, '/home/user/v2d-track3/pipeline')
import det_rules
S = '/tmp/claude-0/-home-user-v2d-track3/68c88876-77c0-55d9-bea4-03de8a3f6ee7/scratchpad'
LIB2 = '/home/user/v2d-track3/meshes/library_v3'; T3D = S + '/map/scoring/t3'
def ext3(m, dep, K):
    v, u = np.nonzero(m & (dep > 0))
    if len(v) < 30: return np.zeros(3)
    z = dep[v, u]; X = np.stack([(u - K[0, 2]) * z / K[0, 0], (v - K[1, 2]) * z / K[1, 1], z], 1)
    X = X[::max(1, len(X) // 5000)]; X = X - np.median(X, 0)
    pr = X @ np.linalg.svd(X, full_matrices=False)[2].T
    return np.sort(np.percentile(pr, 97, 0) - np.percentile(pr, 3, 0))[::-1]
def tpl(path):
    return np.sort(trimesh.load(path, force='mesh').bounding_box_oriented.extents)[::-1]
rows = []
for f in sorted(glob.glob(f'{S}/refine/in/ep*/det_f0.npz'), key=lambda p: int(p.split('/ep')[1].split('/')[0])):
    ep = int(f.split('/ep')[1].split('/')[0]); d = np.load(f)
    sh = d['mask_shape']; mk = np.unpackbits(d['masks'], axis=-1)[:, :, :sh[2]].astype(bool)
    dep = d['depth'].astype(np.float32); K = d['K'].copy(); K[:2] *= 0.5
    names = [str(x) for x in d['names']]
    plane = det_rules.table_plane(dep, K)
    for a, n in enumerate(names):
        j = int(d['chosen'][a]); e = ext3(mk[j], dep, K)
        T_ours = tpl(f'{LIB2}/{n}.glb'); sp = f'{T3D}/mesh/{n}/{n}.glb'; sp = sp if os.path.exists(sp) else f'{T3D}/mesh/{n}/{n}_visual.glb'
        T_scan = tpl(sp)
        rows.append((ep, n, j, e, T_ours, T_scan))
        print(f'ep{ep:2d} {n:18s} chosen {j:3d} ext {np.round(e,3)} ours {np.round(T_ours,3)} scan {np.round(T_scan,3)} ratio(ours) {np.round(e/T_ours,2)}')
    if ep == 0:
        for j in (0, 1, 25, 45, 48, 53):
            print('   ep0 proposal', j, 'ext', np.round(ext3(mk[j], dep, K), 3))
r1 = np.array([r[3][0] / r[4][0] for r in rows]); r2 = np.array([r[3][1] / r[4][1] for r in rows])
print('chosen (ours): ratio of largest extent min/max', r1.min().round(2), r1.max().round(2), '; middle extent min/max', r2.min().round(2), r2.max().round(2))
