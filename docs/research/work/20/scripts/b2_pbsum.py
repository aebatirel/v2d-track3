# b2 copy of b_pbsum.py reading out/b2/pb_*.jsonl
# Summarise b_pb runs: P(frame B) per rule and layout (and roll for the grid layouts).
import json, glob, collections, numpy as np
OUT = '/Users/aebatirel/Documents/Code/v2d-research/work/20/out/b2'
KEYS = ['n07_skew_y', 'n07_skew_x', 'n07_hybrid.02', 'n07_larger_abs', 'noisy_q10_y', 'noisy_-shalf_x', 'noisy_far3d_x']
by = collections.defaultdict(list)
for f in sorted(glob.glob(f'{OUT}/pb_*.jsonl')):
    lay = f.split('pb_')[1].rsplit('_', 1)[0]
    for l in open(f):
        r = json.loads(l)
        for phi, x in r['res'].items():
            by[(lay, 'drawn' if (lay == 'final' or lay.startswith('hl')) else phi)].append((r, x))
print('layout/roll  N | toM2 mean [p10,p90]  P(toM2>0) | noisy-mid P(B) | ' + ' '.join(k.replace('n07_', '')[:10] for k in KEYS) + ' | F2 F2b F3 | zflip midIsY | toConc')
for (lay, phi), L in sorted(by.items(), key=lambda t: (t[0][0], float(t[0][1]) if t[0][1] != 'drawn' else 0)):
    X = [x for _, x in L]; t = np.array([x['toM2'] for x in X])
    pb = lambda k: np.mean([x[k].startswith('B') for x in X])
    print(f"{lay:15s} {phi:>5s} {len(X):3d} | {t.mean():+.3f} [{np.percentile(t,10):+.3f},{np.percentile(t,90):+.3f}] {np.mean(t>0):.2f} | "
          f"{np.mean([x['PB_noisy_mid'] for x in X]):.2f} | " + ' '.join(f'{pb(k):10.2f}' for k in KEYS) +
          f" | {np.mean([x['F2_shareB'] for x in X]):.2f} {np.mean([x['F2b_shareB'] for x in X]):.2f} {np.mean([x['F3_shareB'] for x in X]):.2f} | "
          f"{np.mean([x['zflip'] for x in X]):.2f} {np.mean([x['midIsY'] for x in X]):.2f} | {np.mean([x['toConc'] for x in X]):+.3f}")
# final layout: dependence on the drawn asymmetry and roll
F = by.get(('final', 'drawn'), [])
if F:
    a = np.array([r['p']['w1'] - r['p']['w2'] for r, _ in F]); ph = np.array([r['p']['phi'] for r, _ in F]); t = np.array([x['toM2'] for _, x in F])
    A_ = np.c_[np.ones(len(a)), a, ph]; cf = np.linalg.lstsq(A_, t, rcond=None)[0]
    print(f'final: toM2 ~ {cf[0]:+.4f} {cf[1]:+.4f}*asym(mm) {cf[2]:+.4f}*roll(deg); zero at asym = {-cf[0]/cf[1]:+.2f} mm (roll 0)')
    for lo, hi in ((-9, -1), (-1, 0.5), (0.5, 2), (2, 9)):
        m = (a >= lo) & (a < hi)
        if m.sum(): print(f'   asym [{lo},{hi}) n {m.sum():3d}: P(toM2>0) {np.mean(t[m]>0):.2f}  noisy-mid P(B) {np.mean([F[i][1]["PB_noisy_mid"] for i in np.nonzero(m)[0]]):.2f}')
