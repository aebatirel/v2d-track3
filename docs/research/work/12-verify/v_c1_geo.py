"""Independent check of C1 geometry: deviation of cup scans from a surface of revolution, markers removed.
Own sampling (trimesh.sample), axis from public GT (world z in object frame), marker exclusion radii 16 and 25 mm.
Reports per-spin NN-distance mean / p95 / p99 and per-(h,theta) outer-radius out-of-roundness."""
import numpy as np, json, sys, trimesh, pandas as pd
from scipy.spatial import cKDTree
from scipy.spatial.transform import Rotation as R
ROOT = '/Users/aebatirel/Documents/Code/v2d-research/data/track_3/public'
M = json.load(open('/Users/aebatirel/Documents/Code/v2d-research/work/12/out/markers_raw.json'))

def gt_up(name, ep=11):
    df = pd.read_parquet(f'{ROOT}/data/chunk-000/episode_{ep:06d}.parquet', columns=['observation.objects'])
    for o in df['observation.objects'].iloc[0]:
        if o['name'] == name:
            x, y, z, qw, qx, qy, qz = o['pose']
            Rm = R.from_quat([qx, qy, qz, qw]).as_matrix()
            return Rm.T @ np.array([0, 0, 1.]), np.array([x, y, z])
    return None, None

def run(name, n=300000, excl=0.016):
    s = trimesh.load(f'{ROOT}/mesh/{name}/{name}.glb'); g = list(s.geometry.values())[0]
    P, _ = trimesh.sample.sample_surface(g, n, seed=1); P = np.asarray(P)
    Q, _ = trimesh.sample.sample_surface(g, n, seed=2); Q = np.asarray(Q)
    a, _ = gt_up(name); a = a / np.linalg.norm(a)
    mk = np.array([q['centre'] for q in M[name] if 6.5e-3 < q['radius'] < 8.6e-3 and q['bright'] > 0.55])
    # axis point: centroid projected (cups ~ revolution), refine by circle centre at mid-height
    def cyl(X, p):
        Y = X - p; h = Y @ a; rr = Y - np.outer(h, a); return h, np.linalg.norm(rr, axis=1), rr
    p = P.mean(0)
    for _ in range(5):
        h, r, rr = cyl(P, p)
        m = (r > np.percentile(r, 60))
        p = p + rr[m].mean(0) * 0.0 + (rr[m] / r[m, None]).mean(0) * 0  # keep simple
        # least-squares circle centre in plane
        e1 = np.cross(a, [1, 0, 0]); e1 /= np.linalg.norm(e1); e2 = np.cross(a, e1)
        u, v = (P[m] - p) @ e1, (P[m] - p) @ e2
        A = np.c_[2 * u, 2 * v, np.ones(len(u))]; sol = np.linalg.lstsq(A, u * u + v * v, rcond=None)[0]
        p = p + sol[0] * e1 + sol[1] * e2
    out = {'name': name, 'axis': a.tolist(), 'p': p.tolist(), 'n_markers': len(mk)}
    for ex in (excl, 0.025):
        kP = cKDTree(mk).query(P)[0] > ex; kQ = cKDTree(mk).query(Q)[0] > ex
        A_, B_ = P[kP], Q[kQ]; T = cKDTree(B_)
        rows = []
        for ang in range(0, 360, 2):
            Rm = R.from_rotvec(a * np.radians(ang)).as_matrix()
            d = T.query((A_ - p) @ Rm.T + p)[0]
            rows.append((ang, d.mean() * 1e3, np.percentile(d, 95) * 1e3, np.percentile(d, 99) * 1e3, (d > 0.002).mean()))
        rows = np.array(rows)
        # outer wall out-of-roundness: max radius per (h 4mm, theta 5deg) bin vs ring median
        h, r, rr = cyl(A_, p)
        e1 = np.cross(a, [1, 0, 0]); e1 /= np.linalg.norm(e1); e2 = np.cross(a, e1)
        th = np.degrees(np.arctan2(rr @ e2, rr @ e1))
        hb = np.floor(h / 0.004).astype(int); tb = np.floor((th + 180) / 5).astype(int)
        key = hb * 1000 + tb; order = np.lexsort((r, key)); ks = key[order]; last = np.r_[ks[1:] != ks[:-1], True]
        kmax, rmax = ks[last], r[order][last]
        dev = []
        for hv in np.unique(kmax // 1000):
            sel = (kmax // 1000) == hv
            if sel.sum() >= 60: dev.append(rmax[sel] - np.median(rmax[sel]))
        dev = np.abs(np.concatenate(dev)) * 1e3
        out[f'excl{int(ex*1e3)}'] = dict(mean_max=float(rows[1:, 1].max()), mean_at0=float(rows[0, 1]),
                                         p95_max=float(rows[1:, 2].max()), p99_max=float(rows[1:, 3].max()),
                                         frac2mm_max=float(rows[1:, 4].max()), frac2mm_at0=float(rows[0, 4]),
                                         wall_dev_med=float(np.median(dev)), wall_dev_p95=float(np.percentile(dev, 95)),
                                         wall_dev_p99=float(np.percentile(dev, 99)), wall_dev_max=float(dev.max()),
                                         curve=rows.tolist())
        print(name, 'excl', ex, 'NN mean@0 %.2f max %.2f | p95max %.2f p99max %.2f | frac>2mm @0 %.3f max %.3f | outer-wall dev med %.2f p95 %.2f p99 %.2f max %.2f mm' % (
            rows[0, 1], rows[1:, 1].max(), rows[1:, 2].max(), rows[1:, 3].max(), rows[0, 4], rows[1:, 4].max(),
            np.median(dev), np.percentile(dev, 95), np.percentile(dev, 99), dev.max()), flush=True)
    json.dump(out, open(f'/Users/aebatirel/Documents/Code/v2d-research/work/12-verify/c1_geo_{name}.json', 'w'))

if __name__ == '__main__':
    for nm in sys.argv[1:]: run(nm)
