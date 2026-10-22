# GT-free gate: does the final solid explain our own depth? Evidence voxels = where our own (non-hand/table/other)
# samples put a zero crossing (|mean12| < 0.25, W12 >= 5, M0 >= 5). Unexplained = evidence voxels more than 4 mm from
# the solid's boundary (missing surface: the GT-free analogue of scan->ours). Unsupported = boundary voxels of the solid
# more than 4 mm from any evidence voxel (surface invented by closing / coarse field: analogue of ours->scan).
# Usage: gate_ev.py GRIDS VAR [VAR ...]
import sys, os, json, numpy as np
from scipy import ndimage
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import obspost2 as op
G, shape, lo, vx = op.load(sys.argv[1].split(','))
W = G['W12']; m12 = np.where(W > 0, G['S12'] / np.maximum(W, 1), 1)
ev = (W >= 5) & (np.abs(m12) < 0.25) & (G['M0'] >= 5)
d_ev = ndimage.distance_transform_edt(~ev) * vx
for var in sys.argv[2:]:
    solid, field, info = op.build(G, shape, vx, var)
    bnd = solid & ~ndimage.binary_erosion(solid)
    d_b = ndimage.distance_transform_edt(~bnd) * vx
    r = dict(evidence_vox=int(ev.sum()), unexplained_share=round(float((d_b[ev] > 0.004).mean()), 3), unexplained8=round(float((d_b[ev] > 0.008).mean()), 3),
             unsupported_share=round(float((d_ev[bnd] > 0.004).mean()), 3))
    print(os.path.basename(sys.argv[1].split(',')[0]), var, json.dumps(r), flush=True)
