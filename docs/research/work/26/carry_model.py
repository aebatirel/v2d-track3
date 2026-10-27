"""Carry model: how much wrist-residual range the floating Sharpa wrist needs to carry each public GT object path,
under the default controller and under the control-theory levers of note 26 (stiffer gains, a reference
time-advance that acts as velocity feed-forward, a gravity pre-offset baked into the reference), plus the
grip/load factor a held object sees. Object motion stands in for the holding wrist while the object moves
(same proxy as note 14 kin.py). Ground truth is used for diagnostics on public episodes only. Research only.

Usage: python3 carry_model.py <dir with episode_*.parquet>  > carry_model.txt
"""
import glob, json, sys
import numpy as np
import pandas as pd
import pyarrow.parquet as pq
from scipy.signal import savgol_filter

M_HAND, M_OBJ, G = 1.243, 0.3, 9.81   # URDF hand mass (note 14), URDF object mass, gravity
KP0, KD0 = 25.0, 6.0                   # default prismatic wrist PD (sharpa_hands.py joint_overrides)
KR0, DR0 = 25.0, 6.0                   # default ball-wrist effort kp (action.wrist_kp) and passive damping
CLIP_P, CLIP_R = 0.20, 1.0             # per-axis residual clamps (m, rad)
FPS = 20.0                             # control rate at motion_speed 1.0 (timing rule, note 06)
dt = 1.0 / FPS
ZETA0 = KD0 / (2 * np.sqrt(KP0 * (M_HAND + M_OBJ)))   # default damping ratio, kept in the gain sweep


def load(path):
    t = pq.read_table(path)
    names = json.loads(t.schema.metadata[b"objects"])
    df = t.to_pandas().sort_values("frame_index")
    T, N = len(df), len(names)
    pos = np.full((T, N, 3), np.nan)
    quat = np.full((T, N, 4), np.nan)                 # wxyz
    for i, objs in enumerate(df["observation.objects"]):
        for o in objs:
            j = names.index(o["name"])
            p = np.asarray(o["pose"], float)
            if o.get("visible", True) and np.all(np.isfinite(p)):
                pos[i, j], quat[i, j] = p[:3], p[3:]
    return int(df["episode_index"].iloc[0]), names, pos, quat


def fill(x):
    """Linear interpolation over missing rows, edge hold."""
    x = x.copy()
    idx = np.arange(len(x))
    for k in range(x.shape[1]):
        ok = np.isfinite(x[:, k])
        if ok.sum() >= 2:
            x[:, k] = np.interp(idx, idx[ok], x[ok, k])
    return x


def ang_vel(q):
    """World angular velocity (rad/s) from consecutive wxyz quats."""
    q = q / np.linalg.norm(q, axis=1, keepdims=True)
    for i in range(1, len(q)):                         # sign continuity
        if np.dot(q[i], q[i - 1]) < 0:
            q[i] = -q[i]
    w0, v0 = q[:-1, :1], q[:-1, 1:]
    w1, v1 = q[1:, :1], q[1:, 1:]
    # dq = q1 * conj(q0)
    dw = w1 * w0 + np.sum(v1 * v0, 1, keepdims=True)
    dv = -w1 * v0 + w0 * v1 - np.cross(v1, v0)
    ang = 2 * np.arctan2(np.linalg.norm(dv, axis=1), np.abs(dw[:, 0]))
    axis = dv / np.maximum(np.linalg.norm(dv, axis=1, keepdims=True), 1e-12) * np.sign(dw)
    w = axis * ang[:, None] / dt
    return np.vstack([w[:1], w])


def gains(kp):
    """Prismatic and rotational gains at the default damping ratio (kd grows with sqrt(kp))."""
    kd = ZETA0 * 2 * np.sqrt(kp * (M_HAND + M_OBJ))
    return kp, kd


def residual_pos(x, v, a, carried, kp, kd, advance=False, grav_offset=False, m_obj=M_OBJ):
    """Per-axis residual (m) the policy must hold so the wrist follows x exactly under PD F = kp(e) - kd v."""
    M = M_HAND + m_obj * carried[:, None]
    F = M * a
    F[:, 2] += m_obj * G * carried
    r = (F + kd * v) / kp
    if advance:                                        # hand reference shifted tau = kd/kp ahead of the object
        tau = kd / kp
        t = np.arange(len(x)) * dt
        x_ahead = np.stack([np.interp(t + tau, t, x[:, k]) for k in range(3)], 1)
        r = r - (x_ahead - x)
    if grav_offset:                                    # + m g / kp on the reference z while carried
        r[:, 2] -= m_obj * G * carried / kp
    return r


