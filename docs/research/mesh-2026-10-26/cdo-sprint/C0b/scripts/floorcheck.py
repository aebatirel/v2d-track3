"""Re-run lathe_obs.main's steps (defaults) on the C0 blue-cup obs up to the floor rule and report which branch decided hfloor. GT-free."""
import sys, numpy as np
sys.path.insert(0, '/home/user/v2d-track3/docs/research/mesh-2026-10-26/scripts')
import lathe_obs as L
Z = np.load(sys.argv[1]); P = Z['pts'].astype(np.float64); C = Z['cam'].astype(np.float64)
key = np.floor(P / 0.0015).astype(np.int64); _, first = np.unique(key, axis=0, return_index=True); P, C = P[first], C[first]
sub = np.random.default_rng(0).choice(len(P), min(60000, len(P)), replace=False)
cost, c, d, k = L.fit_axis(P[sub], C[sub], knn=24)
h, r, th, (e1, e2, d) = L.cyl(P, c, d)
v = C - P; v /= np.linalg.norm(v, axis=1, keepdims=True)
vr = (v @ e1) * np.cos(th) + (v @ e2) * np.sin(th)
outer, inner = vr > 0.3, vr < -0.3
So, h0 = L.sector_stat(h, r, th, outer); Si, _ = L.sector_stat(h, r, th, inner)
nb = So.shape[0]; no = np.isfinite(So).sum(1); ni = np.isfinite(Si).sum(1)
r_out = np.where(no >= 6, np.nanmedian(np.where(np.isfinite(So), So, np.nan), 1), np.nan)
r_in = np.where(ni >= 6, np.nanmedian(np.where(np.isfinite(Si), Si, np.nan), 1), np.nan)
hc = h0 + (np.arange(nb) + 0.5) * L.DH
vo = np.isfinite(r_out); vi = np.isfinite(r_in) & vo & (r_in < r_out)
body = r < np.nanmax(r_out) + 0.005
hlo, hhi = np.percentile(h[body], [0.5, 99.5])
hi_in = hc[vi]; open_top = (len(hi_in) > 0) and (np.mean(hi_in > 0.5 * (hlo + hhi)) >= 0.5)
if not open_top:
    d = -d; h = -h; hlo, hhi = -hhi, -hlo
    r_out, r_in, vo, vi, hc = r_out[::-1], r_in[::-1], vo[::-1], vi[::-1], -hc[::-1]
t = float(np.median((r_out - r_in)[vi])) if vi.sum() >= 3 else 0.003
print('two-wall bins', int(vi.sum()), 't_meas_mm', round(t * 1e3, 3), 'tmin binds', t < 0.0015)
t = max(t, 0.0015)
sel = (hc >= hlo) & (hc <= hhi)
hc, r_out, r_in, vo, vi = hc[sel], r_out[sel], r_in[sel], vo[sel], vi[sel]
ro = L.smooth_fill(r_out, vo); ri = np.minimum(L.smooth_fill(np.where(vi, r_in, r_out - t), vi | vo), ro - 0.0015)
capin = (~outer) & (~inner) & (r < np.interp(h, hc, ri) - 0.003) & (h > hlo) & (h < hhi)
low = capin & (h < hlo + 0.4 * (hhi - hlo))
print('capin', int(capin.sum()), 'low', int(low.sum()))
if low.sum() > 200:
    q10, q50, q90 = np.percentile(h[low], [10, 50, 90])
    print('q90-q10 mm', round((q90 - q10) * 1e3, 2), 'q50-hlo mm', round((q50 - hlo) * 1e3, 2), 't mm', round(t*1e3,2))
# old (pre-15:56) rule for comparison
if capin.sum() > 50:
    print('old rule hfloor-hlo mm', round((max(float(np.percentile(h[capin], 5)), hlo + t) - hlo) * 1e3, 2))
fr = (h[capin] - hlo) / (hhi - hlo)
print('capin height fraction pct 5/25/50/75/95', np.round(np.percentile(fr, [5, 25, 50, 75, 95]), 3))
for f in (0.3, 0.4, 0.5, 0.6, 0.7, 0.8):
    m = capin & (h < hlo + f * (hhi - hlo))
    s = ''
    if m.sum() > 20:
        q10, q50, q90 = np.percentile(h[m], [10, 50, 90]); s = f'q90-q10 {1e3*(q90-q10):.1f} mm q50 {1e3*(q50-hlo):.1f} mm'
    print('frac', f, 'n', int(m.sum()), s)
