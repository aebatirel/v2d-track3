"""As branch_margin.py, but two views of the same static cup (camera moved by daz deg of azimuth around it, relative
camera motion assumed known, e.g. from ego-motion odometry), the same two markers detected in both, one shared
centre shift (per-axis bound s) and spin for the wrong hypothesis. Tilt fixed. Usage: branch_margin2.py <object> <daz>"""
import numpy as np, sys, json, itertools
from scipy.optimize import least_squares
W = '/Users/aebatirel/Documents/Code/v2d-research/work/12'; sys.path.insert(0, W); sys.path.insert(0, W + '/c')
import mc_spin as mc
name, daz = sys.argv[1], float(sys.argv[2])
up = np.array(mc.AX[name]['gt_up'], float); up /= np.linalg.norm(up)
R0 = mc.Rr.align_vectors([[0, 0, 1.]], [up])[0].as_matrix()
g_, tex = mc.load(name); P, _, _ = mc.sample(g_, tex, 60000, seed=3); c0 = P.mean(0)
M = (mc.good_markers(name) - c0) @ R0.T; K = mc.CAMS['a'][0]
th_m = np.arctan2(M[:, 1], M[:, 0]); nrm = np.c_[np.cos(th_m), np.sin(th_m), np.zeros(len(M))]
S_GRID = [2, 3, 5, 8]
def visible(pos):
    v = pos - M; v /= np.linalg.norm(v, axis=1, keepdims=True); return (v * nrm).sum(1) > np.cos(np.radians(95))
rows = []
for D in (0.45, 0.60):
    for el in (30, 45, 60):
        for az in range(0, 360, 10):
            cams = [mc.camera(az, el, D), mc.camera(az + daz, el, D)]
            vis = np.flatnonzero(visible(cams[0][1]) & visible(cams[1][1]))
            for i, j in itertools.combinations(vis, 2):
                uvs = [mc.project(M[[i, j]], Rcw, pos, K)[0] for Rcw, pos in cams]
                best = {s: 1e9 for s in S_GRID}
                for k, l in itertools.permutations(range(len(M)), 2):
                    if (k, l) == (i, j): continue
                    th0 = np.angle(np.exp(1j * (th_m[i] - th_m[k])) + np.exp(1j * (th_m[j] - th_m[l])))
                    for s in S_GRID:
                        b = 1e-3 * s
                        def res(q):
                            return np.concatenate([(mc.project(mc.pose_pts(M[[k, l]], q[0], q[1:4], np.zeros(2)), Rcw, pos, K)[0] - uv).ravel()
                                                   for (Rcw, pos), uv in zip(cams, uvs)])
                        r = least_squares(res, np.r_[th0, 0, 0, 0], bounds=(np.r_[-np.inf, -b, -b, -b], np.r_[np.inf, b, b, b]), max_nfev=200)
                        best[s] = min(best[s], float(np.sqrt(np.mean(r.fun.reshape(-1, 2) ** 2) * 2)))
                rows.append(dict(D=D, el=el, az=az, pair=(int(i), int(j)), rms=best))
out = {}
print(name, 'two views, daz %.0f deg, view-pairs %d' % (daz, len(rows)))
for s in S_GRID:
    r = np.array([q['rms'][s] for q in rows])
    out[s] = dict(p10=float(np.percentile(r, 10)), median=float(np.median(r)), frac_lt3=float((r < 3).mean()), frac_lt6=float((r < 6).mean()))
    print('  centre bound %d mm: wrong-branch rms px median %.1f p10 %.1f; share < 3 px %.2f, < 6 px %.2f' % (s, out[s]['median'], out[s]['p10'], out[s]['frac_lt3'], out[s]['frac_lt6']))
json.dump(dict(summary=out, rows=rows), open(f'{W}/c2/branch_margin2_{name}_daz{int(daz)}.json', 'w'), default=str)
