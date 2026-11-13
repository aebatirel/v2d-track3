#!/usr/bin/env python3
"""Public calibration of the depth flag D (diagnostic side: joins the 30 Oct perception-mode depth audit with its
public mocap labels, docs/research/work/depth-audit-20261030/calib_gt/v2/per_frame.csv). Public only.
Usage: python3 calib_depth_pub.py PER_FRAME.csv OUT.json"""
import json, sys
import pandas as pd

d = pd.read_csv(sys.argv[1])
d['bad'] = (d.hidden == 1) | ((d.valid == 1) & ((d.behind > 0.2) | (d.front > 0.5)))


def maxrun(x):
    m = r = 0
    for v in x:
        r = r + 1 if v else 0
        m = max(m, r)
    return m


rows = []
for (e, o), g in d.groupby(['ep', 'obj']):
    g = g.sort_values('frame')
    rows.append(dict(ep=int(e), obj=o, frames=len(g), gross_share_glob5=round(float((g.adds_glob_cm > 5).mean()), 3),
                     gross_share_kit5=round(float((g.adds_cm > 5).mean()), 3), depth_bad_share=round(float(g.bad.mean()), 3),
                     depth_bad_run=maxrun(g.bad.values), hidden_share=round(float(g.hidden.mean()), 3)))
json.dump(dict(source=sys.argv[1], rule='bad = hidden | valid & (behind > 0.2 | front > 0.5)', objects=rows),
          open(sys.argv[2], 'w'), indent=1)
print(pd.DataFrame(rows).sort_values('depth_bad_share', ascending=False).head(8).to_string())
