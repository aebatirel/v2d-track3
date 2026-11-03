#!/usr/bin/env python3
"""Hand-masked ray correction (HRC) of held phases: a post-processor on a perc2 track (hand-aware lane, 3 Nov 2026;
PREREG docs/analysis/hand-aware-20261103/PREREG.md).

Inference only. Reads the track (poses.npz: world_T_cam, cam_T_<obj>), the FoundationStereo depth cache (rectified-left,
1600x1000), our templates (library_v3), our MediaPipe hand fit (hands_refined.npz, world frame), calibration, and the
episode's object names / slot order. No ground truth.

Per object:
  1. contact frames: >= 2 fingertips of one hand within CONTACT_CM of the tracked template surface; runs bridged over
     gaps <= 12 frames or gaps where a hand stays within NEAR_CM of the tracked surface, dilated +-8;
  2. residual r(t): median (z_obs - z_render) over visible own-surface pixels (eroded silhouette, no other object in
     front, outside the hand mask, observed depth > 0, |z_obs - z_render| < BAND);
  3. baseline b: median r over the frames before the first contact frame (>= 5), else over the first 10 frames;
  4. in contact frames with |r - b| > TAU (spans extended forward / backward while |r - b| > TAU: hysteresis): translate along the camera ray through the object origin to cancel r - b,
     re-render, repeat up to ITERS times or until |r - b| < 0.3 cm; keep the frame only if the final |r - b| < half
     the initial one;
  5. the ray shift is median-filtered over 5 frames inside each corrected span; spans shorter than MIN_SPAN dropped.
Outputs in OUT: poses.npz, poses_world_vo.npz (same layout as perc2), hrc.json (per-object log).
Usage: hrc.py --t3 T3 --ep N --track DIR --depth depths.npy --lib LIBDIR --hands hands_refined.npz --out OUT
              [--tau 0.015] [--contact_cm 3] [--min_span 3] [--band 0.08] [--iters 4] [--skip obj,obj]
"""
import argparse, json, os
import numpy as np, cv2, trimesh, pyarrow.parquet as pq
from scipy.ndimage import median_filter

p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
p.add_argument('--t3', required=True); p.add_argument('--ep', type=int, required=True)
p.add_argument('--track', required=True); p.add_argument('--depth', required=True); p.add_argument('--lib', required=True)
p.add_argument('--hands', required=True); p.add_argument('--out', required=True)
p.add_argument('--tau', type=float, default=0.015); p.add_argument('--contact_cm', type=float, default=3.0)
p.add_argument('--min_span', type=int, default=3); p.add_argument('--near_cm', type=float, default=15.0); p.add_argument('--band', type=float, default=0.08)
p.add_argument('--iters', type=int, default=4); p.add_argument('--no_hand_mask', action='store_true')
p.add_argument('--gate', choices=['contact', 'near'], default='contact', help='near: a hand within NEAR_CM of the tracked surface within +-15 frames'); p.add_argument('--skip', default='')
p.add_argument('--ds', type=int, default=4); p.add_argument('--hand_r', type=float, default=0.015)
p.add_argument('--npts', type=int, default=30000)
a = p.parse_args()
SKIP = set(x for x in a.skip.split(',') if x)
TIPS = [4, 8, 12, 16, 20]
BONES = [(0, 1), (1, 2), (2, 3), (3, 4), (0, 5), (5, 6), (6, 7), (7, 8), (0, 9), (9, 10), (10, 11), (11, 12), (0, 13), (13, 14),
         (14, 15), (15, 16), (0, 17), (17, 18), (18, 19), (19, 20), (5, 9), (9, 13), (13, 17)]

# rectification exactly as pipeline/perc2.py (left = ego_cam_c)
C = json.load(open(f'{a.t3}/calib.json')); cam = C['cameras']
sp = [q for q in C['stereo_pairs'] if q['camera'] == 'ego'][0]
K_ = lambda n: np.array(cam[n]['intrinsic_matrix'], float); D_ = lambda n: np.array(cam[n]['distortion_coefficients'], float)
E = np.array(sp['left_to_right'], float)
_, _, P1, _, _, _, _ = cv2.stereoRectify(K_('ego_cam_c'), D_('ego_cam_c'), K_('ego_cam_b'), D_('ego_cam_b'), (1280, 800),
                                         E[:3, :3].copy(), E[:3, 3].reshape(3, 1).copy(), alpha=0, newImageSize=(1600, 1000),
                                         flags=cv2.CALIB_ZERO_DISPARITY)
