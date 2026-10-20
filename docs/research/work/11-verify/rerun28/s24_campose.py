"""Stage C: camera pose of public ego_cam_a frame 0 in the MOCAP world, by aligning GT-posed scan silhouettes
(point splats) with an object colour mask (local IoU). Analysis only: uses public GT; nothing here is an inference
step. Output: camera heading psi (deg, yaw of the optical axis in mocap xy), pitch th (deg down), roll ph, centre C.
usage: python s24_campose.py <variant native|flipped> ep [ep ...]"""
import sys, json, os, numpy as np, cv2, trimesh
from scipy.optimize import minimize
from scipy.spatial.transform import Rotation as Rot
import c11
from s23_mask import masks
cal = json.load(open(f"{c11.PUB}/meta/camera_calibration.json"))["cameras"]["ego_cam_a"]
W0, H0 = 2028, 1520
VAR = sys.argv[1]
fx, fy, cx, cy = cal["fx"], cal["fy"], cal["cx"], cal["cy"]
dist = np.array(cal["distortion_coefficients"], float)
if VAR == "flipped":
    cx, cy = W0 - 1 - cx, H0 - 1 - cy; dist = dist.copy(); dist[2:4] *= -1; dist[8:14] *= -1

def Kof(s): return np.array([[fx * s, 0, (cx + 0.5) * s - 0.5], [0, fy * s, (cy + 0.5) * s - 0.5], [0, 0, 1.0]])

def Rwc(psi, th, ph):
    p, t = np.radians(psi), np.radians(th)
    f = np.array([np.cos(t) * np.cos(p), np.cos(t) * np.sin(p), -np.sin(t)])
    r = np.cross(f, [0, 0, 1.0]); r /= np.linalg.norm(r); d = np.cross(f, r)
    Rr = Rot.from_rotvec(f * np.radians(ph)).as_matrix()
    return np.column_stack([Rr @ r, Rr @ d, f])

def project(P, x, s):
    R = Rwc(*x[:3]); Xc = (P - x[3:6]) @ R
    ok = (Xc[:, 2] > 0.05) & (np.abs(Xc[:, 0] / np.maximum(Xc[:, 2], 1e-6)) < 1.6) & (np.abs(Xc[:, 1] / np.maximum(Xc[:, 2], 1e-6)) < 1.3)
    if ok.sum() < 10: return None
    uv, _ = cv2.projectPoints(Xc[ok].reshape(-1, 1, 3), np.zeros(3), np.zeros(3), Kof(s), dist)
    return uv.reshape(-1, 2)

OUTFRAC = {}
def render(P, x, s, shape):
    m = np.zeros(shape, np.uint8); uv = project(P, x, s); OUTFRAC["f"] = 1.0
    if uv is None: return m
    u = np.round(uv[:, 0]).astype(int); v = np.round(uv[:, 1]).astype(int)
    k = (u >= 0) & (u < shape[1]) & (v >= 0) & (v < shape[0]); m[v[k], u[k]] = 1
    OUTFRAC["f"] = 1.0 - k.sum() / len(P)  # share of model points behind/outside the image
    m = cv2.dilate(m, np.ones((3, 3), np.uint8)); return cv2.morphologyEx(m, cv2.MORPH_CLOSE, np.ones((5, 5), np.uint8))

def score(P, x, s, fg, dc, margin, lab):
    """IoU between the rendered silhouette and the fg components it touches (dark pixels = don't care)."""
    r = render(P, x, s, fg.shape)
    if r.sum() < 20: return 0.0
    hit = np.unique(lab[(cv2.dilate(r, np.ones((3, 3), np.uint8)) > 0) & fg]); hit = hit[hit > 0]
    ff = np.isin(lab, hit) & ~dc; rr = (r > 0) & ~dc
    fo = OUTFRAC["f"]; extra = r.sum() * fo / max(1 - fo, 1e-3)  # off-image model area counts as unmatched render
    return (rr & ff).sum() / max((rr | ff).sum() + extra, 1)

def fit(ep, npts=6000, seed=0):
    e = c11.load_episode(ep); img0 = cv2.imread(f"cfr/pub{ep}_f0.png")
    rng = np.random.default_rng(seed); Ps = []
    for j, n in enumerate(e["names"]):
        m = c11.glb_mesh(n); p, _ = trimesh.sample.sample_surface(m, npts, seed=seed)
        Ps.append(p @ c11.R_of(e["pose"][0, j, 3:]).T + e["pose"][0, j, :3])
    P = np.vstack(Ps); c = P.mean(0)
    pyr = {}
    for s in (0.125, 0.25, 0.5):
        fg, dc = masks(img0, s)[1:]; pyr[s] = (fg, dc, cv2.connectedComponents(fg.astype(np.uint8))[1])
    fg, dc, lab = pyr[0.125]; best = []
    for psi in range(140, 221, 5):
        for th in range(25, 66, 5):
            for dx in (0.2, 0.35, 0.5, 0.65, 0.8):
                for dy in (-0.15, -0.075, 0, 0.075, 0.15):
                    for dz in (0.35, 0.5, 0.65, 0.8, 0.95):
                        x = np.array([psi, th, 0, c[0] + dx, c[1] + dy, c[2] + dz], float)
                        best.append((score(P, x, 0.125, fg, dc, 9, lab), x))
    best.sort(key=lambda t: -t[0]); res = []
    for sc0, x0 in best[:6]:
        x = x0
        for s, mg in ((0.25, 15), (0.5, 25)):
            fg, dc, lab = pyr[s]; step = np.array([3, 3, 3, 0.03, 0.03, 0.03]) * (1 if s == 0.25 else 0.4)
            sim = np.vstack([x] + [x + np.eye(6)[i] * step[i] for i in range(6)])
            o = minimize(lambda z: -score(P, z, s, fg, dc, mg, lab), x, method="Nelder-Mead",
                         options=dict(initial_simplex=sim, xatol=1e-3, fatol=1e-5, maxiter=1500, maxfev=1500))
            x = o.x
        res.append((-o.fun, x, sc0))
    res.sort(key=lambda t: -t[0])
    iou, x, sc0 = res[0]
    # overlay for visual check
    fg, dc, lab = pyr[0.5]; r = render(P, x, 0.5, fg.shape); vis = cv2.resize(img0, (fg.shape[1], fg.shape[0]))
    cnts, _ = cv2.findContours(r, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE); cv2.drawContours(vis, cnts, -1, (0, 0, 255), 2)
    cv2.imwrite(f"cfr/fit_{VAR}_{ep}.png", vis)
    alt = [dict(iou=float(a), psi=float(b[0]), th=float(b[1]), ph=float(b[2])) for a, b, _ in res[1:4]]
    return dict(ep=ep, iou=float(iou), psi=float(x[0]), th=float(x[1]), ph=float(x[2]), C=x[3:].tolist(),
                C_rel_obj=(x[3:] - c).tolist(), grid_best=float(best[0][0]), alts=alt)

if __name__ == "__main__":
    fn = f"s24_campose_{VAR}.json"; out = json.load(open(fn)) if os.path.exists(fn) else {}
    for ep in map(int, sys.argv[2:]):
        r = fit(ep); out[str(ep)] = r; json.dump(out, open(fn, "w"), indent=1)
        print(f"ep {ep:2d} IoU {r['iou']:.3f} psi {r['psi']:7.2f} th {r['th']:6.2f} ph {r['ph']:6.2f} Crel {np.round(r['C_rel_obj'],3)} alts {[(round(a['iou'],3), round(a['psi'],1)) for a in r['alts']]}", flush=True)
