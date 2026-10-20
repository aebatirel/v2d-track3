"""DIG 18 B15 (copy of A6 + image-position regression of the disparity residual): a b/c roll error eps predicts
d_stereo - d_map = eps * (v - v0) (row gradient), which would tilt every stereo table plane. Was A6: compare per-frame b/c SGBM stereo depth with SfM map depth at map points observed in cam_c images.
A disparity offset delta (e.g. factory c->b yaw error) predicts ratio r = |X_stereo|/|X_map| ~ 1 - delta*Z/(f*B);
a pure scale error predicts constant r. usage: python a6_depth_ratio.py <model dir> [every]"""
import sys, os, json, glob, numpy as np, cv2, pycolmap
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
from a1_extract import NEW
ROOT = "/Users/aebatirel/Documents/Code/v2d-research"
CAL = json.load(open(f"{ROOT}/data/track_3/public/meta/camera_calibration.json"))
EGO = [s for s in CAL["stereo_pairs"] if s["camera"] == "ego"][0]
T_bc = np.array(EGO["left_to_right"], float); R_bc, t_bc = T_bc[:3, :3].copy(), T_bc[:3, 3].reshape(3, 1).copy()
rec = pycolmap.Reconstruction(sys.argv[1]); EVERY = int(sys.argv[2]) if len(sys.argv) > 2 else 3
w, h, f = NEW["c"]; K = np.array([[f, 0, (w - 1) / 2], [0, f, (h - 1) / 2], [0, 0, 1.0]])
R1, R2, PR1, PR2, Q, _, _ = cv2.stereoRectify(K, np.zeros(5), K, np.zeros(5), (w, h), R_bc, t_bc, alpha=0)
MX1 = cv2.initUndistortRectifyMap(K, np.zeros(5), R1, PR1, (w, h), cv2.CV_32FC1)
MX2 = cv2.initUndistortRectifyMap(K, np.zeros(5), R2, PR2, (w, h), cv2.CV_32FC1)
fB = -PR2[0, 3]; print("rectified f*B (px*m):", round(fB, 3), "f_rect", round(PR1[0, 0], 2))
SGBM = cv2.StereoSGBM_create(minDisparity=0, numDisparities=128, blockSize=7, P1=8 * 49, P2=32 * 49, uniquenessRatio=10,
                             speckleWindowSize=100, speckleRange=2, mode=cv2.STEREO_SGBM_MODE_SGBM_3WAY)
byname = {im.name: im for im in rec.images.values()}
names = sorted(os.path.basename(p) for p in glob.glob(f"{HERE}/imgs/c/*.jpg"))[::EVERY]
Z, Rr, D, Dm, V, U, S = [], [], [], [], [], [], []
for nm in names:
    im = byname.get(f"c/{nm}")
    if im is None: continue
    gc = cv2.imread(f"{HERE}/imgs/c/{nm}", 0); gb = cv2.imread(f"{HERE}/imgs/b/{nm}", 0)
    disp = SGBM.compute(cv2.remap(gc, *MX1, cv2.INTER_LINEAR), cv2.remap(gb, *MX2, cv2.INTER_LINEAR)).astype(np.float32) / 16
    T = im.cam_from_world(); Rcw = T.rotation.matrix(); tcw = np.asarray(T.translation)
    for p2 in im.points2D:
        if p2.point3D_id == pycolmap.INVALID_POINT3D_ID or not rec.exists_point3D(p2.point3D_id): continue
        Xm = Rcw @ rec.point3D(p2.point3D_id).xyz + tcw  # map point in cam_c
        zr = R1 @ Xm  # in rectified-left frame
        if zr[2] <= 0.2: continue
        u = PR1[0, 0] * zr[0] / zr[2] + PR1[0, 2]; v = PR1[1, 1] * zr[1] / zr[2] + PR1[1, 2]
        ui, vi = int(round(u)), int(round(v))
        if not (2 <= ui < w - 2 and 2 <= vi < h - 2): continue
        d = disp[vi, ui]
        if d <= 2: continue
        dm = fB / zr[2]  # disparity the map predicts at its own depth
        Z.append(zr[2]); D.append(d); Dm.append(dm); V.append(v); U.append(u); S.append(nm[:3])
Z, D, Dm, V, U, S = map(np.array, (Z, D, Dm, V, U, S))
ok = (Z < 3.0) & (np.abs(D - Dm) < 8)
Z, D, Dm, V, U, S = Z[ok], D[ok], Dm[ok], V[ok], U[ok], S[ok]
print(f"n={len(Z)} points from {len(names)} c images")
# model: d_stereo = s*d_map + delta  (s: inverse scale ratio map/stereo, delta: disparity offset)
A = np.c_[Dm, np.ones_like(Dm)]
for it in range(3):
    sol, *_ = np.linalg.lstsq(A, D, rcond=None); r = D - A @ sol; keep = np.abs(r) < 3 * np.median(np.abs(r)) * 1.4826
    A, D, Dm, Z, V, U, S = A[keep], D[keep], Dm[keep], Z[keep], V[keep], U[keep], S[keep]
sol, *_ = np.linalg.lstsq(A, D, rcond=None); r = D - A @ sol
print(f"fit d_stereo = {sol[0]:.4f} * d_map + {sol[1]:+.3f} px ; resid MAD {np.median(np.abs(r))*1.4826:.3f} px (n={len(D)})")
for lo, hi in [(0.3, 0.6), (0.6, 0.9), (0.9, 1.3), (1.3, 2.0), (2.0, 3.0)]:
    s = (Z >= lo) & (Z < hi)
    if s.sum() > 20:
        print(f"  Z {lo:.1f}-{hi:.1f} m: n={s.sum():6d} median (d_st - d_map) {np.median(D[s]-Dm[s]):+.3f} px; median Z_st/Z_map {np.median(Dm[s]/D[s]):.4f}")
cx, cy = PR1[0, 2], PR1[1, 2]
def grad(m):
    B = np.c_[Dm[m], np.ones(m.sum()), U[m] - cx, V[m] - cy]; g, *_ = np.linalg.lstsq(B, D[m], rcond=None)
    rr = D[m] - B @ g; se = np.sqrt(np.diag(np.linalg.pinv(B.T @ B)) * np.median(np.abs(rr)) ** 2 * 2.198)
    return g, se
g, se = grad(np.ones(len(D), bool))
print(f"ALL: d_st = {g[0]:.4f} d_map {g[1]:+.3f} + {g[2]*1000:+.3f}e-3 (u-cx) + {g[3]*1000:+.3f}e-3 (v-cy) px; se col {se[2]*1000:.3f}e-3 row {se[3]*1000:.3f}e-3"
      f" -> roll-equivalent {np.degrees(g[3]):+.3f} deg; over 300 rows {g[3]*300:+.2f} px")
for ss in sorted(set(S)):
    m = S == ss
    if m.sum() < 500: continue
    g, se = grad(m); print(f"  {ss}: n {m.sum():6d} row grad {g[3]*1000:+.3f}e-3 (se {se[3]*1000:.3f}) col grad {g[2]*1000:+.3f}e-3 offset {g[1]:+.3f}")
json.dump(dict(s=float(sol[0]), delta=float(sol[1]), fB=float(fB), n=int(len(D))), open(f"{HERE}/b11/b15_disp_rowgrad.json", "w"), indent=1)
