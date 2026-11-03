"""DIAGNOSTIC (reads mocap; never used by inference): where along each public episode does the control track lose AUC?
Held (moving) frames per object from mocap: a frame is STATIC when, within +-W frames, the object stays within POS_MM
and ROT_DEG of its pose at that frame; MOVING = not static; HELD = MOVING dilated by DIL frames (grasp / release).
Per object: frames held, median symmetric ADD (cm) held vs rest, and the share of the AUC loss (1 - AUC) from held frames.
Usage: held_diag.py T3 PF_DIR TAG [EPS...]  (PF_DIR/<TAG>_ep<e>_pf.npz from score_registered.py --per_frame)"""
import sys, json, numpy as np, pyarrow.parquet as pq
from scipy.spatial.transform import Rotation as Rot
W, POS_MM, ROT_DEG, DIL = 10, 5.0, 3.0, 8
TH = np.arange(1, 10); WT = np.r_[0.5, np.ones(7), 0.5] / 8   # kit: thresholds 1..9 cm, trapezoid on [0, 1]
T3, PF, TAG = sys.argv[1:4]
EPS = [int(x) for x in sys.argv[4:]] or [0, 2, 11, 12, 13, 18, 21, 22, 23, 24, 26, 27, 31, 39, 40, 41, 42, 43, 44, 45]


def held_mask(P, Q):
    T = len(P); moving = np.zeros(T, bool); R = Rot.from_quat(Q)
    for t in range(T):
        a, b = max(0, t - W), min(T, t + W + 1)
        dp = np.linalg.norm(P[a:b] - P[t], axis=1).max() * 1000
        dr = np.degrees((R[a:b] * R[t].inv()).magnitude()).max()
        moving[t] = dp > POS_MM or dr > ROT_DEG
    held = moving.copy()
    for t in np.nonzero(moving)[0]:
        held[max(0, t - DIL):t + DIL + 1] = True
    return held


def runs(m):
    d = np.diff(np.r_[0, m.astype(int), 0]); return list(zip(np.nonzero(d == 1)[0].tolist(), np.nonzero(d == -1)[0].tolist()))


out = {}
for e in EPS:
    tab = pq.read_table(f'{T3}/ep{e}.parquet').to_pandas()
    names = [o['name'] for o in tab['observation.objects'].iloc[0]]
    z = np.load(f'{PF}/{TAG}_ep{e}_pf.npz'); fr = z['frames']; A = z['perception_adds_cm']
    for s, n in enumerate(names):
        G = np.array([[o['pose'] for o in tab['observation.objects'].iloc[f] if o['name'] == n][0] for f in fr], float)
        h = held_mask(G[:, :3], G[:, [4, 5, 6, 3]])
        a = A[:, s]; loss = (a[:, None] >= TH).astype(float) @ WT        # exact per-frame share of the kit AUC loss (1-9 cm, trapezoid)
        out[f'{e}:{n}'] = dict(ep=e, obj=n, frames=len(fr), held=int(h.sum()), held_runs=runs(h),
                               med_held=round(float(np.median(a[h])), 2) if h.any() else None,
                               med_rest=round(float(np.median(a[~h])), 2) if (~h).any() else None,
                               auc=round(1 - float(loss.mean()), 4),
                               loss_held=round(float(loss[h].sum() / len(a)), 4), loss_rest=round(float(loss[~h].sum() / len(a)), 4),
                               gt5_held=int((a[h] > 5).sum()), gt1_held=int((a[h] > 1).sum()), gt1_rest=int((a[~h] > 1).sum()))
for k, r in out.items():
    print(f"ep{r['ep']:2d} {r['obj']:18s} held {r['held']:3d}/{r['frames']:3d} medADD held {r['med_held']} rest {r['med_rest']} "
          f"AUC {r['auc']} loss held {r['loss_held']} rest {r['loss_rest']}   >1cm held {r['gt1_held']} rest {r['gt1_rest']}  >5cm held {r['gt5_held']} runs {r['held_runs']}")
L = np.array([[r['loss_held'], r['loss_rest']] for r in out.values()])
print('total loss share held', round(L[:, 0].sum() / L.sum(), 3), 'sum held', round(L[:, 0].sum(), 3), 'sum rest', round(L[:, 1].sum(), 3))
json.dump(out, open(f'{PF}/held_diag_{TAG}.json', 'w'), indent=1)
