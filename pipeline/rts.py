"""Refine step S13 (31 Oct 2026, perception sprint "rts") [H until its public gate]: zero-lag Rauch-Tung-Striebel
smoother on each object's world-frame POSITION; rotations are not changed. GROUND-TRUTH-FREE: it reads only our track
(the output of the earlier refine steps, S2 in the gated chain), our hands (refine's hands file: joints_<side>,
valid_<side>) and our meshes (library_v3), all through refine's checked inputs.
Pre-registration and results: docs/research/work/perception-sprint-20261031/rts/PREREG.md, README.md.
Reference (diagnostic, mocap-tuned, session keen-heisenberg): docs/analysis/roman-ep2-20261031/all20.py kf(...,
smooth=True), rtssweep.py prep (hand gate), cvsmooth.py (parameter choice), on branch claude/keen-heisenberg-engcwz.

Per object, per world axis x, y, z independently (same model on every axis, so it commutes with world rotations):
  model     state [p, v], dt = 1 / FPS; F = [[1, dt], [0, 1]]; H = [1, 0]; Q = q [[dt^3/3, dt^2/2], [dt^2/2, dt]]
            (q in m^2/s^3); R = SIGMA^2. q = Q_NEAR on frames where a hand is near the object, Q_FAR otherwise (the q
            of frame t is used in the prediction t-1 -> t). x0 = [p(0), 0], P0 = diag(SIGMA^2, 1).
  smoother  forward Kalman pass over all frames, then the RTS backward pass t = T-2 .. 0; p(t) := smoothed position.
            The covariance recursion does not depend on the data and the model is the same on every axis, so one
            covariance sequence serves the three axes (numerically the reference's per-axis loop; unit test).
  position  the translation O(t)[:3, 3] of the world pose (our mesh-frame origin); O(t)[:3, :3] is kept byte-identical.
  hand gate near(t) = min over the 21 joints of each hand with valid_<side>(t) (world frame) and over our mesh's
            vertices (trimesh.load(..., force='mesh'), every len(V) // VERTS-th) posed by the step's input track at t,
            of the distance, < NEAR_M. No hands file: no frame is near.
Frame 0 is not held (as S2). Fewer than 2 frames: skipped.
"""
import hashlib
import os

import numpy as np


def cv_noise(dt):
    """Constant-velocity (white-acceleration) process noise per unit q."""
    return np.array([[dt ** 3 / 3, dt ** 2 / 2], [dt ** 2 / 2, dt]])


def rts_smooth(z, near, sigma, q_near, q_far, dt):
    """Zero-lag RTS smoothing of z (T, D) (each column independently, same model); near (T,) bool selects q per frame.
    Returns the smoothed positions (T, D) float64."""
    z = np.asarray(z, np.float64)
    T, D = z.shape
    F = np.array([[1.0, dt], [0.0, 1.0]])
    Hm = np.array([[1.0, 0.0]])
    Qu = cv_noise(dt)
    r = sigma ** 2
    I2 = np.eye(2)
    xs = np.zeros((T, 2, D))
    xp = np.zeros((T, 2, D))
    Ps = np.zeros((T, 2, 2))
    Pp = np.zeros((T, 2, 2))
    x = np.stack([z[0], np.zeros(D)])
    P = np.diag([r, 1.0])
    for t in range(T):
        if t > 0:
            Q = (q_near if near[t] else q_far) * Qu
            x = F @ x
            P = F @ P @ F.T + Q
        xp[t] = x
        Pp[t] = P
        S = Hm @ P @ Hm.T + r                                      # (1, 1)
        K = P @ Hm.T / S                                           # (2, 1)
        x = x + K * (z[t][None, :] - Hm @ x)                       # (2, D)
        P = (I2 - K @ Hm) @ P
        xs[t] = x
        Ps[t] = P
    for t in range(T - 2, -1, -1):
        C = Ps[t] @ F.T @ np.linalg.inv(Pp[t + 1])
        xs[t] = xs[t] + C @ (xs[t + 1] - xp[t + 1])
        Ps[t] = Ps[t] + C @ (Ps[t + 1] - Pp[t + 1]) @ C.T
    return xs[:, 0, :]


