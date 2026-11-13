"""b7_ball_crops: GT-free visual check of detected marker balls (B7 dev diagnostic; never part of a gmg run, never
used to choose a detector setting: the settings are frozen).

For each ball of one object in a b7 dev output (RUN/b7/ep<N>.json), the frames whose raw owned points support it
most (points within the 3 sigma band of the sphere that face their camera) are found in the dev observation file;
the ball centre is moved into the rectified-left camera by OUR track (poses.npz cam_T_<obj>[k]) and projected into
the colour camera ego_cam_a (frame j = k + 1, pipeline/hands_mp.py; geometry as scripts/crops.py). Each crop is
centred on the projected centre (window 6 projected radii, at least 48 px), upscaled to 144 px, with the projected
sphere outline drawn on a second copy. A montage row per ball: label, 3 frames x (plain, outlined).

Inputs (guard roles): obs_all (dev), tracks, calib, video. Nothing else is read. Usage:
  GMG_MODE=dev python gmg/tools/b7_ball_crops.py --ep-json RUN/b7/ep2.json --obj white_pot_lid \
      --video <scratchpad>/data/store/ep2_a.mp4 --out <png> [--top 12]
"""
import argparse
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
MR = os.path.dirname(os.path.dirname(HERE))
if MR not in sys.path:
    sys.path.insert(0, MR)
from gmg import guard  # noqa: E402

import cv2  # noqa: E402
import numpy as np  # noqa: E402
from scipy.spatial import cKDTree  # noqa: E402


def geometry(calib_path):
    """scripts/crops.py geometry(): rectified-left -> ego_cam_a (same chain as pipeline/hands_mp.py)."""
    with open(guard.open_input(calib_path, 'calib')) as f:
        C = json.load(f)
    cam = C['cameras']
    sp = [p for p in C['stereo_pairs'] if p['camera'] == 'ego'][0]
    K_ = lambda n: np.array(cam[n]['intrinsic_matrix'], float)  # noqa: E731
    D_ = lambda n: np.array(cam[n]['distortion_coefficients'], float)  # noqa: E731
    E = np.array(sp['left_to_right'], float); R_lr, T_lr = E[:3, :3].copy(), E[:3, 3].copy()
    R1, _, P1, P2, _, _, _ = cv2.stereoRectify(K_('ego_cam_c'), D_('ego_cam_c'), K_('ego_cam_b'), D_('ego_cam_b'),
                                               (1280, 800), R_lr, T_lr.reshape(3, 1), alpha=0,
                                               newImageSize=(1600, 1000), flags=cv2.CALIB_ZERO_DISPARITY)
    Eab = np.array(cam['ego_cam_a']['extrinsics_to_stereo_left'], float); R_ab, t_ab = Eab[:3, :3], Eab[:3, 3]
    T_a_rect = np.eye(4); T_a_rect[:3, :3] = R_ab.T @ R_lr @ R1.T; T_a_rect[:3, 3] = R_ab.T @ (T_lr - t_ab)
    return K_('ego_cam_a'), D_('ego_cam_a'), T_a_rect


