"""Inference side: collect the per-episode audit.json summaries into one CSV (no ground truth)."""
import json, glob, csv, sys, os
root, out = sys.argv[1], sys.argv[2]
rows = []
for f in sorted(glob.glob(f'{root}/ep*/audit.json'), key=lambda p: int(p.split('/')[-2][2:])):
    J = json.load(open(f))
    for n, s in J['summary'].items():
        rows.append(dict(ep=int(f.split('/')[-2][2:]), obj=n, frames=s['frames'], valid=s['valid'], hidden=s['hidden'],
                         behind_mean=s['behind_mean'], behind_p50=(s['behind_p10_p50_p90'] or [None] * 3)[1],
                         behind_p90=(s['behind_p10_p50_p90'] or [None] * 3)[2], share_behind_gt_0p2=s['share_behind_gt_0p2'],
                         front_p50=(s['front_p10_p50_p90'] or [None] * 3)[1], med_r_cm_p50=(s['med_r_cm_p10_p50_p90'] or [None] * 3)[1],
                         vis_p50=(s['vis_frac_p10_p50_p90'] or [None] * 3)[1], hand_frac_mean=s['hand_frac_mean'],
                         rest_frames=s['rest_frames'], rest_h_measured=s['rest_h_measured'],
                         rest_h_cm_p50=(s['rest_h_cm_p10_p50_p90'] or [None] * 3)[1], seconds=J['seconds'],
                         selftest_identity_behind=J['selftest']['identity'][n]['behind'],
                         selftest_toward3cm_behind=round(J['selftest']['planted'][f'{n}:toward_z-3cm']['behind'], 3)))
with open(out, 'w', newline='') as fo:
    w = csv.DictWriter(fo, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
print(len(rows), 'rows')
