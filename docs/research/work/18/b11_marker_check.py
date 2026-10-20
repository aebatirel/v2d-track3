"""DIG 18 B11/B12: marker reprojection check of map-relocalised poses + direct comparison with note 17's
marker-registered cameras. Validation only (reads public GT and note 17 outputs AFTER inference).
Marker observations = note 17's automatic HoughCircles detections of GT-placed marker spheres on GT-static objects
(work/17/out/reg2_<ep>.json 'obs': t, cam, obj j, marker k, u, v (RAW distorted px), depth z).
Caveat: note 17 associated each detection within 6 a-eq px of ITS OWN camera prediction (selection window).
Tracks (all at the image's own frame index t):
  a17  : note 17 cameras (VO + drift knots fitted to these very markers; in-sample reference)
  a    : my cam_a own PnP (a obs only)
  rigS : my b/c rig c(t) -> cam_a via T_ac self-calibrated at lag 0 (as B2)
  rigL : my rig c(t + LAG) (LAG = -1.15 frames, B5) -> cam_a via T_ac self-calibrated at that lag (B5b)
  rig  : my b/c rig, for b and c obs (c pose; b = T_bc c)
World: my poses -> run1 map (align) -> mocap (a13); one world translation per episode/track either from B2 (edge
chamfer, independent of markers) or refitted on the markers (robust), to absorb the dataset x,y re-centring.
usage: python b11_marker_check.py <ep> <reloc json> <align json|-> <b2 json> <out json> [lag=-1.15]"""
import sys, json, numpy as np
from scipy.optimize import least_squares
from scipy.spatial.transform import Rotation as Rot, Slerp
sys.path.insert(0, "/Users/aebatirel/Documents/Code/v2d-research/work/17")
import lib17 as L

EP = int(sys.argv[1]); RL = json.load(open(sys.argv[2]))
AL = json.load(open(sys.argv[3])) if sys.argv[3] != "-" else None
B2 = json.load(open(sys.argv[4])) if sys.argv[4] != "-" else None; OUTJ = sys.argv[5]; LAG = float(sys.argv[6]) if len(sys.argv) > 6 else -1.15
HERE = "/Users/aebatirel/Documents/Code/v2d-research/work/18"
REG = json.load(open(f"{HERE}/a13_registration_refined.json")); Rm = np.array(REG["R_mocap_from_map"]); tz = REG["t_z"]
R17 = json.load(open(f"/Users/aebatirel/Documents/Code/v2d-research/work/17/out/reg2_{EP}.json"))
T_bc = np.array([s for s in json.load(open(f"{L.PUB}/meta/camera_calibration.json"))["stereo_pairs"] if s["camera"] == "ego"][0]["left_to_right"], float)
FA = L.cam("a")[0][0, 0]
gt = L.load_gt(EP)


def T44(T34):
    T = np.eye(4); T[:3] = np.array(T34); return T


S_al = np.eye(4)
if AL is not None:
    Ra = np.array(AL["Ra"]); ta = np.array(AL["ta"]); S_al[:3, :3] = Ra.T; S_al[:3, 3] = -Ra.T @ ta


def mocap(T_cw):  # cam_from_world (map of the reloc run) -> (R_wc mocap, C mocap with x,y in map coordinates)
    T = T_cw @ S_al; R, t = T[:3, :3], T[:3, 3]; C = -R.T @ t
    return Rm @ R.T, Rm @ C + np.array([0, 0, tz])


fr = {int(r["frame"]): r for r in RL["frames"]}
A = {t: T44(r["a_from_world"]) for t, r in fr.items() if r.get("inl_a", 0) >= 30}
Cc = {t: T44(r["c_from_world"]) for t, r in fr.items() if r.get("inl_bc", 0) >= 30}
ts = np.array(sorted(Cc)); slc = Slerp(ts, Rot.from_matrix([Cc[t][:3, :3] for t in ts]))
cen = np.array([-Cc[t][:3, :3].T @ Cc[t][:3, 3] for t in ts])


def c_at(tau):  # c cam_from_world at fractional frame tau (slerp/lerp)
    if tau < ts[0] or tau > ts[-1]: return None
    R = slc([tau]).as_matrix()[0]; C = np.array([np.interp(tau, ts, cen[:, i]) for i in range(3)])
    T = np.eye(4); T[:3, :3] = R; T[:3, 3] = -R @ C; return T


