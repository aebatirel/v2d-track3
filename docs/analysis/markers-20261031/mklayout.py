"""Marker layout in OUR body frame, and per-frame labelled marker sets (GT-free).

Inputs: scan.py detections (camera frame) and our perc2 track (cam_T_obj, world_T_cam) for one object over a list
of episodes. Steps:
  1. rest frames from our own track (world-frame centre moves < 6 mm and rotation < 4 deg over +-4 frames);
  2. discovery: body-frame points B = R^T (X - t) of all rest detections, greedy clustering (12 mm); clusters seen in
     >= MIN_SHARE of the rest frames of >= 1 episode are markers;
  3. shape: per rest frame, detections labelled to the nearest cluster (< 15 mm); a generalised Procrustes fit of the
     labelled camera-frame sets gives the rigid marker shape independent of the track (stereo only);
  4. placement: the shape is put into the body frame by a Kabsch fit onto the pooled cluster medians (this averages
     our track's pose over all rest frames of all episodes, so it inherits the track's MEAN bias, not its jitter).
No ground truth, no scan.
"""
import itertools
import numpy as np
from scipy.spatial.transform import Rotation as Rot

MIN_SHARE = 0.25


def kabsch(A, B, w=None):
    """R, t minimising sum w |R A + t - B|^2 (A, B: (n,3))."""
    w = np.ones(len(A)) if w is None else np.asarray(w, float)
    ca, cb = (w[:, None] * A).sum(0) / w.sum(), (w[:, None] * B).sum(0) / w.sum()
    H = ((A - ca) * w[:, None]).T @ (B - cb)
    U, S, Vt = np.linalg.svd(H); d = np.sign(np.linalg.det(Vt.T @ U.T))
    R = Vt.T @ np.diag([1, 1, d]) @ U.T
    return R, cb - R @ ca


def rest_mask(Tw, win=4, pos=0.006, rot=4.0, med=3):
    """our track is still over +-win frames, after a +-med running median (robust to one-frame track outliers such
    as a bad frame 0)."""
    n = len(Tw); out = np.zeros(n, bool); Tw = Tw.copy(); Ts = Tw.copy()
    for t in range(n):
        a, b = max(0, t - med), min(n, t + med + 1)
        Ts[t, :3, 3] = np.median(Tw[a:b, :3, 3], 0)
        Ts[t, :3, :3] = Rot.from_matrix(Tw[a:b, :3, :3]).mean().as_matrix()
    Tw = Ts
    for t in range(n):
        a, b = max(0, t - win), min(n - 1, t + win)
        dp = np.linalg.norm(Tw[a:b + 1, :3, 3] - Tw[t, :3, 3], axis=1).max()
        dr = np.degrees(Rot.from_matrix(np.einsum('tij,kj->tik', Tw[a:b + 1, :3, :3], Tw[t, :3, :3])).magnitude()).max()
        out[t] = dp < pos and dr < rot
    return out


def body_points(dets, T):
    """per frame list of (n,3) body-frame points and (n,3) camera points."""
    out = []
    for t, D in enumerate(dets):
        if not D or t >= len(T):
            out.append((np.zeros((0, 3)), np.zeros((0, 3)))); continue
        X = np.array([d['X'] for d in D]); R, p = T[t][:3, :3], T[t][:3, 3]
        out.append(((X - p) @ R, X))
    return out


def discover(B_list, rest_list, radius=0.012, min_share=MIN_SHARE):
    """greedy clustering of body-frame rest points pooled over episodes; returns (k,3) medians and support shares."""
    pts, src = [], []
    for e, (BL, rest) in enumerate(zip(B_list, rest_list)):
        for t, (B, _) in enumerate(BL):
            if rest[t] and len(B):
                pts.append(B); src += [(e, t)] * len(B)
    P = np.concatenate(pts); src = np.array(src)
    nrest = [max(1, int(r.sum())) for r in rest_list]
    alive = np.ones(len(P), bool); out = []
    while alive.sum() > 5:
        idx = np.nonzero(alive)[0]
        D = np.linalg.norm(P[idx, None] - P[None, idx], axis=2)
        cnt = (D < radius).sum(1); i = idx[np.argmax(cnt)]
        mem = idx[np.linalg.norm(P[idx] - P[i], axis=1) < radius]
        c = np.median(P[mem], 0)
        mem = idx[np.linalg.norm(P[idx] - c, axis=1) < radius]; c = np.median(P[mem], 0)
        share = max(len(set(map(tuple, src[mem][src[mem][:, 0] == e]))) / nrest[e] for e in range(len(nrest)))
        alive[mem] = False
        if share < min_share:
            if len(mem) < 3:
                break
            continue
        out.append((c, share, len(mem)))
    out.sort(key=lambda x: -x[1])
    return np.array([o[0] for o in out]), [round(o[1], 3) for o in out], [o[2] for o in out]


def label(B, C, tol=0.015):
    """assign body-frame points B (n,3) to cluster centres C (k,3): dict marker -> detection index (unique)."""
    if not len(B):
        return {}
    D = np.linalg.norm(B[:, None] - C[None], axis=2); lab = {}
    for i, k in sorted(((i, k) for i in range(len(B)) for k in range(len(C)) if D[i, k] < tol), key=lambda x: D[x]):
        if k not in lab and i not in lab.values():
            lab[k] = i
    return lab


def gpa(sets, k, iters=10):
    """generalised Procrustes over partial labelled sets [(dict marker->(3,)), ...] -> (k,3) shape, residual stats."""
    full = [s for s in sets if len(s) == k]
    if not full:
        return None, None
    S = np.array([full[0][j] for j in range(k)]); S = S - S.mean(0)      # first guess: one complete set
    for _ in range(iters):
        acc = [[] for _ in range(k)]
        for s in sets:
            if len(s) < 3:
                continue
            ks = sorted(s); A = np.array([s[j] for j in ks])
            R, t = kabsch(A, S[ks])
            for j, a in zip(ks, A @ R.T + t):
                acc[j].append(a)
        S_new = np.array([np.median(a, 0) if a else S[j] for j, a in enumerate(acc)])
        S = S_new - S_new.mean(0)
    res = []
    for s in sets:
        if len(s) < 3:
            continue
        ks = sorted(s); A = np.array([s[j] for j in ks]); R, t = kabsch(A, S[ks])
        res.append(np.linalg.norm(A @ R.T + t - S[ks], axis=1).mean())
    return S, np.array(res)


def pair_dists(S):
    return {f'{i}-{j}': float(np.linalg.norm(S[i] - S[j])) for i, j in itertools.combinations(range(len(S)), 2)}
