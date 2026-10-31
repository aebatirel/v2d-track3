"""Is the half-frame delay (and the small noise) the same in every public episode, and which filter fixes the most?
For each public episode and object: our track (P_o, library_v3 templates) vs public mocap after a robust world fit and
one constant body offset per object (DIAGNOSTIC: mocap is read only for scoring; both fits are upper bounds of a
constant correction, so what is left is the VARYING error the filters can act on).
Variants (all GT-free transforms of our track; only the scoring reads mocap):
  raw; adv = constant advance of 0.545 frames (the refine stage's S2);
  kf_{low,med,high} = causal per-object constant-velocity Kalman, process noise small unless a hand keypoint is within
    3.5 cm of the tracked surface (Roman's model), at three observation-noise levels;
  kfd_med = the same filter predicting 0.545 frames ahead (delay-aware);
  rts_med = offline Rauch-Tung-Striebel smoother; adv_rts = advance, then smoother.
Score: mean ADD (cm) on a 5 cm sphere, per object. Usage: all20.py DATA_DIR MESHDIR OUT.json
"""
import glob, json, os, sys
import numpy as np
import pyarrow.parquet as pq
import trimesh
from scipy.spatial.transform import Rotation as R

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lagnoise import decompose, moving_mask, rigid  # noqa: E402

FPS = 20.0; DT = 1 / FPS; ADV = 0.545
LEVELS = {'low': (0.001, 0.2), 'med': (0.003, 0.6), 'high': (0.010, 2.0)}
rng = np.random.default_rng(0); SPH = rng.normal(size=(200, 3)); SPH = 0.05 * SPH / np.linalg.norm(SPH, axis=1, keepdims=True)


def kf(z, gate, sig, q_free, q_still, smooth=False, lead=0.0):
    T_, D = z.shape; F = np.array([[1, DT], [0, 1]]); Hm = np.array([[1.0, 0.0]]); out = np.zeros_like(z)
    for a in range(D):
        x = np.array([z[0, a], 0.0]); P = np.diag([sig ** 2, 1.0]); xs, Ps, xp_l, Pp_l = [], [], [], []
        for t in range(T_):
            q = q_free if gate[t] else q_still; Q = q * np.array([[DT ** 3 / 3, DT ** 2 / 2], [DT ** 2 / 2, DT]])
            if t > 0:
                x = F @ x; P = F @ P @ F.T + Q
            xp_l.append(x.copy()); Pp_l.append(P.copy())
            S = Hm @ P @ Hm.T + sig ** 2; K = P @ Hm.T / S
            x = x + (K * (z[t, a] - Hm @ x)).ravel(); P = (np.eye(2) - K @ Hm) @ P; xs.append(x.copy()); Ps.append(P.copy())
        if smooth:
            for t in range(T_ - 2, -1, -1):
                C = Ps[t] @ F.T @ np.linalg.inv(Pp_l[t + 1]); xs[t] = xs[t] + C @ (xs[t + 1] - xp_l[t + 1]); Ps[t] = Ps[t] + C @ (Ps[t + 1] - Pp_l[t + 1]) @ C.T
        out[:, a] = [s[0] + s[1] * lead * DT for s in xs]
    return out


def advance(z, d):
    t = np.arange(len(z)); s = np.clip(t + d, 0, len(z) - 1); return np.stack([np.interp(s, t, z[:, a]) for a in range(z.shape[1])], 1)


def qcont(Rm):  # (T,3,3) -> sign-continuous quaternions (T,4), xyzw
    q = R.from_matrix(Rm).as_quat()
    for t in range(1, len(q)):
        if np.dot(q[t], q[t - 1]) < 0:
            q[t] = -q[t]
    return q


def qadvance(q, d):  # slerp-based fractional advance
    t = np.arange(len(q)); s = np.clip(t + d, 0, len(q) - 1); i0 = np.floor(s).astype(int); i1 = np.minimum(i0 + 1, len(q) - 1); f = s - i0
    out = np.zeros_like(q)
    for k in range(len(q)):
        a, b = q[i0[k]], q[i1[k]]; dot = np.clip(np.dot(a, b), -1, 1); w = np.arccos(dot)
        out[k] = a if w < 1e-9 else (np.sin((1 - f[k]) * w) * a + np.sin(f[k] * w) * b) / np.sin(w)
    return out


def add_cm(p, q, R0, Gn):
    Rm = R.from_quat(q / np.linalg.norm(q, axis=1, keepdims=True)).as_matrix()
    a = np.einsum('tij,kj->tki', Rm, SPH) + p[:, None]; b = np.einsum('tij,kj->tki', Gn[:, :3, :3], SPH) + Gn[:, None, :3, 3]
    return float(np.linalg.norm(a - b, axis=2).mean() * 100)


