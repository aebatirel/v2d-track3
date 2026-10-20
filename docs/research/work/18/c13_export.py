"""DIG 18 C13: the DEFAULT relocalisation module end to end (public-only map run3 + a13 + C10 tilt + C9 gate), per-frame
mocap camera tracks for eval clips. Reads NO GT (the C10 lean and the a13 registration are fixed offline constants
derived from public GT once, before inference).
Differences from c6_export:
  - input prefix is a run3 relocalisation converted to run1 coordinates (c13_to_run1.py);
  - keyframe acceptance (design step 2): trusted = rig inliers >= 100 and not a C9 glitch; 30-100 inliers = trusted
    only if the C9 VO gate agrees (min(dL, dR) <= THR); else rejected and bridged by VO; flags per frame;
  - registration: X = R_tilt (R_a13 X_run1 + [0, 0, t_z] - p) + p, R_tilt = rotation taking +z to the C10 GT up
    (lean (+0.30, -0.45) deg), pivot p = mean gaze point on the table (z = 0.6012) of the public cam_a map images,
    so the table height at the work area is unchanged.
usage: python c13_export.py <prefix r3s5r1> <c2 stats json> <c10 json> <out dir> [thr_mm=5] [eps...]"""
import sys, os, json, numpy as np
from scipy.spatial.transform import Rotation as Rot, Slerp

HERE = os.path.dirname(os.path.abspath(__file__))
REG = json.load(open(f"{HERE}/a13_registration_refined.json")); Rm = np.array(REG["R_mocap_from_map"]); tz = REG["t_z"]
PFX, STATS, C10, OD = sys.argv[1], json.load(open(sys.argv[2])), json.load(open(sys.argv[3])), sys.argv[4]
THR = float(sys.argv[5]) if len(sys.argv) > 5 else 5.0
EPS = [int(e) for e in sys.argv[6:]] or [int(k) for k in STATS]
os.makedirs(OD, exist_ok=True)
TABLE = 0.6012
lx, ly = np.radians(C10["mean"]); up = np.array([np.tan(lx), np.tan(ly), 1.0]); up /= np.linalg.norm(up)
ax = np.cross([0, 0, 1.0], up); R_tilt = Rot.from_rotvec(ax / np.linalg.norm(ax) * np.arcsin(np.linalg.norm(ax))).as_matrix()
G = []
for nm, p in REG["poses"].items():
    if not nm.startswith("a/p"): continue
    C = np.array(p["C"]); f = np.array(p["R_wc"])[:, 2]
    if f[2] < -0.2: G.append(C + (TABLE - C[2]) / f[2] * f)
PIV = np.array([*np.mean(G, 0)[:2], TABLE])


def T44(m):
    x = np.eye(4); x[:3] = np.array(m); return x


def inv(T):
    x = np.eye(4); x[:3, :3] = T[:3, :3].T; x[:3, 3] = -T[:3, :3].T @ T[:3, 3]; return x


def cen(T):
    return -T[:3, :3].T @ T[:3, 3]


def blend(A, B, w):
    r = Slerp([0, 1], Rot.from_matrix([A[:3, :3], B[:3, :3]]))([w]).as_matrix()[0]
    x = np.eye(4); x[:3, :3] = r; x[:3, 3] = (1 - w) * A[:3, 3] + w * B[:3, 3]; return x


def to_mocap(Wc):
    R = R_tilt @ Rm @ Wc[:3, :3]; C = R_tilt @ (Rm @ Wc[:3, 3] + np.array([0, 0, tz]) - PIV) + PIV
    return R, C


