"""DIG 18 B5b: does a -1.15-frame lag explain the rig->cam_a vs cam_a-own-PnP disagreement? (no GT)
usage: python b5b_lagfix.py <reloc json>..."""
import sys, json, numpy as np
from scipy.spatial.transform import Rotation as R, Slerp


def T44(m):
    x = np.eye(4); x[:3] = np.array(m); return x


for fn in sys.argv[1:]:
    d = json.load(open(fn)); fr = [r for r in d["frames"] if r.get("inl_bc", 0) >= 30 and r.get("inl_a", 0) >= 30]
    t = np.array([r["frame"] for r in fr], float); Tc = [T44(r["c_from_world"]) for r in fr]; Ta = [T44(r["a_from_world"]) for r in fr]
    Rcw = R.from_matrix([T[:3, :3].T for T in Tc]); Cc = np.array([-T[:3, :3].T @ T[:3, 3] for T in Tc]); sl = Slerp(t, Rcw)
    res = []
    for lag in (0.0, -0.5, -1.0, -1.15, -1.5):
        tt = np.clip(t + lag, t[0], t[-1]); Rw = sl(tt).as_matrix(); C = np.array([np.interp(tt, t, Cc[:, k]) for k in range(3)]).T
        Tci = []
        for Rw_, C_ in zip(Rw, C):
            T = np.eye(4); T[:3, :3] = Rw_.T; T[:3, 3] = -Rw_.T @ C_; Tci.append(T)
        P = [Ta[i] @ np.linalg.inv(Tci[i]) for i in range(len(fr))]  # a <- c(t+lag)
        U, S, Vt = np.linalg.svd(sum(p[:3, :3] for p in P)); Rm = U @ Vt; tm = np.mean([p[:3, 3] for p in P], 0)
        ang = [np.degrees(np.linalg.norm(R.from_matrix(p[:3, :3] @ Rm.T).as_rotvec())) for p in P]
        dt = [np.linalg.norm(p[:3, 3] - tm) * 1000 for p in P]
        res.append(f"lag {lag:+.2f}: a<-c rot spread median {np.median(ang):.3f} p90 {np.percentile(ang, 90):.3f} deg, trans spread median {np.median(dt):.2f} mm")
    print(d["tag"], "\n  " + "\n  ".join(res))
