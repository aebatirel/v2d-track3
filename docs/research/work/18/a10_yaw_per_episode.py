"""DIG 18 A10 (from A9): per-episode 4-DoF fit (dx, dy, dz, dpsi) -> independent yaw check per public episode.
DIG 18 A9: validation of the map->mocap registration on frames OTHER than frame 0 (GT used only to score).
For a public episode, x,y offset (dx,dy) of the episode is taken from frame 0 (ref fit for refs; else none). Each
map-registered cam_a frame f of that episode gets its pose from a8_registration.json; GT objects at frame_index f
are projected (undistorted PINHOLE a, f=500). Score = chamfer distance (px) from the projected silhouette contour to
Canny edges, plus the best 2-D shift within +-30 px (a registration/drift error proxy). Overlays -> ov/.
usage: python a9_overlay_check.py <eps csv> [dxy source: fit|selfshift]"""
import sys, os, json, numpy as np, cv2, trimesh
sys.path.insert(0, "/Users/aebatirel/Documents/Code/v2d-research/work/11")
import c11
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
from a1_extract import NEW, newK
REG = json.load(open(f"{HERE}/a8_registration.json")); POSES = REG["poses"]
EPS = [int(x) for x in sys.argv[1].split(",")]
w, h, f = NEW["a"]; K = newK("a")
os.makedirs(f"{HERE}/ov10", exist_ok=True)
PTS = {}


def pts(name):
    if name not in PTS:
        m = c11.glb_mesh(name); PTS[name] = trimesh.sample.sample_surface(m, 15000, seed=0)[0]
    return PTS[name]


def render(P, Rwc, C):
    Xc = (P - C) @ Rwc; ok = Xc[:, 2] > 0.05
    uv = Xc[ok, :2] / Xc[ok, 2:3] * f + K[:2, 2]
    m = np.zeros((h, w), np.uint8); u = np.round(uv).astype(int); k = (u[:, 0] >= 0) & (u[:, 0] < w) & (u[:, 1] >= 0) & (u[:, 1] < h)
    m[u[k, 1], u[k, 0]] = 255
    m = cv2.morphologyEx(cv2.dilate(m, np.ones((3, 3), np.uint8)), cv2.MORPH_CLOSE, np.ones((7, 7), np.uint8))
    return m, float(np.median(Xc[ok, 2])) if ok.any() else np.nan


from scipy.optimize import minimize
from scipy.spatial.transform import Rotation as Rot
INIT = np.median([v["dxy_episode_offset"] for v in REG["refs_check"].values()], 0)


