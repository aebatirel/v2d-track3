"""verify_scorer test 6: physical check of the GT quaternion order. Place each public scan by its frame-0 GT pose read as
w-first (x,y,z,qw,qx,qy,qz -> scipy xyzw) and, as a control, read as if it were x-first; at rest the lowest scan point
must sit on the table (~0.61 m) for every object. Usage: python -I t6_quat.py OUT.json EP..."""
import json, sys
sys.path.insert(0, '/home/user/v2d-track3/docs/analysis/robustness-review-20261026/refcheck/verify_scorer')
import numpy as np, pyarrow.parquet as pq
from vs_core import *
out = {}
for ep in map(int, sys.argv[2:]):
    tab = pq.read_table(f'{T3D}/ep{ep}.parquet', columns=['observation.objects']).to_pandas()
    r = {}
    for o in tab['observation.objects'].iloc[0]:
        n = str(o['name']); x = np.asarray(o['pose'], float)
        v, f = load_vf(scan_path(n))
        wfirst = Rot.from_quat(np.r_[x[4:7], x[3]]).apply(v) + x[:3]
        xfirst = Rot.from_quat(x[3:7]).apply(v) + x[:3]
        r[n] = dict(minz_wfirst=round(float(wfirst[:, 2].min()), 4), minz_xfirst=round(float(xfirst[:, 2].min()), 4),
                    scan_extent_z=round(float(np.ptp(v[:, 2])), 3))
    out[ep] = r
    print(ep, r, flush=True)
json.dump(out, open(sys.argv[1], 'w'), indent=1)
