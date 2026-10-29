# Local fallback (GT-free): where our own 12 mm zero-crossing evidence is unexplained by the fine solid (> R mm from its
# boundary), take the coarse (today's rules: 12 mm, fill) solid within R of that evidence; elsewhere keep the fine solid.
# Usage: localfb.py GRIDS FINE_VAR COARSE_VAR OUTDIR [R_mm]
import sys, os, json, numpy as np, trimesh
from scipy import ndimage
from skimage.measure import marching_cubes
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import obspost2 as op
G, shape, lo, vx = op.load(sys.argv[1].split(',')); fv, cv, od = sys.argv[2:5]; R = float(sys.argv[5]) / 1000 if len(sys.argv) > 5 else 0.008
os.makedirs(od, exist_ok=True)
W = G['W12']; m12 = np.where(W > 0, G['S12'] / np.maximum(W, 1), 1)
ev = (W >= 5) & (np.abs(m12) < 0.25) & (G['M0'] >= 5)
sf, ff, _ = op.build(G, shape, vx, fv); sc, fc, _ = op.build(G, shape, vx, cv)
bnd = sf & ~ndimage.binary_erosion(sf)
un = ev & (ndimage.distance_transform_edt(~bnd) * vx > R)
zone = ndimage.distance_transform_edt(~un) * vx <= R
solid = sf | (sc & zone)
field = np.where(np.pad(zone, 1), np.minimum(ff, fc), ff)        # coarse surface inside the zone, fine elsewhere
verts, faces, _, _ = marching_cubes(field, 0.0, spacing=(vx,) * 3); verts = verts - vx + lo + 0.5 * vx
m = trimesh.Trimesh(verts, faces, process=True)
parts = m.split(only_watertight=False)
if len(parts) > 1:
    big = max(parts, key=lambda q: q.area); m = trimesh.util.concatenate([q for q in parts if q.area >= 0.05 * big.area and np.linalg.norm(q.centroid - big.centroid) < 0.15])
name = f'{fv}__fb{cv}'; m.export(f'{od}/{name}_full.glb')
sys.path.insert(0, op.KIT)
from v2dlb.mesh_budget import budget_mesh
vb, fb = budget_mesh(f'{od}/{name}_full.glb', 4096, 4096); trimesh.Trimesh(vb, fb, process=False).export(f'{od}/{name}.glb')
c = lambda M: round(float(M.sum()) * vx ** 3 * 1e6, 1)  # noqa: E731
print(json.dumps(dict(unexplained_vox=int(un.sum()), zone_cm3=c(zone), fine_cm3=c(sf), coarse_cm3=c(sc), solid_cm3=c(solid), out=f'{od}/{name}.glb')))
