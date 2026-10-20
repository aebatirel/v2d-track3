"""Stage C retry: does temporal smoothing rescue marker-only spoon ROLL at realistic noise (1-2.6 px epipolar residual
measured by notes 11/15)? Smooth random trajectories at 20 fps; per frame, triangulate M1-M3 (c_track geometry) and Kabsch;
compare raw per-frame poses with poses from Savitzky-Golay-smoothed (quadratic) marker tracks.
Usage: c2_smooth.py [ntraj]  -> stdout (redirect to out/c2_smooth.log)"""
import sys, json, numpy as np
from scipy.signal import savgol_filter
from scipy.ndimage import gaussian_filter1d
from scipy.spatial.transform import Rotation as Rot
sys.path.insert(0, "/Users/aebatirel/Documents/Code/v2d-research/work/13/scripts")
import c_track as ct

rng = np.random.default_rng(13)
NT = int(sys.argv[1]) if len(sys.argv) > 1 else 40
T, DT = 200, 0.05


def trajectory(w_rms_deg):
    w = gaussian_filter1d(rng.normal(size=(T, 3)), 5, axis=0)
    w *= np.radians(w_rms_deg) / np.sqrt((w ** 2).sum(1).mean())
    R = [Rot.random(random_state=rng.integers(1 << 31)).as_matrix()]
    for k in range(T - 1):
        R.append(Rot.from_rotvec(w[k] * DT).as_matrix() @ R[-1])
    v = gaussian_filter1d(rng.normal(size=(T, 3)), 5, axis=0)
    v *= 0.20 / np.sqrt((v ** 2).sum(1).mean())
    t = np.array([0.0, 0.0, 0.52]) + np.cumsum(v * DT, 0)
    t = np.clip(t, [-0.15, -0.10, 0.35], [0.15, 0.10, 0.70])
    return np.array(R), t


def observe(R, t, cams, sig):
    P = np.empty((T, 3, 3))
    for k in range(T):
        W = ct.M @ R[k].T + t[k]
        for j, X in enumerate(W):
            uvs = [np.array(ct.project(X, cm)) + sig * rng.normal(size=2) for cm in cams]
            P[k, j] = ct.triangulate(uvs, cams)
    return P


def score(R, t, P):
    out = []
    for k in range(T):
        Re, te = ct.kabsch(ct.M, P[k])
        out.append(ct.errs(R[k], t[k], Re, te))
    return np.array(out)


def summ(o):
    return dict(rot_med=np.median(o[:, 0]), roll_med=np.median(o[:, 2]), roll_p90=np.percentile(o[:, 2], 90),
                tilt_med=np.median(o[:, 1]), pos_med_mm=np.median(o[:, 3]), mppe_med_cm=np.median(o[:, 5]),
                frac_rot_gt30=float(np.mean(o[:, 0] > 30)), frac_rot_gt0p5rad=float(np.mean(o[:, 0] > 28.65)))


if __name__ == "__main__":
    configs = [("b+c", ["b", "c"], 1.0), ("b+c", ["b", "c"], 2.0), ("b+c", ["b", "c"], 2.6), ("a+b+c", ["a", "b", "c"], 1.0),
               ("a+b+c", ["a", "b", "c"], 2.0)]
    for w_rms in (60.0, 180.0):
        for nm, cams, sig in configs:
            acc = {}
            for _ in range(NT):
                R, t = trajectory(w_rms); P = observe(R, t, cams, sig)
                acc.setdefault("raw", []).append(score(R, t, P))
                for win in (5, 9, 15):
                    Ps = savgol_filter(P, win, 2, axis=0, mode="interp")
                    acc.setdefault(f"sg{win}", []).append(score(R, t, Ps))
            for k, v in acc.items():
                s = summ(np.vstack(v))
                print(f"w_rms {w_rms:.0f} deg/s {nm} sig {sig} {k}", json.dumps({a: round(float(b), 3) for a, b in s.items()}), flush=True)
