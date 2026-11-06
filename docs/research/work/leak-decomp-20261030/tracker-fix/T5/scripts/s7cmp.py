"""GT-free: object-level camera correction of the T5 camera vs perc2's stored camera (world shift of each board's centroid
from swapping W_base for W_t5), against rule K's absorbed camera steps (ep24/vo_k_ep24.json, primary setting)."""
import json, sys, numpy as np, trimesh
W = sys.argv[1]; P = np.load(sys.argv[2]); out = sys.argv[3]
Wb = np.load(f'{W}/main/W_base.npy'); res = {}
cen = {n: np.asarray(trimesh.load(f'/home/user/v2d-track3/meshes/library_v3/{n}.glb', force='mesh').vertices).mean(0) for n in ('wooden_piece_1', 'wooden_piece_2')}
log = json.load(open('/home/user/v2d-track3/docs/research/work/leak-decomp-20261030/tracker-fix/ep24/vo_k_ep24.json'))['episodes']['24']['Po']['K_h3_r5_w2']['log']
ck = np.zeros((len(Wb), 3))
for t, kind, objs, v in log:
    ck[t:] += np.asarray(v) / 100
nk = np.linalg.norm(ck, axis=1) * 100
res['ruleK'] = dict(first_ge_1cm=int(np.argmax(nk >= 1.0)), f40=round(nk[40], 2), f50=round(nk[50], 2), f100=round(nk[100], 2), end=round(nk[-1], 2))
for v in ('rvo', 'rvo_plane', 'plane'):
    Wn = np.load(f'{W}/main/W_{v}.npy'); r = {}
    for n, c in cen.items():
        T = P[f'cam_T_{n}']
        xb = np.einsum('tij,tj->ti', Wb[:, :3, :3], T[:, :3, :3] @ c + T[:, :3, 3]) + Wb[:, :3, 3]
        xn = np.einsum('tij,tj->ti', Wn[:, :3, :3], T[:, :3, :3] @ c + T[:, :3, 3]) + Wn[:, :3, 3]
        d = np.linalg.norm(xn - xb, axis=1) * 100
        r[n] = dict(first_ge_1cm=int(np.argmax(d >= 1.0)) if (d >= 1).any() else None, f36=round(d[36], 2), f40=round(d[40], 2), f50=round(d[50], 2),
                    f100=round(d[100], 2), end=round(d[-1], 2), max=round(d.max(), 2),
                    max_before_f27=round(d[:27].max(), 2), cos_with_ruleK_f100=round(float((xn - xb)[100] @ ck[100] / (np.linalg.norm((xn - xb)[100]) * np.linalg.norm(ck[100]) + 1e-12)), 3))
    res[v] = r
json.dump(res, open(out, 'w'), indent=1)
print(json.dumps(res, indent=1))
