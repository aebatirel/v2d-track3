"""[D] DIAGNOSTIC ONLY (reads the public scans; never a method input). Approach-1 study, 2026-10-25.

How much of what insert_test.py's planar slot cut removes from each board is real wood (inside the public scan),
i.e. what the cut would cost if it were applied to the SUBMITTED mesh instead of the collision copy only.
Re-derives the cut exactly as insert_test.py does (claims K >= 5 frames, 1-99 % slab + 1 mm, one shared split plane).
Usage: python diag_cut_realwood.py CLAIMS.npz SCAN_A SCAN_B"""
import os, sys

import numpy as np
from scipy.spatial.transform import Rotation as R

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pair_overlap as po  # noqa: E402

K, MARGIN = 5, 0.001
z = np.load(sys.argv[1]); sa, sb = po.load_mesh(sys.argv[2]), po.load_mesh(sys.argv[3])
SDa, SDb = po.SD(sa), po.SD(sb)
asm, rel = z['asm'], z['rel']                     # rel = B in A per frame (pair_overlap 'rel' = Ti)
Ra = R.from_matrix(rel[asm, :3, :3]).mean().as_matrix(); tB = rel[asm, :3, 3].mean(0)
first = int(np.argmax(z['ovl'] > 0.5)); t0 = max(0, first - 12)
path_B_in_A = rel[t0:, :3, 3]; path_A_in_B = np.linalg.inv(rel[t0:])[:, :3, 3]


def region(S, cnt, a, path, plane=None):
    C = S[cnt >= K]; a = a / np.linalg.norm(a)
    s = C @ a; lo, hi = np.percentile(s, 1) - MARGIN, np.percentile(s, 99) + MARGIN
    if plane is None:
        ins = path[0] - path[-1]; ins -= a * (ins @ a); ins /= np.linalg.norm(ins)
        p = C @ ins; c = (np.percentile(p, 1) + np.percentile(p, 99)) / 2
    else:
        ins, c = plane
    m = ((S @ a) > lo) & ((S @ a) < hi) & ((S @ ins) > c)
    return m, ins, c


v = po.PITCH ** 3 * 1e6
mA, nA, cA = region(z['SA'], z['cntA'], Ra[:, 0], path_B_in_A)
mB, _, _ = region(z['SB'], z['cntB'], Ra.T[:, 0], path_A_in_B, plane=(-Ra.T @ nA, float(nA @ tB - cA)))
for name, S, m, sd in [('board 1', z['SA'], mA, SDa), ('board 2', z['SB'], mB, SDb)]:
    real = sd(S[m]) < 0
    print(f'{name}: cut removes {m.sum() * v:.2f} cm3 of our solid; inside the public scan (real wood) {real.sum() * v:.2f} cm3 '
          f'({100 * real.mean():.0f} %); outside the scan (our excess, e.g. the filled notch) {(~real).sum() * v:.2f} cm3')
