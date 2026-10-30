#!/usr/bin/env python3
"""Physics fit of perceived object trajectories (2026-10-30; owner's inverse-dynamics idea; v1 pre-registered in
docs/research/physics-2026-10-30/README.md). Ground-truth-free perception refinement, same in/out layout as
pipeline/refine.py, so pipeline/mkref.py and pipeline/score_registered.py consume the output unchanged.

For every object and frame, the perceived pose may move by a small world-frame correction (prior: 1 cm, 3 deg). The
corrected trajectory must be explainable by physics: the Newton-Euler wrench it needs, m (a - g) and I_w alpha +
omega x I_w omega about the centre of mass, minus the best non-negative combination of contact forces in friction
pyramids (mu 1.0) from the contacts available in that frame, is the dynamics violation (normalised by m g and
m g * 10 cm). Contact candidates per frame, from the perceived scene (fixed in the object frame):
  hands   perceived hand keypoints (not the wrists) within 6 cm of the object's surface, snapped onto it (force along
          the inward surface normal);
  table   the object's surface samples within 1 cm of the table plane (force up);
  objects the object's surface samples within 1 cm of another object's surface (force along that object's outward
          normal; the reaction on the other object is not modelled in v1).
Plus a table-penetration penalty on the lowest samples (2 mm). Solved with scipy least_squares (sparse finite-difference
Jacobian; the inner non-negative least squares runs per frame). Outputs: poses.npz / poses_world_vo.npz with the
corrected poses (world_T_cam copied), phys_fit.json (violation before/after, frames no contact can explain, per-object
corrections) and phys_fit_aux.npz.

Usage: phys_fit.py IN_DIR OUT_DIR --meshes DIR --props PROPS.json [--w_dyn 1] [--max_nfev 60]
  IN_DIR: poses.npz, poses_world_vo.npz, hands_refined.npz (else hands.npz), table_frame.npz (mkref).
No ground truth is read (refine.assert_inference_input guards every input path).
"""
import argparse, json, os, sys, time
import numpy as np, trimesh
from scipy.optimize import least_squares, nnls
from scipy.sparse import lil_matrix
from scipy.spatial.transform import Rotation as Rot

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from refine import assert_inference_input  # noqa: E402

G = np.array([0.0, 0.0, -9.81])
MU, L_REF = 1.0, 0.10


def edges(d, mu=MU):
    """Four friction-pyramid edge directions around the push direction d (unit)."""
    a = np.array([1.0, 0, 0]) if abs(d[0]) < 0.9 else np.array([0, 1.0, 0])
    t1 = np.cross(d, a); t1 /= np.linalg.norm(t1); t2 = np.cross(d, t1)
    E = np.stack([d + mu * t1, d - mu * t1, d + mu * t2, d - mu * t2])
    return E / np.linalg.norm(E, axis=1, keepdims=True)


def spread(P, k):
    """Up to k farthest-point picks (indices) from P."""
    if len(P) <= k:
        return np.arange(len(P))
    sel = [int(np.argmin(P[:, 2]))]; d = np.linalg.norm(P - P[sel[0]], axis=1)
    while len(sel) < k:
        i = int(np.argmax(d)); sel.append(i); d = np.minimum(d, np.linalg.norm(P - P[i], axis=1))
    return np.array(sel)


class Obj:
    def __init__(self, name, mesh_path, props):
        self.name = name
        self.mesh = trimesh.load(mesh_path, force='mesh')
        self.pq = trimesh.proximity.ProximityQuery(self.mesh)
        self.S = trimesh.sample.sample_surface_even(self.mesh, 400, seed=0)[0]
        ph = props[name]['physics']
        self.m = float(ph['mass_kg']); self.c = np.array(ph['com_m'], float); self.I = np.array(ph['inertia_kgm2'], float)

    def normals(self, pts):
        """Closest surface points and outward normals (object frame)."""
        cp, dist, tri = self.pq.on_surface(pts)
        n = self.mesh.face_normals[tri]
        return cp, dist, n


