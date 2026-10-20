"""C1 geometry, best-fit axis: fit axis (point + direction) minimising outer-wall out-of-roundness, then
spin NN statistics (markers excluded 16 mm; hole effect avoided by excluding from the query set only points whose
rotated image lands in a B-marker hole). Independent of work/12 code."""
import numpy as np, json, sys, trimesh
from scipy.spatial import cKDTree
from scipy.spatial.transform import Rotation as R
from scipy.optimize import minimize
ROOT = '/Users/aebatirel/Documents/Code/v2d-research/data/track_3/public'
M = json.load(open('/Users/aebatirel/Documents/Code/v2d-research/work/12/out/markers_raw.json'))
A0 = json.load(open('/Users/aebatirel/Documents/Code/v2d-research/work/12/out/axes2.json'))

def frame(a):
    e1 = np.cross(a, [1, 0, 0]); e1 /= np.linalg.norm(e1); return e1, np.cross(a, e1)

def wall(X, p, a, hb=0.004, tbw=5):
    e1, e2 = frame(a); Y = X - p; h = Y @ a; rr = Y - np.outer(h, a); r = np.linalg.norm(rr, axis=1)
    th = np.degrees(np.arctan2(rr @ e2, rr @ e1))
    key = np.floor(h / hb).astype(int) * 1000 + np.floor((th + 180) / tbw).astype(int)
    o = np.lexsort((r, key)); ks = key[o]; last = np.r_[ks[1:] != ks[:-1], True]
    return ks[last], r[o][last]

def dev_of(X, p, a):
    k, rm = wall(X, p, a); hv = k // 1000; dev = []
    for v in np.unique(hv):
        s = hv == v
        if s.sum() >= 60: dev.append(rm[s] - np.median(rm[s]))
    return np.concatenate(dev)

def run(name, n=300000):
    g = list(trimesh.load(f'{ROOT}/mesh/{name}/{name}.glb').geometry.values())[0]
    P = np.asarray(trimesh.sample.sample_surface(g, n, seed=1)[0]); Q = np.asarray(trimesh.sample.sample_surface(g, n, seed=2)[0])
    mk = np.array([q['centre'] for q in M[name] if 6.5e-3 < q['radius'] < 8.6e-3 and q['bright'] > 0.55])
    kP = cKDTree(mk).query(P)[0] > 0.016; kQ = cKDTree(mk).query(Q)[0] > 0.016
    a0, p0 = np.array(A0[name]['a']), np.array(A0[name]['p']); e1, e2 = frame(a0)
    def par(x):
        a = a0 + x[2] * e1 + x[3] * e2; a /= np.linalg.norm(a); return p0 + x[0] * e1 + x[1] * e2, a
    sub = P[kP][::3]
    f = lambda x: np.mean(dev_of(sub, *par(x)) ** 2)
    res = minimize(f, np.zeros(4), method='Nelder-Mead', options=dict(xatol=1e-5, fatol=1e-12, maxiter=600))
    p, a = par(res.x)
    d = np.abs(dev_of(P[kP], p, a)) * 1e3
    print(name, 'fit shift %.2f %.2f mm tilt %.2f deg' % (res.x[0] * 1e3, res.x[1] * 1e3, np.degrees(np.hypot(res.x[2], res.x[3]))),
          '| outer-wall |dev| med %.2f p95 %.2f p99 %.2f max %.2f mm' % (np.median(d), *np.percentile(d, [95, 99]), d.max()), flush=True)
    # spin NN with hole-masking
    T = cKDTree(Q[kQ]); A_ = P[kP]; rows = []
    for ang in range(0, 360, 2):
        Rm = R.from_rotvec(a * np.radians(ang)).as_matrix(); A2 = (A_ - p) @ Rm.T + p
        valid = cKDTree(mk).query(A2)[0] > 0.016 + 0.004    # rotated point not inside a marker hole of B
        dd = T.query(A2[valid])[0]
        rows.append((ang, dd.mean() * 1e3, np.percentile(dd, 95) * 1e3, np.percentile(dd, 99) * 1e3, (dd > 0.002).mean()))
    rows = np.array(rows)
    j = rows[1:, 1].argmax() + 1
    print(name, 'spin NN mean @0 %.2f, max %.2f @%d; p95 max %.2f; p99 max %.2f; frac>2mm max %.3f' % (
        rows[0, 1], rows[j, 1], rows[j, 0], rows[1:, 2].max(), rows[1:, 3].max(), rows[1:, 4].max()), flush=True)
    json.dump(dict(name=name, p=p.tolist(), a=a.tolist(), curve=rows.tolist(), wall_dev_pct=[float(x) for x in np.percentile(d, [50, 95, 99, 100])]),
              open(f'/Users/aebatirel/Documents/Code/v2d-research/work/12-verify/c1_geo2_{name}.json', 'w'))

if __name__ == '__main__':
    for nm in sys.argv[1:]: run(nm)