K = P1[:3, :3].copy(); K[:2] /= a.ds; Wd, Hd = 1600 // a.ds, 1000 // a.ds

if os.path.exists(f'{a.t3}/ep{a.ep}.parquet'):
    tab = pq.read_table(f'{a.t3}/ep{a.ep}.parquet', columns=['observation.objects']).slice(0, 1).to_pylist()
    names = [o['name'] for o in tab[0]['observation.objects']]             # names / slot order only
else:                                                                      # eval: the kit roster
    names = json.load(open(os.environ['ROSTER']))['episodes'][str(a.ep)]
Z = np.load(f'{a.track}/poses.npz'); WC = Z['world_T_cam']; N = len(WC)
POSE = {n: Z[f'cam_T_{n}'].copy() for n in names}
PTS = {n: np.asarray(trimesh.load(f'{a.lib}/{n}.glb', force='mesh').sample(a.npts, seed=1)) for n in names}
dep = np.load(a.depth, mmap_mode='r')
h = np.load(a.hands); HJ = [(h[f'joints_{s}'].astype(float), h[f'valid_{s}']) for s in ('right', 'left')]


def render(n, T):
    X = PTS[n] @ T[:3, :3].T + T[:3, 3]; X = X[X[:, 2] > 0.05]
    uv = X @ K.T; u = (uv[:, 0] / uv[:, 2]).astype(int); v = (uv[:, 1] / uv[:, 2]).astype(int)
    ok = (u >= 0) & (u < Wd) & (v >= 0) & (v < Hd); zb = np.full((Hd, Wd), np.inf, np.float32)
    np.minimum.at(zb, (v[ok], u[ok]), X[ok, 2].astype(np.float32))
    m = cv2.morphologyEx(np.isfinite(zb).astype(np.uint8), cv2.MORPH_CLOSE, np.ones((3, 3), np.uint8))
    zc = cv2.dilate(np.where(np.isfinite(zb), zb, 0), np.ones((3, 3), np.uint8))
    return np.where(np.isfinite(zb), zb, np.where(m > 0, zc, np.inf)).astype(np.float32)


def hand_cam(i):
    Wi = np.linalg.inv(WC[i]); return [J[i] @ Wi[:3, :3].T + Wi[:3, 3] for J, V in HJ if V[i]]


def hand_mask(i):
    m = np.zeros((Hd, Wd), np.uint8)
    if a.no_hand_mask: return m.astype(bool)
    for X in hand_cam(i):
        if (X[:, 2] < 0.05).any(): continue
        uv = X @ K.T; uv = uv[:, :2] / uv[:, 2:]
        for b0, b1 in BONES:
            rpx = int(np.ceil(a.hand_r * K[0, 0] / min(X[b0, 2], X[b1, 2])))
            cv2.line(m, tuple(np.round(uv[b0]).astype(int)), tuple(np.round(uv[b1]).astype(int)), 1, 2 * rpx + 1)
        for j in range(21):
            cv2.circle(m, tuple(np.round(uv[j]).astype(int)), int(np.ceil(a.hand_r * K[0, 0] / X[j, 2])), 1, -1)
    return m.astype(bool)


def residual(n, T, D, hm, others):
    zb = render(n, T); sil = cv2.erode(np.isfinite(zb).astype(np.uint8), np.ones((3, 3), np.uint8)).astype(bool)
    for zo in others: sil &= ~(zo < zb - 0.005)
    v = sil & (D > 0) & ~hm
    d = np.where(v, D - zb, np.nan); v &= np.abs(np.nan_to_num(d, nan=9)) < a.band
    return (float(np.median(d[v])), int(v.sum())) if v.sum() >= 20 else (np.nan, int(v.sum()))


def runs(m):
    d = np.diff(np.r_[0, m.astype(int), 0]); return list(zip(np.nonzero(d == 1)[0], np.nonzero(d == -1)[0]))


# ---- contact frames per object (GT-free) ----
contact = {n: np.zeros(N, bool) for n in names}; near = {n: np.zeros(N, bool) for n in names}
for i in range(N):
    hs = hand_cam(i)
    for n in names:
        X = PTS[n][::30] @ POSE[n][i][:3, :3].T + POSE[n][i][:3, 3]
        for H in hs:
            d = np.linalg.norm(H[TIPS][:, None] - X[None], axis=-1).min(1) * 100
            if (d < a.contact_cm).sum() >= 2: contact[n][i] = True
            if d.min() < a.near_cm: near[n][i] = True
