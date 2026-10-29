"""Summarise tools/ckpt_curve.sh output: per checkpoint, sim_vs_ref (vs our reference) and per object the max lift,
the share of frames within 3 cm of the reference path, and the frame where the object is first > 10 cm off its path
after the reference starts moving it ("lost at"). No ground truth. Usage: ckpt_curve_summary.py OUT_DIR [floor]"""
import glob, json, os, re, sys

import numpy as np
import pyarrow.parquet as pq

out = sys.argv[1]; rows = []
for d in sorted(glob.glob(f'{out}/policy_*'), key=lambda x: int(re.findall(r'\d+', os.path.basename(x))[0])):
    try:
        q = json.load(open(f'{d}/qa_policy.json')); t = pq.read_table(glob.glob(f'{d}/*.parquet')[0]).to_pandas()
    except Exception:
        continue
    row = dict(ckpt_M=round(int(re.findall(r'\d+', os.path.basename(d))[0]) / 1e6), sim_vs_ref=q['sim_vs_ref'], floor=q.get('floor_vs_ref'))
    for n, g in t.groupby('object_body_name'):
        g = g.sort_values('step'); a = g[['achieved_position_x', 'achieved_position_y', 'achieved_position_z']].values
        r = g[['reference_position_x', 'reference_position_y', 'reference_position_z']].values; e = np.linalg.norm(a - r, axis=1)
        moving = np.nonzero(np.linalg.norm(r - r[0], axis=1) > 0.03)[0]; start = int(moving[0]) if len(moving) else 0
        lost = np.nonzero(e[start:] > 0.10)[0]
        row[n] = dict(lift_cm=round(100 * float((a[:, 2] - a[0, 2]).max()), 1), ref_lift_cm=round(100 * float((r[:, 2] - r[0, 2]).max()), 1),
                      within3cm=round(float((e < 0.03).mean()), 2), moves_from=start,
                      lost_at=int(start + lost[0]) if len(lost) else None, frames=len(e))
    rows.append(row)
json.dump(rows, open(f'{out}/curve.json', 'w'), indent=1)
for r in rows:
    objs = '  '.join(f"{n[:12]}: lift {v['lift_cm']:5.1f} (ref {v['ref_lift_cm']:4.1f}) in3cm {v['within3cm']:.2f} lost@{v['lost_at']}/{v['frames']}"
                     for n, v in r.items() if isinstance(v, dict))
    print(f"{r['ckpt_M']:4d}M  sim_vs_ref {r['sim_vs_ref']:.3f}  |  {objs}")
