"""Physical acceptance of a carved simulator copy (INTERLOCK.md 6.2-6.3, PREREG F-I1.8; build step BI1).

Every judgement that runs the simulator is a mean over 16 jittered copies (0.5 mm / 0.005 rad, common random numbers:
the same 16 draws for the default and the carved pieces), never a single draw.

  overlap(hulls_host, hulls_guest, T_hg)          Monte Carlo collider overlap (cm3) of the guest's union inside the
                                                  host's pieces (guest pieces mapped by T_hg = T_{host<-guest})
  free_travel(host, guest, T_hg, dirs)            P2: travel of the guest along each direction (0.5 mm steps) until the
                                                  overlap grows by more than 0.05 cm3 over its value at the pose
  over_removal(default, carved, carve_cm3)        P4
  shape_budget(counts)                            P5 (<= 165 per episode)
  overlap_series(...)                             P6 / P7 per frame
  settle(host, guest, T_wh, T_wg, table, ...)     P1 pre-check in plain MuJoCo (the FlashCHORD settle is not in this
                                                  container; INTERLOCK 6.2: the pre-check does not decide)
  replay_proxy(host, guest, rel, f0, f1, asm)     P3: interaction_carve.py's MuJoCo proxy (host fixed, guest welded to a
                                                  kinematic target that follows the replayed relative path)
  accept(...)                                     P1-P7 table for one carved pair
"""
from __future__ import annotations

import numpy as np
from scipy.spatial import ConvexHull
from scipy.spatial.transform import Rotation as Rot

from gmg import guard
from gmg.simpieces import inside_any, inside_eq

C = dict(
    copies=(16, 'generic:F-I1.14 16 jittered copies'),
    jit_m=(0.0005, 'generic:F-I1.8 jitter 0.5 mm (jitter_check.py settings)'),
    jit_rad=(0.005, 'generic:F-I1.8 jitter 0.005 rad'),
    mc_points=(200000, 'generic:F-I1.8 200,000 points in the guest box'),
    travel_step_m=(0.0005, 'generic:F-I1.8 0.5 mm steps'),
    travel_thr_cm3=(0.05, 'generic:F-I1.8 0.05 cm3'),
    travel_cap_m=(0.060, 'generic:numerical cap of the travel search'),
    travel_max_m=(0.004, 'informed:F-I1.14 free travel 4 mm (after carve-20261030)'),
    travel_default_plus_m=(0.001, 'informed:F-I1.14 default + 1 mm'),
    settle_s=(2.0, 'informed:F-I1.14 settle 2 s (carve-20261030 criteria)'),
    drift_max_m=(0.010, 'informed:F-I1.14 1 cm'),
    tilt_max_deg=(5.0, 'informed:F-I1.14 5 deg'),
    sink_max_m=(0.004, 'informed:F-I1.14 relative sink 4 mm'),
    lag_asm_m=(0.005, 'informed:F-I1.14 proxy lag 0.5 cm (26 Oct)'),
    lag_asm_deg=(5.0, 'informed:F-I1.14 proxy lag 5 deg (26 Oct)'),
    lag_after_m=(0.010, 'informed:F-I1.14 lag never > 1.0 cm after the first assembled frame'),
    ovl_max_cm3=(1.0, 'informed:F-I1.14 collider overlap 1.0 cm3 (26 Oct)'),
    not_limiting_m=(0.01, 'informed:F-I1.14 slot not limiting: default lag < 1 cm and < 10 deg'),
    not_limiting_deg=(10.0, 'informed:F-I1.14 slot not limiting'),
    removal_x=(1.5, 'informed:F-I1.14 P4 1.5 x'),
    keep_share=(0.90, 'informed:F-I1.14 P4 90 %'),
    shapes_max=(165, 'informed:F-I1.14 165-shape cap (note 19)'),
    p6_tol_cm3=(0.1, 'informed:F-I1.14 P6 0.1 cm3 (carve-20261030 criterion 3)'),
    p7_share=(0.5, 'generic:F-I1.8 P7 half the default'),
    pre=(40, 'informed:F-I1.14 40 frames before the first engaged frame (26 Oct proxy)'),
    fps=(20.0, 'kit:reference frame rate 20 Hz'),
    sub=(25, 'generic:interaction_carve.py 25 substeps (2 ms)'),
)


