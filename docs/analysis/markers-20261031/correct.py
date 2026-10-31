"""Step 3 (GT-free): marker correction layer on our perc2 track.

Input: census.py's per-frame layout-consistent marker fixes (fix_<split><ep>_<obj>.npz: number of markers n, the
fixed pose, the track rest mask) and our track. Output: a corrected cam_T_<obj> track + statistics. Steps:
  1. body-frame correction per fix frame, D_t = T_prior(t)^-1 F(t); weight 1 for >= 3 markers, W2 for 2 markers
     (2-marker fixes keep the prior's rotation about the marker axis); 1-marker fixes are not used;
  2. consistency gate with the prior: |D| < GATE_T and < GATE_R;
  3. temporal outlier rejection: reject D_t that differs from the weighted median of its +-6 frames by > 15 mm / 8 deg;
  4. per-frame smoothing: weighted mean of the accepted D over a 9-frame window (centre +-4); frames without a fix
     interpolate linearly between the nearest smoothed corrections (carry), and hold the nearest one at the ends;
  5. static segments (track rest runs >= 10 frames): vote over the >= 3-marker corrections; the largest 5-deg cluster
     wins if it has >= 4 votes and >= 2x the runner-up, and its chordal mean (rotation) and median (translation) is
     applied as one constant correction to the whole segment; otherwise abstain (keep step 4).
No ground truth, no scan.
Usage: python correct.py SPLIT EP OBJ [OUT_NPZ]  (prints a JSON line of statistics)
"""
import json, os, sys
import numpy as np
from scipy.spatial.transform import Rotation as Rot
sys.path.insert(0, os.path.dirname(__file__))
import mlib

W2 = 0.4
GATE_T, GATE_R = 0.03, 20.0
OUT_T, OUT_R = 0.015, 8.0
HALF = 4
SEG_MIN, CL_DEG, VOTE_MIN = 10, 5.0, 4


def runs(mask):
    m = np.concatenate([[0], mask.astype(int), [0]]); d = np.diff(m)
    return list(zip(np.nonzero(d == 1)[0], np.nonzero(d == -1)[0]))


def wavg(D, w):
    """weighted mean of 4x4 corrections: translation mean, rotation chordal mean."""
    R = Rot.from_matrix(D[:, :3, :3]).mean(weights=w)
    out = np.eye(4); out[:3, :3] = R.as_matrix(); out[:3, 3] = (D[:, :3, 3] * w[:, None]).sum(0) / w.sum()
    return out


def dist(A, B):
    return np.linalg.norm(A[:3, 3] - B[:3, 3]), np.degrees(Rot.from_matrix(A[:3, :3] @ B[:3, :3].T).magnitude())


def interp(Da, Db, s):
    out = np.eye(4); out[:3, 3] = (1 - s) * Da[:3, 3] + s * Db[:3, 3]
    r = Rot.from_matrix(Db[:3, :3] @ Da[:3, :3].T).as_rotvec()
    out[:3, :3] = Rot.from_rotvec(s * r).as_matrix() @ Da[:3, :3]
    return out


