"""Per-frame collision-hull overlap of a two-object reference (scratch, 2026-10-29; logic of tools/hull_census.py).
Object solids (2 mm grid, winding number) posed by the reference in the partner's frame, tested against the partner's
FlashCHORD hulls (flash_chord.assets.mesh.convex_decompose, CoACD 0.05, or the pieces of --pieces DIR) and mesh.
Adds what hull_census does not report: overlap per frame (stride), object speeds, rest segments, the final rest
("placed") frame, and overlap at frame 0 / at the placed frame / at the worst rest frame.
--poses GT.npz (optional) replaces the reference poses (diagnostics on public twins only; key 'T' [F, B, 4, 4]).
Usage (FlashCHORD venv): overlap_frames.py REF.parquet MESHDIR OUT.json [--stride 1] [--pieces DIR]"""
import argparse, glob, json, os, sys

import numpy as np
import pyarrow.parquet as pq
import trimesh
from scipy.spatial import ConvexHull
from scipy.spatial.transform import Rotation as R

sys.path.insert(0, '/home/user/v2d-track3/pipeline')
from collision_decomp import SignedDistance, inside  # noqa: E402

ap = argparse.ArgumentParser(); ap.add_argument('ref'); ap.add_argument('meshdir'); ap.add_argument('out')
ap.add_argument('--stride', type=int, default=1); ap.add_argument('--pitch', type=float, default=0.002)
ap.add_argument('--pieces'); ap.add_argument('--poses')
ap.add_argument('--rest_cm', type=float, default=0.15, help='rest: speed below this (cm/frame) ...')
ap.add_argument('--rest_deg', type=float, default=0.8, help='... and below this (deg/frame), 5-frame median')
a = ap.parse_args()
row = pq.read_table(a.ref).to_pylist()[0]; names = list(row['object_body_names'])
if a.poses:
    T = np.load(a.poses)['T']; nF = len(T)
else:
    pos = np.array(row['object_body_position'], float); q = np.array(row['object_body_wxyz'], float)[..., [1, 2, 3, 0]]
    nF = len(pos); T = np.tile(np.eye(4), (nF, len(names), 1, 1))
    T[..., :3, :3] = R.from_quat(q.reshape(-1, 4)).as_matrix().reshape(nF, len(names), 3, 3); T[..., :3, 3] = pos


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

# speeds and rest
spd = np.zeros((nF, len(names))); ang = np.zeros((nF, len(names)))
spd[1:] = np.linalg.norm(np.diff(T[:, :, :3, 3], axis=0), axis=-1) * 100
for k in range(len(names)):
    ang[1:, k] = np.degrees(R.from_matrix(np.einsum('fij,fkj->fik', T[1:, k, :3, :3], T[:-1, k, :3, :3])).magnitude())


def med5(x):
    return np.array([np.median(x[max(0, i - 2):i + 3]) for i in range(len(x))])


rest = np.stack([(med5(spd[:, k]) < a.rest_cm) & (med5(ang[:, k]) < a.rest_deg) for k in range(len(names))], 1)
placed = {}
for k, n in enumerate(names):
    i = nF - 1
    while i > 0 and rest[i - 1, k]:
        i -= 1
    placed[n] = int(i) if rest[nF - 1, k] else None
first_move = {n: int(np.argmax(~rest[:, k])) if (~rest[:, k]).any() else None for k, n in enumerate(names)}

frames = list(range(0, nF, a.stride))
for extra in [nF - 1] + [x for x in placed.values() if x is not None]:
    if extra not in frames:
        frames.append(extra)
frames = sorted(frames)
res = dict(ref=a.ref, poses=a.poses, objects=names, frames=nF, hulls=[len(h) for h in H],
           hull_cm3=[round(sum(ConvexHull(V).volume for V in h) * 1e6, 1) for h in H],
           solid_cm3=[round(len(s) * v, 1) for s in S], stride=a.stride, placed_frame=placed, first_move_frame=first_move,
           rest_frames=[int(rest[:, k].sum()) for k in range(len(names))], directions={})
per = {}
for i, j in ((0, 1), (1, 0)):
    hv, mv = [], []
    for f in frames:
        Mij = np.linalg.inv(T[f, j]) @ T[f, i]; X = S[i] @ Mij[:3, :3].T + Mij[:3, 3]
        lo, hi = M[j].bounds[0] - 0.01, M[j].bounds[1] + 0.01; X = X[np.all((X > lo) & (X < hi), 1)]
        inm = SD[j](X) < 0 if len(X) else np.zeros(0, bool); inh = np.zeros(len(X), bool)
        for e in EQ[j]:
            inh |= inside(e, X)
        hv.append(inh.sum() * v); mv.append(inm.sum() * v)
    per[(i, j)] = (np.array(hv), np.array(mv))
fr = np.array(frames)
both_rest = rest[fr].all(1)
for (i, j), (hv, mv) in per.items():
    key = f'{names[i]} in {names[j]}'
    d = dict(hull_cm3_max=round(float(hv.max()), 2), hull_cm3_median_over_gt1=round(float(np.median(hv[hv > 1])), 2) if (hv > 1).any() else 0.0,
             mesh_cm3_max=round(float(mv.max()), 2), frames_hull_gt1=int((hv > 1).sum()) * a.stride,
             first_gt1=int(fr[np.argmax(hv > 1)]) if (hv > 1).any() else None,
             last_gt1=int(fr[len(hv) - 1 - np.argmax((hv > 1)[::-1])]) if (hv > 1).any() else None,
             argmax_frame=int(fr[np.argmax(hv)]), f0_hull_cm3=round(float(hv[0]), 2), f0_mesh_cm3=round(float(mv[0]), 2),
             last_hull_cm3=round(float(hv[-1]), 2), last_mesh_cm3=round(float(mv[-1]), 2),
             rest_max_hull_cm3=round(float(hv[both_rest].max()), 2) if both_rest.any() else None,
             rest_argmax_frame=int(fr[both_rest][np.argmax(hv[both_rest])]) if both_rest.any() else None,
             series=[[int(f), round(float(h), 2), round(float(m), 2)] for f, h, m in zip(fr, hv, mv)])
    for n, pf in placed.items():
        if pf is not None:
            k = frames.index(pf); d[f'placed_{n}_f{pf}_hull_cm3'] = round(float(hv[k]), 2); d[f'placed_{n}_f{pf}_mesh_cm3'] = round(float(mv[k]), 2)
    res['directions'][key] = d
json.dump(res, open(a.out, 'w'), indent=1)
print(json.dumps({k: (v if k != 'directions' else {d: {kk: vv for kk, vv in x.items() if kk != 'series'} for d, x in v.items()})
                  for k, v in res.items() if k not in ('ref',)}))
