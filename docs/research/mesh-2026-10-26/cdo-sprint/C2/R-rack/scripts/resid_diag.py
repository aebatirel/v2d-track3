#!/usr/bin/env python
"""C2 track R: GT-free residual diagnosis of a rack mesh against OUR observed points (obs_points npz files).

Reads only obs_points npz files (pts, cam, frame, args) and our own meshes / build records. No scan, mocap, parquet
pose or *_align file.

For every observed point (1.5 mm voxel-downsampled, prim_rack.VOX) the distance to the mesh surface (dense surface
samples, nearest sample) and its side (outside / inside by the sample's face normal). Points farther than THR from the
surface are residuals; they are voxelized (4 mm, the obs_points vote voxel), split into 26-connected clusters, and each
cluster is reported in rack coordinates (x along the tray, y across, h above the table cut; frame from the build
record) with its point count per episode (cross-episode support is the evidence that a cluster is structure, not
noise). Maps (top view x-y, front view x-h) are written as PNGs.

Usage: resid_diag.py --mesh M.glb --rec joint.json --obs a.npz,b.npz,... --out OUTDIR [--thr_mm 6] [--tag T]
"""
import argparse, json, os, sys
import numpy as np
import trimesh
from scipy import ndimage
from scipy.spatial import cKDTree

VOX = 0.0015
CV = 0.004


def load(path):
    Z = np.load(path)
    P = Z['pts'].astype(np.float64); C = Z['cam'].astype(np.float64)
    F = Z['frame'] if 'frame' in Z.files else np.zeros(len(P), int)
    key = np.floor(P / VOX).astype(np.int64)
    _, first = np.unique(key, axis=0, return_index=True)
    first = np.sort(first)
    return P[first], C[first], F[first]


def rack_frame(rec):
    fr = {k: np.asarray(v) for k, v in rec['frame'].items()}
    Tm = np.asarray(rec['alignment']['mean_frame_T']) if 'alignment' in rec else np.eye(4)
    return fr, Tm