def k_(name):
    v, o = C[name]
    if o.startswith(('generic', 'kit')):
        guard.constant(f'ph.{name}', v, o)
    return v


def _tf(T, X):
    return X @ T[:3, :3].T + T[:3, 3]


def guest_samples(hulls, n=None, seed=0):
    """Uniform grid points in the guest's bounding box (n points) that lie inside its pieces; cell volume (m3)."""
    n = n or k_('mc_points')
    P = np.vstack(hulls); lo, hi = P.min(0), P.max(0)
    vol = float(np.prod(hi - lo))
    pitch = (vol / n) ** (1 / 3)
    ax = [np.arange(lo[k] + pitch / 2, hi[k], pitch) for k in range(3)]
    G = np.stack(np.meshgrid(*ax, indexing='ij'), -1).reshape(-1, 3)
    return G[inside_any(hulls, G)], pitch ** 3


def overlap(host_eqs, Xg, cell):
    hit = np.zeros(len(Xg), bool)
    for eq in host_eqs:
        hit |= inside_eq(eq, Xg)
    return float(hit.sum()) * cell * 1e6


def eqs(hulls):
    return [ConvexHull(V).equations for V in hulls]


def free_travel(host, guest, T_hg, dirs, Xg=None, cell=None):
    """P2: per direction (host frame unit vectors), the largest translation (0.5 mm steps) before the overlap grows by
    more than 0.05 cm3 over its value at the pose (the guest may already touch the host there). Returns {name: m}."""
    if Xg is None:
        Xg, cell = guest_samples(guest)
    He = eqs(host)
    X0 = _tf(T_hg, Xg)
    # only guest points near the host's box can collide
    Hp = np.vstack(host); lo, hi = Hp.min(0) - k_('travel_cap_m'), Hp.max(0) + k_('travel_cap_m')
    X0 = X0[np.all((X0 > lo) & (X0 < hi), axis=1)]
    base = overlap(He, X0, cell)
    out = {}
    step, cap, thr = k_('travel_step_m'), k_('travel_cap_m'), k_('travel_thr_cm3')
    for name, u in dirs.items():
        u = np.asarray(u, float); u = u / np.linalg.norm(u)
        s = 0.0
        # coarse 2 mm search, then 0.5 mm refinement
        coarse = None
        for s in np.arange(0.002, cap + 1e-9, 0.002):
            if overlap(He, X0 + u * s, cell) - base > thr:
                coarse = s; break
        if coarse is None:
            out[name] = float(cap); continue
        fine = coarse
        for s2 in np.arange(max(coarse - 0.002, 0) + step, coarse + 1e-9, step):
            if overlap(He, X0 + u * s2, cell) - base > thr:
                fine = s2; break
        out[name] = float(fine - step)
    return out, base


def collider_volume(hulls, n=None):
    X, cell = guest_samples(hulls, n)
    return len(X) * cell * 1e6


def over_removal(default, carved, carve_cm3):
    """P4: removed collider volume = default minus carved (Monte Carlo, on the default's box) <= 1.5 x the carved
    region at w_sim, and >= 90 % of the default collider volume kept."""
    X, cell = guest_samples(default)
    inC = inside_any(carved, X)
    removed = float((~inC).sum()) * cell * 1e6
    vd = len(X) * cell * 1e6
    vc = collider_volume(carved)
    ok = removed <= k_('removal_x') * max(carve_cm3, 1e-9) and vc >= k_('keep_share') * vd
    return dict(removed_cm3=round(removed, 2), carve_cm3=round(carve_cm3, 2), default_cm3=round(vd, 2),
                carved_cm3=round(vc, 2), kept_share=round(vc / max(vd, 1e-9), 3), pass_=bool(ok))


def shape_budget(counts):
    n = int(sum(counts.values()))
    return dict(shapes=n, cap=k_('shapes_max'), pass_=n <= k_('shapes_max'))


