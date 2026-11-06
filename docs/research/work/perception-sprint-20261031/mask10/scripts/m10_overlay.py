"""GT-free overlay QA of S12 (mask10) on rectified cam-c frames (public camera calibration, as pipeline/track_overlay.py):
our mesh surface samples drawn for
  red      blue cup, our stored track (refine S2: the reference's input)
  cyan     blue cup, S12 V1 (held at its pre-nest pose; refine S12,S2)
  magenta  blue cup, V3p (physics only: both cups settled on hands-off window frames; nest_physics --mode both + S2)
  yellow   beige cup, our track (S2)
Each tile is a crop around the cups, labelled with the blue cup's height from frame 0 along our table normal for the
three blue poses (track / V1 / V3p). Reads our perception outputs, our meshes and the video only (no ground truth).
Usage: python -I m10_overlay.py S2_DIR V1_DIR V3P_DIR VIDEO CALIB MESHES OUT.png FRAMES TITLE [LABEL_OF_THIRD]"""
import json, sys

import cv2
import numpy as np
import trimesh

REPO = '/home/user/v2d-track3'
sys.path.insert(0, f'{REPO}/pipeline')
from refine import assert_inference_input  # noqa: E402
from track_overlay import rectify_maps  # noqa: E402


def main():
    s2, v1, v3p, video, calib, meshes, out, frames, title = sys.argv[1:10]
    lab3 = sys.argv[10] if len(sys.argv) > 10 else 'V3p'
    frames = [int(x) for x in frames.split(',')]
    for f in (s2, v1, v3p, video, calib, meshes):
        assert_inference_input(f)
    P = {k: np.load(f'{d}/poses.npz') for k, d in (('trk', s2), ('v1', v1), ('v3p', v3p))}
    W = P['trk']['world_T_cam'].astype(float)
    pl = json.load(open(f'{v1}/pose_opt.json'))['steps']['S12']
    nrm = np.asarray(pl['plane']['n'], float)
    win = [w for w in pl['windows'] if w.get('applied')]
    MC, K = rectify_maps(calib)
    M = {n: trimesh.load(f'{meshes}/{n}.glb', force='mesh') for n in ('blue_cup', 'beige_cup')}
    pts = {n: np.asarray(trimesh.sample.sample_surface(m, 2500, seed=0)[0], float) for n, m in M.items()}
    cen = np.asarray(M['blue_cup'].vertices, float).mean(0)

    def height(k):
        O = W @ P[k]['cam_T_blue_cup'].astype(float)
        c = O[:, :3, :3] @ cen + O[:, :3, 3]
        return (c - c[0]) @ nrm
    hv = {k: height(k) for k in P}
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
        lay = [('beige_cup', P['trk']['cam_T_beige_cup'][t], (0, 220, 255)),
               ('blue_cup', P['v3p']['cam_T_blue_cup'][t], (255, 0, 255)),
               ('blue_cup', P['v1']['cam_T_blue_cup'][t], (255, 255, 0)),
               ('blue_cup', P['trk']['cam_T_blue_cup'][t], (0, 0, 255))]
        allp = []
        for n, T_, col in lay:
            T_ = np.asarray(T_, float)
            X = pts[n] @ T_[:3, :3].T + T_[:3, 3]
            X = X[X[:, 2] > 0.05]
            uv = X[:, :2] / X[:, 2:3] * [K[0, 0], K[1, 1]] + [K[0, 2], K[1, 2]]
            allp.append(uv)
            for u, v in uv.astype(int):
                if 0 <= u < img.shape[1] and 0 <= v < img.shape[0]:
                    cv2.circle(img, (u, v), 1, col, -1)
        A = np.vstack(allp[1:])
        x0, y0 = np.clip(A.min(0) - 110, 0, None).astype(int)
        x1, y1 = np.minimum(A.max(0) + 110, [img.shape[1], img.shape[0]]).astype(int)
        side = max(x1 - x0, y1 - y0)
        cx, cy = (x0 + x1) // 2, (y0 + y1) // 2
        x0, y0 = max(0, cx - side // 2), max(0, cy - side // 2)
        crop = cv2.resize(img[y0:y0 + side, x0:x0 + side], (420, 420))
        inw = any(w['start'] <= t < w.get('hold_end', w['end']) for w in win)
        cv2.rectangle(crop, (0, 0), (420, 58), (0, 0, 0), -1)
        cv2.putText(crop, f'f{t}{"  [S12 window]" if inw else ""}', (8, 22), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
        cv2.putText(crop, f'blue v: trk {hv["trk"][t] * 100:+.1f}  V1 {hv["v1"][t] * 100:+.1f}  {lab3} {hv["v3p"][t] * 100:+.1f} cm',
                    (8, 48), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 255), 1)
        tiles.append(crop)
    while len(tiles) % 4:
        tiles.append(np.zeros_like(tiles[0]))
    grid = np.vstack([np.hstack(tiles[i:i + 4]) for i in range(0, len(tiles), 4)])
    leg = np.zeros((70, grid.shape[1], 3), np.uint8)
    cv2.putText(leg, title, (10, 24), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (255, 255, 255), 1)
    for k, (txt, col) in enumerate((('blue, our track', (0, 0, 255)), ('blue, S12 V1 hold', (255, 255, 0)),
                                    (f'blue, {lab3}', (255, 0, 255)), ('beige, our track', (0, 220, 255)))):
        cv2.circle(leg, (14 + k * 420, 52), 7, col, -1)
        cv2.putText(leg, txt, (28 + k * 420, 58), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1)
    cv2.imwrite(out, np.vstack([leg, grid]))
    print('wrote', out, grid.shape)


if __name__ == '__main__':
    main()