summary = {}
for ep in EPS:
    RL = json.load(open(f"{HERE}/c1/{PFX}_e{ep}.json")); V = json.load(open(f"{HERE}/c3/vo_e{ep}.json"))
    rows = {r["frame"]: r for r in RL["frames"]}
    Tall = {t: T44(r["c_from_world"]) for t, r in rows.items() if r.get("inl_bc", 0) >= 30}
    Ta = {t: T44(r["a_from_world"]) for t, r in rows.items() if r.get("inl_a", 0) >= 30}
    Tv = {r["frame"]: T44(r["c_from_c0"]) for r in V["frames"] if "c_from_c0" in r}
    ts = sorted(Tall); s = RL.get("stride", 5)
    # ---- keyframe acceptance (C9 gate + inlier rule)
    verdict = {}
    for t in sorted(rows):
        inl = rows[t].get("inl_bc", 0) or 0
        if t not in Tall or t not in Tv: verdict[t] = ("rejected", None); continue
        g = None
        if t - s in Tall and t + s in Tall and all(u in Tv for u in (t - s, t + s)):
            M = Tall[t]; preds = [Tv[t] @ inv(Tv[u]) @ Tall[u] for u in (t - s, t + s)]
            dL, dR = (np.linalg.norm(cen(M) - cen(p)) * 1000 for p in preds)
            dLR = np.linalg.norm(cen(preds[0]) - cen(preds[1])) * 1000; g = (min(dL, dR), dLR)
        glitch = g is not None and g[0] > THR and g[1] < 0.5 * g[0]
        if inl >= 100 and not glitch: verdict[t] = ("trusted", g)
        elif 30 <= inl < 100 and g is not None and g[0] <= THR: verdict[t] = ("trusted_gate", g)
        else: verdict[t] = ("rejected", g)
    ks = sorted(t for t, v in verdict.items() if v[0].startswith("trusted"))
    Tc = {t: Tall[t] for t in ks}; n = max(Tv) + 1
    Wc, bridge = {}, {}
    for t in range(n):
        if t not in Tv: continue
        prv = max([k for k in ks if k <= t], default=None); nxt = min([k for k in ks if k >= t], default=None)
        P = [inv(Tv[t] @ inv(Tv[k]) @ Tc[k]) for k in (prv, nxt) if k is not None]
        if not P: continue
        Wc[t] = blend(P[0], P[1], (t - prv) / (nxt - prv)) if (len(P) == 2 and nxt != prv) else P[0]
        bridge[t] = min(abs(t - k) for k in (prv, nxt) if k is not None)
    # ---- cam_a lag (as c6_export: sub-frame part from c2 best lag, integer pairing with one optional changepoint)
    lag0 = STATS[str(ep)].get("a_lag", {}).get("best", -1.0); frac = lag0 - np.round(lag0)

    def c_at(tq):
        a = int(np.floor(tq))
        if a not in Wc or a + 1 not in Wc: return None
        return blend(Wc[a], Wc[a + 1], tq - a)
    N = (0, 1, 2, 3); kf = sorted(t for t in Ta if all(c_at(t - m + frac) is not None for m in N))
    ref = Rot.from_matrix([(Ta[t] @ c_at(t + lag0))[:3, :3] for t in kf]).mean()
    E = np.array([[np.degrees((ref.inv() * Rot.from_matrix((Ta[t] @ c_at(t - m + frac))[:3, :3])).magnitude()) for m in N] for t in kf])
    best = (E[:, int(np.argmin(E.sum(0)))].sum(), None, int(np.argmin(E.sum(0))), int(np.argmin(E.sum(0))))
    for i in range(3, len(kf) - 3):
        a, b = int(np.argmin(E[:i].sum(0))), int(np.argmin(E[i:].sum(0)))
        cost = E[:i, a].sum() + E[i:, b].sum() + 0.5
        if a != b and cost < best[0]: best = (cost, kf[i], a, b)
    _, tsw, n1, n2 = best

    def lag_at(t):
        return -(n1 if (tsw is None or t < tsw) else n2) + frac
    rel = [Ta[t] @ c_at(t + lag_at(t)) for t in Ta if c_at(t + lag_at(t)) is not None]
    rr = Rot.from_matrix([x[:3, :3] for x in rel]); rmean = rr.mean()
    spread = np.degrees((rmean.inv() * rr).magnitude())
    T_ac = np.eye(4); T_ac[:3, :3] = rmean.as_matrix(); T_ac[:3, 3] = np.median([x[:3, 3] for x in rel], 0)
    out = []
    for t in sorted(Wc):
        Rc, Cc = to_mocap(Wc[t]); ca = c_at(t + lag_at(t)); v = verdict.get(t)
        row = dict(frame=t, keyframe=v[0] if v else None, inl_bc=rows[t].get("inl_bc") if t in rows else None,
                   gate_mm=(round(v[1][0], 2) if v and v[1] else None), bridge=bridge[t],
                   c=dict(R_wc=Rc.tolist(), C=Cc.tolist()))
        if ca is not None:
            Ra_, Ca_ = to_mocap(ca @ inv(T_ac)); row["a"] = dict(R_wc=Ra_.tolist(), C=Ca_.tolist())
        out.append(row)
    nk = len(verdict); nrej = sum(v[0] == "rejected" for v in verdict.values()); ngate = sum(v[0] == "trusted_gate" for v in verdict.values())
    json.dump(dict(ep=ep, split="evaluation",
                   source="DIG 18 default room-map module: public-only map run3 (-> run1 via b2_align_run3), a13 + C10 tilt, "
                          f"C9 gate {THR} mm, keyframes every {s} + VO v2 forward/backward bridge; reads no GT",
                   registration=dict(R_tilt=R_tilt.tolist(), pivot=PIV.tolist(), lean_deg=C10["mean"], a13_t_z=tz),
                   lag_a_minus_c_frames=dict(frac=frac, n_before=n1, n_after=n2, switch_keyframe=tsw), T_a_from_c=T_ac.tolist(),
                   a_from_c_rot_spread_deg=[float(np.median(spread)), float(np.percentile(spread, 90))],
                   convention="mocap rotation (C10-corrected gravity), z; x,y = map coords (per-episode constant offset vs the dataset, "
                              "irrelevant to the slot-0-aligned scorer); R_wc columns = right/down/forward of the UNDISTORTED pinhole "
                              "image (a1); c = ego_cam_c (mono time base), a = ego_cam_a at its own (earlier) capture time; "
                              "keyframe = trusted | trusted_gate | rejected | null (bridged frame); bridge = frames to the nearest trusted keyframe",
                   frames=out), open(f"{OD}/e{ep}.json", "w"))
    summary[ep] = dict(frames=len(out), keyframes=nk, rejected=nrej, trusted_gate=ngate, max_bridge=max(bridge.values()),
                       lag=[n1, n2, tsw, round(frac, 3)], t_ac_cm=round(float(np.linalg.norm(T_ac[:3, 3])) * 100, 2),
                       a_c_spread=[round(float(np.median(spread)), 3), round(float(np.percentile(spread, 90)), 3)])
    print(f"e{ep}: {len(out)} frames, keyframes {nk} (rejected {nrej}, gate-trusted {ngate}), max bridge {max(bridge.values())}, "
          f"lag -{n1}{frac:+.2f}" + (f" -> -{n2}{frac:+.2f} from {tsw}" if tsw is not None else "") +
          f", |t_ac| {np.linalg.norm(T_ac[:3, 3])*100:.2f} cm, a<-c spread {np.median(spread):.3f}/{np.percentile(spread, 90):.3f} deg", flush=True)
print("R_tilt angle deg", np.degrees(np.arcsin(np.linalg.norm(ax))), "pivot", PIV.round(4).tolist(), "n gaze", len(G))
json.dump({str(k): v for k, v in summary.items()}, open(f"{OD}/summary.json", "w"), indent=1)
