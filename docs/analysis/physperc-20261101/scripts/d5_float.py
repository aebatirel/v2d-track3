"""D5: GT-free detection of floating resting objects; DIAGNOSTIC check of their true vertical error.
GT-free part, per object and frame: hand distance (our hands) > HAND_MM, lowest point of our mesh above OUR table
> FLOAT_MM, and no other roster object under it (no other object's hull vertex within the object's table-plane
footprint radius with height in [bottom - 15 mm, bottom + 3 mm]). Floating runs >= 5 frames.
Diagnostic part (mocap): in the kit-aligned frame, the vertical residual (truth - ours, mm) of the kit anchor over
those frames, vs the drop a rule would apply (f0-gap target or 0-gap target).
Usage: d5_float.py SCRATCH TRACKS OUT"""
import sys, json, os, numpy as np
S, TR, OUT = sys.argv[1:4]
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import physlib as PL
HAND_MM, FLOAT_MM, MINRUN = 50.0, 10.0, 5
EPS = [0, 2, 11, 12, 13, 18, 21, 22, 23, 24, 26, 27, 31, 39, 40, 41, 42, 43, 44, 45]
import pyarrow.parquet as pq, trimesh
from scipy.spatial.transform import Rotation as Rot
res = {}
for e in EPS:
    tab = pq.read_table(f'{S}/t3/ep{e}.parquet').to_pandas()   # DIAGNOSTIC ONLY (truth heights)
    P = dict(np.load(f'{TR}/ep{e}/poses_world_vo.npz')); names = list(P)
    up, d = PL.table_up(S, e, P, f'{S}/mesh9a'); J = PL.hand_joints(S, e)
    T = len(P[names[0]])
    hv = {n: np.asarray(PL.mesh(f'{S}/mesh9a/{n}.glb').convex_hull.vertices) for n in names}
    res[e] = {}
    for n in names:
        mp = f'{S}/mesh9a/{n}.glb'
        gap = np.zeros(T); hd = np.zeros(T); under = np.zeros(T, bool)
        for t in range(T):
            X = hv[n] @ P[n][t][:3, :3].T + P[n][t][:3, 3]
            h = X @ up + d; gap[t] = h.min()
            hd[t] = PL.hand_dist(J, t, mp, P[n][t])
            c = X.mean(0); rad = np.max(np.linalg.norm((X - c) - np.outer((X - c) @ up, up), axis=1))
            for m in names:
                if m == n:
                    continue
                Y = hv[m] @ P[m][t][:3, :3].T + P[m][t][:3, 3]
                hy = Y @ up + d
                lat = np.linalg.norm((Y - c) - np.outer((Y - c) @ up, up), axis=1)
                if np.any((lat < rad) & (hy > gap[t] - 0.015) & (hy < gap[t] + 0.003)):
                    under[t] = True
        sv = np.asarray(trimesh.load(PL.scan_path(S, n), force='mesh').convex_hull.vertices)
        htrue = np.array([ (sv @ Rot.from_quat([q[4], q[5], q[6], q[3]]).as_matrix().T + q[:3])[:, 2].min() - 0.600 for q in [np.array([o for o in tab['observation.objects'].iloc[t] if o['name'] == n][0]['pose']) for t in range(T)]])
        flo = (hd * 1000 > HAND_MM) & (gap * 1000 > FLOAT_MM) & ~under
        segs = []
        for k, g in __import__('itertools').groupby(enumerate(flo), key=lambda x: x[1]):
            g = list(g)
            if k and len(g) >= MINRUN:
                segs.append((g[0][0], g[-1][0]))
        res[e][n] = dict(gap0_mm=round(gap[0] * 1000, 1), segs=segs, n_float=int(sum(b - a + 1 for a, b in segs)),
                         gap_mm_in_segs=[round(float(np.median(gap[a:b + 1])) * 1000, 1) for a, b in segs],
                         true_gap_mm_in_segs=[round(float(np.median(htrue[a:b + 1])) * 1000, 1) for a, b in segs], true_gap0_mm=round(float(htrue[0]) * 1000, 1),
                         gap_series_mm=np.round(gap * 1000, 1).tolist(), hand_series_mm=np.round(np.minimum(hd, 9.99) * 1000, 0).tolist(),
                         under_series=under.astype(int).tolist())
        if segs:
            print(e, n, 'gap0', res[e][n]['gap0_mm'], 'true0', res[e][n]['true_gap0_mm'], 'segs', segs, 'ours', res[e][n]['gap_mm_in_segs'], 'TRUE', res[e][n]['true_gap_mm_in_segs'], flush=True)
json.dump(res, open(OUT, 'w'))
