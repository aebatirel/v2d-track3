"""Geometry facts about the public scans and our library meshes that matter for the registered scorer's stand-ins.
For every public scan: glTF node transforms (does trimesh's force='mesh' change the vertices?), surface centroid
(our anchor stand-in), bounding-box centre, vertex mean, frame origin, extents, PCA eigenvalues and the symmetry axis
our scorer derives (cups: distinct principal axis; lid: thinnest), and that axis' angle to the nearest coordinate axis.
For each library mesh: the same node-transform check (budget_mesh loads with force='mesh', process=False; make_assets
loads with force='mesh' and re-exports flattened).
Usage: python -I scan_geometry.py T3_DIR KIT_DIR LIB_DIR... > scan_geometry.json
"""
import sys, json, os, glob
import numpy as np, trimesh
t3, kit, libs = sys.argv[1], sys.argv[2], sys.argv[3:]
sys.path.insert(0, kit)
from v2dlb.object_mesh import _surface_moments
from v2dlb.mesh_common import _sample_mesh_surface

def node_info(path):
    sc = trimesh.load(path, force='scene')
    nonid = []
    for nm in sc.graph.nodes_geometry:
        T, g = sc.graph[nm]
        if not np.allclose(T, np.eye(4), atol=1e-9):
            nonid.append({'node': nm, 'T': np.round(T, 6).tolist()})
    return len(sc.geometry), nonid

out = {'scans': {}, 'library': {}}
for d in sorted(glob.glob(f'{t3}/mesh/*/')):
    n = os.path.basename(d.rstrip('/'))
    p = f'{d}{n}.glb'
    if not os.path.exists(p):
        p = f'{d}{n}_visual.glb'
    m = trimesh.load(p, force='mesh')
    v, f = np.asarray(m.vertices, float), np.asarray(m.faces, np.int64)
    c, r = _surface_moments(v, f)
    pts = _sample_mesh_surface(v, f, 1000, 7) - c
    w, U = np.linalg.eigh(np.cov(pts.T))
    k = int(np.argmax([abs(w[i] - np.mean(np.delete(w, i))) for i in range(3)]))
    ngeo, nonid = node_info(p)
    bb = (v.min(0) + v.max(0)) / 2
    def ang(ax):
        return float(np.degrees(np.arccos(min(1, np.max(np.abs(ax))))))
    out['scans'][n] = dict(file=os.path.basename(p), n_vertices=len(v), n_faces=len(f), n_geometries=ngeo,
                           non_identity_nodes=nonid,
                           extents_cm=np.round((v.max(0) - v.min(0)) * 100, 2).tolist(),
                           surface_centroid_cm=np.round(c * 100, 2).tolist(), radius_cm=round(r * 100, 2),
                           bbox_centre_cm=np.round(bb * 100, 2).tolist(),
                           vertex_mean_cm=np.round(v.mean(0) * 100, 2).tolist(),
                           centroid_to_bbox_cm=round(float(np.linalg.norm(c - bb) * 100), 2),
                           centroid_to_origin_cm=round(float(np.linalg.norm(c) * 100), 2),
                           pca_eig_cm2=np.round(w * 1e4, 3).tolist(),
                           distinct_axis=np.round(U[:, k], 4).tolist(), distinct_axis_off_coord_deg=round(ang(U[:, k]), 2),
                           thinnest_axis=np.round(U[:, 0], 4).tolist(), thinnest_axis_off_coord_deg=round(ang(U[:, 0]), 2))
for lib in libs:
    for p in sorted(glob.glob(f'{lib}/*.glb')):
        ngeo, nonid = node_info(p)
        out['library'][f'{os.path.basename(lib)}/{os.path.basename(p)}'] = dict(n_geometries=ngeo, non_identity_nodes=nonid)
print(json.dumps(out, indent=1))
