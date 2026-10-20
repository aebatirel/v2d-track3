"""DIG 18 stage A3: inspect the room SfM model, check its metric scale, find the floor plane, and register it to
the mocap world via the GT-silhouette frame-0 camera fits of note 11 (work/11/s25_refine_native.json; colour K as
given). Research only: public GT is used for registration/validation only; eval images are only localised in the map.
usage: python a3_register.py <model dir> [refs csv, default 12,13,21,0]"""
import sys, os, json, numpy as np
import pycolmap
from scipy.spatial.transform import Rotation as Rot

ROOT = "/Users/aebatirel/Documents/Code/v2d-research"
HERE = os.path.dirname(os.path.abspath(__file__))
MODEL = sys.argv[1]
REFS = [int(x) for x in (sys.argv[2] if len(sys.argv) > 2 else "12,13,21,0").split(",")]
FITS = json.load(open(f"{ROOT}/work/11/s25_refine_native.json"))
W11 = {1: 184.2, 3: 179.5, 5: 179.3, 6: 178.5, 8: 183.8, 10: 180.4, 14: 181.9, 15: 180.8, 16: 182.8, 19: 179.4,
       20: 178.6, 25: 182.2, 28: 179.4, 30: 183.0, 32: 184.6, 33: 177.1, 35: 174.1, 36: 178.1, 37: 176.1, 38: 177.2}
CAL = json.load(open(f"{ROOT}/data/track_3/public/meta/camera_calibration.json"))["cameras"]
T_ba = np.array(CAL["ego_cam_a"]["extrinsics_to_stereo_left"], float)  # X_b = R X_a + t (a -> b, verified 15-verify)
OUT = {}


def Rwc11(psi, th, ph):  # note 11 convention: columns = camera right, down, forward in mocap
    p, t = np.radians(psi), np.radians(th)
    f = np.array([np.cos(t) * np.cos(p), np.cos(t) * np.sin(p), -np.sin(t)])
    r = np.cross(f, [0, 0, 1.0]); r /= np.linalg.norm(r); d = np.cross(f, r)
    Rr = Rot.from_rotvec(f * np.radians(ph)).as_matrix()
    return np.column_stack([Rr @ r, Rr @ d, f])


def hpr(Rwc):
    f = Rwc[:, 2]; r = Rwc[:, 0]
    psi = np.degrees(np.arctan2(f[1], f[0])); th = np.degrees(np.arcsin(-f[2]))
    r0 = np.cross(f, [0, 0, 1.0]); r0 /= np.linalg.norm(r0)
    ph = np.degrees(np.arctan2(np.dot(np.cross(r0, r), f), np.dot(r0, r))); return psi, th, ph


def rotang(R):
    return np.degrees(np.arccos(np.clip((np.trace(R) - 1) / 2, -1, 1)))


def wrap(a): return (np.asarray(a) + 180) % 360 - 180


rec = pycolmap.Reconstruction(MODEL)
print(rec.summary())
cams = {}
for iid, im in rec.images.items():
    if not im.has_pose: continue
    T = im.cam_from_world(); R = T.rotation.matrix(); t = np.asarray(T.translation)
    cams[im.name] = dict(Rwc=R.T, C=-R.T @ t, npts=im.num_points3D)
print("registered", len(cams), "of", rec.num_images())
# coverage per camera / split
cov = {}
for n in cams:
    c, rest = n.split("/"); key = (c, rest[0]); cov[key] = cov.get(key, 0) + 1
print("coverage (cam, split) ->", dict(sorted(cov.items())))
OUT["coverage"] = {f"{k[0]}_{k[1]}": v for k, v in cov.items()}
OUT["n_reg"] = len(cams); OUT["n_img"] = rec.num_images(); OUT["n_pts"] = rec.num_points3D()
OUT["mean_reproj_px"] = rec.compute_mean_reprojection_error(); OUT["mean_track"] = rec.compute_mean_track_length()

