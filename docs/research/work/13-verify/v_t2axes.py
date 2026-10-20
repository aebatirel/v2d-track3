"""Verifier: which axis construction reproduces the STORED Track 2 axes? Compare stored axes (identity) with
(a) area-surface PCA, (b) vertex PCA, (c) solid-volume inertia principal axes, (d) trimesh minimum-volume OBB,
(e) convex-hull surface PCA. Reports max angle (deg) between each stored axis and its best-matching candidate axis."""
import sys, json, numpy as np, trimesh
D = "/Users/aebatirel/Documents/Code/v2d-research/work/13/t2"
names = sys.argv[1:]


def ang(E):  # E columns = candidate axes; angle of each stored axis to nearest candidate axis (sign-free)
    M = np.abs(E.T @ np.eye(3))
    return np.degrees(np.arccos(np.clip(M.max(0), -1, 1))).round(2).tolist()


def pca_area(V, F):
    T = V[F]; a = 0.5 * np.linalg.norm(np.cross(T[:, 1] - T[:, 0], T[:, 2] - T[:, 0]), axis=1); A = a.sum()
    c = (a[:, None] * T.mean(1)).sum(0) / A; Q = T - c
    C = sum(np.einsum("n,ni,nj->ij", a, Q[:, k], Q[:, k]) for k in range(3)) + np.einsum("n,ni,nj->ij", a, Q.sum(1), Q.sum(1))
    return np.linalg.eigh(C / 12 / A)[1]


for n in names:
    z = np.load(f"{D}/{n}.npz"); V, F = z["V"], z["F"]
    m = trimesh.Trimesh(V, F, process=True)
    out = {"name": n, "watertight": bool(m.is_watertight)}
    out["area_pca"] = ang(pca_area(V, F))
    Vc = V - V.mean(0); out["vertex_pca"] = ang(np.linalg.eigh(Vc.T @ Vc)[1])
    try:
        I = m.moment_inertia; out["inertia"] = ang(np.linalg.eigh(I)[1]); out["vol"] = float(m.volume)
    except Exception as e:
        out["inertia"] = str(e)
    try:
        to, ext = trimesh.bounds.oriented_bounds(m)
        out["obb"] = ang(to[:3, :3].T); out["obb_ext_mm"] = (1000 * np.array(ext)).round(1).tolist()
    except Exception as e:
        out["obb"] = str(e)
    h = m.convex_hull; out["hull_pca"] = ang(pca_area(h.vertices, h.faces))
    print(json.dumps(out), flush=True)
