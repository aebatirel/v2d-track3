"""Verifier (new C2): run3 stride-5 vs run1 stride-5 eval poses, with MY alignment (v_align_run3.json); list every
difference > 6 mm for rig AND cam_a, and attribute it (which map is off) by VO-free temporal smoothness: distance of
each map's pose to the midpoint of its own t-5/t+5 neighbours."""
import json, numpy as np
from scipy.spatial.transform import Rotation as Rot
W = "/Users/aebatirel/Documents/Code/v2d-research/work/18"
A = json.load(open("v_align_run3.json")); Ra = np.array(A["Ra"]); ta = np.array(A["ta"])
EV = [1, 3, 5, 6, 8, 10, 14, 15, 16, 19, 20, 25, 28, 30, 32, 33, 35, 36, 37, 38]
def pose(m):
    m = np.array(m); R = m[:, :3]; t = m[:, 3]; return R.T, -R.T @ t
out = {"c_from_world": ([], []), "a_from_world": ([], [])}; big = []
for e in EV:
    F3 = {f["frame"]: f for f in json.load(open(f"{W}/c1/r3s5_e{e}.json"))["frames"]}
    F1 = {f["frame"]: f for f in json.load(open(f"{W}/c1/s5_e{e}.json"))["frames"]}
    assert set(F3) == set(F1), e
    C = {k: {} for k in out}
    for t in sorted(F3):
        for key in out:
            R3, C3 = pose(F3[t][key]); R1, C1 = pose(F1[t][key])
            R3, C3 = Ra @ R3, Ra @ C3 + ta
            dr = np.degrees(Rot.from_matrix(R3 @ R1.T).magnitude()); dp = 1000 * np.linalg.norm(C3 - C1)
            out[key][0].append(dr); out[key][1].append(dp); C[key][t] = (C3, C1, dp, dr)
    for key in out:
        for t, (C3, C1, dp, dr) in C[key].items():
            if dp > 6:
                nb = [C[key].get(t - 5), C[key].get(t + 5)]
                if all(nb):
                    m3 = (nb[0][0] + nb[1][0]) / 2; m1 = (nb[0][1] + nb[1][1]) / 2
                    s3, s1 = 1000 * np.linalg.norm(C3 - m3), 1000 * np.linalg.norm(C1 - m1)
                else: s3 = s1 = float("nan")
                big.append((key[0], e, t, round(dp, 2), round(dr, 3), round(s3, 2), round(s1, 2)))
for key, (r, p) in out.items():
    r, p = np.array(r), np.array(p)
    print(key, "n", len(r), "rot median %.4f p90 %.4f max %.3f deg | pos median %.3f p90 %.3f max %.2f mm" % (
        np.median(r), np.percentile(r, 90), r.max(), np.median(p), np.percentile(p, 90), p.max()))
print("diffs > 6 mm (cam, ep, frame, d_pos mm, d_rot deg, run3 dist-to-own-neighbour-midpoint, run1 same):")
for b in big: print("  ", b)
