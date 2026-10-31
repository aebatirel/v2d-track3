"""Placement and physics checks along our track for every candidate (INTERLOCK.md section 5, PREREG F-I1.6 / F-I1.9;
build step BI1). Everything uses P_sel (the bundle's tracks), our grids, our table plane. Features go under key
`phys` of the candidate's feature line (hook for B10; this module writes nothing itself).

  placement(mesh, b, obj, frames=None)          5.1 per-frame 6-DoF offsets (trimmed point-to-plane Gauss-Newton,
                                                unconstrained directions excluded); constant part, drift, flags, VP
  interpenetration(mesh, b, obj, phases)        5.2 partner evidence volume inside the candidate per frame and phase
  vi_veto(I_by_cand)                            5.2 VI relative to the best candidate (> 1.0 cm3 more at assembled)
  table(mesh, b, obj)                           5.3 share of 20,000 volume samples below the table per frame; V4t
  rest(mesh, b, obj, hands=None)                5.4 lowest point, stable pose, COM in the support at static segments
  hands_inside(mesh, b, obj, hands)             5.5 hand keypoints inside the candidate (report only)
  phases(b, o, p, runs)                         apart / contact / engaged / assembled frame lists for a pair
  features(mesh, b, obj, phases_by_partner, cls, hands=None) -> dict
"""
from __future__ import annotations

import numpy as np
from scipy.spatial.transform import Rotation as Rot

from gmg import guard, geom, interlock as IL

C = dict(
    trim=(0.8, 'generic:numerical trimmed point-to-plane share'),
    gn_steps=(5, 'generic:F-I1.9 at most 5 Gauss-Newton steps'),
    eig_floor=(0.01, 'generic:F-I1.9 directions below 1 % of the largest information eigenvalue excluded'),
    pts_per_frame=(1500, 'generic:numerical points per frame'),
    off_sigma=(3.0, 'generic:F-I1.14 offset flags 3 sigma'),
    off_mm=(0.002, 'generic:F-I1.14 2 mm'),
    off_deg=(2.0, 'generic:F-I1.14 2 deg'),
    drift_block=(10, 'generic:F-I1.14 10-frame drift blocks'),
    drift_mm=(0.005, 'generic:F-I1.14 5 mm block deviation'),
    vp_m=(0.010, 'generic:F-I1.6 VP 10 mm (= K-c)'),
    vp_deg=(15.0, 'generic:F-I1.6 VP 15 deg (= K-c)'),
    vi_cm3=(1.0, 'informed:F-I1.14 VI 1.0 cm3 margin (26 Oct)'),
    table_n=(20000, 'generic:F-I1.6 20,000 volume samples'),
    table_share=(0.01, 'generic:F-I1.6 V4t > 1 %'),
    table_frames=(0.25, 'generic:F-I1.14 V4t persistence 25 %'),
    rest_frames=(15, 'generic:F-I1.14 rest 15 frames'),
    rest_hand_m=(0.030, 'generic:F-I1.14 rest hands 30 mm'),
    rest_deg=(10.0, 'generic:F-I1.9 stable pose within 10 deg'),
    sample_cm3=(0.008, 'generic:one 2 mm partner sub-sample = 0.008 cm3'),
)


def k_(n):
    v, o = C[n]
    if o.startswith('generic'):
        guard.constant(f'pc.{n}', v, o)
    return v


def _frame_points(b, obj, f, n, rng):
    ob = b.obs(obj)
    fr = np.asarray(ob['frame']); own = np.asarray(ob.get('own', np.zeros(len(fr), np.uint8)))
    idx = np.nonzero((fr == f) & (own == 0))[0]
    if len(idx) > n:
        idx = rng.choice(idx, n, replace=False)
    return np.asarray(ob['pts'], np.float64)[idx]


def _align(P, cl, steps, trim, floor):
    """Trimmed point-to-plane Gauss-Newton of points P onto the mesh (object frame). Returns the 6-vector
    x = (rotation vector, translation) of the rigid map that moves P onto the surface, and the number of constrained
    directions (information eigenvalues >= floor x the largest)."""
    import trimesh
    x = np.zeros(6)
    used = 6
    for _ in range(steps):
        R = Rot.from_rotvec(x[:3]).as_matrix()
        Q = P @ R.T + x[3:]
        d, face, nrm = cl.query(Q)
        k = d <= np.quantile(d, trim)
        Qk, nk = Q[k], nrm[k]
        Ck = trimesh.triangles.closest_point(cl.T[face[k]], Qk)
        res = np.einsum('ij,ij->i', Qk - Ck, nk)              # signed point-to-plane residual
        J = np.hstack([np.cross(Qk, nk), nk])                  # d res / d (omega, t)
        H = J.T @ J
        w, V = np.linalg.eigh(H)
        keep = w >= floor * w.max()
        used = int(keep.sum())
        g = J.T @ res
        dx = -(V[:, keep] @ ((V[:, keep].T @ g) / w[keep]))
        x = x + dx
        if np.linalg.norm(dx) < 1e-6:
            break
    return x, used