for n in names:
    # bridge gaps <= 12 frames, and longer gaps while a hand stays within NEAR_CM of the tracked surface (a track that
    # has drifted off the object leaves the fingertips, so contact alone would drop exactly the frames to correct)
    c = contact[n].copy(); r_ = runs(c)
    for (a0, a1), (b0, _) in zip(r_, r_[1:]):
        if b0 - a1 <= 12 or near[n][a1:b0].all(): c[a1:b0] = True
    g = c.copy()
    for t in np.nonzero(c)[0]: g[max(0, t - 8):t + 9] = True
    if a.gate == 'near':
        for t in np.nonzero(near[n])[0]: g[max(0, t - 15):t + 16] = True
    contact[n] = g

# ---- residuals at the track pose ----
r0 = {n: np.full(N, np.nan) for n in names}; DCACHE = {}
def frame_data(i):
    D = cv2.resize(np.asarray(dep[i]), (Wd, Hd), interpolation=cv2.INTER_NEAREST)
    return D, hand_mask(i), {n: render(n, POSE[n][i]) for n in names}
for i in range(N):
    D, hm, zbs = frame_data(i)
    for n in names:
        r0[n][i] = residual(n, POSE[n][i], D, hm, [zbs[o] for o in names if o != n])[0]

LOG = {}; NEW = {n: POSE[n].copy() for n in names}
for n in names:
    L = LOG[n] = dict(contact_frames=int(contact[n].sum()), skipped=n in SKIP)
    if n in SKIP or not contact[n].any(): continue
    first = int(np.argmax(contact[n])); pre = r0[n][:first]; pre = pre[np.isfinite(pre)]
    b = float(np.median(pre)) if len(pre) >= 5 else float(np.nanmedian(r0[n][:10]))
    L['baseline_cm'] = round(b * 100, 2)
    off = np.isfinite(r0[n]) & (np.abs(r0[n] - b) > a.tau)
    cand = contact[n] & off
    # hysteresis: an excursion that starts in a contact frame continues while the residual stays off (the drifted track
    # leaves the hand, and the hand fit may drop out), forward and backward
    for i in np.nonzero(contact[n] & off)[0]:
        for step in (1, -1):
            j = i + step
            while 0 <= j < N and off[j] and not cand[j]: cand[j] = True; j += step
    shift = np.zeros(N); ok = np.zeros(N, bool)
    for i in np.nonzero(cand)[0]:
        D, hm, zbs = frame_data(i); others = [zbs[o] for o in names if o != n]
        T = POSE[n][i].copy(); u = T[:3, 3] / np.linalg.norm(T[:3, 3]); s = 0.0; e0 = r0[n][i] - b; e = e0
        for _ in range(a.iters):
            s += e / max(u[2], 0.3); T2 = T.copy(); T2[:3, 3] = POSE[n][i][:3, 3] + s * u
            rr, _ = residual(n, T2, D, hm, others)
            if not np.isfinite(rr): break
            e = rr - b; T = T2
            if abs(e) < 0.003: break
        if np.isfinite(e) and abs(e) < 0.5 * abs(e0):
            shift[i] = s; ok[i] = True
    kept = np.zeros(N, bool)
    for a0, a1 in runs(ok):
        if a1 - a0 >= a.min_span:
            kept[a0:a1] = True; shift[a0:a1] = median_filter(shift[a0:a1], size=5, mode='nearest')
    shift[~kept] = 0
    for i in np.nonzero(kept)[0]:
        T = POSE[n][i]; u = T[:3, 3] / np.linalg.norm(T[:3, 3]); NEW[n][i][:3, 3] = T[:3, 3] + shift[i] * u
    L.update(candidates=int(cand.sum()), passed_check=int(ok.sum()), corrected=int(kept.sum()),
             spans=[[int(x), int(y)] for x, y in runs(kept)],
             max_shift_cm=round(float(np.abs(shift).max() * 100), 2), mean_abs_shift_cm=round(float(np.abs(shift[kept]).mean() * 100), 2) if kept.any() else 0.0)

os.makedirs(a.out, exist_ok=True)
np.savez(f'{a.out}/poses.npz', world_T_cam=WC, **{f'cam_T_{n}': NEW[n] for n in names})
np.savez(f'{a.out}/poses_world_vo.npz', **{n: np.stack([WC[i] @ NEW[n][i] for i in range(N)]) for n in names})
json.dump(dict(ep=a.ep, params=vars(a), objects=LOG), open(f'{a.out}/hrc.json', 'w'), indent=1)
print(json.dumps(LOG))
