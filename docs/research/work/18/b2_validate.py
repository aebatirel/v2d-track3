"""DIG 18 B2: validate per-frame relocalised poses with public GT (GT read ONLY here, after inference).
Tracks (all brought to cam_a, undistorted PINHOLE 1014x760 f=500):
  rig : b/c rig generalized-PnP pose (c_from_world) -> cam_a via calibrated extrinsics (T_ab T_bc)
  a   : cam_a single-camera PnP
  vo  : stereo VO chained from frame 0 (optional json from b3_vo.py; c_from_world, map frame)
  map : run1 bundle-adjusted pose of the map frames (every 30th) as reference (a13 registration)
Map -> mocap: a13_registration_refined (+ optional held-out-map alignment X_run1 = Ra X_run2 + ta).
Static GT objects at frame t: never-moving objects (max displacement < 1 cm) + moving objects before onset-3 frames.
One 3-D offset (dx,dy,dz) per episode and track is fitted (dataset x,y re-centring); for 'vo' the rig offset is used
(VO is anchored to the rig pose at frame 0), so its residual shows accumulated drift.
Per-frame residual = A9 metric: best extra 2-D shift (+-20 px) of the projected static-object contour vs Canny
edges, converted to cm at the median object depth; plus chamfer at zero shift.
usage: python b2_validate.py <reloc json> <out json> [align json|-] [vo json|-] [fit stride]"""
import sys, os, json, time, numpy as np, cv2, trimesh
sys.path.insert(0, "/Users/aebatirel/Documents/Code/v2d-research/work/11")
import c11
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
from a1_extract import NEW, newK, maps, clip
from scipy.optimize import minimize

RL = json.load(open(sys.argv[1])); OUTJ = sys.argv[2]
AL = json.load(open(sys.argv[3])) if len(sys.argv) > 3 and sys.argv[3] != "-" else None
VO = json.load(open(sys.argv[4])) if len(sys.argv) > 4 and sys.argv[4] != "-" else None
FS = int(sys.argv[5]) if len(sys.argv) > 5 else 10
REG = json.load(open(f"{HERE}/a13_registration_refined.json"))
Rm = np.array(REG["R_mocap_from_map"]); tz = REG["t_z"]
CAL = json.load(open("/Users/aebatirel/Documents/Code/v2d-research/data/track_3/public/meta/camera_calibration.json"))
T_bc = np.array([s for s in CAL["stereo_pairs"] if s["camera"] == "ego"][0]["left_to_right"], float)
T_ba = np.array(CAL["cameras"]["ego_cam_a"]["extrinsics_to_stereo_left"], float)
T_ac = np.linalg.inv(T_ba) @ T_bc  # X_a = T_ac X_c
w, h, f = NEW["a"]; K = newK("a"); EP = RL["ep"]; TAG = RL["tag"]


def T44(T34):
    T = np.eye(4); T[:3] = np.array(T34); return T


def to_run1(T):  # cam_from_world in run2 map -> run1 map
    if AL is None: return T
    Ra = np.array(AL["Ra"]); ta = np.array(AL["ta"]); S = np.eye(4); S[:3, :3] = Ra.T; S[:3, 3] = -Ra.T @ ta
    return T @ S


def mocap_pose(T_cw):  # cam_from_world (run1 map) -> (R_wc columns right/down/fwd in mocap, C in mocap with dx=dy=0)
    R, t = T_cw[:3, :3], T_cw[:3, 3]; C = -R.T @ t
    return Rm @ R.T, Rm @ C + np.array([0, 0, tz])


tracks = {k: {} for k in ("rig", "rigS", "a", "vo", "map")}
# self-calibrated a<-c extrinsic from this clip's own relocalisations (automatic, no GT): chordal-mean rotation, mean t
_P = [(T44(r["a_from_world"]) @ np.linalg.inv(T44(r["c_from_world"]))) for r in RL["frames"] if r.get("inl_bc", 0) >= 30 and r.get("inl_a", 0) >= 30]
_U, _S, _Vt = np.linalg.svd(sum(P[:3, :3] for P in _P)); T_ac_self = np.eye(4); T_ac_self[:3, :3] = _U @ _Vt
T_ac_self[:3, 3] = np.mean([P[:3, 3] for P in _P], 0)
print("T_ac factory t", np.round(T_ac[:3, 3] * 100, 2), "self t", np.round(T_ac_self[:3, 3] * 100, 2), "cm; rot diff deg",
      round(float(np.degrees(np.arccos(np.clip((np.trace(T_ac[:3, :3].T @ T_ac_self[:3, :3]) - 1) / 2, -1, 1)))), 3), flush=True)
for r in RL["frames"]:
    if r.get("inl_bc", 0) >= 30:
        tracks["rig"][r["frame"]] = mocap_pose(T_ac @ to_run1(T44(r["c_from_world"])))
        tracks["rigS"][r["frame"]] = mocap_pose(T_ac_self @ to_run1(T44(r["c_from_world"])))
    if r.get("inl_a", 0) >= 30: tracks["a"][r["frame"]] = mocap_pose(to_run1(T44(r["a_from_world"])))
