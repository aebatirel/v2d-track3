"""DIG 18 B18: GT-free divergence of frame-to-frame stereo VO (b3 v2, chained from the relocalised frame 0) from per-frame map
relocalisation (rig c pose), over EVERY frame of a clip. Map units are metric. usage: python b18_vo_drift.py <reloc json> <vo json> ..."""
import sys, json, numpy as np
from scipy.spatial.transform import Rotation as Rot
a = sys.argv[1:]
for i in range(0, len(a), 2):
    RL = json.load(open(a[i])); VO = json.load(open(a[i + 1]))
    R = {int(r["frame"]): np.vstack([np.array(r["c_from_world"]), [0, 0, 0, 1]]) for r in RL["frames"] if r.get("inl_bc", 0) >= 30}
    V = {int(r["frame"]): np.array(r["c_from_c0"]) for r in VO["frames"] if "c_from_c0" in r}
    T0 = R[0]; rows = []
    for t in sorted(set(R) & set(V)):
        Tv = np.vstack([V[t][:3], [0, 0, 0, 1]]) @ T0
        Cv = -Tv[:3, :3].T @ Tv[:3, 3]; Cm = -R[t][:3, :3].T @ R[t][:3, 3]
        rows.append((t, np.linalg.norm(Cv - Cm) * 1000, np.degrees(np.linalg.norm(Rot.from_matrix(Tv[:3, :3] @ R[t][:3, :3].T).as_rotvec()))))
    r = np.array(rows); n = len(r)
    print(f"{RL['tag']}: {n} frames ({n / 20:.1f} s) | VO vs map: end {r[-1, 1]:.1f} mm / {r[-1, 2]:.2f} deg; max {r[:, 1].max():.1f} mm / {r[:, 2].max():.2f} deg;"
          f" at thirds (mm) {r[n // 3, 1]:.1f} / {r[2 * n // 3, 1]:.1f} / {r[-1, 1]:.1f}")
