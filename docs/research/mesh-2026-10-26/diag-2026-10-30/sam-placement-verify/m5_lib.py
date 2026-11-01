"""M5: independent re-implementation of the 'lib' placement (Sim(3) of the RAW SAM 3D mesh onto our library_v3 mesh
surface; identity excluded, 24 PCA cube starts, symmetric trimmed ICP, best by trimmed residual). No scan read here.
Writes placed meshes to lib_mine/ and the GT-free registration gap (second start > 30 deg away)."""
import json, trimesh
import numpy as np
from vlib import *
os.makedirs(f'{OUT}/lib_mine', exist_ok=True)
with open(f'{OUT}/m5_lib_fits.jsonl', 'w') as fo:
    for obj in EPS:
        lv, lf = load(f'{LIB}/{obj}.glb'); Bl = sample(lv, lf, 4000, 41)
        for seed in (42, 7):
            v, f = load(f'{GEN}/sam3d/{obj}_{KTAG[obj]}_s{seed}.ply')
            A = sample(v, f, 4000, 42)
            res = multi_start(A, Bl, scale=True, include_identity=False, return_all=True)
            tr, un, T = res[0]
            alt = [r for r in res[1:] if rot_angle(r[2][1] @ T[1].T) > 30]
            trimesh.Trimesh(apply(T, v), f, process=False).export(f'{OUT}/lib_mine/{obj}_{KTAG[obj]}_s{seed}.ply')
            rec = dict(obj=obj, seed=seed, scale=T[0], trim_mm=round(tr * 1e3, 3), gap_mm=round((alt[0][0] - tr) * 1e3, 3) if alt else None,
                       alt_rot=round(rot_angle(alt[0][2][1] @ T[1].T), 1) if alt else None)
            print(json.dumps(rec), flush=True); fo.write(json.dumps(rec) + '\n')