def candidates(objs, O, H, Hok, tz, hand_cm=6.0, near_cm=1.0, k_hand=8, k_sup=6, k_obj=6):
    """Per object, per frame: list of (point in object frame (3,), push direction in the table frame (3,), kind)."""
    T = O.shape[1]; out = [[[] for _ in range(T)] for _ in objs]; stats = {o.name: dict(hand=0, table=0, object=0) for o in objs}
    kp = [k for k in range(1, 21)]
    for j, o in enumerate(objs):
        for t in range(T):
            R, p = O[j, t, :3, :3], O[j, t, :3, 3]
            W = o.S @ R.T + p                                              # samples in the table frame
            # table support
            low = np.nonzero(W[:, 2] - tz < near_cm / 100)[0]
            for i in low[spread(W[low], k_sup)] if len(low) else []:
                out[j][t].append((o.S[i], np.array([0, 0, 1.0]), 'table')); stats[o.name]['table'] += 1
            # hands
            for s in H:
                if not Hok[s][t]:
                    continue
                X = (H[s][t, kp] - p) @ R                                  # keypoints in the object frame
                cp, dist, n = o.normals(X)
                near = np.nonzero(dist < hand_cm / 100)[0]
                for i in near[np.argsort(dist[near])][:k_hand]:
                    out[j][t].append((cp[i], -(R @ n[i]), 'hand')); stats[o.name]['hand'] += 1
            # other objects
            for k, o2 in enumerate(objs):
                if k == j:
                    continue
                R2, p2 = O[k, t, :3, :3], O[k, t, :3, 3]
                X2 = (W - p2) @ R2                                         # j's samples in k's frame
                cp, dist, n = o2.normals(X2)
                close = np.nonzero(dist < near_cm / 100)[0]
                for i in close[spread(W[close], k_obj)] if len(close) else []:
                    out[j][t].append((o.S[i], R2 @ n[i], 'object')); stats[o.name]['object'] += 1
    return out, stats


def poses_from(x, O0):
    """x (T*6,) corrections -> (T,4,4) corrected poses (world-frame rotation and translation corrections)."""
    T = O0.shape[0]; d = x.reshape(T, 6); O = O0.copy()
    O[:, :3, :3] = Rot.from_rotvec(d[:, 3:]).as_matrix() @ O0[:, :3, :3]
    O[:, :3, 3] = O0[:, :3, 3] + d[:, :3]
    return O


def wrench_needed(o, O, dt):
    """(T,6) required wrench m(a - g), I_w alpha + w x I_w w (central differences; ends copy their neighbours)."""
    T = O.shape[0]; R = O[:, :3, :3]; c = np.einsum('tij,j->ti', R, o.c) + O[:, :3, 3]
    a = np.zeros((T, 3)); a[1:-1] = (c[2:] - 2 * c[1:-1] + c[:-2]) / dt ** 2
    rel = Rot.from_matrix(np.einsum('tij,tkj->tik', R[1:], R[:-1])).as_rotvec() / dt      # omega between frames (world)
    w = np.zeros((T, 3)); w[1:-1] = (rel[1:] + rel[:-1]) / 2
    al = np.zeros((T, 3)); al[1:-1] = (rel[1:] - rel[:-1]) / dt
    Iw = np.einsum('tij,jk,tlk->til', R, o.I, R)
    tau = np.einsum('tij,tj->ti', Iw, al) + np.cross(w, np.einsum('tij,tj->ti', Iw, w))
    F = o.m * (a - G)
    F[[0, -1]] = F[[1, -2]]; tau[[0, -1]] = tau[[1, -2]]
    return np.concatenate([F, tau], 1), c


