"""Verifier: independent recompute of C8 (run3 vs run1 eval poses) from c1/*.json + an independently recomputed alignment.
usage: python v_c8.py <align.json>"""
import sys, json, glob, numpy as np
from scipy.spatial.transform import Rotation as Rot
W = "/Users/aebatirel/Documents/Code/v2d-research/work/18"
A = json.load(open(sys.argv[1])); Ra = np.array(A["Ra"]); ta = np.array(A["ta"])
EV = [1, 3, 5, 6, 8, 10, 14, 15, 16, 19, 20, 25, 28, 30, 32, 33, 35, 36, 37, 38]
def pose(m):  # cam_from_world 3x4 -> R_wc, C
    m = np.array(m); R = m[:, :3]; t = m[:, 3]; return R.T, -R.T @ t
dr, dp, ar, ap, inl, n3, cov = [], [], [], [], [], 0, []
inl_a3 = []
for e in EV:
    F3 = json.load(open(f"{W}/c1/r3s25_e{e}.json"))["frames"]; F1 = {f["frame"]: f for f in json.load(open(f"{W}/c1/s5_e{e}.json"))["frames"]}
    n3 += len(F3)
    for f in F3:
        inl.append(f.get("inl_bc", 0)); inl_a3.append(f.get("inl_a", 0)); cov.append(f.get("inl_bc", 0) >= 30)
        g = F1.get(f["frame"])
        if g is None: print("missing run1 frame", e, f["frame"]); continue
        for key, LR, LP in (("c_from_world", dr, dp), ("a_from_world", ar, ap)):
            if key not in f or key not in g: continue
            R3, C3 = pose(f[key]); R1, C1 = pose(g[key])
            # map run3 world -> run1 world: X1 = Ra X3 + ta
            R3in1 = Ra @ R3; C3in1 = Ra @ C3 + ta
            LR.append(np.degrees(Rot.from_matrix(R3in1 @ R1.T).magnitude())); LP.append(1000 * np.linalg.norm(C3in1 - C1))
dr, dp, ar, ap = map(np.array, (dr, dp, ar, ap))
print("n keyframes run3", n3, "coverage", np.mean(cov), "rig inl min", min(inl), "median", np.median(inl), "cam_a inl min", min(inl_a3))
print("rig rot median %.4f p90 %.4f max %.3f deg; pos median %.3f p90 %.3f max %.2f mm" % (np.median(dr), np.percentile(dr, 90), dr.max(), np.median(dp), np.percentile(dp, 90), dp.max()))
print("cam_a rot median %.4f max %.3f; pos median %.3f max %.2f mm" % (np.median(ar), ar.max(), np.median(ap), ap.max()))
print("n>=8mm rig", int((dp >= 8).sum()), "n>=3mm", int((dp >= 3).sum()), "n>=5mm", int((dp >= 5).sum()))
