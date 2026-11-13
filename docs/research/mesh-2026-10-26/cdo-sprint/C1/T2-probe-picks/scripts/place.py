"""GT-free placement of an already-scored generated mesh into the library_v3 object frame (C1/T2, PREREG.md s2).

Reads ONLY: the candidate mesh (the probe-scored sam3d_sim3 ply) and our library_v3 mesh of the same object.
No scan, mocap, parquet pose or *_align.npz is read here.

Method (the diag-2026-10-30 'lib' registration, sam-placement/common.py best_sim3, functions copied below):
  Sim(3) (free scale) symmetric trimmed ICP (keep 0.9 both ways, 30 iterations) of 8000 candidate surface samples
  (seed 0) onto 8000 library_v3 surface samples (seed 3); multi-start = the 24 proper signed permutations of the
  PCA axes (initial scale = geometric mean of the PCA sigma ratios) + the identity (the candidate as placed by the
  probe's point fit). The start with the smallest trimmed symmetric mean distance wins. The kit's CD-O normalises
  scale and registers rigidly, so the placed copy has the probe's CD-O; only its frame (and size) changes.
Writes OUT.glb (the placed mesh, vertex order and faces kept) and OUT.json (transform, residuals, GT-free checks).
Usage: place.py OBJECT CANDIDATE.ply LIBRARY.glb OUT_STEM
"""
import hashlib, itertools, json, math, os, sys
import numpy as np
import trimesh
from scipy.spatial import cKDTree

N, ITERS, KEEP = 8000, 30, 0.9
AXIAL = {'beige_cup', 'blue_cup'}


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


def umeyama(src, dst, with_scale=True):
    w = np.full(len(src), 1.0 / len(src))
    ms, md = w @ src, w @ dst
    a, b = src - ms, dst - md
    U, S, Vt = np.linalg.svd((b * w[:, None]).T @ a)
    D = np.eye(3); D[2, 2] = np.sign(np.linalg.det(U @ Vt))
    R = U @ D @ Vt
    s = np.trace(np.diag(S) @ D) / (w @ (a ** 2).sum(1)) if with_scale else 1.0
    return s, R, md - s * R @ ms


def pca(x):
    c = x.mean(0)
    w, V = np.linalg.eigh(np.cov((x - c).T))
    V = V[:, ::-1].copy()
    if np.linalg.det(V) < 0:
        V[:, 2] *= -1
    return c, V, np.sqrt(np.maximum(w[::-1], 1e-12))


def apply(T, x):
    s, R, t = T
    return s * x @ R.T + t


def angle_deg(R):
    return math.degrees(math.acos(max(-1.0, min(1.0, (np.trace(R) - 1) / 2))))


def sim3_icp(M, Y, T0, iters=ITERS, keep=KEEP):
    ty = cKDTree(Y)
    T = T0
    for _ in range(iters):
        X = apply(T, M)
        dy, iy = cKDTree(X).query(Y)
        dm, im = ty.query(X)
        ky = dy <= np.quantile(dy, keep)
        km = dm <= np.quantile(dm, keep)
        T = umeyama(np.r_[M[iy[ky]], M[km]], np.r_[Y[ky], Y[im[km]]])
    return T


def sym_dist(A, B, keep=KEEP):
    da = np.sort(cKDTree(B).query(A)[0]); db = np.sort(cKDTree(A).query(B)[0])
    return 0.5 * (da[:int(keep * len(da))].mean() + db[:int(keep * len(db))].mean())


def cup_axis(P):
    """GT-free cup axis: the PCA axis the points are most invariant under a 90 deg turn about (mesh_metric.sym_axis)."""
    c, V, _ = pca(P)
    tree = cKDTree(P)
    best = None
    for k in range(3):
        a = V[:, k]
        K = np.array([[0, -a[2], a[1]], [a[2], 0, -a[0]], [-a[1], a[0], 0]])
        Rq = np.eye(3) + K + K @ K                         # rotation by 90 deg: I + sin K + (1 - cos) K^2
        d = tree.query((P - c) @ Rq.T + c)[0].mean()
        if best is None or d < best[0]:
            best = (d, a.copy())
    return best[1]


def sha256(p):
    return hashlib.sha256(open(p, 'rb').read()).hexdigest()


