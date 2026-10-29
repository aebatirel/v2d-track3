"""Overlap of two meshes posed by our tracks, per frame (census method: 2 mm solid samples of A, exact winding-number
signed distance in B; reported = mean of A-in-B and B-in-A). fcvenv (warp).
Usage: ovl_eval.py MESH_A MESH_B POSES.npz OBJ_A OBJ_B --frames a:b[:s] [--json OUT]"""
import argparse, json, sys
import numpy as np, trimesh
sys.path.insert(0, '/tmp/claude-0/-home-user-v2d-track3/8c892c5e-fd7c-57aa-abef-68d2af098e4f/scratchpad/interact')
import vox2
p = argparse.ArgumentParser(); p.add_argument('ma'); p.add_argument('mb'); p.add_argument('poses'); p.add_argument('oa'); p.add_argument('ob')
p.add_argument('--frames', default='0:100000:2'); p.add_argument('--json', default=''); p.add_argument('--pitch', type=float, default=0.002)
a = p.parse_args()
P = np.load(a.poses); TA = P[f'cam_T_{a.oa}'].astype(np.float64); TB = P[f'cam_T_{a.ob}'].astype(np.float64)
f = [int(x) for x in a.frames.split(':')]; fr = np.arange(f[0], min(f[1], len(TA), len(TB)), f[2] if len(f) > 2 else 1)
O = {}
for k, path in (('A', a.ma), ('B', a.mb)):
    m = trimesh.load(path, force='mesh'); m.merge_vertices()
    sd = vox2.SD(m, 'winding'); pts, _, _ = vox2.solid_samples(m, sd, a.pitch)
    O[k] = dict(m=m, sd=sd, pts=np.asarray(pts, np.float64), lo=m.bounds[0] - 1e-3, hi=m.bounds[1] + 1e-3)
h3 = a.pitch ** 3 * 1e6
def inside(X, Y, T):
    Q = X['pts'] @ T[:3, :3].T + T[:3, 3]
    box = np.flatnonzero(np.all((Q >= Y['lo']) & (Q <= Y['hi']), 1))
    if len(box) == 0:
        return 0, 0.0
    d = Y['sd'](Q[box]); k = d < 0
    return int(k.sum()), (float(-d[k].min()) if k.any() else 0.0)
rows = []
for t in fr:
    T = np.linalg.inv(TB[t]) @ TA[t]
    nab, _ = inside(O['A'], O['B'], T); nba, _ = inside(O['B'], O['A'], np.linalg.inv(T))
    rows.append((int(t), round(nab * h3, 3), round(nba * h3, 3), round(0.5 * (nab + nba) * h3, 3)))
ov = np.array([r[3] for r in rows])
res = dict(meshA=a.ma, meshB=a.mb, volA_cm3=round(len(O['A']['pts']) * h3, 2), volB_cm3=round(len(O['B']['pts']) * h3, 2),
           frames=len(rows), max_cm3=float(ov.max()) if len(ov) else 0, max_frame=int(rows[int(ov.argmax())][0]) if len(ov) else -1,
           median_cm3=float(np.median(ov)) if len(ov) else 0, final_cm3=float(ov[-1]) if len(ov) else 0,
           frames_gt1=int((ov > 1).sum()), per_frame=rows)
print(json.dumps({k: v for k, v in res.items() if k != 'per_frame'}))
if a.json:
    json.dump(res, open(a.json, 'w'))