def contour_pts(sil):
    cnts, _ = cv2.findContours(sil, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
    return np.vstack([c.reshape(-1, 2) for c in cnts]) if cnts else None


def cham(cp, dt, dx=0, dy=0):
    q = cp + [dx, dy]; k = (q[:, 0] >= 0) & (q[:, 0] < w) & (q[:, 1] >= 0) & (q[:, 1] < h)
    return float(np.mean(np.minimum(dt[q[k, 1], q[k, 0]], 15))) if k.sum() > 50 else 15.0


rows = []; EPOUT = {}
for ep in EPS:
    e = c11.load_episode(ep); fr = list(e["frame"]); F = []
    for nm in sorted(k for k in POSES if k.startswith(f"a/p{ep:02d}_")):
        fi = int(nm.split("_")[1][:4]); i = fr.index(fi)
        P = np.vstack([pts(n)[::3] @ c11.R_of(e["pose"][i, j, 3:]).T + e["pose"][i, j, :3] for j, n in enumerate(e["names"])
                       if np.isfinite(e["pose"][i, j]).all()])
        img = cv2.imread(f"{HERE}/imgs/a/p{ep:02d}_{fi:04d}.jpg")
        edges = cv2.Canny(cv2.GaussianBlur(cv2.cvtColor(img, cv2.COLOR_BGR2GRAY), (5, 5), 0), 30, 90)
        F.append(dict(fi=fi, P=P, Rwc=np.array(POSES[nm]["R_wc"]), C=np.array(POSES[nm]["C"]), img=img,
                      dt=cv2.distanceTransform(255 - edges, cv2.DIST_L2, 3)))
    Cbar = np.mean([Fr["C"] for Fr in F], 0)
    def pose(Fr, o):
        Rz = Rot.from_euler("z", o[3] if len(o) > 3 else 0.0, degrees=True).as_matrix()
        return Rz @ Fr["Rwc"], Rz @ (Fr["C"] - Cbar) + Cbar + o[:3]
    def cost(o, sub=None):
        cs = []
        for Fr in (F if sub is None else [F[k] for k in sub]):
            sil, _ = render(Fr["P"], *pose(Fr, o)); cp = contour_pts(sil)
            cs.append(cham(cp, Fr["dt"]) if cp is not None else 15.0)
        return float(np.mean(cs))
    A9 = json.load(open(f"{HERE}/a9_overlay_check.json"))["episodes"][str(ep)]["o"]  # A9 translation as the start
    xs = np.array(list(A9) + [0.0]); st = np.array([0.01, 0.01, 0.01, 1.5])
    best = minimize(lambda z: cost(z), xs, method="Nelder-Mead", options=dict(initial_simplex=np.vstack([xs] + [xs + np.eye(4)[k] * st[k] for k in range(4)]),
                                                                             xatol=5e-4, fatol=1e-3, maxiter=300))
    # yaw profile around the optimum (translation re-fit at fixed yaw is skipped; report cost at +-2 deg with translation fixed)
    o = best.x
    fit = REG["refs_check"].get(str(ep)); c_at = cost(o)
    print(f"ep {ep:2d}: n={len(F)} offset dx {o[0]:+.3f} dy {o[1]:+.3f} dz {o[2]*100:+.1f} cm dpsi {o[3]:+.2f} deg | chamfer {c_at:.2f} px"
          + (f" | frame-0 fit dxy {np.round(fit['dxy_episode_offset'],3)}" if fit else ""), flush=True)
    EPOUT[ep] = dict(o=o.tolist(), cham=c_at, n=len(F))
    for Fr in F:
        sil, depth = render(Fr["P"], *pose(Fr, o)); cp = contour_pts(sil)
        if cp is None: continue
        c0 = cham(cp, Fr["dt"]); b = min(((cham(cp, Fr["dt"], dx, dy), dx, dy) for dx in range(-20, 21) for dy in range(-20, 21)))
        sh = float(np.hypot(b[1], b[2])); rows.append(dict(ep=ep, frame=Fr["fi"], cham0=c0, cham_best=b[0], shift=[b[1], b[2]], shift_px=sh,
                                                         shift_cm=sh * depth / f * 100, depth=depth))
        vis = Fr["img"].copy(); cv2.drawContours(vis, [cp.reshape(-1, 1, 2)], -1, (0, 0, 255), 1)
        cv2.imwrite(f"{HERE}/ov10/p{ep:02d}_{Fr['fi']:04d}.jpg", vis)
    rr = [r for r in rows if r["ep"] == ep]
    print("    per-frame residual shift (cm):", " ".join(f"{r['shift_cm']:.1f}" for r in rr), flush=True)
json.dump(dict(frames=rows, episodes=EPOUT), open(f"{HERE}/a10_yaw_per_episode.json", "w"), indent=1, default=float)
s_ = np.array([r["shift_cm"] for r in rows]); c0 = np.array([r["cham0"] for r in rows])
dz = np.array([v["o"][2] for v in EPOUT.values()]) * 100
print(f"n={len(rows)} frames / {len(EPOUT)} eps: residual best-shift median {np.median(s_):.2f} cm p90 {np.percentile(s_,90):.2f}; "
      f"chamfer median {np.median(c0):.2f} px; per-episode dz median {np.median(dz):+.1f} cm sd {dz.std():.1f}")
dp = np.array([v["o"][3] for v in EPOUT.values()])
print(f"per-episode dpsi (deg): median {np.median(dp):+.2f} mean {dp.mean():+.2f} sd {dp.std():.2f} | " + " ".join(f"{e}:{v['o'][3]:+.1f}" for e, v in EPOUT.items()))
