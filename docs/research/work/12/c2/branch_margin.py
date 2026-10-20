"""Stage C re-run: how well must the cup centre be known for TWO detected markers to name the spin branch?
Deterministic, synthetic (upright cup, scan markers in the upright gauge, mc_spin camera model, cam a). For each view
and each visible true marker pair, every wrong ordered assignment (k,l) is fitted with free spin and a centre shift
bounded to |d_i| <= s (tilt fixed, or +-1 deg free). Output: wrong-hypothesis RMS reprojection residual vs s, and the
shift the wrong branch needs (split along-ray vs lateral). Usage: branch_margin.py <object> [tilt]"""
import numpy as np, sys, json, itertools
from scipy.optimize import least_squares
W = '/Users/aebatirel/Documents/Code/v2d-research/work/12'; sys.path.insert(0, W); sys.path.insert(0, W + '/c')
import mc_spin as mc
name = sys.argv[1]; tilt = 'tilt' in sys.argv
up = np.array(mc.AX[name]['gt_up'], float); up /= np.linalg.norm(up)
R0 = mc.Rr.align_vectors([[0, 0, 1.]], [up])[0].as_matrix()
g_, tex = mc.load(name); P, _, _ = mc.sample(g_, tex, 60000, seed=3); c0 = P.mean(0)
M = (mc.good_markers(name) - c0) @ R0.T
K = mc.CAMS['a'][0]
th_m = np.arctan2(M[:, 1], M[:, 0]); nrm = np.c_[np.cos(th_m), np.sin(th_m), np.zeros(len(M))]
S_GRID = [0, 1, 2, 3, 5, 8]
def visible(pos):   # marker visible if within 95 deg of its outward (radial) normal, as markers2c
    v = pos - M; v /= np.linalg.norm(v, axis=1, keepdims=True); return (v * nrm).sum(1) > np.cos(np.radians(95))
rows = []
for D in (0.45, 0.60):
    for el in (30, 45, 60):
        for az in range(0, 360, 10):
            Rcw, pos = mc.camera(az, el, D); vis = np.flatnonzero(visible(pos))
            for i, j in itertools.combinations(vis, 2):
                uv, _ = mc.project(M[[i, j]], Rcw, pos, K)
                ray = -pos / np.linalg.norm(pos)
                best = {s: (1e9, None) for s in S_GRID}
                for k, l in itertools.permutations(range(len(M)), 2):
                    if (k, l) == (i, j): continue
                    th0 = np.angle(np.exp(1j * (th_m[i] - th_m[k])) + np.exp(1j * (th_m[j] - th_m[l])))
                    for s in S_GRID:
                        b = 1e-3 * s + 1e-9; ng = 2 if tilt else 0
                        lo = np.r_[-np.inf, -b, -b, -b, [-np.radians(1)] * ng]; hi = np.r_[np.inf, b, b, b, [np.radians(1)] * ng]
                        def res(q):
                            g = q[4:6] if tilt else np.zeros(2)
                            u, _ = mc.project(mc.pose_pts(M[[k, l]], q[0], q[1:4], g), Rcw, pos, K); return (u - uv).ravel()
                        r = least_squares(res, np.r_[th0, 0, 0, 0, [0] * ng], bounds=(lo, hi), max_nfev=200)
                        rms = np.sqrt(np.mean(r.fun.reshape(-1, 2) ** 2) * 2)
                        if rms < best[s][0]:
                            d = r.x[1:4]; best[s] = (rms, dict(kl=(int(k), int(l)), spin=float(np.degrees(r.x[0])), d_ray=float(1e3 * d @ ray),
                                                     d_lat=float(1e3 * np.linalg.norm(d - (d @ ray) * ray))))
                rows.append(dict(D=D, el=el, az=az, pair=(int(i), int(j)), nvis=len(vis), rms={s: best[s][0] for s in S_GRID},
                                 at5=best[5][1], at8=best[8][1]))
out = {'n_views_pairs': len(rows)}
print(name, 'tilt free' if tilt else 'tilt fixed', 'view-pairs', len(rows))
for s in S_GRID:
    r = np.array([q['rms'][s] for q in rows])
    out[s] = dict(median=float(np.median(r)), p10=float(np.percentile(r, 10)), frac_lt3=float((r < 3).mean()), frac_lt6=float((r < 6).mean()))
    print('  centre bound %d mm: wrong-branch rms px median %.1f p10 %.1f; share of view-pairs < 3 px %.2f, < 6 px %.2f' % (
        s, out[s]['median'], out[s]['p10'], out[s]['frac_lt3'], out[s]['frac_lt6']))
a8 = [q['at8'] for q in rows if q['rms'][8] < 1.0]
if a8: print('  wrong fits at 8 mm (rms<1px): |d_ray| median %.1f mm, |d_lat| median %.1f mm, spin %s' % (
    np.median([abs(q['d_ray']) for q in a8]), np.median([q['d_lat'] for q in a8]), np.round(np.percentile([abs(q['spin']) for q in a8], [10, 50, 90]), 0)))
json.dump(dict(summary=out, rows=rows), open(f'{W}/c2/branch_margin_{name}{"_tilt" if tilt else ""}.json', 'w'), default=str)
