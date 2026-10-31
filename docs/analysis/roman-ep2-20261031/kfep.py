"""Roman's proposal on public ep2: one Kalman filter per object, constant-velocity model on 6 DoF (position + rotation
vector relative to frame 0), process noise gated by hand contact (still when no hand is near, free when held), run at
three observation-noise levels; plus an offline RTS smoother. Scored against public mocap after the same world fit and
constant body offset as lagnoise.py (DIAGNOSTIC: mocap is read only for scoring and plotting).
Writes JSON stats and an npz of every series for the video.
Usage: kfep.py POSES_WORLD_VO.npz HANDS_REFINED.npz EP.parquet MESHDIR OUT_PREFIX
"""
import json, sys
import numpy as np
import pyarrow.parquet as pq
import trimesh
from scipy.spatial.transform import Rotation as R

sys.path.insert(0, __file__.rsplit('/', 1)[0])
from lagnoise import decompose, moving_mask, rigid  # noqa: E402

FPS = 20.0; DT = 1 / FPS
wnpz, hnpz, parquet, meshdir, out = sys.argv[1:6]
W = np.load(wnpz); names = list(W.files); H = np.load(hnpz)
rows = pq.read_table(parquet, columns=['observation.objects']).column('observation.objects').to_pylist()
T = min(len(rows), W[names[0]].shape[0])
G = {n: np.zeros((T, 4, 4)) for n in names}
for t in range(T):
    d = {str(o['name']): np.asarray(o['pose'], float) for o in rows[t]}
    for n in names:
        q = d[n]; M = np.eye(4); M[:3, :3] = R.from_quat([q[4], q[5], q[6], q[3]]).as_matrix(); M[:3, 3] = q[:3]; G[n][t] = M
O = {n: W[n][:T].astype(float) for n in names}

# world fit + constant body offsets (as lagnoise.perception)
k4 = np.array([[0, 0, 0], [.05, 0, 0], [0, .05, 0], [0, 0, .05]]); X = {n: np.eye(4) for n in names}
for _ in range(8):
    src = np.concatenate([np.einsum('tij,kj->tki', (O[n] @ X[n])[:, :3, :3], k4) + (O[n] @ X[n])[:, None, :3, 3] for n in names]).reshape(-1, 3)
    dst = np.concatenate([np.einsum('tij,kj->tki', G[n][:, :3, :3], k4) + G[n][:, None, :3, 3] for n in names]).reshape(-1, 3)
    keep = np.ones(len(src), bool)
    for _ in range(5):
        Rm, tv = rigid(src[keep], dst[keep]); dd = np.linalg.norm(src @ Rm.T + tv - dst, axis=1); keep = dd <= np.quantile(dd, 0.8)
    Wf = np.eye(4); Wf[:3, :3] = Rm; Wf[:3, 3] = tv
    for n in names:
        A = np.linalg.inv(Wf @ O[n]) @ G[n]
        X[n] = np.eye(4); X[n][:3, :3] = R.from_matrix(A[:, :3, :3]).mean().as_matrix(); X[n][:3, 3] = np.median(A[:, :3, 3], 0)

# contact gate from OUR hand keypoints (inference-side): any hand keypoint within the object's radius + 3 cm
rad = {}
for n in names:
    m = trimesh.load(f'{meshdir}/{n}.glb', force='mesh'); rad[n] = float(np.linalg.norm(m.vertices - m.vertices.mean(0), axis=1).max())
