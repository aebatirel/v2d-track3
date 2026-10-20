"""DIG 18 C11b: pose error vs rig inlier count over all occluded runs (run3, eps 35/10/38). Reads no GT."""
import json, glob, numpy as np
from scipy.spatial.transform import Rotation as Rot
def T44(m): x = np.eye(4); x[:3] = np.array(m); return x
def cen(T): return -T[:3, :3].T @ T[:3, 3]
P = []
for f in glob.glob("c11/*_e*.json"):
    e = int(f.split("_e")[1].split(".")[0]); B = {r["frame"]: r for r in json.load(open(f"c1/r3s25_e{e}.json"))["frames"]}
    for r in json.load(open(f))["frames"]:
        if r["inl_bc"] < 30: continue
        M, G = T44(r["c_from_world"]), T44(B[r["frame"]]["c_from_world"])
        P.append((r["inl_bc"], np.linalg.norm(cen(M) - cen(G)) * 1000, np.degrees(np.linalg.norm(Rot.from_matrix(M[:3, :3] @ G[:3, :3].T).as_rotvec()))))
P = np.array(P)
for lo, hi in ((30, 60), (60, 100), (100, 200), (200, 400), (400, 2000)):
    s = P[(P[:, 0] >= lo) & (P[:, 0] < hi)]
    if len(s): print(f"rig inliers {lo}-{hi}: n {len(s):3d} dpos median {np.median(s[:,1]):.1f} p90 {np.percentile(s[:,1],90):.1f} max {s[:,1].max():.1f} mm; drot median {np.median(s[:,2]):.3f} max {s[:,2].max():.3f} deg")
