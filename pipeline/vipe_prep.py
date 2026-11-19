"""Frames for MetricTrail (ViPE), in perc2's exact camera geometry (2026-11-19, camera-arms test,
docs/analysis/camarms-20261119/PREREG.md). GT-free: reads the videos, the calibration and the parquet's row count only.

perc2 works in the rectified-left (camera c) frame at 1600 x 1000 with K = P1 of cv2.stereoRectify. This script repeats
that rectification for camera c (and camera b, for the stereo runner), resizes both by SCALE (default 0.32 -> 512 x 320,
INTER_AREA) and writes:
  OUT/c/00000.png ...       rectified camera c, grey (cv2.imread gives ViPE 3 equal channels)
  OUT/b/00000.png ...       rectified camera b, grey, same raster (stereo runner)
  OUT/K.json                {"fx","fy","cx","cy","input_hw": [H, W]} in those pixels (ViPE pipeline.optional.intrinsics)
  OUT/meta.json             frame count, scale, rectified K at 1600 x 1000, baseline
Usage: python vipe_prep.py EP OUT [--t3 /content/t3] [--split public|eval] [--scale 0.32]
"""
import argparse, json, os
import numpy as np, cv2

ap = argparse.ArgumentParser()
ap.add_argument('ep', type=int); ap.add_argument('out')
ap.add_argument('--t3', default='/content/t3'); ap.add_argument('--split', default='public')
ap.add_argument('--scale', type=float, default=0.32)
a = ap.parse_args()
os.makedirs(f'{a.out}/c', exist_ok=True); os.makedirs(f'{a.out}/b', exist_ok=True)

# calibration + rectification: identical to pipeline/perc2.py (left = ego_cam_c, right = ego_cam_b)
C = json.load(open(f'{a.t3}/calib.json')); cam = C['cameras']
sp = [p for p in C['stereo_pairs'] if p['camera'] == 'ego'][0]
K_ = lambda n: np.array(cam[n]['intrinsic_matrix'], float)
D_ = lambda n: np.array(cam[n]['distortion_coefficients'], float)
Kc, dc, Kb, db = K_('ego_cam_c'), D_('ego_cam_c'), K_('ego_cam_b'), D_('ego_cam_b')
E = np.array(sp['left_to_right'], float); R, T = E[:3, :3].copy(), E[:3, 3].reshape(3, 1).copy()
SZ, RSZ = (1280, 800), (1600, 1000)
R1, R2, P1, P2, Q, _, _ = cv2.stereoRectify(Kc, dc, Kb, db, SZ, R, T, alpha=0, newImageSize=RSZ, flags=cv2.CALIB_ZERO_DISPARITY)
MC = cv2.initUndistortRectifyMap(Kc, dc, R1, P1, RSZ, cv2.CV_32FC1)
MB = cv2.initUndistortRectifyMap(Kb, db, R2, P2, RSZ, cv2.CV_32FC1)
FR = P1[0, 0]; BASE = -P2[0, 3] / P2[0, 0]; KR = P1[:3, :3].copy()

VD = f'{a.t3}/v' if a.split == 'public' else f'{a.t3}/eval/v'
def frames(path):
    cap = cv2.VideoCapture(path); out = []
    while True:
        ok, f = cap.read()
        if not ok: break
        out.append(cv2.cvtColor(f, cv2.COLOR_BGR2GRAY))
    return out
fc, fb = frames(f'{VD}/ep{a.ep}_c.mp4'), frames(f'{VD}/ep{a.ep}_b.mp4')
if a.split == 'public':                                   # the parquet's row count (no pose is read)
    import pyarrow.parquet as pq
    NROWS = pq.read_metadata(f'{a.t3}/ep{a.ep}.parquet').num_rows
else:
    NROWS = len(fc)
N = min(len(fc), len(fb), NROWS)                          # = perc2's N
W, H = int(round(RSZ[0] * a.scale)), int(round(RSZ[1] * a.scale))
s = a.scale
for i in range(N):
    for side, f, M in (('c', fc[i], MC), ('b', fb[i], MB)):
        r = cv2.remap(f, M[0], M[1], cv2.INTER_LINEAR)
        cv2.imwrite(f'{a.out}/{side}/{i:05d}.png', cv2.resize(r, (W, H), interpolation=cv2.INTER_AREA))
# pixel-centre convention: x' = (x + 0.5) * s - 0.5
K = dict(fx=float(KR[0, 0] * s), fy=float(KR[1, 1] * s), cx=float((KR[0, 2] + 0.5) * s - 0.5),
         cy=float((KR[1, 2] + 0.5) * s - 0.5), input_hw=[H, W])
json.dump(K, open(f'{a.out}/K.json', 'w'), indent=1)
json.dump(dict(episode=a.ep, split=a.split, frames=N, video_frames=[len(fc), len(fb)], rows=NROWS, scale=s, hw=[H, W],
               KR_1600x1000=KR.tolist(), baseline_m=float(BASE), focal_rect=float(FR)),
          open(f'{a.out}/meta.json', 'w'), indent=1)
print(f'ep{a.ep}: {N} frames -> {a.out} ({W}x{H}), fx {K["fx"]:.2f}, baseline {BASE:.4f} m')
