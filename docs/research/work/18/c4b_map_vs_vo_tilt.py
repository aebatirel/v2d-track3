"""DIG 18 C4b: GT-free arbiter map vs VO. The per-frame stereo table normal (camera frame, c4) is put in mocap with the
map pose (c4) and with the VO-chained pose (anchored at the first keyframe's map pose). If the map is right, its tilt
stays flat over the clip while the VO tilt grows with VO rotation drift. Reads no GT.
usage: python c4b_map_vs_vo_tilt.py <c4 json> <prefix s5>"""
import sys, json, numpy as np
REG = json.load(open("a13_registration_refined.json")); Rm = np.array(REG["R_mocap_from_map"])
C4 = json.load(open(sys.argv[1])); PFX = sys.argv[2]
def T44(m): x = np.eye(4); x[:3] = np.array(m); return x
def inv(T): x = np.eye(4); x[:3, :3] = T[:3, :3].T; x[:3, 3] = -T[:3, :3].T @ T[:3, 3]; return x
allm, allv, late_m, late_v = [], [], [], []
for ep, v in C4.items():
    Tc = {r["frame"]: T44(r["c_from_world"]) for r in json.load(open(f"c1/{PFX}_e{ep}.json"))["frames"] if r.get("inl_bc", 0) >= 30}
    Tv = {r["frame"]: T44(r["c_from_c0"]) for r in json.load(open(f"c3/vo_e{ep}.json"))["frames"]}
    k0 = min(Tc); out = []
    for r in v["rows"]:
        t = r["t"]; nm = np.array([r["nx"], r["ny"], np.sqrt(max(0, 1 - r["nx"] ** 2 - r["ny"] ** 2))])
        ncam = Tc[t][:3, :3] @ Rm.T @ nm                      # camera-frame normal
        Tvo = Tv[t] @ inv(Tv[k0]) @ Tc[k0]
        nv = Rm @ Tvo[:3, :3].T @ ncam
        tv = float(np.degrees(np.arccos(np.clip(nv[2], -1, 1))))
        out.append((t, r["tilt"], tv))
    o = np.array(out); allm += list(o[:, 1]); allv += list(o[:, 2])
    late = o[o[:, 0] >= 0.5 * o[:, 0].max()]; late_m += list(late[:, 1]); late_v += list(late[:, 2])
    print(f"e{ep:>2}: t " + " ".join(f"{int(a)}:{b:.2f}/{c:.2f}" for a, b, c in o) + "   (map/VO tilt deg)")
for nm, a, b in (("all", allm, allv), ("second half of each clip", late_m, late_v)):
    a, b = np.array(a), np.array(b)
    print(f"{nm}: map tilt median {np.median(a):.2f} p90 {np.percentile(a, 90):.2f} max {a.max():.2f} | VO tilt median {np.median(b):.2f} p90 {np.percentile(b, 90):.2f} max {b.max():.2f} (n={len(a)})")
