"""Video: what the simulated robot does next to the real video (2026-10-23, reporting only; nothing is chosen from it).
Three panels per frame:
  1. the real colour camera (camera a);
  2. the same camera with the SIMULATED rollout drawn on it: objects filled at their simulated poses, the reference
     object (what the scorer compares against, our reconstruction) as a white outline, the robot hand links as a
     skeleton (simulated poses);
  3. a 3-D render of the simulated rollout (tools/render_trace.py mp4, same frames).
Projection chain as tools/ref_overlay_video.py (sim world -> perception world -> camera a). Reads only our own outputs
and a recorded rollout (tools/trace_rollout.py npz), no ground truth.
Usage: sim_vs_real_video.py TRACE.npz REF.parquet REFDIR PERCDIR VIDEO_A MESHDIR SIM_RENDER.mp4 OUT.mp4 [--width 640]
       [--title TEXT] [--score TEXT]
"""
import argparse

import cv2
import numpy as np
import pyarrow.parquet as pq
import trimesh
from scipy.spatial.transform import Rotation as R

p = argparse.ArgumentParser()
[p.add_argument(x) for x in ('trace', 'ref', 'refdir', 'percdir', 'video', 'meshdir', 'render', 'out')]
p.add_argument('--width', type=int, default=640); p.add_argument('--fps', type=float, default=20)
p.add_argument('--title', default='simulated robot'); p.add_argument('--score', default='')
a = p.parse_args()

t = pq.read_table(a.ref); names = t.column('object_body_names')[0].as_py()
T = len(np.array(t.column('robot_left_wrist_position')[0].as_py(), float).reshape(-1, 3))
OP = np.array(t.column('object_body_position')[0].as_py(), float).reshape(T, len(names), 3)
OQ = np.array(t.column('object_body_wxyz')[0].as_py(), float).reshape(T, len(names), 4)[..., [1, 2, 3, 0]]
tf = np.load(f'{a.refdir}/table_frame.npz'); Tinv = np.linalg.inv(tf['T_table_from_world']); zs = tf['object_z_shift']
tnames = [str(x) for x in tf['names']]
W_C = np.load(f'{a.percdir}/poses.npz')['world_T_cam'].astype(float)
h = np.load(f'{a.refdir}/hands_refined.npz'); Ka, Da, off = h['Ka'], h['Da'], int(h['a_offset'])
T_ra = np.linalg.inv(h['T_rect_a'].astype(float)); Wa, Ha = [int(x) for x in h['size_a']]
d = np.load(a.trace); Q = d['q']; L = [str(x) for x in d['labels']]; n_tr = len(Q)
obody = [next(i for i, l in enumerate(L) if l.startswith(f'track3_{n}/')) for n in names]


def to_a(Xs, k):  # sim-world points (n, 3) -> camera-a pixels (n, 2), in-front mask
    Xw = Xs @ Tinv[:3, :3].T + Tinv[:3, 3]
    C = np.linalg.inv(W_C[min(k, len(W_C) - 1)]); Xc = Xw @ C[:3, :3].T + C[:3, 3]
    Xa = Xc @ T_ra[:3, :3].T + T_ra[:3, 3]; ok = Xa[:, 2] > 0.05
    uv, _ = cv2.projectPoints(Xa.reshape(-1, 1, 3), np.zeros(3), np.zeros(3), Ka, Da)
    return uv.reshape(-1, 2), ok


meshes = {}
for n in names:
    m = trimesh.load(f'{a.meshdir}/{n}/{n}.glb', force='mesh')
    if len(m.faces) > 4000 and hasattr(m, 'simplify_quadric_decimation'):
        m = m.simplify_quadric_decimation(face_count=4000)
    meshes[n] = (np.asarray(m.vertices, float), np.asarray(m.faces))
chains = {}
for s in ('left', 'right'):
    cs = [[f'{s}_hand_C_MC', f'{s}_thumb_MC', f'{s}_thumb_PP', f'{s}_thumb_DP']]
    cs += [[f'{s}_hand_C_MC', f'{s}_{f}_PP', f'{s}_{f}_MP', f'{s}_{f}_DP'] for f in ('index', 'middle', 'ring', 'pinky')]
    chains[s] = [[next((i for i, l in enumerate(L) if l.endswith('/' + b)), None) for b in c] for c in cs]
