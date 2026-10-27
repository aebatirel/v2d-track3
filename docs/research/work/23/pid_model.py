"""Controller-only carry simulation: how far the floating Sharpa wrist strays from each public GT object path when
the policy adds NOTHING (zero residual), under PD, PID (FlashCHORD-style position integral) and feed-forward.
Object motion stands in for the holding wrist on moving frames (note 23 C). 100 Hz semi-implicit Euler per axis,
hand 1.243 kg gravity-compensated, 0.3 kg object attached on moving frames, effort limit per axis.
Diagnostics on public GT only. Research only.

Usage: python3 pid_model.py <dir with episode_*.parquet>  > pid_model.txt
"""
import glob, importlib.util, os, sys
import numpy as np
import pandas as pd
from scipy.signal import savgol_filter

spec = importlib.util.spec_from_file_location("cm", os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                                                 "carry_model.py"))
cm = importlib.util.module_from_spec(spec); spec.loader.exec_module(cm)
M_HAND, M_OBJ, G = cm.M_HAND, cm.M_OBJ, cm.G
CTRL_DT, SUB = 1.0 / 20.0, 5
DT = CTRL_DT / SUB


def simulate(x_ref, carried, kp, kd, effort, ki_gain=0.0, i_frac=0.15, ff=None):
    """Return wrist trajectory (T,3) at control rate. Targets are held over each 50 ms control step.
    ki_gain: FlashCHORD JointPositionIntegral gain (s^-2); integral effort = kd * v_int, clamped at i_frac*effort.
    ff: None | 'grav' | 'grav+vel' | 'full' (needs code: feed-forward force from the reference)."""
    T = len(x_ref)
    v_ref = np.gradient(x_ref, CTRL_DT, axis=0)
    a_ref = np.gradient(v_ref, CTRL_DT, axis=0)
    x = x_ref[0].copy(); v = np.zeros(3); v_int = np.zeros(3)
    out = np.zeros_like(x_ref)
    for t in range(T):
        tgt = x_ref[t]
        m = M_HAND + M_OBJ * carried[t]
        f_ff = np.zeros(3)
        if ff in ("grav", "grav+vel", "full"):
            f_ff[2] += M_OBJ * G * carried[t]
        if ff in ("grav+vel", "full"):
            f_ff += kd * v_ref[t]
        if ff == "full":
            f_ff += m * a_ref[t]
        for _ in range(SUB):
            e = tgt - x
            f_nom = np.clip(kp * e - kd * v, -effort, effort)
            f_int = np.zeros(3)
            if ki_gain > 0:
                v_int = v_int + DT * ki_gain * e
                f_int = np.clip(kd * v_int, -i_frac * effort, i_frac * effort)
                f_int = np.clip(f_int, -effort - f_nom, effort - f_nom)
                v_int = f_int / kd
            f = f_nom + f_int + f_ff
            f[2] -= M_OBJ * G * carried[t]          # object weight while held (hand itself is gravity-compensated)
            a = f / m
            v = v + DT * a
            x = x + DT * v
        out[t] = x
    return out


def main(data_dir):
    rows = []
    variants = [
        ("PD kp25 kd6 (default)", dict(kp=25, kd=6, effort=45)),
        ("PD kp100 kd12", dict(kp=100, kd=12, effort=45)),
        ("PID kp25 kd6, I gain 5 (stable)", dict(kp=25, kd=6, effort=45, ki_gain=5)),
        ("PID kp25 kd6, I gain 10 (stable)", dict(kp=25, kd=6, effort=45, ki_gain=10)),
        ("PID kp25 kd6, I gain 20 (UNSTABLE)", dict(kp=25, kd=6, effort=45, ki_gain=20)),
        ("PID kp100 kd12, I gain 20 (stable)", dict(kp=100, kd=12, effort=45, ki_gain=20)),
        ("PID kp100 kd12, I gain 40 (stable)", dict(kp=100, kd=12, effort=45, ki_gain=40)),
        ("PD kp25 + gravity FF (code)", dict(kp=25, kd=6, effort=45, ff="grav")),
        ("PD kp25 + gravity+velocity FF (code)", dict(kp=25, kd=6, effort=45, ff="grav+vel")),
        ("PD kp25 + full FF (code)", dict(kp=25, kd=6, effort=45, ff="full")),
    ]
    for f in sorted(glob.glob(f"{data_dir}/episode_*.parquet")):
        ep, names, pos, quat = cm.load(f)
        for j, nm in enumerate(names):
            x = cm.fill(pos[:, j])
            if not np.all(np.isfinite(x)) or len(x) < 15:
                continue
            xs = savgol_filter(x, 9, 2, axis=0)
            v = savgol_filter(x, 9, 2, deriv=1, delta=CTRL_DT, axis=0)
            w = savgol_filter(cm.ang_vel(cm.fill(quat[:, j])), 9, 2, axis=0)
            mov = (np.linalg.norm(v, axis=1) > 0.05) | (np.linalg.norm(w, axis=1) > np.radians(30))
            if mov.sum() < 5:
                continue
            carried = mov.astype(float)
            # first second after each release (carried 1 -> 0)
            rel = np.zeros(len(x), bool)
            for t in np.where(np.diff(carried) < 0)[0]:
                rel[t + 1:t + 21] = True
            for label, kw in variants:
                xw = simulate(xs, carried, **kw)
                err = np.linalg.norm(xw - xs, axis=1)
                ez = xw[:, 2] - xs[:, 2]
                rows.append(dict(ep=ep, obj=nm, variant=label,
                                 carry_rms_cm=100 * np.sqrt(np.mean(err[mov] ** 2)),
                                 carry_p95_cm=100 * np.percentile(err[mov], 95),
                                 release_up_cm=100 * (ez[rel].max() if rel.any() else 0.0)))
    df = pd.DataFrame(rows)
    pd.set_option("display.width", 200)
    for kp, kd in [(25, 6), (100, 12)]:
        m = M_HAND + M_OBJ
        print(f"Routh-Hurwitz (m s^3 + kd s^2 + kp s + Ki): kp {kp} kd {kd} stable only if Ki = kd*gain < kd*kp/m "
              f"= {kd * kp / m:.0f} N/(m s), i.e. I gain < {kp / m:.1f} s^-2")
    print("Zero-residual controller tracking of 27 moving public object paths (wrist proxy), real speed.")
    print("carry_* = 3-D wrist error on moving frames; release_up = max upward z overshoot in the 1 s after release.")
    agg = df.groupby("variant", sort=False).agg(median_carry_rms_cm=("carry_rms_cm", "median"),
                                                 median_carry_p95_cm=("carry_p95_cm", "median"),
                                                 worst_carry_p95_cm=("carry_p95_cm", "max"),
                                                 median_release_up_cm=("release_up_cm", "median"),
                                                 worst_release_up_cm=("release_up_cm", "max"),
                                                 n_tracks=("ep", "size"))
    print(agg.round(2).to_string())
    df.to_csv("pid_model.csv", index=False)


if __name__ == "__main__":
    main(sys.argv[1])
