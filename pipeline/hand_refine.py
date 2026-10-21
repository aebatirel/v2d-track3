"""Bone-length-consistent hand refinement (inference only; 2026-10-21, owner's suggestion after the ep24 failure).

hands_mp.py fits MediaPipe's per-frame 3-D hand shape (world landmarks) rigidly to the 2-D landmarks and depth. When
a hand grips or is occluded by an object, that predicted shape collapses (ep24 left hand: wrist->middle-tip 3.8-5.2
cm from frame 100 on; scale on its lower clamp) and the robot reference inherits an impossible hand. Here, per hand:
  1. reference bone lengths = per-bone median over the BEST frames (measured, depth found, reprojection rms in the
     lowest BEST_FRAC); the reference palm shape (wrist, thumb CMC, 4 MCPs) = Procrustes mean over the same frames;
  2. per frame, in camera a: the reference palm is fitted rigidly (fixed size) to the current palm joints;
  3. each finger chain is rebuilt from its palm joint outwards: joint j lies on the camera ray through its 2-D
     landmark at distance L from its (refined) parent, with L = the current length clipped to [1-MARGIN, 1+MARGIN] x
     reference (stretch margin). Of the two ray/sphere solutions the one nearer the current joint (MediaPipe's
     prediction) wins; a ray that misses the sphere gives the sphere point nearest the ray; frames without a 2-D
     landmark keep the current direction with the clipped length;
  4. light Savitzky-Golay smoothing, then bone lengths re-clipped.
QA (before / after) per hand goes to OUT .json: wrist->middle-tip median / p10, per-bone length CV, collapsed-frame
share (wrist->middle-tip < COLLAPSE x reference), joints under the table if --table is given.
Usage: python hand_refine.py --hands hands.npz --poses poses.npz --out hands_refined.npz [--table table_frame.npz]
"""
import argparse, json
import numpy as np, cv2
from scipy.signal import savgol_filter

CHAINS = [[1, 2, 3, 4], [5, 6, 7, 8], [9, 10, 11, 12], [13, 14, 15, 16], [17, 18, 19, 20]]   # from the palm joint
PALM = [0, 1, 5, 9, 13, 17]
BONES = [(c[i], c[i + 1]) for c in CHAINS for i in range(3)]


def kabsch(src, dst):
    cs, cd = src.mean(0), dst.mean(0)
    U, _, Vt = np.linalg.svd((src - cs).T @ (dst - cd))
    R = Vt.T @ U.T
    if np.linalg.det(R) < 0:
        Vt[-1] *= -1; R = Vt.T @ U.T
    return R, cd - R @ cs