if VO:
    T0_reloc = T44([r for r in RL["frames"] if r["frame"] == 0][0]["c_from_world"])  # VO anchored to reloc frame 0
    for r in VO["frames"]:
        if "c_from_c0" in r: tracks["vo"][r["frame"]] = mocap_pose(T_ac @ to_run1(T44(r["c_from_c0"]) @ T0_reloc))
for nm, v in REG["poses"].items():
    if nm.startswith(f"a/{TAG}_"): tracks["map"][int(nm.split("_")[1][:4])] = (np.array(v["R_wc"]), np.array(v["C"]))

# ---- GT static objects ----
e = c11.load_episode(EP); FR = list(e["frame"]); names = e["names"]
P0 = e["pose"][0]
disp = np.array([[np.linalg.norm(e["pose"][i, j, :3] - P0[j, :3]) for j in range(len(names))] for i in range(len(FR))])
onset = [int(np.argmax(disp[:, j] > 0.01)) if disp[:, j].max() > 0.01 else 10 ** 6 for j in range(len(names))]
PTS = {n: trimesh.sample.sample_surface(c11.glb_mesh(n), 15000, seed=0)[0][::3] for n in names}


def static_pts(t):
    i = FR.index(t); L = [PTS[n] @ c11.R_of(e["pose"][i, j, 3:]).T + e["pose"][i, j, :3] for j, n in enumerate(names)
                          if t < onset[j] - 3 and np.isfinite(e["pose"][i, j]).all()]
    return np.vstack(L) if L else None


def render(P, Rwc, C):
    Xc = (P - C) @ Rwc; ok = Xc[:, 2] > 0.05
    uv = Xc[ok, :2] / Xc[ok, 2:3] * f + K[:2, 2]
    m = np.zeros((h, w), np.uint8); u = np.round(uv).astype(int); k = (u[:, 0] >= 0) & (u[:, 0] < w) & (u[:, 1] >= 0) & (u[:, 1] < h)
    m[u[k, 1], u[k, 0]] = 255
    m = cv2.morphologyEx(cv2.dilate(m, np.ones((3, 3), np.uint8)), cv2.MORPH_CLOSE, np.ones((7, 7), np.uint8))
    return m, float(np.median(Xc[ok, 2])) if ok.any() else np.nan


