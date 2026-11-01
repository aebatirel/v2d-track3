#!/usr/bin/env python
"""C2 track R: GT-free visibility (shadow) test of residual points against a mesh.

A point our camera observed must be visible from that camera. If the segment from an outside-residual point to the
camera centre that observed it (obs_points 'cam') passes through the mesh solid, the point lies in the mesh's own
shadow: either the mesh is wrong there, or the point is a depth-edge (mixed pixel / smear) sample. Residual clusters
made of shadowed points are not evidence of missing structure; clusters of visible points are.

Solid occupancy: mesh voxelized at GRID (2 mm) and filled. Segment samples every GRID from START (4 mm) beyond the point.
Reads only obs_points npz files and our own mesh / build record.

Usage: vis_diag.py --mesh M.glb --rec joint.json --obs a.npz,... --out OUT.json [--thr_mm 6] [--min_pts 200]
"""
import argparse, json, os
import numpy as np
import trimesh
from scipy import ndimage
from scipy.spatial import cKDTree

VOX = 0.0015
GRID = 0.002
START = 0.004
CV = 0.004


def load(path):
    Z = np.load(path)
    P = Z['pts'].astype(np.float64); C = Z['cam'].astype(np.float64)
    key = np.floor(P / VOX).astype(np.int64)
    _, first = np.unique(key, axis=0, return_index=True)
    first = np.sort(first)
    return P[first], C[first]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--mesh', required=True); ap.add_argument('--rec', required=True)
    ap.add_argument('--obs', required=True); ap.add_argument('--out', required=True)
    ap.add_argument('--thr_mm', type=float, default=6.0); ap.add_argument('--min_pts', type=int, default=200)
    a = ap.parse_args()
    rec = json.load(open(a.rec))
    fr = {k: np.asarray(v) for k, v in rec['frame'].items()}
    Tm = np.asarray(rec['alignment']['mean_frame_T']) if 'alignment' in rec else np.eye(4)
    Ti = np.linalg.inv(Tm)
    m = trimesh.load(a.mesh, force='mesh')
    vg = m.voxelized(GRID).fill()
    occ = vg.matrix; T = vg.transform                    # index -> world: T @ [i, j, k, 1]
    Tinv = np.linalg.inv(T)
    S, fi = trimesh.sample.sample_surface(m, 600000, seed=0)
    N = m.face_normals[fi]; tree = cKDTree(S)
    thr = a.thr_mm * 1e-3
    eps = [os.path.basename(f).split('_')[0] for f in a.obs.split(',')]
    Q_all, E_all, V_all = [], [], []
    per_ep = {}
    for k, f in enumerate(a.obs.split(',')):
        P, C = load(f)
        d, j = tree.query(P)
        out = (np.einsum('ij,ij->i', P - S[j], N[j]) > 0) & (d > thr)
        P, C = P[out], C[out]
        u = C - P; L = np.linalg.norm(u, axis=1); u /= L[:, None]
        shadow = np.zeros(len(P), bool)
        steps = np.arange(START, 0.40, GRID)
        for s in steps:
            X = P + s * u
            ijk = np.round(X @ Tinv[:3, :3].T + Tinv[:3, 3]).astype(int)
            ok = np.all((ijk >= 0) & (ijk < np.array(occ.shape)), axis=1) & (s < L)
            hit = np.zeros(len(P), bool)
            hit[ok] = occ[tuple(ijk[ok].T)]
            shadow |= hit
        per_ep[eps[k]] = dict(n_out=int(len(P)), frac_shadow=round(float(shadow.mean()), 4))
        X = P - Tm[:3, 3] if False else P
        Qr = (X @ Ti[:3, :3].T + Ti[:3, 3]) - fr['o']
        Q_all.append(np.c_[Qr @ fr['L'], Qr @ fr['w'], Qr @ fr['up']]); E_all.append(np.full(len(P), k)); V_all.append(~shadow)
    q = np.concatenate(Q_all); e = np.concatenate(E_all); vis = np.concatenate(V_all)
    res = {}
    for nm, sel in (('visible', vis), ('shadow', ~vis)):
        Qs = q[sel]; Es = e[sel]
        lo = Qs.min(0)
        ijk = np.floor((Qs - lo) / CV).astype(int)
        G = np.zeros(ijk.max(0) + 1, bool); G[tuple(ijk.T)] = True
        lab, nl = ndimage.label(G, structure=np.ones((3, 3, 3)))
        Lb = lab[tuple(ijk.T)]
        cl = []
        for c in range(1, nl + 1):
            mm = Lb == c
            if mm.sum() < a.min_pts:
                continue
            cnt = np.bincount(Es[mm], minlength=len(eps))
            cl.append(dict(n=int(mm.sum()), centroid_mm=[round(float(v) * 1e3, 1) for v in Qs[mm].mean(0)],
                           lo_mm=[round(float(v) * 1e3, 1) for v in np.percentile(Qs[mm], 2, axis=0)],
                           hi_mm=[round(float(v) * 1e3, 1) for v in np.percentile(Qs[mm], 98, axis=0)],
                           per_ep={eps[i]: int(cnt[i]) for i in range(len(eps))},
                           n_eps_support=int(sum(1 for i in range(len(eps)) if cnt[i] >= 0.2 * a.min_pts))))
        cl.sort(key=lambda c: -c['n'])
        res[nm] = cl
    out = dict(mesh=a.mesh, thr_mm=a.thr_mm, per_episode=per_ep, clusters=res)
    json.dump(out, open(a.out, 'w'), indent=1)
    print(json.dumps(per_ep))
    for nm in ('visible', 'shadow'):
        print(nm, len(res[nm]))
        for c in res[nm][:20]:
            print('  ', json.dumps(c))


if __name__ == '__main__':
    main()
