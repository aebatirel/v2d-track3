# Stage A4: rolling-shutter check. Offset of each row band of X vs full-frame Y (global-shutter reference).
# Integer slip episodes are restricted to their constant segment. Usage: a_rs.py X Y key[:i0:i1] ...
import sys, numpy as np
sys.path.insert(0, '/Users/aebatirel/Documents/Code/v2d-research/work/20/scripts')
from a_sync import fit_shift
OUT = '/Users/aebatirel/Documents/Code/v2d-research/work/20/out'
X, Y = sys.argv[1], sys.argv[2]; rows = []
import os; CW = [float(v) for v in os.environ.get('CW','1,1,1').split(',')]
for arg in sys.argv[3:]:
    p = arg.split(':'); key = p[0]
    z = np.load(f'{OUT}/motion/{key}.npz'); n = len(z[f'{X}_rv'])
    idx = np.arange(int(p[1]), int(p[2])) if len(p) == 3 else None
    full, _, R, _ = fit_shift(z[f'{X}_rv'], z[f'{Y}_rv'], idx=idx)
    full, _, _, _ = fit_shift(z[f'{X}_rv'], z[f'{Y}_rv'], idx=idx, fixR=R, cw=CW)
    bs = []; ys = []
    for b in range(3):
        wb = z[f'{X}_band'][:, b]
        s, c, _, _ = fit_shift(wb, z[f'{Y}_rv'], fixR=R, idx=idx, cw=CW)
        bs.append(s * 50); ys.append(np.nanmean(z[f'{X}_bandy'][:, b]))
    slope = np.polyfit(ys, bs, 1)[0]
    rows.append((key, full * 50, *bs, slope))
    print(f'{key:5s} full {full*50:+7.2f} | top {bs[0]:+7.2f} mid {bs[1]:+7.2f} bot {bs[2]:+7.2f} ms | band y {np.round(ys,2)} | slope {slope:+6.2f} ms/height', flush=True)
r = np.array([x[1:] for x in rows]); print('MEAN full %.2f top %.2f mid %.2f bot %.2f slope %.2f +- %.2f (sd)' % (*r.mean(0), r[:, -1].std()))
