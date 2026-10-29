# DIAGNOSTIC ONLY (reads the public scan solid from interact/defects; never an input to the method): excess / missing
# volume of our meshes vs the object's scan, on the defects step's 2 mm scan-frame grid (T_ours_to_scan from its ICP).
# Usage: eval_scan.py NAME MESH [MESH ...]
import sys, os, json, numpy as np, trimesh
sys.path.insert(0, '/tmp/claude-0/-home-user-v2d-track3/8c892c5e-fd7c-57aa-abef-68d2af098e4f/scratchpad/interact')
import vox2
D = '/tmp/claude-0/-home-user-v2d-track3/8c892c5e-fd7c-57aa-abef-68d2af098e4f/scratchpad/interact/defects'
n = sys.argv[1]
z = np.load(f'{D}/{n}_vox.npz'); sh = tuple(z['shape']); lo = z['lo']; p = float(z['pitch'])
U = lambda a: np.unpackbits(a)[:np.prod(sh)].reshape(sh).astype(bool)  # noqa: E731
if os.path.exists(f'{D}/{n}_scan_solid.npz'):
    S_ = U(np.load(f'{D}/{n}_scan_solid.npz')['final']); src = 'visibility-repaired'
else:
    S_ = U(np.load(f'{D}/{n}_gwn.npz')['thr0.5']); src = 'winding>=0.5'
X = lo + (np.argwhere(np.ones(sh, bool)) + 0.5) * p
Ti = np.linalg.inv(z['T_ours_to_scan']); Xo = X @ Ti[:3, :3].T + Ti[:3, 3]
c3 = p ** 3 * 1e6
out = dict(obj=n, scan_solid=src, scan_cm3=round(float(S_.sum() * c3), 1))
prev = None
for mp in sys.argv[2:]:
    m = trimesh.load(mp, force='mesh'); m.merge_vertices(); sd = vox2.SD(m, 'winding')
    O = (sd(Xo, maxd=0.2) < 0).reshape(sh)
    r = dict(ours_cm3=round(float(O.sum() * c3), 1), excess_cm3=round(float((O & ~S_).sum() * c3), 1),
             missing_cm3=round(float((S_ & ~O).sum() * c3), 1), iou=round(float((O & S_).sum() / max((O | S_).sum(), 1)), 3))
    if prev is not None:
        rem = prev & ~O
        r['removed_vs_prev_cm3'] = round(float(rem.sum() * c3), 1)
        r['removed_that_was_excess_cm3'] = round(float((rem & ~S_).sum() * c3), 1)
        r['removed_that_was_real_cm3'] = round(float((rem & S_).sum() * c3), 1)
    out[os.path.relpath(mp, '/tmp/claude-0/-home-user-v2d-track3/8c892c5e-fd7c-57aa-abef-68d2af098e4f/scratchpad/interact/joint')] = r
    prev = O
print(json.dumps(out))
