"""DIG 18 B12: which absolute camera tilt is right, the map's (a13) or note 17's marker-registered cameras?
Arbiter = the dense b/c stereo table plane measured in the cam_c frame (a5, map-free) at every 30th frame; GT says the
table top is level in the dataset world to 0.4 deg (a4). Express the plane normal in each world through that frame's
cam_c orientation and report the angle to +z. Also the orbit-ambiguity profile of a 6-DoF marker fit.
usage: python b12_table_arbiter.py <ep> <reloc json> <align json|->"""
import sys, json, numpy as np
HERE = "/Users/aebatirel/Documents/Code/v2d-research/work/18"
EP = int(sys.argv[1]); RL = json.load(open(sys.argv[2])); AL = json.load(open(sys.argv[3])) if sys.argv[3] != "-" else None
REG = json.load(open(f"{HERE}/a13_registration_refined.json")); Rm = np.array(REG["R_mocap_from_map"])
R17 = json.load(open(f"/Users/aebatirel/Documents/Code/v2d-research/work/17/out/reg2_{EP}.json"))
A5 = {x["name"]: x for x in json.load(open(f"{HERE}/a5_stereo_table.json")) if x.get("ok")}
Ra = np.array(AL["Ra"]) if AL else np.eye(3)
fr = {int(r["frame"]): r for r in RL["frames"]}
rows = []
for t in range(0, 10 ** 4, 30):
    k = f"p{EP:02d}_{t:04d}.jpg"
    if k not in A5 or t not in fr or t >= len(R17["cams_c"]): continue
    n = np.array(A5[k]["n"]); n /= np.linalg.norm(n)
    Rcw = np.array(fr[t]["c_from_world"])[:, :3]           # run2 map: X_c = Rcw X_w + t
    Rwc_mine = Rm @ (Rcw @ Ra.T).T                           # run2 -> run1 (X1 = Ra X2 + ta) -> mocap
    Rwc_17 = np.array(R17["cams_c"][t]["Rwc"])
    tilt = lambda R: float(np.degrees(np.arccos(min(1.0, abs((R @ n)[2])))))
    rows.append((t, tilt(Rwc_mine), tilt(Rwc_17), A5[k]["sig_deg"]))
r = np.array(rows)
print(f"ep {EP}: stereo table normal tilt from +z (deg) at frames {r[:, 0].astype(int).tolist()}")
print(f"   map (a13)        : {np.round(r[:, 1], 2).tolist()}  median {np.median(r[:, 1]):.2f}")
print(f"   note 17 cameras  : {np.round(r[:, 2], 2).tolist()}  median {np.median(r[:, 2]):.2f}")
print(f"   plane sigma (deg): {np.round(r[:, 3], 2).tolist()}")
json.dump(dict(ep=EP, rows=rows), open(f"{HERE}/b11/b12_table_p{EP}.json", "w"))