# ---- scale check 1: a vs b on the same frame index (calibrated a->b extrinsic: |t| = 3.74 cm)
ab = []
for n in cams:
    if not n.startswith("a/"): continue
    nb = "b/" + n[2:]
    if nb not in cams: continue
    A, B = cams[n], cams[nb]
    # relative pose of a in b's frame: X_b = R_ba X_a + t_ba
    R_ba = B["Rwc"].T @ A["Rwc"]; t_ba = B["Rwc"].T @ (A["C"] - B["C"])
    ab.append((n[2:], np.linalg.norm(A["C"] - B["C"]), rotang(R_ba @ T_ba[:3, :3].T), t_ba))
if ab:
    d = np.array([x[1] for x in ab]); r = np.array([x[2] for x in ab]); tt = np.array([x[3] for x in ab])
    print(f"a-b baseline: n={len(d)} median {np.median(d)*100:.2f} cm (calib {np.linalg.norm(T_ba[:3,3])*100:.2f}) "
          f"p10-p90 {np.percentile(d,10)*100:.2f}-{np.percentile(d,90)*100:.2f}; rot err vs calib median {np.median(r):.2f} deg "
          f"p90 {np.percentile(r,90):.2f}; t_ba median {np.round(np.median(tt,0)*100,2)} cm (calib {np.round(T_ba[:3,3]*100,2)})")
    OUT["ab_baseline_cm"] = dict(n=len(d), median=float(np.median(d) * 100), p10=float(np.percentile(d, 10) * 100),
                                 p90=float(np.percentile(d, 90) * 100), rot_err_med=float(np.median(r)),
                                 rot_err_p90=float(np.percentile(r, 90)), t_ba_med_cm=(np.median(tt, 0) * 100).tolist())
# b-c baseline (should be fixed by the rig)
bc = [np.linalg.norm(cams["b/" + n[2:]]["C"] - cams[n]["C"]) for n in cams if n.startswith("c/") and "b/" + n[2:] in cams]
if bc: print(f"b-c baseline (rig-fixed): median {np.median(bc)*100:.3f} cm n={len(bc)}")

# ---- planes: floor and table top. Up prior = average of the reference fits (pitch only to 2-5 deg), then RANSAC
P = np.array([p.xyz for p in rec.points3D.values()]); E = np.array([p.error for p in rec.points3D.values()])
TL = np.array([p.track.length() for p in rec.points3D.values()])
Cs = np.array([v["C"] for v in cams.values()]); Cm = np.median(Cs, 0)
def _avgR(Rs):
    q = np.array([Rot.from_matrix(R).as_quat() for R in Rs]); q *= np.sign(q @ q[0])[:, None]
    return Rot.from_quat(q.mean(0)).as_matrix()
_R0 = _avgR([Rwc11(FITS[str(e)]["psi"], FITS[str(e)]["th"], FITS[str(e)]["ph"]) @ cams[f"a/p{e:02d}_0000.jpg"]["Rwc"].T
             for e in REFS if f"a/p{e:02d}_0000.jpg" in cams])
up0 = _R0.T @ np.array([0, 0, 1.0])
good = (E < 2.0) & (TL >= 3); H = (P - Cm) @ up0
def ransac_plane(Q, prior, thr=0.01, maxang=15, it=4000, seed=0):
    rng = np.random.default_rng(seed); best = (0, None)
    for _ in range(it):
        i = rng.choice(len(Q), 3, replace=False); n = np.cross(Q[i[1]] - Q[i[0]], Q[i[2]] - Q[i[0]])
        if np.linalg.norm(n) < 1e-9: continue
        n /= np.linalg.norm(n)
        if abs(n @ prior) < np.cos(np.radians(maxang)): continue
        inl = np.abs((Q - Q[i[0]]) @ n) < thr
        if inl.sum() > best[0]: best = (inl.sum(), inl)
    inl = best[1]
    for _ in range(3):  # LSQ refit + re-threshold
        F = Q[inl]; c = F.mean(0); n = np.linalg.svd(F - c)[2][2]; n = n if n @ prior > 0 else -n
        inl = np.abs((Q - c) @ n) < thr
    F = Q[inl]; c = F.mean(0); n = np.linalg.svd(F - c)[2][2]; n = n if n @ prior > 0 else -n
    return n, c, inl, float(np.sqrt(np.mean(((F - c) @ n) ** 2)))