COL = [(60, 200, 255), (255, 120, 60), (120, 255, 120)]


def draw_objects(img, k, sc, poses, filled):
    for j, n in enumerate(names):
        V, Fc = meshes[n]; zshift = zs[tnames.index(n)] if n in tnames else 0.0
        pos, quat = poses(j)
        uv, ok = to_a(R.from_quat(quat).apply(V) + pos - np.array([0, 0, zshift]), k); uv = (uv * sc).astype(np.int32)
        if filled:
            fill = img.copy()
            for fc in Fc[ok[Fc].all(1)]:
                cv2.fillConvexPoly(fill, uv[fc], COL[j % 3])
            img[:] = cv2.addWeighted(fill, 0.5, img, 0.5, 0)
        else:
            mask = np.zeros(img.shape[:2], np.uint8)
            for fc in Fc[ok[Fc].all(1)]:
                cv2.fillConvexPoly(mask, uv[fc], 255)
            cs, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            cv2.drawContours(img, cs, -1, (255, 255, 255), 2, cv2.LINE_AA)


def label(img, txt, y=0, scale=0.55):
    cv2.rectangle(img, (0, y), (img.shape[1], y + 26), (0, 0, 0), -1)
    cv2.putText(img, txt, (6, y + 18), cv2.FONT_HERSHEY_SIMPLEX, scale, (255, 255, 255), 1, cv2.LINE_AA)


cap = cv2.VideoCapture(a.video); real = []
while True:
    ok, f = cap.read()
    if not ok:
        break
    real.append(f)
cap = cv2.VideoCapture(a.render); rend = []
while True:
    ok, f = cap.read()
    if not ok:
        break
    rend.append(f)
sc = a.width / Wa; Hs = int(round(Ha * sc))
out = cv2.VideoWriter(a.out + '.tmp.mp4', cv2.VideoWriter_fourcc(*'mp4v'), a.fps, (3 * a.width, Hs))
for k in range(min(T, n_tr)):
    raw = cv2.resize(real[min(k + off, len(real) - 1)], (a.width, Hs)); ov = raw.copy()
    draw_objects(ov, k, sc, lambda j: (Q[k, obody[j], :3], Q[k, obody[j], 3:7]), True)        # simulated objects
    draw_objects(ov, k, sc, lambda j: (OP[k, j], OQ[k, j]), False)                           # reference outline
    for s, c in (('left', (255, 0, 255)), ('right', (0, 255, 0))):
        for ch in chains[s]:
            ids = [i for i in ch if i is not None]
            uv, ok = to_a(Q[k, ids, :3], k); uv = (uv * sc).astype(int)
            for i0 in range(len(ids) - 1):
                if ok[i0] and ok[i0 + 1]:
                    cv2.line(ov, tuple(uv[i0]), tuple(uv[i0 + 1]), c, 2, cv2.LINE_AA)
    r3 = rend[min(k, len(rend) - 1)] if rend else np.zeros_like(raw)
    r3 = cv2.resize(r3, (a.width, int(round(r3.shape[0] * a.width / r3.shape[1]))))
    r3 = cv2.copyMakeBorder(r3, 0, max(0, Hs - r3.shape[0]), 0, 0, cv2.BORDER_CONSTANT)[:Hs]
    label(raw, 'REAL camera'); label(ov, f'SIM ({a.title}) on the camera: filled = sim, white = target'); label(r3, 'SIM 3-D view')
    cv2.putText(ov, f'frame {k}', (6, Hs - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 255), 2, cv2.LINE_AA)
    if a.score:
        cv2.putText(r3, a.score, (6, Hs - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 255), 2, cv2.LINE_AA)
    out.write(np.hstack([raw, ov, r3]))
out.release(); print(f'wrote {a.out}.tmp.mp4 ({min(T, n_tr)} frames)', flush=True)
