"""GT-free helper: stable resting faces of a mesh = convex-hull facets (coplanar triangle groups) whose plane contains the
projection of the centre of mass (surface centroid if not watertight). Returns outward unit normals (body 'down'
directions when resting on that facet), facet areas and the COM-in-facet margin (m)."""
import numpy as np, trimesh


def stable_faces(mesh):
    h = mesh.convex_hull
    com = mesh.center_mass if mesh.is_watertight else np.asarray(mesh.vertices).mean(0)
    groups = [list(f) for f in h.facets]
    used = set(i for g in groups for i in g)
    groups += [[i] for i in range(len(h.faces)) if i not in used]
    out = []
    for g in groups:
        n = h.face_normals[g[0]]; tri = h.triangles[g]
        d = (tri[0, 0] - com) @ n
        q = com + d * n     # projection onto the facet plane
        inside, margin = False, -1.0
        for t in tri:
            v0, v1, v2 = t; e0, e1 = v1 - v0, v2 - v0; w = q - v0
            M = np.array([[e0 @ e0, e0 @ e1], [e0 @ e1, e1 @ e1]]); b = np.array([w @ e0, w @ e1])
            try:
                u, v = np.linalg.solve(M, b)
            except np.linalg.LinAlgError:
                continue
            if u >= -1e-9 and v >= -1e-9 and u + v <= 1 + 1e-9:
                inside = True
        if inside:
            # margin: distance from q to the facet boundary (approx: min distance to facet edge vertices' segments)
            edges = trimesh.graph.shared_edges if False else None
            pts = tri.reshape(-1, 3); margin = float(np.min(np.linalg.norm(pts - q, axis=1)))
            out.append(dict(normal=n.copy(), area=float(h.area_faces[g].sum()), height=float(d), margin=margin))
    out.sort(key=lambda r: -r['area'])
    return out, com
