"""refcheck/systematics: systematic geometric errors of our object paths vs mocap (PUBLIC episodes; diagnostics only).

Inference never reads this script's outputs; mocap is read only here, after inference, as allowed for development.

Sources per episode (refcheck/resolve/canonical_refs.json):
  ref   final reference parquet (what the policy tracks; table frame, our mesh body frame)
  pre   e2s_reference.parquet (mkref output before contact retarget; rest settle can move objects)
  perc  canonical perception poses_world_vo.npz (camera-0 frame), mapped into the table frame with the reference's
        table_frame.npz (or, for the 10 episodes without a canonical reference, the stale 20 Oct refsweep table frame)
Comparable centres: the kit's registration (v2dlb.track3_pose._register_object_body, same seeds and mesh budget as
pipeline/score_registered.py) gives, for our mesh, the body point that corresponds to the scan's surface centroid
("kit anchor") and the body rotation B (our body axes -> scan body axes). Our poses are converted with the kit's
_convert_object_body, so ours and mocap are compared in the scan's body convention. The plain surface-centroid
version (our mesh's centroid vs the scan's centroid) is reported for the scale fit as a cross-check.

Checks (all per source and episode):
  1 scale     Umeyama similarity fit mocap -> ours of object centres (s = our length / true length; s < 1 = shrunk),
              jointly and per object; inter-object distance at rest; displacement ratio where mocap moved > 2 cm
  2 time      frame counts; cross-correlation of centre-speed profiles (sub-frame peak); RMSE-vs-shift minimum
  3 up axis   angle between our table normal and mocap z under (a) the kit's own frame-0 scene alignment,
              (b) the best rigid fit of centre positions, (c) each object's rest orientation
  4 rest      lowest mesh point above our table plane vs lowest scan point above the mocap table height
              (mocap table = lowest resting object's median lowest scan point); centre-height error; float/sink mm
  5 rotation  mean signed tilt (swing of the up axis, scan body frame) at rest frames; kit-aligned residual rotation
AUC cost: oracle corrections of each systematic (scale by 1/s, time shift, rest heights, tilt bias, all) re-scored
with the kit's registered AUC (in-process, identical functions/seeds to score_registered.py; verified separately).
Usage: python -I systematics.py OUT.json [--eps 2,11,...] [--sources ref,pre,perc] [--no_auc]
"""
import argparse, json, os, sys, time
import numpy as np
from scipy.spatial.transform import Rotation as Rot, Slerp
from scipy.ndimage import gaussian_filter1d

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sysload import *                                                   # noqa: E402,F401
from v2dlb import track3_pose as T3                                     # noqa: E402
from v2dlb.mesh_budget import budget_mesh                               # noqa: E402
from v2dlb.object_mesh import _surface_moments                          # noqa: E402
from v2dlb.mesh_common import _sample_mesh_surface                      # noqa: E402
from v2dlb.object_pose import _add_auc                                  # noqa: E402

WORK = f'{RC}/work/systematics'
STALE = 'runs/20261020-refsweep-ea14fdf/refs/perc2/ep{}'
Z = np.array([0.0, 0.0, 1.0])
_GEOM, _REG = {}, {}


def host_geometry(n, slot, n_points=1000):
    key = (n, slot)
    if key not in _GEOM:
        v, f = mesh_vf(scan_path(n))
        c, r = _surface_moments(v, f)
        pts = _sample_mesh_surface(v, f, n_points, 7 + slot) - c
        axis, order = np.zeros(3), 0
        if n in SYM:
            w, U = np.linalg.eigh(np.cov(pts.T))
            if SYM[n] == 'half':
                axis, order = U[:, 0], 2
            else:
                k = int(np.argmax([abs(w[i] - np.mean(np.delete(w, i))) for i in range(3)]))
                axis, order = U[:, k], 360
        hull = np.asarray(trimesh.Trimesh(v, f, process=False).convex_hull.vertices, float)   # lowest point lies on the hull
        _GEOM[key] = dict(v=v, f=f, anchor=c, radius=r, points=pts, axis=axis, order=order, hull=hull)
    return _GEOM[key]


