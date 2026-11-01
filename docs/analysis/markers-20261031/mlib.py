"""Shared helpers for the GT-free marker correction layer (markers-20261031).
Inference side only: videos (ego_cam_b/c), the public camera calibration, our perc2 tracks and our own meshes.
Nothing here reads mocap, the parquet pose field, or any scan."""
import json, os
import numpy as np, cv2

S = os.environ.get('MK_SCRATCH', '/tmp/claude-0/-home-user-v2d-track3/6190fffb-f3a1-5d0e-84bd-7370ece99c2f/scratchpad')
CALIB = f'{S}/eg/dl/track_3/public/meta/camera_calibration.json'
VID = {('eval', 'c'): f'{S}/eg/dlvid/track_3/evaluation/videos/chunk-000/observation.images.ego_cam_c/episode_{{:06d}}.mp4',
       ('eval', 'b'): f'{S}/mk/dl/track_3/evaluation/videos/chunk-000/observation.images.ego_cam_b/episode_{{:06d}}.mp4',
       ('public', 'c'): f'{S}/eg/dlvid/track_3/public/videos/chunk-000/observation.images.ego_cam_c/episode_{{:06d}}.mp4',
       ('public', 'b'): f'{S}/mk/dl/track_3/public/videos/chunk-000/observation.images.ego_cam_b/episode_{{:06d}}.mp4'}
# eval perception runs feeding the pack references (docs/analysis/evalgross-20261031/fetch.py)
P6 = '20261026-pack6-5203d42'
PERC_EVAL = {e: P6 for e in (1, 3, 5, 6, 10, 15, 16, 19, 20, 28, 35, 36, 37, 38)}
PERC_EVAL.update({8: '20261025-evb0810-ee7ba8e', 14: '20261025-evb1420-ee7ba8e', 25: '20261026-c25s42-feb0407',
                  30: '20261025-std30-ee7ba8e', 32: '20261026-fr32s46b-5e0e100', 33: '20261026-fr3233s43-6a8a0e2'})
GUARD = [0, 11, 12, 18, 21, 23, 24, 31]


def poses_path(split, e):
    if split == 'eval':
        return f'{S}/eg/dl/runs/{PERC_EVAL[e]}/perc2/ep{e}/poses.npz'
    d = f'runs/20261025-guard-fe3f407/results/sweep/guard/ep{e}' if e in GUARD else \
        f'runs/20261025-sweep-a894083/results/sweep/base/ep{e}'
    return f'{S}/eg/dlpub/{d}/poses.npz'


class Rig:
    """Rectified ego stereo rig exactly as pipeline/perc2.py builds it (left = ego_cam_c, right = ego_cam_b)."""
    def __init__(self):
        C = json.load(open(CALIB)); cam = C['cameras']
        sp = [p for p in C['stereo_pairs'] if p['camera'] == 'ego'][0]
        K_ = lambda n: np.array(cam[n]['intrinsic_matrix'], float)
        D_ = lambda n: np.array(cam[n]['distortion_coefficients'], float)
        Kc, dc, Kb, db = K_('ego_cam_c'), D_('ego_cam_c'), K_('ego_cam_b'), D_('ego_cam_b')
        E = np.array(sp['left_to_right'], float); R, T = E[:3, :3].copy(), E[:3, 3].reshape(3, 1).copy()
        self.SZ, self.RSZ = (1280, 800), (1600, 1000)
        R1, R2, P1, P2, Q, _, _ = cv2.stereoRectify(Kc, dc, Kb, db, self.SZ, R, T, alpha=0, newImageSize=self.RSZ,
                                                    flags=cv2.CALIB_ZERO_DISPARITY)
        self.MC = cv2.initUndistortRectifyMap(Kc, dc, R1, P1, self.RSZ, cv2.CV_32FC1)
        self.MB = cv2.initUndistortRectifyMap(Kb, db, R2, P2, self.RSZ, cv2.CV_32FC1)
        self.FR = P1[0, 0]; self.BASE = -P2[0, 3] / P2[0, 0]; self.KR = P1[:3, :3].copy()
        self.cx, self.cy = P1[0, 2], P1[1, 2]

    def proj(self, X):
        """camera (rectified-left) points (N,3) -> left uv (N,2), right uv (N,2)."""
        X = np.atleast_2d(X); z = X[:, 2:3]
        uL = self.FR * X[:, :2] / z + [self.cx, self.cy]
        uR = uL.copy(); uR[:, 0] -= self.FR * self.BASE / z[:, 0]
        return uL, uR

    def tri(self, uL, uR):
        """left uv + right uv (same row) -> camera point."""
        d = uL[..., 0] - uR[..., 0]; z = self.FR * self.BASE / d
        x = (uL[..., 0] - self.cx) * z / self.FR; y = (0.5 * (uL[..., 1] + uR[..., 1]) - self.cy) * z / self.FR
        return np.stack([x, y, z], -1)


def read_frames(path, maxn=None, remap=None):
    """grey frames of a video; with remap=(mapx, mapy) each frame is rectified as it is read (saves memory)."""
    cap = cv2.VideoCapture(path); out = []
    while True:
        ok, f = cap.read()
        if not ok or (maxn and len(out) >= maxn): break
        g = cv2.cvtColor(f, cv2.COLOR_BGR2GRAY)
        out.append(cv2.remap(g, remap[0], remap[1], cv2.INTER_LINEAR) if remap is not None else g)
    return out


def rectified(rig, split, e, maxn=None):
    """rectified left (ego_cam_c) and right (ego_cam_b) frames, exactly as pipeline/perc2.py builds them."""
    rc = read_frames(VID[(split, 'c')].format(e), maxn, rig.MC); rb = read_frames(VID[(split, 'b')].format(e), maxn, rig.MB)
    n = min(len(rc), len(rb))
    return rc[:n], rb[:n]
