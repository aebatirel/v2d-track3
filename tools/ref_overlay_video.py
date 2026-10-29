"""Video of our reconstruction drawn on the real colour camera (2026-10-23): the reference the simulator follows (object
meshes at their reference poses, the MANO hand estimated from the video, the retargeted robot hand) projected into
camera a, next to the plain camera frames. Reads only our own outputs (no ground truth).

Frames: reference/perception frame k <-> camera-a frame k + a_offset. Sim world -> perception world: inverse of mkref's
T_table_from_world after removing the per-object z snap; perception world -> rectified-left camera: inv(world_T_cam[k]);
rectified-left -> camera a: inv(hands_refined.npz T_rect_a), projected with its Ka / Da. Check printed at the start: the
projected MANO joints vs the 2-D hand detections in camera a (median px; ep3: 11 px on 2028 px).
Usage: ref_overlay_video.py REF.parquet REFDIR PERCDIR VIDEO_A MESHDIR OUT.mp4 [--width 960] [--every 1]
"""
import argparse

import cv2
import numpy as np
import pyarrow.parquet as pq
import trimesh
from scipy.spatial.transform import Rotation as R

p = argparse.ArgumentParser(); [p.add_argument(x) for x in ('ref', 'refdir', 'percdir', 'video', 'meshdir', 'out')]
p.add_argument('--width', type=int, default=960); p.add_argument('--every', type=int, default=1); p.add_argument('--fps', type=float, default=20)
a = p.parse_args()

t = pq.read_table(a.ref); names = t.column('object_body_names')[0].as_py()
T = len(np.array(t.column('robot_left_wrist_position')[0].as_py(), float).reshape(-1, 3))
OP = np.array(t.column('object_body_position')[0].as_py(), float).reshape(T, len(names), 3)
OQ = np.array(t.column('object_body_wxyz')[0].as_py(), float).reshape(T, len(names), 4)[..., [1, 2, 3, 0]]
tf = np.load(f'{a.refdir}/table_frame.npz'); Tinv = np.linalg.inv(tf['T_table_from_world']); zs = tf['object_z_shift']
tnames = [str(x) for x in tf['names']]
W_C = np.load(f'{a.percdir}/poses.npz')['world_T_cam'].astype(float)
h = np.load(f'{a.refdir}/hands_refined.npz'); Ka, Da, off = h['Ka'], h['Da'], int(h['a_offset'])
T_ra = np.linalg.inv(h['T_rect_a'].astype(float))   # hands_mp stores T_rect_a = inv(T_a_rect): camera a -> rectified
Wa, Ha = [int(x) for x in h['size_a']]


def to_a(Xs, k):  # sim-world points (n, 3) -> camera-a pixels (n, 2), in-front mask
    Xw = Xs @ Tinv[:3, :3].T + Tinv[:3, 3]
    C = np.linalg.inv(W_C[min(k, len(W_C) - 1)]); Xc = Xw @ C[:3, :3].T + C[:3, 3]
    Xa = Xc @ T_ra[:3, :3].T + T_ra[:3, 3]; ok = Xa[:, 2] > 0.05
    uv, _ = cv2.projectPoints(Xa.reshape(-1, 1, 3), np.zeros(3), np.zeros(3), Ka, Da)
    return uv.reshape(-1, 2), ok


meshes = {}
for n in names:
    m = trimesh.load(f'{a.meshdir}/{n}/{n}.glb', force='mesh')
    if len(m.faces) > 6000:
        m = m.simplify_quadric_decimation(face_count=6000) if hasattr(m, 'simplify_quadric_decimation') else m
    meshes[n] = (np.asarray(m.vertices, float), np.asarray(m.faces))
MANO = {s: np.array(t.column(f'mano_{s}_joints')[0].as_py(), float).reshape(T, 21, 3) for s in ('left', 'right')}
BONES = [(0, 1), (1, 2), (2, 3), (3, 4), (0, 5), (5, 6), (6, 7), (7, 8), (0, 9), (9, 10), (10, 11), (11, 12),
         (0, 13), (13, 14), (14, 15), (15, 16), (0, 17), (17, 18), (18, 19), (19, 20)]
