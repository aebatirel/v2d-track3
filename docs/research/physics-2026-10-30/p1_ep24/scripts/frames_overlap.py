"""(1) Assembled stretch on our reference: relative speed of the partner origin in the target's frame per frame (stride 1
and 2) over the gmg engaged run, last static stretch (< 2 mm per frame, >= 5 frames). (2) Collider overlap (cm3) of the
guest's pieces inside the host's pieces and the deepest guest sample (mm inside the host) at chosen frames, carved and
default. Grid samples at PITCH inside the guest pieces (half-space tests). Our reference only.
Usage: frames_overlap.py REF.parquet R0_DIR --host wooden_piece_1 --guest wooden_piece_2 --run 164,274 --frames 218,246,274"""
import argparse, glob, json
import numpy as np, pyarrow.parquet as pq, trimesh
from scipy.spatial.transform import Rotation as R
ap = argparse.ArgumentParser(); ap.add_argument('ref'); ap.add_argument('r0'); ap.add_argument('--host', default='wooden_piece_1')
ap.add_argument('--guest', default='wooden_piece_2'); ap.add_argument('--run', default='164,274'); ap.add_argument('--frames', default='218,246,274')
ap.add_argument('--pitch', type=float, default=0.0005); ap.add_argument('--json', default='')
a = ap.parse_args()
row = pq.read_table(a.ref).to_pylist()[0]
P = np.array(row['object_body_position']); Q = np.array(row['object_body_wxyz'])[..., [1, 2, 3, 0]]
names = list(row['object_body_names']); hk, gk = names.index(a.host), names.index(a.guest)
def T(k, f):
    M = np.eye(4); M[:3, :3] = R.from_quat(Q[f, k]).as_matrix(); M[:3, 3] = P[f, k]; return M
f0, f1 = map(int, a.run.split(','))
rel = {f: np.linalg.inv(T(hk, f)) @ T(gk, f) for f in range(len(P))}
res = dict(run=[f0, f1])
for stride in (1, 2):
    fr = list(range(f0, f1 + 1, stride))
    sp = [np.linalg.norm(rel[fr[i]][:3, 3] - rel[fr[i - 1]][:3, 3]) * 1e3 for i in range(1, len(fr))]
    static = [fr[i] for i in range(1, len(fr)) if sp[i - 1] < 2.0]
    # last maximal run of consecutive static frames
    runs = []; cur = []
    for i in range(1, len(fr)):
        if sp[i - 1] < 2.0:
            cur = cur + [fr[i - 1], fr[i]] if not cur else cur + [fr[i]]
        else:
            if cur: runs.append(sorted(set(cur)))
            cur = []
    if cur: runs.append(sorted(set(cur)))
    runs = [r for r in runs if len(r) >= 5]
    last = runs[-1] if runs else []
    res[f'stride{stride}'] = dict(last_static=[last[0], last[-1]] if last else None, n=len(last),
                                  median_frame=int(last[len(last) // 2]) if last else None,
                                  runs=[[r[0], r[-1], len(r)] for r in runs],
                                  speed_mm_per_frame_218_274=[round(float(x), 2) for x, f in zip(sp, fr[1:]) if f >= 210])
    print(f'stride {stride}: static runs (>=5 frames) {[[r[0], r[-1], len(r)] for r in runs]}; last {res[f"stride{stride}"]["last_static"]}, median {res[f"stride{stride}"]["median_frame"]}')
def hull_eqs(fs):
    out = []
    for f in fs:
        m = trimesh.load(f, force='mesh'); out.append(trimesh.convex.convex_hull(m.vertices).facets_normal if False else m)
    return out
def load(d, n):
    return [trimesh.load(f, force='mesh') for f in sorted(glob.glob(f'{d}/{n}/piece_*.obj'))]
def samples(ms, pitch):
    X = []
    for m in ms:
        lo, hi = m.bounds
        g = [np.arange(lo[i] + pitch / 2, hi[i], pitch) for i in range(3)]
        G = np.stack(np.meshgrid(*g, indexing='ij'), -1).reshape(-1, 3)
        eq = m.facets_normal if False else None
        A = m.face_normals; b = np.einsum('ij,ij->i', A, m.triangles[:, 0])
        inside = np.all(G @ A.T - b <= 1e-12, axis=1)
        X.append(G[inside])
    return np.vstack(X)
def depth_inside(ms, X):
    """for points X (host frame): max over pieces of the inside depth (min over faces of b - A x); <= 0 outside"""
    best = np.full(len(X), -np.inf)
    for m in ms:
        A = m.face_normals; b = np.einsum('ij,ij->i', A, m.triangles[:, 0])
        d = (b[None, :] - X @ A.T).min(1)
        best = np.maximum(best, d)
    return best
frames = [int(x) for x in a.frames.split(',')]
res['overlap'] = {}
for cfg, d in (('carved', a.r0), ('default', f'{a.r0}/_default')):
    H = load(d, a.host); G = load(d, a.guest)
    Xg = samples(G, a.pitch); cell = a.pitch ** 3
    # sample volume check
    vg = sum(m.volume for m in G)
    res['overlap'][cfg] = {}
    for f in frames:
        Xh = Xg @ rel[f][:3, :3].T + rel[f][:3, 3]
        lo, hi = np.vstack([m.bounds for m in H]).min(0), np.vstack([m.bounds for m in H]).max(0)
        near = np.all((Xh >= lo - 1e-3) & (Xh <= hi + 1e-3), axis=1)
        dep = np.full(len(Xh), -1.0); dep[near] = depth_inside(H, Xh[near])
        ins = dep > 0
        r = dict(overlap_cm3=round(float(ins.sum() * cell * 1e6), 3), deepest_mm=round(float(dep.max() * 1e3), 2) if ins.any() else 0.0,
                 p90_depth_mm=round(float(np.percentile(dep[ins], 90) * 1e3), 2) if ins.any() else 0.0)
        res['overlap'][cfg][f] = r
        print(cfg, 'frame', f, r, f'(guest sample volume {len(Xg) * cell * 1e6:.2f} vs exact {vg * 1e6:.2f} cm3)')
if a.json:
    json.dump(res, open(a.json, 'w'), indent=1)
