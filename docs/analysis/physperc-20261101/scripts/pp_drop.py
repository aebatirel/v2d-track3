"""pp_drop (GT-free inference transform): "a resting object does not float". For each object, frames where
  our hand is > HAND_MM from it, its lowest point is > FLOAT_MM above OUR table, and no other roster object supports
  it (another object's hull vertex inside its table-plane footprint, height in [bottom - 15 mm, bottom + 3 mm]);
  runs of >= MINRUN frames that are STATIC (median per-frame translation < STATIC_MM) and LOW (median gap <= CAP_MM;
  a held object whose hand MediaPipe missed is lifted much higher, D5: 54-280 mm) are lowered along OUR table normal
  so the lowest point touches the table (translation only; orientation kept), with RAMP-frame linear ramps.
Inputs: our tracks, our 9a+ meshes, our table plane, our hands. Usage: pp_drop.py SCRATCH MESHDIR TRACKS_IN OUT [EPS]"""
import itertools, json, os, sys, numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import physlib as PL
HAND_MM, FLOAT_MM, MINRUN, STATIC_MM, CAP_MM, RAMP = 50.0, 10.0, 10, 3.0, 40.0, 3
S, MD, TIN, OUT = sys.argv[1:5]
EPS = [int(x) for x in sys.argv[5:]] or [0, 2, 11, 12, 13, 18, 21, 22, 23, 24, 26, 27, 31, 39, 40, 41, 42, 43, 44, 45]
for p in (TIN, MD):
    assert 'parquet' not in p and '/t3' not in p, p
for e in EPS:
    P = dict(np.load(f'{TIN}/ep{e}/poses_world_vo.npz')); names = list(P)
    up, d = PL.table_up(S, e, P, MD); J = PL.hand_joints(S, e); T = len(P[names[0]])
    hv = {n: np.asarray(PL.mesh(f'{MD}/{n}.glb').convex_hull.vertices) for n in names}
    rec = {}
    Q = {n: P[n].copy() for n in names}
    for n in names:
        mp = f'{MD}/{n}.glb'; gap = np.zeros(T); flo = np.zeros(T, bool)
        for t in range(T):
            X = hv[n] @ P[n][t][:3, :3].T + P[n][t][:3, 3]; h = X @ up + d; gap[t] = h.min()
            c = X.mean(0); rad = np.max(np.linalg.norm((X - c) - np.outer((X - c) @ up, up), axis=1))
            sup = False
            for m in names:
                if m == n:
                    continue
                Y = hv[m] @ P[m][t][:3, :3].T + P[m][t][:3, 3]; hy = Y @ up + d
                lat = np.linalg.norm((Y - c) - np.outer((Y - c) @ up, up), axis=1)
                sup |= bool(np.any((lat < rad) & (hy > gap[t] - 0.015) & (hy < gap[t] + 0.003)))
            flo[t] = (PL.hand_dist(J, t, mp, P[n][t]) * 1000 > HAND_MM) and gap[t] * 1000 > FLOAT_MM and not sup
        sp = np.r_[np.linalg.norm(np.diff(P[n][:, :3, 3], axis=0), axis=1), 0] * 1000
        segs = []
        for k, g in itertools.groupby(range(T), key=lambda t: flo[t]):
            g = list(g)
            if k and len(g) >= MINRUN:
                a, b = g[0], g[-1]
                st, lo = float(np.median(sp[a:b])), float(np.median(gap[a:b + 1]) * 1000)
                ok = st < STATIC_MM and lo <= CAP_MM
                segs.append(dict(a=a, b=b, static_mm=round(st, 2), gap_mm=round(lo, 1), applied=ok))
                if ok:
                    for t in range(max(0, a - RAMP), min(T, b + RAMP + 1)):
                        w = 1.0 if a <= t <= b else (1 - (a - t) / (RAMP + 1) if t < a else 1 - (t - b) / (RAMP + 1))
                        gt_ = gap[min(max(t, a), b)]
                        Q[n][t][:3, 3] = P[n][t][:3, 3] - w * gt_ * up
        if segs:
            rec[n] = segs
    os.makedirs(f'{OUT}/ep{e}', exist_ok=True)
    np.savez(f'{OUT}/ep{e}/poses_world_vo.npz', **Q)
    json.dump(rec, open(f'{OUT}/ep{e}/pp_drop.json', 'w'), indent=1)
    if rec:
        print(e, json.dumps(rec), flush=True)
