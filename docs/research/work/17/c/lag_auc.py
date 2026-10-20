"""Stage C (resume), GT-only: AUC cost of a pure time lag. A perfect tracker whose pose for video frame t is reported at
GT row t, while b/c frame t actually shows GT row t - 0.5 (B7/B19), has ADD(t) = ADD(GT(t), GT(t - L)) with L = 0.5.
Also L = 1.35 / 2.4 (cam-a frames used without the per-episode delta: ~1.1 + 0.25, ~2.14 + 0.25) and L = 1.0.
Per object: ADD over 3000 mesh vertices, kit AUC (1-9 cm). No scorer anchor needed (lag has no constant part).
usage: c/lag_auc.py ep [ep ...]"""
import sys, numpy as np
sys.path.insert(0, '/Users/aebatirel/Documents/Code/v2d-research/work/17'); sys.path.insert(0, '/Users/aebatirel/Documents/Code/v2d-research/work/17/c')
import ev17 as E, lib17 as L, det17lib as D
LAGS = [0.5, 1.0, 1.35, 2.4]; rows = []
for ep in [int(x) for x in sys.argv[1:]]:
    gt = L.load_gt(ep); T = len(gt['t'])
    for j, n in enumerate(gt['names']):
        try: V = E.verts(n)
        except Exception: continue
        res = []
        for lag in LAGS:
            ea = np.zeros(T)
            for t in range(T):
                R1, t1 = gt['R'][t, j], gt['t'][t, j]; R2, t2 = D.gt_interp(gt, j, t - lag)
                ea[t] = np.linalg.norm(V @ (R1 - R2).T + (t1 - t2), axis=1).mean() * 1000
            res.append((E.auc_add(ea), np.percentile(ea, 95), ea.max()))
        rows.append((ep, n, res)); print(ep, n, ' | '.join(f'L{l}: AUC {a:.3f} p95 {p:.1f} max {m:.0f} mm' for l, (a, p, m) in zip(LAGS, res)), flush=True)
A = np.array([[r[0] for r in res] for _, _, res in rows]); print('MEAN over', len(rows), 'objects: ' + ' '.join(f'L{l} {1 - a:.4f} loss' for l, a in zip(LAGS, A.mean(0))))
