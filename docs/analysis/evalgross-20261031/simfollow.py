#!/usr/bin/env python3
"""Does the packed rollout follow the reference inside the flagged windows? Mean |achieved - reference| position of
the object (cm) inside vs outside each window, from the evaluator output parquets (our rollout and our reference
only; no ground truth). Usage: python3 simfollow.py PACK6_RESULTS_DIR C33B_RESULTS_DIR OUT.json"""
import json, sys
import numpy as np
import pyarrow.parquet as pq

base, b33, outp = sys.argv[1:4]
W = {(32, 'blue_cup'): [(21, 34)], (14, 'blue_cup'): [(35, 46)], (33, 'blue_cup'): [(46, 91)],
     (32, 'wooden_spoon'): [(91, 117), (199, 221)], (33, 'wooden_spoon'): [(251, 282), (183, 217)],
     (3, 'white_pot'): [(81, 231)], (6, 'white_pot'): [(51, 135)], (8, 'beige_cup'): [(94, 103)],
     (20, 'blue_cup'): [(83, 123)], (28, 'white_pot'): [(171, 219)], (25, 'wooden_piece_1'): [(36, 118)],
     (30, 'plastic_dish_rack'): [(74, 169)], (19, 'mini_sweeper'): [(43, 98)]}
out = []
for (ep, obj), wins in W.items():
    t = pq.read_table((b33 if ep == 33 else base) + f'/episode_{ep:06d}.parquet').to_pandas()
    g = t[t.object_body_name == obj].sort_values('step')
    a = g[[f'achieved_position_{k}' for k in 'xyz']].values; r = g[[f'reference_position_{k}' for k in 'xyz']].values
    fr = g.reference_frame.values; e = np.linalg.norm(a - r, axis=1) * 100
    for s0, s1 in wins:
        m = (fr >= s0) & (fr < s1)
        out.append(dict(ep=ep, obj=obj, window=[s0, s1], sim_minus_ref_cm_in=round(float(e[m].mean()), 1),
                        sim_minus_ref_cm_out=round(float(e[~m].mean()), 1), sim_minus_ref_cm_max_in=round(float(e[m].max()), 1)))
        print(out[-1])
json.dump(out, open(outp, 'w'), indent=1)
