"""Spin-specific texture detail: band-pass colour (DoG 3-10 mm) minus its ring mean at each (height, radius) bin,
then its normalised correlation with the spun copy. 'all' vs 'nomk' (marker neighbourhoods removed)."""
import numpy as np, json, sys
from scipy.spatial import cKDTree
from scipy.ndimage import gaussian_filter
from meshlib import *
from selfsim import good_markers
AX = json.load(open('out/axes2.json'))

def bandpass(P, C, vox=0.002, s1=1.5, s2=5.0):
    lo = P.min(0) - 0.01; idx = np.floor((P - lo) / vox).astype(int); dims = idx.max(0) + 2; t = tuple(idx.T)
    cnt = np.zeros(dims, np.float32); np.add.at(cnt, t, 1)
    c1, c2 = gaussian_filter(cnt, s1)[t], gaussian_filter(cnt, s2)[t]
    out = np.empty_like(C)
    for c in range(3):
        s = np.zeros(dims, np.float32); np.add.at(s, t, C[:, c])
        out[:, c] = gaussian_filter(s, s1)[t] / np.maximum(c1, 1e-9) - gaussian_filter(s, s2)[t] / np.maximum(c2, 1e-9)
    return out

def ring_remove(P, X, p, a, dh=0.002, dr=0.002):
    Q = P - p; h = Q @ a; r = np.linalg.norm(Q - np.outer(h, a), axis=1)
    key = np.floor(h / dh).astype(np.int64) * 100000 + np.floor(r / dr).astype(np.int64)
    u, inv = np.unique(key, return_inverse=True)
    out = X.copy()
    for c in range(X.shape[1]):
        m = np.bincount(inv, X[:, c]) / np.bincount(inv); out[:, c] -= m[inv]
    return out

def run(name, nA=150000, nB=600000, excl=0.016, step=1.0):
    g, tex = load(name)
    PA, CA, _ = sample(g, tex, nA, seed=13); PB, CB, _ = sample(g, tex, nB, seed=14)
    p, a = np.array(AX[name]['p']), np.array(AX[name]['a'])
    XA = ring_remove(PA, bandpass(PA, CA), p, a); XB = ring_remove(PB, bandpass(PB, CB), p, a)
    mk = good_markers(name)
    kA = cKDTree(mk).query(PA)[0] > excl; kB = cKDTree(mk).query(PB)[0] > excl
    eB = (XB ** 2).sum(1)
    res = dict(aniso_rms_all=float(np.sqrt(eB.mean())), aniso_rms_nomk=float(np.sqrt(eB[kB].mean())),
               energy_share_markers=float(eB[~kB].sum() / eB.sum()), marker_area=float(1 - kB.mean()))
    angles = np.arange(0, 360, step); res['angles'] = angles.tolist()
    for tag, mA, mB in [('all', np.ones(len(PA), bool), np.ones(len(PB), bool)), ('nomk', kA, kB)]:
        A, xa = PA[mA], XA[mA]; T = cKDTree(PB[mB]); xb = XB[mB]
        corr = []
        for ang in angles:
            d, i = T.query((A - p) @ rot(a, np.radians(ang)).T + p, distance_upper_bound=0.0015); nr = np.isfinite(d)
            x, y = xa[nr], xb[i[nr]]
            corr.append(float((x * y).sum() / np.sqrt((x * x).sum() * (y * y).sum())) if nr.sum() > 200 else np.nan)
        res[tag] = corr
    return res

if __name__ == '__main__':
    for n in sys.argv[1:]:
        r = run(n); json.dump(r, open(f'out/symm3_{n}.json', 'w'))
        c = np.array(r['nomk']); ca = np.array(r['all']); ang = np.array(r['angles'])
        far = np.abs((ang + 180) % 360 - 180) > 15
        print(f"{n}: aniso rms all {r['aniso_rms_all']:.4f} nomk {r['aniso_rms_nomk']:.4f}; marker area {r['marker_area']:.3f} carries {r['energy_share_markers']:.2f} of energy; "
              f"corr@0 all {ca[0]:.2f} nomk {c[0]:.2f}; max corr |spin|>15: all {np.nanmax(ca[far]):.2f} @ {ang[far][np.nanargmax(ca[far])]:.0f}, nomk {np.nanmax(c[far]):.2f} @ {ang[far][np.nanargmax(c[far])]:.0f}", flush=True)
