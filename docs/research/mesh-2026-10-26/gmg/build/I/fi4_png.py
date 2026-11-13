"""PREREG F-I4 / INTERLOCK 20 (board slot under the owner's waiver): draw each slotted plate of a delivered round over
ego cam_a RGB frames (our tracks place it; looked at, not a measurement).

  GMG_MODE=dev GMG_RUN=<run> python fi4_png.py <r0 dir> <bundle dir> <video> <calib> <decisions.json> <out_dir> [ep]

Per board: one assembled frame of the pair's INSERTION run (median) and one frame where the board is separated from
its partner (the middle good separated frame), the slotted pieces' edges in green, the analytic slot box in red, the
unslotted plate body in thin yellow. Writes <out_dir>/ep<N>_fi4_<obj>.png."""
import json
import os
import sys

import numpy as np
import cv2
import trimesh

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))
from gmg import guard, interlock as IL, silhouette as SI, contact as CT  # noqa: E402

r0, bdir, video, calib, decp, out = sys.argv[1:7]
ep = int(sys.argv[7]) if len(sys.argv) > 7 else 24
guard.set_run(os.environ['GMG_RUN'])
b = IL.load_bundle_any(bdir)
geo = SI.geometry(calib)
dec = json.load(open(decp))
os.makedirs(out, exist_ok=True)


def hull_edges(V):
    m = trimesh.convex.convex_hull(V)
    E = m.face_adjacency_edges[m.face_adjacency_angles > 1e-3]
    return m.vertices, E


def box_edges(box):
    A = np.asarray(box['axes']); c = np.asarray(box['centre']); h = np.asarray(box['half'])
    s = np.array([[x, y, z] for x in (-1, 1) for y in (-1, 1) for z in (-1, 1)], float)
    V = c + (s * h) @ A
    E = [(i, j) for i in range(8) for j in range(i + 1, 8) if bin(i ^ j).count('1') == 1]
    return V, np.array(E)


def draw(im, V, E, T, col, th):
    uv, _ = SI.project_a(geo, V @ T[:3, :3].T + T[:3, 3])
    for i, j in E:
        if np.isfinite(uv[i]).all() and np.isfinite(uv[j]).all():
            cv2.line(im, tuple(int(x) for x in uv[i]), tuple(int(x) for x in uv[j]), col, th, cv2.LINE_AA)
    return uv[np.isfinite(uv).all(1)]


for r in dec:
    if 'owner_waiver_fi4' not in r.get('flags', []) or r.get('decision') != 'CARVE':
        continue
    obj = r['target']
    W = r['waiver_fi4']
    pdir = os.path.join(r0, obj)
    pieces = [np.asarray(trimesh.load(os.path.join(pdir, f), force='mesh').vertices)
              for f in sorted(os.listdir(pdir)) if f.startswith('piece_')]
    run = r['run']
    a0, a1 = run['assembled'] if run.get('assembled') else (run['frames'][0], run['frames'][1])
    f_asm = int((a0 + a1) // 2)
    f_asm = min(b.frames(), key=lambda f: abs(f - f_asm))
    sep = sorted(set(CT.separated_for(b.meta['contact'], obj, b.partners(obj))) & set(b.good_frames(obj)))
    f_sep = sep[len(sep) // 2] if sep else None
    frames = [f for f in (f_sep, f_asm) if f is not None]
    imgs = SI.read_frames(video, frames)
    tiles = []
    for f in frames:
        im = imgs[f].copy()
        T = b.poses[f'cam_T_{obj}'][f].astype(np.float64)
        Vb, Eb = box_edges(W['body'][obj]['box'])
        pts = [draw(im, Vb, Eb, T, (0, 220, 255), 1)]
        for V in pieces:
            Vv, Ev = hull_edges(V)
            pts.append(draw(im, Vv, Ev, T, (0, 255, 0), 2))
        Vs, Es = box_edges(W['slot'][obj]['box'])
        pts.append(draw(im, Vs, Es, T, (0, 0, 255), 2))
        P = np.vstack([p for p in pts if len(p)])
        x0, y0 = np.maximum(P.min(0).astype(int) - 80, 0)
        x1, y1 = np.minimum(P.max(0).astype(int) + 80, [im.shape[1], im.shape[0]])
        crop = im[y0:y1, x0:x1].copy()
        kind = 'assembled' if f == f_asm else 'separated'
        sl = W['slot'][obj]
        cv2.putText(crop, f'ep{ep} {obj} frame {f} ({kind}) F-I4 owner waiver, SIMULATOR copy only', (8, 22),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
        cv2.putText(crop, f'green slotted plate pieces, red slot w {sl["w_mm"]} D {sl["D_mm"]} mm, yellow unslotted body',
                    (8, 46), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 255), 2)
        tiles.append(cv2.resize(crop, (640, int(640 * crop.shape[0] / crop.shape[1]))))
    h = max(t.shape[0] for t in tiles)
    tiles = [np.vstack([t, np.zeros((h - t.shape[0], t.shape[1], 3), np.uint8)]) for t in tiles]
    path = os.path.join(out, f'ep{ep}_fi4_{obj}.png')
    cv2.imwrite(path, np.hstack(tiles))
    print(path, 'frames', frames)