def main(data_dir):
    rows, grip = [], []
    for f in sorted(glob.glob(f"{data_dir}/episode_*.parquet")):
        ep, names, pos, quat = load(f)
        for j, nm in enumerate(names):
            x = fill(pos[:, j])
            q = fill(quat[:, j])
            if not np.all(np.isfinite(x)) or len(x) < 15:
                continue
            v = savgol_filter(x, 9, 2, deriv=1, delta=dt, axis=0)
            a = savgol_filter(x, 9, 2, deriv=2, delta=dt, axis=0)
            w = savgol_filter(ang_vel(q), 9, 2, axis=0)
            wd = savgol_filter(w, 9, 2, deriv=1, delta=dt, axis=0)
            sp = np.linalg.norm(v, axis=1)
            mov = (sp > 0.05) | (np.linalg.norm(w, axis=1) > np.radians(30))
            if mov.sum() < 5:
                continue
            carried = mov.astype(float)
            # grip/load: specific force the grasp must transmit, |a - g| / g (1 = static weight)
            lf = np.linalg.norm(a + np.array([0, 0, G]), axis=1)[mov] / G
            grip.append(dict(ep=ep, obj=nm, load_p05=np.percentile(lf, 5), load_p50=np.median(lf),
                             load_p95=np.percentile(lf, 95), load_max=lf.max()))
            for label, kp_, adv, gof, m in [
                ("default kp25", 25, False, False, M_OBJ),
                ("kp25 +advance", 25, True, False, M_OBJ),
                ("kp25 +grav", 25, False, True, M_OBJ),
                ("kp25 +advance+grav", 25, True, True, M_OBJ),
                ("kp25 m=0.15", 25, False, False, 0.15),
                ("kp50", 50, False, False, M_OBJ),
                ("kp100", 100, False, False, M_OBJ),
                ("kp200", 200, False, False, M_OBJ),
                ("kp400", 400, False, False, M_OBJ),
                ("kp6000 (stiff)", 6000, False, False, M_OBJ),
            ]:
                kp, kd = gains(kp_) if kp_ != 25 else (KP0, KD0)
                if kp_ == 6000:
                    kd = 60.0                           # shipped stiff variant
                r = residual_pos(x, v, a, carried, kp, kd, adv, gof, m)[mov]
                ra = np.abs(r)
                rows.append(dict(ep=ep, obj=nm, variant=label, kp=kp, kd=round(kd, 1), nmov=int(mov.sum()),
                                 z_p95=np.percentile(ra[:, 2], 95), xy_p95=np.percentile(ra[:, :2].max(1), 95),
                                 max_axis=ra.max(), sat=float(np.mean(ra.max(1) > CLIP_P)),
                                 sag_static_cm=100 * m * G / kp))
            # rotation: residual = (I wdot + d w) / k ; I ~ hand 0.008 + object 0.003 kg m^2 (order of magnitude)
            I = 0.011
            for label, k, d in [("rot default k25 d6", KR0, DR0), ("rot k100 d12", 100, 12.0),
                                ("rot stiff k1200 d60", 1200, 60.0)]:
                rr = np.abs((I * wd + d * w) / k)[mov]
                rows.append(dict(ep=ep, obj=nm, variant=label, kp=k, kd=d, nmov=int(mov.sum()),
                                 z_p95=np.nan, xy_p95=np.percentile(rr.max(1), 95), max_axis=rr.max(),
                                 sat=float(np.mean(rr.max(1) > CLIP_R)), sag_static_cm=np.nan))
    df = pd.DataFrame(rows)
    pd.set_option("display.width", 200)
    print(f"default damping ratio zeta0 = {ZETA0:.3f}; gain sweep keeps it (kd = 2 zeta0 sqrt(kp M))")
    print("Per variant over moving object tracks (27 expected); residuals in m (rad for rot), clip 0.20 m / 1.0 rad")
    out = []
    for v_, g in df.groupby("variant", sort=False):
        out.append(dict(variant=v_, kp=g.kp.iloc[0], kd=g.kd.iloc[0],
                        tracks_saturating=int((g.sat > 0).sum()), n_tracks=len(g),
                        frame_sat_pct=100 * np.average(g.sat, weights=g.nmov),
                        median_z_p95=g.z_p95.median(), median_xy_p95=g.xy_p95.median(),
                        worst_axis=g.max_axis.max(), static_sag_cm=g.sag_static_cm.iloc[0],
                        lag_s=g.kd.iloc[0] / g.kp.iloc[0]))
    print(pd.DataFrame(out).round(3).to_string(index=False))
    print()
    gr = pd.DataFrame(grip)
    print("Grip/load factor |a - g|/g on moving frames (1.0 = static weight), per track:")
    print(gr.round(2).to_string(index=False))
    print("over tracks: median p05 %.2f, median p95 %.2f, max %.2f" % (gr.load_p05.median(), gr.load_p95.median(),
                                                                          gr.load_max.max()))
    print("min normal force to hold a 0.3 kg object at the worst load, two-sided pinch: mu=1.0 -> %.2f N, "
          "mu=0.5 -> %.2f N" % (M_OBJ * G * gr.load_max.max() / 2, M_OBJ * G * gr.load_max.max() / 1.0))
    df.to_csv("carry_model.csv", index=False)


if __name__ == "__main__":
    main(sys.argv[1])
