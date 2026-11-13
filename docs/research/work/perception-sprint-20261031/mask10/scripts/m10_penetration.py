"""GT-free physical-consistency check: penetration of the beige cup's eval-10 collision pieces into the blue cup's
(meshes/carve/ev10, the simulator geometry of eval 10) along refine outputs, as docs/analysis/ev10-stack-20261026/
nest_pen.py (max over pieces of the depth inside a convex piece), plus the blue cup's lowest collision point vs our
frame-0 table plane (S12's). Reads our perception outputs and our collision pieces only.
Usage: python -I m10_penetration.py POSE_OPT_WITH_S12 OUT_JSON label=DIR [label=DIR ...]"""
import glob, json, sys
import numpy as np, trimesh
from scipy.spatial import ConvexHull
sys.path.insert(0, '/home/user/v2d-track3/pipeline')
import refine
PC = '/home/user/v2d-track3/meshes/carve/ev10'
popt, out = sys.argv[1], sys.argv[2]
pl = json.load(open(refine.checked(popt)))['steps']['S12']['plane']
n, d = np.asarray(pl['n'], float), float(pl['d'])
pa = [trimesh.load(refine.checked(f), force='mesh') for f in sorted(glob.glob(f'{PC}/beige_cup/piece_*.obj'))]
pb_m = [trimesh.load(refine.checked(f), force='mesh') for f in sorted(glob.glob(f'{PC}/blue_cup/piece_*.obj'))]
pb = [ConvexHull(p.vertices) for p in pb_m]
Sa = np.vstack([p.sample(300, seed=1) if 'seed' in p.sample.__code__.co_varnames else p.sample(300) for p in pa] + [p.vertices for p in pa])
Vb = np.vstack([p.vertices for p in pb_m])


def depth(X):
    best = np.zeros(len(X))
    for h in pb:
        sd = X @ h.equations[:, :3].T + h.equations[:, 3]
        best = np.maximum(best, -sd.max(1))
    return best


res = {}
for arg in sys.argv[3:]:
    lab, dr = arg.split('=', 1)
    V = np.load(refine.checked(f'{dr}/poses_world_vo.npz'))
    A, B = V['beige_cup'].astype(float), V['blue_cup'].astype(float)
    pen, bot = [], []
    for t in range(len(A)):
        X = (Sa @ A[t][:3, :3].T + A[t][:3, 3] - B[t][:3, 3]) @ B[t][:3, :3]      # beige samples in the blue frame
        pen.append(float(depth(X).max() * 1000))
        bot.append(float(((Vb @ B[t][:3, :3].T + B[t][:3, 3]) @ n).min() + d) * 100)
    pen, bot = np.array(pen), np.array(bot)
    res[lab] = dict(pen_mm=np.round(pen, 1).tolist(), blue_bottom_cm=np.round(bot, 2).tolist(),
                    frames_pen_gt_2mm=int((pen > 2).sum()), pen_max_mm=round(float(pen.max()), 1),
                    pen_median_nested_mm=round(float(np.median(pen[-40:])), 1),
                    blue_bottom_last40_median_cm=round(float(np.median(bot[-40:])), 2), blue_bottom_f0_cm=round(float(bot[0]), 2))
    print(lab, {k: v for k, v in res[lab].items() if not isinstance(v, list)})
json.dump(res, open(out, 'w'))
