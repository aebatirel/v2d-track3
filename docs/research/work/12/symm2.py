"""Rotational self-similarity about the physical spin axis (out/axes2.json).
Per angle: geometry (mean NN distance, fraction > 2 mm) and texture (high-pass colour correlation, mean |dRGB|),
with all surface points ('all') and with marker neighbourhoods removed ('nomk')."""
import numpy as np, json, sys
from scipy.spatial import cKDTree
from scipy.ndimage import gaussian_filter
from meshlib import *
from selfsim import good_markers
AX = json.load(open('out/axes2.json'))

def highpass(P, C, vox=0.004, sig=2.0):
    lo = P.min(0); idx = np.floor((P - lo) / vox).astype(int); dims = idx.max(0) + 1
    cnt = np.zeros(dims); np.add.at(cnt, tuple(idx.T), 1)
    out = np.empty_like(C)
    cs = gaussian_filter(cnt, sig)
    for c in range(3):
        s = np.zeros(dims); np.add.at(s, tuple(idx.T), C[:, c]); out[:, c] = gaussian_filter(s, sig)[tuple(idx.T)] / np.maximum(cs[tuple(idx.T)], 1e-9)
    return C - out

def run(name, nA=100000, nB=400000, excl=0.016, step=2.0):
    g, tex = load(name)
    PA, CA, _ = sample(g, tex, nA, seed=3); PB, CB, _ = sample(g, tex, nB, seed=4)
    HA, HB = highpass(PA, CA), highpass(PB, CB)
    p, a = np.array(AX[name]['p']), np.array(AX[name]['a'])
    mk = good_markers(name)
    keepA = cKDTree(mk).query(PA)[0] > excl if len(mk) else np.ones(len(PA), bool)
    keepB = cKDTree(mk).query(PB)[0] > excl if len(mk) else np.ones(len(PB), bool)
    angles = np.arange(0, 360, step)
    res = dict(angles=angles.tolist(), axis_p=p.tolist(), axis_a=a.tolist(), markers=mk.tolist(),
               hp_rms_all=float(np.sqrt((HB ** 2).sum(1).mean())), hp_rms_nomk=float(np.sqrt((HB[keepB] ** 2).sum(1).mean())),
               marker_area_frac=float(1 - keepB.mean()))
    for tag, kA, kB in [('all', np.ones(len(PA), bool), np.ones(len(PB), bool)), ('nomk', keepA, keepB)]:
        A, cA, hA = PA[kA], CA[kA], HA[kA]; T = cKDTree(PB[kB]); cB, hB = CB[kB], HB[kB]
        geo, out2, cmad, corr = [], [], [], []
        for ang in angles:
            A2 = (A - p) @ rot(a, np.radians(ang)).T + p
            d, i = T.query(A2, distance_upper_bound=0.01); ok = np.isfinite(d)
            geo.append(np.where(ok, d, 0.01).mean()); out2.append((~ok | (d > 0.002)).mean())
            nr = d < 0.0015
            if nr.sum() > 200:
                x, y = hA[nr], hB[i[nr]]
                cmad.append(np.abs(cA[nr] - cB[i[nr]]).mean()); corr.append((x * y).sum() / np.sqrt((x * x).sum() * (y * y).sum()))
            else: cmad.append(np.nan); corr.append(np.nan)
        res[tag] = {k: [float(x) for x in v] for k, v in dict(geo=geo, out2=out2, cmad=cmad, corr=corr).items()}
    return res

if __name__ == '__main__':
    for n in sys.argv[1:]:
        r = run(n); json.dump(r, open(f'out/symm2_{n}.json', 'w'))
        print(n, 'done; hp rms all %.4f nomk %.4f marker area %.3f' % (r['hp_rms_all'], r['hp_rms_nomk'], r['marker_area_frac']), flush=True)
