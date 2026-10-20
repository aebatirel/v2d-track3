"""DIG 18 C6: export drift-free per-frame camera tracks for eval clips in MOCAP coordinates (prototype output of the
relocalisation module). Reads NO GT.
  c (mono time base): keyframes (map relocalisation every STRIDE frames, rig pose) bridged by VO v2 with a
      forward/backward blend: P(t) = interp_w( VO-propagated from previous keyframe, from next keyframe ), w = linear.
  a (colour time base): T_a_from_c (self-calibrated per clip, median over keyframes) x c(t + lag), lag = c2 best lag
      (GT-free rotation matching; DIG 20 found a[k+1] ~ b[k] in 36/39 clips).
Output json per clip: frames -> R_wc (columns right/down/forward in mocap), C (mocap z; x,y in map coords = per-episode
constant offset vs the dataset), plus flags (keyframe, bridge length, rig inliers).
usage: python c6_export.py <prefix s5> <c2 stats json> <out dir> [eps...]"""
import sys, os, json, numpy as np
from scipy.spatial.transform import Rotation as Rot, Slerp

HERE = os.path.dirname(os.path.abspath(__file__))
REG = json.load(open(f"{HERE}/a13_registration_refined.json")); Rm = np.array(REG["R_mocap_from_map"]); tz = REG["t_z"]
PFX, STATS, OD = sys.argv[1], json.load(open(sys.argv[2])), sys.argv[3]; os.makedirs(OD, exist_ok=True)
EPS = [int(e) for e in sys.argv[4:]] or [int(k) for k in STATS]


def T44(m):
    x = np.eye(4); x[:3] = np.array(m); return x


def inv(T):
    x = np.eye(4); x[:3, :3] = T[:3, :3].T; x[:3, 3] = -T[:3, :3].T @ T[:3, 3]; return x


def blend(A, B, w):
    """interpolate two world_from_cam poses"""
    r = Slerp([0, 1], Rot.from_matrix([A[:3, :3], B[:3, :3]]))([w]).as_matrix()[0]
    x = np.eye(4); x[:3, :3] = r; x[:3, 3] = (1 - w) * A[:3, 3] + w * B[:3, 3]; return x


def to_mocap(Wc):
    return Rm @ Wc[:3, :3], Rm @ Wc[:3, 3] + np.array([0, 0, tz])


for ep in EPS:
    RL = json.load(open(f"{HERE}/c1/{PFX}_e{ep}.json")); V = json.load(open(f"{HERE}/c3/vo_e{ep}.json"))
    Tc = {r["frame"]: T44(r["c_from_world"]) for r in RL["frames"] if r.get("inl_bc", 0) >= 30}
    Ta = {r["frame"]: T44(r["a_from_world"]) for r in RL["frames"] if r.get("inl_a", 0) >= 30}
    inl = {r["frame"]: r.get("inl_bc", 0) for r in RL["frames"]}
    Tv = {r["frame"]: T44(r["c_from_c0"]) for r in V["frames"]}
    ks = sorted(t for t in Tc if t in Tv); n = max(Tv) + 1
    Wc = {}
    for t in range(n):
        if t not in Tv: continue
        prv = max([k for k in ks if k <= t], default=None); nxt = min([k for k in ks if k >= t], default=None)
        P = [inv(Tv[t] @ inv(Tv[k]) @ Tc[k]) for k in (prv, nxt) if k is not None]
        if len(P) == 2 and nxt != prv:
            Wc[t] = blend(P[0], P[1], (t - prv) / (nxt - prv))
        else:
            Wc[t] = P[0]
    lag0 = STATS[str(ep)].get("a_lag", {}).get("best", -1.0)
    frac = lag0 - np.round(lag0)  # sub-frame part (~ -0.15: rolling-shutter / exposure offset)

    def c_at(tq):
        a = int(np.floor(tq))
        if a not in Wc or a + 1 not in Wc: return None
        return blend(Wc[a], Wc[a + 1], tq - a)
    # per-keyframe integer pairing n (lag = -n + frac): pick the n whose a<-c rotation is closest to the clip consensus;
    # then a single-changepoint fit (frame drops switch the pairing once, DIG 20) with fallback to one constant n
    N = (0, 1, 2, 3); kf = sorted(t for t in Ta if all(c_at(t - n + frac) is not None for n in N))
    ref = Rot.from_matrix([(Ta[t] @ c_at(t + lag0))[:3, :3] for t in kf]).mean()
    E = np.array([[np.degrees((ref.inv() * Rot.from_matrix((Ta[t] @ c_at(t - n + frac))[:3, :3])).magnitude()) for n in N] for t in kf])
    best = (E[:, int(np.argmin(E.sum(0)))].sum(), None, int(np.argmin(E.sum(0))), int(np.argmin(E.sum(0))))
    for i in range(3, len(kf) - 3):
        a, b = int(np.argmin(E[:i].sum(0))), int(np.argmin(E[i:].sum(0)))
        cost = E[:i, a].sum() + E[i:, b].sum() + 0.5  # small penalty per switch
        if a != b and cost < best[0]: best = (cost, kf[i], a, b)
    _, tsw, n1, n2 = best

    def lag_at(t):
        return -(n1 if (tsw is None or t < tsw) else n2) + frac
    rel = [Ta[t] @ c_at(t + lag_at(t)) for t in Ta if c_at(t + lag_at(t)) is not None]
    rr = Rot.from_matrix([x[:3, :3] for x in rel]).mean().as_matrix(); tt = np.median([x[:3, 3] for x in rel], 0)
    T_ac = np.eye(4); T_ac[:3, :3] = rr; T_ac[:3, 3] = tt
    out = []
    for t in sorted(Wc):
        Rc, Cc = to_mocap(Wc[t]); ca = c_at(t + lag_at(t))
        row = dict(frame=t, keyframe=t in Tc, inl_bc=inl.get(t), c=dict(R_wc=Rc.tolist(), C=Cc.tolist()))
        if ca is not None:
            Wa = ca @ inv(T_ac); Ra, Ca = to_mocap(Wa); row["a"] = dict(R_wc=Ra.tolist(), C=Ca.tolist())
        out.append(row)
    json.dump(dict(ep=ep, split="evaluation", source="DIG 18 room-map relocalisation (run1 map, a13 registration), keyframes every "
                   f"{RL.get('stride')} + VO v2 bridge; reads no GT", lag_a_minus_c_frames=dict(frac=frac, n_before=n1, n_after=n2, switch_keyframe=tsw), T_a_from_c=T_ac.tolist(),
                   convention="mocap rotation/gravity/z; x,y = map coords (per-episode constant offset vs the dataset, irrelevant to the "
                              "slot-0-aligned scorer); R_wc columns = right/down/forward of the UNDISTORTED pinhole image (a1); "
                              "c = ego_cam_c (mono time base), a = ego_cam_a at its own (earlier) capture time",
                   frames=out), open(f"{OD}/e{ep}.json", "w"))
    print(f"e{ep}: {len(out)} frames, {len(ks)} keyframes, lag -{n1}{frac:+.2f}" + (f" -> -{n2}{frac:+.2f} from keyframe {tsw}" if tsw is not None else "") + f", |t_ac| {np.linalg.norm(tt)*100:.2f} cm", flush=True)
