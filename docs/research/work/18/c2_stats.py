"""DIG 18 C2: GT-free statistics of eval-clip relocalisation (c1 outputs) + VO (c3). Reads NO GT.
Per clip: coverage, inliers, cam_a pitch/roll/heading/height in mocap (a13 registration), c-only vs rig, a-vs-c relative
rotation spread (lag 0 and best lag, using VO to interpolate c at sub-frame times), VO drift vs map, 5-frame VO bridge
error (hybrid validation), increment noise bound.
usage: python c2_stats.py <prefix e.g. s5> <out json> [eps...]"""
import sys, os, json, glob, numpy as np
from scipy.spatial.transform import Rotation as Rot, Slerp

HERE = os.path.dirname(os.path.abspath(__file__))
REG = json.load(open(f"{HERE}/a13_registration_refined.json"))
Rm = np.array(REG["R_mocap_from_map"]); tz = REG["t_z"]
PFX, OUT = sys.argv[1], sys.argv[2]
EPS = [int(e) for e in sys.argv[3:]] or [1, 3, 5, 6, 8, 10, 14, 15, 16, 19, 20, 25, 28, 30, 32, 33, 35, 36, 37, 38]


def T44(m):
    x = np.eye(4); x[:3] = np.array(m); return x


def inv(T):
    R, t = T[:3, :3], T[:3, 3]; x = np.eye(4); x[:3, :3] = R.T; x[:3, 3] = -R.T @ t; return x


def ang(R):
    return float(np.degrees(np.linalg.norm(Rot.from_matrix(R).as_rotvec())))


def hpr(Rwc):
    f = Rwc[:, 2]; r = Rwc[:, 0]
    psi = np.degrees(np.arctan2(f[1], f[0])); th = np.degrees(np.arcsin(-f[2]))
    r0 = np.cross(f, [0, 0, 1.0]); r0 /= np.linalg.norm(r0)
    return psi, th, np.degrees(np.arctan2(np.dot(np.cross(r0, r), f), np.dot(r0, r)))


def mocap(T_cw):
    """cam_from_world (map) -> (R_wc mocap, C mocap with map x,y)"""
    R = T_cw[:3, :3]; t = T_cw[:3, 3]
    return Rm @ R.T, Rm @ (-R.T @ t) + np.array([0, 0, tz])


def q(x, p):
    return float(np.percentile(x, p)) if len(x) else float("nan")


def interp_pose(Ts, tq):
    """Ts: dict frame -> 4x4 world_from_cam ; linear/slerp interpolation at fractional frame tq"""
    a = int(np.floor(tq)); b = a + 1
    if a not in Ts or b not in Ts: return None
    w = tq - a
    sl = Slerp([0, 1], Rot.from_matrix([Ts[a][:3, :3], Ts[b][:3, :3]]))
    x = np.eye(4); x[:3, :3] = sl([w]).as_matrix()[0]; x[:3, 3] = (1 - w) * Ts[a][:3, 3] + w * Ts[b][:3, 3]
    return x


