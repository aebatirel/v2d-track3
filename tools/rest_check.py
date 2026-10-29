"""Physical check of the resting poses (2026-10-23; owner: "make sure it starts stable"; pipeline/support_fill.py makes
the meshes stand statically, this checks it in the simulator). From a zero-action rollout trace (tools/trace_rollout.py:
the policy adds nothing, the hands follow the reference), every object must stay where it started until a hand comes
for it: largest displacement / rotation from its simulated frame-0 pose over frames 0 .. (its first hold start - LEAD);
an object no hand holds (a rack) is checked until the first hold of any object - LEAD (something may be placed into
it later: public ep12 / ep27).
PASS when within MM mm and DEG deg. Our reference only (hold phases from our MANO contacts); no ground truth.
Usage: rest_check.py TRACE.npz REF.parquet [--mm 5] [--deg 2] [--lead 6]   (prints JSON; exit 0 even on FAIL)
"""
import argparse, json, os, sys

import numpy as np
from scipy.spatial.transform import Rotation as R

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'pipeline'))
from hold_phases import hold_phases  # noqa: E402

p = argparse.ArgumentParser(); p.add_argument('trace'); p.add_argument('ref')
p.add_argument('--mm', type=float, default=5.0); p.add_argument('--deg', type=float, default=2.0); p.add_argument('--lead', type=int, default=6)
a = p.parse_args()
d = np.load(a.trace); Q = d['q']; L = [str(x) for x in d['labels']]; ph = hold_phases(a.ref)[0]['phases']; out = {}
for i, l in enumerate(L):
    if not (l.startswith('track3_') and l.endswith('/object')):
        continue
    n = l[len('track3_'):-len('/object')]
    first = min((x['start'] for x in ph if x['object'] == n), default=min((x['start'] for x in ph), default=len(Q)))
    end = max(1, min(len(Q), first - a.lead))
    dp = 1000 * np.linalg.norm(Q[:end, i, :3] - Q[0, i, :3], axis=1)
    dr = np.degrees((R.from_quat(Q[:end, i, 3:7]) * R.from_quat(Q[0, i, 3:7]).inv()).magnitude())
    out[n] = dict(until_frame=int(end), max_mm=round(float(dp.max()), 1), max_deg=round(float(dr.max()), 1),
                  worst_frame=int(np.argmax(dp)), ok=bool(dp.max() <= a.mm and dr.max() <= a.deg))
print(json.dumps(dict(all_ok=all(v['ok'] for v in out.values()), mm=a.mm, deg=a.deg, objects=out)))
