"""Delay or noise? Decompose a pose error time series into constant offset, delay, slow drift and high-frequency noise.
Layer R (robot): evaluator rollouts, simulated object vs our reference, same parquet, same frame (no ground truth).
Layer P (perception): our tracked object poses vs public mocap (DIAGNOSTIC, public ep only), after a robust rigid world
fit and a constant body offset per object (both fitted to mocap: an upper bound of what a constant correction removes).
Usage: lagnoise.py rollouts DIR...    |   lagnoise.py perception POSES_WORLD_VO.npz EP.parquet
"""
import glob, json, sys
import numpy as np
import pyarrow.parquet as pq
from scipy.signal import savgol_filter
from scipy.spatial.transform import Rotation as R, Slerp

FPS = 20.0


def shift(P, tau):  # P (T,3) sampled at frames 0..T-1 -> P(t - tau) by linear interpolation (tau > 0 = delayed copy)
    t = np.arange(len(P)); s = np.clip(t - tau, 0, len(P) - 1)
    return np.stack([np.interp(s, t, P[:, k]) for k in range(3)], 1)


def decompose(Pa, Pr, moving):
    """Pa achieved/ours, Pr reference/truth, (T,3) m. Returns cm numbers. moving: frames where the reference moves."""
    e = Pa - Pr
    const = e.mean(0)
    rms_total = np.sqrt((np.linalg.norm(e, axis=1) ** 2).mean())
    e0 = e - const
    # best constant delay, searched in 0.05-frame steps over +-10 frames, on moving frames (where a delay can show)
    taus = np.arange(-10, 10.001, 0.05); m = moving if moving.sum() >= 10 else np.ones(len(e), bool)
    def rms_shift(tau):  # tau > 0: the achieved path lags the reference by tau frames (Pa(t + tau) = Pr(t))
        d = (shift(Pa, -tau) - Pr)[m]; d = d - d.mean(0)
        return np.sqrt((np.linalg.norm(d, axis=1) ** 2).mean())
    errs = [rms_shift(tau) for tau in taus]
    k = int(np.argmin(errs)); tau = taus[k]
    rms_moving_nolag = np.sqrt((np.linalg.norm((Pa - Pr)[m] - (Pa - Pr)[m].mean(0), axis=1) ** 2).mean())
    e_l = shift(Pa, -tau) - Pr; e_l = e_l - e_l.mean(0)
    w = 9 if len(e) > 20 else 5
    low = savgol_filter(e_l, w, 2, axis=0); high = e_l - low
    return dict(rms_total_cm=round(rms_total * 100, 2), const_cm=round(float(np.linalg.norm(const)) * 100, 2),
                rms_varying_cm=round(float(np.sqrt((np.linalg.norm(e0, axis=1) ** 2).mean())) * 100, 2),
                best_delay_frames=round(float(tau), 2), best_delay_ms=round(float(tau) / FPS * 1000, 0),
                moving_rms_no_shift_cm=round(float(rms_moving_nolag) * 100, 2), moving_rms_best_shift_cm=round(float(errs[k]) * 100, 2),
                slow_drift_rms_cm=round(float(np.sqrt((np.linalg.norm(low, axis=1) ** 2).mean())) * 100, 2),
                noise_rms_cm=round(float(np.sqrt((np.linalg.norm(high, axis=1) ** 2).mean())) * 100, 2),
                frames=int(len(e)), moving_frames=int(m.sum()))


def moving_mask(Pr, thr_cm_s=2.0):
    v = np.r_[0, np.linalg.norm(np.diff(Pr, axis=0), axis=1)] * FPS * 100
    return v > thr_cm_s


def rollouts(dirs):
    out = {}
    for f in sorted(sum([glob.glob(f'{d}/**/episode_*.parquet', recursive=True) for d in dirs], [])):
        t = pq.read_table(f).to_pydict(); st = np.array(t['step']); oid = np.array(t['object_id'])
        T, B = st.max() + 1, oid.max() + 1; A = np.zeros((T, B, 3)); F = np.zeros((T, B, 3)); names = [None] * B
        for i in range(len(st)):
            A[st[i], oid[i]] = [t[f'achieved_position_{c}'][i] for c in 'xyz']
            F[st[i], oid[i]] = [t[f'reference_position_{c}'][i] for c in 'xyz']; names[oid[i]] = t['object_body_name'][i]
        out[f] = {n: decompose(A[:, b], F[:, b], moving_mask(F[:, b])) for b, n in enumerate(names)}
    return out


