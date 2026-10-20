"""Scorer impact of a 180-deg spin error of the slot-0 anchor (2-fold objects) and of slot-1 objects."""
from c11 import *
import json, sys
sys.argv = ['x']
exec(open('s3_loo.py').read().split("CUPEPS = ")[0])  # reuse metrics/spin helpers
rows = {}
for ep in [23, 24, 31, 26, 27, 18, 0, 2, 11]:
    e = load_episode(ep); p, nm = e['pose'], e['names']
    r = {}
    for j in range(len(nm)):
        ax = UP[nm[j]]
        for d in [10, 90, 180]:
            r[f"slot{j}_spin{d}"] = metrics(spin(p, j, d, ax), p, nm)
    rows[ep] = r
    print(f"== ep{ep} {e['task']} slots={nm}")
    for k, v in r.items():
        print(f"  {k:16s} " + " ".join(f"{m}={v[m]:.3f}" for m in v))
json.dump(rows, open('s6_twofold.json', 'w'), indent=1)
