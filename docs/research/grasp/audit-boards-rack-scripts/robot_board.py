"""Robot fingers vs board (reference targets and a zero-action trace): DP / palm (C_MC) in the board frame.
h = height above the board's up face (+) or below its down face (-), 0 = within the slab; out = distance outside the
footprint rectangle. Our reference + simulator trace only (no ground truth)."""
import sys, numpy as np, trimesh
from scipy.spatial.transform import Rotation as R
sys.path.insert(0, __file__.rsplit('/', 1)[0]); from refload import load_ref
ref, trace, lib, obj, hand, frames = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4], sys.argv[5], [int(x) for x in sys.argv[6].split(',')]
SLAB = {'wooden_piece_1': (-0.004, 0.004), 'wooden_piece_2': (-0.004, 0.008)}[obj]
d = load_ref(ref); j = d['names'].index(obj); m = trimesh.load(f'{lib}/{obj}.glb', force='mesh'); b = m.bounds
z = np.load(trace); L = [str(x) for x in z['labels']]; Q = z['q'].astype(float); oi = L.index(f'track3_{obj}/object')
F = ['thumb', 'index', 'middle', 'ring', 'pinky']
def rel(pts, p, q):
    r = R.from_quat(q); loc = r.inv().apply(pts - p); s = 1 if r.apply([1, 0, 0])[2] > 0 else -1
    up = SLAB[1] if s > 0 else SLAB[0]; dn = SLAB[0] if s > 0 else SLAB[1]; res = []
    for x, y, zz in loc:
        a, bb = s * (x - up), s * (dn - x)
        h = a if a > 0 else (-bb if bb > 0 else 0.0)
        out = max(y - b[1][1], b[0][1] - y, zz - b[1][2], b[0][2] - zz, 0)
        res.append(f'{h*100:+5.1f}/{out*100:3.1f}')
    return ' '.join(res)
fn = d[f'frames_{hand}']; names = d[f'fnames_{hand}']
ri = [names.index(f'{hand}_hand_C_MC')] + [names.index(f'{hand}_{f}_DP') for f in F]
ti = [L.index(f'{hand}_sharpa_wave/{hand}_hand_C_MC')] + [L.index(f'{hand}_sharpa_wave/{hand}_{f}_DP') for f in F]
print(f'{obj} {hand}: columns palm(C_MC) thumb index middle ring pinky DP: h/out cm')
for t in frames:
    print(f' f{t:3d} REF   {rel(fn[t][ri, :3], d["OP"][t, j], d["OQ"][t, j])}')
    print(f'      ZERO  {rel(Q[t][ti, :3], Q[t, oi, :3], Q[t, oi, 3:7])}   (sim board vs its own pose)')
