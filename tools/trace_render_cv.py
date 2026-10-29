"""3-D view of a recorded rollout without FlashCHORD (2026-10-23; for reports when no GPU box is up). Software render with
OpenCV: object meshes (OUR library meshes, the ones the simulator was built from) at their recorded poses, flat shaded,
the robot hands as link skeletons (left magenta, right green), a table disc under the objects; painter's algorithm.
Input: a tools/trace_rollout.py npz (body poses per frame + body labels). Reporting only.
Usage: trace_render_cv.py TRACE.npz MESHDIR OUT.mp4 [--eye x,y,z] [--target x,y,z] [--size 640x480] [--fps 20]
MESHDIR/<name>/<name>.glb for each object body labelled track3_<name>/...
"""
import argparse

import cv2
import numpy as np
import trimesh
from scipy.spatial.transform import Rotation as R

p = argparse.ArgumentParser(); p.add_argument('trace'); p.add_argument('meshdir'); p.add_argument('out')
p.add_argument('--eye', default='0.70,-0.65,1.15'); p.add_argument('--target', default='0.0,0.0,0.62')
p.add_argument('--size', default='640x480'); p.add_argument('--fps', type=float, default=20); p.add_argument('--fov', type=float, default=45)
a = p.parse_args()
d = np.load(a.trace); Q = d['q']; L = [str(x) for x in d['labels']]
W, H = [int(x) for x in a.size.split('x')]
eye, tgt = np.array([float(x) for x in a.eye.split(',')]), np.array([float(x) for x in a.target.split(',')])
fz = tgt - eye; fz /= np.linalg.norm(fz); fx = np.cross(fz, [0, 0, 1.0]); fx /= np.linalg.norm(fx); fy = np.cross(fz, fx)
Rc = np.stack([fx, fy, fz]); f = 0.5 * W / np.tan(np.radians(a.fov) / 2)


def proj(X):  # world (n, 3) -> pixels (n, 2), depth (n,)
    C = (X - eye) @ Rc.T; z = np.maximum(C[:, 2], 1e-3)
    return np.stack([f * C[:, 0] / z + W / 2, f * C[:, 1] / z + H / 2], 1), C[:, 2]


objs = []
for i, l in enumerate(L):
    if l.startswith('track3_') and l.endswith('/object'):
        n = l[len('track3_'):-len('/object')]
        m = trimesh.load(f'{a.meshdir}/{n}/{n}.glb', force='mesh')
        if len(m.faces) > 1500 and hasattr(m, 'simplify_quadric_decimation'):
            try:
                m = m.simplify_quadric_decimation(face_count=1500)
            except Exception:
                pass
        objs.append((i, n, np.asarray(m.vertices, float), np.asarray(m.faces)))
COL = [(60, 170, 255), (255, 150, 60), (120, 230, 120), (200, 120, 255)]
chains = {}
for s in ('left', 'right'):
    cs = [[f'{s}_hand_C_MC', f'{s}_thumb_MC', f'{s}_thumb_PP', f'{s}_thumb_DP']]
    cs += [[f'{s}_hand_C_MC', f'{s}_{g}_PP', f'{s}_{g}_MP', f'{s}_{g}_DP'] for g in ('index', 'middle', 'ring', 'pinky')]
    chains[s] = [[next((i for i, l in enumerate(L) if l.endswith('/' + b)), None) for b in c] for c in cs]
# table disc: under the objects' lowest point at frame 0, centred on them
lows = [(R.from_quat(Q[0, i, 3:7]).apply(V) + Q[0, i, :3])[:, 2].min() for i, _, V, _ in objs]
cxy = np.mean([Q[0, i, :2] for i, *_ in objs], 0); ztab = min(lows) if lows else 0.6
ang = np.linspace(0, 2 * np.pi, 48, endpoint=False); disc = np.c_[cxy[0] + 0.45 * np.cos(ang), cxy[1] + 0.45 * np.sin(ang), np.full(48, ztab)]
light = np.array([0.3, -0.4, 0.85]); light /= np.linalg.norm(light)
out = cv2.VideoWriter(a.out, cv2.VideoWriter_fourcc(*'mp4v'), a.fps, (W, H))
for k in range(len(Q)):
    img = np.full((H, W, 3), (40, 34, 30), np.uint8)
    uv, _ = proj(disc); cv2.fillConvexPoly(img, uv.astype(np.int32), (150, 120, 95), cv2.LINE_AA)
    prims = []                                                       # (depth, kind, data)
    for j, (i, n, V, F) in enumerate(objs):
        X = R.from_quat(Q[k, i, 3:7]).apply(V) + Q[k, i, :3]; uv, z = proj(X)
        T = X[F]; nrm = np.cross(T[:, 1] - T[:, 0], T[:, 2] - T[:, 0]); nrm /= np.maximum(np.linalg.norm(nrm, axis=1, keepdims=True), 1e-12)
        shade = 0.35 + 0.65 * np.abs(nrm @ light); base = np.array(COL[j % len(COL)], float)
        for fi in range(len(F)):
            prims.append((z[F[fi]].mean(), 0, (uv[F[fi]].astype(np.int32), tuple(int(c) for c in base * shade[fi]))))
    for s, c in (('left', (255, 0, 255)), ('right', (0, 220, 0))):
        for ch in chains[s]:
            ids = [i for i in ch if i is not None]
            uv, z = proj(Q[k, ids, :3])
            for q in range(len(ids) - 1):
                prims.append((0.5 * (z[q] + z[q + 1]) - 0.01, 1, (tuple(uv[q].astype(int)), tuple(uv[q + 1].astype(int)), c)))
    for _, kind, dat in sorted(prims, key=lambda t: -t[0]):
        if kind == 0:
            cv2.fillConvexPoly(img, dat[0], dat[1], cv2.LINE_AA)
        else:
            cv2.line(img, dat[0], dat[1], dat[2], 4, cv2.LINE_AA); cv2.circle(img, dat[1], 4, dat[2], -1, cv2.LINE_AA)
    cv2.putText(img, f'frame {k}', (8, H - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (230, 230, 230), 1, cv2.LINE_AA)
    out.write(img)
out.release(); print(f'wrote {a.out} ({len(Q)} frames)')
