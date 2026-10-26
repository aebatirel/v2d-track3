"""Pivot path offset from the object frame, hand COM offset c=6.5 cm from the pivot (URDF), object COM at object frame.
Translational force = M_hand a_handCOM + m a_obj + m g z ; damping on pivot velocity. Random directions, 5 seeds."""
import sys, importlib.util, numpy as np
from scipy.signal import savgol_filter
from scipy.spatial.transform import Rotation as Rot
spec = importlib.util.spec_from_file_location("sens", sys.argv[3]); S = importlib.util.module_from_spec(spec)
sys.argv = sys.argv[:3]; spec.loader.exec_module(S)
dt, G = S.dt, 9.81
def sg(x, d=0): return savgol_filter(x, 9, 2, deriv=d, delta=dt, axis=0)
for dw in (0.0, 0.10):
    for cmag in (0.0, 0.065):
        out = []
        for seed in range(5):
            rng = np.random.default_rng(seed); nt = 0; ntot = 0; frs = []; nt100 = 0; nt50 = 0
            for tr in S.TR:
                x, q = tr["x"], tr["q"]
                qn = q / np.linalg.norm(q, axis=1, keepdims=True)
                Rm = Rot.from_quat(np.concatenate([qn[:, 1:], qn[:, :1]], 1))
                d = rng.normal(size=3); d *= dw / max(np.linalg.norm(d), 1e-9)
                c = rng.normal(size=3); c *= cmag / np.linalg.norm(c)
                pw = x + Rm.apply(d); ph = pw + Rm.apply(c)
                vw = sg(pw, 1); ah = sg(ph, 2); ao = sg(x, 2)
                w = savgol_filter(S.cm.ang_vel(q.copy()), 9, 2, axis=0)
                mov = (np.linalg.norm(sg(x, 1), axis=1) > 0.05) | (np.linalg.norm(w, axis=1) > np.radians(30))
                if mov.sum() < 5: continue
                ntot += 1
                for kp, kd, tag in [(25, 6.0, "d"), (50, 8.485, "50"), (100, 12.0, "100")]:
                    F = 1.243 * ah + 0.3 * ao; F[:, 2] += 0.3 * G
                    r = np.abs((F + kd * vw) / kp)[mov]
                    s = r.max(1) > 0.2
                    if tag == "d": nt += s.any(); frs.append((s.sum(), mov.sum()))
                    elif tag == "50": nt50 += s.any()
                    else: nt100 += s.any()
            fr = 100 * sum(a for a, b in frs) / sum(b for a, b in frs)
            out.append((int(nt), round(fr, 2), int(nt50), int(nt100)))
        print(f"pivot offset {dw:.2f} m, hand COM offset {cmag:.3f} m: (default tracks, default %, kp50 tracks, kp100 tracks) per seed {out}")