def placement(mesh, b, obj, frames=None, seed=0):
    """5.1. Per good frame: offset delta_f; constant part (median over frames), drift (MAD), max 10-frame block mean
    deviation, flags placement_offset / placement_drift, and VP's inputs (held-out = odd frames of the sequence)."""
    rng = np.random.default_rng(seed)
    frames = frames if frames is not None else b.good_frames(obj)
    cl = geom.Closest(mesh)
    sig = b.sigma(obj)
    rows = []
    for f in frames:
        P = _frame_points(b, obj, f, k_('pts_per_frame'), rng)
        if len(P) < 30:
            continue
        x, used = _align(P, cl, k_('gn_steps'), k_('trim'), k_('eig_floor'))
        rows.append((f, x, used))
    if not rows:
        return dict(frames=0)
    X = np.array([r[1] for r in rows])
    fr = np.array([r[0] for r in rows])
    med = np.median(X, axis=0)
    mad = np.median(np.abs(X - med), axis=0)
    t_med = float(np.linalg.norm(med[3:])); r_med = float(np.degrees(np.linalg.norm(med[:3])))
    t_mad = float(np.linalg.norm(mad[3:]))
    nb = k_('drift_block')
    blk = [np.linalg.norm(X[i:i + nb, 3:].mean(0) - med[3:]) for i in range(0, len(X), nb) if len(X[i:i + nb]) >= 3]
    blk_max = float(max(blk)) if blk else 0.0
    flags = []
    if t_med > max(k_('off_sigma') * sig, k_('off_mm')) or r_med > k_('off_deg'):
        flags.append('placement_offset')
    if t_mad > k_('off_sigma') * sig or blk_max > max(k_('off_sigma') * sig, k_('drift_mm')):
        flags.append('placement_drift')
    odd = X[1::2]
    ho = np.median(odd, axis=0) if len(odd) else med
    return dict(frames=int(len(rows)), const_t_mm=round(t_med * 1e3, 2), const_r_deg=round(r_med, 2),
                const_vec=np.round(med, 5).tolist(), drift_mad_mm=round(t_mad * 1e3, 2), block_max_mm=round(blk_max * 1e3, 2),
                constrained_dirs_median=float(np.median([r[2] for r in rows])),
                heldout_t_mm=round(float(np.linalg.norm(ho[3:])) * 1e3, 2),
                heldout_r_deg=round(float(np.degrees(np.linalg.norm(ho[:3]))), 2), flags=flags,
                per_frame_t_mm=dict(zip([int(f) for f in fr], np.round(np.linalg.norm(X[:, 3:], axis=1) * 1e3, 2).tolist())))


def vp_veto(pl, cls):
    if cls not in ('GEN', 'FUSE', 'FUSE-I') or not pl.get('frames'):
        return False
    return pl['heldout_t_mm'] > k_('vp_m') * 1e3 or pl['heldout_r_deg'] > k_('vp_deg')


def phases(b, o, p, runs):
    allf = set(b.frames())
    cf = set(b.contact(o, p)['contact'])
    eng = set(f for r in runs for f in r.frames)
    asm = set(f for r in runs for f in r.assembled)
    return dict(apart=sorted(allf - cf), contact=sorted(cf - eng), engaged=sorted(eng), assembled=sorted(asm))


_OCC = {}


def _occ_grid(mesh, pitch=0.001):
    """Candidate occupancy on a 1 mm grid over its bounds (cached per mesh): per-frame inside tests become look-ups."""
    key = id(mesh)
    if key not in _OCC:
        g = IL.Grid(mesh.bounds[0] - 2 * pitch, pitch, np.ceil((mesh.extents + 4 * pitch) / pitch).astype(int))
        _OCC[key] = (g, IL.fast_inside(mesh, g.centres()))
    return _OCC[key]


def interpenetration(mesh, b, obj, partner, ph, poses=None):
    """5.2: per phase, I_f = partner evidence sub-samples (2 mm, 0.008 cm3 each) inside the candidate (cm3); inside =
    the sample's cell of the candidate's 1 mm occupancy grid."""
    poses = b.poses if poses is None else poses
    Xp = IL.partner_points(b, partner)
    g, occ = _occ_grid(mesh)
    out, per = {}, {}
    for name, frs in ph.items():
        vals = []
        for f in frs:
            T = IL.rel_pose(poses, obj, partner, f)
            X = Xp @ T[:3, :3].T + T[:3, 3]
            l, ok = g.lin(X)
            n = int(occ[l[ok]].sum())
            vals.append(n * k_('sample_cm3'))
            per[int(f)] = round(n * k_('sample_cm3'), 3)
        if vals:
            out[name] = dict(frames=len(vals), median=round(float(np.median(vals)), 3),
                             p90=round(float(np.percentile(vals, 90)), 3), max=round(float(np.max(vals)), 3))
        else:
            out[name] = dict(frames=0)
    return out, per