def episode(d, meshdir):
    W = np.load(f'{d}/poses_world_vo.npz'); names = list(W.files); Hh = np.load(f'{d}/hands_refined.npz')
    rows = pq.read_table(glob.glob(f'{d}/ep*.parquet')[0], columns=['observation.objects']).column('observation.objects').to_pylist()
    T = min(len(rows), W[names[0]].shape[0]); G = {n: np.zeros((T, 4, 4)) for n in names}
    for t in range(T):
        dd = {str(o['name']): np.asarray(o['pose'], float) for o in rows[t]}
        for n in names:
            q = dd[n]; M = np.eye(4); M[:3, :3] = R.from_quat([q[4], q[5], q[6], q[3]]).as_matrix(); M[:3, 3] = q[:3]; G[n][t] = M
    O = {n: W[n][:T].astype(float) for n in names}
    k4 = np.array([[0, 0, 0], [.05, 0, 0], [0, .05, 0], [0, 0, .05]]); X = {n: np.eye(4) for n in names}
    for _ in range(8):
        src = np.concatenate([np.einsum('tij,kj->tki', (O[n] @ X[n])[:, :3, :3], k4) + (O[n] @ X[n])[:, None, :3, 3] for n in names]).reshape(-1, 3)
        dst = np.concatenate([np.einsum('tij,kj->tki', G[n][:, :3, :3], k4) + G[n][:, None, :3, 3] for n in names]).reshape(-1, 3)
        keep = np.ones(len(src), bool)
        for _ in range(5):
            Rm, tv = rigid(src[keep], dst[keep]); e = np.linalg.norm(src @ Rm.T + tv - dst, axis=1); keep = e <= np.quantile(e, 0.8)
        Wf = np.eye(4); Wf[:3, :3] = Rm; Wf[:3, 3] = tv
        for n in names:
            A = np.linalg.inv(Wf @ O[n]) @ G[n]; X[n] = np.eye(4); X[n][:3, :3] = R.from_matrix(A[:, :3, :3]).mean().as_matrix(); X[n][:3, 3] = np.median(A[:, :3, 3], 0)
    J = [Hh[f'joints_{s}'][:T] for s in ('left', 'right')]; V = [Hh[f'valid_{s}'][:T].astype(bool) for s in ('left', 'right')]
    res = {}
    for n in names:
        m = trimesh.load(f'{meshdir}/{n}.glb', force='mesh'); vs = np.asarray(m.vertices)[::max(1, len(m.vertices) // 300)]
        Vw = np.einsum('tij,kj->tki', O[n][:, :3, :3], vs) + O[n][:, None, :3, 3]; held = np.zeros(T, bool)
        for j, v in zip(J, V):
            held |= v & (np.linalg.norm(j[:, :, None, :] - Vw[:, None, :, :], axis=3).min(axis=(1, 2)) < 0.035)
        A = Wf @ O[n] @ X[n]; R0 = A[0, :3, :3]; p = A[:, :3, 3]; rv = qcont(A[:, :3, :3])  # quaternion components, filtered per component
        gp = G[n][:, :3, 3]; dec = decompose(p, gp, moving_mask(gp))
        out = dict(held_frames=int(held.sum()), frames=int(T), moving_frames=dec['moving_frames'], delay_frames=dec['best_delay_frames'],
                   noise_cm=dec['noise_rms_cm'], drift_cm=dec['slow_drift_rms_cm'], varying_cm=dec['rms_varying_cm'],
                   const_body_offset_cm=round(float(np.linalg.norm((Wf @ O[n])[:, :3, 3] - p, axis=1).mean() * 100), 2))
        v = {'raw': (p, rv), 'adv': (advance(p, ADV), qadvance(rv, ADV))}
        for lv, (sp, sr) in LEVELS.items():
            v[f'kf_{lv}'] = (kf(p, held, sp, 4.0, 1e-4), kf(rv, held, np.deg2rad(sr) / 2, 10.0, 2.5e-4))
        sp, sr = LEVELS['med']
        v['kfd_med'] = (kf(p, held, sp, 4.0, 1e-4, lead=ADV), kf(rv, held, np.deg2rad(sr) / 2, 10.0, 2.5e-4, lead=ADV))
        v['rts_med'] = (kf(p, held, sp, 4.0, 1e-4, smooth=True), kf(rv, held, np.deg2rad(sr) / 2, 10.0, 2.5e-4, smooth=True))
        pa, ra = v['adv']; v['adv_rts'] = (kf(pa, held, sp, 4.0, 1e-4, smooth=True), kf(ra, held, np.deg2rad(sr) / 2, 10.0, 2.5e-4, smooth=True))
        out['add_cm'] = {k: round(add_cm(pp, rr, R0, G[n]), 4) for k, (pp, rr) in v.items()}
        res[n] = out
    return res


if __name__ == '__main__':
    data, meshdir, outf = sys.argv[1:4]; allr = {}
    for d in sorted(glob.glob(f'{data}/ep*'), key=lambda s: int(s.rsplit('ep', 1)[1])):
        try:
            allr[os.path.basename(d)] = episode(d, meshdir)
        except Exception as e:  # report, do not hide
            allr[os.path.basename(d)] = {'error': repr(e)}
        print(os.path.basename(d), 'done', file=sys.stderr, flush=True)
    json.dump(allr, open(outf, 'w'), indent=1)
