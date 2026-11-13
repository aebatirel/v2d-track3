"""Eval 16: what holds our reference spoon in the rack? Per frame: gap between the spoon solid and the rack visual solid,
spoon volume within 2 mm of the rack (contact band), within 2 mm of the rack's CoACD pieces, and the spoon's lowest point
above the table (z-up world, table top from the support usda via support_fill.json). Usage: ev16_support.py SCRIPTS CONFIG OUT"""
import json, sys
import numpy as np
from scipy.ndimage import distance_transform_edt
sys.path.insert(0, sys.argv[1]); import vox  # noqa: E402
sys.argv = [sys.argv[0], sys.argv[1], sys.argv[2], sys.argv[3]]
exec(open(f'{sys.argv[1]}/analyze.py').read().split('def main():')[0])   # reuse helpers (ref_poses, load_hulls, hull_test)
c = cfg['episodes']['16']; TABLE = 0.6
names, T = ref_poses(c['ref']); ci = names.index(c['container']); si = names.index('wooden_spoon')
g = vox.voxelize(vox.load(c['container_mesh']), PITCH, pad=0.03); dout = distance_transform_edt(~g.occ) * PITCH
H, eqs, boxes = load_hulls(c['hulls'])
S = vox.voxelize(vox.load(c['spoon_mesh']), SPOON_PITCH).centres()
rows = []
for f in range(len(T)):
    M = np.linalg.inv(T[f, ci]) @ T[f, si]; X = S @ M[:3, :3].T + M[:3, 3]
    ijk = np.floor((X - g.lo) / PITCH).astype(int); ok = np.all((ijk >= 0) & (ijk < np.array(g.occ.shape)), 1)
    d = np.full(len(X), np.inf); d[ok] = dout[ijk[ok, 0], ijk[ok, 1], ijk[ok, 2]]
    # dilate the hulls by 2 mm: plane offsets
    near_h = np.zeros(len(X), bool)
    for e, (lo, hi) in zip(eqs, boxes):
        cand = np.flatnonzero(np.all((X >= lo - 0.002) & (X <= hi + 0.002), 1))
        if len(cand):
            near_h[cand[(X[cand] @ e[:, :3].T + e[:, 3]).max(1) <= 0.002]] = True
    W = S @ T[f, si][:3, :3].T + T[f, si][:3, 3]
    rows.append(dict(f=f, gap_mm=round(float(d.min() * 1000), 1) if np.isfinite(d.min()) else None,
                     within2mm_vis_cm3=round(cm3((d <= 0.002).sum(), SPOON_PITCH), 2), within2mm_hull_cm3=round(cm3(near_h.sum(), SPOON_PITCH), 2),
                     lowest_above_table_mm=round(float((W[:, 2].min() - TABLE) * 1000), 1)))
json.dump(rows, open(f'{sys.argv[3]}/ev16_support.json', 'w'), indent=0)
for r in rows:
    if r['f'] >= 80 and (r['f'] % 4 == 0 or r['f'] > 165):
        print(r)
