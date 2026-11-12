#!/usr/bin/env python3
"""Test G-B inputs (Gemini track audit, note 28 idea 1): one Decisions API request per row of gb_rows.csv (the depth
audit's 7,835 valid object-frames). INFERENCE SIDE ONLY: the audit's own perception tracks (sha256-checked against
each audit.json), the public calibration and ego_cam_c video, and our library_v3 meshes.

Per row (episode e, object o, frame t), in the camera our tracks live in (rectified left, pipeline/track_overlay.py
rectify_maps; video frame t = track frame t = depth frame t):
  - window: square around the silhouette of our library_v3 mesh at our tracked pose cam_T_<o>[t], 1.6 x its longest
    edge (at least 160 px), so a track that is a few cm off still shows the real object;
  - left panel: the rectified frame cropped to the window, 448 x 448;
  - right panel: the same crop with the external outline of that silhouette in magenta (2 px), as track_overlay.py
    draws the tracked mesh, but as an outline so the real edges stay visible. The silhouette is closed with a 9 px
    elliptic kernel first: our library cups are two-body meshes with thin slits that would draw an outline running
    into the object;
  - composite 902 x 448 JPEG (6 px grey separator), quality 90. One request: intro text (object name) + the image at
    resolution high + one noul question (questions.json GB).
Usage: gb_build.py --rows gb_rows.csv --audit_root .../audit/public --tracks DIR --videos DIR --calib calib.json
                   --lib meshes/library_v3 --questions questions.json --out OUT [--workers 4] [--episodes 0,2]
"""
import argparse, csv, hashlib, json, os, sys, time
from collections import defaultdict
from multiprocessing import Pool

import numpy as np
import cv2

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gj_common as C  # noqa: E402

PANEL, SEP, GROW, MIN_SIDE, CLOSE = 448, 6, 1.6, 160, 9
COLOUR = (255, 0, 255)                       # BGR magenta


def build_episode(args):
    e, rows, a = args
    Q = json.load(open(a.questions))['GB']
    A = json.load(open(os.path.join(a.audit_root, f'ep{e}', 'audit.json')))
    pp = C.guard(os.path.join(a.tracks, f'ep{e}', 'poses.npz'))
    if hashlib.sha256(open(pp, 'rb').read()).hexdigest() != A['inputs']['poses']['sha256']:
        raise SystemExit(f'ep{e}: track differs from the one the depth audit used')
    P = np.load(pp)
    MC, K = C.rectify_maps(C.guard(a.calib))
    if np.abs(K - np.array(A['K'])).max() > 1e-6:
        raise SystemExit(f'ep{e}: rectified K differs from the audit K')
    lib = {o: C.load_mesh(os.path.join(a.lib, o + '.glb')) for o in {r[1] for r in rows}}
    vid = C.Reader(os.path.join(a.videos, f'ep{e}_c.mp4'))
    assert vid.n == A['T'] == len(P['world_T_cam']), (e, vid.n, A['T'])
    os.makedirs(os.path.join(a.out, 'img', f'ep{e}'), exist_ok=True)
    by_t = defaultdict(list)
    for r in rows:
        by_t[r[3]].append(r)
    specs = []
    for t in sorted(by_t):
        img = cv2.remap(vid.get(t), MC[0], MC[1], cv2.INTER_LINEAR)
        for (_, o, slot, _) in by_t[t]:
            V, F = lib[o]
            T = P['cam_T_' + o][t].astype(np.float64)
            X = V @ T[:3, :3].T + T[:3, 3]
            uv = C.project_pinhole(X, K)
            cx, cy, side = C.square_window(*uv.min(0), *uv.max(0), GROW, MIN_SIDE)
            clean = C.crop_affine(img, cx, cy, side, PANEL)
            m = C.silhouette_pinhole(V, F, T, K, cx, cy, side, PANEL)
            m = cv2.morphologyEx(m, cv2.MORPH_CLOSE, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (CLOSE, CLOSE)))
            over = clean.copy()
            cv2.drawContours(over, C.outline(m), -1, COLOUR, 2, cv2.LINE_AA)
            comp = np.full((PANEL, 2 * PANEL + SEP, 3), 128, np.uint8)
            comp[:, :PANEL] = clean; comp[:, PANEL + SEP:] = over
            b = C.jpeg_bytes(comp, 90)
            fn = os.path.join(a.out, 'img', f'ep{e}', f'{o}_f{t:04d}.jpg')
            open(fn, 'wb').write(b)
            specs.append(dict(id=f'ep{e}:{o}:{t}', test='GB', episode=e, obj=o, slot=slot, frame=t,
                              window=[round(cx, 2), round(cy, 2), round(side, 2)], sil_px=int(m.sum()),
                              sil_touches_border=bool(m[0].any() or m[-1].any() or m[:, 0].any() or m[:, -1].any()),
                              input=[dict(type='text', text=Q['input_intro'].format(name=C.nice_name(o))),
                                     dict(type='image', path=os.path.abspath(fn), mime_type='image/jpeg',
                                          resolution=Q['image_resolution'], sha256=hashlib.sha256(b).hexdigest())],
                              questions=Q['questions']))
    print(f'[gb] ep{e}: {len(specs)} rows', flush=True)
    return specs


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    for k in ('rows', 'audit_root', 'tracks', 'videos', 'calib', 'lib', 'questions', 'out'):
        ap.add_argument('--' + k, required=True)
    ap.add_argument('--workers', type=int, default=4); ap.add_argument('--episodes', default=None)
    a = ap.parse_args()
    t0 = time.time()
    rows = [(int(r['ep']), r['obj'], int(r['slot']), int(r['frame'])) for r in csv.DictReader(open(a.rows))]
    by_e = defaultdict(list)
    for r in rows:
        by_e[r[0]].append(r)
    eps = sorted(by_e) if a.episodes is None else [int(x) for x in a.episodes.split(',')]
    with Pool(a.workers) as pool:
        res = pool.map(build_episode, [(e, by_e[e], a) for e in eps])
    specs = [s for r in res for s in r]
    order = {(r[0], r[1], r[3]): i for i, r in enumerate(rows)}
    specs.sort(key=lambda s: order[(s['episode'], s['obj'], s['frame'])])
    C.write_jsonl(os.path.join(a.out, 'specs_GB.jsonl'), specs)
    print(f'[gb] wrote {len(specs)} specs in {time.time() - t0:.0f} s; silhouettes touching the crop border: '
          f'{sum(s["sil_touches_border"] for s in specs)}')


if __name__ == '__main__':
    main()