def overlap_series(host, guest, rels, frames, Xg=None, cell=None):
    """Collider overlap (cm3) of the guest's pieces inside the host's at each frame; rels[f] = T_{host<-guest}[f]."""
    if Xg is None:
        Xg, cell = guest_samples(guest, 60000)
    He = eqs(host)
    return {int(f): overlap(He, _tf(rels[f], Xg), cell) for f in frames}


# --------------------------------------------------------------------------- MuJoCo
def _mesh_assets(hulls, tag):
    a = ''.join(f'<mesh name="{tag}{i}" vertex="{" ".join(map(str, np.round(V.ravel(), 6)))}"/>'
                for i, V in enumerate(hulls))
    return a


def _geoms(hulls, tag, ct=1, ca=1, density=0):
    return ''.join(f'<geom type="mesh" mesh="{tag}{i}" contype="{ct}" conaffinity="{ca}" density="{density}" '
                   f'condim="3" friction="0.5"/>' for i in range(len(hulls)))


def _inertial(props):
    c = np.asarray(props['com']); I = np.asarray(props['inertia'])
    w = np.linalg.eigvalsh(I)
    w = np.maximum(w, 1e-7)
    return (f'<inertial pos="{c[0]:.6f} {c[1]:.6f} {c[2]:.6f}" mass="{props["mass"]}" '
            f'fullinertia="{I[0,0]:.9g} {I[1,1]:.9g} {I[2,2]:.9g} {I[0,1]:.9g} {I[0,2]:.9g} {I[1,2]:.9g}"/>')


def _quat(R):
    return Rot.from_matrix(R).as_quat()[[3, 0, 1, 2]]


def replay_xml(host, guest, collide=True, guest_props=None):
    gp = guest_props or dict(com=[0, 0, 0], inertia=np.diag([0.002, 0.002, 0.0005]).tolist(), mass=0.3)
    ct = 1 if collide else 2
    return f'''<mujoco><option timestep="{1 / (k_('fps') * k_('sub'))}" gravity="0 0 0"/>
<asset>{_mesh_assets(host, 'a')}{_mesh_assets(guest, 'b')}</asset><worldbody>
<body name="A">{_geoms(host, 'a')}</body>
<body name="tgt" mocap="true"/>
<body name="B"><freejoint/>{_inertial(gp)}{_geoms(guest, 'b', ct, ct)}</body>
</worldbody><equality><weld body1="tgt" body2="B" solref="0.02 1"/></equality></mujoco>'''


def _drive(model_xml, rels, frames, jit):
    import mujoco
    m = mujoco.MjModel.from_xml_string(model_xml); d = mujoco.MjData(m)
    bid = mujoco.mj_name2id(m, mujoco.mjtObj.mjOBJ_BODY, 'B')
    J = np.eye(4)
    J[:3, :3] = Rot.from_rotvec(jit[3:]).as_matrix(); J[:3, 3] = jit[:3]
    f0 = frames[0]
    T0 = rels[f0] @ J
    d.qpos[:3] = T0[:3, 3]; d.qpos[3:7] = _quat(T0[:3, :3])
    d.mocap_pos[0] = T0[:3, 3]; d.mocap_quat[0] = _quat(T0[:3, :3])
    mujoco.mj_forward(m, d)
    lt, lr = [], []
    for f in frames:
        T = rels[f] @ J
        d.mocap_pos[0] = T[:3, 3]; d.mocap_quat[0] = _quat(T[:3, :3])
        for _ in range(k_('sub')):
            mujoco.mj_step(m, d)
        if not np.all(np.isfinite(d.qpos)):
            return None, None
        lt.append(np.linalg.norm(d.xpos[bid] - T[:3, 3]))
        lr.append(np.degrees(Rot.from_matrix(T[:3, :3].T @ d.xmat[bid].reshape(3, 3)).magnitude()))
    return np.array(lt), np.array(lr)


def jitters(n=None, seed=0):
    n = n or k_('copies')
    rng = np.random.default_rng(seed)
    return np.hstack([rng.normal(0, k_('jit_m'), (n, 3)), rng.normal(0, k_('jit_rad'), (n, 3))])