res = {}
for ep in EPS:
    fn = f"{HERE}/c1/{PFX}_e{ep}.json"
    if not os.path.exists(fn): print(f"e{ep}: missing {fn}"); continue
    D = json.load(open(fn)); fr = D["frames"]
    F = np.array([r["frame"] for r in fr])
    inl = {k: np.array([r.get(k, 0) or 0 for r in fr]) for k in ("inl_bc", "inl_c", "inl_b", "inl_a", "inl_c_only")}
    okr = inl["inl_bc"] >= 30; oka = inl["inl_a"] >= 30
    out = dict(n=len(fr), cov_rig=float(okr.mean()), cov_a=float(oka.mean()),
               inl={k: [int(v.min()), q(v, 5), q(v, 50)] for k, v in inl.items()})
    # mocap head pose from cam_a own PnP and from rig c
    Ta = {r["frame"]: T44(r["a_from_world"]) for r in fr if r.get("inl_a", 0) >= 30}
    Tc = {r["frame"]: T44(r["c_from_world"]) for r in fr if r.get("inl_bc", 0) >= 30}
    Tco = {r["frame"]: T44(r["c_only_from_world"]) for r in fr if r.get("inl_c_only", 0) >= 30 and "c_only_from_world" in r}
    H = np.array([hpr(mocap(Ta[t])[0]) for t in sorted(Ta)]); Cz = np.array([mocap(Ta[t])[1][2] for t in sorted(Ta)])
    out["pitch"] = [float(H[:, 1].min()), float(np.median(H[:, 1])), float(H[:, 1].max())]
    out["roll"] = [float(H[:, 2].min()), float(np.median(H[:, 2])), float(H[:, 2].max())]
    hd = (H[:, 0] - H[0, 0] + 180) % 360 - 180
    out["heading_rel_f0"] = [float(hd.min()), float(hd.max())]; out["heading_f0"] = float(H[0, 0])
    out["Cz"] = [float(Cz.min()), float(np.median(Cz)), float(Cz.max())]
    th = np.array([hpr(mocap(Ta[t])[0])[1] for t in F if t in Ta]); ia = np.array([inl["inl_a"][i] for i, t in enumerate(F) if t in Ta])
    ib = np.array([inl["inl_bc"][i] for i, t in enumerate(F) if t in Ta])
    out["corr_pitch_inl_a"] = float(np.corrcoef(th, ia)[0, 1]); out["corr_pitch_inl_bc"] = float(np.corrcoef(th, ib)[0, 1])
    out["inl_bc_steep10"] = q(ib[th >= np.percentile(th, 90)], 50)
    # c-only vs rig (rig-extrinsic compromise)
    dco = [(ang(Tco[t][:3, :3] @ Tc[t][:3, :3].T), np.linalg.norm(inv(Tco[t])[:3, 3] - inv(Tc[t])[:3, 3]) * 1000) for t in Tc if t in Tco]
    dco = np.array(dco)
    out["c_only_vs_rig"] = dict(rot_med=q(dco[:, 0], 50), rot_p90=q(dco[:, 0], 90), pos_med_mm=q(dco[:, 1], 50), pos_p90_mm=q(dco[:, 1], 90))
    # a vs c at lag 0 (relative rotation spread about the clip median)
    common = [t for t in Ta if t in Tc]
    rel0 = Rot.from_matrix([Ta[t][:3, :3] @ Tc[t][:3, :3].T for t in common])
    m0 = rel0.mean(); s0 = np.degrees((m0.inv() * rel0).magnitude())
    out["a_vs_c_lag0"] = [q(s0, 50), q(s0, 90)]
    # VO
    vf = f"{HERE}/c3/vo_e{ep}.json"
    if os.path.exists(vf):
        V = json.load(open(vf)); Tv = {r["frame"]: T44(r["c_from_c0"]) for r in V["frames"]}
        nvo = len(Tv); out["vo_frames"] = nvo
        # world_from_c at every frame via VO anchored to each keyframe's map pose (for sub-frame interpolation)
        k0 = min(Tc); Wv = {t: inv(Tv[t] @ inv(Tv[k0]) @ Tc[k0]) for t in Tv if k0 in Tv}  # pure VO chain, world_from_c
        # drift: VO chain from first keyframe vs map at each keyframe
        dr = []
        for t in sorted(Tc):
            if t not in Tv: continue
            E = (Tv[t] @ inv(Tv[k0]) @ Tc[k0]) @ inv(Tc[t])  # c_vo_from_c_map ... error transform
            Cv = inv(Tv[t] @ inv(Tv[k0]) @ Tc[k0])[:3, 3]; Cm = inv(Tc[t])[:3, 3]
            dr.append((t, np.linalg.norm(Cv - Cm) * 1000, ang(E[:3, :3])))
        dr = np.array(dr)
        out["vo_drift"] = dict(end_mm=float(dr[-1, 1]), end_deg=float(dr[-1, 2]), max_mm=float(dr[:, 1].max()), max_deg=float(dr[:, 2].max()),
                               dur_s=float(dr[-1, 0] / 20.0), rate_mm_s=float(dr[:, 1].max() / max(dr[-1, 0] / 20.0, 1e-3)),
                               rate_deg_s=float(dr[:, 2].max() / max(dr[-1, 0] / 20.0, 1e-3)))
        # 5-frame VO bridge (hybrid N=10 midpoint) error: predict t from keyframe t-5 by VO
        stride = int(D.get("stride", 5)); br = []; inc = []
        for t in sorted(Tc):
            k = t - stride
            if k in Tc and t in Tv and k in Tv:
                P = Tv[t] @ inv(Tv[k]) @ Tc[k]; E = P @ inv(Tc[t])
                br.append((np.linalg.norm(inv(P)[:3, 3] - inv(Tc[t])[:3, 3]) * 1000, ang(E[:3, :3])))
        br = np.array(br)
        out["bridge5"] = dict(pos_med_mm=q(br[:, 0], 50), pos_p95_mm=q(br[:, 0], 95), pos_max_mm=float(br[:, 0].max()),
                              rot_med=q(br[:, 1], 50), rot_p95=q(br[:, 1], 95), rot_max=float(br[:, 1].max()))
        # sub-frame lag of cam_a vs c: c pose at t+lag from VO-relative motion attached to the keyframe map pose
        def c_at(t, lag):
            """world_from_c at fractional time t+lag, = map pose at keyframe t moved by VO-relative motion"""
            Wt = inv(Tc[t]); Vt = Tv[t]
            loc = {}
            for j in (int(np.floor(t + lag)), int(np.floor(t + lag)) + 1):
                if j not in Tv: return None
                loc[j] = Wt @ (Vt @ inv(Tv[j]))  # world_from_c(j) = world_from_c(t) * c_t_from_c_j
            return interp_pose(loc, t + lag)
        lags = np.round(np.arange(-2.5, 0.51, 0.05), 3); prof = []
        for lag in lags:
            rr = []
            for t in common:
                Wc = c_at(t, lag)
                if Wc is None: continue
                rr.append(Ta[t][:3, :3] @ Wc[:3, :3])  # a_from_world * world_from_c = a_from_c(t+lag)
            r = Rot.from_matrix(rr); s = np.degrees((r.mean().inv() * r).magnitude()); prof.append((lag, q(s, 50), q(s, 90), len(rr)))
        prof = np.array(prof); b = int(np.argmin(prof[:, 1]))
        out["a_lag"] = dict(best=float(prof[b, 0]), med_at_best=float(prof[b, 1]), p90_at_best=float(prof[b, 2]),
                            med_at_0=float(prof[np.argmin(np.abs(prof[:, 0])), 1]), med_at_m1=float(prof[np.argmin(np.abs(prof[:, 0] + 1)), 1]),
                            med_at_m2=float(prof[np.argmin(np.abs(prof[:, 0] + 2)), 1]))
        # windowed best lag (detect pairing switches, e.g. dropped frames)
        win = []
        for w0 in range(0, int(max(common)) + 1, 60):
            ts = [t for t in common if w0 <= t < w0 + 60]
            if len(ts) < 6: continue
            bestw = None
            for lag in np.round(np.arange(-2.5, 0.51, 0.05), 3):
                rr = [Ta[t][:3, :3] @ c_at(t, lag)[:3, :3] for t in ts if c_at(t, lag) is not None]
                if len(rr) < 6: continue
                r = Rot.from_matrix(rr); s = float(np.median(np.degrees((r.mean().inv() * r).magnitude())))
                if bestw is None or s < bestw[1]: bestw = (float(lag), s)
            if bestw: win.append((w0, bestw[0], round(bestw[1], 3)))
        out["a_lag_windows"] = win
    res[ep] = out
    s = (f"e{ep:2d} n={out['n']:3d} cov rig {out['cov_rig']:.2f} a {out['cov_a']:.2f} | inl min/p5/med bc {out['inl']['inl_bc']} a {out['inl']['inl_a']}"
         f" | pitch {out['pitch'][0]:.1f}..{out['pitch'][2]:.1f} roll {out['roll'][0]:.1f}..{out['roll'][2]:.1f} Cz {out['Cz'][0]:.3f}..{out['Cz'][2]:.3f}"
         f" head {out['heading_rel_f0'][0]:+.1f}..{out['heading_rel_f0'][1]:+.1f} | corr(pitch,inl_bc) {out['corr_pitch_inl_bc']:+.2f}"
         f" | c-only vs rig {out['c_only_vs_rig']['rot_med']:.3f}deg {out['c_only_vs_rig']['pos_med_mm']:.1f}mm | a-c lag0 {out['a_vs_c_lag0'][0]:.3f}")
    if "vo_drift" in out:
        d = out["vo_drift"]; b5 = out["bridge5"]; al = out["a_lag"]
        s += (f"\n      VO drift max {d['max_mm']:.1f}mm/{d['max_deg']:.2f}deg over {d['dur_s']:.1f}s | bridge5 pos {b5['pos_med_mm']:.2f}/{b5['pos_p95_mm']:.2f}"
              f" rot {b5['rot_med']:.3f}/{b5['rot_p95']:.3f} | a lag best {al['best']:+.2f} (med {al['med_at_best']:.3f}, at0 {al['med_at_0']:.3f},"
              f" at-1 {al['med_at_m1']:.3f}, at-2 {al['med_at_m2']:.3f}) windows {out['a_lag_windows']}")
    print(s, flush=True)
json.dump(res, open(OUT, "w"), indent=1)
