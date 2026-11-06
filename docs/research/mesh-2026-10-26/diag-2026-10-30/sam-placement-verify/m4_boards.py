"""M4 [D]: board identity / chirality checks.
(a) our observed points (ep23, ep24) vs board-1 and board-2 scans: rigid multi-start ICP, residuals and rotation from
    identity of the best and the 180-deg alternative.
(b) SAM board meshes vs both scans and the mirrored scans: shape match after the best similarity (which board, which
    chirality did SAM generate?)."""
import numpy as np
from vlib import *
from scipy.spatial import cKDTree
scans = {o: load_scan(o) for o in ('wooden_piece_1', 'wooden_piece_2')}
B = {o: sample(*scans[o], 6000, 21) for o in scans}
print('(a) observed points -> scan, rigid, symmetric-trim not used: one-sided obs->scan trimmed 90%')
def one_sided_rigid(O, Bs, T0, iters=60):
    s, R, t = T0; tb = cKDTree(Bs)
    for _ in range(iters):
        X = O @ R.T + t; d, i = tb.query(X); k = d <= np.quantile(d, 0.9)
        _, R, t = umeyama(O[k], Bs[i[k]], scale=False)
    d = tb.query(O @ R.T + t)[0]
    return (1.0, R, t), float(np.sort(d)[:int(0.9 * len(d))].mean()), float(np.mean(d < 0.002))
for ep in (23, 24):
    for o in ('wooden_piece_1', 'wooden_piece_2'):
        f = f'{SCR}/obs_all/ep{ep}_{o}.npz'
        P = np.load(f)['pts']; rng = np.random.default_rng(0); O = P[rng.choice(len(P), min(8000, len(P)), replace=False)]
        for so in B:
            ca, Va, _ = pca_frame(O); cb, Vb, _ = pca_frame(B[so])
            starts = [(1.0, np.eye(3), np.zeros(3))] + [(1.0, Vb @ M @ Va.T, cb - Vb @ M @ Va.T @ ca) for M in cube_rots()]
            res = sorted([one_sided_rigid(O, B[so], T0) for T0 in starts], key=lambda r: r[1])
            best = res[0]; alt = [r for r in res if rot_angle(r[0][1] @ best[0][1].T) > 90]
            idr = one_sided_rigid(O, B[so], starts[0])
            print(f'ep{ep} pts labelled {o:15s} -> scan {so:15s}: best trim {best[1]*1e3:5.2f} mm, within2mm {best[2]:.2f}, rot from identity {rot_angle(best[0][1]):6.1f} deg | '
                  f'local-from-identity {idr[1]*1e3:5.2f} mm ({rot_angle(idr[0][1]):5.1f} deg, in2mm {idr[2]:.2f}) | best >90deg-away alt {alt[0][1]*1e3 if alt else float("nan"):5.2f} mm ({rot_angle(alt[0][0][1]) if alt else float("nan"):5.1f} deg)', flush=True)
print('(b) SAM raw board meshes vs scans (similarity, symmetric trimmed 90%)')
for o in ('wooden_piece_1', 'wooden_piece_2'):
    for seed in (42, 7):
        v, f = load(f'{GEN}/sam3d/{o}_{"k27" if o=="wooden_piece_1" else "k6"}_s{seed}.ply')
        A = sample(v, f, 5000, 31)
        row = []
        for so in B:
            for mir in (False, True):
                Bs = B[so] * (np.array([-1, 1, 1]) if mir else 1)
                tr = multi_start(A, Bs, scale=True, include_identity=False)[0]
                row.append(f'{so[-1]}{"m" if mir else " "} {tr*1e3:5.2f}')
        print(f'SAM {o} s{seed}: trimmed sym dist mm to scan b1 / b1-mirror / b2 / b2-mirror: ' + ' | '.join(row), flush=True)