def stats(J, valid, ref_len=None, table=None):
    J = J[valid]
    if not len(J):
        return {}
    wt = np.linalg.norm(J[:, 12] - J[:, 0], axis=1)
    L = np.stack([np.linalg.norm(J[:, b] - J[:, a], axis=1) for a, b in BONES], 1)
    out = dict(wrist_midtip_cm_median=round(float(np.median(wt) * 100), 1), wrist_midtip_cm_p10=round(float(np.percentile(wt, 10) * 100), 1),
               bone_cv_median=round(float(np.median(L.std(0) / np.maximum(L.mean(0), 1e-6))), 3))
    if ref_len is not None:
        ref_wt = ref_len['wrist_midtip']
        out['collapsed_share'] = round(float((wt < 0.6 * ref_wt).mean()), 3)
    if table is not None:
        n, d = table
        out['frames_joint_below_table_5mm'] = round(float(((J @ n + d).min(1) < -0.005).mean()), 3)
    return out


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('--hands', required=True); p.add_argument('--poses', required=True); p.add_argument('--out', required=True)
    p.add_argument('--table', default=None, help='table_frame.npz (mkref) for the under-table QA only')
    p.add_argument('--best_frac', type=float, default=0.3); p.add_argument('--margin', type=float, default=0.10)
    p.add_argument('--smooth_win', type=int, default=7)
    a = p.parse_args()
    H = dict(np.load(a.hands, allow_pickle=True)); W_C = np.load(a.poses)['world_T_cam'].astype(np.float64)
    Ka, Da, T_rect_a = H['Ka'], H['Da'], H['T_rect_a']
    table = None
    if a.table:
        tf = np.load(a.table); table = (tf['plane_n'].astype(float), float(tf['plane_d']))
    qa = {}
    for side in ('left', 'right'):
        J = H[f'joints_{side}'].astype(np.float64); valid = H[f'valid_{side}'].astype(bool)
        meas = H[f'measured_{side}'].astype(bool); uv = H[f'uv_a_{side}'].astype(np.float64)
        T = min(len(J), len(W_C))
        # camera-a coordinates of every frame
        A_T_W = [np.linalg.inv(W_C[t] @ T_rect_a) for t in range(T)]
        Ja = np.stack([J[t] @ A_T_W[t][:3, :3].T + A_T_W[t][:3, 3] for t in range(T)])
        # 1) reference from the best frames
        rms = H[f'rms_px_{side}'][:T].astype(float); dok = H[f'depth_ok_{side}'][:T].astype(bool)
        cand = np.nonzero(meas[:T] & valid[:T] & dok & np.isfinite(rms))[0]
        if len(cand) < 5:
            qa[side] = dict(skipped=f'only {len(cand)} good frames'); continue
        best = cand[np.argsort(rms[cand])[:max(5, int(len(cand) * a.best_frac))]]
        Lref = {bn: float(np.median(np.linalg.norm(Ja[best, bn[1]] - Ja[best, bn[0]], axis=1))) for bn in BONES}
        palm0 = Ja[best[0], PALM]; P = [palm0 - palm0.mean(0)]
        for t in best[1:]:
            R, tr = kabsch(Ja[t, PALM], palm0); P.append(Ja[t, PALM] @ R.T + tr - palm0.mean(0))
        palm_ref = np.median(np.stack(P), 0)
        ref_wt = float(np.median(np.linalg.norm(Ja[best, 12] - Ja[best, 0], axis=1)))
        before = stats(np.stack([Ja[t] @ np.linalg.inv(A_T_W[t])[:3, :3].T + np.linalg.inv(A_T_W[t])[:3, 3] for t in range(T)]),
                       valid[:T], dict(wrist_midtip=ref_wt), table)
        # 2) + 3) per frame
        out = Ja.copy(); nray = nmiss = 0
        for t in range(T):
            if not valid[t]:
                continue
            R, tr = kabsch(palm_ref, Ja[t, PALM]); out[t, PALM] = palm_ref @ R.T + tr
            has_uv = meas[t] and np.all(np.isfinite(uv[t]))
            if has_uv:
                xn = cv2.undistortPoints(uv[t].reshape(-1, 1, 2), Ka, Da).reshape(-1, 2)
                rays = np.c_[xn, np.ones(len(xn))]; rays /= np.linalg.norm(rays, axis=1, keepdims=True)
            for ch in CHAINS:
                for i in range(3):
                    pa, j = ch[i], ch[i + 1]
                    par = out[t, pa]; cur = Ja[t, j] - Ja[t, pa]; lc = np.linalg.norm(cur)
                    L = float(np.clip(lc, (1 - a.margin) * Lref[(pa, j)], (1 + a.margin) * Lref[(pa, j)]))
                    prior = par + L * (cur / lc if lc > 1e-9 else np.array([0, 0, 1.0]))
                    if not has_uv:
                        out[t, j] = prior; continue
                    r = rays[j]; rp = r @ par; disc = rp * rp - par @ par + L * L
                    if disc >= 0:
                        s = np.array([rp - np.sqrt(disc), rp + np.sqrt(disc)]); s = s[s > 0.05]
                        if len(s):
                            q = s[:, None] * r; out[t, j] = q[np.argmin(np.linalg.norm(q - prior, axis=1))]; nray += 1
                            continue
                    c = rp * r - par; nmiss += 1                   # ray misses: sphere point nearest the ray
                    out[t, j] = par + L * c / max(np.linalg.norm(c), 1e-9)
        # 4) smoothing over valid runs, then bone lengths re-clipped along the smoothed directions
        if a.smooth_win >= 5:
            v = valid[:T].copy(); i = 0
            while i < T:
                if not v[i]:
                    i += 1; continue
                k = i
                while k < T and v[k]:
                    k += 1
                if k - i >= a.smooth_win:
                    out[i:k] = savgol_filter(out[i:k], a.smooth_win, 2, axis=0)
                i = k
            for t in range(T):
                if not valid[t]:
                    continue
                for ch in CHAINS:
                    for i in range(3):
                        pa, j = ch[i], ch[i + 1]; d = out[t, j] - out[t, pa]; ld = np.linalg.norm(d)
                        L = np.clip(ld, (1 - a.margin) * Lref[(pa, j)], (1 + a.margin) * Lref[(pa, j)])
                        out[t, j] = out[t, pa] + L * d / max(ld, 1e-9)
        Jw = np.stack([out[t] @ np.linalg.inv(A_T_W[t])[:3, :3].T + np.linalg.inv(A_T_W[t])[:3, 3] for t in range(T)])
        H[f'joints_{side}'] = np.concatenate([Jw, J[T:]]).astype(np.float32)
        after = stats(Jw, valid[:T], dict(wrist_midtip=ref_wt), table)
        qa[side] = dict(best_frames=len(best), ref_wrist_midtip_cm=round(ref_wt * 100, 1),
                        ref_palm_width_cm=round(float(np.linalg.norm(palm_ref[2] - palm_ref[5]) * 100), 1),
                        ray_solved=nray, ray_missed=nmiss, before=before, after=after)
    np.savez_compressed(a.out, **H)
    json.dump(qa, open(a.out.replace('.npz', '.json'), 'w'), indent=1)
    print(json.dumps(qa, indent=1))


if __name__ == '__main__':
    main()
