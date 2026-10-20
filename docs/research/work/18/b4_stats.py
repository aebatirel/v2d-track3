"""DIG 18 B4: statistics over relocalisation (b1), validation (b2) and VO (b3) outputs.
usage: python b4_stats.py <label> <reloc json> <validate json> [<reloc json> <validate json> ...]   -> b4_<label>.json"""
import sys, json, numpy as np
from scipy.signal import savgol_filter
from scipy.spatial.transform import Rotation as Rot

LABEL = sys.argv[1]; args = sys.argv[2:]
pairs = [(args[i], args[i + 1]) for i in range(0, len(args), 2)]


def ang(Ra, Rb):
    return np.degrees(np.linalg.norm(Rot.from_matrix(Ra.T @ Rb).as_rotvec()))


OUT = {}
for rj, vj in pairs:
    RL = json.load(open(rj)); V = json.load(open(vj)); tag = RL["tag"]; fr = RL["frames"]; n = len(fr)
    inl = np.array([r.get("inl_bc", 0) for r in fr]); inla = np.array([r.get("inl_a", 0) for r in fr])
    blur = np.array([r["blur_c"] for r in fr]); blura = np.array([r["blur_a"] for r in fr])
    tt = np.array([sum(r["time"].values()) for r in fr])
    o = dict(n=n, cov_rig=float((inl >= 30).mean()), cov_a=float((inla >= 30).mean()),
             inl_rig=np.percentile(inl, [0, 5, 50, 95]).tolist(), inl_a=np.percentile(inla, [0, 5, 50, 95]).tolist(),
             fail_rig=[int(r["frame"]) for r in fr if r.get("inl_bc", 0) < 30], fail_a=[int(r["frame"]) for r in fr if r.get("inl_a", 0) < 30],
             low_rig=[(int(r["frame"]), int(r.get("inl_bc", 0))) for r in fr if r.get("inl_bc", 0) < np.percentile(inl, 5)],
             corr_inl_blur=float(np.corrcoef(inl, blur)[0, 1]), corr_inla_blura=float(np.corrcoef(inla, blura)[0, 1]),
             time_med=float(np.median(tt)), time_p90=float(np.percentile(tt, 90)),
             time_parts={k: float(np.median([r["time"].get(k, 0) for r in fr])) for k in fr[0]["time"]})
    rows = V["rows"]; OFF = {k: np.array(v) if v is not None else None for k, v in V["offsets"].items()}
    T = {}
    for r in rows:
        T.setdefault(r["track"], {})[r["frame"]] = (np.array(r["C"]) - OFF[r["track"]], np.array(r["Rwc"]), r["shift_cm"], r["cham0"])
    # GT residual per track + by thirds of the clip
    for tr, d in T.items():
        f = np.array(sorted(d)); s = np.array([d[k][2] for k in f])
        thirds = [s[(f >= n * i / 3) & (f < n * (i + 1) / 3)] for i in range(3)]
        o[f"gt_{tr}"] = dict(n=len(s), med=float(np.median(s)), p90=float(np.percentile(s, 90)), max=float(s.max()),
                             frac_gt1cm=float((s > 1).mean()), thirds_med=[float(np.median(x)) if len(x) else None for x in thirds],
                             worst=[(int(k), round(float(v), 2)) for k, v in sorted(zip(f, s), key=lambda z: -z[1])[:6]])
    # jitter: high-frequency residual vs Savitzky-Golay (9 frames, order 2) on consecutive successful frames
    for tr in ("rig", "rigS", "a", "vo"):
        if tr not in T: continue
        f = np.array(sorted(T[tr])); C = np.array([T[tr][k][0] for k in f]); R = np.array([T[tr][k][1] for k in f])
        if len(f) < 15: continue
        Cs = savgol_filter(C, 9, 2, axis=0); rv = Rot.from_matrix(R).as_rotvec(); rvs = savgol_filter(np.unwrap(rv, axis=0), 9, 2, axis=0)
        jr = np.degrees(np.linalg.norm((Rot.from_rotvec(rvs).inv() * Rot.from_matrix(R)).as_rotvec(), axis=1))
        jp = np.linalg.norm(C - Cs, axis=1) * 1000
        dC = np.linalg.norm(np.diff(C, axis=0), axis=1) * 1000
        o[f"jit_{tr}"] = dict(pos_mm_rms=float(np.sqrt((jp ** 2).mean())), pos_mm_p90=float(np.percentile(jp, 90)),
                              rot_deg_rms=float(np.sqrt((jr ** 2).mean())), rot_deg_p90=float(np.percentile(jr, 90)),
                              step_mm_med=float(np.median(dC)))
    # rig vs a (raw poses, cam_a), rig vs map BA (map frames), vo vs rig over time
    for a_, b_ in (("rig", "a"), ("rig", "map"), ("rigS", "map"), ("a", "map"), ("vo", "rig"), ("vo", "a")):
        if a_ not in T or b_ not in T: continue
        f = sorted(set(T[a_]) & set(T[b_]))
        if not f: continue
        dp = np.array([np.linalg.norm(T[a_][k][0] - T[b_][k][0]) * 1000 for k in f]); dr = np.array([ang(T[a_][k][1], T[b_][k][1]) for k in f])
        dv = np.array([T[a_][k][0] - T[b_][k][0] for k in f]) * 1000
        rec = dict(n=len(f), pos_mm_med=float(np.median(dp)), pos_mm_p90=float(np.percentile(dp, 90)), pos_mm_max=float(dp.max()),
                   rot_deg_med=float(np.median(dr)), rot_deg_p90=float(np.percentile(dr, 90)), rot_deg_max=float(dr.max()),
                   mean_vec_mm=dv.mean(0).round(2).tolist(), sd_vec_mm=dv.std(0).round(2).tolist())
        if a_ == "vo":
            idx = [k for k in (len(f) // 4, len(f) // 2, 3 * len(f) // 4, len(f) - 1)]
            rec["at_frames"] = [(int(f[i]), round(float(dp[i]), 1), round(float(dr[i]), 2)) for i in idx]
        o[f"cmp_{a_}_vs_{b_}"] = rec
    # per-frame relative-motion consistency vs VO (bounds per-frame noise of both): camera-frame increments
    for tr in ("rig", "rigS", "a"):
        if tr not in T or "vo" not in T: continue
        f = [k for k in sorted(T[tr]) if k - 1 in T[tr] and k in T["vo"] and k - 1 in T["vo"]]
        dr, dt = [], []
        for k in f:
            inc = {}
            for x in (tr, "vo"):
                C0, R0 = T[x][k - 1][0], T[x][k - 1][1]; C1, R1 = T[x][k][0], T[x][k][1]
                inc[x] = (R0.T @ R1, R0.T @ (C1 - C0))
            dr.append(Rot.from_matrix(inc[tr][0] @ inc["vo"][0].T).as_rotvec()); dt.append(inc[tr][1] - inc["vo"][1])
        dr = np.degrees(np.array(dr)); dt = np.array(dt) * 1000
        o[f"inc_{tr}_vs_vo"] = dict(n=len(f), rot_sd_deg=np.round(dr.std(0), 4).tolist(), rot_mean_deg=np.round(dr.mean(0), 4).tolist(),
                                    rot_norm_p90_deg=float(np.percentile(np.linalg.norm(dr, axis=1), 90)),
                                    trans_sd_mm=np.round(dt.std(0), 3).tolist(), trans_norm_p90_mm=float(np.percentile(np.linalg.norm(dt, axis=1), 90)))
    OUT[tag] = o
    print(f"== {tag}: n={n} cov rig {o['cov_rig']:.3f} a {o['cov_a']:.3f} | inl rig p0/p5/p50 {o['inl_rig'][:3]} a {o['inl_a'][:3]} | "
          f"time med {o['time_med']:.2f}s p90 {o['time_p90']:.2f} {o['time_parts']}")
    for tr in ("map", "rig", "rigS", "a", "vo"):
        if f"gt_{tr}" in o:
            g = o[f"gt_{tr}"]; print(f"   GT {tr:3s}: n={g['n']} med {g['med']:.2f} cm p90 {g['p90']:.2f} max {g['max']:.2f} >1cm {g['frac_gt1cm']:.2f} thirds {g['thirds_med']} worst {g['worst'][:4]}")
    for tr in ("rig", "rigS", "a", "vo"):
        if f"jit_{tr}" in o: print(f"   jitter {tr}: {o[f'jit_{tr}']}")
    for k in [k for k in o if k.startswith("cmp_")]: print(f"   {k}: {o[k]}")
json.dump(OUT, open(f"b4_{LABEL}.json", "w"), indent=1)
