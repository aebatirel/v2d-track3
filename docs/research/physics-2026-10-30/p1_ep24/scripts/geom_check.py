"""Geometry at reference poses: lowest point of each board's pieces vs the table, per frame; piece counts/volumes.
Usage: geom_check.py REF.parquet R0_DIR LIB_DIR"""
import sys, glob, os, json
import numpy as np, pyarrow.parquet as pq, trimesh
from scipy.spatial.transform import Rotation as R
ref, r0, lib = sys.argv[1:4]
row = pq.read_table(ref).to_pylist()[0]
P = np.array(row['object_body_position']); Q = np.array(row['object_body_wxyz'])[..., [1, 2, 3, 0]]
names = list(row['object_body_names'])
def load(d, n):
    fs = sorted(glob.glob(f'{d}/{n}/piece_*.obj'))
    return [trimesh.load(f, force='mesh') for f in fs]
out = {}
for cfg, d in (('carved', r0), ('default', f'{r0}/_default')):
    for k, n in enumerate(names):
        ms = load(d, n)
        V = np.vstack([m.vertices for m in ms])
        vol = sum(m.volume for m in ms)
        widths = [float(m.bounding_box_oriented.primitive.extents.min()) for m in ms]
        conv = [bool(m.is_convex) for m in ms]
        wat = [bool(m.is_watertight) for m in ms]
        lowest = []
        for f in range(len(P)):
            Rm = R.from_quat(Q[f, k]).as_matrix(); W = V @ Rm.T + P[f, k]
            lowest.append(W[:, 2].min())
        lowest = np.array(lowest)
        out[(cfg, n)] = lowest
        print(cfg, n, 'pieces', len(ms), 'vol cm3 %.2f' % (vol * 1e6), 'convex', sum(conv), 'watertight', sum(wat),
              'min OBB width mm %.2f' % (min(widths) * 1e3), 'n<2mm', sum(w < 0.002 for w in widths),
              'bbox mm', np.round((V.max(0) - V.min(0)) * 1e3, 1), 'centroid mm', np.round(V.mean(0) * 1e3, 1))
    lm = trimesh.load(f'{lib}/{n}.glb', force='mesh')
for n in names:
    lm = trimesh.load(f'{lib}/{n}.glb', force='mesh')
    print('library', n, 'bbox mm', np.round(lm.extents * 1e3, 1), 'bbox centre mm', np.round(lm.bounds.mean(0) * 1e3, 1))
for f in [0, 100, 160, 200, 218, 230, 240, 246, 250, 260, 274]:
    print('f', f, ' '.join(f'{c[0]}:{c[1][-1]} low-table {((out[c][f]) - 0.6) * 1e3:.1f}mm' for c in out))
