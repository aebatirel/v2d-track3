"""Verifier: independent recompute of C2 (run1 stride-5 eval keyframes): counts, coverage, inliers, cam_a pitch/roll/height in mocap via a13."""
import json, numpy as np, cv2
W = "/Users/aebatirel/Documents/Code/v2d-research/work/18"; D = "/Users/aebatirel/Documents/Code/v2d-research/data/track_3/evaluation/videos/chunk-000"
REG = json.load(open(f"{W}/a13_registration_refined.json")); Rm = np.array(REG["R_mocap_from_map"]); tz = REG["t_z"]
EV = [1, 3, 5, 6, 8, 10, 14, 15, 16, 19, 20, 25, 28, 30, 32, 33, 35, 36, 37, 38]
tot = 0; exp_tot = 0; allp, allr, allz, inl_bc, inl_a, cov_r, cov_a = [], [], [], [], [], [], []
for e in EV:
    nf = min(int(cv2.VideoCapture(f"{D}/observation.images.ego_cam_{c}/episode_{e:06d}.mp4").get(cv2.CAP_PROP_FRAME_COUNT)) for c in "abc")
    F = json.load(open(f"{W}/c1/s5_e{e}.json"))["frames"]; tot += len(F); exp_tot += -(-nf // 5)
    fr = [f["frame"] for f in F]
    assert fr == list(range(0, 5 * len(F), 5)), e
    P, Rr, Z = [], [], []
    for f in F:
        inl_bc.append(f.get("inl_bc", 0)); inl_a.append(f.get("inl_a", 0)); cov_r.append(f.get("inl_bc", 0) >= 30); cov_a.append(f.get("inl_a", 0) >= 30)
        if f.get("inl_a", 0) < 30: continue
        m = np.array(f["a_from_world"]); R = m[:, :3]; t = m[:, 3]
        Rwc = Rm @ R.T; C = Rm @ (-R.T @ t)
        fwd, rgt = Rwc[:, 2], Rwc[:, 0]
        P.append(np.degrees(np.arcsin(-fwd[2])))  # below horizon
        Rr.append(np.degrees(np.arcsin(-rgt[2])))  # right vector dipping => positive (my convention)
        Z.append(C[2] + tz)
    print(f"e{e:2d} nf {nf} kf {len(F)} (exp {-(-nf // 5)}) pitch {min(P):.1f}..{max(P):.1f} rollasin {min(Rr):.1f}..{max(Rr):.1f} z {min(Z):.3f}..{max(Z):.3f}")
    allp += P; allr += Rr; allz += Z
print("TOTAL keyframes", tot, "expected", exp_tot, "rig cov", np.mean(cov_r), "a cov", np.mean(cov_a), "rig inl min", min(inl_bc), "a inl min", min(inl_a))
print("pitch %.1f..%.1f  roll(asin right_z) %.1f..%.1f  height %.3f..%.3f" % (min(allp), max(allp), min(allr), max(allr), min(allz), max(allz)))