def vi_veto(I):
    """I: {cid: median assembled overlap cm3}. Returns {cid: veto bool} relative to the best candidate."""
    if not I:
        return {}
    best = min(I.values())
    return {c: bool(v - best > k_('vi_cm3')) for c, v in I.items()}


def table(mesh, b, obj, poses=None):
    """5.3: per good frame, the share of volume samples more than max(3 sigma, 2 mm) below the table plane."""
    if not b.meta.get('table'):
        return dict(applies=False, reason='no table plane in the bundle')
    X, _ = geom.volume_samples(mesh, k_('table_n'), seed=0)
    thr = max(3 * b.sigma(obj), 0.002)
    shares = {}
    for f in b.good_frames(obj):
        pl = b.table_in_obj(obj, f)
        if pl is None:
            continue
        h = X @ pl[0] + pl[1]
        shares[int(f)] = float((h < -thr).mean())
    if not shares:
        return dict(applies=False)
    v = np.array(list(shares.values()))
    frac = float((v > k_('table_share')).mean())
    return dict(applies=True, frames=len(v), frames_over_share=round(frac, 3), median_share=round(float(np.median(v)), 4),
                max_share=round(float(v.max()), 4), veto=bool(frac >= k_('table_frames')))


def rest(mesh, b, obj):
    """5.4: static segments on the table; lowest point vs the table, stable pose vs the observed up, COM support."""
    import trimesh
    if not b.meta.get('table'):
        return dict(applies=False, reason='no table plane')
    W = b.poses['world_T_cam'].astype(np.float64); T = b.poses[f'cam_T_{obj}'].astype(np.float64)
    xw = np.einsum('fij,fj->fi', W[:, :3, :3], T[:, :3, 3]) + W[:, :3, 3]
    sp = np.r_[np.linalg.norm(np.diff(xw, axis=0), axis=1), np.inf]
    good = set(b.good_frames(obj))
    segs, cur = [], []
    for f in range(len(sp)):
        if sp[f] < 0.002 and f in good:
            cur.append(f)
        else:
            if len(cur) >= k_('rest_frames'):
                segs.append(cur)
            cur = []
    if len(cur) >= k_('rest_frames'):
        segs.append(cur)
    if not segs:
        return dict(applies=False, reason='no static segment')
    try:
        tfs, probs = trimesh.poses.compute_stable_poses(mesh, n_samples=1, threshold=0.0)
        ups = [np.linalg.inv(t)[:3, 2] for t in tfs]
    except Exception:
        ups = []
    thr = max(3 * b.sigma(obj), 0.002)
    out = []
    V = np.asarray(mesh.vertices)
    for s in segs:
        f = s[len(s) // 2]
        pl = b.table_in_obj(obj, f)
        h = V @ pl[0] + pl[1]
        low = float(h.min())
        ang = min([float(np.degrees(np.arccos(np.clip(u @ pl[0], -1, 1)))) for u in ups]) if ups else None
        out.append(dict(frames=[s[0], s[-1]], lowest_mm=round(low * 1e3, 2), on_table=bool(abs(low) <= thr + 0.008),
                        stable_pose_deg=None if ang is None else round(ang, 1)))
    mism = any((r['on_table'] and r['stable_pose_deg'] is not None and r['stable_pose_deg'] > k_('rest_deg'))
               for r in out)
    return dict(applies=True, segments=out, flags=['rest_mismatch'] if mism else [])


def hands_inside(mesh, b, obj, hands):
    if hands is None:
        return dict(applies=False)
    W = b.poses['world_T_cam'].astype(np.float64); T = b.poses[f'cam_T_{obj}'].astype(np.float64)
    n_in, n_all = 0, 0
    for f in b.good_frames(obj):
        M = np.linalg.inv(W[f] @ T[f])
        for side in ('left', 'right'):
            if f < len(hands[f'valid_{side}']) and hands[f'valid_{side}'][f]:
                J = np.asarray(hands[f'joints_{side}'][f], np.float64)
                J = J[np.isfinite(J).all(1)]
                if len(J):
                    X = J @ M[:3, :3].T + M[:3, 3]
                    n_in += int(IL.fast_inside(mesh, X).sum()); n_all += len(X)
    return dict(applies=True, joints=n_all, inside=n_in)


def features(mesh, b, obj, phases_by_partner, cls, hands=None):
    pl = placement(mesh, b, obj)
    inter = {}
    for p, ph in phases_by_partner.items():
        inter[p], _ = interpenetration(mesh, b, obj, p, ph)
    tb = table(mesh, b, obj)
    rs = rest(mesh, b, obj)
    hd = hands_inside(mesh, b, obj, hands)
    flags = list(pl.get('flags', [])) + list(rs.get('flags', []))
    return dict(placement=pl, interpenetration=inter, table=tb, rest=rs, hands=hd, vp=vp_veto(pl, cls),
                v4t=bool(tb.get('veto')), flags=flags)
