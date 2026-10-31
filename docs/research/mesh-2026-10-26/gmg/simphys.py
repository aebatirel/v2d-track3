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


def p3_pass(res):
    c = res.get('carved', {})
    d = res.get('default', {})
    if 'lag_cm_asm' not in c:
        return dict(pass_=False, reason='carved proxy produced no finite copy')
    ok = (c['lag_cm_asm'] <= k_('lag_asm_m') * 100 and c['lag_deg_asm'] <= k_('lag_asm_deg') and
          c['lag_cm_after_max'] <= k_('lag_after_m') * 100 and c['nan'] == 0)
    not_lim = 'lag_cm_asm' in d and d['lag_cm_asm'] < k_('not_limiting_m') * 100 and d['lag_deg_asm'] < k_('not_limiting_deg')
    return dict(pass_=bool(ok), slot_not_limiting=bool(not_lim))


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
