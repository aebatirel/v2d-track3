"""Visual QA of object tracking (no ground truth): project each tracked mesh onto the rectified-left mono frames.

Draws the mesh's surface samples (one colour per object) at the tracked pose cam_T_<obj> on N evenly spaced frames
and tiles them into one JPEG. Use it on eval episodes, where no score exists, to see whether a track holds.
Usage: python track_overlay.py --video ep_c.mp4 --poses poses.npz --calib calib.json --mesh obj=path.glb[,obj2=...]
                               --out overlay.jpg [--frames 8]
"""
import argparse, json
import numpy as np, cv2, trimesh


def rectify_maps(calib_path):
    C = json.load(open(calib_path)); cam = C['cameras']
    sp = [p for p in C['stereo_pairs'] if p['camera'] == 'ego'][0]
    K_ = lambda n: np.array(cam[n]['intrinsic_matrix'], float)  # noqa: E731
    D_ = lambda n: np.array(cam[n]['distortion_coefficients'], float)  # noqa: E731
    E = np.array(sp['left_to_right'], float)
    R1, R2, P1, P2, Q, _, _ = cv2.stereoRectify(K_('ego_cam_c'), D_('ego_cam_c'), K_('ego_cam_b'), D_('ego_cam_b'),
                                                (1280, 800), E[:3, :3].copy(), E[:3, 3].reshape(3, 1).copy(),
                                                alpha=0, newImageSize=(1600, 1000), flags=cv2.CALIB_ZERO_DISPARITY)
    MC = cv2.initUndistortRectifyMap(K_('ego_cam_c'), D_('ego_cam_c'), R1, P1, (1600, 1000), cv2.CV_32FC1)
    return MC, P1[:3, :3]


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('--video', required=True); p.add_argument('--poses', required=True)
    p.add_argument('--calib', required=True); p.add_argument('--mesh', required=True); p.add_argument('--out', required=True)
    p.add_argument('--frames', type=int, default=8); p.add_argument('--width', type=int, default=640)
    a = p.parse_args()
    MC, K = rectify_maps(a.calib)
    P = np.load(a.poses)
    objs = [s.split('=', 1) for s in a.mesh.split(',')]
    pts = {n: trimesh.sample.sample_surface(trimesh.load(f, force='mesh'), 1500, seed=0)[0] for n, f in objs}
    cols = [(0, 0, 255), (0, 200, 0), (255, 0, 0), (0, 200, 255)]
    cap = cv2.VideoCapture(a.video); frames = []
    while True:
        ok, f = cap.read()
        if not ok:
            break
        frames.append(f)
    N = min(len(frames), *(len(P[f'cam_T_{n}']) for n, _ in objs))
    tiles = []
    for t in np.linspace(0, N - 1, a.frames).round().astype(int):
        img = cv2.remap(frames[t], MC[0], MC[1], cv2.INTER_LINEAR)
        for j, (n, _) in enumerate(objs):
            T = P[f'cam_T_{n}'][t]; X = pts[n] @ T[:3, :3].T + T[:3, 3]
            uv = (X[:, :2] / X[:, 2:3]) * [K[0, 0], K[1, 1]] + [K[0, 2], K[1, 2]]
            for u, v in uv[(X[:, 2] > 0.05)].astype(int):
                if 0 <= u < img.shape[1] and 0 <= v < img.shape[0]:
                    cv2.circle(img, (u, v), 2, cols[j % 4], -1)
        cv2.putText(img, f'f{t}', (20, 60), cv2.FONT_HERSHEY_SIMPLEX, 2, (255, 255, 255), 4)
        tiles.append(cv2.resize(img, (a.width, int(a.width * img.shape[0] / img.shape[1]))))
    while len(tiles) % 4:
        tiles.append(np.zeros_like(tiles[0]))
    rows = [np.hstack(tiles[i:i + 4]) for i in range(0, len(tiles), 4)]
    cv2.imwrite(a.out, np.vstack(rows), [cv2.IMWRITE_JPEG_QUALITY, 80])
    print('wrote', a.out, 'frames', N, 'objects', [n for n, _ in objs])


if __name__ == '__main__':
    main()
