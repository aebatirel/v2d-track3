# Residual interaction exclusion AFTER observation-first fusion (scratch, 2026-10-22; repo unchanged). GT-free.
# Two objects A, B, their obsfuse2 (+ maskfuse) grids and one post-pass variant each. At the given frames (both
# objects' tracks), every solid voxel of A is mapped into B's grid (nearest voxel) and vice versa. A voxel claimed by
# both in >= MINF of the frames is contested. Each side's claim is STRONG if the voxel was observed inside with the fine
# truncation (W_fine >= 3, mean < 0) and was never seen free by the silhouette; otherwise WEAK (thickness never
# observed = only the coarse field or the closing put it there). Contested voxels are removed from the weak side
# (both weak: from both; both strong: kept and reported as a conflict = a pose or depth error, not shape evidence).
# Usage: resid.py OUTDIR VARIANT_A VARIANT_B POSES.npz FRAMES(a:b[,c:d]) STRIDE NAME_A GRIDS_A NAME_B GRIDS_B [POSES2 FRAMES2 ...]
import sys, os, json
import numpy as np, trimesh
from skimage.measure import marching_cubes
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import obspost2 as op
KIT = op.KIT
od, varA, varB = sys.argv[1:4]
na, ga, nb, gb = sys.argv[7:11]
eps = [(sys.argv[4], sys.argv[5], int(sys.argv[6]))] + [(sys.argv[i], sys.argv[i + 1], int(sys.argv[6])) for i in range(11, len(sys.argv), 2)]
os.makedirs(od, exist_ok=True)
MINF = 0.3
obj = {}
for n, g, var in ((na, ga, varA), (nb, gb, varB)):
    G, shape, lo, vx = op.load(g.split(','))
    solid, field, info = op.build(G, shape, vx, var)
    tau = var.split('_')[0]; tf = tau.split('c')[0]
    Wf = G[f'W{tf}']; mf = np.where(Wf > 0, G[f'S{tf}'] / np.maximum(Wf, 1), 1)
    strong = (Wf >= 3) & (mf < 0)
    if 'NMF' in G:
        strong &= ~(G['NMF'] >= 1) | (G['NMF'] < 0.3 * np.maximum(G['NMV'], 1))
    obj[n] = dict(G=G, shape=np.array(shape), lo=lo, vx=vx, solid=solid, field=field, strong=strong, var=var)
cnt = {n: np.zeros(tuple(obj[n]['shape']), np.int32) for n in obj}
nfr = 0
for poses, frs, st in eps:
    P = np.load(poses)
    fr = []
    for seg in frs.split(','):
        a, b = map(int, seg.split(':')); fr += list(range(a, b, st))
    for t in fr:
        nfr += 1
        for A, B in ((na, nb), (nb, na)):
            oa, ob = obj[A], obj[B]
            T = np.linalg.inv(P[f'cam_T_{B}'][t]) @ P[f'cam_T_{A}'][t]
            ij = np.argwhere(oa['solid']); Xa = oa['lo'] + (ij + 0.5) * oa['vx']
            Xb = Xa @ T[:3, :3].T + T[:3, 3]
            kb = np.floor((Xb - ob['lo']) / ob['vx']).astype(int)
            ok = np.all((kb >= 0) & (kb < ob['shape']), 1)
            hit = np.zeros(len(ij), bool); hit[ok] = ob['solid'][tuple(kb[ok].T)]
            cnt[A][tuple(ij[hit].T)] += 1
res = {}
for A, B in ((na, nb), (nb, na)):
    oa = obj[A]; con = cnt[A] >= max(1, MINF * nfr)
    weak = con & ~oa['strong']
    res[A] = dict(contested_cm3=round(float(con.sum()) * oa['vx'] ** 3 * 1e6, 2), removed_weak_cm3=round(float(weak.sum()) * oa['vx'] ** 3 * 1e6, 2),
                  kept_strong_cm3=round(float((con & oa['strong']).sum()) * oa['vx'] ** 3 * 1e6, 2))
    sol = oa['solid'] & ~weak
    field = np.where(np.pad(weak, 1), np.maximum(oa['field'], 0.5), oa['field'])
    vx = oa['vx']
    verts, faces, _, _ = marching_cubes(field, 0.0, spacing=(vx,) * 3)
    verts = verts - vx + oa['lo'] + 0.5 * vx
    m = trimesh.Trimesh(verts, faces, process=True)
    parts = m.split(only_watertight=False)
    if len(parts) > 1:
        big = max(parts, key=lambda q: q.area)
        m = trimesh.util.concatenate([q for q in parts if q.area >= 0.05 * big.area and np.linalg.norm(q.centroid - big.centroid) < 0.15])
    full = f'{od}/{A}_full.glb'; m.export(full)
    sys.path.insert(0, KIT)
    from v2dlb.mesh_budget import budget_mesh
    vb, fb = budget_mesh(full, 4096, 4096)
    trimesh.Trimesh(vb, fb, process=False).export(f'{od}/{A}.glb')
    res[A]['solid_cm3'] = round(float(sol.sum()) * vx ** 3 * 1e6, 1)
res['frames'] = nfr
print(json.dumps(res))
json.dump(res, open(f'{od}/resid.json', 'w'), indent=1)