Qf = P[good & (H > -1.45) & (H < -0.85)]
nF, cF, inlF, rmsF = ransac_plane(Qf, up0)
# table top: points 0.40-0.65 m below the cameras within 0.9 m horizontally of the median camera
hz = (P - Cm) - np.outer((P - Cm) @ up0, up0)
Qt = P[good & (H > -0.65) & (H < -0.40) & (np.linalg.norm(hz, axis=1) < 0.9)]
nT, cT, inlT, rmsT = ransac_plane(Qt, up0, thr=0.006)
ang = lambda a, b: float(np.degrees(np.arccos(np.clip(a @ b, -1, 1))))
print(f"floor: {inlF.sum()} inl of {len(Qf)}; rms {rmsF*1000:.1f} mm | table: {inlT.sum()} inl of {len(Qt)}; rms {rmsT*1000:.1f} mm")
print(f"angles (deg): floor-table {ang(nF,nT):.2f}, floor-refavg {ang(nF,up0):.2f}, table-refavg {ang(nT,up0):.2f}")
h_cam = (Cs - cF) @ nF; h_tab = float((cT - cF) @ nF)
print(f"camera height above floor: median {np.median(h_cam):.3f} m p10-p90 {np.percentile(h_cam,10):.3f}-{np.percentile(h_cam,90):.3f}; "
      f"table top above floor {h_tab:.3f} m (mocap table top 0.6012)")
OUT["floor"] = dict(n_inl=int(inlF.sum()), rms_mm=rmsF * 1000, up_map=nF.tolist(), point=cF.tolist(),
                    cam_height_med=float(np.median(h_cam)), table_n=nT.tolist(), table_point=cT.tolist(),
                    table_rms_mm=rmsT * 1000, table_above_floor=h_tab, ang_floor_table=ang(nF, nT),
                    ang_floor_refavg=ang(nF, up0))

# ---- registration to mocap via the reference frame-0 cameras (cam_a)
refs = [e for e in REFS if f"a/p{e:02d}_0000.jpg" in cams and str(e) in FITS]
print("refs registered:", refs)
Rm = {}
for e in [int(k) for k in FITS]:
    n = f"a/p{e:02d}_0000.jpg"
    if n not in cams: continue
    f = FITS[str(e)]; Rm[e] = Rwc11(f["psi"], f["th"], f["ph"]) @ cams[n]["Rwc"].T  # mocap_from_map rotation
# (i) full rotation average over refs
def avgR(Rs):
    q = np.array([Rot.from_matrix(R).as_quat() for R in Rs]); q *= np.sign(q @ q[0])[:, None]
    return Rot.from_quat(q.mean(0)).as_matrix()
R_full = avgR([Rm[e] for e in refs])
print("ref rotation spread about the mean (deg):", {e: round(rotang(Rm[e] @ R_full.T), 2) for e in Rm})
# (ii) gravity from a map plane (map up -> mocap +z), yaw from refs' headings (median). Candidates: table top (GT: table
# level in mocap to 0.4 deg, a4_table_tilt_gt), floor, and the refs' own average (pitch poorly pinned).
def align_up(n):  # rotation taking n to +z (minimal)
    z = np.array([0, 0, 1.0]); v = np.cross(n, z); s = np.linalg.norm(v); c = n @ z
    if s < 1e-12: return np.eye(3)
    return Rot.from_rotvec(v / s * np.arctan2(s, c)).as_matrix()
