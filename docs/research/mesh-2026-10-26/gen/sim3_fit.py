"""GT-free Sim(3) registration of a generated mesh (arbitrary frame and scale) to OUR observed points of the object.

Batch-2 generative probe, 2026-10-29. Observed points = obs_points.py output (our stereo depth along our own track,
object frame, hands/table/other objects removed), subsampled. Multi-start (24 proper rotations of the cube group
applied after PCA alignment, x scale from the PCA extents) trimmed ICP with scale (Umeyama), objective =
trimmed mean of the two one-sided distances (obs -> mesh over the best 90 % of observed points, mesh -> obs over the
best 70 % of mesh samples, since part of the true surface is never observed). The best start is kept. Output: the
mesh mapped into our object frame (metres), plus a JSON line with the fit residuals. No scan, no mocap.
Usage: sim3_fit.py --obs OBS.npz --out OUT.ply [--n 20000] mesh.ply
"""
import argparse, itertools, json, os, sys
import numpy as np
import trimesh
from scipy.spatial import cKDTree


def rotations24():
    out = []
    for perm in itertools.permutations(range(3)):
        for signs in itertools.product([1, -1], repeat=3):
            R = np.zeros((3, 3))
            for i, (p, s) in enumerate(zip(perm, signs)):
                R[i, p] = s
            if np.linalg.det(R) > 0:
                out.append(R)
    return out


def umeyama(src, dst):
    ms, md = src.mean(0), dst.mean(0)
    a, b = src - ms, dst - md
    U, S, Vt = np.linalg.svd(b.T @ a / len(src))
    D = np.eye(3); D[2, 2] = np.sign(np.linalg.det(U @ Vt))
    R = U @ D @ Vt
    s = np.trace(np.diag(S) @ D) / (a ** 2).sum(1).mean()
    return s, R, md - s * R @ ms


def pca(x):
    c = x.mean(0)
    w, V = np.linalg.eigh(np.cov((x - c).T))
    V = V[:, ::-1].copy()
    if np.linalg.det(V) < 0:                           # proper rotation, so the 24 starts are rotations too
        V[:, 2] *= -1
    return c, V, np.sqrt(np.maximum(w[::-1], 1e-12))


def fit(M, O, iters=40, keep_o=0.9, keep_m=0.7):
    to = cKDTree(O)
    cm, Vm, sm = pca(M); co, Vo, so = pca(O)
    s0 = float(np.median(so / sm))
    best = None
    for Rs in rotations24():
        R = Vo @ Rs @ Vm.T
        if np.linalg.det(R) < 0:
            continue
        s, t = s0, co - s0 * R @ cm
        for _ in range(iters):
            X = s * M @ R.T + t
            tx = cKDTree(X)
            do, io = tx.query(O)                       # obs -> mesh
            dm, im = to.query(X)                       # mesh -> obs
            ko = do <= np.quantile(do, keep_o); km = dm <= np.quantile(dm, keep_m)
            src = np.r_[M[io[ko]], M[km]]; dst = np.r_[O[ko], O[im[km]]]
            s, R, t = umeyama(src, dst)
        X = s * M @ R.T + t
        do = cKDTree(X).query(O)[0]; dm = to.query(X)[0]
        obj = float(np.sort(do)[:int(keep_o * len(do))].mean() + np.sort(dm)[:int(keep_m * len(dm))].mean())
        if best is None or obj < best[0]:
            best = (obj, s, R, t, float(np.median(do)), float(np.median(dm)))
    return best


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--obs', required=True); ap.add_argument('--out', required=True)
    ap.add_argument('--n', type=int, default=20000); ap.add_argument('mesh')
    a = ap.parse_args()
    rng = np.random.default_rng(0)
    O = np.load(a.obs)['pts']
    if len(O) > a.n:
        O = O[rng.choice(len(O), a.n, replace=False)]
    m = trimesh.load(a.mesh, force='mesh', process=False)
    M = trimesh.sample.sample_surface(m, a.n, seed=0)[0]
    obj, s, R, t, med_o, med_m = fit(M, O)
    v = s * np.asarray(m.vertices) @ R.T + t
    os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
    trimesh.Trimesh(v, m.faces, process=False).export(a.out)
    print(json.dumps(dict(mesh=a.mesh, out=a.out, scale=round(s, 6), objective_m=round(obj, 5),
                          med_obs_to_mesh_mm=round(med_o * 1e3, 2), med_mesh_to_obs_mm=round(med_m * 1e3, 2),
                          R=R.round(6).tolist(), t=t.round(6).tolist())))


if __name__ == '__main__':
    main()
