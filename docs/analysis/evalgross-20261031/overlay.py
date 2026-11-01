#!/usr/bin/env python3
"""Draw our reference (solid hull outline) and its feeding perception (projected vertex dots) on rectified ego_cam_c
frames, for visual checks of screen events. Inference side only (video, calibration, our poses, our meshes).
Usage: python3 overlay.py VIDEO CALIB POSES REF TABLE MESH_DIR FRAMES(comma) OUT.png [--scale 0.5]"""
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import identity  # noqa: E402
import screen  # noqa: E402


def main():
    import cv2
    import trimesh
    video, calib, poses, ref, table, mdir, fr, out = sys.argv[1:9]
    scale = float(sys.argv[sys.argv.index('--scale') + 1]) if '--scale' in sys.argv else 0.5
    F = [int(x) for x in fr.split(',')]
    P = np.load(screen.refine.checked(poses))
    W = np.asarray(P['world_T_cam'], float)
    Z = np.load(screen.refine.checked(table))
    names, O = screen.load_ref(ref, np.asarray(Z['T_table_from_world'], float))
    pn, PO = screen.load_perc(poses)
    PO = PO[:, [pn.index(x) for x in names]]
    Winv = np.linalg.inv(W)
    C = np.einsum('tij,tbjk->tbik', Winv, O); PC = np.einsum('tij,tbjk->tbik', Winv, PO)
    MC, KR = identity.rect_maps(calib)
    imgs = identity.frames(video, set(F), MC)
    V = {n: np.asarray(trimesh.load(os.path.join(mdir, f'{n}.glb'), force='mesh').vertices) for n in names}
    cols = [(0, 0, 255), (0, 220, 0), (255, 0, 0)]
    tiles = []
    for t in F:
        img = imgs[t].copy()
        for b, n in enumerate(names):
            for src, style in ((C, 'ref'), (PC, 'perc')):
                Tm = src[t, b]; Y = V[n] @ Tm[:3, :3].T + Tm[:3, 3]
                if (Y[:, 2] <= 0.05).any():
                    continue
                u = Y @ KR.T; uv = (u[:, :2] / u[:, 2:3]).astype(np.int32)
                if style == 'ref':
                    cv2.polylines(img, [cv2.convexHull(uv)], True, cols[b], 3)
                else:
                    for p in uv[::25]:
                        cv2.circle(img, (int(p[0]), int(p[1])), 2, cols[b], -1)
        cv2.putText(img, f'f{t}', (20, 60), cv2.FONT_HERSHEY_SIMPLEX, 2, (0, 255, 255), 3)
        tiles.append(cv2.resize(img, None, fx=scale, fy=scale))
    rows = [np.hstack(tiles[i:i + 2]) if len(tiles[i:i + 2]) == 2 else np.hstack([tiles[i], np.zeros_like(tiles[i])])
            for i in range(0, len(tiles), 2)]
    cv2.imwrite(out, np.vstack(rows))
    print(out, 'objects', list(zip(names, ['red', 'green', 'blue'])))


if __name__ == '__main__':
    main()
