#!/usr/bin/env python3
"""Flag D of PREREG (block 1) on the eval depth audits (inference side only: our audit.npz files).
bad = hidden | valid & (behind > 0.2 | front > 0.5); flag if bad share >= 0.25 or longest bad run >= 50 frames.
Usage: python3 depth_summ.py DEPTH_ROOT OUT.json   (DEPTH_ROOT/{perc,ref}/ep<N>/audit.npz)"""
import json
import os
import sys

import numpy as np

root, out = sys.argv[1:3]
res = []


def runs(x):
    r, best, cur, start = [], (0, -1), 0, 0
    for i, v in enumerate(x):
        if v:
            if cur == 0:
                start = i
            cur += 1
            if cur > best[0]:
                best = (cur, start)
        else:
            if cur >= 5:
                r.append((start, start + cur - 1))
            cur = 0
    if cur >= 5:
        r.append((start, start + cur - 1))
    return best, r


for mode in ('perc', 'ref'):
    d = os.path.join(root, mode)
    if not os.path.isdir(d):
        continue
    for ep in sorted(os.listdir(d), key=lambda s: int(s[2:])):
        f = os.path.join(d, ep, 'audit.npz')
        if not os.path.exists(f):
            continue
        z = np.load(f)
        names = [str(x) for x in z['names']]
        for b, nm in enumerate(names):
            hid = z['hidden'][:, b].astype(bool); val = z['valid'][:, b].astype(bool)
            beh = np.nan_to_num(z['behind'][:, b]); fr = np.nan_to_num(z['front'][:, b])
            bad = hid | (val & ((beh > 0.2) | (fr > 0.5)))
            (L, s0), segs = runs(bad)
            share = float(bad.mean())
            res.append(dict(mode=mode, ep=int(ep[2:]), obj=nm, T=int(len(bad)), bad_share=round(share, 3),
                            longest_run=int(L), longest_run_start=int(s0), runs_ge5=segs,
                            hidden_share=round(float(hid.mean()), 3),
                            behind_gt02_share=round(float((val & (beh > 0.2)).mean()), 3),
                            front_gt05_share=round(float((val & (fr > 0.5)).mean()), 3),
                            med_r_cm_p50=round(float(np.nanmedian(z['med_r_cm'][:, b])), 2),
                            flag_D=bool(share >= 0.25 or L >= 50)))
json.dump(res, open(out, 'w'), indent=1)
print('mode ep obj T bad_share longest(start) hidden beh>0.2 front>0.5 med_r flag runs')
for r in res:
    print(r['mode'], r['ep'], r['obj'][:14], r['T'], r['bad_share'], f"{r['longest_run']}({r['longest_run_start']})",
          r['hidden_share'], r['behind_gt02_share'], r['front_gt05_share'], r['med_r_cm_p50'], 'D' if r['flag_D'] else '-',
          r['runs_ge5'][:6])
