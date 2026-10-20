"""DIG 18 A5: map-free arbiter for gravity. Per frame, triangulate SIFT matches c<->b on the table region with the
factory c->b extrinsic and fit the table plane in the cam_c frame (RANSAC). Compare its normal with:
  (1) the SfM map's table normal brought into that frame's cam_c (tests map bending / camera-vs-plane angles);
  (2) for the GT-fitted reference frames, mocap +z from the s25 fit (cam_a) taken through the calibrated a->b and c->b
      extrinsics (tests the fits' pitch/roll; mocap z = table normal to 0.4 deg, a4).
usage: python a5_stereo_table.py <model dir> <a3 json>"""
import sys, os, json, glob, numpy as np, cv2, pycolmap
from scipy.spatial.transform import Rotation as Rot
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
from a1_extract import NEW
ROOT = "/Users/aebatirel/Documents/Code/v2d-research"
CAL = json.load(open(f"{ROOT}/data/track_3/public/meta/camera_calibration.json"))
EGO = [s for s in CAL["stereo_pairs"] if s["camera"] == "ego"][0]
T_bc = np.array(EGO["left_to_right"], float); R_bc, t_bc = T_bc[:3, :3], T_bc[:3, 3]
T_ba = np.array(CAL["cameras"]["ego_cam_a"]["extrinsics_to_stereo_left"], float); R_ba = T_ba[:3, :3]
FITS = json.load(open(f"{ROOT}/work/11/s25_refine_native.json"))
rec = pycolmap.Reconstruction(sys.argv[1]); A3 = json.load(open(sys.argv[2]))
nT = np.array(A3["floor"]["table_n"])
w, h, f = NEW["c"]; K = np.array([[f, 0, (w - 1) / 2], [0, f, (h - 1) / 2], [0, 0, 1.0]])
P1 = K @ np.c_[np.eye(3), np.zeros(3)]; P2 = K @ np.c_[R_bc, t_bc]
sift = cv2.SIFT_create(8000); bf = cv2.BFMatcher()


def Rwc11(psi, th, ph):
    p, t = np.radians(psi), np.radians(th)
    fw = np.array([np.cos(t) * np.cos(p), np.cos(t) * np.sin(p), -np.sin(t)])
    r = np.cross(fw, [0, 0, 1.0]); r /= np.linalg.norm(r); d = np.cross(fw, r)
    Rr = Rot.from_rotvec(fw * np.radians(ph)).as_matrix()
    return np.column_stack([Rr @ r, Rr @ d, fw])


R1, R2, PR1, PR2, Q, _, _ = cv2.stereoRectify(K, np.zeros(5), K, np.zeros(5), (w, h), R_bc.copy(), t_bc.reshape(3, 1).copy(), alpha=0)
MX1 = cv2.initUndistortRectifyMap(K, np.zeros(5), R1, PR1, (w, h), cv2.CV_32FC1)
MX2 = cv2.initUndistortRectifyMap(K, np.zeros(5), R2, PR2, (w, h), cv2.CV_32FC1)
SGBM = cv2.StereoSGBM_create(minDisparity=0, numDisparities=128, blockSize=7, P1=8 * 49, P2=32 * 49, uniquenessRatio=10,
                             speckleWindowSize=100, speckleRange=2, mode=cv2.STEREO_SGBM_MODE_SGBM_3WAY)


def table_plane(name):
    """dense SGBM on the rectified c|b pair; plane RANSAC on the lower-centre region; returns normal in the cam_c frame"""
    gc = cv2.imread(f"{HERE}/imgs/c/{name}", 0); gb = cv2.imread(f"{HERE}/imgs/b/{name}", 0)
    rc = cv2.remap(gc, *MX1, cv2.INTER_LINEAR); rb = cv2.remap(gb, *MX2, cv2.INTER_LINEAR)
    disp = SGBM.compute(rc, rb).astype(np.float32) / 16.0
    X = cv2.reprojectImageTo3D(disp, Q)  # rectified-left frame
    m = np.zeros((h, w), bool); m[int(0.5 * h):, int(0.2 * w):int(0.8 * w)] = True
    ok = m & (disp > 5) & np.isfinite(X).all(2)
    Xr = X[ok]; Xr = Xr[(Xr[:, 2] > 0.25) & (np.linalg.norm(Xr, axis=1) < 1.2)]
    if len(Xr) < 500: return None
    Xc = Xr @ R1  # rectified -> cam_c: X_c = R1^T X_rect
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
    for _ in range(3):
        F = Xc[inl]; c = F.mean(0); n = np.linalg.svd(F - c, full_matrices=False)[2][2]; n = n if n[1] < 0 else -n
        inl = np.abs((Xc - c) @ n) < 0.004
    F = Xc[inl]; c = F.mean(0); U, S, Vt = np.linalg.svd(F - c, full_matrices=False); n = Vt[2]; n = n if n[1] < 0 else -n
    rms = float(np.sqrt(np.mean(((F - c) @ n) ** 2)))
    # half-split stability as the uncertainty proxy (near vs far halves of the inliers)
    dd = F @ np.array([0, 0, 1.0]); md = np.median(dd); ns = []
    for sel in (dd < md, dd >= md):
        G = F[sel]; cg = G.mean(0); ng = np.linalg.svd(G - cg, full_matrices=False)[2][2]; ns.append(ng if ng[1] < 0 else -ng)
    sig = float(np.degrees(np.arccos(np.clip(ns[0] @ ns[1], -1, 1))) / 2)
    return dict(n=n, d=float(-c @ n), ninl=int(inl.sum()), nX=len(Xc), rms=rms, sig_deg=sig)


