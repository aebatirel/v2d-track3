"""DIG 18 A13: apply the multi-episode yaw correction (A11 median over 19 public eps, cross-checked by A12 IoU on 6
frame-0s) to the A8 registration. Writes a13_registration_refined.json (same layout as a8_registration.json)."""
import json, numpy as np, os
from scipy.spatial.transform import Rotation as Rot
HERE = os.path.dirname(os.path.abspath(__file__))
R8 = json.load(open(f"{HERE}/a8_registration.json")); A11 = json.load(open(f"{HERE}/a11_yaw_profile.json"))["episodes"]
A12 = json.load(open(f"{HERE}/a12_iou_check.json"))
d11 = np.array([v["best_parab"] for v in A11.values()]); d12 = np.array([v["best"] for v in A12.values()])
delta = float(np.median(d11))
print(f"A11 median {np.median(d11):+.2f} mean {d11.mean():+.2f} sd {d11.std():.2f} (n={len(d11)}); A12 mean {d12.mean():+.2f} sd {d12.std():.2f} (n={len(d12)}) -> delta {delta:+.2f}")
Rz = Rot.from_euler("z", delta, degrees=True).as_matrix()
out = dict(R8); out["R_mocap_from_map"] = (Rz @ np.array(R8["R_mocap_from_map"])).tolist(); out["yaw0"] = R8["yaw0"] + delta
out["yaw_correction_deg"] = delta; out["note"] = "A8 registration with yaw rotated by delta about mocap z (x,y per episode anyway)"
P = {}
for n, p in R8["poses"].items():
    Rw = Rz @ np.array(p["R_wc"]); C = Rz @ np.array(p["C"])
    P[n] = dict(R_wc=Rw.tolist(), C=C.tolist(), psi=float((p["psi"] + delta + 180) % 360 - 180), th=p["th"], ph=p["ph"])
out["poses"] = P
W = {e: dict(v, psi=float((v["psi"] + delta + 180) % 360 - 180), d11=float(v["d11"] + delta)) for e, v in R8["W_eval"].items()}
out["W_eval"] = W
json.dump(out, open(f"{HERE}/a13_registration_refined.json", "w"), indent=1)
print("refined eval W (deg, mocap heading of cam_a frame 0; note 11 value + d):")
print(" ".join(f"ev{e}:{(v['psi']) % 360:.1f}({v['d11']:+.1f})" for e, v in W.items()))