def registration(ep, slot, n, mesh_path):
    key = (ep, slot, mesh_path)
    if key not in _REG:
        H = host_geometry(n, slot)
        cf = f"{WORK}/regcache/ep{ep}_s{slot}_{mesh_path.replace('/', '_')}.npz"
        if os.path.exists(cf):
            z = np.load(cf); ca, R = z['ca'], z['R']
        else:
            cand = budget_mesh(mesh_path, 4096, 4096)
            ca, R = T3._register_object_body(cand, (H['v'], H['f']), H['anchor'], 1_000_003 * ep + 101 * slot)
            os.makedirs(os.path.dirname(cf), exist_ok=True); np.savez(cf, ca=ca, R=R)
        ov, of = mesh_vf(mesh_path)
        cc, cr = _surface_moments(ov, of)
        hull = np.asarray(trimesh.Trimesh(ov, of, process=False).convex_hull.vertices, float)
        _REG[key] = dict(anchor=ca, R=R, centroid=cc, radius=cr, low_v=hull)
    return _REG[key]


# ------------------------------------------------------------------ geometry helpers
def to7(M):
    return np.concatenate([M[:, :3, 3], Rot.from_matrix(M[:, :3, :3]).as_quat()], 1)


def from7(A):
    return mats(A[:, :3], A[:, 3:])


def umeyama(X, Y, with_scale=True):
    """Y ~ s R X + t (least squares). Returns s, R, t, rmse."""
    mx, my = X.mean(0), Y.mean(0)
    Xc, Yc = X - mx, Y - my
    S = Yc.T @ Xc / len(X)
    U, D, Vt = np.linalg.svd(S)
    E = np.eye(3); E[2, 2] = np.sign(np.linalg.det(U @ Vt))
    R = U @ E @ Vt
    s = float(np.trace(np.diag(D) @ E) / (Xc ** 2).sum(1).mean()) if with_scale else 1.0
    t = my - s * R @ mx
    rmse = float(np.sqrt(((Y - (s * X @ R.T + t)) ** 2).sum(1).mean()))
    return s, R, t, rmse


def angle_deg(a, b):
    return float(np.degrees(np.arctan2(np.linalg.norm(np.cross(a, b)), np.dot(a, b))))


def swing_rotvec(u_from, u_to):
    """Rotation vector of the minimal rotation taking unit vectors u_from -> u_to (rows)."""
    c = np.cross(u_from, u_to); s = np.linalg.norm(c, axis=-1); d = np.sum(u_from * u_to, -1)
    ang = np.arctan2(s, d)
    ax = c / np.maximum(s, 1e-12)[..., None]
    return ax * ang[..., None]


def rest_segments(P, Rm, T, move_mm=5.0, move_deg=3.0, margin=3):
    """Mocap rest frames of one object: before its first motion and after its last (scan-centroid motion)."""
    d0 = np.linalg.norm(P - P[0], axis=1) * 1000
    a0 = np.degrees(Rot.from_matrix(np.einsum('tji,jk->tik', Rm, Rm[0])).magnitude())
    dl = np.linalg.norm(P - P[-1], axis=1) * 1000
    al = np.degrees(Rot.from_matrix(np.einsum('tji,jk->tik', Rm, Rm[-1])).magnitude())
    mv0 = np.where((d0 > move_mm) | (a0 > move_deg))[0]
    mvl = np.where((dl > move_mm) | (al > move_deg))[0]
    if not len(mv0):
        return dict(pre=np.arange(T), post=np.array([], int), moves=False)
    first = mv0[0]
    last = mvl[-1] if len(mvl) else first                      # a jump at the start only: rests from then on
    pre = np.arange(0, max(0, first - margin))
    post = np.arange(min(T, last + 1 + margin), T)
    return dict(pre=pre, post=post, moves=True, first_motion=int(first), last_motion=int(last))


def speed(P, sigma=1.0):
    Ps = gaussian_filter1d(P, sigma, axis=0, mode='nearest') if sigma else P
    v = np.zeros(len(P))
    v[1:-1] = np.linalg.norm(Ps[2:] - Ps[:-2], axis=1) / 2
    v[0], v[-1] = v[1], v[-2]
    return v


