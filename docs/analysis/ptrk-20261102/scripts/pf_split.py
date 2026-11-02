"""Diagnostic (reads mocap): where along the episode the per-frame error of a scored track lives.
Per object: symmetric ADD (the AUC's error) on mocap-static vs mocap-moving frames, frames with position error > 3 cm,
largest one-frame jump of the error. Usage: python -I pf_split.py RUNS_DIR TAG [TAG...] (needs t3/ep<e>.parquet)."""
import sys, json, glob, os
import numpy as np, pyarrow.parquet as pq
R = sys.argv[1]; out = {}
for tag in sys.argv[2:]:
    rows = []
    for f in sorted(glob.glob(f'{R}/runs/{tag}/ep*_pf.npz'), key=lambda p: int(p.split('/ep')[-1].split('_')[0])):
        e = int(f.split('/ep')[-1].split('_')[0]); Z = np.load(f); names = list(Z['names'])
        tab = pq.read_table(f'{R}/t3/ep{e}.parquet', columns=['observation.objects']).to_pandas()
        for s, n in enumerate(names):
            p = np.array([[o['pose'][:3] for o in r if o['name'] == n][0] for r in tab['observation.objects']])[:len(Z['frames'])]
            sp = np.r_[0, np.linalg.norm(np.diff(p, axis=0), axis=1)] * 100           # cm / frame
            mov = np.convolve(sp > 0.3, np.ones(5), 'same') > 0
            adds, pos = Z['perception_adds_cm'][:, s], Z['perception_pos_cm'][:, s]
            rows.append(dict(ep=e, obj=n, frames=len(adds), moving=int(mov.sum()),
                             adds_static=round(float(np.median(adds[~mov])) if (~mov).any() else -1, 2),
                             adds_moving=round(float(np.median(adds[mov])) if mov.any() else -1, 2),
                             gt3=int((pos > 3).sum()), jump=round(float(np.abs(np.diff(pos)).max()), 2)))
    out[tag] = rows
json.dump(out, open(f'{R}/pf_split.json', 'w'), indent=0)
for tag, rows in out.items():
    print('==', tag, 'frames>3cm total', sum(r['gt3'] for r in rows))
    for r in rows: print(r)
