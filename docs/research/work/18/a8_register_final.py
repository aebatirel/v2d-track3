"""DIG 18 A8: final map -> mocap registration.
  gravity  : mean dense-stereo table normal in the map frame (a7; GT: table level in mocap to 0.4 deg, a4)
  yaw      : median over reference frame-0 GT-silhouette fits (note 11 s25, K as given) of (psi_fit - psi_map)
  z        : median over frames of the stereo table-plane height, mapped to the GT table top 0.6012 m
  scale    : 1 (metric b/c rig; a-b check 0.5-2 %)
  x,y      : per-episode (dataset re-centres x,y per episode); given for the GT-fitted refs only.
Writes a8_registration.json (transform + all camera poses in the gravity/mocap-rotated frame) and prints checks.
usage: python a8_register_final.py <model dir> <a5 json> <refs csv>"""
import sys, os, json, numpy as np, pycolmap
from scipy.spatial.transform import Rotation as Rot
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
ROOT = "/Users/aebatirel/Documents/Code/v2d-research"
rec = pycolmap.Reconstruction(sys.argv[1]); A5 = json.load(open(sys.argv[2]))
REFS = [int(x) for x in sys.argv[3].split(",")]
FITS = json.load(open(f"{ROOT}/work/11/s25_refine_native.json"))
W11 = {1: 184.2, 3: 179.5, 5: 179.3, 6: 178.5, 8: 183.8, 10: 180.4, 14: 181.9, 15: 180.8, 16: 182.8, 19: 179.4,
       20: 178.6, 25: 182.2, 28: 179.4, 30: 183.0, 32: 184.6, 33: 177.1, 35: 174.1, 36: 178.1, 37: 176.1, 38: 177.2}
wrap = lambda a: (np.asarray(a) + 180) % 360 - 180


def Rwc11(psi, th, ph):
    p, t = np.radians(psi), np.radians(th)
    f = np.array([np.cos(t) * np.cos(p), np.cos(t) * np.sin(p), -np.sin(t)])
    r = np.cross(f, [0, 0, 1.0]); r /= np.linalg.norm(r); d = np.cross(f, r)
    return np.column_stack([Rot.from_rotvec(f * np.radians(ph)).as_matrix() @ r, Rot.from_rotvec(f * np.radians(ph)).as_matrix() @ d, f])


def hpr(Rwc):
    f = Rwc[:, 2]; r = Rwc[:, 0]
    psi = np.degrees(np.arctan2(f[1], f[0])); th = np.degrees(np.arcsin(-f[2]))
    r0 = np.cross(f, [0, 0, 1.0]); r0 /= np.linalg.norm(r0)
    return psi, th, np.degrees(np.arctan2(np.dot(np.cross(r0, r), f), np.dot(r0, r)))


cams = {}
for im in rec.images.values():
    T = im.cam_from_world(); R = T.rotation.matrix(); t = np.asarray(T.translation)
    cams[im.name] = dict(Rwc=R.T, C=-R.T @ t, Rcw=R, t=t)
# gravity + table height from the per-frame stereo planes
N, H = [], []
for r in A5:
    if not r.get("ok") or r["ninl"] < 3000 or r["sig_deg"] > 1.0: continue
    c = cams["c/" + r["name"]]; n_c = np.array(r["n"]); n_m = c["Rcw"].T @ n_c
    N.append(n_m); H.append(-(n_c @ c["t"] + r["d_table"]))  # plane in map: n_m . X = H
N = np.array(N); up = N.mean(0); up /= np.linalg.norm(up)
H = np.array(H) / (N @ up)  # approx: project offsets on the common normal
cam_above = np.array([r["d_table"] for r in A5 if r.get("ok") and r["ninl"] >= 3000 and r["sig_deg"] <= 1.0])
print(f"stereo gravity from {len(N)} frames; table offset along up: median {np.median(H):.4f} sd {H.std()*1000:.1f} mm; "
      f"camera height above table (stereo, cam_c) median {np.median(cam_above):.3f} p10-p90 {np.percentile(cam_above,10):.3f}-{np.percentile(cam_above,90):.3f}")


def align_up(n):
    z = np.array([0, 0, 1.0]); v = np.cross(n, z); s = np.linalg.norm(v)
    return np.eye(3) if s < 1e-12 else Rot.from_rotvec(v / s * np.arctan2(s, n @ z)).as_matrix()