def xcorr_lag(vo, vg, maxlag=15):
    """Lag L (frames) maximising sum_t vo(t) vg(t - L): L > 0 = ours LATE. Parabolic sub-frame peak."""
    a, b = vo - vo.mean(), vg - vg.mean()
    lags = np.arange(-maxlag, maxlag + 1)
    cc = []
    for L in lags:
        if L >= 0:
            x, y = a[L:], b[:len(b) - L]
        else:
            x, y = a[:L], b[-L:]
        cc.append(float((x * y).sum() / (np.linalg.norm(x) * np.linalg.norm(y) + 1e-12)))
    cc = np.array(cc); k = int(np.argmax(cc))
    sub = 0.0
    if 0 < k < len(cc) - 1:
        den = cc[k - 1] - 2 * cc[k] + cc[k + 1]
        sub = 0.5 * (cc[k - 1] - cc[k + 1]) / den if den < 0 else 0.0
    return float(lags[k] + sub), float(cc[k]), float(cc[maxlag])


def shift_path(A7, L):
    """ours'(t) = ours(t + L) by linear / slerp interpolation (clamped at the ends)."""
    T = len(A7); tq = np.clip(np.arange(T) + L, 0, T - 1)
    pos = np.stack([np.interp(tq, np.arange(T), A7[:, k]) for k in range(3)], 1)
    rot = Slerp(np.arange(T), Rot.from_quat(A7[:, 3:]))(tq).as_quat()
    return np.concatenate([pos, rot], 1)


# ------------------------------------------------------------------ kit scoring (mirrors pipeline/score_registered.py)
def kit_prepare(ep, names, ours7, gt, H, REG):
    B = len(names)
    ach = np.stack([ours7[n] for n in names], 1)[:, None].copy()             # T,1,B,7
    ref = np.stack([to7(gt[n]) for n in names], 1)[:, None].copy()
    for s in range(B):
        ach[:, :, s] = T3._convert_object_body(ach[:, :, s], REG[s]['anchor'], REG[s]['R'])
        ref[:, :, s, :3] += np.einsum('...ij,j->...i', T3._rotation_matrix(ref[:, :, s, 3:]), H[s]['anchor'])
    return ach, ref


def kit_W(ach, ref, axes):
    """The rotation of the kit's _align_registered_scene (world 0)."""
    fixed = [i for i, a in enumerate(axes) if not np.any(a)]
    if fixed or ach.shape[2] == 1:
        k = fixed[0] if fixed else 0
        return T3._rotation_matrix(ref[0, 0, k, 3:]) @ T3._rotation_matrix(ach[0, 0, k, 3:]).T
    ar = T3._rotation_matrix(ref[0, 0, 0, 3:]) @ axes[0]
    aa = T3._rotation_matrix(ach[0, 0, 0, 3:]) @ axes[0]
    dr = ref[0, 0, 1, :3] - ref[0, 0, 0, :3]
    da = ach[0, 0, 1, :3] - ach[0, 0, 0, :3]
    return T3._axis_basis(ar, dr) @ T3._axis_basis(aa, da).T


def kit_auc(ep, names, ours7, gt, H, REG):
    ach, ref = kit_prepare(ep, names, ours7, gt, H, REG)
    axes = [h['axis'] for h in H]; orders = [h['order'] for h in H]
    al = T3._align_registered_scene(ach, ref, axes)
    vals = [T3._symmetry_point_errors(al[:, :, i], ref[:, :, i], H[i]['points'], axes[i], orders[i]) for i in range(len(names))]
    per = {n: round(float(_add_auc(vals[i][..., None])), 4) for i, n in enumerate(names)}
    return round(float(_add_auc(np.stack(vals, -1))), 4), per, al, ref


