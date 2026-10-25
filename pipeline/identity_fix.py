"""Board identity and in-plane symmetry repair (rule R1 of docs/research/approaches-2026-10-25/approach1-motion-
constrained-meshes.md §2.6; the scoring is approach1-scripts/identity_rule.py, unchanged). Ground-truth-free: video,
calibration, our poses and our meshes only.

perc2 names the two near-identical boards by template similarity, intensity and extent, none of which separates them
(eval 25 and the 24 Oct ep24 track came out swapped, with one board turned 180 deg). Our board meshes carry the mocap
marker knobs (wooden_piece_1: four corner knobs on +x; wooden_piece_2: three on -x). For each assignment (as tracked /
swapped) and each of the 4 in-plane symmetries F of each board, the knob vertices on the camera-facing side are projected
into the rectified ego_cam_c frames FRAMES and scored by darkness against the plate (lower is better). The best choice
is applied to poses.npz (cam_T_<name> <- cam_T_<source> @ F) and poses_world_vo.npz; the as-tracked files are kept as
*_as_tracked.npz and the decision is written to identity_fix.json.
Validated on public ep24 (approach 1, T-1): keeps the good track, repairs the swapped 24 Oct track (0.029 -> 0.706 vs
mocap) and undoes all 8 injected swap x flip combinations. Only for the board pair wooden_piece_1 / wooden_piece_2.
Usage: python identity_fix.py VIDEO_C.mp4 CALIB.json PERC_DIR MESH_1 MESH_2 [--frames 0,2,4,6] [--dry]"""
import argparse, itertools, json, os, shutil

import cv2
import numpy as np
import trimesh

NAMES = ['wooden_piece_1', 'wooden_piece_2']
FL = {'I': np.eye(4), 'Rx': np.diag([1., -1, -1, 1]), 'Ry': np.diag([-1., 1, -1, 1]), 'Rz': np.diag([-1., -1, 1, 1])}


def rectified_frames(vid, calib, frames):
    C = json.load(open(calib)); cam = C['cameras']; sp = [p for p in C['stereo_pairs'] if p['camera'] == 'ego'][0]
    K_ = lambda n: np.array(cam[n]['intrinsic_matrix'], float)  # noqa: E731
    D_ = lambda n: np.array(cam[n]['distortion_coefficients'], float)  # noqa: E731
    E = np.array(sp['left_to_right'], float); SZ, RSZ = (1280, 800), (1600, 1000)
    R1, R2, P1, P2, Q, _, _ = cv2.stereoRectify(K_('ego_cam_c'), D_('ego_cam_c'), K_('ego_cam_b'), D_('ego_cam_b'), SZ,
                                                E[:3, :3].copy(), E[:3, 3].reshape(3, 1).copy(), alpha=0, newImageSize=RSZ,
                                                flags=cv2.CALIB_ZERO_DISPARITY)
    MC = cv2.initUndistortRectifyMap(K_('ego_cam_c'), D_('ego_cam_c'), R1, P1, RSZ, cv2.CV_32FC1)
    cap = cv2.VideoCapture(vid); imgs = {}; i = 0
    while True:
        ok, f = cap.read()
        if not ok or i > max(frames):
            break
        if i in frames:
            imgs[i] = cv2.GaussianBlur(cv2.remap(cv2.cvtColor(f, cv2.COLOR_BGR2GRAY), MC[0], MC[1], cv2.INTER_LINEAR),
                                       (3, 3), 0).astype(float)
        i += 1
    return imgs, P1[:3, :3]


def main():
    p = argparse.ArgumentParser()
    p.add_argument('video'); p.add_argument('calib'); p.add_argument('perc_dir'); p.add_argument('mesh1'); p.add_argument('mesh2')
    p.add_argument('--frames', default='0,2,4,6'); p.add_argument('--dry', action='store_true')
    a = p.parse_args()
    F = [int(x) for x in a.frames.split(',')]
    P = dict(np.load(os.path.join(a.perc_dir, 'poses.npz')))
    if sorted(k[6:] for k in P if k.startswith('cam_T_')) != NAMES:
        print('identity_fix: not the board pair; nothing to do'); return
    imgs, KR = rectified_frames(a.video, a.calib, F)
    missing = [f for f in F if f not in imgs]
    if missing:
        raise SystemExit(f'identity_fix: frames {missing} not read from {a.video}')
    TT = {n: P[f'cam_T_{n}'] for n in NAMES}
    M = {}
    for n, mp in zip(NAMES, (a.mesh1, a.mesh2)):
        V = np.asarray(trimesh.load(mp, force='mesh').vertices); xm = np.median(V[:, 0])
        M[n] = (V[np.abs(V[:, 0] - xm) > 0.009], V[np.abs(V[:, 0] - xm) < 0.003], xm)

    def score(mesh, T, img):
        knobs, plate, xm = M[mesh]
        cam_side = np.sign((np.linalg.inv(T) @ np.r_[0, 0, 0, 1.0])[0] - xm)     # which face sees the camera
        k = knobs[np.sign(knobs[:, 0] - xm) == cam_side]
        if len(k) < 5:
            return 0.0

        def sample(X):
            Y = X @ T[:3, :3].T + T[:3, 3]; u = Y @ KR.T; uv = np.round(u[:, :2] / u[:, 2:3]).astype(int)
            ok = (uv[:, 0] >= 0) & (uv[:, 0] < img.shape[1]) & (uv[:, 1] >= 0) & (uv[:, 1] < img.shape[0])
            return img[uv[ok, 1], uv[ok, 0]]
        s_k, s_p = sample(k), sample(plate)
        return float(s_k.mean() - s_p.mean()) if len(s_k) and len(s_p) else 0.0

    res = []
    for assign in ('as tracked', 'swapped'):
        src = dict(zip(NAMES, NAMES if assign == 'as tracked' else NAMES[::-1]))
        for f1, f2 in itertools.product(FL, FL):
            s = sum(score(NAMES[0], TT[src[NAMES[0]]][t] @ FL[f1], imgs[t]) + score(NAMES[1], TT[src[NAMES[1]]][t] @ FL[f2], imgs[t])
                    for t in F)
            res.append((round(s / len(F), 1), assign, f1, f2))
    res.sort()
    best = res[0]; base = [r for r in res if r[1] == 'as tracked' and r[2] == 'I' and r[3] == 'I'][0]
    change = best[1:] != base[1:]
    out = dict(frames=F, best=best, as_tracked=base, as_tracked_rank=res.index(base) + 1, n=len(res), top5=res[:5],
               applied=bool(change and not a.dry))
    print('identity_fix:', json.dumps(out))
    if change and not a.dry:
        src = dict(zip(NAMES, NAMES if best[1] == 'as tracked' else NAMES[::-1])); FF = dict(zip(NAMES, (FL[best[2]], FL[best[3]])))
        for fn, key in (('poses.npz', 'cam_T_{}'), ('poses_world_vo.npz', '{}')):
            path = os.path.join(a.perc_dir, fn)
            if not os.path.exists(path):
                continue
            Z = dict(np.load(path)); orig = {n: Z[key.format(n)].copy() for n in NAMES}
            shutil.copy(path, path.replace('.npz', '_as_tracked.npz'))
            for n in NAMES:
                Z[key.format(n)] = orig[src[n]] @ FF[n]
            np.savez(path, **Z)
    json.dump(out, open(os.path.join(a.perc_dir, 'identity_fix.json'), 'w'), indent=1)


if __name__ == '__main__':
    main()
