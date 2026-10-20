# Diagnostic: limb edges (L, R), width and midpoint along the whole handle (image-plane mm, relative to the reference line
# mid(M1,M2)->M3), 10-mm bins, plus deviations from straight-line fits over the whole handle. Usage: b2_limbs.py <ep> <k> [--rest]
import sys, numpy as np
REST = '--rest' in sys.argv; a = [x for x in sys.argv[1:] if not x.startswith('--')]
sys.argv = ['b2_front.py', a[0]] + (['--rest'] if REST else [])
src = open('/Users/aebatirel/Documents/Code/v2d-research/work/20/scripts/b2_front.py').read().split('\nfor k in KS:')[0]
src = src.replace("    ok = [x for x in rows if x is not None]\n", "    ok = [x for x in rows if x is not None]; DUMP.update(ok=ok, mpu=mm_per_unit, sMmm=sM * mm_per_unit, Zs=Zs)\n")
DUMP = {}; exec(compile(src, 'b2_front', 'exec'))
k = int(a[1]); measure(k); ok = np.array(DUMP['ok']); z = 1e3 * DUMP['Zs'](ok[:, 0])
s = ok[:, 0] * DUMP['mpu']; L = ok[:, 1] * z; R_ = ok[:, 2] * z; W = R_ - L; sM = DUMP['sMmm']
print(f'e{ep} k{k} markers s', np.round(sM, 1))
hm = (s > sM[1] + 12) & (s < sM[2] - 6) & (W > 14) & (W < 24)
for j in range(2): hm &= np.abs(s - sM[j]) > 12
cL = np.polyfit(s[hm], L[hm], 1); cR = np.polyfit(s[hm], R_[hm], 1); cM = np.polyfit(s[hm], 0.5 * (L + R_)[hm], 1)
cM2 = np.polyfit(s[hm], 0.5 * (L + R_)[hm], 2)
print(f'  whole-handle LSQ: L slope {cL[0]*1e3:+.1f} mm/m, R slope {cR[0]*1e3:+.1f} mm/m (taper {1e3*(cR[0]-cL[0]):+.1f} mm/m); mid quad coef {cM2[0]*1e4:+.3f} mm per (100 mm)^2')
for lo in np.arange(np.floor(sM[1]), sM[2] + 5, 10):
    m = (s >= lo) & (s < lo + 10)
    if m.sum() < 3: continue
    print(f'  s {lo:6.0f}: n {m.sum():3d} L {np.median(L[m]):+7.2f} R {np.median(R_[m]):+7.2f} W {np.median(W[m]):6.2f} mid {np.median(0.5*(L+R_)[m]):+6.2f} | dev from mid-line {np.median((0.5*(L+R_) - np.polyval(cM, s))[m]):+5.2f}  L-dev {np.median((L - np.polyval(cL, s))[m]):+5.2f} R-dev {np.median((R_ - np.polyval(cR, s))[m]):+5.2f}' + ('  (handle rows)' if hm[m].mean() > 0.5 else ''))