def main():
    obj, cand_p, lib_p, stem = sys.argv[1:5]
    cand = trimesh.load(cand_p, force='mesh', process=False)
    lib = trimesh.load(lib_p, force='mesh', process=False)
    M = np.asarray(trimesh.sample.sample_surface(cand, N, seed=0)[0])
    Y = np.asarray(trimesh.sample.sample_surface(lib, N, seed=3)[0])
    cm, Vm, sm = pca(M); cy, Vy, sy = pca(Y)
    s0 = float(np.exp(np.mean(np.log(sy / sm))))
    starts = [('pca%02d' % i, (s0, Vy @ Rs @ Vm.T, cy - s0 * (Vy @ Rs @ Vm.T) @ cm)) for i, Rs in enumerate(rotations24())]
    starts.append(('identity', (1.0, np.eye(3), np.zeros(3))))
    res = []
    for name, T0 in starts:
        T = sim3_icp(M, Y, T0)
        res.append(dict(start=name, j_mm=sym_dist(apply(T, M), Y) * 1e3, T=T))
    res.sort(key=lambda r: r['j_mm'])
    best = res[0]
    s, R, t = best['T']
    axial = obj in AXIAL
    if axial:                                      # only the axis matters: distinct = axis tilt > 30 deg
        a_m = cup_axis(M)                          # candidate axis in the candidate's own frame

        def dist_from_best(T):                     # tilt between where this fit and the best fit send that axis
            return math.degrees(math.acos(min(1.0, abs(float((T[1] @ a_m) @ (R @ a_m))))))
    else:
        def dist_from_best(T):
            return angle_deg(T[1] @ R.T)
    alt = [r for r in res[1:] if dist_from_best(r['T']) > 30]
    ident = next(r for r in res if r['start'] == 'identity')
    # placed mesh
    V = apply(best['T'], np.asarray(cand.vertices, np.float64))
    placed = trimesh.Trimesh(V, np.asarray(cand.faces), process=False)
    out_glb = stem + '.glb'
    placed.export(out_glb)
    back = trimesh.load(out_glb, force='mesh', process=False)
    rt_err = float(np.abs(np.asarray(back.vertices) - V).max()) if len(back.vertices) == len(V) else None
    Mp = apply(best['T'], M)
    info = dict(object=obj, candidate=cand_p, candidate_sha256=sha256(cand_p), library=lib_p, library_sha256=sha256(lib_p),
                out=out_glb, out_sha256=sha256(out_glb), n_samples=N, iters=ITERS, keep=KEEP,
                best_start=best['start'], residual_mm=round(best['j_mm'], 4), scale=float(s),
                R=np.round(R, 8).tolist(), t=np.round(t, 8).tolist(),
                rot_from_probe_deg=round(angle_deg(R), 3), trans_from_probe_mm=round(float(np.linalg.norm(t)) * 1e3, 3),
                centroid_shift_mm=round(float(np.linalg.norm(Mp.mean(0) - M.mean(0))) * 1e3, 3),
                identity_start_residual_mm=round(ident['j_mm'], 4),
                second_distinct_residual_mm=round(alt[0]['j_mm'], 4) if alt else None,
                second_distinct_start=alt[0]['start'] if alt else None,
                second_distinct_angle_deg=round(dist_from_best(alt[0]['T']), 1) if alt else None,
                all_starts=[dict(start=r['start'], j_mm=round(r['j_mm'], 4), scale=round(float(r['T'][0]), 5),
                                 rot_from_best_deg=round(angle_deg(r['T'][1] @ R.T), 1)) for r in res],
                glb_roundtrip_max_err_m=rt_err, n_vertices=int(len(V)), n_faces=int(len(cand.faces)))
    if axial:
        a_lib = cup_axis(Y)
        a_c = cup_axis(Mp)
        info['axis_angle_to_library_deg'] = round(math.degrees(math.acos(min(1.0, abs(float(a_lib @ a_c))))), 3)
    json.dump(info, open(stem + '.json', 'w'), indent=1)
    print(json.dumps({k: v for k, v in info.items() if k not in ('all_starts', 'R')}, indent=1))


if __name__ == '__main__':
    main()
