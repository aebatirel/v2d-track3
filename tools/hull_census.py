"""Does the simulator's collision geometry block what our reference does? (2026-10-26 forensics; GT-free.)
For a two-object reference: each object's solid samples (2 mm) are posed by the reference in the partner's frame, every
STRIDE frames, and tested against (a) the partner's MESH and (b) the partner's collision hulls exactly as FlashCHORD builds
them (flash_chord.assets.mesh.convex_decompose, CoACD 0.05; or the pieces of a PIECES dir). Volume inside the hulls but
outside the mesh is geometry that only the collision copy adds (filled cavities, slots, holders): the reference asks for
a motion the simulator cannot follow. Reported per direction: median / max over frames and frames above 1 cm3.
Usage (FlashCHORD venv, FLASH_CHORD_CACHE_DIR): hull_census.py REF.parquet MESHDIR OUT.json [--stride 3] [--pieces DIR]"""
import argparse, glob, json, os, sys

import numpy as np
import pyarrow.parquet as pq
import trimesh
from scipy.spatial import ConvexHull
from scipy.spatial.transform import Rotation as R

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'pipeline'))
from collision_decomp import SignedDistance, inside  # noqa: E402

ap = argparse.ArgumentParser(); ap.add_argument('ref'); ap.add_argument('meshdir'); ap.add_argument('out')
ap.add_argument('--stride', type=int, default=3); ap.add_argument('--pitch', type=float, default=0.002); ap.add_argument('--pieces')
a = ap.parse_args()
row = pq.read_table(a.ref).to_pylist()[0]; names = list(row['object_body_names'])
pos = np.array(row['object_body_position'], float); q = np.array(row['object_body_wxyz'], float)[..., [1, 2, 3, 0]]
T = np.tile(np.eye(4), (len(pos), len(names), 1, 1)); T[..., :3, :3] = R.from_quat(q.reshape(-1, 4)).as_matrix().reshape(len(pos), len(names), 3, 3)
T[..., :3, 3] = pos


def load(n):
    p = next(x for x in (f'{a.meshdir}/{n}.glb', f'{a.meshdir}/{n}/{n}.glb') if os.path.exists(x))
    m = trimesh.load(p, force='mesh'); return trimesh.Trimesh(np.asarray(m.vertices), np.asarray(m.faces), process=True)


def hulls(n, m):
    pcs = sorted(glob.glob(f'{a.pieces}/{n}/piece_*.obj')) if a.pieces else []
    if pcs:
        return [np.asarray(trimesh.load(p).vertices) for p in pcs]
    from flash_chord.assets.mesh import convex_decompose
    return [np.asarray(h.vertices, float) for h in convex_decompose(np.asarray(m.vertices), np.asarray(m.faces))]


M = [load(n) for n in names]; SD = [SignedDistance(m) for m in M]; H = [hulls(n, m) for n, m in zip(names, M)]
EQ = [[ConvexHull(V).equations for V in h] for h in H]; v = a.pitch ** 3 * 1e6
S = []
for m, sd in zip(M, SD):
    lo, hi = m.bounds[0] - a.pitch, m.bounds[1] + a.pitch; n = np.ceil((hi - lo) / a.pitch).astype(int) + 1
    G = np.stack(np.meshgrid(*[lo[k] + a.pitch * np.arange(n[k]) for k in range(3)], indexing='ij'), -1).reshape(-1, 3)
    S.append(G[sd(G) < 0])
res = dict(ref=a.ref, objects=names, hulls=[len(h) for h in H], hull_cm3=[round(sum(ConvexHull(V).volume for V in h) * 1e6, 1) for h in H],
           solid_cm3=[round(len(s) * v, 1) for s in S], stride=a.stride, directions={})
for i, j in ((0, 1), (1, 0)):                                       # object i's solid inside partner j
    mesh_v, hull_v, only_hull = [], [], []
    for f in range(0, len(pos), a.stride):
        Mij = np.linalg.inv(T[f, j]) @ T[f, i]; X = S[i] @ Mij[:3, :3].T + Mij[:3, 3]
        lo, hi = M[j].bounds[0] - 0.01, M[j].bounds[1] + 0.01; near = np.all((X > lo) & (X < hi), 1); X = X[near]
        inm = SD[j](X) < 0 if len(X) else np.zeros(0, bool); inh = np.zeros(len(X), bool)
        for e in EQ[j]:
            inh |= inside(e, X)
        mesh_v.append(inm.sum() * v); hull_v.append(inh.sum() * v); only_hull.append((inh & ~inm).sum() * v)
    mv, hv, ov = map(np.array, (mesh_v, hull_v, only_hull))
    res['directions'][f'{names[i]} in {names[j]}'] = dict(
        mesh_cm3_median=round(float(np.median(mv)), 2), mesh_cm3_max=round(float(mv.max()), 2),
        hull_cm3_median=round(float(np.median(hv)), 2), hull_cm3_max=round(float(hv.max()), 2),
        hull_only_cm3_median=round(float(np.median(ov)), 2), hull_only_cm3_max=round(float(ov.max()), 2),
        frames_hull_gt1cm3=int((hv > 1).sum()) * a.stride, frames_hull_only_gt1cm3=int((ov > 1).sum()) * a.stride,
        first_hull_gt1cm3_frame=int(np.argmax(hv > 1)) * a.stride if (hv > 1).any() else None,
        hull_only_cm3_every=np.round(ov, 1).tolist())
json.dump(res, open(a.out, 'w'), indent=1)
print(json.dumps({k: (v if k != 'directions' else {d: {kk: vv for kk, vv in x.items() if kk != 'hull_only_cm3_every'} for d, x in v.items()}) for k, v in res.items() if k != 'ref'}))
