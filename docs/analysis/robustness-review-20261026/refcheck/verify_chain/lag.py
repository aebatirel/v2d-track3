"""Frame-indexing check without any alignment (refcheck/verify_chain; DIAGNOSTIC: reads public mocap after inference).

For every object of every canonical perception run, the per-frame speed of the object's surface centroid and its
angular speed are rigid-frame invariant, so they can be compared between perception and mocap without the scorer's
frame-0 alignment. The cross-correlation of perceived vs mocap speed over lags -3..+3 frames should peak at lag 0 if
perception frame t is mocap row t. lag > 0 means perception frame t + lag matches mocap row t (perception late).
Also scores the speed-weighted RMS difference at each lag.
Usage: python -I lag.py OUT.json
"""
import json, os, sys
import numpy as np, trimesh, pyarrow.parquet as pq
from scipy.spatial.transform import Rotation as Rot

SP = '/tmp/claude-0/-home-user-v2d-track3/12630086-0942-582d-80bb-a9806af3e32b/scratchpad/refcheck'
ST = f'{SP}/store'; T3 = f'{SP}/t3'
C = json.load(open(f'{SP}/work/canonical_refs.json'))['episodes']
LAGS = range(-3, 4)
out = {}
runs = [(e['ep'], e['perception_path']) for e in C if e['ref_path']]
runs += [(e['ep'], e['newest_perception_path']) for e in C if not e['ref_path']]
for ep, pth in runs:
    tab = pq.read_table(f'{T3}/ep{ep}.parquet', columns=['observation.objects']).to_pandas()
    names = [o['name'] for o in tab['observation.objects'].iloc[0]]
    P = np.load(f'{ST}/{pth}')
    r = {}
    for n in names:
        q = f'{T3}/mesh/{n}/{n}.glb'; q = q if os.path.exists(q) else f'{T3}/mesh/{n}/{n}_visual.glb'
        c = np.asarray(trimesh.load(q, force='mesh').vertices).mean(0)
        G = np.array([[o['pose'] for o in row if o['name'] == n][0] for row in tab['observation.objects']], float)
        Rg = Rot.from_quat(G[:, [4, 5, 6, 3]]); pg = G[:, :3] + Rg.apply(c)
        Rp = Rot.from_matrix(P[n][:, :3, :3]); pp = P[n][:, :3, 3] + Rp.apply(c)
        vg = np.linalg.norm(np.diff(pg, axis=0), axis=1); vp = np.linalg.norm(np.diff(pp, axis=0), axis=1)
        wg = (Rg[1:] * Rg[:-1].inv()).magnitude(); wp = (Rp[1:] * Rp[:-1].inv()).magnitude()
        res = {}
        for name, a, b in (('lin', vp, vg), ('ang', wp, wg)):
            cc = {}
            for k in LAGS:      # compare perception[t + k] with mocap[t]
                if k >= 0:
                    x, y = a[k:], b[:len(b) - k]
                else:
                    x, y = a[:len(a) + k], b[-k:]
                cc[k] = float(np.corrcoef(x, y)[0, 1]) if x.std() > 0 and y.std() > 0 else float('nan')
            best = max(cc, key=lambda k: cc[k] if np.isfinite(cc[k]) else -9)
            res[name] = dict(best_lag=int(best), corr={str(k): round(v, 4) for k, v in cc.items()})
        res['gt_travel_cm'] = round(float(vg.sum() * 100), 1)
        r[n] = res
    out[ep] = dict(path=pth, objects=r)
    print(ep, {n: (v['lin']['best_lag'], v['lin']['corr']['0'], v['lin']['corr'][str(v['lin']['best_lag'])], v['ang']['best_lag'], v['gt_travel_cm'])
               for n, v in r.items()}, flush=True)
json.dump(out, open(sys.argv[1], 'w'), indent=1)
