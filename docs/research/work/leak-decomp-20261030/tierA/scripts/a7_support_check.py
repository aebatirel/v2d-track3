"""ORACLE (public): A7 side check. At each A7 rest configuration (frame 0 here), per object: footprint of the vertices
within 3 mm of the lowest point (convex hull in xy, cm^2) and whether the volume centroid projects inside it."""
import sys, numpy as np, trimesh
from scipy.spatial import ConvexHull, Delaunay
W = sys.argv[1]
for ep, g in [(11, 'lib'), (11, 'scan'), (11, 'lib_xkit'), (31, 'lib'), (31, 'scan'), (18, 'lib'), (18, 'scan'), (21, 'lib'), (21, 'scan')]:
    Z = np.load(f'{W}/a7/ep{ep}/{g}.npz'); A = str(Z['assets']); names = [str(x) for x in Z['names']]; C = Z['configs'][0]
    row = []
    for b, n in enumerate(names):
        m = trimesh.load(f'{A}/mesh/{n}/{n}.glb', force='mesh')
        V = np.asarray(m.vertices) @ C[b, :3, :3].T + C[b, :3, 3]
        com = (m.center_mass if m.is_watertight else m.centroid) @ C[b, :3, :3].T + C[b, :3, 3]
        low = V[V[:, 2] < V[:, 2].min() + 0.003][:, :2]
        try:
            h = ConvexHull(low); area = h.volume * 1e4; inside = bool(Delaunay(low[h.vertices]).find_simplex(com[:2]) >= 0)
        except Exception:
            area, inside = 0.0, False
        row.append(f'{n}: base z {V[:, 2].min() - 0.60:+.4f} m, footprint {area:.2f} cm2 ({len(low)} verts), com over footprint {inside}, watertight {m.is_watertight}')
    print(f'ep{ep} {g}: ' + '; '.join(row))
