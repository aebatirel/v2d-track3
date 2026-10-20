import json, numpy as np
from scipy.spatial.transform import Rotation as Rot
W = "/Users/aebatirel/Documents/Code/v2d-research/work/18"
A = json.load(open("v_align_run3.json")); Ra = np.array(A["Ra"]); ta = np.array(A["ta"])
def C(m):
    m = np.array(m); return -m[:, :3].T @ m[:, 3]
for e, ts in ((3, [75, 80, 85, 90, 95]), (35, [225, 230, 235, 240, 245]), (35, [165, 170, 175, 180, 185])):
    F3 = {f["frame"]: f for f in json.load(open(f"{W}/c1/r3s5_e{e}.json"))["frames"]}
    F1 = {f["frame"]: f for f in json.load(open(f"{W}/c1/s5_e{e}.json"))["frames"]}
    for t in ts:
        c3 = Ra @ C(F3[t]["c_from_world"]) + ta; c1 = C(F1[t]["c_from_world"])
        print(e, t, "run1 C mm", np.round(c1 * 1000, 1), "run3-run1 mm", np.round((c3 - c1) * 1000, 2), "inl r1", F1[t]["inl_bc"], "r3", F3[t]["inl_bc"])
