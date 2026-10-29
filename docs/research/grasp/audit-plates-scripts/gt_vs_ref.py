"""DIAGNOSTIC WITH GROUND TRUTH (public episode mocap, after inference): displacement of each object from its frame-0
pose (frame-invariant: |p(t)-p(0)|, rotation angle, height change along the table normal approximated by the
world z of each frame) in mocap vs our reference, to tell perception drift from real motion."""
import sys, glob
import numpy as np, pyarrow.parquet as pq
from scipy.spatial.transform import Rotation as R
sys.path.insert(0, sys.argv[3]); from audit_lib import load_ref
t = pq.read_table(sys.argv[1]).to_pylist(); ref = load_ref(sys.argv[2])
names = ref['names']; T = min(len(t), ref['T']); st = int(sys.argv[4]) if len(sys.argv) > 4 else 2
gt = {n: np.array([[o['pose'] for o in r['observation.objects'] if o['name'] == n][0] for r in t[:T]]) for n in names}
print('f | ' + ' | '.join(f'{n}: gt_disp_cm gt_dz_cm gt_turn ref_disp_cm ref_dz_cm ref_turn' for n in names))
for f in range(0, T, st):
    row = f'{f:3d}'
    for j, n in enumerate(names):
        g = gt[n]; qg = R.from_quat(g[:, [4, 5, 6, 3]])
        gd = 100 * np.linalg.norm(g[f, :3] - g[0, :3]); gz = 100 * (g[f, 2] - g[0, 2]); gr = np.degrees((qg[f] * qg[0].inv()).magnitude())
        r_ = ref['obj'][:, j]; qr = R.from_quat(r_[:, 3:7])
        rd = 100 * np.linalg.norm(r_[f, :3] - r_[0, :3]); rz = 100 * (r_[f, 2] - r_[0, 2]); rr = np.degrees((qr[f] * qr[0].inv()).magnitude())
        row += f' | {gd:5.1f} {gz:5.1f} {gr:5.1f}   {rd:5.1f} {rz:5.1f} {rr:5.1f}'
    print(row)
