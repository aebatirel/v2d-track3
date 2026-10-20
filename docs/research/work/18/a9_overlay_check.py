"""DIG 18 A9: validation of the map->mocap registration on frames OTHER than frame 0 (GT used only to score).
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
os.makedirs(f"{HERE}/ov", exist_ok=True)
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
    def cost(o, sub=None):
        cs = []
        for Fr in (F if sub is None else [F[k] for k in sub]):
            sil, _ = render(Fr["P"], Fr["Rwc"], Fr["C"] + o); cp = contour_pts(sil)
            cs.append(cham(cp, Fr["dt"]) if cp is not None else 15.0)
        return float(np.mean(cs))
    sub = list(range(0, len(F), max(1, len(F) // 6)))
    g = min(((cost(np.array([INIT[0] + dx, INIT[1] + dy, 0.0]), sub), dx, dy) for dx in np.arange(-0.10, 0.101, 0.01)
             for dy in np.arange(-0.10, 0.101, 0.01)))
    x0 = np.array([INIT[0] + g[1], INIT[1] + g[2], 0.0])
    o = minimize(lambda z: cost(z), x0, method="Nelder-Mead", options=dict(initial_simplex=np.vstack([x0] + [x0 + np.eye(3)[k] * 0.01 for k in range(3)]),
                                                                          xatol=5e-4, fatol=1e-3, maxiter=250)).x
    fit = REG["refs_check"].get(str(ep)); c_at = cost(o)
    print(f"ep {ep:2d}: n={len(F)} offset dx {o[0]:+.3f} dy {o[1]:+.3f} dz {o[2]*100:+.1f} cm | chamfer {c_at:.2f} px"
          + (f" | frame-0 fit dxy {np.round(fit['dxy_episode_offset'],3)}" if fit else ""), flush=True)
    EPOUT[ep] = dict(o=o.tolist(), cham=c_at, n=len(F))
    for Fr in F:
        sil, depth = render(Fr["P"], Fr["Rwc"], Fr["C"] + o); cp = contour_pts(sil)
        if cp is None: continue
        c0 = cham(cp, Fr["dt"]); b = min(((cham(cp, Fr["dt"], dx, dy), dx, dy) for dx in range(-20, 21) for dy in range(-20, 21)))
        sh = float(np.hypot(b[1], b[2])); rows.append(dict(ep=ep, frame=Fr["fi"], cham0=c0, cham_best=b[0], shift=[b[1], b[2]], shift_px=sh,
                                                         shift_cm=sh * depth / f * 100, depth=depth))
        vis = Fr["img"].copy(); cv2.drawContours(vis, [cp.reshape(-1, 1, 2)], -1, (0, 0, 255), 1)
        cv2.imwrite(f"{HERE}/ov/p{ep:02d}_{Fr['fi']:04d}.jpg", vis)
    rr = [r for r in rows if r["ep"] == ep]
    print("    per-frame residual shift (cm):", " ".join(f"{r['shift_cm']:.1f}" for r in rr), flush=True)
json.dump(dict(frames=rows, episodes=EPOUT), open(f"{HERE}/a9_overlay_check.json", "w"), indent=1, default=float)
s_ = np.array([r["shift_cm"] for r in rows]); c0 = np.array([r["cham0"] for r in rows])
dz = np.array([v["o"][2] for v in EPOUT.values()]) * 100
print(f"n={len(rows)} frames / {len(EPOUT)} eps: residual best-shift median {np.median(s_):.2f} cm p90 {np.percentile(s_,90):.2f}; "
      f"chamfer median {np.median(c0):.2f} px; per-episode dz median {np.median(dz):+.1f} cm sd {dz.std():.1f}")
