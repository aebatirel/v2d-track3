"""Joint-consistency flip test (GT-free): approach-1 study, 2026-10-25.

At the assembled frames of a slotted pair, re-pose B by a 180-degree turn about each of its own principal axes
(T_B' = T_B @ Rflip, about B's origin) and measure the A-B mesh overlap. Our board meshes keep a partial notch
(roughly 40 % open), so the configuration whose notches face each other should overlap least. On ep24 (control, whose
track agrees with mocap) the as-tracked pose should win; a flip that wins on another episode flags a flipped track.
Inputs: our meshes and our poses only. Reuses pair_overlap.py (same folder).
Usage: python flip_test.py MESH_A MESH_B SRC a:b:s OUT.json"""
import json, os, sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pair_overlap as po  # noqa: E402

ma, mb, src, fr, out = sys.argv[1:6]
mA, mB = po.load_mesh(ma), po.load_mesh(mb); sA, sB = po.SD(mA), po.SD(mB)
SA, _ = po.solid(mA, sA); SB, _ = po.solid(mB, sB); v = po.PITCH ** 3 * 1e6
TA, TB = po.load_poses(src, 'wooden_piece_1', 'wooden_piece_2')
a, b, s = map(int, fr.split(':')); F = list(range(a, min(b, len(TA)), s))
flips = {'as_tracked': np.eye(3), 'rot180_x': np.diag([1., -1, -1]), 'rot180_y': np.diag([-1., 1, -1]), 'rot180_z': np.diag([-1., -1, 1])}
res = {}
for k, Rf in flips.items():
    Fm = np.eye(4); Fm[:3, :3] = Rf
    ov = []
    for t in F:
        TBp = TB[t] @ Fm
        T = np.linalg.inv(TBp) @ TA[t]; Ti = np.linalg.inv(T)
        inA = sB(SA @ T[:3, :3].T + T[:3, 3]) < 0; inB = sA(SB @ Ti[:3, :3].T + Ti[:3, 3]) < 0
        ov.append((inA.sum() + inB.sum()) / 2 * v)
    res[k] = dict(median_cm3=round(float(np.median(ov)), 2), min_cm3=round(float(np.min(ov)), 2), max_cm3=round(float(np.max(ov)), 2))
    print(k, res[k], flush=True)
json.dump(dict(mesh_a=ma, mesh_b=mb, src=src, frames=[a, b, s], result=res), open(out, 'w'), indent=1)
