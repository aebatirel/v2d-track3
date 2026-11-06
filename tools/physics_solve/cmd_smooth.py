"""Zero-lag smoothing of a reference's ROBOT targets (2026-10-31; physics-solver.md section 11, keen-heisenberg's
[H-cmdsmooth]). Constant-velocity Kalman filter + RTS backward pass per channel (keen-heisenberg's all20.py kf model),
at the reference fps, with measurement sigma SIG and process q Q for the wrist position (defaults 5 mm, 4.0); the wrist
quaternion components (sign-continuous, renormalised) and finger joints use the same q / sigma^2 ratio (same bandwidth;
the smoother is scale-free at a fixed ratio). Frame 0 is pinned to the original (the reset pose) and the frame-0
offset is blended out over frames 1-4. Only robot_{left,right}_{wrist_position, wrist_wxyz, finger_joints} change;
everything else (object path, robot_*_frames, MANO fields) is copied. Our reference only; no ground truth.
Usage: cmd_smooth.py REF.parquet OUT.parquet [--sig 0.005 --q 4.0] [--json STATS.json]"""
import argparse, json

import numpy as np
import pyarrow as pa, pyarrow.parquet as pq


def rts(z, dt, ratio):
    """z (T, D) -> RTS-smoothed (T, D); constant-velocity model, measurement variance 1, process q = ratio."""
    T, D = z.shape; F = np.array([[1.0, dt], [0.0, 1.0]]); Q = ratio * np.array([[dt ** 3 / 3, dt ** 2 / 2], [dt ** 2 / 2, dt]])
    out = np.zeros_like(z)
    for a in range(D):
        x = np.array([z[0, a], 0.0]); P = np.diag([1.0, 1.0e6]); xs, Ps, xp, Pp = [], [], [], []
        for t in range(T):
            if t > 0:
                x = F @ x; P = F @ P @ F.T + Q
            xp.append(x.copy()); Pp.append(P.copy())
            k = P[:, 0] / (P[0, 0] + 1.0); x = x + k * (z[t, a] - x[0]); P = P - np.outer(k, P[0, :])
            xs.append(x.copy()); Ps.append(P.copy())
        for t in range(T - 2, -1, -1):
            C = Ps[t] @ F.T @ np.linalg.inv(Pp[t + 1]); xs[t] = xs[t] + C @ (xs[t + 1] - xp[t + 1]); Ps[t] = Ps[t] + C @ (Ps[t + 1] - Pp[t + 1]) @ C.T
        out[:, a] = [s[0] for s in xs]
    return out


def pin0(orig, sm, n=5):
    d = orig[0] - sm[0]; w = np.clip(1.0 - np.arange(len(sm)) / n, 0.0, 1.0)[:, None]
    out = sm + w * d[None]; out[0] = orig[0]                       # frame 0 exactly the original (the reset pose)
    return out


def main():
    p = argparse.ArgumentParser(); p.add_argument('ref'); p.add_argument('out')
    p.add_argument('--sig', type=float, default=0.005); p.add_argument('--q', type=float, default=4.0); p.add_argument('--json', default='')
    a = p.parse_args()
    t = pq.read_table(a.ref); fps = float(t.column('fps')[0].as_py()) if 'fps' in t.column_names else 20.0
    dt, ratio = 1.0 / fps, a.q / a.sig ** 2; stats = dict(fps=fps, sig=a.sig, q=a.q, ratio=ratio)
    for s in ('left', 'right'):
        for col, kind in ((f'robot_{s}_wrist_position', 'pos'), (f'robot_{s}_wrist_wxyz', 'quat'), (f'robot_{s}_finger_joints', 'fin')):
            v = np.array(t.column(col)[0].as_py(), float); shape = v.shape; z = v.reshape(shape[0], -1).copy()
            if kind == 'quat':
                for k in range(1, len(z)):
                    if np.dot(z[k], z[k - 1]) < 0:
                        z[k] = -z[k]
            sm = pin0(z, rts(z, dt, ratio))
            if kind == 'quat':
                sm /= np.linalg.norm(sm, axis=1, keepdims=True)
                if np.dot(sm[0], v.reshape(shape[0], -1)[0]) < 0:
                    sm = -sm
                sm[0] = v.reshape(shape[0], -1)[0]
            hf = lambda x: float(np.sqrt(np.mean(np.sum(np.diff(x, 2, axis=0) ** 2, axis=1))))  # noqa: E731  (2nd-difference RMS)
            stats[col] = dict(change_rms=float(np.sqrt(np.mean(np.sum((sm - z) ** 2, axis=1)))), change_max=float(np.abs(sm - z).max()),
                              d2_rms_before=hf(z), d2_rms_after=hf(sm), frame0_equal=bool(np.array_equal(sm[0], v.reshape(shape[0], -1)[0])))
            i = t.column_names.index(col)
            t = t.set_column(i, col, pa.array([sm.reshape(shape).tolist()], type=t.schema.field(col).type))
    pq.write_table(t, a.out)
    if a.json:
        json.dump(stats, open(a.json, 'w'), indent=1)
    print(json.dumps({k: (round(v['change_rms'], 5), round(v['d2_rms_before'], 5), round(v['d2_rms_after'], 5)) for k, v in stats.items() if isinstance(v, dict)}))


if __name__ == '__main__':
    main()
