"""GT-free summary of what S11 did (pose_opt.json only; no mocap). Usage: python -I off_gtfree_summary.py RUNS_DIR OUT_JSON"""
import json, sys, glob, os
import numpy as np
W = sys.argv[1]; out = {}
for arm in ('Po', 'refineP'):
    for v in ('V1', 'V2', 'V3'):
        rows = []
        for f in sorted(glob.glob(f'{W}/{arm}/{v}/ep*/pose_opt.json'), key=lambda p: int(p.split('/ep')[-1].split('/')[0])):
            ep = int(f.split('/ep')[-1].split('/')[0]); s = json.load(open(f))['steps']['S11']
            for n, o in s['objects'].items():
                rows.append(dict(ep=ep, obj=n, applied=o['applied'], reason=o.get('reason'),
                                 shift_cm=(o.get('correction') or {}).get('shift_cm'), rot_deg=(o.get('correction') or {}).get('rot_deg'),
                                 frames=f'{o.get("frames_accepted")}/{o.get("frames_tried")}' if 'frames_tried' in o else None,
                                 onset=o.get('onset')))
        ap = [r for r in rows if r['applied']]
        out[f'{arm}_{v}'] = dict(objects=len(rows), applied=len(ap),
                                 shift_cm_median=round(float(np.median([r['shift_cm'] for r in ap])), 3) if ap else None,
                                 rot_deg_median=round(float(np.median([r['rot_deg'] for r in ap])), 3) if ap else None,
                                 shift_cm_max=max([r['shift_cm'] for r in ap], default=None), rot_deg_max=max([r['rot_deg'] for r in ap], default=None),
                                 rejected={k: sum(1 for r in rows if not r['applied'] and (r['reason'] or '').startswith(k))
                                           for k in ('rotation spread', 'shift spread', 'few points', 'residual', 'change', 'consensus', 'icp', '0 accepted')},
                                 rows=rows)
        print(arm, v, {k: out[f'{arm}_{v}'][k] for k in ('objects', 'applied', 'shift_cm_median', 'rot_deg_median', 'shift_cm_max', 'rot_deg_max', 'rejected')})
json.dump(out, open(sys.argv[2], 'w'), indent=1)
