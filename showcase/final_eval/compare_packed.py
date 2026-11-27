"""How faithful is a fresh CPU replay to the rollout we actually submitted? Compares the replay's object poses with the
packed rows of the final pack (14p), frame by frame. Both are our own outputs; no ground truth is read.
  compare_packed.py [--out /content/ev] [--pack PARQUET] [--json OUT.json]
Per episode and object: mean / p95 / max centre distance (cm), mean rotation difference (deg), share of frames within
2 cm. Slot k of the pack = the k-th object of the reference (checked: the other order is also scored and reported).
"""
import argparse, glob, json, os

import numpy as np
import pyarrow.parquet as pq
from scipy.spatial.transform import Rotation as R

HERE = os.path.dirname(os.path.abspath(__file__)); REPO = os.path.dirname(os.path.dirname(HERE))
p = argparse.ArgumentParser(); p.add_argument('--out', default='/content/ev')
p.add_argument('--pack', default=f'{REPO}/results/submissions/20261102-track3s-candidate/build_14p/track3_submission.parquet')
p.add_argument('--json', default=''); p.add_argument('--trace', default='replay_cpu.npz'); a = p.parse_args()
t = pq.read_table(a.pack, columns=['row_id', 'pos_x', 'pos_y', 'pos_z', 'quat_x', 'quat_y', 'quat_z', 'quat_w']).to_pandas()
t['ep'] = t.row_id.str.extract(r'e0*(\d+)/')[0].astype(int); t['f'] = t.row_id.str.extract(r'/f0*(\d+)/')[0].fillna(0).astype(int)
t['o'] = t.row_id.str.extract(r'/o(\d+)$')[0].astype(int)
res = {}
for D in sorted(glob.glob(f'{a.out}/ep*'), key=lambda x: int(x.split('ep')[-1])):
    ep = int(D.split('ep')[-1]); tr = f'{D}/{a.trace}'
    if not os.path.exists(tr):
        continue
    s = json.load(open(f'{D}/setup.json')); d = np.load(tr); Q = d['q']; fr = d['frame']; L = [str(x) for x in d['labels']]
    keep = np.r_[True, np.diff(fr) > 0]                     # drop the final auto-reset row (frame jumps back to 0)
    Q, fr = Q[keep], fr[keep]
    pk = t[t.ep == ep]; F = int(pk.f.max()) + 1; nob = int(pk.o.max()) + 1
    P = np.zeros((nob, F, 7))
    for o in range(nob):
        x = pk[pk.o == o].sort_values('f'); P[o, x.f.to_numpy()] = x[['pos_x', 'pos_y', 'pos_z', 'quat_x', 'quat_y', 'quat_z', 'quat_w']].to_numpy()
    n = min(F, len(fr)); idx = {int(f): i for i, f in enumerate(fr)}
    rows = [idx[f] for f in range(n)]
    out = {'frames_packed': F, 'frames_replay': int(len(fr)), 'objects': {}}
    for k, name in enumerate(s['objects']):
        bi = [i for i, l in enumerate(L) if l.split('/')[0] == f'track3_{name}'][0]
        Y = Q[rows, bi]
        best = None
        for o in range(nob):                                 # expected slot k; the other order is checked too
            dpos = np.linalg.norm(Y[:, :3] - P[o, :n, :3], axis=1) * 100
            drot = np.degrees((R.from_quat(Y[:, 3:]).inv() * R.from_quat(P[o, :n, 3:])).magnitude())
            r = dict(slot=o, mean_cm=float(dpos.mean()), p95_cm=float(np.percentile(dpos, 95)), max_cm=float(dpos.max()),
                     rot_mean_deg=float(drot.mean()), within_2cm=float((dpos < 2).mean()), first_gt5cm=int(np.argmax(dpos > 5)) if (dpos > 5).any() else -1)
            if best is None or r['mean_cm'] < best['mean_cm']:
                best = r
        best['slot_matches_order'] = best['slot'] == k
        out['objects'][name] = best
    res[ep] = out
    print(f'eval {ep:2d}: ' + '; '.join(f"{n} mean {v['mean_cm']:.2f} p95 {v['p95_cm']:.2f} max {v['max_cm']:.1f} cm, rot {v['rot_mean_deg']:.1f} deg, "
                                       f"<2cm {v['within_2cm'] * 100:.0f}%{'' if v['slot_matches_order'] else ' (SLOT ORDER DIFFERS)'}"
                                       f"{'' if v['first_gt5cm'] < 0 else ', >5cm from f' + str(v['first_gt5cm'])}" for n, v in out['objects'].items()), flush=True)
if a.json:
    json.dump(res, open(a.json, 'w'), indent=1)
