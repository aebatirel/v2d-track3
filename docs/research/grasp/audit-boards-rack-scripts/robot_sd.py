"""Signed distance (cm, + = inside the object mesh) of robot link origins to an object, reference vs zero trace."""
import sys, numpy as np, trimesh
from scipy.spatial.transform import Rotation as R
sys.path.insert(0, __file__.rsplit('/', 1)[0]); from refload import load_ref
ref, trace, lib, obj, hand, frames = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4], sys.argv[5], [int(x) for x in sys.argv[6].split(',')]
d = load_ref(ref); j = d['names'].index(obj); m = trimesh.load(f'{lib}/{obj}.glb', force='mesh'); pq_ = trimesh.proximity.ProximityQuery(m)
z = np.load(trace); L = [str(x) for x in z['labels']]; Q = z['q'].astype(float); oi = L.index(f'track3_{obj}/object')
LK = ['hand_C_MC'] + [f'{f}_{s}' for f in ('thumb',) for s in ('MC', 'PP', 'DP')] + [f'{f}_{s}' for f in ('index', 'middle', 'ring', 'pinky') for s in ('PP', 'MP', 'DP')]
fn = d[f'fnames_{hand}']
ri = [fn.index(f'{hand}_{k}') for k in LK]; ti = [L.index(f'{hand}_sharpa_wave/{hand}_{k}') for k in LK]
print('links:', ' '.join(LK))
for t in frames:
    for lab, pts, p, q in (('REF ', d[f'frames_{hand}'][t][ri, :3], d['OP'][t, j], d['OQ'][t, j]), ('ZERO', Q[t][ti, :3], Q[t, oi, :3], Q[t, oi, 3:7])):
        loc = R.from_quat(q).inv().apply(pts - p); sd = pq_.signed_distance(loc) * 100
        print(f' f{t:3d} {lab} ' + ' '.join(f'{v:+5.1f}' for v in sd))