def chordal_T(P):
    U, _, Vt = np.linalg.svd(sum(p[:3, :3] for p in P)); T = np.eye(4); T[:3, :3] = U @ Vt
    T[:3, 3] = np.mean([p[:3, 3] for p in P], 0); return T


T_ac0 = chordal_T([A[t] @ np.linalg.inv(Cc[t]) for t in A if t in Cc])
T_acL = chordal_T([A[t] @ np.linalg.inv(c_at(t + LAG)) for t in A if c_at(t + LAG) is not None])
tracks = {"a17": {}, "a": {}, "rigS": {}, "rigL": {}, "rig_c": {}, "rig_b": {}, "a17_b": {}, "a17_c": {}}
for t in range(len(R17["cams"])):
    tracks["a17"][t] = (np.array(R17["cams"][t]["Rwc"]), np.array(R17["cams"][t]["C"]))
    tracks["a17_b"][t] = (np.array(R17["cams_b"][t]["Rwc"]), np.array(R17["cams_b"][t]["C"]))
    tracks["a17_c"][t] = (np.array(R17["cams_c"][t]["Rwc"]), np.array(R17["cams_c"][t]["C"]))
for t in A: tracks["a"][t] = mocap(A[t])
for t in Cc:
    tracks["rigS"][t] = mocap(T_ac0 @ Cc[t]); tracks["rig_c"][t] = mocap(Cc[t]); tracks["rig_b"][t] = mocap(T_bc @ Cc[t])
    T = c_at(t + LAG)
    if T is not None: tracks["rigL"][t] = mocap(T_acL @ T)

import os
obs = R17["obs"]; res17 = np.array(R17["res"])
OBJF = os.environ.get("B11_OBJ")  # optional: keep only obs of objects whose name contains this substring
if OBJF:
    keep = [i for i, o in enumerate(obs) if OBJF in gt["names"][o[2]]]; obs = [obs[i] for i in keep]; res17 = res17[keep]
    R17 = dict(R17); R17["lomo"] = None
CAMF = os.environ.get("B11_CAMS")  # optional: keep only obs from these cameras, e.g. "bc"
if CAMF:
    keep = [i for i, o in enumerate(obs) if o[1] in CAMF]; obs = [obs[i] for i in keep]; res17 = res17[keep]
    R17 = dict(R17); R17["lomo"] = None
X = np.array([L.markers_world(gt, o[0], o[2])[o[3]] for o in obs])  # GT marker centre (dataset world) at row t
UV = np.array([[o[4], o[5]] for o in obs]); Z = np.array([o[6] for o in obs]); CAM = np.array([o[1] for o in obs]); TT = np.array([o[0] for o in obs]); JJ = np.array([o[2] for o in obs])
SC = np.array([FA / L.cam(c)[0][0, 0] for c in CAM])
USE = {"a17": ("a17", "a17_b", "a17_c"), "a": ("a", None, None), "rigS": ("rigS", "rig_b", "rig_c"), "rigL": ("rigL", "rig_b", "rig_c")}
if B2 is not None:
    B2OFF = {"a17": [0, 0, 0], "a": B2["offsets"]["a"], "rigS": B2["offsets"]["rigS"], "rigL": B2["offsets"]["rigS"]}
else:  # no B2 run: initialise the translation from note 17's camera centres (only an init; mode 'b2' is then this init)
    B2OFF = {"a17": [0, 0, 0]}
    for k in ("a", "rigS", "rigL"):
        B2OFF[k] = np.mean([tracks["a17"][t][1] - tracks[k][t][1] for t in tracks[k] if t in tracks["a17"]], 0).tolist()


C0 = {}


def resid(name, o):
    """o: 3 (world translation added to camera centres) or 6 (+ world rotation vector about the track's mean centre)."""
    ta, tb, tc = USE[name]; out = np.full((len(obs), 2), np.nan)
    Rd = Rot.from_rotvec(o[3:6]).as_matrix() if len(o) > 3 else np.eye(3)
    if name not in C0: C0[name] = np.mean([v[1] for v in tracks[ta].values()], 0)
    c0 = C0[name]
    for i in range(len(obs)):
        key = {"a": ta, "b": tb, "c": tc}[CAM[i]]
        if key is None or TT[i] not in tracks[key]: continue
        R, C = tracks[key][TT[i]]; R = Rd @ R; C = Rd @ (C - c0) + c0
        p, _ = L.project(X[i][None], R, C + o[:3], CAM[i], own=True)
        out[i] = (p[0] - UV[i]) * SC[i]
    return out