UPS = dict(table=nT, floor=nF, refavg=R_full.T @ np.array([0, 0, 1.0]))
OUT["reg"] = {}
for gname, nup in UPS.items():
    G = align_up(nup); yaws = {}
    for e in Rm:
        n = f"a/p{e:02d}_0000.jpg"; yaws[e] = float(wrap(FITS[str(e)]["psi"] - hpr(G @ cams[n]["Rwc"])[0]))
    yaw0 = float(np.median([yaws[e] for e in refs]))
    R_grav = Rot.from_euler("z", yaw0, degrees=True).as_matrix() @ G
    loo = {e: float(wrap(yaws[e] - np.median([yaws[x] for x in refs if x != e]))) for e in refs}
    print(f"\n== gravity from {gname}: yaw offset per ref", {e: round(v, 2) for e, v in yaws.items()}, "median", round(yaw0, 2),
          "| LOO", {e: round(v, 2) for e, v in loo.items()}, "rms", round(float(np.sqrt(np.mean(np.square(list(loo.values()))))), 2))
    tz_tab = 0.6012 - float((R_grav @ cT)[2])  # table plane -> GT table top height
    zs = {e: FITS[str(e)]["C"][2] - (R_grav @ cams[f"a/p{e:02d}_0000.jpg"]["C"])[2] for e in Rm}
    tz_ref = float(np.median([zs[e] for e in refs]))
    dpr = []
    for e in Rm:
        n = f"a/p{e:02d}_0000.jpg"; h = hpr(R_grav @ cams[n]["Rwc"]); f = FITS[str(e)]
        zc = (R_grav @ cams[n]["C"])[2] + tz_tab
        if e in refs: dpr.append((h[1] - f["th"], h[2] - f["ph"]))
        print(f"  ep {e:2d}{'*' if e in refs else ' '} fit psi/th/ph/Cz {f['psi']:7.2f} {f['th']:6.2f} {f['ph']:6.2f} {f['C'][2]:.3f} | map "
              f"{h[0]:7.2f} {h[1]:6.2f} {h[2]:6.2f} {zc:.3f} | d {wrap(h[0]-f['psi']):+.2f} {h[1]-f['th']:+.2f} {h[2]-f['ph']:+.2f} {zc-f['C'][2]:+.3f}")
    dpr = np.array(dpr)
    print(f"  refs pitch d mean {dpr[:,0].mean():+.2f} sd {dpr[:,0].std():.2f}; roll d mean {dpr[:,1].mean():+.2f} sd {dpr[:,1].std():.2f}")
    print(f"  t_z: table-plane {tz_tab:.4f} vs refs' C_z median {tz_ref:.4f} (diff {(tz_ref-tz_tab)*1000:+.1f} mm); floor in mocap z "
          f"{(R_grav @ cF)[2] + tz_tab:+.4f} m (table-based)")
    Wt = {}
    for e in sorted(W11):
        row = {c: hpr(R_grav @ cams[f"{c}/e{e:02d}_0000.jpg"]["Rwc"]) for c in "abc" if f"{c}/e{e:02d}_0000.jpg" in cams}
        if "a" in row:
            Wt[e] = dict(psi=float(row["a"][0]), th=float(row["a"][1]), ph=float(row["a"][2]), d11=float(wrap(row["a"][0] - W11[e])),
                         psi_b=float(row.get("b", [np.nan])[0]), psi_c=float(row.get("c", [np.nan])[0]))
    d = np.array([v["d11"] for v in Wt.values()])
    print(f"  eval W (cam_a frame 0) map - note11: n={len(d)} mean {d.mean():+.2f} sd {d.std():.2f} max|d| {np.abs(d).max():.2f}; "
          f"b-a {np.mean([wrap(v['psi_b']-v['psi']) for v in Wt.values()]):+.2f} c-a {np.mean([wrap(v['psi_c']-v['psi']) for v in Wt.values()]):+.2f}")
    print("  " + " ".join(f"ev{e}:{v['psi']:.1f}({v['d11']:+.1f})" for e, v in Wt.items()))
    OUT["reg"][gname] = dict(refs=refs, up_map=nup.tolist(), yaw0=yaw0, yaw_per_ref=yaws, loo=loo, R_mocap_from_map=R_grav.tolist(),
                             tz_table=tz_tab, tz_refs=tz_ref, tz_per_ref=zs, W_eval=Wt,
                             note="X_mocap = R X_map + [dx_ep, dy_ep, tz_table]; scale 1 (metric rig); dx,dy per-episode")
tag = MODEL.rstrip("/").split("/")[-3] if MODEL.rstrip("/").split("/")[-2] == "sparse" else os.path.basename(MODEL)
json.dump(OUT, open(f"{HERE}/a3_register_{tag}.json", "w"), indent=1, default=float)
