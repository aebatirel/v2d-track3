"""grid_base.npz: the rack mesh's 1 mm occupancy (exact parity) and the packed hulls' union (centre-inside) on the
rack-frame grid of rs_lib.Grid. Usage: make_grid.py OUT.npz"""
import sys, numpy as np, rs_lib as L
H = L.load_hulls(L.RACK_PACKED); G = L.Grid(H)
M = G.mesh_occ(L.load_mesh(L.RACK_MESH)); PK = G.union_occ(H)
np.savez_compressed(sys.argv[1], M=M, PK=PK, lo=G.lo, n=G.n)
print('mesh', M.sum() / 1e3, 'packed', PK.sum() / 1e3, 'cm3')
