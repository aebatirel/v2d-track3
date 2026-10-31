"""Slot position from each source, in the board's own axes (GT-free; dev). Reads a BI2 output folder.

  python slot_summary.py OUT_DIR CAND_DIR obj=cid,obj=cid > slot_summary.json

Per object: the pick's PCA axes (long L, width W, thickness T, mm from the pick's centroid); for each source the
voxels near the motion region (within 20 mm): (c) the motion component (all persistent voxels) and its carve side,
(a) the placed SAM 3D notch C_a (restricted to the candidate), (b) silhouette see-through voxels; their centroid
along L and W, their extent along L (the slot's width direction on a board) and along W (its depth), and the
pairwise centroid distances (3-D and along L) = the agreement in mm.
"""
import json
import sys

import numpy as np
import trimesh
from scipy import ndimage


def centres(lo, vox, shape, lin):
    idx = np.stack(np.unravel_index(np.asarray(lin, np.int64), tuple(shape)), 1)
    return np.asarray(lo) + (idx + 0.5) * vox


def main():
    out_dir, cand_dir, picks = sys.argv[1:4]
    picks = dict(kv.split('=') for kv in picks.split(','))
    res = {}
    for obj, cid in picks.items():
        z = dict(np.load(f'{out_dir}/voxels_{obj}.npz'))
        lo, vox, shape = z['lo'], float(z['vox']), z['shape']
        m = trimesh.load(f'{cand_dir}/{obj}/{cid}.glb', force='mesh')
        X = trimesh.sample.sample_surface(m, 30000, seed=0)[0]
        c = X.mean(0); U = np.linalg.svd(X - c, full_matrices=False)[2]
        ext = np.ptp((X - c) @ U.T, axis=0)
        comps = sorted([k for k in z if k.endswith('_lin') and k.startswith('comp')],
                       key=lambda k: -len(z[k]))
        if not comps:
            res[obj] = dict(note='no motion component'); continue
        R = z[comps[0]]
        CR = centres(lo, vox, shape, R)
        near = np.zeros(int(np.prod(shape)), bool); near[R] = True
        near = ndimage.binary_dilation(near.reshape(tuple(shape)), iterations=5).ravel()
        src = dict(c_motion=R, c_carve_side=z[comps[0].replace('_lin', '_region')])
        if 'gen_C_a' in z:
            ca = np.nonzero(z['gen_C_a'] & near)[0]
            if len(ca):
                lab, n = ndimage.label(np.isin(np.arange(near.size), ca).reshape(tuple(shape)), structure=np.ones((3, 3, 3)))
                lab = lab.ravel()
                # the C_a component that overlaps the motion region most (else the largest)
                best = max(range(1, n + 1), key=lambda i: (np.isin(np.nonzero(lab == i)[0], R).sum(), (lab == i).sum()))
                src['a_sam_notch'] = np.nonzero(lab == best)[0]
        if 'sil' in z:
            sl = np.nonzero(z['sil'] & near)[0]
            if len(sl):
                src['b_silhouette'] = sl
        rows = {}
        for k, lin in src.items():
            C = centres(lo, vox, shape, lin)
            A = (C - c) @ U.T
            rows[k] = dict(voxels=int(len(lin)), centroid_L_mm=round(float(A[:, 0].mean()) * 1e3, 1),
                           centroid_W_mm=round(float(A[:, 1].mean()) * 1e3, 1),
                           extent_L_mm=round(float(np.ptp(A[:, 0]) + vox) * 1e3, 1),
                           extent_W_mm=round(float(np.ptp(A[:, 1]) + vox) * 1e3, 1),
                           W_range_mm=[round(float(A[:, 1].min() - vox / 2) * 1e3, 1),
                                       round(float(A[:, 1].max() + vox / 2) * 1e3, 1)],
                           _c=C.mean(0))
        names = list(rows)
        agree = {}
        for i in range(len(names)):
            for j in range(i + 1, len(names)):
                a, b = rows[names[i]], rows[names[j]]
                agree[f'{names[i]}|{names[j]}'] = dict(dist_3d_mm=round(float(np.linalg.norm(a['_c'] - b['_c'])) * 1e3, 1),
                                                       along_L_mm=round(a['centroid_L_mm'] - b['centroid_L_mm'], 1))
        for r in rows.values():
            r.pop('_c')
        res[obj] = dict(pick=cid, pick_extent_mm=np.round(ext * 1e3, 1).tolist(), sources=rows, agreement=agree)
    print(json.dumps(res, indent=1))


if __name__ == '__main__':
    main()
