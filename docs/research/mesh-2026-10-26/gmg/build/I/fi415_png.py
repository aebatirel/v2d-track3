"""PREREG F-I4.15 (board slot round 2): draw the outline-polygon plate body (and, when built, the slot box and the slotted
prisms) of each board over ego cam_a RGB frames (our tracks place it; looked at, not a measurement).

  GMG_MODE=dev GMG_RUN=<run> python fi415_png.py <decisions.json> <r0 dir or -> <bundle dir> <video> <calib> <out_dir> [ep]

Per board with an F-I4.15 body record: one separated frame (the middle good separated frame) and one assembled frame of
the pair's INSERTION run (median); yellow = the polygon (top and bottom faces), green = the slotted prisms of the round
folder (piece_XX.obj) when it holds them, red = the analytic slot box. Writes <out_dir>/ep<N>_fi415_<obj>.png.
render() is reused by fi415_ep23.py (body only)."""
import json
import os
import sys

import numpy as np
import cv2
import trimesh

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))
from gmg import guard, interlock as IL, silhouette as SI, contact as CT  # noqa: E402


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


def poly_edges(body):
    A = np.asarray(body['axes']); c = np.asarray(body['centre']); h = float(body['half'][2])
    Q = np.asarray(body['poly'], float)
    B = c + Q[:, :1] * A[0] + Q[:, 1:2] * A[1]
    V = np.vstack([B - h * A[2], B + h * A[2]])
    n = len(Q)
    E = [(i, (i + 1) % n) for i in range(n)] + [(n + i, n + (i + 1) % n) for i in range(n)]
    return V, np.array(E)


def draw(geo, im, V, E, T, col, th):
    uv, _ = SI.project_a(geo, V @ T[:3, :3].T + T[:3, 3])
    for i, j in E:
        if np.isfinite(uv[i]).all() and np.isfinite(uv[j]).all():
            cv2.line(im, tuple(int(x) for x in uv[i]), tuple(int(x) for x in uv[j]), col, th, cv2.LINE_AA)
    return uv[np.isfinite(uv).all(1)]


def render(b, geo, video, obj, body, frames, path, lines, slot_box=None, pieces=()):
    imgs = SI.read_frames(video, [f for f, _ in frames])
    tiles = []
    for f, kind in frames:
        im = imgs[f].copy()
        T = b.poses[f'cam_T_{obj}'][f].astype(np.float64)
        pts = []
        for V in pieces:
            Vv, Ev = hull_edges(V)
            pts.append(draw(geo, im, Vv, Ev, T, (0, 255, 0), 1))
        Vp, Ep = poly_edges(body)
        pts.append(draw(geo, im, Vp, Ep, T, (0, 220, 255), 2))
        if slot_box is not None:
            Vs, Es = box_edges(slot_box)
            pts.append(draw(geo, im, Vs, Es, T, (0, 0, 255), 2))
        P = np.vstack([p for p in pts if len(p)])
        x0, y0 = np.maximum(P.min(0).astype(int) - 80, 0)
        x1, y1 = np.minimum(P.max(0).astype(int) + 80, [im.shape[1], im.shape[0]])
        crop = im[y0:y1, x0:x1].copy()
        crop = cv2.resize(crop, (720, int(720 * crop.shape[0] / crop.shape[1])))
        txt = [f'frame {f} ({kind})'] + list(lines)
        band = np.zeros((14 + 18 * len(txt), crop.shape[1], 3), np.uint8)
        for q, s in enumerate(txt):
            cv2.putText(band, s[:110], (6, 16 + 18 * q), cv2.FONT_HERSHEY_SIMPLEX, 0.42, (255, 255, 255), 1,
                        cv2.LINE_AA)
        tiles.append(np.vstack([band, crop]))
    h = max(t.shape[0] for t in tiles)
    tiles = [np.vstack([t, np.zeros((h - t.shape[0], t.shape[1], 3), np.uint8)]) for t in tiles]
    cv2.imwrite(path, np.hstack(tiles))
    return path


def sep_frame(b, obj):
    sep = sorted(set(CT.separated_for(b.meta['contact'], obj, b.partners(obj))) & set(b.good_frames(obj)))
    return sep[len(sep) // 2] if sep else None


def main():
    decp, r0, bdir, video, calib, out = sys.argv[1:7]
    ep = int(sys.argv[7]) if len(sys.argv) > 7 else 24
    guard.set_run(os.environ['GMG_RUN'])
    b = IL.load_bundle_any(bdir)
    geo = SI.geometry(calib)
    dec = json.load(open(decp))
    os.makedirs(out, exist_ok=True)
    for r in dec:
        W = r.get('waiver_fi4') or {}
        obj = r['target']
        bd = (W.get('body') or {}).get(obj) or {}
        if not bd.get('ok') or 'poly' not in (bd.get('box') or {}):
            continue
        sl = (W.get('slot') or {}).get(obj) or {}
        pieces = []
        pdir = os.path.join(r0, obj) if r0 != '-' else None
        if r.get('decision') == 'CARVE' and pdir and os.path.isdir(pdir):
            pieces = [np.asarray(trimesh.load(os.path.join(pdir, f), force='mesh').vertices)
                      for f in sorted(os.listdir(pdir)) if f.startswith('piece_')]
        run = r['run']
        a0, a1 = run['assembled'] if run.get('assembled') else (run['frames'][0], run['frames'][1])
        f_asm = min(b.frames(), key=lambda f: abs(f - int((a0 + a1) // 2)))
        fs = sep_frame(b, obj)
        frames = [(f, k) for f, k in ((fs, 'separated'), (f_asm, 'assembled')) if f is not None]
        pg = bd.get('polygon') or {}
        bud = (W.get('budget') or {}).get(obj) or {}
        lines = [f'ep{ep} {obj} F-I4.15 (owner waiver) SIMULATOR copy only; decision {r["decision"]}'
                 + (f' (gate {W.get("gate_fail")})' if W.get('gate_fail') else ''),
                 f'yellow polygon body t {bd.get("t_mm")} mm, {pg.get("vertices")} vertices; green slotted prisms '
                 f'{len(pieces)}',
                 f'red slot w {sl.get("w_mm")} D {sl.get("D_mm")} mm (from the polygon edge); budget {bud.get("vol_share")}']
        p = render(b, geo, video, obj, bd['box'], frames, os.path.join(out, f'ep{ep}_fi415_{obj}.png'), lines,
                   slot_box=sl.get('box') if sl.get('ok') else None, pieces=pieces)
        print(p, 'frames', frames, 'pieces', len(pieces))


if __name__ == '__main__':
    main()