def replay_proxy(host, guest, rels, frames, asm_frames, variants, copies=None, guest_props=None, log=None):
    """P3. variants: {name: (host_hulls, guest_hulls, collide)}. Frames: every frame from 40 before the first engaged
    frame to the end of the run. Per variant: median over copies of the median lag at the assembled frames, the max
    lag after the first assembled frame, NaN count."""
    J = jitters(copies)
    loc = np.isin(frames, asm_frames)
    first_asm = int(np.argmax(loc)) if loc.any() else len(frames)
    out = {}
    for name, (h, g, col) in variants.items():
        xml = replay_xml(h, g, col, guest_props)
        L, A, nan = [], [], 0
        for j in J:
            lt, lr = _drive(xml, rels, frames, j)
            if lt is None:
                nan += 1; continue
            L.append(lt); A.append(lr)
        if not L:
            out[name] = dict(nan=nan); continue
        L, A = np.array(L), np.array(A)
        med_t = np.median(L[:, loc], axis=1) if loc.any() else np.median(L, axis=1)
        med_r = np.median(A[:, loc], axis=1) if loc.any() else np.median(A, axis=1)
        after = L[:, first_asm:].max(axis=1) if first_asm < L.shape[1] else L.max(axis=1)
        out[name] = dict(lag_cm_asm=round(float(np.mean(med_t)) * 100, 3), lag_cm_asm_sd=round(float(np.std(med_t)) * 100, 3),
                         lag_deg_asm=round(float(np.mean(med_r)), 2), lag_cm_after_max=round(float(np.mean(after)) * 100, 3),
                         copies=int(len(L)), nan=nan)
        if log:
            log(f'proxy {name}: {out[name]}')
    return out


def p3_pass(res, overlap_cm3=None):
    """P3 judgement (F-I1.8 / INTERLOCK 6.3): carved median lag <= 0.5 cm and <= 5 deg at the assembled frames, lag never
    > 1.0 cm after the first assembled frame, no NaN copy, and collider overlap < 1.0 cm3 at the assembled frames.
    OVERLAP_CM3 = the median carved collider overlap at the assembled frames (the P6 series); this F-I1.8 clause was
    missing from the BI1 code and is restored by PREREG F-I4.7 (None: not judged, as before)."""
    c = res.get('carved', {})
    d = res.get('default', {})
    if 'lag_cm_asm' not in c:
        return dict(pass_=False, reason='carved proxy produced no finite copy')
    ok = (c['lag_cm_asm'] <= k_('lag_asm_m') * 100 and c['lag_deg_asm'] <= k_('lag_asm_deg') and
          c['lag_cm_after_max'] <= k_('lag_after_m') * 100 and c['nan'] == 0)
    ovl_ok = None if overlap_cm3 is None else bool(overlap_cm3 < k_('ovl_max_cm3'))
    if ovl_ok is False:
        ok = False
    not_lim = 'lag_cm_asm' in d and d['lag_cm_asm'] < k_('not_limiting_m') * 100 and d['lag_deg_asm'] < k_('not_limiting_deg')
    return dict(pass_=bool(ok), slot_not_limiting=bool(not_lim),
                overlap_asm_cm3=None if overlap_cm3 is None else round(float(overlap_cm3), 3), overlap_ok=ovl_ok)


def settle_xml(host, guest, T_wh, T_wg, n_table, d_table, hp, gp):
    """Two free bodies on a table plane (world frame), gravity along -n_table."""
    g = -9.81 * np.asarray(n_table, float)
    # plane: MuJoCo plane geom through the point -d n (n.x + d = 0), oriented so its z is n
    n = np.asarray(n_table, float); p0 = -d_table * n
    z = n; x = np.cross([0, 1.0, 0], z) if abs(z[1]) < 0.9 else np.cross([1.0, 0, 0], z)
    x /= np.linalg.norm(x); y = np.cross(z, x)
    qp = _quat(np.stack([x, y, z], 1))

    def body(name, hulls, T, props, tag):
        q = _quat(T[:3, :3]); t = T[:3, 3]
        return (f'<body name="{name}" pos="{t[0]:.6f} {t[1]:.6f} {t[2]:.6f}" quat="{q[0]:.6f} {q[1]:.6f} {q[2]:.6f} '
                f'{q[3]:.6f}"><freejoint/>{_inertial(props)}{_geoms(hulls, tag)}</body>')
    return f'''<mujoco><option timestep="0.002" gravity="{g[0]:.5f} {g[1]:.5f} {g[2]:.5f}"/>
<asset>{_mesh_assets(host, 'a')}{_mesh_assets(guest, 'b')}</asset><worldbody>
<geom type="plane" size="2 2 0.1" pos="{p0[0]:.6f} {p0[1]:.6f} {p0[2]:.6f}" quat="{qp[0]:.6f} {qp[1]:.6f} {qp[2]:.6f} {qp[3]:.6f}" friction="0.5"/>
{body('H', host, T_wh, hp, 'a')}{body('G', guest, T_wg, gp, 'b')}
</worldbody></mujoco>'''


