"""Construction diagnostic (not a gate): where the F cells left inside a build's pieces lie, by distance from the rack
mesh surface. Usage: diag_left.py BUILD_DIR EP[,EP]"""
import sys, glob, numpy as np, trimesh
from scipy.spatial import cKDTree
import rs_lib as L
bd, eps = sys.argv[1], sys.argv[2].split(',')
H = L.load_hulls(L.RACK_PACKED); G = L.Grid(H)
z0 = np.load(f'{L.SCR}/rackslot/grid_base.npz'); M, PK = z0['M'], z0['PK']
RV = np.zeros(G.n, bool)
for ep in eps:
    R, _ = L.rest_frames(ep); P = L.poses(ep)
    RV |= L.rest_volume(G, L.load_hulls(L.GUEST[ep]['packed']), P['rel'], R, PK)
C = [np.asarray(trimesh.load(f, force='mesh').vertices) for f in sorted(glob.glob(f'{bd}/plastic_dish_rack/piece_*.obj'))]
CO = G.union_occ(C)
left = RV & CO & ~M
rack = L.load_mesh(L.RACK_MESH)
S = np.asarray(trimesh.sample.sample_surface_even(rack, int(rack.area / 0.0003 ** 2), seed=3)[0])
d = cKDTree(S).query(G.centres(left))[0] * 1e3
F = RV & PK & ~M
dF = cKDTree(S).query(G.centres(F))[0] * 1e3
print(bd.split('/')[-1], 'pieces', len(C), 'F', F.sum() / 1e3, 'left', left.sum() / 1e3, 'cm3')
for t in (0.6, 0.8, 1.0, 1.5, 2.0, 3.0):
    print(f'  within {t} mm of the mesh surface: left {(d <= t).sum() / 1e3:.3f} cm3 of F {(dF <= t).sum() / 1e3:.3f}')
print('  left beyond 1.0 mm:', (d > 1.0).sum() / 1e3, ' max dist mm', d.max() if len(d) else 0)
