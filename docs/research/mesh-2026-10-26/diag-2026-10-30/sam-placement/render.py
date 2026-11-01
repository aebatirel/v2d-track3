"""[D] Overlay renders: public scan (grey), our observed points (blue dots), SAM 3D mesh as placed (orange) for the
original sim3_fit and each GT-free fix variant. Orthographic views along the scan's PCA axes (in our object frame).
Output: renders/<obj>_s<seed>.png and renders/montage_s<seed>.png
"""
import json, sys
import cv2
import numpy as np
sys.path.insert(0, '/tmp/claude-0/-home-user-v2d-track3/90d4009c-b597-536b-9d55-58f81afca135/scratchpad/diag/sam-placement')
from common import *  # noqa

CELL = 280
VIEWS = [(0, 1, 'view along short axis'), (0, 2, 'view along mid axis'), (1, 2, 'view along long axis')]
COL = dict(sim3_fit=(0, 140, 255), vis=(200, 120, 0), vis_slib=(160, 0, 160), lib=(0, 160, 0), lib_vis=(0, 120, 120))


def raster(P2, lo, sc, size, rad=1):
    m = np.zeros((size, size), np.uint8)
    ij = np.round((P2 - lo) * sc).astype(int)
    ok = np.all((ij >= 0) & (ij < size), 1)
    m[size - 1 - ij[ok, 1], ij[ok, 0]] = 255
    if rad:
        m = cv2.dilate(m, np.ones((2 * rad + 1, 2 * rad + 1), np.uint8))
    return m > 0


def cell(Y, X, O, V, view, color, c0, half):
    a, b, name = view
    proj = lambda P: np.c_[(P - c0) @ V[:, a], (P - c0) @ V[:, b]]
    lo = np.array([-half, -half]); sc = CELL / (2 * half)
    img = np.full((CELL, CELL, 3), 255, np.uint8)
    ms = raster(proj(Y), lo, sc, CELL, 1)
    img[ms] = (175, 175, 175)
    mm = raster(proj(X), lo, sc, CELL, 1)
    img[mm] = (0.55 * np.array(color) + 0.45 * img[mm]).astype(np.uint8)
    mo = raster(proj(O), lo, sc, CELL, 0)
    img[mo] = (255, 60, 0)
    cv2.rectangle(img, (0, 0), (CELL - 1, CELL - 1), (220, 220, 220), 1)
    return img


def put(img, txt, y, scale=0.45, col=(30, 30, 30)):
    cv2.putText(img, txt, (6, y), cv2.FONT_HERSHEY_SIMPLEX, scale, col, 1, cv2.LINE_AA)


def main():
    rows = json.load(open(f'{OUT}/analysis.json'))
    dec = {}
    for l in open(f'{OUT}/decomp_before.jsonl'):
        r = json.loads(l); dec[(r['model'], r['obj'], r['seed'])] = r
    fits = {}
    for l in open(f'{OUT}/fits.jsonl'):
        r = json.loads(l); fits[(r['obj'], r['seed'], r['variant'])] = r
    os.makedirs(f'{OUT}/renders', exist_ok=True)
    montage = {42: [], 7: []}
    for r in rows:
        obj, seed = r['obj'], r['seed']
        d = dec[('sam3d', obj, seed)]
        V = np.array(d['scan_pca'])
        Y, _ = surf(load_scan(obj), 6000, seed=2)                     # [D]
        obs = load_obs(obj, n=2500, seed=5); O = obs['pts']
        c0 = Y.mean(0); half = 1.08 * np.abs((Y - c0) @ V).max()
        rp, pp = gen_paths('sam3d', obj, seed)
        raw = load_mesh(rp)
        variants = [('sim3_fit', load_mesh(pp))]
        for v in ('vis', 'vis_slib', 'lib', 'lib_vis'):
            f = fits.get((obj, seed, v))
            if f is not None:
                variants.append((v, trimesh.Trimesh(apply((f['s'], np.array(f['R']), np.array(f['t'])),
                                                          np.asarray(raw.vertices)), raw.faces, process=False)))
        lines = []
        for v, P in variants:
            X, _ = surf(P, 6000, seed=1)
            cells = [cell(Y, X, O, V, vw, COL[v], c0, half) for vw in VIEWS]
            e = r['variants'][v]
            band = np.full((22, CELL * 3, 3), 255, np.uint8)
            put(band, f"{v}: size {e['size_pct']:+.0f}%  rot {e['rot']:.0f} deg (as kit counts {e['rot_kit']:.0f})  "
                      f"centroid {e['trans_mm']:.0f} mm  ADD~sym {e['add_sym_mm']:.0f} mm", 16, 0.5)
            lines.append(np.vstack([band, np.hstack(cells)]))
            if v in ('sim3_fit', 'lib'):
                montage[seed].append((obj, v, cells[0], e))
        head = np.full((44, CELL * 3, 3), 255, np.uint8)
        put(head, f"{obj}  SAM 3D seed {seed}   grey = public scan [D], blue = our observed points, colour = mesh", 16, 0.5)
        put(head, f"shape error after best similarity {r['shape_mm']:.1f} mm; extents/scan L/M/S "
                  f"{'/'.join(f'{x:.2f}' for x in r['ext_ratio'])}; views: " + ', '.join(v[2] for v in VIEWS), 36, 0.42)
        cv2.imwrite(f'{OUT}/renders/{obj}_s{seed}.png', np.vstack([head] + lines))
    for seed, items in montage.items():
        if not items:
            continue
        objs = [o for o in OBJS if any(i[0] == o for i in items)]
        cols = []
        for o in objs:
            col = []
            for v in ('sim3_fit', 'lib'):
                it = [i for i in items if i[0] == o and i[1] == v]
                if not it:
                    col.append(np.full((CELL + 40, CELL, 3), 255, np.uint8)); continue
                _, _, img, e = it[0]
                band = np.full((40, CELL, 3), 255, np.uint8)
                put(band, f"{o} {'before (sim3_fit)' if v == 'sim3_fit' else 'fix: lib'}", 15, 0.45)
                put(band, f"size {e['size_pct']:+.0f}% rot {e['rot_kit']:.0f} ADD~sym {e['add_sym_mm']:.0f}mm", 33, 0.42)
                col.append(np.vstack([band, img]))
            cols.append(np.vstack(col))
        rowsimg = [np.hstack(cols[i:i + 5] + [np.full_like(cols[0], 255)] * (5 - len(cols[i:i + 5])))
                   for i in range(0, len(cols), 5)]
        cv2.imwrite(f'{OUT}/renders/montage_s{seed}.png', np.vstack(rowsimg))


if __name__ == '__main__':
    main()