def settle(host, guest, T_wh, T_wg, table, hp, gp, copies=None):
    """P1 pre-check (plain MuJoCo, not the FlashCHORD scene): 2 s hands-free settle under gravity; means over jittered
    copies of guest and host drift and tilt, and the guest's sink relative to the host along gravity."""
    import mujoco
    n_t, d_t = table
    J = jitters(copies, seed=1)
    rows, nan = [], 0
    for j in J:
        Jm = np.eye(4); Jm[:3, :3] = Rot.from_rotvec(j[3:]).as_matrix(); Jm[:3, 3] = j[:3]
        Tg = T_wg @ Jm
        m = mujoco.MjModel.from_xml_string(settle_xml(host, guest, T_wh, Tg, n_t, d_t, hp, gp))
        d = mujoco.MjData(m)
        mujoco.mj_forward(m, d)
        hid = mujoco.mj_name2id(m, mujoco.mjtObj.mjOBJ_BODY, 'H'); gid = mujoco.mj_name2id(m, mujoco.mjtObj.mjOBJ_BODY, 'G')
        x0h, x0g = d.xpos[hid].copy(), d.xpos[gid].copy()
        R0h, R0g = d.xmat[hid].reshape(3, 3).copy(), d.xmat[gid].reshape(3, 3).copy()
        for _ in range(int(k_('settle_s') / 0.002)):
            mujoco.mj_step(m, d)
        if not np.all(np.isfinite(d.qpos)):
            nan += 1; continue
        dh = d.xpos[hid] - x0h; dg = d.xpos[gid] - x0g
        tilt = lambda R0, R1: float(np.degrees(Rot.from_matrix(R0.T @ R1).magnitude()))  # noqa: E731
        rows.append(dict(host_drift=float(np.linalg.norm(dh)), guest_drift=float(np.linalg.norm(dg)),
                         host_tilt=tilt(R0h, d.xmat[hid].reshape(3, 3)), guest_tilt=tilt(R0g, d.xmat[gid].reshape(3, 3)),
                         rel_sink=float(-(dg - dh) @ np.asarray(n_t)), guest_below_host=bool(d.xpos[gid] @ n_t < x0h @ n_t - 0.05)))
    if not rows:
        return dict(nan=nan, pass_=False)
    M = {k: float(np.mean([r[k] for r in rows])) for k in rows[0] if k != 'guest_below_host'}
    fall = sum(r['guest_below_host'] for r in rows)
    ok = (M['host_drift'] <= k_('drift_max_m') and M['guest_drift'] <= k_('drift_max_m') and
          M['host_tilt'] <= k_('tilt_max_deg') and M['guest_tilt'] <= k_('tilt_max_deg') and
          M['rel_sink'] <= k_('sink_max_m') and nan == 0 and fall == 0)
    return dict(**{k: round(v * (100 if 'drift' in k or 'sink' in k else 1), 3) for k, v in M.items()},
                units='drift/sink cm, tilt deg', copies=len(rows), nan=nan, fall_through=int(fall), pass_=bool(ok),
                decides=False, note='plain-MuJoCo pre-check; INTERLOCK 6.2: P1 is decided in the FlashCHORD scene')