J = [H[f'joints_{s}'][:T] for s in ('left', 'right')]; V = [H[f'valid_{s}'][:T].astype(bool) for s in ('left', 'right')]
held = {}
for n in names:  # a hand keypoint within 3.5 cm of the object's tracked surface (300 mesh vertices)
    m = trimesh.load(f'{meshdir}/{n}.glb', force='mesh'); vs = np.asarray(m.vertices)[::max(1, len(m.vertices) // 300)]
    Vw = np.einsum('tij,kj->tki', O[n][:, :3, :3], vs) + O[n][:, None, :3, 3]
    near = np.zeros(T, bool)
    for j, v in zip(J, V):
        dmin = np.linalg.norm(j[:, :, None, :] - Vw[:, None, :, :], axis=3).min(axis=(1, 2)); near |= v & (dmin < 0.035)
    held[n] = near


def kf(z, gate, sig, q_free, q_still, smooth=False):
    """Per-axis constant-velocity Kalman filter (+ optional RTS smoother). z (T, D); gate (T,) True = held."""
    T_, D = z.shape; F = np.array([[1, DT], [0, 1]]); Hm = np.array([[1.0, 0.0]])
    out = np.zeros_like(z)
    for a in range(D):
        x = np.array([z[0, a], 0.0]); P = np.diag([sig ** 2, 1.0]); xs, Ps, xp_l, Pp_l = [], [], [], []
        for t in range(T_):
            q = q_free if gate[t] else q_still
            Q = q * np.array([[DT ** 3 / 3, DT ** 2 / 2], [DT ** 2 / 2, DT]])
            if t > 0:
                x = F @ x; P = F @ P @ F.T + Q
            xp_l.append(x.copy()); Pp_l.append(P.copy())
            S = Hm @ P @ Hm.T + sig ** 2; K = P @ Hm.T / S
            x = x + (K * (z[t, a] - Hm @ x)).ravel(); P = (np.eye(2) - K @ Hm) @ P
            xs.append(x.copy()); Ps.append(P.copy())
        if smooth:
            for t in range(T_ - 2, -1, -1):
                C = Ps[t] @ F.T @ np.linalg.inv(Pp_l[t + 1])
                xs[t] = xs[t] + C @ (xs[t + 1] - xp_l[t + 1]); Ps[t] = Ps[t] + C @ (Ps[t + 1] - Pp_l[t + 1]) @ C.T
        out[:, a] = [s[0] for s in xs]
    return out


def pose_series(Tm, R0):  # (T,4,4) -> position (T,3) m, rotation vector relative to R0 (T,3) rad, unwrapped
    return Tm[:, :3, 3], (R.from_matrix(R0).inv() * R.from_matrix(Tm[:, :3, :3])).as_rotvec()


def from_series(p, rv, R0):
    Tm = np.tile(np.eye(4), (len(p), 1, 1)); Tm[:, :3, :3] = (R.from_matrix(R0) * R.from_rotvec(rv)).as_matrix(); Tm[:, :3, 3] = p
    return Tm


def score(Tours, Gn):  # position RMS cm, rotation median deg, ADD on a 5 cm sphere (mean cm) vs mocap
    rng = np.random.default_rng(0); P = rng.normal(size=(200, 3)); P = 0.05 * P / np.linalg.norm(P, axis=1, keepdims=True)
    a = np.einsum('tij,kj->tki', Tours[:, :3, :3], P) + Tours[:, None, :3, 3]; b = np.einsum('tij,kj->tki', Gn[:, :3, :3], P) + Gn[:, None, :3, 3]
    rot = (R.from_matrix(Tours[:, :3, :3]).inv() * R.from_matrix(Gn[:, :3, :3])).magnitude() * 180 / np.pi
    return dict(pos_rms_cm=round(float(np.sqrt((np.linalg.norm(Tours[:, :3, 3] - Gn[:, :3, 3], axis=1) ** 2).mean()) * 100), 3),
                rot_median_deg=round(float(np.median(rot)), 3), add_mean_cm=round(float(np.linalg.norm(a - b, axis=2).mean() * 100), 3))


LEVELS = {'low': (0.001, 0.2), 'medium': (0.003, 0.6), 'high': (0.010, 2.0)}  # observation sigma: (m, deg)
stats = {}; save = {}
for n in names:
    A = Wf @ O[n] @ X[n]; R0 = A[0, :3, :3]; p, rv = pose_series(A, R0)
    gp, grv = pose_series(G[n], R0)
    s = {'held_frames': int(held[n].sum()), 'raw': score(A, G[n])}
    save[f'{n}_raw_p'] = p; save[f'{n}_raw_r'] = rv; save[f'{n}_gt_p'] = gp; save[f'{n}_gt_r'] = grv; save[f'{n}_held'] = held[n]
    for lv, (sp, sr) in LEVELS.items():
        pf = kf(p, held[n], sp, q_free=4.0, q_still=1e-4); rf = kf(rv, held[n], np.deg2rad(sr), q_free=40.0, q_still=1e-3)
        Af = from_series(pf, rf, R0); s[f'kf_{lv}'] = score(Af, G[n])
        s[f'kf_{lv}']['delay_frames'] = decompose(pf, gp, moving_mask(gp))['best_delay_frames']
        save[f'{n}_kf_{lv}_p'] = pf; save[f'{n}_kf_{lv}_r'] = rf
    pf = kf(p, held[n], LEVELS['medium'][0], 4.0, 1e-4, smooth=True); rf = kf(rv, held[n], np.deg2rad(LEVELS['medium'][1]), 40.0, 1e-3, smooth=True)
    s['rts_medium'] = score(from_series(pf, rf, R0), G[n]); s['rts_medium']['delay_frames'] = decompose(pf, gp, moving_mask(gp))['best_delay_frames']
    save[f'{n}_rts_p'] = pf; save[f'{n}_rts_r'] = rf
    s['raw']['delay_frames'] = decompose(p, gp, moving_mask(gp))['best_delay_frames']
    # half-frame advance (the adopted S2 step) for comparison
    t = np.arange(T); sh = np.clip(t + 0.545, 0, T - 1)
    ps = np.stack([np.interp(sh, t, p[:, a]) for a in range(3)], 1); rs = np.stack([np.interp(sh, t, rv[:, a]) for a in range(3)], 1)
    s['raw_advanced_0.545'] = score(from_series(ps, rs, R0), G[n])
    stats[n] = s
save['Wf'] = Wf; save['names'] = np.array(names)
for n in names:
    save[f'{n}_X'] = X[n]
np.savez(f'{out}_series.npz', **save)
json.dump(stats, open(f'{out}_kf.json', 'w'), indent=1)
print(json.dumps(stats, indent=1))
