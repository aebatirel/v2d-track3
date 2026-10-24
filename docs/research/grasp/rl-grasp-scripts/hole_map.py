"""Ring-hole map of a plate's collision pieces in its PCA frame: 2 mm grid over the ring part (axis1 < X1 cm);
a cell is solid if a line along axis3 through it hits any CoACD piece. Free cells enclosed by solid cells = the hole.
Prints the hole bbox / area / inscribed radius and the plate's axis3 extent around the hole; saves the hole cells."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
from scipy import ndimage
from rlgrasp_lib import ObjGeom
G = ObjGeom(sys.argv[1], sys.argv[2]); X1 = float(sys.argv[3]) / 100; out = sys.argv[4]
g = 0.002; a1 = np.arange(-0.14, X1, g); a2 = np.arange(-0.08, 0.08, g); a3 = np.arange(-0.04, 0.04, 0.001)
A1, A2 = np.meshgrid(a1, a2, indexing='ij'); solid = np.zeros(A1.shape, bool); top = np.full(A1.shape, np.nan); bot = np.full(A1.shape, np.nan)
for i in range(len(a1)):
    P = np.stack(np.meshgrid(a2, a3, indexing='ij'), -1).reshape(-1, 2)
    Q = np.c_[np.full(len(P), a1[i]), P]                      # PCA coords
    Xo = G.c + Q @ G.W; d = G.lb(Xo)[0].reshape(len(a2), len(a3)) <= 0
    solid[i] = d.any(1)
    for j in range(len(a2)):
        if d[j].any():
            top[i, j] = a3[d[j]].max(); bot[i, j] = a3[d[j]].min()
lab, n = ndimage.label(~solid); border = set(np.unique(np.r_[lab[0], lab[-1], lab[:, 0], lab[:, -1]]))
hole = np.isin(lab, [k for k in range(1, n + 1) if k not in border])
if hole.any():
    h1, h2 = A1[hole], A2[hole]; dist = ndimage.distance_transform_edt(hole) * g
    print(f'hole: {hole.sum()} cells, area {hole.sum() * g * g * 1e4:.1f} cm2, axis1 {100 * h1.min():.1f}..{100 * h1.max():.1f}, axis2 {100 * h2.min():.1f}..{100 * h2.max():.1f} cm, inscribed radius {100 * dist.max():.2f} cm, centre ({100 * h1.mean():.1f}, {100 * h2.mean():.1f})')
    ring = ndimage.binary_dilation(hole, iterations=4) & solid
    print(f'band around the hole: axis3 top {100 * np.nanmedian(top[ring]):.1f} cm, bottom {100 * np.nanmedian(bot[ring]):.1f} cm (median)')
    np.savez(out, a1=a1, a2=a2, hole=hole, top=top, bot=bot, solid=solid)
else:
    print('no enclosed hole in the collision pieces'); np.savez(out, a1=a1, a2=a2, hole=hole, top=top, bot=bot, solid=solid)
