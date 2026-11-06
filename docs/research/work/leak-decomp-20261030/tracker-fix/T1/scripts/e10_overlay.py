"""GT-free overlay QA of S6 on eval 10 (T1 eval side): our stored track vs the pose S6 would hold if it froze the cup.

On rectified cam-c frames (public camera calibration, as pipeline/track_overlay.py) it draws our mesh surface samples:
  red     blue cup, our track (S6's input; S6 kept it, so also its output)
  cyan    blue cup held at its frame-0 world pose (what S6 would write if it froze the cup), through world_T_cam[t]
  yellow  beige cup, our track
Each tile is a crop around the cups, labelled with the blue cup's horizontal travel and height from frame 0 (S6's own
measure: vertex centroid, S6's frame-0 depth plane from pose_opt.json). Reads our perception outputs, our meshes and the
eval video only; no ground truth exists for eval. Usage:
  python -I e10_overlay.py POSES POSE_OPT_JSON VIDEO CALIB MESHES OUT.png [frames]
"""
import json, sys

import cv2
import numpy as np
import trimesh

REPO = '/home/user/v2d-track3'
sys.path.insert(0, f'{REPO}/pipeline')
from refine import assert_inference_input  # noqa: E402
from track_overlay import rectify_maps  # noqa: E402


def main():
    poses, popt, video, calib, meshes, out = sys.argv[1:7]
    frames = [int(x) for x in (sys.argv[7] if len(sys.argv) > 7 else '0,35,42,46,60,100,117,160').split(',')]
    for f in (poses, popt, video, calib, meshes):
        assert_inference_input(f)
    P = np.load(poses)
    W = P['world_T_cam'].astype(float)
    camT = {n: P[f'cam_T_{n}'].astype(float) for n in ('blue_cup', 'beige_cup')}
    s6 = json.load(open(popt))['steps']['S6']
    nrm = np.asarray(s6['plane']['n'], float)
    MC, K = rectify_maps(calib)
    M = {n: trimesh.load(f'{meshes}/{n}.glb', force='mesh') for n in camT}
    pts = {n: np.asarray(trimesh.sample.sample_surface(m, 2500, seed=0)[0], float) for n, m in M.items()}
    cen = np.asarray(M['blue_cup'].vertices, float).mean(0)
    O = W @ camT['blue_cup']
    c = O[:, :3, :3] @ cen + O[:, :3, 3]
    hold = np.einsum('tij,jk->tik', np.linalg.inv(W), O[0])           # frame-0 world pose seen from camera t
    cap, imgs, t = cv2.VideoCapture(video), {}, 0
    while len(imgs) < len(frames):
        ok, f = cap.read()
        if not ok:
            break
        if t in frames:
            imgs[t] = cv2.remap(f, MC[0], MC[1], cv2.INTER_LINEAR)
        t += 1
    tiles = []
    for t in frames:
        img = imgs[t].copy()
        lay = [('beige_cup', camT['beige_cup'][t], (0, 220, 255)), ('blue_cup', hold[t], (255, 255, 0)),
               ('blue_cup', camT['blue_cup'][t], (0, 0, 255))]
        allp = []
        for n, T_, col in lay:
            X = pts[n] @ T_[:3, :3].T + T_[:3, 3]
            X = X[X[:, 2] > 0.05]
            uv = X[:, :2] / X[:, 2:3] * [K[0, 0], K[1, 1]] + [K[0, 2], K[1, 2]]
            allp.append(uv)
            for u, v in uv.astype(int):
                if 0 <= u < img.shape[1] and 0 <= v < img.shape[0]:
                    cv2.circle(img, (u, v), 1, col, -1)
        A = np.vstack(allp[1:])                                         # crop on the blue cup (both poses)
        x0, y0 = np.clip(A.min(0) - 110, 0, None).astype(int)
        x1, y1 = np.minimum(A.max(0) + 110, [img.shape[1], img.shape[0]]).astype(int)
        side = max(x1 - x0, y1 - y0)
        cx, cy = (x0 + x1) // 2, (y0 + y1) // 2
        x0, y0 = max(0, cx - side // 2), max(0, cy - side // 2)
        crop = cv2.resize(img[y0:y0 + side, x0:x0 + side], (420, 420))
        d = c[t] - c[0]
        v = float(d @ nrm)
        h = float(np.linalg.norm(d - v * nrm))
        cv2.rectangle(crop, (0, 0), (420, 34), (0, 0, 0), -1)
        cv2.putText(crop, f'f{t}  blue: h {h * 100:.1f} cm, v {v * 100:+.1f} cm', (8, 24), cv2.FONT_HERSHEY_SIMPLEX, 0.62,
                    (255, 255, 255), 2)
        tiles.append(crop)
    while len(tiles) % 4:
        tiles.append(np.zeros_like(tiles[0]))
    grid = np.vstack([np.hstack(tiles[i:i + 4]) for i in range(0, len(tiles), 4)])
    leg = np.zeros((40, grid.shape[1], 3), np.uint8)
    for k, (txt, col) in enumerate((('blue cup, our track (S6 kept it)', (0, 0, 255)),
                                    ('blue cup held at frame 0 (S6 if frozen)', (255, 255, 0)),
                                    ('beige cup, our track', (0, 220, 255)))):
        cv2.circle(leg, (14 + k * 560, 20), 7, col, -1)
        cv2.putText(leg, txt, (28 + k * 560, 27), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1)
    cv2.imwrite(out, np.vstack([leg, grid]))
    print('wrote', out, grid.shape)


if __name__ == '__main__':
    main()
