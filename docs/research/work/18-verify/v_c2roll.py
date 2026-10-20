import json, numpy as np
W = "/Users/aebatirel/Documents/Code/v2d-research/work/18"
REG = json.load(open(f"{W}/a13_registration_refined.json")); Rm = np.array(REG["R_mocap_from_map"])
EV = [1, 3, 5, 6, 8, 10, 14, 15, 16, 19, 20, 25, 28, 30, 32, 33, 35, 36, 37, 38]
ph = []
for e in EV:
    for f in json.load(open(f"{W}/c1/s5_e{e}.json"))["frames"]:
        R = np.array(f["a_from_world"])[:, :3]; Rwc = Rm @ R.T; fwd, rgt = Rwc[:, 2], Rwc[:, 0]
        th = np.arcsin(-fwd[2]); ph.append(np.degrees(np.arcsin(np.clip(-rgt[2] / np.cos(th), -1, 1))))
print("roll about optical axis: %.1f .. %.1f deg" % (min(ph), max(ph)))
