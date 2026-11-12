#!/usr/bin/env python3
"""Contact sheets of example inputs (what Gemini will see), PNG <= 1 MB each. Examples are chosen without any score
or label: G-A by model name (Pixal3D-MV, SAM 3D, TripoSG; seed 42), G-B the middle valid frame of 12 tracks.
Usage: make_sheets.py --ga_specs specs_GA.jsonl --gb_specs specs_GB.jsonl --out DIR
"""
import argparse, io, json, os
from collections import defaultdict

import numpy as np
import cv2
from PIL import Image


def save_png(img_bgr, path, limit=1_000_000):
    im = Image.fromarray(cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB))
    for colours in (None, 256, 128, 64):
        q = im if colours is None else im.quantize(colours, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE)
        buf = io.BytesIO(); q.save(buf, 'PNG', optimize=True)
        if buf.tell() <= limit:
            open(path, 'wb').write(buf.getvalue()); return buf.tell(), colours
    raise SystemExit(f'{path}: cannot get under {limit} bytes')


def label(img, text, h=30):
    band = np.full((h, img.shape[1], 3), 255, np.uint8)
    cv2.putText(band, text, (6, h - 9), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 0, 0), 1, cv2.LINE_AA)
    return np.vstack([band, img])


def main():
    ap = argparse.ArgumentParser(); ap.add_argument('--ga_specs', required=True); ap.add_argument('--gb_specs', required=True)
    ap.add_argument('--out', required=True)
    a = ap.parse_args()
    ga = [json.loads(l) for l in open(a.ga_specs)]
    gb = [json.loads(l) for l in open(a.gb_specs)]
    imgs = lambda s: [b['path'] for b in s['input'] if b['type'] == 'image']  # noqa: E731
    sc = 0.5
    # G-A sheet 1: white pot, three candidates x four pictures
    rows = []
    for model in ('pixal_mv', 'sam3d', 'triposg'):
        s = [x for x in ga if x['object'] == 'white_pot' and x['group'] == model and x['id'].endswith('_s42')][0]
        tiles = [cv2.resize(cv2.imread(p), None, fx=sc, fy=sc, interpolation=cv2.INTER_AREA) for p in imgs(s)]
        rows.append(label(np.hstack(tiles), f'{s["id"]}   (pictures 1-4; left real photo, right candidate render)'))
    n1 = save_png(np.vstack(rows), os.path.join(a.out, 'sheet_GA_white_pot.png'))
    # G-A sheet 2: every object, Pixal3D-MV seed 42, pictures 1 and 3
    rows = []
    for o in dict.fromkeys(x['object'] for x in ga):
        s = [x for x in ga if x['object'] == o and x['group'] == 'pixal_mv' and x['id'].endswith('_s42')][0]
        p = imgs(s)
        ix = (0, min(2, len(p) - 1))
        tiles = [cv2.resize(cv2.imread(p[i]), None, fx=0.4, fy=0.4, interpolation=cv2.INTER_AREA) for i in ix]
        rows.append(label(np.hstack(tiles), f'{s["id"]}   (pictures {ix[0] + 1} and {ix[1] + 1} of {len(p)})'))
    pairs = [np.hstack(rows[i:i + 2]) if i + 1 < len(rows) else np.hstack([rows[i], np.full_like(rows[i], 255)])
             for i in range(0, len(rows), 2)]
    n2 = save_png(np.vstack(pairs), os.path.join(a.out, 'sheet_GA_objects.png'))
    # G-B sheet: 12 tracks, the middle answered frame of each (no label used)
    tr = defaultdict(list)
    for s in gb:
        tr[(s['episode'], s['obj'])].append(s)
    keys = sorted(tr)
    pick = [keys[int(i)] for i in np.linspace(0, len(keys) - 1, 12).round()]
    tiles = []
    for k in pick:
        s = tr[k][len(tr[k]) // 2]
        im = cv2.resize(cv2.imread(imgs(s)[0]), None, fx=sc, fy=sc, interpolation=cv2.INTER_AREA)
        tiles.append(label(im, f'{s["id"]}  ({s["input"][0]["text"].splitlines()[0]})'))
    grid = [np.hstack(tiles[i:i + 3]) for i in range(0, 12, 3)]
    n3 = save_png(np.vstack(grid), os.path.join(a.out, 'sheet_GB_examples.png'))
    print('sheet_GA_white_pot.png', n1, 'sheet_GA_objects.png', n2, 'sheet_GB_examples.png', n3)


if __name__ == '__main__':
    main()
