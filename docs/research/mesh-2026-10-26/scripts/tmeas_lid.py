# GT-free: lid rim thickness from OUR side-seen points near the edge (no scan)
import sys, json, numpy as np
sys.path.insert(0, '/home/user/v2d-track3/docs/research/mesh-2026-10-26/scripts')
import prim_potlid as PL, lathe_obs as L
P, C = PL.load_obs(sys.argv[1]); v = PL.unit(C - P)
info = json.load(open(sys.argv[2]))
c = np.array(info['centre']); d = np.array(info['axis']); re = info['r_edge_mm'] / 1e3
h, r, th, (e1, e2, d) = L.cyl(P, c, d)
vh = v @ d
for band in (0.002, 0.004):
    m = (r > re - band) & (r < re + 0.004)
    for lab, s in (('all', m), ('side |v.d|<0.5', m & (np.abs(vh) < 0.5))):
        if s.sum() < 20: print(band, lab, s.sum()); continue
        sb = ((th[s] + np.pi) / (2 * np.pi) * 24).astype(int)
        ext = [np.ptp(np.percentile(h[s][sb == q], [5, 95])) for q in range(24) if (sb == q).sum() > 15]
        print(f'band {band*1e3:.0f}mm {lab}: n={s.sum()} sectors={len(ext)} 5-95% height extent median={np.median(ext)*1e3:.2f} mm  [{np.percentile(ext,25)*1e3:.2f},{np.percentile(ext,75)*1e3:.2f}]')
print('view-to-axis cos at edge: median', np.median(np.abs(vh[(r > re - 0.004)])))
