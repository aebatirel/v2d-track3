"""Per-frame and per-range summary of one (reference x mesh set) cell: intrusion.py output (via intrusion_diag.py) + gapA.
I(f) = max over the two ordered pairs of intr_vol (cm3); depth = max over both pairs of depth_m (mm); floor gap = gapA
floor_gap_mm where the beige's lowest point is over the floor. PREREG G1: max I over f100-160 <= 2.0 cm3.
Usage: summarize.py DIAG.npz GAPA.json LABEL OUT.json"""
import sys, json
import numpy as np
dz, gj, label, outp = sys.argv[1:5]
Z = np.load(dz); G = json.load(open(gj))
names = [str(x) for x in Z['objects']]; ib, ig = names.index('blue_cup'), names.index('beige_cup')
T = len(G['A'][1])
vol = {ib: np.zeros(T), ig: np.zeros(T)}; dep = {ib: np.zeros(T), ig: np.zeros(T)}
for i in range(len(Z['fp_frame'])):
    vol[int(Z['fp_target'][i])][int(Z['fp_frame'][i])] = float(Z['intr_vol_m3'][i]) * 1e6
fr, tg, d = Z['frame'], Z['target'], Z['depth_m']
for t in (ib, ig):
    for f in np.unique(fr[tg == t]):
        dep[t][f] = float(d[(fr == f) & (tg == t)].max()) * 1e3
I = np.maximum(vol[ib], vol[ig]); D = np.maximum(dep[ib], dep[ig])
gap = np.array([r['floor_gap_mm'] if r['over_floor'] else np.nan for r in G['A'][1]])
RANGES = [('f0-46', 0, 46), ('f47-99', 47, 99), ('f100-117', 100, 117), ('f118-160', 118, 160), ('f100-160', 100, 160)]


def st(x):
    x = np.asarray(x, float); x = x[np.isfinite(x)]
    return None if not len(x) else dict(min=round(float(x.min()), 2), median=round(float(np.median(x)), 2), max=round(float(x.max()), 2))


S = {}
for lab, a, b in RANGES:
    s = slice(a, b + 1); k = I[s] > 0
    S[lab] = dict(frames=b - a + 1, intruding_frames=int(k.sum()), I_cm3_all=st(I[s]), I_cm3_intruding=st(I[s][k]),
                  beige_in_blue_cm3_max=round(float(vol[ib][s].max()), 2), blue_in_beige_cm3_max=round(float(vol[ig][s].max()), 2),
                  depth_max_mm=round(float(D[s].max()), 2), depth_mm_intruding=st(D[s][k]), floor_gap_mm=st(gap[s]),
                  frames_over_2cm3=int((I[s] > 2.0).sum()))
g1 = bool(I[100:161].max() <= 2.0)
out = dict(label=label, diag=dz, gap=gj, floor_mm=G['A'][0]['floor_mm'], G1_part_pass=g1, I_max_f100_160=round(float(I[100:161].max()), 2),
           ranges=S, per_frame=dict(I_cm3=np.round(I, 3).tolist(), depth_mm=np.round(D, 2).tolist(),
                                    floor_gap_mm=[None if not np.isfinite(v) else round(float(v), 2) for v in gap]))
json.dump(out, open(outp, 'w'), indent=1)
print(label, 'G1 part', 'PASS' if g1 else 'FAIL', 'max I f100-160', out['I_max_f100_160'])
for lab in S:
    r = S[lab]
    print(f"  {lab:9s} intr {r['intruding_frames']:2d}/{r['frames']:2d}  I(intr) {r['I_cm3_intruding']}  dmax {r['depth_max_mm']}  gap {r['floor_gap_mm']}")
