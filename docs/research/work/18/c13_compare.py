"""DIG 18 C13: default-module tracks (run3 + a13 + C10 + C9 gate, c13_export) vs the prototype tracks (run1 + a13,
c6_export) at every frame of every eval clip. The known C10 tilt is undone first, so the remainder = map choice
(run3 vs run1) + gate + lag re-estimate. Reads no GT.
usage: python c13_compare.py <v2 dir> <v1 dir>"""
import sys, json, glob, os, numpy as np
from scipy.spatial.transform import Rotation as Rot

D2, D1 = sys.argv[1], sys.argv[2]
allr, allp = {"c": [], "a": []}, {"c": [], "a": []}
for f2 in sorted(glob.glob(f"{D2}/e*.json"), key=lambda x: int(os.path.basename(x)[1:-5])):
    A = json.load(open(f2)); B = json.load(open(f"{D1}/{os.path.basename(f2)}"))
    Rt = np.array(A["registration"]["R_tilt"]); p = np.array(A["registration"]["pivot"])
    F1 = {r["frame"]: r for r in B["frames"]}; line = [f"e{A['ep']}:"]
    for cam in ("c", "a"):
        rr, dp = [], []
        for r in A["frames"]:
            if cam not in r or r["frame"] not in F1 or cam not in F1[r["frame"]]: continue
            R2 = Rt.T @ np.array(r[cam]["R_wc"]); C2 = Rt.T @ (np.array(r[cam]["C"]) - p) + p
            R1 = np.array(F1[r["frame"]][cam]["R_wc"]); C1 = np.array(F1[r["frame"]][cam]["C"])
            rr.append(np.degrees(np.linalg.norm(Rot.from_matrix(R2 @ R1.T).as_rotvec()))); dp.append((C2 - C1) * 1000)
        rr, dp = np.array(rr), np.array(dp); d = np.linalg.norm(dp, axis=1); dv = np.linalg.norm(dp - np.median(dp, 0), axis=1)
        allr[cam] += rr.tolist(); allp[cam] += d.tolist()
        line.append(f"{cam} n{len(rr)} rot med {np.median(rr):.3f} max {rr.max():.3f} deg | pos med {np.median(d):.2f} p90 {np.percentile(d, 90):.2f} "
                    f"max {d.max():.1f} mm | varying med {np.median(dv):.2f} max {dv.max():.1f} mm;")
    lv2, lv1 = A["lag_a_minus_c_frames"], B["lag_a_minus_c_frames"]
    line.append(f"lag v2 {lv2['n_before']}/{lv2['n_after']}@{lv2['switch_keyframe']} {lv2['frac']:+.2f} v1 {lv1['n_before']}/{lv1['n_after']}@{lv1['switch_keyframe']} {lv1['frac']:+.2f}")
    print(" ".join(line), flush=True)
for cam in ("c", "a"):
    r, d = np.array(allr[cam]), np.array(allp[cam])
    print(f"ALL {cam}: n {len(r)} rot med {np.median(r):.3f} p90 {np.percentile(r, 90):.3f} max {r.max():.3f} deg | pos med {np.median(d):.2f} "
          f"p90 {np.percentile(d, 90):.2f} p99 {np.percentile(d, 99):.2f} max {d.max():.1f} mm")
