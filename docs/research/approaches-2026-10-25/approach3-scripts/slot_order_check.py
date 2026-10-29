"""Which robot site does each of the 16 reference contact slots belong to? (GT-free check of the slot order.)
For every active slot k on object j, the distance of each candidate site (15 PROBE_SITES + the palm mean) to the object
surface is computed; slot k should be nearest to (and within the 18 / 28 mm threshold of) PROBE_SITES[k] (palm: k=15).
Prints, per slot, the fraction of its active frames where the site of the mkref order is within threshold, and the
same fraction for the site the human-grasp census (docs/research/grasp/hand-biomech-scripts) assumed (MANO link order).
Usage: python -I slot_order_check.py REF.parquet [REF2 ...]
"""
import sys, os
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import load_ref, Surface, to_obj, PROBE_SITES, PALM_FRAMES, SLOTS  # noqa: E402

CENSUS = ['palm', 'thumb1', 'thumb2', 'thumb3', 'index1', 'index2', 'index3', 'middle1', 'middle2', 'middle3',
          'ring1', 'ring2', 'ring3', 'pinky1', 'pinky2', 'pinky3']

tot = np.zeros((16, 2)); cnt = np.zeros(16)
for path in sys.argv[1:]:
    d = load_ref(path); surf = {n: Surface(n) for n in d['names']}
    for s in ('left', 'right'):
        F = d[f'F_{s}']
        sites = np.stack([F[k] for k in PROBE_SITES] + [np.mean([F[k] for k in PALM_FRAMES], 0)], 1)   # (T,16,3)
        pid = d[f'pid_{s}']
        for f in range(0, d['T'], 2):
            for k in np.nonzero(pid[f] > 0)[0]:
                j = pid[f, k] - 1
                dist, _, _ = surf[d['names'][j]].query(to_obj(d, j, f, sites[f]))
                thr = np.full(16, 0.018); thr[15] = 0.028
                ok = dist < thr + 0.004
                tot[k, 0] += ok[k]; tot[k, 1] += ok[0] if k != 0 else ok[15]; cnt[k] += 1
print('slot  mkref-site  frac_within(mkref order)  | census label  frac_within(site the census label implies: slot0<->palm)')
for k in range(16):
    if cnt[k]:
        print(f'{k:2d} {SLOTS[k]:11s} {tot[k, 0] / cnt[k]:.2f}  n={int(cnt[k])} | census "{CENSUS[k]}"')
print('slot 0 (census "palm"): fraction of its active frames with the PALM probe within threshold:',
      round(tot[0, 1] / max(cnt[0], 1), 2))
print('slot 15 (census "pinky3"): fraction of its active frames with the THUMB TIP within threshold:',
      round(tot[15, 1] / max(cnt[15], 1), 2))
