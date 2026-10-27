import sys, numpy as np, pandas as pd
sys.argv = [sys.argv[0], sys.argv[1], sys.argv[2]]
import importlib.util
spec = importlib.util.spec_from_file_location("sens", __file__.replace("sens2.py", "sens.py")); S = importlib.util.module_from_spec(spec); spec.loader.exec_module(S)
pd.set_option("display.width", 220)
s, r, l, df, ro, gr = S.run(detail=True)
print("== wrist-to-own-reference gap (m) over moving frames, baseline ==")
for v in ("adv", "grav", "adv+grav"):
    g = df[df.variant == v]
    print(f"{v:9s} median-track p95 {g.gap_p95.median():.3f}  max-track p95 {g.gap_p95.max():.3f}  max {g.gap_max.max():.3f}  "
          f"frames >0.15 m {100*np.average(g.gap_over15, weights=g.nmov):.2f}%  tracks with any >0.15: {(g.gap_over15>0).sum()}")
g = df[df.variant == "adv"]; print("adv gap p95 per track quantiles (10/50/90%):", np.round(np.percentile(g.gap_p95, [10, 50, 90]), 3))
print("== net actuator force needed |(M+m)a|+mg (N), max over tracks; hand gravcomp share on z = %.1f N ==" % (1.243 * 9.81))
print(df[df.variant == "default"].F_net_max.describe().round(2).to_string())
print("== P-term force kp*|r| max (N) by gain (prismatic) ==")
for kp, kd in [(25, 6.0), (50, 8.485), (100, 12.0), (200, 16.97), (400, 24.0), (6000, 60.0)]:
    mx = []
    for tr in S.TR:
        x = tr["x"]
        from scipy.signal import savgol_filter
        v = savgol_filter(x, 9, 2, deriv=1, delta=S.dt, axis=0); a = savgol_filter(x, 9, 2, deriv=2, delta=S.dt, axis=0)
        w = savgol_filter(S.cm.ang_vel(tr["q"].copy()), 9, 2, axis=0)
        mov = (np.linalg.norm(v, axis=1) > 0.05) | (np.linalg.norm(w, axis=1) > np.radians(30))
        if mov.sum() < 5: continue
        rr, _ = S.resid(x, v, a, mov.astype(float), kp, kd, 1.243, 0.3)
        mx.append(np.abs(kp * rr[mov]).max()); 
    print(f"kp {kp:5d} kd {kd:5.1f}: max |kp r| {max(mx):6.2f} N, max |kd v| part {max(mx)-0:.1f}")
print("== kp sweep: zeta-scaled kd vs kd fixed 6 ==")
for mode in ("zeta", 6.0):
    s2, _, _ = S.run(kd_mode=mode)
    print(mode, {k: (s2[k]["tracks"], round(100 * s2[k]["med_z_p95"], 1)) for k in ("kp50", "kp100", "kp200")})
for mode in ("zeta", 6.0):
    s2, _, _ = S.run(kd_mode=mode, win=5)
    print("win5", mode, {k: (s2[k]["tracks"], round(s2[k]["frame_pct"], 2), round(100 * s2[k]["med_z_p95"], 1)) for k in ("kp50", "kp100", "kp200")})
    s2, _, _ = S.run(kd_mode=mode, clip=0.15)
    print("clip.15", mode, {k: (s2[k]["tracks"], round(s2[k]["frame_pct"], 2)) for k in ("kp50", "kp100", "kp200")})
print("== rotation: inertia sensitivity (tracks per-axis / norm > 1 rad; median p95 axis) ==")
for I in (0.003, 0.011, 0.021, 0.03, 0.05, 0.1):
    _, rr, _ = S.run(I=I)
    print(f"I={I:5.3f}", {k: (rr[k]["tracks_axis"], rr[k]["tracks_norm"], round(rr[k]["med_p95_axis"], 3), round(rr[k]["Iterm_med"], 4), round(rr[k]["Dterm_med"], 3)) for k in rr}, rr["rot25"]["sat_eps"])
for w in (5, 7, 11):
    _, rr, _ = S.run(I=0.021, win=w)
    print(f"I=0.021 win{w}", {k: (rr[k]["tracks_axis"], rr[k]["tracks_norm"], round(rr[k]["med_p95_axis"], 3)) for k in rr}, rr["rot25"]["sat_eps"])
print("== wrist rigidly offset from object frame origin (random direction per track), 5 seeds ==")
for off in (0.05, 0.10, 0.15):
    res = []
    for sd in range(5):
        s3, r3, _ = S.run(offset=off, seed=sd)
        res.append((s3["default"]["tracks"], round(s3["default"]["frame_pct"], 2), s3["adv"]["tracks"], s3["adv+grav"]["tracks"], s3["kp50"]["tracks"], s3["kp100"]["tracks"]))
    print(f"offset {off:.2f} m: (default, default%, adv, adv+grav, kp50, kp100) per seed: {res}")