G = align_up(up)
yaws = {e: float(wrap(FITS[str(e)]["psi"] - hpr(G @ cams[f"a/p{e:02d}_0000.jpg"]["Rwc"])[0])) for e in map(int, FITS)
        if f"a/p{e:02d}_0000.jpg" in cams}
yaw0 = float(np.median([yaws[e] for e in REFS]))
R = Rot.from_euler("z", yaw0, degrees=True).as_matrix() @ G
loo = {e: float(wrap(yaws[e] - np.median([yaws[x] for x in REFS if x != e]))) for e in REFS}
tz = float(0.6012 - np.median(H))  # X_mocap_z = (R X_map)_z + tz, since (R X)_z = up . X
print(f"yaw offsets {dict((e, round(v, 2)) for e, v in yaws.items())}; median(refs {REFS}) {yaw0:.2f}; LOO {dict((e, round(v, 2)) for e, v in loo.items())} "
      f"rms {np.sqrt(np.mean(np.square(list(loo.values())))):.2f}")
print(f"t_z = {tz:.4f} m")
refs_out = {}
for e in sorted(yaws):
    n = f"a/p{e:02d}_0000.jpg"; h = hpr(R @ cams[n]["Rwc"]); fz = FITS[str(e)]; Cm = R @ cams[n]["C"] + [0, 0, tz]
    dxy = np.array(fz["C"][:2]) - Cm[:2]
    refs_out[e] = dict(psi=h[0], th=h[1], ph=h[2], Cz=float(Cm[2]), dpsi=float(wrap(h[0] - fz["psi"])), dth=float(h[1] - fz["th"]),
                       dph=float(h[2] - fz["ph"]), dCz=float(Cm[2] - fz["C"][2]), dxy_episode_offset=dxy.tolist())
    print(f"  ep {e:2d}{'*' if e in REFS else ' '} map psi/th/ph/Cz {h[0]:7.2f} {h[1]:6.2f} {h[2]:6.2f} {Cm[2]:.3f} | fit {fz['psi']:7.2f} {fz['th']:6.2f} {fz['ph']:6.2f} "
          f"{fz['C'][2]:.3f} | d {refs_out[e]['dpsi']:+.2f} {refs_out[e]['dth']:+.2f} {refs_out[e]['dph']:+.2f} {refs_out[e]['dCz']*100:+.1f}cm")
d = np.array([[v["dth"], v["dph"], v["dCz"]] for e, v in refs_out.items() if e in REFS])
print(f"refs: pitch d {d[:,0].mean():+.2f}±{d[:,0].std():.2f}, roll d {d[:,1].mean():+.2f}±{d[:,1].std():.2f}, Cz d {d[:,2].mean()*100:+.1f}±{d[:,2].std()*100:.1f} cm")
Wt = {}
for e in sorted(W11):
    n = f"a/e{e:02d}_0000.jpg"
    if n in cams:
        h = hpr(R @ cams[n]["Rwc"]); Wt[e] = dict(psi=float(h[0]), th=float(h[1]), ph=float(h[2]), Cz=float((R @ cams[n]["C"])[2] + tz),
                                                  d11=float(wrap(h[0] - W11[e])))
dd = np.array([v["d11"] for v in Wt.values()])
print(f"eval W map - note11: mean {dd.mean():+.2f} sd {dd.std():.2f} max {np.abs(dd).max():.2f}")
print("eval frame-0 cam_a (psi, pitch, roll, Cz):", "; ".join(f"ev{e} {v['psi']:.1f} {v['th']:.1f} {v['ph']:.1f} {v['Cz']:.3f}" for e, v in Wt.items()))
poses = {}
for n, c in cams.items():
    Rw = R @ c["Rwc"]; h = hpr(Rw)
    poses[n] = dict(R_wc=Rw.tolist(), C=(R @ c["C"] + [0, 0, tz]).tolist(), psi=float(h[0]), th=float(h[1]), ph=float(h[2]))
json.dump(dict(model=os.path.abspath(sys.argv[1]), refs=REFS, R_mocap_from_map=R.tolist(), t_z=tz, scale=1.0,
               up_map=up.tolist(), yaw0=yaw0, yaw_per_fit=yaws, loo=loo, refs_check=refs_out, W_eval=Wt,
               convention="X_mocap = R_mocap_from_map @ X_map + [dx_ep, dy_ep, t_z]; R_wc columns = cam right/down/forward "
                          "(undistorted PINHOLE images of a1; same orientation as raw frames). C has dx=dy=0 (map x,y).",
               poses=poses), open(f"{HERE}/a8_registration.json", "w"), indent=1, default=float)
