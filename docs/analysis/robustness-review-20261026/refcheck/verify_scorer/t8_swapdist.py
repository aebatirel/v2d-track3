"""verify_scorer test 8: distribution of the pitcher swap (library_v3 -> library_v3p) on the ep21 twin rollout r1
(a) over 30 consecutive registration seeds from the twin's own seed (offset 0..29), full host;
(b) at Kaggle's eval-20 seeds (offset -1_000_003) over 24 stand-in hosts (quadric and vertex-clustering decimations).
Only the submitted pitcher mesh changes; the rollout is the same. Own scorer (vs_core). Public mocap used for scoring only.
Usage: python -I t8_swapdist.py OUT.json"""
import json, sys, time
sys.path.insert(0, '/home/user/v2d-track3/docs/analysis/robustness-review-20261026/refcheck/verify_scorer')
import numpy as np
from vs_core import *

ep = 21
SUBP = 'runs/20261025-twin21arc-ee7ba8e/results/glock_public/ep21/best/r1'
names, G = load_gt(ep)
rn, X, ref, steps, rf, md = load_rollout(f'{STORE}/{SUBP}/episode_{ep:06d}.parquet')
assert rn == names == ['blue_cup', 'water_pitcher']
C = {L: [budget(f'{LIB}/{L}/{n}.glb') for n in names] for L in ('library_v3', 'library_v3p')}
res = dict(rollout=SUBP, seeds={}, eval_hosts={})


def one(Hs, off):
    s0 = 1_000_003 * ep + off
    cup = register(C['library_v3'][0], Hs[0], s0)
    out = {}
    for L in ('library_v3', 'library_v3p'):
        pit = register(C[L][1], Hs[1], s0 + 101)
        r = my_score(X, G, Hs, [cup, pit])
        out[L] = dict(AUC=round(r['AUC'], 4), pit_deg=round(reg_angle(pit[1]), 2),
                      pit_yaw=round(float(Rot.from_matrix(pit[1]).as_euler('ZYX', degrees=True)[0]), 2))
    out['d'] = round(out['library_v3p']['AUC'] - out['library_v3']['AUC'], 4)
    return out


t0 = time.time()
Hfull = [host(n, s) for s, n in enumerate(names)]
for off in range(30):
    res['seeds'][off] = one(Hfull, off)
    print('seed', off, res['seeds'][off], flush=True)
specs = [(0, 'fs')] + [(k, 'fs') for k in (60000, 50000, 40000, 30000, 25000, 20000, 16000, 14000, 12000, 10000, 8192,
                                           6000, 5000, 4096, 3000, 2500, 2000)] + [(k, 'cluster') for k in (50000, 20000, 8000, 4096)]
for k, dec in specs:
    Hs = [host(n, s, faces=k, weld_dec=dec) for s, n in enumerate(names)]
    key = f'{"vc" if dec == "cluster" else "qd"}{k}' if k else 'full'
    res['eval_hosts'][key] = one(Hs, -1_000_003)
    print('evalhost', key, res['eval_hosts'][key], flush=True)
    json.dump(res, open(sys.argv[1], 'w'), indent=1)
ds = np.array([v['d'] for v in res['seeds'].values()]); dh = np.array([v['d'] for v in res['eval_hosts'].values()])
res['summary'] = dict(seed_d_mean=round(float(ds.mean()), 4), seed_d_median=round(float(np.median(ds)), 4),
                      seed_n_neg=int((ds < 0).sum()), seed_n_lt_m02=int((ds < -0.2).sum()), n_seeds=len(ds),
                      evalhost_d_mean=round(float(dh.mean()), 4), evalhost_d_median=round(float(np.median(dh)), 4),
                      evalhost_n_neg=int((dh < 0).sum()), evalhost_n_lt_m02=int((dh < -0.2).sum()), n_hosts=len(dh),
                      seconds=round(time.time() - t0, 1))
json.dump(res, open(sys.argv[1], 'w'), indent=1)
print(res['summary'])