def pair_physics(b, o, p, hulls_o, hulls_p, run, carve_cm3, default_o, default_p, copies, label, rels=None,
                 do_proxy=True, log=None):
    """The F-I1.8 table for one carved pair (o host, p guest): P2 free travel, P4 over-removal, P6 / P7 overlap, the
    plain-MuJoCo P1 pre-check (does not decide; FlashCHORD's settle is the Embodiment's jitter_check, A3) and the P3
    replay proxy for INSERTION runs. RELS = {frame: T_{o<-p}} of the pose source the simulator replays (P_sim: an
    Embodiment export's rel_T, F-I3.1); None = our tracks (P_sel). Shared by the dev driver and
    interlock.default_physics (moved here from tools/interlock_dev.py)."""
    import time
    from gmg import interlock as IL, simpieces as SP
    log = log or (lambda *a: None)
    out = dict(label=label, pose_source='rels (P_sim)' if rels is not None else 'our tracks (P_sel)')
    T = int(b.meta['T'])
    if rels is None:
        rels = {f: IL.rel_pose(b.poses, o, p, f) for f in range(T)}
    asm = [f for f in (run.assembled or run.build[-5:]) if f in rels] or [f for f in run.frames if f in rels][-5:]
    f_asm = asm[len(asm) // 2]
    pl = b.table_in_obj(o, f_asm) if b.meta.get('table') else None
    dirs = {}
    if pl is not None:
        dirs['gravity'] = -np.asarray(pl[0])
    A = IL.axes_of(np.vstack(hulls_p) @ rels[f_asm][:3, :3].T + rels[f_asm][:3, 3], run.d)[1]
    dirs.update({'+d': A[0], '+n': A[1], '-n': -A[1]})
    Xg, cell = guest_samples(hulls_p)
    tr_c, base_c = free_travel(hulls_o, hulls_p, rels[f_asm], dirs, Xg, cell)
    Xd, celld = guest_samples(default_p)
    tr_d, base_d = free_travel(default_o, default_p, rels[f_asm], dirs, Xd, celld)
    p2 = all(tr_c[k] <= max(k_('travel_max_m'), tr_d[k] + k_('travel_default_plus_m')) for k in tr_c)
    out['P2'] = dict(frame=int(f_asm), carved_mm={k: round(v * 1e3, 1) for k, v in tr_c.items()},
                     default_mm={k: round(v * 1e3, 1) for k, v in tr_d.items()},
                     overlap_at_pose_cm3=[round(base_d, 3), round(base_c, 3)], pass_=bool(p2))
    out['P4'] = {o: over_removal(default_o, hulls_o, carve_cm3.get(o, 0.0)),
                 p: over_removal(default_p, hulls_p, carve_cm3.get(p, 0.0))}
    fr6 = sorted(set([f for f in range(0, T, 4) if f in rels] + [f for f in run.assembled if f in rels]))
    ov_d = overlap_series(default_o, default_p, rels, fr6, Xd, celld)
    ov_c = overlap_series(hulls_o, hulls_p, rels, fr6, Xg, cell)
    worse = [f for f in fr6 if ov_c[f] > ov_d[f] + k_('p6_tol_cm3')]
    asm_in = [f for f in run.assembled if f in ov_d]
    out['P6'] = dict(frames=len(fr6), worse_frames=worse[:20], n_worse=len(worse), pass_=not worse,
                     default_asm_median=round(float(np.median([ov_d[f] for f in asm_in])) if asm_in else 0, 3),
                     carved_asm_median=round(float(np.median([ov_c[f] for f in asm_in])) if asm_in else 0, 3))
    chk = [f for f in run.check if f in rels]
    if chk:
        od = overlap_series(default_o, default_p, rels, chk, Xd, celld)
        oc = overlap_series(hulls_o, hulls_p, rels, chk, Xg, cell)
        sd, sc = float(np.sum(list(od.values()))), float(np.sum(list(oc.values())))
        out['P7'] = dict(check_frames=len(chk), default_sum_cm3=round(sd, 2), carved_sum_cm3=round(sc, 2),
                         default_median=round(float(np.median(list(od.values()))), 3),
                         carved_median=round(float(np.median(list(oc.values()))), 3),
                         pass_=bool(sc <= k_('p7_share') * sd) if sd > 0 else True)
    else:
        out['P7'] = dict(applies=False, flag='no_holdout')
    out['overlap_series'] = dict(default={int(k): round(v, 3) for k, v in ov_d.items()},
                                 carved={int(k): round(v, 3) for k, v in ov_c.items()})
    if b.meta.get('table'):
        tb = b.meta['table']
        W0 = b.poses['world_T_cam'][f_asm].astype(np.float64) @ b.poses[f'cam_T_{o}'][f_asm].astype(np.float64)
        Wg = W0 @ rels[f_asm]
        hp = SP.props(hulls_o, 0.3); gp = SP.props(hulls_p, 0.3)
        try:
            out['P1_precheck'] = settle(hulls_o, hulls_p, W0, Wg, (np.asarray(tb['n']), float(tb['d'])), hp, gp,
                                        copies=copies)
            hpd = SP.props(default_o, 0.3); gpd = SP.props(default_p, 0.3)
            out['P1_precheck_default'] = settle(default_o, default_p, W0, Wg, (np.asarray(tb['n']), float(tb['d'])),
                                                hpd, gpd, copies=copies)
        except Exception as e:
            out['P1_precheck'] = dict(error=f'{type(e).__name__}: {e}')
    else:
        out['P1_precheck'] = dict(applies=False, reason='no table plane in the bundle')
    out['P1'] = dict(run=False, reason='FlashCHORD scene not in this container (INTERLOCK 6.2: the pre-check does not '
                                       'decide; the settle is the Embodiment jitter_check, A3)')
    if do_proxy and run.kind == 'INSERTION':
        t0 = max(0, run.frames[0] - k_('pre'))
        frames = [f for f in range(t0, T) if f in rels]
        gpp = SP.props(hulls_p, 0.3)
        t = time.time()
        res = replay_proxy(hulls_o, hulls_p, rels, frames, asm,
                           dict(default=(default_o, default_p, True), carved=(hulls_o, hulls_p, True),
                                nocollide=(default_o, default_p, False)), copies=copies, guest_props=gpp, log=log)
        res['sec'] = round(time.time() - t, 1)
        res['frames'] = [frames[0], frames[-1]]
        res['judge'] = p3_pass(res, overlap_cm3=out['P6']['carved_asm_median'])     # F-I4.7: overlap clause restored
        out['P3'] = res
    tests = [out['P2']['pass_'], out['P4'][o]['pass_'], out['P4'][p]['pass_'], out['P6']['pass_'],
             out['P7'].get('pass_', True)]
    if 'P3' in out:
        tests.append(out['P3']['judge']['pass_'])
    out['P2_P7_pass'] = bool(all(tests))
    out['deliver_carved'] = False
    out['deliver_reason'] = ('P2-P7 pass but P1 (FlashCHORD settle) not run: default pieces delivered, carved pieces '
                             'kept for the FlashCHORD check') if out['P2_P7_pass'] else \
        'a physical test failed: default pieces'
    return out


# --------------------------------------------------------------------------- PREREG F-I5.5 S (collision carve)
def sink_xml(host, guest, T_wh, T_wg, n_table, d_table, gp, dt=0.002):
    """S scene (ev10w M3 setup): the receiver (host) FIXED at its pose (static geoms), the guest free, the table plane,
    gravity along -n_table, plain MuJoCo defaults otherwise."""
    g = -9.81 * np.asarray(n_table, float)
    n = np.asarray(n_table, float); p0 = -d_table * n
    z = n; x = np.cross([0, 1.0, 0], z) if abs(z[1]) < 0.9 else np.cross([1.0, 0, 0], z)
    x /= np.linalg.norm(x); y = np.cross(z, x)
    qp = _quat(np.stack([x, y, z], 1))
    qh = _quat(T_wh[:3, :3]); th = T_wh[:3, 3]
    qg = _quat(T_wg[:3, :3]); tg = T_wg[:3, 3]
    return f'''<mujoco><option timestep="{dt}" gravity="{g[0]:.5f} {g[1]:.5f} {g[2]:.5f}"/>
<asset>{_mesh_assets(host, 'a')}{_mesh_assets(guest, 'b')}</asset><worldbody>
<geom type="plane" size="2 2 0.1" pos="{p0[0]:.6f} {p0[1]:.6f} {p0[2]:.6f}" quat="{qp[0]:.6f} {qp[1]:.6f} {qp[2]:.6f} {qp[3]:.6f}" friction="0.5"/>
<body name="H" pos="{th[0]:.7f} {th[1]:.7f} {th[2]:.7f}" quat="{qh[0]:.7f} {qh[1]:.7f} {qh[2]:.7f} {qh[3]:.7f}">{_geoms(host, 'a')}</body>
<body name="G" pos="{tg[0]:.7f} {tg[1]:.7f} {tg[2]:.7f}" quat="{qg[0]:.7f} {qg[1]:.7f} {qg[2]:.7f} {qg[3]:.7f}"><freejoint/>{_inertial(gp)}{_geoms(guest, 'b')}</body>
</worldbody></mujoco>'''


def sink_test(host, guest, T_wh, T_wg, table, gp, copies=None, secs=2.0, dt=0.002, disp_max=0.004, tilt_max=5.0,
              seed=2):
    """PREREG F-I5.5 S, hands-off rest / sink at one frame: receiver fixed at T_wh, guest free starting at its tracked
    pose T_wg composed with each jitter (16 copies, 0.5 mm / 0.005 rad, common random numbers through SEED), table
    (n, d) in world, 2 s at 2 ms. Per copy: displacement of the guest's centre of mass from its TRACKED position, its
    vertical drop (dz, along -n), lateral part, tilt from the tracked orientation; NaN; below the receiver's lowest
    point. Pass: mean displacement <= 4 mm, mean tilt <= 5 deg, no NaN copy, no copy below."""
    import mujoco
    n_t, d_t = np.asarray(table[0], float), float(table[1])
    J = jitters(copies, seed=seed)
    com = np.asarray(gp['com'], float)
    x_tr = T_wg[:3, :3] @ com + T_wg[:3, 3]
    R_tr = T_wg[:3, :3]
    lowest = float(min((np.vstack(host) @ T_wh[:3, :3].T + T_wh[:3, 3]) @ n_t))
    rows, nan = [], 0
    for j in J:
        Jm = np.eye(4); Jm[:3, :3] = Rot.from_rotvec(j[3:]).as_matrix(); Jm[:3, 3] = j[:3]
        m = mujoco.MjModel.from_xml_string(sink_xml(host, guest, T_wh, T_wg @ Jm, n_t, d_t, gp, dt))
        d = mujoco.MjData(m)
        mujoco.mj_forward(m, d)
        gid = mujoco.mj_name2id(m, mujoco.mjtObj.mjOBJ_BODY, 'G')
        for _ in range(int(round(secs / dt))):
            mujoco.mj_step(m, d)
        if not np.all(np.isfinite(d.qpos)):
            nan += 1; continue
        x = d.xipos[gid].copy()
        R = d.xmat[gid].reshape(3, 3)
        dv = x - x_tr
        dz = float(-(dv @ n_t))
        rows.append(dict(disp=float(np.linalg.norm(dv)), dz=dz, lateral=float(np.linalg.norm(dv + dz * n_t)),
                         tilt=float(np.degrees(Rot.from_matrix(R_tr.T @ R).magnitude())),
                         below=bool(x @ n_t < lowest)))
    if not rows:
        return dict(nan=nan, copies=0, pass_=False, reason='no finite copy')
    M = {k: float(np.mean([r[k] for r in rows])) for k in ('disp', 'dz', 'lateral', 'tilt')}
    below = int(sum(r['below'] for r in rows))
    ok = M['disp'] <= disp_max and M['tilt'] <= tilt_max and nan == 0 and below == 0
    return dict(disp_mm=round(M['disp'] * 1e3, 3), dz_mm=round(M['dz'] * 1e3, 3), lateral_mm=round(M['lateral'] * 1e3, 3),
                tilt_deg=round(M['tilt'], 3), per_copy=[dict(disp_mm=round(r['disp'] * 1e3, 2), dz_mm=round(r['dz'] * 1e3, 2),
                                                             lateral_mm=round(r['lateral'] * 1e3, 2),
                                                             tilt_deg=round(r['tilt'], 2), below=r['below']) for r in rows],
                copies=len(rows), nan=nan, below=below, pass_=bool(ok))
