"""DIG 18 C4: GT-free gravity/height check on eval clips. At every 50th frame: dense SGBM b/c table plane (as a5) in
the cam_c frame -> mocap via the frame's map relocalisation (c1 rig pose) and the a13 registration. Reports the angle
between the table normal and mocap +z, and the implied table height (GT table top is 0.6012 m in every public ep).
These frames (t > 0) were NOT used to build the map or the registration. Reads no GT.
usage: python c4_gravity.py <prefix s5> <out json> [step=50] [eps...]"""
import sys, os, json, numpy as np, cv2
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
from a1_extract import NEW, maps, clip
ROOT = "/Users/aebatirel/Documents/Code/v2d-research"
CAL = json.load(open(f"{ROOT}/data/track_3/public/meta/camera_calibration.json"))
T_bc = np.array([s for s in CAL["stereo_pairs"] if s["camera"] == "ego"][0]["left_to_right"], float); R_bc, t_bc = T_bc[:3, :3], T_bc[:3, 3]
REG = json.load(open(f"{HERE}/a13_registration_refined.json")); Rm = np.array(REG["R_mocap_from_map"]); tz = REG["t_z"]
PFX, OUT = sys.argv[1], sys.argv[2]; STEP = int(sys.argv[3]) if len(sys.argv) > 3 else 50
EPS = [int(e) for e in sys.argv[4:]] or [1, 3, 5, 6, 8, 10, 14, 15, 16, 19, 20, 25, 28, 30, 32, 33, 35, 36, 37, 38]
w, h, f = NEW["c"]; K = np.array([[f, 0, (w - 1) / 2], [0, f, (h - 1) / 2], [0, 0, 1.0]])
R1, R2, PR1, PR2, Q, _, _ = cv2.stereoRectify(K, np.zeros(5), K, np.zeros(5), (w, h), R_bc.copy(), t_bc.reshape(3, 1).copy(), alpha=0)
MX1 = cv2.initUndistortRectifyMap(K, np.zeros(5), R1, PR1, (w, h), cv2.CV_32FC1)
MX2 = cv2.initUndistortRectifyMap(K, np.zeros(5), R2, PR2, (w, h), cv2.CV_32FC1)
SGBM = cv2.StereoSGBM_create(minDisparity=0, numDisparities=128, blockSize=7, P1=8 * 49, P2=32 * 49, uniquenessRatio=10,
                             speckleWindowSize=100, speckleRange=2, mode=cv2.STEREO_SGBM_MODE_SGBM_3WAY)
MP = {c: maps(c)[0] for c in "bc"}


def table_plane(gc, gb):
    rc = cv2.remap(gc, *MX1, cv2.INTER_LINEAR); rb = cv2.remap(gb, *MX2, cv2.INTER_LINEAR)
    disp = SGBM.compute(rc, rb).astype(np.float32) / 16.0
    X = cv2.reprojectImageTo3D(disp, Q)
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
    for _ in range(3):
        F = Xc[inl]; c = F.mean(0); n = np.linalg.svd(F - c, full_matrices=False)[2][2]; n = n if n[1] < 0 else -n
        inl = np.abs((Xc - c) @ n) < 0.004
    F = Xc[inl]; c = F.mean(0); n = np.linalg.svd(F - c, full_matrices=False)[2][2]; n = n if n[1] < 0 else -n
    return dict(n=n, d=float(-c @ n), ninl=int(inl.sum()), rms=float(np.sqrt(np.mean(((F - c) @ n) ** 2))))


res = {}
for ep in EPS:
    R = {r["frame"]: np.array(r["c_from_world"]) for r in json.load(open(f"{HERE}/c1/{PFX}_e{ep}.json"))["frames"] if r.get("inl_bc", 0) >= 30}
    caps = {c: cv2.VideoCapture(clip("evaluation", ep, c)) for c in "bc"}; rows = []; t = 0
    while True:
        ok = [caps[c].grab() for c in "bc"]
        if not all(ok): break
        if t % STEP == 0 and t in R:
            g = {}
            for c in "bc":
                _, im = caps[c].retrieve(); im = cv2.cvtColor(im, cv2.COLOR_BGR2GRAY) if im.ndim == 3 else im
                g[c] = cv2.remap(im, MP[c][0], MP[c][1], cv2.INTER_LINEAR)
            p = table_plane(g["c"], g["b"])
            if p is not None and p["ninl"] > 3000:
                Rcw = R[t][:3, :3]; tcw = R[t][:3, 3]
                n_m = Rm @ (Rcw.T @ p["n"]); Cm = Rm @ (-Rcw.T @ tcw) + np.array([0, 0, tz])
                tilt = float(np.degrees(np.arccos(np.clip(n_m[2], -1, 1))))
                ztab = float(Cm[2] - p["d"] / max(n_m[2], 1e-6))
                rows.append(dict(t=t, tilt=tilt, nx=float(n_m[0]), ny=float(n_m[1]), ztab=ztab, ninl=p["ninl"], rms=p["rms"]))
        t += 1
    tl = np.array([r["tilt"] for r in rows]); zt = np.array([r["ztab"] for r in rows])
    res[ep] = dict(rows=rows, n=len(rows), tilt_med=float(np.median(tl)) if len(tl) else None, tilt_max=float(tl.max()) if len(tl) else None,
                   ztab_med=float(np.median(zt)) if len(zt) else None, ztab_sd=float(zt.std()) if len(zt) else None)
    print(f"e{ep:2d}: n={len(rows)} tilt med {res[ep]['tilt_med']:.2f} max {res[ep]['tilt_max']:.2f} deg | table z med {res[ep]['ztab_med']:.4f} sd {res[ep]['ztab_sd']*1000:.1f} mm"
          f" | mean n_xy ({np.mean([r['nx'] for r in rows]):+.4f}, {np.mean([r['ny'] for r in rows]):+.4f})", flush=True)
json.dump(res, open(OUT, "w"), indent=1)
allt = np.concatenate([[r["tilt"] for r in v["rows"]] for v in res.values()]); allz = np.concatenate([[r["ztab"] for r in v["rows"]] for v in res.values()])
print(f"ALL: n={len(allt)} tilt median {np.median(allt):.2f} p90 {np.percentile(allt, 90):.2f} max {allt.max():.2f} deg; table z median {np.median(allz):.4f} (GT 0.6012) p10-p90 {np.percentile(allz, 10):.4f}-{np.percentile(allz, 90):.4f}")