def stats(e, m):
    v = e[m]; v = v[np.isfinite(v)]
    return dict(n=int(len(v)), med=float(np.median(v)), p75=float(np.percentile(v, 75)), p90=float(np.percentile(v, 90))) if len(v) else dict(n=0)


R = {"ep": EP, "lag": LAG, "n_obs": len(obs), "note17_insample": stats(res17, np.ones(len(res17), bool)), "tracks": {}}
lom = np.array([np.hypot(a[4], a[5]) for a in R17.get("lomo", [])]) if R17.get("lomo") else None
if lom is not None: R["note17_lomo"] = stats(lom, np.ones(len(lom), bool))
print(f"ep {EP}: {len(obs)} marker obs (a {np.sum(CAM == 'a')} b {np.sum(CAM == 'b')} c {np.sum(CAM == 'c')}); note17 in-sample med "
      f"{np.median(res17):.2f} p90 {np.percentile(res17, 90):.2f}" + (f"; LOMO med {np.median(lom):.2f} p90 {np.percentile(lom, 90):.2f}" if lom is not None else "") + " (a-eq px)")
T_end = max(TT) + 1
TRK = os.environ.get("B11_TRACKS")
for name in [n for n in USE if not TRK or n in TRK.split(",")]:
    rr = {}
    for mode in ("b2", "fit", "fit6"):
        o = np.array(B2OFF[name], float)
        if mode == "fit6": o = np.r_[np.array(rr["fit"]["offset_m"]), 0, 0, 0]
        if mode in ("fit", "fit6"):
            def f(oo):
                e = resid(name, oo); e = e[np.isfinite(e[:, 0])]; return e.ravel()
            sol = least_squares(f, o, loss="cauchy", f_scale=2.5); o = sol.x
            if mode == "fit6":  # Gauss-Newton covariance (robust residual scale) -> standard errors
                J = sol.jac; r_ = sol.fun; s2 = np.median(np.abs(r_)) ** 2 / 0.4549 ** 2 if len(r_) else np.nan
                cov = np.linalg.pinv(J.T @ J) * s2; se = np.sqrt(np.diag(cov))
                print(f"        fit6 std err: trans mm {np.round(se[:3] * 1000, 1)} rot deg {np.round(np.degrees(se[3:]), 2)}; "
                      f"corr(rot, trans) max {np.max(np.abs((cov / np.outer(se, se))[:3, 3:])):.3f}", flush=True)
        e = resid(name, o); n = np.hypot(e[:, 0], e[:, 1])
        d = dict(offset_m=o[:3].tolist(), rot_deg=np.degrees(o[3:6]).tolist() if len(o) > 3 else None)
        if len(o) > 3:
            Rd = Rot.from_rotvec(o[3:6]).as_matrix(); d["rot_tilt_deg"] = float(np.degrees(np.arccos(np.clip(Rd[2, 2], -1, 1))))
            d["rot_yaw_deg"] = float(np.degrees(np.arctan2(Rd[1, 0] - Rd[0, 1], Rd[0, 0] + Rd[1, 1])))
        for cm in ("a", "b", "c", "all"):
            m = (CAM == cm) if cm != "all" else np.ones(len(obs), bool)
            d[cm] = stats(n, m)
        mm = n * Z / FA * 1000; d["lateral_mm_all"] = stats(mm, np.ones(len(obs), bool))
        d["thirds_a_med"] = [stats(n, (CAM == "a") & (TT >= T_end * k / 3) & (TT < T_end * (k + 1) / 3)).get("med", np.nan) for k in range(3)]
        d["bias_px_a"] = np.nanmedian(e[CAM == "a"], 0).tolist() if np.any(CAM == "a") else None
        d["per_obj_a"] = {f"{gt['names'][j]}": stats(n, (CAM == "a") & (JJ == j)) for j in sorted(set(JJ.tolist()))}
        rr[mode] = d
        if mode != "b2" or name != "a17":
            print(f"  {name:5s} {mode:4s} off {np.round(o[:3] * 1000, 1)} mm" + (f" rot tilt {d['rot_tilt_deg']:.2f} yaw {d['rot_yaw_deg']:+.2f} deg" if len(o) > 3 else "") + f" | a {d['a'].get('med', np.nan):.2f}/{d['a'].get('p90', np.nan):.2f} (n {d['a']['n']})"
                  f" b {d['b'].get('med', np.nan):.2f} c {d['c'].get('med', np.nan):.2f} all {d['all'].get('med', np.nan):.2f}/{d['all'].get('p90', np.nan):.2f}"
                  f" | lat mm {d['lateral_mm_all'].get('med', np.nan):.2f}/{d['lateral_mm_all'].get('p90', np.nan):.2f} | thirds(a) {np.round(d['thirds_a_med'], 2)} | bias a {np.round(d['bias_px_a'], 2) if d['bias_px_a'] is not None else '-'}", flush=True)
        if mode != "b2": print("        per object (cam a med/p90 px): " + "; ".join(f"{k[:12]} {v.get('med', np.nan):.2f}/{v.get('p90', np.nan):.2f} n{v['n']}" for k, v in d["per_obj_a"].items()))
    rr["per_obs_fit"] = [None if not np.isfinite(v) else float(v) for v in np.hypot(*resid(name, np.array(rr["fit"]["offset_m"])).T)]
    R["tracks"][name] = rr