def support_frames(P, C, F, c, r, tol, n=3, gap=10):
    d = np.linalg.norm(P - c, axis=1)
    m = (np.abs(d - r) < tol) & (np.einsum('ij,ij->i', P - c, C - P) > 0)
    fr, cnt = np.unique(F[m], return_counts=True)
    out = []
    for k in fr[np.argsort(-cnt, kind='stable')]:
        if all(abs(int(k) - j) >= gap for j in out):
            out.append(int(k))
        if len(out) == n:
            break
    return out, dict(zip(fr.tolist(), cnt.tolist()))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--ep-json', required=True)
    ap.add_argument('--obj', required=True)
    ap.add_argument('--video', required=True)
    ap.add_argument('--out', required=True)
    ap.add_argument('--top', type=int, default=12)
    ap.add_argument('--a-offset', type=int, default=1)
    a = ap.parse_args()
    if guard.mode() != 'dev':
        raise SystemExit('dev diagnostic: GMG_MODE=dev only')
    with open(a.ep_json) as f:
        E = json.load(f)
    ep = int(E['ep'])
    balls = sorted(E['markers']['balls'][a.obj], key=lambda b: -b['votes'])[:a.top]
    sig = E['sigma_mm'][a.obj] * 1e-3
    D = guard.CFG['data']
    z = guard.load_npz(os.path.join(D, 'obs_all', f'ep{ep}_{a.obj}.npz'), 'obs_all', keys=['pts', 'cam', 'frame'])
    P = np.asarray(z['pts'], float); C = np.asarray(z['cam'], float); F = np.asarray(z['frame']).astype(int)
    ok = np.all(np.isfinite(P), 1) & np.all(np.isfinite(C), 1)
    P, C, F = P[ok], C[ok], F[ok]
    tree = cKDTree(P)
    poses = guard.load_npz(os.path.join(D, 'data', 'sweep', f'ep{ep}', 'poses.npz'), 'tracks', keys=[f'cam_T_{a.obj}'])
    T_o = poses[f'cam_T_{a.obj}']
    Ka, Da, T_a_rect = geometry(os.path.join(D, 'data', 'calib.json'))
    cap = cv2.VideoCapture(guard.open_input(a.video, 'video'))
    cache = {}

    def frame(j):
        if j not in cache:
            cap.set(cv2.CAP_PROP_POS_FRAMES, j)
            okf, im = cap.read()
            cache[j] = im if okf else None
        return cache[j]

    S = 144
    rows, meta = [], []
    for bi, b in enumerate(balls):
        c = np.array(b['c']); r = float(b['r'])
        near = tree.query_ball_point(c, r + 3 * sig)
        ks, counts = support_frames(P[near], C[near], F[near], c, r, 3 * sig)
        tiles = []
        for k in ks:
            X = T_a_rect @ (T_o[k] @ np.r_[c, 1.0])
            uv, _ = cv2.projectPoints(X[:3].reshape(1, 1, 3), np.zeros(3), np.zeros(3), Ka, Da)
            u, v = uv.reshape(2)
            rp = float(Ka[0, 0] * r / max(X[2], 1e-6))
            im = frame(k + a.a_offset)
            if im is None:
                continue
            h = int(max(24, 3 * rp))
            x0, y0 = int(round(u)) - h, int(round(v)) - h
            pad = cv2.copyMakeBorder(im, 2 * h, 2 * h, 2 * h, 2 * h, cv2.BORDER_CONSTANT, value=(0, 0, 0))
            crop = pad[y0 + 2 * h:y0 + 4 * h, x0 + 2 * h:x0 + 4 * h]
            crop = cv2.resize(crop, (S, S), interpolation=cv2.INTER_CUBIC)
            ol = crop.copy()
            cv2.circle(ol, (S // 2, S // 2), max(1, int(round(rp * S / (2 * h)))), (0, 0, 255), 1, cv2.LINE_AA)
            cv2.putText(crop, f'k{k} n{counts.get(k, 0)}', (3, 12), cv2.FONT_HERSHEY_SIMPLEX, 0.35, (0, 255, 255), 1)
            tiles += [crop, ol]
            meta.append(dict(ball=bi, k=k, u=round(float(u), 1), v=round(float(v), 1), r_px=round(rp, 2),
                             z_m=round(float(X[2]), 3)))
        while len(tiles) < 6:
            tiles.append(np.zeros((S, S, 3), np.uint8))
        lab = np.zeros((S, 150, 3), np.uint8)
        for i, t in enumerate([f'#{bi} r {b["r_mm"]:.1f} mm', f'votes {b["votes"]} pass {b["pass_"]}',
                               f'ndev {b["normal_dev_deg"]}', f'out {b["outside_ratio"]}', f'cap {b["cap_deg"]:.0f}',
                               f'fit {b["fit"]}']):
            cv2.putText(lab, t, (4, 18 + 20 * i), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 255), 1)
        rows.append(np.hstack([lab] + tiles))
    if not rows:
        raise SystemExit('no balls')
    os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
    cv2.imwrite(a.out, np.vstack(rows))
    with open(os.path.splitext(a.out)[0] + '.json', 'w') as f:
        json.dump(dict(ep=ep, obj=a.obj, ep_json=a.ep_json, crops=meta), f, indent=1)
    print(a.out, len(rows), 'balls')


if __name__ == '__main__':
    main()
