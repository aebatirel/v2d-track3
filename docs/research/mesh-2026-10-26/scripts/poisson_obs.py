"""Screened Poisson surface from OBSERVED points (obs_points.py), no GT.

Normals: PCA over k nearest neighbours, oriented towards the camera that observed each point, so the two faces of a
thin wall get opposite normals (the TSDF average cancels them instead). Screened Poisson (pymeshlab, Kazhdan & Hoppe
2013) closes the never-observed parts smoothly. Optional trimming drops the surface far from any observation
(--trim_mm; 0 keeps the closed surface, which the scorer's scans mostly have: they include undersides).
Optional --table: points on the support plane under the object during rest frames (obs_points.py --rest_table) are
added as surface samples with normals pointing down (a resting object touches the table; Vysics-style support prior).
Usage: poisson_obs.py OBS.npz OUT.glb [--depth 10] [--pw 4] [--spn 1.5] [--k 24] [--trim_mm 0] [--max_pts 400000]
"""
import argparse, json, time
import numpy as np
import trimesh
from scipy.spatial import cKDTree


def oriented_normals(P, C, k):
    tree = cKDTree(P)
    _, nb = tree.query(P, k=k)
    Q = P[nb] - P[nb].mean(1, keepdims=True)
    cov = np.einsum('nki,nkj->nij', Q, Q) / k
    w, V = np.linalg.eigh(cov)
    n = V[:, :, 0]
    flip = np.einsum('ni,ni->n', n, C - P) < 0
    n[flip] *= -1
    return n


def main():
    p = argparse.ArgumentParser()
    p.add_argument('obs'); p.add_argument('out')
    p.add_argument('--depth', type=int, default=10); p.add_argument('--pw', type=float, default=4.0)
    p.add_argument('--spn', type=float, default=1.5); p.add_argument('--k', type=int, default=24)
    p.add_argument('--trim_mm', type=float, default=0.0); p.add_argument('--max_pts', type=int, default=400000)
    p.add_argument('--vox', type=float, default=0.001)
    a = p.parse_args()
    t0 = time.time()
    Z = np.load(a.obs); P = Z['pts'].astype(np.float64); C = Z['cam'].astype(np.float64)
    key = np.floor(P / a.vox).astype(np.int64)
    _, first = np.unique(key, axis=0, return_index=True)
    P, C = P[first], C[first]
    if len(P) > a.max_pts:
        s = np.random.default_rng(0).choice(len(P), a.max_pts, replace=False); P, C = P[s], C[s]
    N = oriented_normals(P, C, a.k)
    import pymeshlab
    ms = pymeshlab.MeshSet()
    ms.add_mesh(pymeshlab.Mesh(vertex_matrix=P, v_normals_matrix=N))
    ms.generate_surface_reconstruction_screened_poisson(depth=a.depth, pointweight=a.pw, samplespernode=a.spn,
                                                        preclean=True)
    m = ms.current_mesh()
    V, F = m.vertex_matrix(), m.face_matrix()
    mesh = trimesh.Trimesh(V, F, process=True)
    info = dict(points=int(len(P)), faces_raw=int(len(mesh.faces)))
    if a.trim_mm > 0:
        d = cKDTree(P).query(mesh.triangles_center)[0]
        mesh.update_faces(d <= a.trim_mm * 1e-3); mesh.remove_unreferenced_vertices()
    # keep the largest connected piece and any piece >= 5 % of its area (Poisson can leave small bubbles)
    parts = mesh.split(only_watertight=False)
    if len(parts) > 1:
        big = max(parts, key=lambda q: q.area)
        mesh = trimesh.util.concatenate([q for q in parts if q.area >= 0.05 * big.area])
    mesh.export(a.out)
    info.update(faces=int(len(mesh.faces)), area_cm2=round(mesh.area * 1e4, 1), watertight=bool(mesh.is_watertight),
                extents_cm=np.round(mesh.extents * 100, 1).tolist(), sec=round(time.time() - t0, 1), out=a.out)
    print(json.dumps(info))


if __name__ == '__main__':
    main()