def to_rack(P, fr, Tm):
    Ti = np.linalg.inv(Tm)
    Q = P @ Ti[:3, :3].T + Ti[:3, 3]
    X = Q - fr['o']
    return np.c_[X @ fr['L'], X @ fr['w'], X @ fr['up']]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--mesh', required=True); ap.add_argument('--rec', required=True)
    ap.add_argument('--obs', required=True); ap.add_argument('--out', required=True)
    ap.add_argument('--thr_mm', type=float, default=6.0); ap.add_argument('--tag', default='diag')
    ap.add_argument('--min_pts', type=int, default=200)
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    rec = json.load(open(a.rec))
    fr, Tm = rack_frame(rec)
    m = trimesh.load(a.mesh, force='mesh')
    S, fi = trimesh.sample.sample_surface(m, 600000, seed=0)
    N = m.face_normals[fi]
    tree = cKDTree(S)
    thr = a.thr_mm * 1e-3
    allq, alld, allside, alle = [], [], [], []
    per_ep = {}
    for k, f in enumerate(a.obs.split(',')):
        P, C, F = load(f)
        d, j = tree.query(P)
        side = np.einsum('ij,ij->i', P - S[j], N[j]) > 0
        q = to_rack(P, fr, Tm)
        ep = os.path.basename(f).split('_')[0]
        per_ep[ep] = dict(n=int(len(P)), p50_mm=float(np.percentile(d, 50) * 1e3), p90_mm=float(np.percentile(d, 90) * 1e3),
                          p99_mm=float(np.percentile(d, 99) * 1e3), frac_out_thr=float(np.mean(side & (d > thr))),
                          frac_in_thr=float(np.mean(~side & (d > thr))))
        allq.append(q); alld.append(d); allside.append(side); alle.append(np.full(len(P), k))
    q = np.concatenate(allq); d = np.concatenate(alld); side = np.concatenate(allside); e = np.concatenate(alle)
    eps = [os.path.basename(f).split('_')[0] for f in a.obs.split(',')]
    ntot = np.bincount(e, minlength=len(eps))
    res = {}
    for nm, sel in (('outside', side & (d > thr)), ('inside', ~side & (d > thr))):
        Q = q[sel]; E = e[sel]; D = d[sel]
        if len(Q) == 0:
            res[nm] = []
            continue
        lo = Q.min(0)
        ijk = np.floor((Q - lo) / CV).astype(int)
        G = np.zeros(ijk.max(0) + 1, bool); G[tuple(ijk.T)] = True
        lab, nl = ndimage.label(G, structure=np.ones((3, 3, 3)))
        L = lab[tuple(ijk.T)]
        cl = []
        for c in range(1, nl + 1):
            mm = L == c
            if mm.sum() < a.min_pts:
                continue
            cnt = np.bincount(E[mm], minlength=len(eps))
            cl.append(dict(n=int(mm.sum()), centroid_mm=[round(float(v) * 1e3, 1) for v in Q[mm].mean(0)],
                           lo_mm=[round(float(v) * 1e3, 1) for v in np.percentile(Q[mm], 2, axis=0)],
                           hi_mm=[round(float(v) * 1e3, 1) for v in np.percentile(Q[mm], 98, axis=0)],
                           d_med_mm=round(float(np.median(D[mm])) * 1e3, 1), d_p90_mm=round(float(np.percentile(D[mm], 90)) * 1e3, 1),
                           per_ep={eps[i]: int(cnt[i]) for i in range(len(eps))},
                           per_ep_frac_permille={eps[i]: round(1e3 * cnt[i] / max(ntot[i], 1), 2) for i in range(len(eps))},
                           n_eps_support=int(sum(1 for i in range(len(eps)) if cnt[i] >= 0.2 * a.min_pts))))
        cl.sort(key=lambda c: -c['n'])
        res[nm] = cl
    out = dict(mesh=a.mesh, sha1_16=__import__('hashlib').sha1(open(a.mesh, 'rb').read()).hexdigest()[:16],
               obs=a.obs.split(','), thr_mm=a.thr_mm, per_episode=per_ep, clusters=res)
    json.dump(out, open(os.path.join(a.out, f'{a.tag}.json'), 'w'), indent=1)
    np.savez_compressed(os.path.join(a.out, f'{a.tag}_pts.npz'), q=q.astype(np.float32), d=d.astype(np.float32),
                        side=side, e=e.astype(np.int8))
    # maps
    import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
    sd = np.where(side, d, -d) * 1e3
    fig, ax = plt.subplots(3, 1, figsize=(16, 13))
    rng = np.random.default_rng(0)
    sub = rng.choice(len(q), min(len(q), 400000), replace=False)
    for axi, (i, j, nm) in zip(ax[:2], ((0, 1, 'top x-y'), (0, 2, 'front x-h'))):
        o = sub[np.argsort(np.abs(sd[sub]))]
        sc = axi.scatter(q[o, i] * 1e3, q[o, j] * 1e3, c=np.clip(sd[o], -15, 15), s=0.3, cmap='coolwarm', vmin=-15, vmax=15)
        axi.set_aspect('equal'); axi.set_title(f'{a.tag} {nm} (signed distance to mesh, mm; red = outside)')
        plt.colorbar(sc, ax=axi, fraction=0.02)
    o = sub
    axi = ax[2]
    axi.scatter(q[o, 0] * 1e3, q[o, 2] * 1e3, c=q[o, 1] * 1e3, s=0.3, cmap='viridis')
    axi.set_aspect('equal'); axi.set_title('front x-h, colour = y (mm)')
    plt.tight_layout(); plt.savefig(os.path.join(a.out, f'{a.tag}_maps.png'), dpi=90)
    print(json.dumps(dict(per_episode=per_ep, n_out=len(res['outside']), n_in=len(res['inside']))))
    for nm in ('outside', 'inside'):
        for c in res[nm][:25]:
            print(nm, json.dumps(c))


if __name__ == '__main__':
    main()
