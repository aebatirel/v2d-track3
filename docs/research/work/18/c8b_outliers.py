"""DIG 18 C8b: list the largest run3-vs-run1 rig disagreements with inliers on both sides and the VO v2 verdict
(which map pose is consistent with VO-propagated neighbours). Reads no GT."""
import json, numpy as np, sys
from scipy.spatial.transform import Rotation as Rot
A = json.load(open("b2_align_run3.json")); Ra = np.array(A["Ra"]); ta = np.array(A["ta"])
T13 = np.eye(4); T13[:3, :3] = Ra.T; T13[:3, 3] = -Ra.T @ ta
def T44(m): x = np.eye(4); x[:3] = np.array(m); return x
for e in [int(x) for x in sys.argv[1:]]:
    R3 = {r["frame"]: r for r in json.load(open(f"c1/r3s25_e{e}.json"))["frames"]}
    R1 = {r["frame"]: r for r in json.load(open(f"c1/s5_e{e}.json"))["frames"]}
    out = []
    for t, r in R3.items():
        if t not in R1: continue
        Ta = T44(r["c_from_world"]) @ T13; Tb = T44(R1[t]["c_from_world"])
        dr = np.degrees(np.linalg.norm(Rot.from_matrix(Ta[:3, :3] @ Tb[:3, :3].T).as_rotvec()))
        Ca = -Ta[:3, :3].T @ Ta[:3, 3]; Cb = -Tb[:3, :3].T @ Tb[:3, 3]
        # neighbours in run1 (t-5, t+5): smoothness check of the run1 pose at t
        nb = [R1[u] for u in (t - 5, t + 5) if u in R1]
        Cn = [(-T44(x["c_from_world"])[:3, :3].T @ T44(x["c_from_world"])[:3, 3]) for x in nb]
        dev1 = np.linalg.norm(Cb - np.mean(Cn, 0)) * 1000 if len(Cn) == 2 else np.nan
        dev3 = np.linalg.norm(Ca - np.mean(Cn, 0)) * 1000 if len(Cn) == 2 else np.nan
        out.append((np.linalg.norm(Ca - Cb) * 1000, dr, t, r["inl_bc"], R1[t]["inl_bc"], dev1, dev3, r.get("blur_c"), R1[t].get("blur_c")))
    out.sort(reverse=True)
    for o in out[:3]:
        print(f"e{e} t={o[2]} dpos {o[0]:.2f} mm drot {o[1]:.3f} deg inl run3 {o[3]} run1 {o[4]} | dist to midpoint of run1 t+-5: run1 {o[5]:.2f} mm, run3 {o[6]:.2f} mm | blur {o[7]}")