def correct(T, n, F, rest, opts=None):
    """T (N,4,4) prior cam_T_obj, n (N,) markers per fix, F (N,4,4) fixed poses (nan if none), rest (N,) bool.
    Returns corrected track (N,4,4), per-frame correction D (N,4,4), info dict."""
    o = dict(vote=True, carry=True); o.update(opts or {})
    N = len(T); D = np.full((N, 4, 4), np.nan); w = np.zeros(N)
    for t in range(N):
        if n[t] >= 2 and np.all(np.isfinite(F[t])):
            d = np.linalg.inv(T[t]) @ F[t]; dt, dr = dist(d, np.eye(4))
            if dt < GATE_T and dr < GATE_R:
                D[t] = d; w[t] = 1.0 if n[t] >= 3 else W2
    n_gate = int((w > 0).sum())
    # temporal outlier rejection
    acc = w > 0
    for t in np.nonzero(w > 0)[0]:
        nb = [s for s in range(max(0, t - 6), min(N, t + 7)) if w[s] > 0 and s != t]
        if len(nb) >= 2:
            ref = wavg(D[nb], w[nb]); dt, dr = dist(D[t], ref)
            if dt > OUT_T or dr > OUT_R:
                acc[t] = False
    w = np.where(acc, w, 0.0)
    # smoothing + carry
    Ds = np.full((N, 4, 4), np.nan)
    for t in range(N):
        nb = [s for s in range(max(0, t - HALF), min(N, t + HALF + 1)) if w[s] > 0]
        if nb:
            Ds[t] = wavg(D[nb], w[nb])
    have = np.nonzero(np.isfinite(Ds[:, 0, 0]))[0]
    C = np.tile(np.eye(4), (N, 1, 1))
    if len(have) and o['carry']:
        for t in range(N):
            if np.isfinite(Ds[t, 0, 0]):
                C[t] = Ds[t]; continue
            a = have[have < t]; b = have[have > t]
            if len(a) and len(b):
                C[t] = interp(Ds[a[-1]], Ds[b[0]], (t - a[-1]) / (b[0] - a[-1]))
            else:
                C[t] = Ds[a[-1]] if len(a) else Ds[b[0]]
    elif len(have):
        for t in have:
            C[t] = Ds[t]
    # static segments: vote
    segs = []
    if o['vote']:
        for a, b in runs(rest):
            if b - a < SEG_MIN:
                continue
            idx = [t for t in range(a, b) if w[t] >= 1.0]
            rec = dict(a=int(a), b=int(b), full=len(idx), decision='abstain')
            if len(idx) >= VOTE_MIN:
                Rv = Rot.from_matrix(D[idx][:, :3, :3])
                ang = np.degrees(np.array([[(Rv[i] * Rv[j].inv()).magnitude() for j in range(len(idx))]
                                           for i in range(len(idx))]))
                cnt = (ang < CL_DEG).sum(1); i = int(np.argmax(cnt)); win = np.nonzero(ang[i] < CL_DEG)[0]
                rest_i = np.setdiff1d(np.arange(len(idx)), win)
                ru = int((ang[np.ix_(rest_i, rest_i)] < CL_DEG).sum(1).max()) if len(rest_i) else 0
                rec.update(winner=int(len(win)), runner_up=ru)
                if len(win) >= VOTE_MIN and len(win) >= 2 * ru:
                    sel = [idx[j] for j in win]
                    P = np.eye(4); P[:3, :3] = Rot.from_matrix(D[sel][:, :3, :3]).mean().as_matrix()
                    P[:3, 3] = np.median(D[sel][:, :3, 3], 0)
                    C[a:b] = P; rec['decision'] = 'vote'
                    rec['corr_mm'] = round(float(np.linalg.norm(P[:3, 3]) * 1000), 1)
                    rec['corr_deg'] = round(float(np.degrees(Rot.from_matrix(P[:3, :3]).magnitude())), 2)
            segs.append(rec)
    out = T @ C
    info = dict(N=N, fix2=int((n >= 2).sum()), fix3=int((n >= 3).sum()), gated=n_gate, accepted=int((w > 0).sum()),
                segs=segs)
    return out, C, info


def twist_deg(R, axis):
    """signed twist angle of rotation R about unit axis (swing-twist)."""
    q = Rot.from_matrix(R).as_quat(); v = q[:3] @ axis
    return float(np.degrees(2 * np.arctan2(v, q[3])))


def main():
    split, ep, obj = sys.argv[1], int(sys.argv[2]), sys.argv[3]
    F = np.load(f'{mlib.S}/mk/scan/fix_{split}{ep}_{obj}.npz')
    P = np.load(mlib.poses_path(split, ep)); T = P[f'cam_T_{obj}'].astype(np.float64)[:len(F['n'])]
    out, C, info = correct(T, F['n'], F['fix'], F['rest'])
    rv = Rot.from_matrix(C[:, :3, :3])
    info.update(ep=ep, obj=obj, corr_t_mm_med=round(float(np.median(np.linalg.norm(C[:, :3, 3], axis=1)) * 1000), 1),
                corr_r_deg_med=round(float(np.median(np.degrees(rv.magnitude()))), 2),
                f0_t_mm=round(float(np.linalg.norm(C[0, :3, 3]) * 1000), 1),
                f0_r_deg=round(float(np.degrees(rv[0].magnitude())), 2))
    if obj == 'wooden_spoon':          # body z = handle axis in our template's R1 frame
        tw = np.array([twist_deg(c[:3, :3], np.array([0, 0, 1.0])) for c in C])
        info.update(f0_roll_deg=round(tw[0], 2), roll_med_abs_deg=round(float(np.median(np.abs(tw))), 2))
    if len(sys.argv) > 4:
        np.savez_compressed(sys.argv[4], **{f'cam_T_{obj}': out.astype(np.float32)}, corr=C)
    print(json.dumps(info))
    return info


if __name__ == '__main__':
    main()
