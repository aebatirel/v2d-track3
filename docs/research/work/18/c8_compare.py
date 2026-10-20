"""DIG 18 C8: public-only map (run3, no eval image at all) vs pooled map (run1): relocalised eval poses at common
frames, after mapping run3 into run1 coordinates with b2_align (X_run1 = Ra X_run3 + ta). Reads no GT.
usage: python c8_compare.py <align json> <prefix run3 outputs e.g. r3s25> <prefix run1 outputs e.g. s5>"""
import sys, json, os, numpy as np
from scipy.spatial.transform import Rotation as Rot
A = json.load(open(sys.argv[1])); Ra = np.array(A["Ra"]); ta = np.array(A["ta"]); P3, P1 = sys.argv[2], sys.argv[3]
T13 = np.eye(4); T13[:3, :3] = Ra.T; T13[:3, 3] = -Ra.T @ ta  # run1 coords -> run3 coords


def T44(m):
    x = np.eye(4); x[:3] = np.array(m); return x


EV = [1, 3, 5, 6, 8, 10, 14, 15, 16, 19, 20, 25, 28, 30, 32, 33, 35, 36, 37, 38]
allr, allp, alla_r, alla_p, cov, inl = [], [], [], [], [], []
for e in EV:
    f3, f1 = f"c1/{P3}_e{e}.json", f"c1/{P1}_e{e}.json"
    if not (os.path.exists(f3) and os.path.exists(f1)): continue
    R3 = json.load(open(f3))["frames"]; R1 = {r["frame"]: r for r in json.load(open(f1))["frames"]}
    rr, pp, ar, ap, dv = [], [], [], [], []
    for r in R3:
        cov.append(r.get("inl_bc", 0) >= 30); inl.append(r.get("inl_bc", 0))
        t = r["frame"]
        if t not in R1 or r.get("inl_bc", 0) < 30: continue
        for key, lr, lp in (("c_from_world", rr, pp), ("a_from_world", ar, ap)):
            if key not in r or key not in R1[t]: continue
            Ta = T44(r[key]) @ T13; Tb = T44(R1[t][key])
            lr.append(np.degrees(np.linalg.norm(Rot.from_matrix(Ta[:3, :3] @ Tb[:3, :3].T).as_rotvec())))
            Ca = -Ta[:3, :3].T @ Ta[:3, 3]; Cb = -Tb[:3, :3].T @ Tb[:3, 3]; lp.append(np.linalg.norm(Ca - Cb) * 1000)
            if key == "c_from_world": dv.append((Ca - Cb) * 1000)
    allr += rr; allp += pp; alla_r += ar; alla_p += ap
    print(f"e{e:2d}: n={len(rr)} rig rot {np.median(rr):.3f}/{np.max(rr):.3f} deg pos {np.median(pp):.2f}/{np.max(pp):.2f} mm | "
          f"cam_a rot {np.median(ar):.3f}/{np.max(ar):.3f} pos {np.median(ap):.2f}/{np.max(ap):.2f} (median/max) | rig pos time-varying part "
          f"(dist to clip-mean offset) median {np.median(np.linalg.norm(np.array(dv) - np.mean(dv, 0), axis=1)):.2f} max {np.max(np.linalg.norm(np.array(dv) - np.mean(dv, 0), axis=1)):.2f} mm")
print(f"ALL: coverage {np.mean(cov):.3f} (n={len(cov)}), rig inliers min {min(inl)} median {np.median(inl):.0f}; "
      f"rig vs run1 rot median {np.median(allr):.3f} p90 {np.percentile(allr, 90):.3f} max {np.max(allr):.3f} deg, pos median {np.median(allp):.2f} p90 "
      f"{np.percentile(allp, 90):.2f} max {np.max(allp):.2f} mm; cam_a rot median {np.median(alla_r):.3f} max {np.max(alla_r):.3f}, pos median "
      f"{np.median(alla_p):.2f} max {np.max(alla_p):.2f} mm")
