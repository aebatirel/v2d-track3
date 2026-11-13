"""M6 [D]: how much does the 'placement error' of a placed mesh depend on the registration used to define the ideal?
For already-kit-scored SAM sim3 meshes only (validation, no new mesh scored): (i) symmetric trimmed Sim(3) (keep .9),
(ii) untrimmed symmetric Sim(3), (iii) my re-implementation of the kit's AUC.py _register_object_body (RMS-radius scale,
one-sided trimmed rigid ICP, 25 starts, best by symmetric mean) -> static ADD as mesh_metric defines it."""
import sys, json
import numpy as np
from vlib import *
from scipy.spatial import cKDTree
SYM = kit_sym()

def surf_moments(v, f):
    tri = v[f]; ar = tri_area(v, f); k = ar > 1e-12; tri, ar = tri[k], ar[k]
    c = (tri.mean(1) * ar[:, None]).sum(0) / ar.sum()
    cen = tri - c
    sq = np.einsum('tij,tij->ti', cen, cen).sum(1)
    cr = np.einsum('ti,ti->t', cen[:, 0], cen[:, 1]) + np.einsum('ti,ti->t', cen[:, 0], cen[:, 2]) + np.einsum('ti,ti->t', cen[:, 1], cen[:, 2])
    return c, float(np.sqrt((ar * (sq + cr) / 6).sum() / ar.sum()))

def kit_like_register(cv, cf, rv, rf, seed):
    cc, cr = surf_moments(cv, cf); rc, rr = surf_moments(rv, rf)
    sc = rr / cr
    cp = (sample(cv, cf, 3000, seed) - cc) * sc; rp = sample(rv, rf, 3000, seed + 7) - rc
    tr = cKDTree(rp); best = None
    ca, Va, _ = pca_frame(cp); cb, Vb, _ = pca_frame(rp)
    starts = [np.eye(3)] + [Vb @ M @ Va.T for M in cube_rots()]
    for R in starts:
        t = rp.mean(0) - R @ cp.mean(0); prev = None
        for _ in range(40):
            X = cp @ R.T + t; d, i = tr.query(X); k = d <= np.quantile(d, 0.9)
            _, dR, dt = umeyama(X[k], rp[i[k]], scale=False)
            R = dR @ R; t = dR @ t + dt
            e = d[k].mean()
            if prev is not None and abs(prev - e) <= 1e-8 * max(prev, 1): break
            prev = e
        X = cp @ R.T + t
        sd = 0.5 * (tr.query(X)[0].mean() + cKDTree(X).query(rp)[0].mean())
        if best is None or sd < best[0]: best = (sd, R, t)
    _, R, off = best
    anchor = rc
    ca_ = cc + R.T @ (anchor - rc - off) / sc
    return ca_ - anchor, R, rc

def add_static(da, R, q, kind, axis):
    moved = q @ R + da
    if kind is None: return float(np.linalg.norm(moved - q, axis=1).mean())
    angs = np.radians(np.arange(0, 360, 1.0)) if kind == 'axial' else [0, math.pi]
    return min(float(np.linalg.norm(moved - q @ axis_rot(axis, a).T, axis=1).mean()) for a in angs)

def add_T(T, q, kind, axis, c):
    s, R, t = T; p = ((q - t) @ R) / s
    if kind is None: return float(np.linalg.norm(p - q, axis=1).mean())
    angs = np.radians(np.arange(0, 360, 1.0)) if kind == 'axial' else [0, math.pi]
    return min(float(np.linalg.norm(p - ((q - c) @ axis_rot(axis, a).T + c), axis=1).mean()) for a in angs)

if __name__ != "__main__":
    todo = []
else:
    todo = [a.split(':') for a in sys.argv[1:]]
for obj, seed in todo:
    v, f = load(f'{GEN}/sam3d_sim3/{obj}_{KTAG[obj]}_s{seed}.ply'); sv, sf = load_scan(obj)
    kind = SYM.get(obj); c = centroid(sv, sf)
    axis = sym_axis(sample(sv, sf, 6000, 14), kind) if kind else None
    q = sample(sv, sf, 500, 0)
    A = sample(v, f, 4000, 11); B = sample(sv, sf, 4000, 12)
    out = {}
    for keep in (0.9, 1.0):
        tr, un, T = multi_start(A, B, scale=True, keep=keep)
        cm = centroid(v, f)
        out[f'sim3_keep{keep}'] = (round(add_T(T, q, kind, axis, c) * 1e3, 1), round(float(np.linalg.norm(apply(T, cm[None])[0] - cm)) * 1e3, 1))
    kit = []
    for s in (1000003 * 22, 11, 22):
        da, R, rc = kit_like_register(v, f, sv, sf, s)
        kit.append(add_static(da, R, q - rc, kind, axis) * 1e3)
    out['kitlike_ADD_3seeds'] = [round(x, 1) for x in kit]
    print(obj, seed, json.dumps(out), flush=True)
