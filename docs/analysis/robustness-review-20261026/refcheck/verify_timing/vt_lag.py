"""verify_timing: independent onset-lag measurement (27 Oct 2026, CPU).

Own method (deliberately different in details from refcheck/timing/timing.py):
  * tracked point: mocap = public scan's area-weighted surface centroid; ours = OUR mesh's own surface centroid
    (no kit registration, so a registration bug in the other check cannot leak in);
  * rest = MEAN of frames 0-4 (theirs: median); crossing = first frame k with d[k..k+2] > thr, sub-frame by linear
    interpolation between k-1 and k;
  * second, crossing-free estimator: least-squares time shift tau (and a free amplitude k) that best maps the mocap
    displacement-from-rest curve onto ours in the window [t_gt-10, t_gt+25]: d_ours(t) ~ k * d_gt(t - tau).
  * rotation onset: 10 deg from rest, full rotation for non-symmetric objects, axis swing for cups (axis = the
    distinct principal axis of each mesh's vertex cloud).
Output: JSON with per-object crossings and pooled medians. lag > 0 = ours LATE.
Usage: python -I vt_lag.py OUT.json [sources...]  (sources: perc pre ref sweep_base sweep_t4 sweep_t8)
"""
import sys, json, os, glob
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import vt_load as L
import trimesh

SYM = {'beige_cup', 'blue_cup'}


def cross(d, thr, start=5):
    T = len(d)
    for k in range(start, T - 2):
        if d[k] > thr and d[k + 1] > thr and d[k + 2] > thr:
            if d[k - 1] >= thr:
                return float(k)
            return (k - 1) + (thr - d[k - 1]) / (d[k] - d[k - 1])
    return None


def interp(d, t):
    return np.interp(t, np.arange(len(d)), d)


def shift_fit(dg, do, t1, lo=-3.0, hi=3.0):
    T = min(len(dg), len(do))
    w = np.arange(max(1, int(t1) - 10), min(T - 4, int(t1) + 25))
    best = None
    for tau in np.arange(lo, hi + 1e-9, 0.01):
        g = interp(dg, w - tau)
        y = do[w]
        k = float(g @ y / max(g @ g, 1e-12))
        r = float(((y - k * g) ** 2).sum())
        r0 = float(((y - g) ** 2).sum())
        if best is None or r < best[1]:
            best = (tau, r, k)
        if best is None or True:
            pass
    # also unit-amplitude fit
    bu = min(((tau, float(((do[w] - interp(dg, w - tau)) ** 2).sum())) for tau in np.arange(lo, hi + 1e-9, 0.01)),
             key=lambda x: x[1])
    return dict(tau_scaled=round(float(best[0]), 2), k=round(best[2], 3), tau_unit=round(float(bu[0]), 2))


def principal_axis(path):
    v = np.asarray(trimesh.load(path, force='mesh').vertices, float)
    w, U = np.linalg.eigh(np.cov((v - v.mean(0)).T))
    k = int(np.argmax([abs(w[i] - np.mean(np.delete(w, i))) for i in range(3)]))
    return U[:, k]


def rot_from_rest(M, axis=None):
    R = M[:, :3, :3]
    R0 = R[:5].mean(0); U, _, Vt = np.linalg.svd(R0); R0 = U @ Vt
    if axis is None:
        D = np.einsum('tji,jk->tik', R, R0)          # R_t^T R0
        c = np.clip((np.trace(D, axis1=1, axis2=2) - 1) / 2, -1, 1)
        return np.degrees(np.arccos(c))
    a = R @ axis; a0 = R0 @ axis
    return np.degrees(np.arccos(np.clip(a @ a0, -1, 1)))


def disp(M, c):
    P = L.point_path(M, c)
    return np.linalg.norm(P - P[:5].mean(0), axis=1), P


def main():
    out_path = sys.argv[1]
    srcs = sys.argv[2:] or ['perc', 'pre', 'ref']
    C = L.canon()
    res = []
    for ep in L.PUBLIC:
        e = C[ep]
        names, gt = L.load_mocap(ep)
        fin, pre = L.ref_paths(e)
        avail = {}
        for s in srcs:
            if s == 'perc':
                avail[s] = (L.load_npz(f"{L.STORE}/{e['perception_path']}"), L.lib_of(e, 'perc'))
            elif s == 'ref' and fin:
                avail[s] = (L.load_refpq(fin), L.lib_of(e, 'ref'))
            elif s == 'pre' and pre:
                avail[s] = (L.load_refpq(pre), L.lib_of(e, 'ref'))
            elif s.startswith('sweep_'):
                p = f"{L.STORE}/runs/20261025-sweep-a894083/results/sweep/{s[6:]}/ep{ep}/poses_world_vo.npz"
                if os.path.exists(p):
                    avail[s] = (L.load_npz(p), 'library_v2')
        for n in names:
            cg = L.surf_centroid(L.scan_mesh(n))
            dg, Pg = disp(gt[n], cg)
            axg = principal_axis(L.scan_mesh(n)) if n in SYM else None
            rg = rot_from_rest(gt[n], axg)
            row = dict(ep=ep, obj=n, T_gt=len(dg), gt_max_cm=round(float(dg.max() * 100), 2),
                       gt_rot_max_deg=round(float(rg.max()), 1))
            for thr, key in ((0.01, '1cm'), (0.02, '2cm')):
                row[f'gt_{key}'] = cross(dg, thr)
            row['gt_10deg'] = cross(rg, 10.0)
            for s, (P, lib) in avail.items():
                if n not in P:
                    continue
                M = P[n]
                co = L.surf_centroid(L.our_mesh(lib, n))
                do, _ = disp(M, co)
                axo = principal_axis(L.our_mesh(lib, n)) if n in SYM else None
                ro = rot_from_rest(M, axo)
                d = dict(T=len(do), max_cm=round(float(do.max() * 100), 2))
                for thr, key in ((0.01, '1cm'), (0.02, '2cm')):
                    t = cross(do, thr)
                    d[key] = t
                    if t is not None and row[f'gt_{key}'] is not None:
                        d[f'lag_{key}'] = round(t - row[f'gt_{key}'], 3)
                t = cross(ro, 10.0); d['10deg'] = t
                if t is not None and row['gt_10deg'] is not None:
                    d['lag_10deg'] = round(t - row['gt_10deg'], 3)
                if row['gt_1cm'] is not None and row['gt_max_cm'] > 3:
                    d.update(shift_fit(dg, do, row['gt_1cm']))
                row[s] = d
            res.append(row)
            print(ep, n, {k: (v if not isinstance(v, dict) else {kk: vv for kk, vv in v.items() if 'lag' in kk or 'tau' in kk})
                          for k, v in row.items() if k not in ('ep', 'obj')}, flush=True)
    json.dump(res, open(out_path, 'w'), indent=1)


if __name__ == '__main__':
    main()
