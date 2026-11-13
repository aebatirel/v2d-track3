"""3-D view of an OFFICIAL evaluation rollout from its evaluator parquet (episode_XXXXXX.parquet: achieved and reference
object poses per step), CPU only (2026-10-25; owner asked to see eval 25's best rollout). The simulated objects are drawn
solid and shaded (our library meshes, the ones the simulator used); the reference poses (our perceived object path) are
drawn as a light wireframe ghost; the top line gives each object's centre distance to its reference. The evaluator file
has no robot state, so the hands are not drawn. Reporting only, no ground truth.
Usage: render_eval_rollout.py EPISODE.parquet MESHDIR OUT.mp4 [--title TEXT] [--size 800x600] [--fps 20]
MESHDIR/<name>.glb (a library folder) or MESHDIR/<name>/<name>.glb."""
import argparse, os, subprocess

import cv2
import numpy as np
import pyarrow.parquet as pq
import trimesh
from scipy.spatial.transform import Rotation as R

p = argparse.ArgumentParser(); p.add_argument('parquet'); p.add_argument('out')
p.add_argument('--title', default=''); p.add_argument('--size', default='800x600'); p.add_argument('--fps', type=float, default=20)
p.add_argument('--fov', type=float, default=45); p.add_argument('--pieces', nargs='+', required=True); p.add_argument('--zoom', type=float, default=1.0); a = p.parse_args()
t = pq.read_table(a.parquet).to_pandas(); t = t[t.environment_id == t.environment_id.min()].sort_values(['step', 'object_id'])
names = list(dict.fromkeys(t.object_body_name)); steps = sorted(t.step.unique()); B, K = len(names), len(steps)


def poses(prefix):
    P = np.zeros((K, B, 7))
    for j, n in enumerate(names):
        s = t[t.object_body_name == n].sort_values('step')
        P[:, j, :3] = s[[f'{prefix}_position_{c}' for c in 'xyz']].to_numpy()
        P[:, j, 3:] = s[[f'{prefix}_quaternion_{c}' for c in 'xyzw']].to_numpy()
    return P


ACH, REF = poses('achieved'), poses('reference')
W, H = [int(x) for x in a.size.split('x')]
meshes = []; HULLID = []
PIE = dict(x.split('=', 1) for x in a.pieces)
for n in names:
    src_ = PIE[n]; parts = []
    if src_.endswith('.npz'):
        Z = np.load(src_); parts = [(Z[f'v{i}'], Z[f'f{i}']) for i in range(int(Z['n']))]
    else:
        import glob as _g
        for fp in sorted(_g.glob(src_ + '/*.obj')):
            mm = trimesh.load(fp, force='mesh'); parts.append((np.asarray(mm.vertices), np.asarray(mm.faces)))
    Vs, Fs, hid, off = [], [], [], 0
    for i, (v, f) in enumerate(parts):
        Vs.append(v); Fs.append(f + off); hid += [i] * len(f); off += len(v)
    meshes.append((np.concatenate(Vs).astype(float), np.concatenate(Fs))); HULLID.append(np.array(hid))
ctr = REF[0, :, :3].mean(0); eye = ctr + a.zoom * np.array([0.55, -0.62, 0.48]); tgt = ctr + np.array([0.0, 0.0, 0.05])
fz = tgt - eye; fz /= np.linalg.norm(fz); fx = np.cross(fz, [0, 0, 1.0]); fx /= np.linalg.norm(fx); fy = np.cross(fz, fx)
Rc = np.stack([fx, fy, fz]); f = 0.5 * W / np.tan(np.radians(a.fov) / 2)


def proj(X):
    C = (X - eye) @ Rc.T; z = np.maximum(C[:, 2], 1e-3)
    return np.stack([f * C[:, 0] / z + W / 2, f * C[:, 1] / z + H / 2], 1), C[:, 2]