# ------------------------------------------------------------------ one source
def analyse(ep, names, gt, ours, mesh_lib, table_z, H, label):
    T = len(gt[names[0]])
    B = len(names)
    mp = {n: (our_mesh_path(mesh_lib, n) if mesh_lib else scan_path(n)) for n in names}
    REG = [registration(ep, s, n, mp[n]) for s, n in enumerate(names)]
    out = dict(source=label, mesh_lib=mesh_lib or 'public scans', frames=dict(ours=int(len(ours[names[0]])), mocap=int(T)))
    ours7 = {n: to7(ours[n]) for n in names}
    ach, ref = kit_prepare(ep, names, ours7, gt, H, REG)
    pc_o = ach[:, 0, :, :3]; pc_g = ref[:, 0, :, :3]                          # T,B,3 kit-anchor centres
    Ro = T3._rotation_matrix(ach[:, 0, :, 3:]); Rg = T3._rotation_matrix(ref[:, 0, :, 3:])  # T,B,3,3 scan body conv.
    sc_o = np.stack([centre_path(ours[n], REG[s]['centroid']) for s, n in enumerate(names)], 1)   # surface centroids
    sc_g = np.stack([centre_path(gt[n], H[s]['anchor']) for s, n in enumerate(names)], 1)
    rest = [rest_segments(pc_g[:, s], Rg[:, s], T) for s in range(B)]
    out['registration'] = {n: dict(rot_deg=round(float(np.degrees(Rot.from_matrix(REG[s]['R']).magnitude())), 2),
                                   anchor_vs_centroid_mm=round(float(np.linalg.norm(REG[s]['anchor'] - REG[s]['centroid']) * 1000), 1),
                                   radius_ratio_ours_over_scan=round(REG[s]['radius'] / H[s]['radius'], 4))
                           for s, n in enumerate(names)}
    out['rest'] = {n: {k: (v if not isinstance(v, np.ndarray) else [int(v[0]), int(v[-1])] if len(v) else [])
                       for k, v in rest[s].items()} for s, n in enumerate(names)}

    # ---- 1 scale
    sc = {}
    X, Y = pc_g.reshape(-1, 3), pc_o.reshape(-1, 3)
    s_j, R_j, t_j, rm_s = umeyama(X, Y)
    _, _, _, rm_r = umeyama(X, Y, False)
    s_inv = 1.0 / umeyama(Y, X)[0]
    s_c = umeyama(sc_g.reshape(-1, 3), sc_o.reshape(-1, 3))[0]
    sp = float(np.sqrt(((X - X.mean(0)) ** 2).sum(1).mean()) * 100)
    sc['joint'] = dict(s=round(s_j, 4), s_from_inverse_fit=round(s_inv, 4), s_surface_centroids=round(s_c, 4),
                       mocap_spread_cm=round(sp, 1), rmse_rigid_mm=round(rm_r * 1000, 1), rmse_similarity_mm=round(rm_s * 1000, 1))
    sc['per_object'] = {}
    for s, n in enumerate(names):
        ss, _, _, r1 = umeyama(pc_g[:, s], pc_o[:, s]); _, _, _, r0 = umeyama(pc_g[:, s], pc_o[:, s], False)
        spn = float(np.sqrt(((pc_g[:, s] - pc_g[:, s].mean(0)) ** 2).sum(1).mean()) * 100)
        dg = np.linalg.norm(pc_g[:, s] - pc_g[0, s], axis=1); do = np.linalg.norm(pc_o[:, s] - pc_o[0, s], axis=1)
        m = dg > 0.02
        sc['per_object'][n] = dict(s=round(ss, 4) if spn > 2 else None, mocap_spread_cm=round(spn, 1),
                                   rmse_rigid_mm=round(r0 * 1000, 1), rmse_similarity_mm=round(r1 * 1000, 1),
                                   disp_frames_over_2cm=int(m.sum()),
                                   disp_ratio_median=round(float(np.median(do[m] / dg[m])), 4) if m.sum() >= 5 else None,
                                   disp_ratio_iqr=[round(float(q), 4) for q in np.percentile(do[m] / dg[m], [25, 75])] if m.sum() >= 5 else None,
                                   peak_disp_cm=[round(float(do.max() * 100), 1), round(float(dg.max() * 100), 1)])
    if B == 2:
        fr = np.intersect1d(rest[0]['pre'], rest[1]['pre']) if len(rest[0]['pre']) and len(rest[1]['pre']) else np.arange(1)
        if not len(fr):
            fr = np.arange(1)
        do = np.median(np.linalg.norm(pc_o[fr, 1] - pc_o[fr, 0], axis=1)); dg = np.median(np.linalg.norm(pc_g[fr, 1] - pc_g[fr, 0], axis=1))
        sc['inter_object_rest'] = dict(frames=len(fr), ours_cm=round(float(do * 100), 2), mocap_cm=round(float(dg * 100), 2),
                                       ratio=round(float(do / dg), 4), diff_mm=round(float((do - dg) * 1000), 1))
    out['scale'] = sc

    # ---- 2 time
    tm = dict(frames_equal=bool(len(ours[names[0]]) == T))
    for s, n in enumerate(names):
        dg = np.linalg.norm(pc_g[:, s] - pc_g[0, s], axis=1)
        if dg.max() < 0.05:
            tm[n] = dict(note='moves < 5 cm, no lag estimate', peak_disp_cm=round(float(dg.max() * 100), 1)); continue
        L, cmax, c0 = xcorr_lag(speed(pc_o[:, s]), speed(pc_g[:, s]))
        # RMSE vs shift (per object, rigid fit at each shift)
        shifts = np.arange(-6, 6.01, 0.25); rms = []
        for tau in shifts:
            A = shift_path(np.concatenate([pc_o[:, s], np.tile([0, 0, 0, 1.0], (T, 1))], 1), tau)[:, :3]
            rms.append(umeyama(pc_g[:, s], A, False)[3])
        k = int(np.argmin(rms))
        tm[n] = dict(xcorr_lag_frames=round(L, 2), xcorr_peak=round(cmax, 3), xcorr_at_0=round(c0, 3),
                     rmse_min_shift_frames=float(shifts[k]), rmse_at_min_mm=round(rms[k] * 1000, 1),
                     rmse_at_0_mm=round(rms[int(np.argmin(np.abs(shifts)))] * 1000, 1))
    out['time'] = tm

    # ---- 3 up axis (our table normal = +z of the table frame)
    axes = [h['axis'] for h in H]
    W = kit_W(ach, ref, axes)
    up = dict(kit_alignment_deg=round(angle_deg(W @ Z, Z), 2))
    _, Rp, _, _ = umeyama(pc_o.reshape(-1, 3), pc_g.reshape(-1, 3), False)
    ev = np.linalg.eigvalsh(np.cov(pc_g.reshape(-1, 3).T))
    up['rigid_position_fit_deg'] = round(angle_deg(Rp @ Z, Z), 2)
    up['position_fit_conditioning'] = dict(mocap_extent_cm=[round(float(np.sqrt(e) * 100), 1) for e in ev])
    up['rest_orientation_deg'] = {}
    ups = []
    for s, n in enumerate(names):
        fr = np.r_[rest[s]['pre'], rest[s]['post']].astype(int)
        if not len(fr):
            continue
        wz = np.einsum('tij,tkj,k->ti', Rg[fr, s], Ro[fr, s], Z)               # R_gt R_ours^T z
        mz = wz.mean(0); mz /= np.linalg.norm(mz); ups.append(mz)
        up['rest_orientation_deg'][n] = dict(angle=round(angle_deg(mz, Z), 2), dir_xy=np.round(mz[:2], 4).tolist(), frames=int(len(fr)))
    if len(ups) == 2:
        up['rest_orientation_between_objects_deg'] = round(angle_deg(ups[0], ups[1]), 2)
    out['up_axis'] = up

    # ---- 4 resting height (table frame; ours: lowest vertex of OUR mesh; mocap: lowest scan vertex)
    low_o = np.stack([(np.einsum('tij,vj->tvi', ours[n][:, :3, :3], REG[s]['low_v'])[..., 2]).min(1) + ours[n][:, 2, 3]
                      for s, n in enumerate(names)], 1)
    low_g = np.stack([(np.einsum('tij,vj->tvi', gt[n][:, :3, :3], H[s]['hull'])[..., 2]).min(1) + gt[n][:, 2, 3]
                      for s, n in enumerate(names)], 1)
    med_pre = [float(np.median(low_g[rest[s]['pre'], s])) if len(rest[s]['pre']) else np.inf for s in range(B)]
    h_tab = float(min(med_pre))
    rh = dict(mocap_table_z_m=round(h_tab, 4), mocap_table_from=names[int(np.argmin(med_pre))], our_table_z_m=table_z)
    for s, n in enumerate(names):
        d = {}
        for seg in ('pre', 'post'):
            fr = rest[s][seg]
            if not len(fr):
                continue
            fo = (low_o[fr, s] - table_z) * 1000; fg = (low_g[fr, s] - h_tab) * 1000
            # centre heights (kit anchor centres; ours in the table frame, mocap in its world)
            co = (pc_o[fr, s, 2] - table_z) * 1000; cg = (pc_g[fr, s, 2] - h_tab) * 1000
            d[seg] = dict(frames=[int(fr[0]), int(fr[-1])], ours_lowest_above_table_mm=round(float(np.median(fo)), 1),
                          mocap_lowest_above_table_mm=round(float(np.median(fg)), 1),
                          float_mm=round(float(np.median(fo - fg)), 1),
                          centre_height_error_mm=round(float(np.median(co - cg)), 1))
        rh[n] = d
    if B == 2:
        rel = {}
        for seg in ('pre', 'post'):
            fr = np.intersect1d(rest[0][seg], rest[1][seg])
            if len(fr):
                rel[seg] = dict(frames=int(len(fr)), dz_ours_mm=round(float(np.median(pc_o[fr, 1, 2] - pc_o[fr, 0, 2]) * 1000), 1),
                                dz_mocap_mm=round(float(np.median(pc_g[fr, 1, 2] - pc_g[fr, 0, 2]) * 1000), 1))
                rel[seg]['error_mm'] = round(rel[seg]['dz_ours_mm'] - rel[seg]['dz_mocap_mm'], 1)
        rh[f'{names[1]}_minus_{names[0]}_centre_height'] = rel
    out['rest_height'] = rh

    # ---- 5 rotation bias at rest (tilt = swing of the up axis, scan body frame) + kit-aligned residual
    kit_al = T3._align_registered_scene(ach, ref, axes)
    Ra = T3._rotation_matrix(kit_al[:, 0, :, 3:])
    rb = {}
    tilt_bias = {}
    for s, n in enumerate(names):
        d = {}
        for seg in ('pre', 'post'):
            fr = rest[s][seg]
            if not len(fr):
                continue
            ug = np.einsum('tji,j->ti', Rg[fr, s], Z); uo = np.einsum('tji,j->ti', Ro[fr, s], Z)
            rv = np.degrees(swing_rotvec(ug, uo))                               # takes mocap up -> our up (body frame)
            E = np.einsum('tji,tjk->tik', Rg[fr, s], Ra[fr, s])                 # kit-aligned residual (body frame)
            if H[s]['order'] == 2:
                flip = Rot.from_rotvec(np.pi * H[s]['axis']).as_matrix()
                E2 = np.einsum('ij,tjk->tik', flip.T, E)                       # alternate reference R_gt flip
                pick = Rot.from_matrix(E2).magnitude() < Rot.from_matrix(E).magnitude()
                E[pick] = E2[pick]
            ev = np.degrees(Rot.from_matrix(E).as_rotvec())
            if H[s]['order'] == 360:                                              # cups: drop spin about the axis
                a = H[s]['axis']; ea = np.einsum('tij,j->ti', E, a)
                ev = np.degrees(swing_rotvec(np.tile(a, (len(fr), 1)), ea))
            d[seg] = dict(frames=int(len(fr)), tilt_deg=round(float(np.median(np.linalg.norm(rv, axis=1))), 2),
                          tilt_mean_rotvec_deg=np.round(rv.mean(0), 2).tolist(), tilt_std_deg=np.round(rv.std(0), 2).tolist(),
                          kit_residual_deg=round(float(np.median(np.linalg.norm(ev, axis=1))), 2),
                          kit_residual_mean_rotvec_deg=np.round(ev.mean(0), 2).tolist())
        rb[n] = d
        segs = [d[k] for k in ('pre', 'post') if k in d]
        if segs:
            w = np.array([g['frames'] for g in segs], float)
            tilt_bias[n] = (np.array([g['tilt_mean_rotvec_deg'] for g in segs]) * w[:, None]).sum(0) / w.sum()
    out['rotation_bias'] = rb

    # ---- kit-aligned vertical error at rest (what the score sees)
    ve = {}
    for s, n in enumerate(names):
        for seg in ('pre', 'post'):
            fr = rest[s][seg]
            if len(fr):
                ve.setdefault(n, {})[seg] = round(float(np.median(kit_al[fr, 0, s, 2] - ref[fr, 0, s, 2]) * 1000), 1)
    out['kit_aligned_vertical_error_mm'] = ve
    out['_internal'] = dict(REG=REG, rest=rest, s=s_j, tilt_bias=tilt_bias, h_tab=h_tab, pc_o=pc_o, pc_g=pc_g,
                            lags={n: tm[n]['xcorr_lag_frames'] for n in names if isinstance(tm.get(n), dict) and 'xcorr_lag_frames' in tm[n]})
    return out


