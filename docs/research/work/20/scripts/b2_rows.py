# Debug helper: dump per-row outline (s, left, right, width, midline) from b2_front.measure for one frame (no file output).
import sys, numpy as np
src = open('/Users/aebatirel/Documents/Code/v2d-research/work/20/scripts/b2_front.py').read().split('\nfor k in KS:')[0]
src = src.replace("    ok = [x for x in rows if x is not None]\n", "    ok = [x for x in rows if x is not None]; DUMP['ok'] = ok; DUMP['zs'] = Zs; DUMP['mpu'] = mm_per_unit; DUMP['sM'] = sM\n")
DUMP = {}; exec(compile(src, 'b2_front', 'exec'))
k = KS[0]; o = measure(k); ok = np.array(DUMP['ok']); mpu = DUMP['mpu']
s = ok[:, 0] * mpu; l = ok[:, 1] * 1e3 * DUMP['zs'](ok[:, 0]); r = ok[:, 2] * 1e3 * DUMP['zs'](ok[:, 0])
print('markers s', np.round(DUMP['sM'] * mpu, 1))
for lo in np.arange(-180, 190, 5):
    m = (s >= lo) & (s < lo + 5)
    if m.sum(): print(f's {lo:5.0f} n {m.sum():3d} L {np.median(l[m]):+6.2f} R {np.median(r[m]):+6.2f} W {np.median(r[m]-l[m]):5.2f} mid {np.median(0.5*(l[m]+r[m])):+6.2f}')