def violation(o, O, cand, dt, eps=1e-3):
    """(T,6) unexplained wrench, normalised (force / m g, torque / m g L)."""
    Wn, c = wrench_needed(o, O, dt); T = len(O); v = np.zeros((T, 6)); sc = np.r_[[o.m * 9.81] * 3, [o.m * 9.81 * L_REF] * 3]
    for t in range(T):
        cs = cand[t]
        if not cs:
            v[t] = Wn[t] / sc; continue
        R = O[t, :3, :3]; cols = []
        for x, d, _ in cs:                                                 # push directions are table-frame already
            r = R @ (x - o.c)
            for e in edges(d):
                cols.append(np.r_[e, np.cross(r, e)])
        A = np.array(cols).T / sc[:, None]; b = Wn[t] / sc
        Aa = np.vstack([A, np.sqrt(eps) * np.eye(A.shape[1])]); ba = np.r_[b, np.zeros(A.shape[1])]
        lam, _ = nnls(Aa, ba, maxiter=200)
        v[t] = b - A @ lam
    return v


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('inp'); ap.add_argument('out'); ap.add_argument('--meshes', required=True); ap.add_argument('--props', required=True)
    ap.add_argument('--fps', type=float, default=20.0); ap.add_argument('--w_dyn', type=float, default=1.0)
    ap.add_argument('--sig_p', type=float, default=0.01); ap.add_argument('--sig_r_deg', type=float, default=3.0)
    ap.add_argument('--max_nfev', type=int, default=60)
    a = ap.parse_args(); t0 = time.time(); dt = 1.0 / a.fps
    for f in ('poses.npz', 'poses_world_vo.npz', 'table_frame.npz'):
        assert_inference_input(f'{a.inp}/{f}')
    hp = f'{a.inp}/hands_refined.npz' if os.path.exists(f'{a.inp}/hands_refined.npz') else f'{a.inp}/hands.npz'
    assert_inference_input(hp)
    P = np.load(f'{a.inp}/poses.npz'); names = [k[6:] for k in P.files if k.startswith('cam_T_')]
    WV = np.load(f'{a.inp}/poses_world_vo.npz'); TF = np.load(f'{a.inp}/table_frame.npz'); HN = np.load(hp)
    Ttab = TF['T_table_from_world']; tz = float(TF['table_z']); Tinv = np.linalg.inv(Ttab)
    props = json.load(open(a.props))
    objs = [Obj(n, f'{a.meshes}/{n}.glb', props) for n in names]
    O = np.stack([Ttab @ WV[n] for n in names])                            # (B,T,4,4) table frame
    T = O.shape[1]
    H = {s: HN[f'joints_{s}'] @ Ttab[:3, :3].T + Ttab[:3, 3] for s in ('left', 'right')}
    Hok = {s: HN[f'valid_{s}'].astype(bool) for s in ('left', 'right')}
    cand, cstats = candidates(objs, O, H, Hok, tz)
    print(f'candidates {cstats} ({time.time() - t0:.0f} s)', flush=True)
    rep = dict(objects={}, args=vars(a), frames=T)
    Onew = O.copy()
    for j, o in enumerate(objs):
        sc_x = np.tile(np.r_[[a.sig_p] * 3, [np.radians(a.sig_r_deg)] * 3], T)

        def fun(x):
            Oc = poses_from(x, O[j])
            v = violation(o, Oc, cand[j], dt).ravel() * a.w_dyn
            Wz = np.einsum('tij,sj->tsi', Oc[:, :3, :3], o.S)[..., 2] + Oc[:, None, :3, 3][..., 2]
            pen = np.minimum(np.sort(Wz, 1)[:, :10] - tz, 0.0).ravel() / 0.002
            return np.r_[v, x / sc_x, pen]

        n_v, n_x, n_p = T * 6, T * 6, T * 10
        J = lil_matrix((n_v + n_x + n_p, T * 6), dtype=np.int8)
        for t in range(T):
            for u in range(max(0, t - 1), min(T, t + 2)):
                J[t * 6:(t + 1) * 6, u * 6:(u + 1) * 6] = 1
            J[n_v + t * 6:n_v + (t + 1) * 6, t * 6:(t + 1) * 6] = 1
            J[n_v + n_x + t * 10:n_v + n_x + (t + 1) * 10, t * 6:(t + 1) * 6] = 1
        x0 = np.zeros(T * 6)
        v0 = violation(o, O[j], cand[j], dt); t1 = time.time()
        r = least_squares(fun, x0, jac_sparsity=J.tocsr(), method='trf', x_scale=sc_x, max_nfev=a.max_nfev, verbose=0)
        Onew[j] = poses_from(r.x, O[j]); v1 = violation(o, Onew[j], cand[j], dt)
        d = r.x.reshape(T, 6)
        nv0, nv1 = np.linalg.norm(v0[:, :3], axis=1), np.linalg.norm(v1[:, :3], axis=1)
        none = [t for t in range(T) if not cand[j][t]]
        rep['objects'][o.name] = dict(
            mass_kg=o.m, nfev=int(r.nfev), seconds=round(time.time() - t1, 1), cost0=float(np.sum(fun(x0) ** 2) / 2), cost1=float(r.cost),
            force_violation_mg_median_before=round(float(np.median(nv0)), 3), force_violation_mg_median_after=round(float(np.median(nv1)), 3),
            force_violation_mg_p90_before=round(float(np.percentile(nv0, 90)), 3), force_violation_mg_p90_after=round(float(np.percentile(nv1, 90)), 3),
            frames_violation_gt_1mg_before=int((nv0 > 1).sum()), frames_violation_gt_1mg_after=int((nv1 > 1).sum()),
            frames_without_contact=len(none), correction_cm_median=round(float(np.median(np.linalg.norm(d[:, :3], axis=1)) * 100), 2),
            correction_cm_max=round(float(np.linalg.norm(d[:, :3], axis=1).max() * 100), 2),
            correction_deg_median=round(float(np.degrees(np.median(np.linalg.norm(d[:, 3:], axis=1)))), 2))
        print(o.name, json.dumps(rep['objects'][o.name]), flush=True)
    os.makedirs(a.out, exist_ok=True)
    Wnew = {n: Tinv @ Onew[j] for j, n in enumerate(names)}
    np.savez(f'{a.out}/poses_world_vo.npz', **{n: Wnew[n].astype(np.float64) for n in names})
    keep = {k: P[k] for k in P.files if not k.startswith('cam_T_')}
    wTc = P['world_T_cam']
    camT = {f'cam_T_{n}': np.einsum('tij,tjk->tik', np.linalg.inv(wTc), Wnew[n]).astype(np.float32) for n in names}
    np.savez(f'{a.out}/poses.npz', **keep, **camT)
    rep['seconds'] = round(time.time() - t0, 1)
    json.dump(rep, open(f'{a.out}/phys_fit.json', 'w'), indent=1)
    print('wrote', a.out, f'({rep["seconds"]} s)')


if __name__ == '__main__':
    main()