# ------------------------------------------------------------------ oracle corrections of our path
def corrected_paths(names, ours, res, gt, H, table_z):
    """Each correction removes one measured systematic (oracle: derived from mocap) from our path, in OUR convention."""
    I = res['_internal']; REG = I['REG']; T = len(gt[names[0]])
    base = {n: to7(ours[n]) for n in names}
    out = {'base': base}
    # scale: centres scaled by 1/s about the kit anchor object's frame-0 centre (any fixed point: the kit aligns frame 0)
    s = I['s']
    c0 = I['pc_o'][0, 0]
    sc = {}
    for k, n in enumerate(names):
        M = ours[n].copy(); a = REG[k]['anchor']
        cen = centre_path(M, a)
        M[:, :3, 3] = c0 + (cen - c0) / s - M[:, :3, :3] @ a
        sc[n] = to7(M)
    out['scale'] = sc
    # time: episode lag = median of the per-object xcorr lags (frames), applied to all objects
    lags = list(I['lags'].values())
    L = float(np.median(lags)) if lags else 0.0
    out['time'] = {n: shift_path(base[n], L) for n in names}
    out['_lag'] = L
    # rest height: at each rest segment remove the median centre-height error (table referenced)
    hh = {}
    for k, n in enumerate(names):
        M = ours[n].copy()
        for seg in ('pre', 'post'):
            fr = I['rest'][k][seg]
            if len(fr):
                err = np.median((I['pc_o'][fr, k, 2] - table_z) - (I['pc_g'][fr, k, 2] - I['h_tab']))
                M[fr, 2, 3] -= err
        hh[n] = to7(M)
    out['height'] = hh
    # tilt: constant body-frame tilt bias removed at all frames (R_s' = R_s Q, Q takes our up back to mocap's)
    tb = {}
    for k, n in enumerate(names):
        M = ours[n].copy()
        if n in I['tilt_bias']:
            Q = Rot.from_rotvec(np.radians(I['tilt_bias'][n])).as_matrix()      # takes mocap up -> our up
            Bm = REG[k]['R']; a = REG[k]['anchor']
            Rn = M[:, :3, :3] @ Bm.T @ Q @ Bm
            M[:, :3, 3] = M[:, :3, 3] + (M[:, :3, :3] - Rn) @ a
            M[:, :3, :3] = Rn
        tb[n] = to7(M)
    out['tilt'] = tb
    return out