def decomp(n_meas, n_ref):
    """angle and its components: about camera x (pitch-like) and about camera z (roll-like), degrees"""
    a = np.degrees(np.arccos(np.clip(n_meas @ n_ref, -1, 1)))
    px = np.degrees(np.arctan2(n_meas[2], -n_meas[1]) - np.arctan2(n_ref[2], -n_ref[1]))
    rz = np.degrees(np.arctan2(n_meas[0], -n_meas[1]) - np.arctan2(n_ref[0], -n_ref[1]))
    return a, px, rz


rows = []; byname = {im.name: im for im in rec.images.values()}
names = sorted(os.path.basename(p) for p in glob.glob(f"{HERE}/imgs/c/*.jpg"))
for nm in names:
    if f"c/{nm}" not in byname: continue
    r = table_plane(nm)
    if r is None: rows.append(dict(name=nm, ok=False)); continue
    Rcw = byname[f"c/{nm}"].cam_from_world().rotation.matrix()
    n_map = Rcw @ nT
    a, px, rz = decomp(r["n"], n_map)
    row = dict(name=nm, ok=True, ninl=r["ninl"], nX=r["nX"], rms_mm=r["rms"] * 1000, sig_deg=r["sig_deg"], d_table=r["d"],
               map_ang=a, map_px=px, map_rz=rz, n=r["n"].tolist())
    ep = int(nm[1:3]); fr = int(nm[4:8])
    if nm.startswith("p") and fr == 0 and str(ep) in FITS:
        fz = FITS[str(ep)]; up_a = Rwc11(fz["psi"], fz["th"], fz["ph"]).T @ np.array([0, 0, 1.0])
        up_c = R_bc.T @ (R_ba @ up_a)
        a2, px2, rz2 = decomp(r["n"], up_c); row.update(fit_ang=a2, fit_px=px2, fit_rz=rz2)
    rows.append(row)
    print(f"{nm} inl {r['ninl']:4d}/{r['nX']:4d} rms {r['rms']*1000:4.1f} mm sig {r['sig_deg']:.2f} | vs map {a:5.2f} (px {px:+5.2f} rz {rz:+5.2f})"
          + (f" | vs fit {row['fit_ang']:5.2f} (px {row['fit_px']:+5.2f} rz {row['fit_rz']:+5.2f})" if "fit_ang" in row else ""), flush=True)
ok = [r for r in rows if r["ok"] and r["ninl"] >= 3000 and r["sig_deg"] < 1.0]
P = np.array([[r["map_ang"], r["map_px"], r["map_rz"]] for r in ok])
print(f"\nframes with a good stereo table plane: {len(ok)} of {len(rows)}")
print(f"stereo vs MAP table normal: angle median {np.median(P[:,0]):.2f}; about cam-x (pitch) median {np.median(P[:,1]):+.2f} sd {P[:,1].std():.2f};"
      f" about cam-z (roll) median {np.median(P[:,2]):+.2f} sd {P[:,2].std():.2f}")
for split in "pe":
    Q = np.array([[r["map_px"], r["map_rz"]] for r in ok if r["name"][0] == split])
    if len(Q): print(f"  split {split}: n={len(Q)} pitch {np.median(Q[:,0]):+.2f} roll {np.median(Q[:,1]):+.2f}")
F = [r for r in rows if r.get("fit_ang") is not None]
for r in F: print(f"  ref {r['name']}: stereo vs FIT angle {r['fit_ang']:.2f} (px {r['fit_px']:+.2f} rz {r['fit_rz']:+.2f}); vs MAP {r['map_ang']:.2f} (px {r['map_px']:+.2f} rz {r['map_rz']:+.2f})")
json.dump(rows, open(f"{HERE}/a5_stereo_table.json", "w"), indent=1, default=float)