def gate_vertices(mesh_path, verts=300):
    """Our mesh's vertices as the reference gate loads them, every len(V) // verts-th."""
    import trimesh
    V = np.asarray(trimesh.load(mesh_path, force='mesh').vertices, np.float64)
    return V[::max(1, len(V) // verts)]


def hand_near(Ot, V, Jh, Vh, near_m):
    """near (T,) bool and the nearest valid-joint-to-vertex distance (T,) in m (inf: no valid hand or non-finite)."""
    T = len(Ot)
    dmin = np.full(T, np.inf)
    Vw = np.einsum('tij,kj->tki', Ot[:, :3, :3], V) + Ot[:, None, :3, 3]
    for s in Jh:
        for t in np.nonzero(Vh[s])[0]:
            d = np.linalg.norm(Jh[s][t][:, None, :] - Vw[t][None, :, :], axis=2).min()
            if np.isfinite(d) and d < dmin[t]:
                dmin[t] = d
    return dmin < near_m, dmin


def hands_of(H, T):
    """joints_<side> (T, 21, 3) float64 and valid_<side> (T,) bool from refine's hands file (measured_<side> if a file has
    no valid_<side>); {} without a hands file."""
    Jh, Vh, keys = {}, {}, {}
    if H is None:
        return Jh, Vh, keys
    for s in ('left', 'right'):
        if f'joints_{s}' not in H.files:
            continue
        k = f'valid_{s}' if f'valid_{s}' in H.files else (f'measured_{s}' if f'measured_{s}' in H.files else None)
        J = np.asarray(H[f'joints_{s}'], np.float64)
        if len(J) != T:
            raise SystemExit(f'S13: hands joints_{s} has {len(J)} frames, poses {T}')
        Jh[s] = J
        Vh[s] = np.asarray(H[k], bool) if k else np.zeros(T, bool)
        keys[s] = k
    return Jh, Vh, keys


def step_S13(a, objs, O, H, checked, log=print):
    """Apply S13 on O (list of (T,4,4) world poses; each changed entry is replaced by a new array whose rotation block is
    a byte copy of the input). Returns the record for pose_opt.json (per-frame diagnostics under '_aux')."""
    rec = dict(sigma_m=a.s13_sigma, q_near=a.s13_q_near, q_far=a.s13_q_far, near_m=a.s13_near_m, fps=a.s13_fps,
               verts=a.s13_verts, position='translation of the world pose (mesh-frame origin)', rotation='unchanged',
               rts_sha256=hashlib.sha256(open(os.path.abspath(__file__), 'rb').read()).hexdigest(), objects={})
    T = len(O[0])
    if T < 2:
        rec['skipped'] = f'{T} frame(s)'
        log('S13 skipped:', rec['skipped'])
        return rec
    Jh, Vh, keys = hands_of(H, T)
    rec['hands'] = {s: dict(valid_key=keys[s], valid_frames=int(Vh[s].sum())) for s in Jh} if Jh else 'no hands file: no frame near'
    dt = 1.0 / a.s13_fps
    aux = {}
    for j, o in enumerate(objs):
        V = gate_vertices(checked(o.path), a.s13_verts)
        near, dmin = hand_near(O[j], V, Jh, Vh, a.s13_near_m)
        p = O[j][:, :3, 3].astype(np.float64)
        ps = rts_smooth(p, near, a.s13_sigma, a.s13_q_near, a.s13_q_far, dt)
        new = O[j].copy()
        new[:, :3, 3] = ps
        O[j] = new
        dp = np.linalg.norm(ps - p, axis=1) * 100
        rec['objects'][o.name] = dict(gate_vertices=int(len(V)), near_frames=int(near.sum()),
                                      change_cm_mean=round(float(dp.mean()), 4), change_cm_p90=round(float(np.percentile(dp, 90)), 4),
                                      change_cm_max=round(float(dp.max()), 4), change_cm_max_frame=int(np.argmax(dp)),
                                      f0_change_cm=round(float(dp[0]), 4))
        aux[f'S13_{o.name}_near'] = near
        aux[f'S13_{o.name}_hand_m'] = dmin
        aux[f'S13_{o.name}_change_cm'] = dp
        log(f'S13 {o.name}: near {int(near.sum())}/{T} frames, change mean {dp.mean():.3f} cm, max {dp.max():.3f} cm '
            f'(f{int(np.argmax(dp))}), f0 {dp[0]:.3f} cm')
    rec['_aux'] = aux
    return rec