ROB = {}
for s in ('left', 'right'):
    fn = t.column(f'{s}_robot_frame_names')[0].as_py(); F = np.array(t.column(f'robot_{s}_frames')[0].as_py(), float).reshape(T, -1, 7)[..., :3]
    chains = [[f'{s}_hand_C_MC', f'{s}_thumb_MC', f'{s}_thumb_PP', f'{s}_thumb_DP', f'{s}_thumb_tip_site']]
    for fi in ('index', 'middle', 'ring', 'pinky'):
        chains.append([f'{s}_hand_C_MC', f'{s}_{fi}_PP', f'{s}_{fi}_MP', f'{s}_{fi}_DP', f'{s}_{fi}_tip_site'])
    ROB[s] = (F, [[fn.index(x) for x in c if x in fn] for c in chains])

# projection check against the 2-D hand detections (camera a)
errs = []
for s in ('left', 'right'):
    uv_det, meas = h[f'uv_a_{s}'], h[f'measured_{s}'].astype(bool)
    for k in np.nonzero(meas)[0][::10]:
        uv, ok = to_a(MANO[s][k], k); d = np.linalg.norm(uv - uv_det[k], axis=1)[ok]
        if len(d):
            errs.append(np.median(d))
print(f'projection check: MANO joints vs 2-D detections, median {np.median(errs):.1f} px over {len(errs)} frames '
      f'(image {Wa}x{Ha})', flush=True)

COL = [(60, 200, 255), (255, 120, 60), (120, 255, 120)]  # objects (BGR): orange-ish, blue-ish, green
cap = cv2.VideoCapture(a.video); frames = []
while True:
    ok, f = cap.read()
    if not ok:
        break
    frames.append(f)
sc = a.width / Wa; Hs = int(round(Ha * sc)); out = cv2.VideoWriter(a.out + '.tmp.mp4', cv2.VideoWriter_fourcc(*'mp4v'), a.fps, (2 * a.width, Hs))
for k in range(0, T, a.every):
    img = frames[min(k + off, len(frames) - 1)]; raw = cv2.resize(img, (a.width, Hs)); ov = raw.copy(); fill = ov.copy()
    for j, n in enumerate(names):
        V, Fc = meshes[n]; zshift = zs[tnames.index(n)] if n in tnames else 0.0
        Xs = R.from_quat(OQ[k, j]).apply(V) + OP[k, j] - np.array([0, 0, zshift])
        uv, ok = to_a(Xs, k); uv = (uv * sc).astype(np.int32)
        for fc in Fc[ok[Fc].all(1)]:
            cv2.fillConvexPoly(fill, uv[fc], COL[j % 3])
    ov = cv2.addWeighted(fill, 0.45, ov, 0.55, 0)
    for s, c in (('left', (255, 0, 255)), ('right', (0, 255, 0))):          # MANO hand from the video: magenta / green
        uv, ok = to_a(MANO[s][k], k); uv = (uv * sc).astype(int)
        for i0, i1 in BONES:
            if ok[i0] and ok[i1]:
                cv2.line(ov, tuple(uv[i0]), tuple(uv[i1]), c, 2, cv2.LINE_AA)
        F, chains = ROB[s]; uv, ok = to_a(F[k], k); uv = (uv * sc).astype(int)
        for ch in chains:                                                     # robot hand the simulator tracks: white
            for i0, i1 in zip(ch, ch[1:]):
                if ok[i0] and ok[i1]:
                    cv2.line(ov, tuple(uv[i0]), tuple(uv[i1]), (255, 255, 255), 1, cv2.LINE_AA)
    for im, txt in ((raw, 'REAL camera'), (ov, 'OUR RECONSTRUCTION (what the sim follows)')):
        cv2.rectangle(im, (0, 0), (im.shape[1], 30), (0, 0, 0), -1); cv2.putText(im, txt, (8, 21), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1, cv2.LINE_AA)
    cv2.putText(ov, f'frame {k}', (8, Hs - 12), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2, cv2.LINE_AA)
    cv2.putText(ov, 'objects: filled  |  hand from video: green R / magenta L  |  robot hand: white', (8, Hs - 36),
                cv2.FONT_HERSHEY_SIMPLEX, 0.45, (255, 255, 255), 1, cv2.LINE_AA)
    out.write(np.hstack([raw, ov]))
out.release(); print(f'wrote {a.out}.tmp.mp4 ({T // a.every} frames)', flush=True)
