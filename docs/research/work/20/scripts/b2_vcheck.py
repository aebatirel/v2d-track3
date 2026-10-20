# Diagnostic: brightness (V) and saturation (S) just inside each side of the bowl outline (b2_front edges), to test whether
# b_geom's wood test (S 35-135, V > 160) truncates one side.  Usage: b2_vcheck.py <ep> <k> [--rest]
import sys, numpy as np
REST = '--rest' in sys.argv; a = [x for x in sys.argv[1:] if not x.startswith('--')]
sys.argv = ['b2_front.py', a[0]] + (['--rest'] if REST else [])
src = open('/Users/aebatirel/Documents/Code/v2d-research/work/20/scripts/b2_front.py').read().split('\nfor k in KS:')[0]
src = src.replace("    Sst = cv2.GaussianBlur(Sst, (0, 0), 1.0)\n", "    Sst = cv2.GaussianBlur(Sst, (0, 0), 1.0); DUMP.update(Sst=Sst, Vst=Vst, ss=ss, nn=nn)\n")
src = src.replace("    ok = [x for x in rows if x is not None]\n", "    ok = [x for x in rows if x is not None]; DUMP.update(ok=ok, mpu=mm_per_unit, sMmm=sM * mm_per_unit, Zs=Zs)\n")
DUMP = {}; exec(compile(src, 'b2_front', 'exec'))
k = int(a[1]); measure(k); ok = np.array(DUMP['ok']); Sst, Vst, ss, nn = DUMP['Sst'], DUMP['Vst'], DUMP['ss'], DUMP['nn']
STEPmm = STEP * 1e3 * DUMP['Zs'](0.0)
print(f'e{ep} k{k}: sample = {STEPmm:.3f} mm')
for lo, hi in ((-130, -110), (-110, -90), (-90, -70), (-70, -50)):
    rows = [(s, l, r) for s, l, r, *_ in ok if lo <= s * DUMP['mpu'] < hi]
    out = []
    for side in ('L(-n, M2 side)', 'R(+n, M1 side)'):
        Vv, Sv, frac = [], [], []
        for s, l, r in rows:
            ri = int(round((s - ss[0]) / STEP)); il = int(round((l - nn[0]) / STEP)); ir = int(round((r - nn[0]) / STEP))
            band = range(il + 2, il + 2 + int(8 / STEPmm)) if side[0] == 'L' else range(ir - 2 - int(8 / STEPmm), ir - 2)   # 8 mm inside
            v = Vst[ri, list(band)]; sv = Sst[ri, list(band)]; Vv.append(np.median(v)); Sv.append(np.median(sv))
            frac.append(np.mean(~((sv > 35) & (sv < 135) & (v > 160))))
        out.append(f'{side}: V {np.median(Vv):5.1f} S {np.median(Sv):5.1f} non-wood(b_geom test) {np.mean(frac):.2f}')
    print(f'  s {lo}..{hi} (n {len(rows)}): ' + ' | '.join(out))
