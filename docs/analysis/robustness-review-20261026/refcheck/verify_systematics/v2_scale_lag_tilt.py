"""V2 (verify_systematics): my own re-derivation of scale s, constant lag and the kit's frame-0 scene tilt.

Independent code (own Kabsch/Umeyama, own lag estimators, own alignment-rotation computation). Shared with the other
agent only by necessity: the kit's own registration function (v2dlb.track3_pose._register_object_body with the same
seeds / mesh budget as pipeline/score_registered.py) to get the scored body point of our mesh.
Lag estimators (both different from the other agent's speed cross-correlation):
  A  velocity regression: after a rigid fit, residual e(t) ~ -L v_gt(t)  =>  L = -<e,v>/<v,v>, iterated with the shift.
  B  RMSE(shift) with CUBIC-spline resampling of our path, rigid refit per shift, parabolic minimum.
Scale: (1) Umeyama gt->ours on kit anchors, joint; (2) registration-free: alternate the similarity fit with a
least-squares body point c of our object (our_R(t) c + our_p(t) ~ s Rw gt_anchor(t) + tw).
Also: mocap table-height check between the two objects of an episode (is mocap z the table normal?).
Usage: python -I v2_scale_lag_tilt.py OUT.json [eps]"""
import json, os, sys
import numpy as np
from scipy.interpolate import CubicSpline
from scipy.spatial.transform import Rotation as R
import trimesh
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from vload import *  # noqa
sys.path.insert(0, KIT)
from v2dlb import track3_pose as K
from v2dlb.mesh_budget import budget_mesh
from v2dlb.object_mesh import _surface_moments

# mesh library each source used: from canonical_refs.json 'tracking_mesh_library' + its notes (my own reading)
LIB_REF = {2: 'library_v3', 11: 'library_v3x', 12: 'library_v2', 18: 'library_v3', 21: 'library_v3', 24: 'library_v2',
           26: 'library_v4', 27: 'library_v2', 31: 'library_v3', 39: 'library_v3'}
LIB_PERC = {e: LIB_REF.get(e, 'library_v2') for e in CE}; LIB_PERC[18] = 'library_v2'
STALE_TF = 'runs/20261020-refsweep-ea14fdf/refs/perc2/ep{}/table_frame.npz'
SYMN = {'beige_cup', 'blue_cup', 'white_pot_lid'}


def scanp(n):
    p = f'{T3D}/mesh/{n}/{n}.glb'
    return p if os.path.exists(p) else f'{T3D}/mesh/{n}/{n}_visual.glb'


def vf(p):
    m = trimesh.load(p, force='mesh'); return np.asarray(m.vertices, float), np.asarray(m.faces, np.int64)


_RC = {}


def reg(ep, slot, n, lib):
    key = (ep, slot, n, lib)
    if key in _RC:
        return _RC[key]
    cf = f'{WORK}/reg/ep{ep}_{slot}_{n}_{lib}.npz'
    sv, sf = vf(scanp(n)); sa, _ = _surface_moments(sv, sf)
    if os.path.exists(cf):
        z = np.load(cf); ca, B = z['ca'], z['B']
    else:
        ca, B = K._register_object_body(budget_mesh(f'{REPO}/meshes/{lib}/{n}.glb', 4096, 4096), (sv, sf), sa,
                                        1_000_003 * ep + 101 * slot)
        os.makedirs(os.path.dirname(cf), exist_ok=True); np.savez(cf, ca=ca, B=B)
    _RC[key] = (np.asarray(ca), np.asarray(B), sa, sv)
    return _RC[key]


def kabsch(X, Y, scale=False):
    """Y ~ s Q X + t."""
    mx, my = X.mean(0), Y.mean(0); A, Bm = X - mx, Y - my
    U, S, Vt = np.linalg.svd(Bm.T @ A)
    d = np.sign(np.linalg.det(U @ Vt)); D = np.diag([1, 1, d])
    Q = U @ D @ Vt
    s = (S * np.diag(D)).sum() / (A ** 2).sum() if scale else 1.0
    return s, Q, my - s * Q @ mx


def resample(P, tau):
    """P(t + tau) by cubic spline, ends clamped."""
    T = len(P); t = np.arange(T)
    cs = CubicSpline(t, P, axis=0)
    return cs(np.clip(t + tau, 0, T - 1))


def lag_A(po, pg, iters=6):
    """po, pg: T x B x 3 (ours, gt). Velocity-regression lag, ours late by L (frames)."""
    L = 0.0
    for _ in range(iters):
        ps = np.stack([resample(po[:, b], L) for b in range(po.shape[1])], 1)
        _, Q, t = kabsch(ps.reshape(-1, 3), pg.reshape(-1, 3))
        e = ps @ Q.T + t - pg
        v = np.zeros_like(pg); v[1:-1] = (pg[2:] - pg[:-2]) / 2
        dL = -(e * v).sum() / (v * v).sum()
        # e ~ -(L_res) v where L_res is the remaining lag of the shifted path
        L = L + dL
    return float(L)


