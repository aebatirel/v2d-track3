"""Diagnostic oracle (reads mocap): upper bound of fixing only REST frames. Per object, frames where mocap moves
< 0.3 cm/frame (5-frame dilation of motion) get symmetric ADD 0 (perfect), others keep the track's error; AUC via the
kit's _add_auc over the episode's objects. Also 'rest frames set to the segment-median error' is NOT modelled.
Usage: python -I rest_oracle.py SCRATCH TAG"""
import sys, glob, json, numpy as np, pyarrow.parquet as pq
S, tag = sys.argv[1:3]
sys.path.insert(0, f'{S}/kit/v2d_submission_kit/metric_code/track_3'); import AUC as A
out = []
for f in sorted(glob.glob(f'{S}/runs/{tag}/ep*_pf.npz')):
    e = int(f.split('/ep')[-1].split('_')[0]); Z = np.load(f); names = list(Z['names']); adds = Z['perception_adds_cm'] / 100
    tab = pq.read_table(f'{S}/t3/ep{e}.parquet', columns=['observation.objects']).to_pandas()
    fixed = adds.copy(); restshare = []
    for s, n in enumerate(names):
        p = np.array([[o['pose'][:3] for o in r if o['name'] == n][0] for r in tab['observation.objects']])[:len(adds)]
        sp = np.r_[0, np.linalg.norm(np.diff(p, axis=0), axis=1)] * 100
        mov = np.convolve(sp > 0.3, np.ones(5), 'same') > 0
        fixed[~mov, s] = 0; restshare.append(float((~mov).mean()))
    a0 = float(A._add_auc(adds[:, None])); a1 = float(A._add_auc(fixed[:, None]))
    out.append(dict(ep=e, auc_track=round(a0, 4), auc_rest_perfect=round(a1, 4), gain=round(a1 - a0, 4), rest_share=np.round(restshare, 2).tolist()))
    print(out[-1])
print('mean gain', round(np.mean([o['gain'] for o in out]), 4), 'n', len(out))
json.dump(out, open(f'{S}/rest_oracle_{tag}.json', 'w'), indent=0)