# ---- B12: direct camera comparison with note 17 cameras (cam_a, frame t), rigid 6-DoF (rotation = chordal mean) ----
R["cam_cmp"] = {}
for name in [n for n in ("a", "rigS", "rigL") if not TRK or n in TRK.split(",")]:
    tt = [t for t in tracks[name] if t in tracks["a17"]]
    Rm_ = [tracks["a17"][t][0] @ tracks[name][t][0].T for t in tt]
    U, _, Vt = np.linalg.svd(sum(Rm_)); R0 = U @ Vt
    C1 = np.array([tracks[name][t][1] for t in tt]); C2 = np.array([tracks["a17"][t][1] for t in tt])
    t0 = np.mean(C2 - C1 @ R0.T, 0); dp = np.linalg.norm(C2 - (C1 @ R0.T + t0), axis=1) * 1000
    dr = np.array([np.degrees(np.linalg.norm(Rot.from_matrix(R0.T @ m).as_rotvec())) for m in Rm_])
    # translation-only (R0 = I) for comparison
    t1 = np.mean(C2 - C1, 0); dp1 = np.linalg.norm(C2 - (C1 + t1), axis=1) * 1000
    z0 = R0[:, 2]; tilt = float(np.degrees(np.arccos(np.clip(z0[2], -1, 1))))
    yaw = float(np.degrees(np.arctan2(R0[1, 0] - R0[0, 1], R0[0, 0] + R0[1, 1])))
    n = len(tt); th = [slice(0, n // 3), slice(n // 3, 2 * n // 3), slice(2 * n // 3, n)]
    R["cam_cmp"][name] = dict(n=n, R0_yaw_deg=yaw, R0_tilt_deg=tilt, t0_mm=(t0 * 1000).tolist(),
                              pos_mm=dict(med=float(np.median(dp)), p90=float(np.percentile(dp, 90)), max=float(dp.max())),
                              rot_deg=dict(med=float(np.median(dr)), p90=float(np.percentile(dr, 90)), max=float(dr.max())),
                              pos_mm_translation_only_med=float(np.median(dp1)),
                              thirds_pos_mm=[float(np.median(dp[s])) for s in th], thirds_rot_deg=[float(np.median(dr[s])) for s in th],
                              per_frame=[[int(t), float(a), float(b)] for t, a, b in zip(tt, dp, dr)])
    print(f"  cam vs note17 [{name}] n {n}: R0 yaw {yaw:+.2f} tilt {tilt:.2f} deg | pos mm med {np.median(dp):.2f} p90 {np.percentile(dp, 90):.2f} max {dp.max():.2f}"
          f" | rot deg med {np.median(dr):.3f} p90 {np.percentile(dr, 90):.3f} max {dr.max():.3f} | thirds pos {np.round(R['cam_cmp'][name]['thirds_pos_mm'], 2)} rot {np.round(R['cam_cmp'][name]['thirds_rot_deg'], 3)}", flush=True)
json.dump(R, open(OUTJ, "w"))