def combine(names, ours, res, gt, H, table_z):
    """All corrections in sequence: tilt -> height -> scale -> time."""
    c = corrected_paths(names, ours, res, gt, H, table_z)
    cur = {n: from7(c['tilt'][n]) for n in names}
    # height on the tilted path: recompute the same rest offsets (heights barely change with tilt)
    I = res['_internal']; REG = I['REG']
    for k, n in enumerate(names):
        for seg in ('pre', 'post'):
            fr = I['rest'][k][seg]
            if len(fr):
                cz = centre_path(cur[n][fr], REG[k]['anchor'])[:, 2]
                err = np.median((cz - table_z) - (I['pc_g'][fr, k, 2] - I['h_tab']))
                cur[n][fr, 2, 3] -= err
    s = I['s']; c0 = centre_path(cur[names[0]][:1], REG[0]['anchor'])[0]
    for k, n in enumerate(names):
        a = REG[k]['anchor']; cen = centre_path(cur[n], a)
        cur[n][:, :3, 3] = c0 + (cen - c0) / s - cur[n][:, :3, :3] @ a
    return {n: shift_path(to7(cur[n]), c['_lag']) for n in names}


def strip(o):
    return {k: v for k, v in o.items() if not k.startswith('_')}


def main():
    p = argparse.ArgumentParser()
    p.add_argument('out'); p.add_argument('--eps', default='0,2,11,12,13,18,21,22,23,24,26,27,31,39,40,41,42,43,44,45')
    p.add_argument('--sources', default='ref,pre,perc'); p.add_argument('--no_auc', action='store_true')
    p.add_argument('--save_npz', action='store_true', help='write base / corrected paths as npz (score_registered.py input)')
    a = p.parse_args()
    C = canon(); res = {}
    for ep in [int(x) for x in a.eps.split(',')]:
        t0 = time.time()
        e = C[ep]; names, gt = load_gt(ep)
        H = [host_geometry(n, s) for s, n in enumerate(names)]
        fin, pre, tf = ref_files(e)
        if tf is None:                                                           # stale refsweep table frame
            tf = f'{STORE}/{STALE.format(ep)}/table_frame.npz'
        TF = np.load(tf); Ttab = TF['T_table_from_world']; table_z = float(TF['table_z'])
        srcs = {}
        if 'ref' in a.sources and fin:
            srcs['ref'] = (load_ref_parquet(fin), REF_LIB[ep], fin)
        if 'pre' in a.sources and pre:
            srcs['pre'] = (load_ref_parquet(pre), REF_LIB[ep], pre)
        if 'perc' in a.sources:
            P = load_npz(f"{STORE}/{e['perception_path']}")
            srcs['perc'] = ({n: Ttab @ P[n] for n in names}, PERC_LIB[ep], f"{STORE}/{e['perception_path']}")
        res[ep] = dict(objects=names, table_frame=tf[len(STORE) + 1:], sources={})
        for k, (ours, lib, path) in srcs.items():
            r = analyse(ep, names, gt, ours, lib, table_z, H, k)
            r['file'] = path[len(STORE) + 1:]
            if not a.no_auc and k == 'pre':
                A, per, _, _ = kit_auc(ep, names, {n: to7(ours[n]) for n in names}, gt, H, r['_internal']['REG'])
                r['auc_oracle_corrections'] = dict(base=dict(AUC=A, per_obj=per))
            if not a.no_auc and k in ('ref', 'perc'):
                cp = corrected_paths(names, ours, r, gt, H, table_z)
                cp['all'] = combine(names, ours, r, gt, H, table_z)
                auc = {}
                for v in ('base', 'scale', 'time', 'height', 'tilt', 'all'):
                    A, per, _, _ = kit_auc(ep, names, cp[v], gt, H, r['_internal']['REG'])
                    auc[v] = dict(AUC=A, per_obj=per)
                    if a.save_npz:
                        os.makedirs(f'{WORK}/npz', exist_ok=True)
                        np.savez(f'{WORK}/npz/ep{ep}_{k}_{v}.npz', **{n: from7(cp[v][n]) for n in names})
                for v in auc:
                    auc[v]['delta'] = round(auc[v]['AUC'] - auc['base']['AUC'], 4)
                auc['time']['lag_applied_frames'] = cp['_lag']
                auc['scale']['s_applied'] = round(r['_internal']['s'], 4)
                r['auc_oracle_corrections'] = auc
            res[ep]['sources'][k] = strip(r)
        print(f'ep{ep} done {time.time() - t0:.0f}s', json.dumps({k: (v['scale']['joint']['s'], v['up_axis']['kit_alignment_deg'],
              v.get('auc_oracle_corrections', {}).get('base', {}).get('AUC')) for k, v in res[ep]['sources'].items()}), flush=True)
        json.dump(res, open(a.out, 'w'), indent=1)


if __name__ == '__main__':
    main()
