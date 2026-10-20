"""Verifier (new C1): independent recompute on run3 stride-5 eval keyframes: counts, rig/a coverage, inliers,
cam_a pitch/roll/heading envelope in mocap via MY run3->run1 alignment (v_align_run3.json) then a13 rotation."""
import json, numpy as np, cv2
W = "/Users/aebatirel/Documents/Code/v2d-research/work/18"; V = "/Users/aebatirel/Documents/Code/v2d-research/work/18-verify"
D = "/Users/aebatirel/Documents/Code/v2d-research/data/track_3/evaluation/videos/chunk-000"
REG = json.load(open(f"{W}/a13_registration_refined.json")); Rm = np.array(REG["R_mocap_from_map"])
A = json.load(open(f"{V}/v_align_run3.json")); Ra = np.array(A["Ra"])  # R_wc(run1) = Ra R_wc(run3)
EV = [1, 3, 5, 6, 8, 10, 14, 15, 16, 19, 20, 25, 28, 30, 32, 33, 35, 36, 37, 38]
tot = exp = 0; inl, inla, P, Rl, H, steep = [], [], [], [], [], []
for e in EV:
    nf = min(int(cv2.VideoCapture(f"{D}/observation.images.ego_cam_{c}/episode_{e:06d}.mp4").get(cv2.CAP_PROP_FRAME_COUNT)) for c in "abc")
    J = json.load(open(f"{W}/c1/r3s5_e{e}.json")); F = J["frames"]
    assert J["pubonly"] == 0 and "run3" in J["model"], (e, J["model"])
    assert [f["frame"] for f in F] == list(range(0, 5 * len(F), 5)), e
    tot += len(F); exp += -(-nf // 5); h0 = None; ph = []
    for f in F:
        inl.append(f["inl_bc"]); inla.append(f["inl_a"])
        R = np.array(f["a_from_world"])[:, :3]; Rwc = Rm @ Ra @ R.T; fwd, rgt = Rwc[:, 2], Rwc[:, 0]
        th = np.arcsin(-fwd[2]); P.append(np.degrees(th))
        Rl.append(np.degrees(np.arcsin(np.clip(-rgt[2] / np.cos(th), -1, 1))))
        hd = np.degrees(np.arctan2(fwd[1], fwd[0])); h0 = hd if h0 is None else h0
        ph.append((hd - h0 + 180) % 360 - 180)
        steep.append((np.degrees(th), f["inl_bc"], e, f["frame"]))
    H += ph
    print(f"e{e:2d} nf {nf} kf {len(F)} rig min {min(x['inl_bc'] for x in F)} a min {min(x['inl_a'] for x in F)} heading {min(ph):+.1f}..{max(ph):+.1f}")
inl, inla = np.array(inl), np.array(inla)
print("TOTAL kf", tot, "expected ceil(nf/5)", exp, "rig cov", np.mean(inl >= 30), "a cov", np.mean(inla >= 30))
print("rig inliers min", inl.min(), "median", np.median(inl), "| a min", inla.min(), "median", np.median(inla))
print("pitch %.1f..%.1f  roll %.1f..%.1f  heading rel f0 %.1f..%.1f" % (min(P), max(P), min(Rl), max(Rl), min(H), max(H)))
steep.sort(reverse=True); print("steepest 5 (pitch, rig inl, ep, frame):", [(round(a, 1), b, c, d) for a, b, c, d in steep[:5]])
print("n frames pitch>55:", sum(1 for s in steep if s[0] > 55), "min rig inl there", min([s[1] for s in steep if s[0] > 55] or [0]))