def lag_B(po, pg):
    taus = np.arange(-3, 3.001, 0.125); r = []
    for tau in taus:
        ps = np.stack([resample(po[:, b], tau) for b in range(po.shape[1])], 1)
        _, Q, t = kabsch(ps.reshape(-1, 3), pg.reshape(-1, 3))
        r.append(np.sqrt(((ps @ Q.T + t - pg) ** 2).sum(-1).mean()))
    r = np.array(r); k = int(np.argmin(r))
    if 0 < k < len(r) - 1:
        den = r[k - 1] - 2 * r[k] + r[k + 1]
        return float(taus[k] + (0.5 * (r[k - 1] - r[k + 1]) / den * 0.125 if den > 0 else 0)), float(r[k] * 1000), float(r[len(r) // 2] * 1000)
    return float(taus[k]), float(r[k] * 1000), float(r[len(r) // 2] * 1000)


def scale_regfree(Mo, pg, iters=50):
    """Registration-free similarity: find c_b (our body point) and s, Q, t with Ro c_b + po ~ s Q pg + t."""
    Bn = len(Mo); c = [np.zeros(3) for _ in range(Bn)]
    for _ in range(iters):
        X = np.concatenate([pg[:, b] for b in range(Bn)]); Y = np.concatenate([Mo[b][:, :3, :3] @ c[b] + Mo[b][:, :3, 3] for b in range(Bn)])
        s, Q, t = kabsch(X, Y, True)
        for b in range(Bn):
            tgt = s * pg[:, b] @ Q.T + t - Mo[b][:, :3, 3]
            c[b] = np.einsum('tji,tj->ti', Mo[b][:, :3, :3], tgt).mean(0)
    return float(s), c


def angle(a, b):
    return float(np.degrees(np.arccos(np.clip(np.dot(a, b) / np.linalg.norm(a) / np.linalg.norm(b), -1, 1))))


def analyse(ep, names, gt, ours, lib):
    T = len(gt[names[0]]); Bn = len(names)
    regs = [reg(ep, s, n, lib) for s, n in enumerate(names)]
    po = np.stack([ours[n][:, :3, :3] @ regs[s][0] + ours[n][:, :3, 3] for s, n in enumerate(names)], 1)
    pg = np.stack([gt[n][:, :3, :3] @ regs[s][2] + gt[n][:, :3, 3] for s, n in enumerate(names)], 1)
    res = {}
    s1, _, _ = kabsch(pg.reshape(-1, 3), po.reshape(-1, 3), True)
    s2, _ = scale_regfree([ours[n] for n in names], pg)
    res['scale_kit_anchor'] = round(float(s1), 4); res['scale_registration_free'] = round(s2, 4)
    res['mocap_spread_cm'] = round(float(np.sqrt(((pg.reshape(-1, 3) - pg.reshape(-1, 3).mean(0)) ** 2).sum(1).mean()) * 100), 1)
    # lag per moving object and joint
    lag = {}
    for s, n in enumerate(names):
        if np.linalg.norm(pg[:, s] - pg[0, s], axis=1).max() < 0.05:
            continue
        lb = lag_B(po[:, s:s + 1], pg[:, s:s + 1])
        lag[n] = dict(A=round(lag_A(po[:, s:s + 1], pg[:, s:s + 1]), 3), B=round(lb[0], 3), rmse_min_mm=round(lb[1], 2), rmse_0_mm=round(lb[2], 2))
    res['lag'] = lag
    # z-only lag (no rotation involved), velocity regression on the vertical component after removing the mean
    # kit frame-0 alignment rotation: ours (table frame) -> mocap. Rotation from the first object without symmetry axis.
    fixed = [s for s, n in enumerate(names) if n not in SYMN]
    if fixed or Bn == 1:
        k = fixed[0] if fixed else 0
        Ro0 = ours[names[k]][0, :3, :3] @ regs[k][1].T                    # our world <- scan body (kit convention)
        Rg0 = gt[names[k]][0, :3, :3]
        W = Rg0 @ Ro0.T
        res['kit_anchor_object'] = names[k]
        res['kit_tilt_deg'] = round(angle(W @ np.array([0, 0, 1.0]), np.array([0, 0, 1.0])), 2)
    else:
        res['kit_anchor_object'] = 'axis+direction (no fixed object)'
    return res, po, pg


def main():
    out = {}
    eps = [int(x) for x in sys.argv[2].split(',')] if len(sys.argv) > 2 else sorted(CE)
    for ep in eps:
        names, gt, _ = mocap(ep)
        d = ref_dir(ep)
        tfp = f'{d}/table_frame.npz' if d else f'{ST}/{STALE_TF.format(ep)}'
        Tt = np.load(tfp)['T_table_from_world']
        P = perc(ep)
        srcs = {'perc': ({n: np.einsum('ij,tjk->tik', Tt, P[n]) for n in names}, LIB_PERC[ep])}
        if d:
            srcs['ref'] = (refparq(ref_final(ep)), LIB_REF[ep])
        out[ep] = {'table_frame': tfp[len(ST) + 1:]}
        for k, (ours, lib) in srcs.items():
            r, po, pg = analyse(ep, names, gt, ours, lib)
            r['lib'] = lib
            out[ep][k] = r
        # mocap: lowest scan hull point of each object over the first 10 frames (both at rest at the start?)
        lows = {}
        for s, n in enumerate(names):
            sv, sf = vf(scanp(n)); hv = np.asarray(trimesh.Trimesh(sv, sf, process=False).convex_hull.vertices)
            z = np.einsum('tij,vj->tvi', gt[n][:10, :3, :3], hv)[..., 2].min(1) + gt[n][:10, 2, 3]
            mv = float(np.linalg.norm(gt[n][:10, :3, 3] - gt[n][0, :3, 3], axis=1).max() * 1000)
            lows[n] = dict(lowest_z_m=round(float(np.median(z)), 4), xy=np.round(gt[n][0, :2, 3], 3).tolist(), moved_mm_first10=round(mv, 1))
        out[ep]['mocap_lowest_first10'] = lows
        print(ep, json.dumps(out[ep]), flush=True)
        json.dump(out, open(sys.argv[1], 'w'), indent=1)


if __name__ == '__main__':
    main()
