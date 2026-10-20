"""DIG 18 B9: keyframe relocalisation + VO bridge, simulated from b1 (rig c_from_world) and b3 (c_from_c0) outputs.
pose(t) = VO(t <- k) * reloc(k), k = last keyframe (every N frames). Compared with per-frame relocalisation.
usage: python b9_hybrid.py <reloc json> <vo json> ..."""
import sys, json, numpy as np
from scipy.spatial.transform import Rotation as R


def T44(m):
    x = np.eye(4); x[:3] = np.array(m); return x


args = sys.argv[1:]
for rj, vj in zip(args[::2], args[1::2]):
    RL = json.load(open(rj)); VO = json.load(open(vj)); tag = RL["tag"]
    Tr = {r["frame"]: T44(r["c_from_world"]) for r in RL["frames"] if r.get("inl_bc", 0) >= 30}
    Tv = {r["frame"]: T44(r["c_from_c0"]) for r in VO["frames"]}
    tm = np.median([sum(r["time"].values()) for r in RL["frames"]])
    out = []
    for N in (1, 5, 10, 20, 40):
        dp, dr = [], []
        for t in sorted(Tr):
            k = (t // N) * N
            if k not in Tr or t not in Tv or k not in Tv: continue
            P = Tv[t] @ np.linalg.inv(Tv[k]) @ Tr[k]; E = P @ np.linalg.inv(Tr[t])
            dp.append(np.linalg.norm(-E[:3, :3].T @ E[:3, 3]) * 1000); dr.append(np.degrees(np.linalg.norm(R.from_matrix(E[:3, :3]).as_rotvec())))
        dp, dr = np.array(dp), np.array(dr)
        out.append(f"N={N:2d}: pos {np.median(dp):.2f}/{np.percentile(dp, 95):.2f}/{dp.max():.2f} mm, rot {np.median(dr):.3f}/{np.percentile(dr, 95):.3f}/{dr.max():.3f} deg, cost ~{tm / N + 0.07:.2f} s/frame")
    print(tag, "(median/p95/max vs per-frame reloc)\n  " + "\n  ".join(out))
