"""qa_physics (GT-free QA, flags only; changes nothing): physically impossible object tracks.
Per object (our tracks, 9a+ meshes, our table plane, our hands):
  PEN  : lowest point < PEN_MM below our table for >= 5 frames while no hand within 50 mm
         (mesh base errors explain at most ~ -20 mm: D1 worst legit f0 gap -18 mm);
  FLOAT: the pp_drop rule (static, low, unsupported, no hand) -> would be dropped;
  JUMP : one-frame translation > JUMP_MM or rotation > JUMP_DEG with no hand within 100 mm (or no hand detected).
Usage: qa_physics.py SCRATCH MESHDIR TRACKS OUT_JSON [EPS]"""
import itertools, json, os, sys, numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import physlib as PL
PEN_MM, JUMP_MM, JUMP_DEG = 30.0, 30.0, 20.0
S, MD, TR, OUT = sys.argv[1:5]
EPS = [int(x) for x in sys.argv[5:]] or [0, 2, 11, 12, 13, 18, 21, 22, 23, 24, 26, 27, 31, 39, 40, 41, 42, 43, 44, 45]
res = {}
for e in EPS:
    P = dict(np.load(f'{TR}/ep{e}/poses_world_vo.npz')); names = list(P)
    up, d = PL.table_up(S, e, P, MD); J = PL.hand_joints(S, e); T = len(P[names[0]])
    res[e] = {}
    for n in names:
        mp = f'{MD}/{n}.glb'; hv = np.asarray(PL.mesh(mp).convex_hull.vertices)
        gap = np.array([((hv @ P[n][t][:3, :3].T + P[n][t][:3, 3]) @ up + d).min() for t in range(T)]) * 1000
        hd = np.array([PL.hand_dist(J, t, mp, P[n][t]) for t in range(T)]) * 1000
        pen = (gap < -PEN_MM) & (hd > 50)
        fl = []
        for k, g in itertools.groupby(range(T), key=lambda t: pen[t]):
            g = list(g)
            if k and len(g) >= 5:
                fl.append(dict(kind='PEN', a=g[0], b=g[-1], gap_mm=round(float(np.median(gap[g])), 1)))
        dp = np.linalg.norm(np.diff(P[n][:, :3, 3], axis=0), axis=1) * 1000
        dr = np.degrees([np.arccos(np.clip((np.trace(P[n][t][:3, :3].T @ P[n][t + 1][:3, :3]) - 1) / 2, -1, 1)) for t in range(T - 1)])
        for t in np.where(((dp > JUMP_MM) | (dr > JUMP_DEG)) & (np.minimum(hd[:-1], hd[1:]) > 100))[0]:
            fl.append(dict(kind='JUMP', a=int(t), b=int(t + 1), mm=round(float(dp[t]), 1), deg=round(float(dr[t]), 1)))
        res[e][n] = dict(flags=fl, frac_pen=round(float(pen.mean()), 3))
        if fl:
            print(e, n, f'pen {pen.mean():.2f}', fl[:4], '...' if len(fl) > 4 else '', flush=True)
for e, o in res.items():
    for n, r in o.items():
        drop = json.load(open(f'{S}/out/F1/ep{e}/pp_drop.json')).get(n, []) if os.path.exists(f'{S}/out/F1/ep{e}/pp_drop.json') else []
        r['flags'] += [dict(kind='FLOAT', a=s['a'], b=s['b'], gap_mm=s['gap_mm']) for s in drop if s['applied']]
json.dump(res, open(OUT, 'w'), indent=1)
