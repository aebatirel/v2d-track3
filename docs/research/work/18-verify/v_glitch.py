"""Verifier: for the two >=8 mm run3-vs-run1 differences, predict the c pose at t from run1 keyframes t-5 and t+5 via VO (c3) and
see which map's pose is off."""
import json, numpy as np
W = "/Users/aebatirel/Documents/Code/v2d-research/work/18"
A = json.load(open(f"{W}/b2_align_run3.json")); Ra = np.array(A["Ra"]); ta = np.array(A["ta"])
def H(m): x = np.eye(4); x[:3] = np.array(m); return x
for e, t in ((10, 100), (35, 175), (3, 85)):
    R1 = {f["frame"]: H(f["c_from_world"]) for f in json.load(open(f"{W}/c1/s5_e{e}.json"))["frames"]}
    R3 = {f["frame"]: H(f["c_from_world"]) for f in json.load(open(f"{W}/c1/r3s25_e{e}.json"))["frames"]}
    V = {f["frame"]: H(f["c_from_c0"]) for f in json.load(open(f"{W}/c3/vo_e{e}.json"))["frames"]}; V.setdefault(0, np.eye(4))
    C = lambda T: -T[:3, :3].T @ T[:3, 3]
    preds = [V[t] @ np.linalg.inv(V[k]) @ R1[k] for k in (t - 5, t + 5)]  # c_t from world (run1)
    out = f"e{e} t{t}: VO preds disagree {1000*np.linalg.norm(C(preds[0]) - C(preds[1])):.2f} mm | run1 vs preds " + \
          " ".join(f"{1000*np.linalg.norm(C(R1[t]) - C(p)):.2f}" for p in preds)
    if t in R3:
        T13 = np.eye(4); T13[:3, :3] = Ra.T; T13[:3, 3] = -Ra.T @ ta; T3 = R3[t] @ T13
        out += " | run3 vs preds " + " ".join(f"{1000*np.linalg.norm(C(T3) - C(p)):.2f}" for p in preds)
    print(out)
