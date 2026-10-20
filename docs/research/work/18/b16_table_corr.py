"""DIG 18 B16: does the b/c stereo disparity bias found in B15 (image-position-dependent residual vs the map) tilt the
dense stereo table plane that defines the map's gravity (A5/A8)? For map c/b image pairs (every Nth): SGBM table plane
(C4 logic) from raw disparity and from disparity corrected by the B15 model d_corr = (d - g1 - g2 (u-cx) - g3 (v-cy)) / g0;
both normals go to mocap through the run1 map pose and a13. Reads no GT.
usage: python b16_table_corr.py <model dir> <b15 json> [every]"""
import sys, os, json, glob, numpy as np, cv2, pycolmap
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
from a1_extract import NEW
ROOT = "/Users/aebatirel/Documents/Code/v2d-research"
CAL = json.load(open(f"{ROOT}/data/track_3/public/meta/camera_calibration.json"))
T_bc = np.array([s for s in CAL["stereo_pairs"] if s["camera"] == "ego"][0]["left_to_right"], float)
R_bc, t_bc = T_bc[:3, :3].copy(), T_bc[:3, 3].reshape(3, 1).copy()
REG = json.load(open(f"{HERE}/a13_registration_refined.json")); Rm = np.array(REG["R_mocap_from_map"])
rec = pycolmap.Reconstruction(sys.argv[1]); G = json.load(open(sys.argv[2])); EVERY = int(sys.argv[3]) if len(sys.argv) > 3 else 6
g0, g1, g2, g3 = G["g"]
w, h, f = NEW["c"]; K = np.array([[f, 0, (w - 1) / 2], [0, f, (h - 1) / 2], [0, 0, 1.0]])
R1, R2, PR1, PR2, Q, _, _ = cv2.stereoRectify(K, np.zeros(5), K, np.zeros(5), (w, h), R_bc, t_bc, alpha=0)
MX1 = cv2.initUndistortRectifyMap(K, np.zeros(5), R1, PR1, (w, h), cv2.CV_32FC1)
MX2 = cv2.initUndistortRectifyMap(K, np.zeros(5), R2, PR2, (w, h), cv2.CV_32FC1)
SGBM = cv2.StereoSGBM_create(minDisparity=0, numDisparities=128, blockSize=7, P1=8 * 49, P2=32 * 49, uniquenessRatio=10,
                             speckleWindowSize=100, speckleRange=2, mode=cv2.STEREO_SGBM_MODE_SGBM_3WAY)
cx, cy = PR1[0, 2], PR1[1, 2]; UU, VV = np.meshgrid(np.arange(w, dtype=np.float32), np.arange(h, dtype=np.float32))


def plane(disp):
    X = cv2.reprojectImageTo3D(disp.astype(np.float32), Q)
    m = np.zeros((h, w), bool); m[int(0.5 * h):, int(0.2 * w):int(0.8 * w)] = True
    ok = m & (disp > 5) & np.isfinite(X).all(2)
    Xr = X[ok]; Xr = Xr[(Xr[:, 2] > 0.25) & (np.linalg.norm(Xr, axis=1) < 1.2)]
    if len(Xr) < 500: return None
    Xc = Xr @ R1
    rng = np.random.default_rng(0); best = (0, None); sub = Xc[rng.choice(len(Xc), min(len(Xc), 20000), replace=False)]
    for _ in range(1500):
        i = rng.choice(len(sub), 3, replace=False); n = np.cross(sub[i[1]] - sub[i[0]], sub[i[2]] - sub[i[0]])
        if np.linalg.norm(n) < 1e-12: continue
        n /= np.linalg.norm(n); n = n if n[1] < 0 else -n
        if n[1] > -0.5: continue
        inl = np.abs((sub - sub[i[0]]) @ n) < 0.004
        if inl.sum() > best[0]: best = (inl.sum(), n, sub[i[0]])
    if best[1] is None: return None
    n, p0 = best[1], best[2]; inl = np.abs((Xc - p0) @ n) < 0.004
    for _ in range(4):
        F = Xc[inl]; c = F.mean(0); n = np.linalg.svd(F - c, full_matrices=False)[2][2]; n = n if n[1] < 0 else -n
        inl = np.abs((Xc - c) @ n) < 0.004
    return n, int(inl.sum())


byname = {im.name: im for im in rec.images.values()}
names = sorted(os.path.basename(p) for p in glob.glob(f"{HERE}/imgs/c/*.jpg"))[::EVERY]
rows = []
for nm in names:
    im = byname.get(f"c/{nm}")
    if im is None: continue
    gc = cv2.imread(f"{HERE}/imgs/c/{nm}", 0); gb = cv2.imread(f"{HERE}/imgs/b/{nm}", 0)
    d = SGBM.compute(cv2.remap(gc, *MX1, cv2.INTER_LINEAR), cv2.remap(gb, *MX2, cv2.INTER_LINEAR)).astype(np.float32) / 16
    dc = np.where(d > 0, (d - g1 - g2 * (UU - cx) - g3 * (VV - cy)) / g0, d)
    p0, p1 = plane(d), plane(dc)
    if p0 is None or p1 is None or min(p0[1], p1[1]) < 3000: continue
    Rcw = im.cam_from_world().rotation.matrix()
    n0 = Rm @ (Rcw.T @ p0[0]); n1 = Rm @ (Rcw.T @ p1[0]); n0 *= np.sign(n0[2]); n1 *= np.sign(n1[2])
    rows.append((nm, *np.degrees(n0[:2]), *np.degrees(n1[:2])))
    print(nm, "raw xy deg (%+.2f, %+.2f) corrected (%+.2f, %+.2f)" % tuple(rows[-1][1:]), flush=True)
A = np.array([r[1:] for r in rows])
print(f"n={len(A)}: mean raw ({A[:, 0].mean():+.2f}, {A[:, 1].mean():+.2f}) deg; corrected ({A[:, 2].mean():+.2f}, {A[:, 3].mean():+.2f}) deg;"
      f" shift ({(A[:, 2] - A[:, 0]).mean():+.2f}, {(A[:, 3] - A[:, 1]).mean():+.2f}) sd ({(A[:, 2] - A[:, 0]).std():.2f}, {(A[:, 3] - A[:, 1]).std():.2f})")
json.dump(dict(rows=rows), open(f"{HERE}/b11/b16_table_corr.json", "w"))
