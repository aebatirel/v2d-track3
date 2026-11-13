"""ORACLE: signed penetration of the sweeper scan into the rack scan (nearest-surface normal sign) at f0/f20/f260, for the
truth and for the perceived relative poses (P_s; P_o in scan frames by X*_geom); and the same with OUR library_v3 meshes at
the perceived lib-frame poses (GT-free quantity: this is what an inference-side depenetration step would see)."""
import sys, numpy as np, trimesh
from scipy.spatial import cKDTree
sys.path.insert(0, sys.argv[1]); import diag31 as D
names, gt, N, tr = D.load_tracks(); XF = D.XF
def sdf_setup(mesh, n=400000, seed=6):
    p, fi = trimesh.sample.sample_surface(mesh, n, seed=seed); return cKDTree(p), p, mesh.face_normals[fi]
def pen(Ts, Tr, spts, setup):
    tree, p, nr = setup
    M = np.linalg.inv(Tr) @ Ts; q = spts @ M[:3, :3].T + M[:3, 3]
    d, i = tree.query(q); s = np.einsum('ij,ij->i', q - p[i], nr[i])
    inside = (s < -0.0005) & (d < 0.03)
    return dict(frac_inside=round(float(inside.mean()), 4), max_mm=round(float(-s[inside].min() * 1000), 1) if inside.any() else 0.0,
                p95_mm=round(float(np.percentile(-s[inside], 95) * 1000), 1) if inside.any() else 0.0)
scan = {n: trimesh.load(XF.scan_path(D.T3D, n), force='mesh') for n in names}
lib = {n: trimesh.load(f'{D.REPO}/meshes/library_v3/{n}.glb', force='mesh') for n in names}
print('rack scan normals outward check: watertight', scan['plastic_dish_rack'].is_watertight, 'lib rack watertight', lib['plastic_dish_rack'].is_watertight)
ss = sdf_setup(scan['plastic_dish_rack']); sl = sdf_setup(lib['plastic_dish_rack'])
sp_s = trimesh.sample.sample_surface(scan['mini_sweeper'], 6000, seed=5)[0]
sp_l = trimesh.sample.sample_surface(lib['mini_sweeper'], 6000, seed=5)[0]
V = np.load(f'{D.RUN}/perc2/poses_world_vo.npz')
for f in (0, 20, 100, 135, 260):
    r = dict(truth_scan=pen(gt['mini_sweeper'][f], gt['plastic_dish_rack'][f], sp_s, ss),
             Ps_scan=pen(tr['Ps']['mini_sweeper'][f], tr['Ps']['plastic_dish_rack'][f], sp_s, ss),
             Po_scan=pen(tr['Po']['mini_sweeper'][f], tr['Po']['plastic_dish_rack'][f], sp_s, ss),
             Po_lib_GTfree=pen(V['mini_sweeper'][f].astype(float), V['plastic_dish_rack'][f].astype(float), sp_l, sl))
    print('f%d' % f, r)