def contour_pts(sil):
    cnts, _ = cv2.findContours(sil, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
    return np.vstack([c.reshape(-1, 2) for c in cnts]) if cnts else None


SH = np.array([(dx, dy) for dx in range(-20, 21) for dy in range(-20, 21)])


def cham_all(cp, dt):
    """chamfer (truncated 15 px) for every shift in SH; returns array len(SH)."""
    q = cp[None, :, :] + SH[:, None, :]
    k = (q[..., 0] >= 0) & (q[..., 0] < w) & (q[..., 1] >= 0) & (q[..., 1] < h)
    v = np.minimum(dt[np.clip(q[..., 1], 0, h - 1), np.clip(q[..., 0], 0, w - 1)], 15.0)
    v = np.where(k, v, 0.0); n = k.sum(1)
    return np.where(n > 50, v.sum(1) / np.maximum(n, 1), 15.0)


# ---- decode cam_a frames (undistorted as a1), edges ----
(m1, m2), _ = maps("a"); cap = cv2.VideoCapture(clip("public", EP, "a")); DT = {}; IMG = {}
need = set().union(*[set(v) for v in tracks.values()])
t = 0
while True:
    ok, fr = cap.read()
    if not ok: break
    if t in need:
        u = cv2.remap(fr, m1, m2, cv2.INTER_AREA)
        g = cv2.cvtColor(u, cv2.COLOR_BGR2GRAY); edges = cv2.Canny(cv2.GaussianBlur(g, (5, 5), 0), 30, 90)
        DT[t] = cv2.distanceTransform(255 - edges, cv2.DIST_L2, 3)
        if t % 10 == 0: IMG[t] = u
    t += 1
SP = {t: static_pts(t) for t in DT if t in FR}
print(time.strftime("%H:%M:%S"), TAG, "decoded", len(DT), "frames; tracks", {k: len(v) for k, v in tracks.items()}, flush=True)


def cost(track, o, frames):
    cs = []
    for t in frames:
        Rwc, C = tracks[track][t]; sil, _ = render(SP[t], Rwc, C + o); cp = contour_pts(sil)
        cs.append(cham_all(cp, DT[t])[len(SH) // 2] if cp is not None else 15.0)
    return float(np.mean(cs))


A9 = json.load(open(f"{HERE}/a9_overlay_check.json"))["episodes"]
init = np.array(A9[str(EP)]["o"]) if str(EP) in A9 else np.array([0.32, 0, 0])
OFF = {}
for tr in ("map", "rig", "rigS", "a"):
    fr_ok = sorted(t for t in tracks[tr] if SP.get(t) is not None)
    if not fr_ok: continue
    sub = fr_ok[::FS] if tr != "map" else fr_ok
    sub6 = sub[::max(1, len(sub) // 6)]
    g = min(((cost(tr, init + [dx, dy, 0], sub6), dx, dy) for dx in np.arange(-0.06, 0.061, 0.01) for dy in np.arange(-0.06, 0.061, 0.01)))
    x0 = init + [g[1], g[2], 0]
    o = minimize(lambda z: cost(tr, z, sub), x0, method="Nelder-Mead",
                 options=dict(initial_simplex=np.vstack([x0] + [x0 + np.eye(3)[k] * 0.01 for k in range(3)]), xatol=3e-4, fatol=1e-3, maxiter=250)).x
    OFF[tr] = o
    print(f"  offset {tr}: {np.round(o, 4)} (n fit {len(sub)})", flush=True)
OFF["vo"] = OFF.get("rig")

# ---- optional held-out yaw profile (B2_YAW=1): rotate the whole track about mocap z through its mean centre by d,
# re-fit the translation at each d (static GT objects, every FS-th frame), parabola around the minimum ----
YAW = {}
if os.environ.get("B2_YAW") == "1":
    import copy
    for tr in ("a", "rigS"):
        fr_ok = sorted(t for t in tracks[tr] if SP.get(t) is not None); sub = fr_ok[::FS]
        orig = {t: tracks[tr][t] for t in sub}; p0 = np.mean([orig[t][1] for t in sub], 0); prof = []
        for d in np.arange(-3.0, 3.01, 1.0):
            c_, s_ = np.cos(np.radians(d)), np.sin(np.radians(d)); Rz = np.array([[c_, -s_, 0], [s_, c_, 0], [0, 0, 1.0]])
            for t in sub: tracks[tr][t] = (Rz @ orig[t][0], Rz @ (orig[t][1] - p0) + p0)
            x0 = OFF[tr]
            o = minimize(lambda z: cost(tr, z, sub), x0, method="Nelder-Mead",
                         options=dict(initial_simplex=np.vstack([x0] + [x0 + np.eye(3)[k] * 0.01 for k in range(3)]), xatol=3e-4, fatol=1e-3, maxiter=200))
            prof.append((float(d), float(o.fun)))
        for t in sub: tracks[tr][t] = orig[t]
        ds = np.array([p[0] for p in prof]); cs = np.array([p[1] for p in prof]); i = int(np.clip(np.argmin(cs), 1, len(ds) - 2))
        den = cs[i - 1] - 2 * cs[i] + cs[i + 1]; best = ds[i] + (0.5 * (cs[i - 1] - cs[i + 1]) / den if den > 0 else 0)
        YAW[tr] = dict(profile=prof, best=float(best), curvature=float(den))
        print(f"  yaw profile {tr}: best d {best:+.2f} deg (curv {den:.3f}) " + " ".join(f"{d:+.0f}:{c:.3f}" for d, c in prof), flush=True)

rows = []
os.makedirs(f"{HERE}/b2ov", exist_ok=True)
for tr in ("rig", "rigS", "a", "vo", "map"):
    if tr not in OFF or OFF[tr] is None: continue
    for t in sorted(tracks[tr]):
        if SP.get(t) is None or t not in DT: continue
        Rwc, C = tracks[tr][t]; sil, depth = render(SP[t], Rwc, C + OFF[tr]); cp = contour_pts(sil)
        if cp is None: continue
        ca = cham_all(cp, DT[t]); b = int(np.argmin(ca)); sh = float(np.hypot(*SH[b]))
        rows.append(dict(track=tr, frame=t, cham0=float(ca[len(SH) // 2]), cham_best=float(ca[b]), shift=SH[b].tolist(),
                         shift_px=sh, shift_cm=sh * depth / f * 100, depth=depth, C=(C + OFF[tr]).tolist(), Rwc=Rwc.tolist()))
        if tr == "rig" and t in IMG and t % 40 == 0:
            vis = IMG[t].copy(); cv2.drawContours(vis, [cp.reshape(-1, 1, 2)], -1, (0, 0, 255), 1)
            cv2.imwrite(f"{HERE}/b2ov/{os.path.basename(OUTJ)[:-5]}_{t:04d}.jpg", vis)
json.dump(dict(reloc=sys.argv[1], align=sys.argv[3] if len(sys.argv) > 3 else "-", vo=sys.argv[4] if len(sys.argv) > 4 else "-",
               ep=EP, yaw=YAW, T_ac_self=T_ac_self.tolist(), offsets={k: (v.tolist() if v is not None else None) for k, v in OFF.items()}, onset=onset, names=names,
               rows=rows), open(OUTJ, "w"))
for tr in ("map", "rig", "rigS", "a", "vo"):
    s = np.array([r["shift_cm"] for r in rows if r["track"] == tr]); c = np.array([r["cham0"] for r in rows if r["track"] == tr])
    if len(s): print(f"  {TAG} {tr:3s}: n={len(s)} shift median {np.median(s):.2f} cm p90 {np.percentile(s, 90):.2f} max {s.max():.2f} | "
                     f"chamfer0 median {np.median(c):.2f} px", flush=True)
