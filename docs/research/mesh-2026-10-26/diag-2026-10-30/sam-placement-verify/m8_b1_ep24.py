"""M8: falsification test of H-track (board 1's placement error comes from the broken ep23 board-1 track, not from
the objective). GT-free step: the repo's own sim3_fit.fit (unchanged) of the raw SAM board-1 meshes to ep24 points
instead of ep23. [D] step: decomposition vs the scan and kit-like ADD (3 seeds). 2 meshes, no selection."""
import sys, json, trimesh
import numpy as np
sys.path.insert(0, '/home/user/v2d-track3/docs/research/mesh-2026-10-26/gen')
import sim3_fit
from vlib import *
from m6_regdep import kit_like_register, add_static
os.makedirs(f'{OUT}/b1_ep24', exist_ok=True)
sv, sf = load_scan('wooden_piece_1'); q = sample(sv, sf, 500, 0); B = sample(sv, sf, 4000, 12)
for ep in (24, 23):
    P = np.load(f'{SCR}/obs_all/ep{ep}_wooden_piece_1.npz')['pts']; rng = np.random.default_rng(0)
    O = P[rng.choice(len(P), min(20000, len(P)), replace=False)]
    for seed in (42, 7):
        m = trimesh.load(f'{GEN}/sam3d/wooden_piece_1_k27_s{seed}.ply', force='mesh', process=False)
        M = trimesh.sample.sample_surface(m, 20000, seed=0)[0]
        obj, s, R, t, mo, mm = sim3_fit.fit(M, O)
        v = s * np.asarray(m.vertices) @ R.T + t; f = np.asarray(m.faces)
        trimesh.Trimesh(v, f, process=False).export(f'{OUT}/b1_ep24/wooden_piece_1_ep{ep}_s{seed}.ply')
        tr, un, T = multi_start(sample(v, f, 4000, 11), B, scale=True)
        cm = centroid(v, f); off = apply(T, cm[None])[0] - cm
        adds, rots = [], []
        for ks in (11, 22, 33):
            da, Rk, rc = kit_like_register(v, f, sv, sf, ks); adds.append(add_static(da, Rk, q - rc, None, None) * 1e3); rots.append(rot_angle(Rk))
        print(json.dumps(dict(points=f'ep{ep}', seed=seed, J_mm=round(obj * 1e3, 2), size_pct=round((1 / T[0] - 1) * 100, 1), rot=round(rot_angle(T[1]), 1),
                              trans_mm=round(float(np.linalg.norm(off)) * 1e3, 1), kitlike_add=[round(a, 1) for a in adds], kit_rot=[round(r, 1) for r in rots])), flush=True)
