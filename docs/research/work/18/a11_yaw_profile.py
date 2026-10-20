"""DIG 18 A11 yaw profile (from A10): translation re-fitted at fixed yaw values; parabola -> best yaw.
DIG 18 A10 (from A9): per-episode 4-DoF fit (dx, dy, dz, dpsi) -> independent yaw check per public episode.
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
YAWS = np.arange(-2.0, 5.01, 1.0)
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
    A9 = json.load(open(f"{HERE}/a9_overlay_check.json"))["episodes"][str(ep)]["o"]
    prof = []
    for yv in YAWS:
        f3 = lambda z: cost(np.r_[z, yv]); x0 = np.array(A9, float)
        r_ = minimize(f3, x0, method="Nelder-Mead", options=dict(initial_simplex=np.vstack([x0] + [x0 + np.eye(3)[k] * 0.008 for k in range(3)]),
                                                                xatol=5e-4, fatol=1e-3, maxiter=150))
        prof.append((yv, float(r_.fun), r_.x.tolist()))
    c = np.array([p[1] for p in prof]); k = int(np.argmin(c))
    lo, hi = max(0, k - 2), min(len(YAWS), k + 3); pf = np.polyfit(YAWS[lo:hi], c[lo:hi], 2)
    yb = float(-pf[1] / (2 * pf[0])) if pf[0] > 0 else float(YAWS[k])
    EPOUT[ep] = dict(profile=[(p[0], p[1]) for p in prof], best_grid=float(YAWS[k]), best_parab=yb, curv=float(pf[0]), n=len(F))
    print(f"ep {ep:2d}: n={len(F)} profile " + " ".join(f"{p[0]:+.0f}:{p[1]:.3f}" for p in prof) + f" | best grid {YAWS[k]:+.1f} parab {yb:+.2f} curv {pf[0]:.4f}", flush=True)
json.dump(dict(episodes=EPOUT), open(f"{HERE}/a11_yaw_profile.json", "w"), indent=1, default=float)
yb = np.array([v["best_parab"] for v in EPOUT.values()])
print(f"best yaw (parabola) per episode: median {np.median(yb):+.2f} mean {yb.mean():+.2f} sd {yb.std():.2f} n={len(yb)}")