def rigid(src, dst):  # Kabsch src -> dst
    cs, cd = src.mean(0), dst.mean(0); U, _, Vt = np.linalg.svd((src - cs).T @ (dst - cd))
    D = np.diag([1, 1, np.sign(np.linalg.det(Vt.T @ U.T))]); Rm = Vt.T @ D @ U.T
    return Rm, cd - Rm @ cs


def perception(world_npz, parquet):
    W = np.load(world_npz); names = [n for n in W.files]
    rows = pq.read_table(parquet, columns=['observation.objects']).column('observation.objects').to_pylist()
    T = min(len(rows), W[names[0]].shape[0])
    G = {n: np.zeros((T, 4, 4)) for n in names}
    for t in range(T):
        d = {str(o['name']): np.asarray(o['pose'], float) for o in rows[t]}
        for n in names:
            q = d[n]; M = np.eye(4); M[:3, :3] = R.from_quat([q[4], q[5], q[6], q[3]]).as_matrix(); M[:3, 3] = q[:3]; G[n][t] = M
    O = {n: W[n][:T].astype(float) for n in names}
    # alternate: world fit Wf (ours world -> mocap world) on object keypoints, then per-object constant body offset X
    k = np.array([[0, 0, 0], [.05, 0, 0], [0, .05, 0], [0, 0, .05]])
    X = {n: np.eye(4) for n in names}; Wf = np.eye(4)
    for _ in range(8):
        src = np.concatenate([np.einsum('tij,kj->tki', (O[n] @ X[n])[:, :3, :3], k) + (O[n] @ X[n])[:, None, :3, 3] for n in names]).reshape(-1, 3)
        dst = np.concatenate([np.einsum('tij,kj->tki', G[n][:, :3, :3], k) + G[n][:, None, :3, 3] for n in names]).reshape(-1, 3)
        keep = np.ones(len(src), bool)
        for _ in range(5):
            Rm, tv = rigid(src[keep], dst[keep]); d = np.linalg.norm(src @ Rm.T + tv - dst, axis=1); keep = d <= np.quantile(d, 0.8)
        Wf = np.eye(4); Wf[:3, :3] = Rm; Wf[:3, 3] = tv
        for n in names:  # X = mean over t of inv(Wf O_t) G_t
            A = np.linalg.inv(Wf @ O[n]) @ G[n]
            X[n] = np.eye(4); X[n][:3, :3] = R.from_matrix(A[:, :3, :3]).mean().as_matrix(); X[n][:3, 3] = np.median(A[:, :3, 3], 0)
    res = {}
    for n in names:
        Pa = (Wf @ O[n] @ X[n])[:, :3, 3]; Pr = G[n][:, :3, 3]
        Pa0 = (Wf @ O[n])[:, :3, 3]  # without the fitted body offset: shows the constant part
        r = decompose(Pa, Pr, moving_mask(Pr))
        r['constant_body_offset_cm_removed'] = round(float(np.linalg.norm(Pa0 - Pa, axis=1).mean()) * 100, 2)
        rot = (R.from_matrix((Wf @ O[n] @ X[n])[:, :3, :3]).inv() * R.from_matrix(G[n][:, :3, :3])).magnitude() * 180 / np.pi
        r['rot_err_deg_median'] = round(float(np.median(rot)), 2); r['rot_err_deg_p90'] = round(float(np.quantile(rot, 0.9)), 2)
        res[n] = r
    return res


if __name__ == '__main__':
    if sys.argv[1] == 'rollouts':
        print(json.dumps(rollouts(sys.argv[2:]), indent=1))
    else:
        print(json.dumps(perception(sys.argv[2], sys.argv[3]), indent=1))