lows = [(R.from_quat(REF[0, j, 3:]).apply(V) + REF[0, j, :3])[:, 2].min() for j, (V, _) in enumerate(meshes)]
ztab = min(lows); ang = np.linspace(0, 2 * np.pi, 64, endpoint=False)
disc = np.c_[ctr[0] + 0.40 * np.cos(ang), ctr[1] + 0.40 * np.sin(ang), np.full(64, ztab)]
light = np.array([0.3, -0.4, 0.85]); light /= np.linalg.norm(light)
COL = [(60, 170, 255), (255, 150, 60), (120, 230, 120), (200, 120, 255)]   # BGR, by slot unless named below
NAMED = {'blue_cup': (220, 120, 40), 'beige_cup': (150, 200, 235), 'wooden_spoon': (60, 120, 190), 'white_pot': (225, 225, 225),
         'white_pot_lid': (200, 200, 200), 'water_pitcher': (230, 200, 160), 'plastic_dish_rack': (120, 200, 120)}   # (26 Oct: the
COL = [NAMED.get(n, COL[j % len(COL)]) for j, n in enumerate(names)]                                        # blue cup was orange)
tmp = a.out + '.mp4v.mp4'; vw = cv2.VideoWriter(tmp, cv2.VideoWriter_fourcc(*'mp4v'), a.fps, (W, H))
for k in range(K):
    img = np.full((H, W, 3), (40, 34, 30), np.uint8)
    uv, _ = proj(disc); cv2.fillConvexPoly(img, uv.astype(np.int32), (150, 120, 95), cv2.LINE_AA)
    prims = []
    for j, (V, F) in enumerate(meshes):
        X = R.from_quat(ACH[k, j, 3:]).apply(V) + ACH[k, j, :3]; uvj, z = proj(X)
        T = X[F]; nrm = np.cross(T[:, 1] - T[:, 0], T[:, 2] - T[:, 0]); nrm /= np.maximum(np.linalg.norm(nrm, axis=1, keepdims=True), 1e-12)
        shade = (0.35 + 0.65 * np.abs(nrm @ light)) * (0.72 + 0.28 * ((HULLID[j] * 0.618) % 1.0)); base = np.array(COL[j], float)
        for fi in range(len(F)):
            prims.append((z[F[fi]].mean(), uvj[F[fi]].astype(np.int32), tuple(int(c) for c in base * shade[fi])))
    for _, poly, c in sorted(prims, key=lambda r: -r[0]):
        cv2.fillConvexPoly(img, poly, c, cv2.LINE_AA)
    ghost = img.copy()
    for j, (V, F) in enumerate(meshes):                               # reference: wireframe ghost on top
        X = R.from_quat(REF[k, j, 3:]).apply(V) + REF[k, j, :3]; uvj, _ = proj(X)
        edges = np.unique(np.sort(np.r_[F[:, [0, 1]], F[:, [1, 2]], F[:, [2, 0]]], axis=1), axis=0)[::3]
        for e0, e1 in edges:
            cv2.line(ghost, tuple(uvj[e0].astype(int)), tuple(uvj[e1].astype(int)), (235, 235, 235), 1, cv2.LINE_AA)
    img = cv2.addWeighted(ghost, 0.55, img, 0.45, 0)
    d = [100 * np.linalg.norm(ACH[k, j, :3] - REF[k, j, :3]) for j in range(B)]
    cv2.putText(img, a.title, (10, 24), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (240, 240, 240), 1, cv2.LINE_AA)
    cv2.putText(img, '  '.join(f'{n}: {x:.1f} cm off' for n, x in zip(names, d)), (10, 48), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (230, 230, 230), 1, cv2.LINE_AA)
    cv2.putText(img, f'frame {k}   solid = simulated COLLISION pieces (shaded per piece), wireframe = reference', (10, H - 12), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (220, 220, 220), 1, cv2.LINE_AA)
    vw.write(img)
vw.release()
subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-i', tmp, '-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-crf', '23', a.out], check=True)
os.remove(tmp); print(f'wrote {a.out} ({K} frames)')
