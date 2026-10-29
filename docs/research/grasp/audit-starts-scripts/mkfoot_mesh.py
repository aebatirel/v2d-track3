"""HYPOTHESIS TEST ASSET (no ground truth): complete a partially observed circular base with a CONVEX MESH prism
(24-gon, 48 vertices <= MuJoCo maxhullvert 64; closed and welded, so CoACD returns it unchanged), radius from a circle
fit to the mesh points in the band [0, BAND] m above the table at our reference frame-0 pose, times RS, height L, axis
= table normal, bottom 0.5 mm above the table. Added as a second <collision> on the object's link; inertial unchanged.
Usage: mkfoot_mesh.py EP OBJ OUTDIR [L=0.02] [RS=1.0] [BAND=0.02]"""
import sys, os, glob, numpy as np, trimesh
sys.path.insert(0, __file__.rsplit('/', 1)[0])
from common import *
ep, o, outd = int(sys.argv[1]), sys.argv[2], sys.argv[3]
L = float(sys.argv[4]) if len(sys.argv) > 4 else 0.02; rs = float(sys.argv[5]) if len(sys.argv) > 5 else 1.0; band = float(sys.argv[6]) if len(sys.argv) > 6 else 0.02
d = load_ref(ref_path(ep)); j = d['names'].index(o); p, q = d['OP'][0, j], d['OQ'][0, j]
m = trimesh.load(f'{LIB}/{o}.glb', force='mesh')
V = local_to_world(trimesh.sample.sample_surface(m, 300000, seed=0)[0], p, q); h = V[:, 2] - 0.6
P = V[(h >= 0) & (h < band)][:, :2]
A = np.c_[2 * P, np.ones(len(P))]; b = (P ** 2).sum(1); x = np.linalg.lstsq(A, b, rcond=None)[0]; cc = x[:2]; r = rs * np.sqrt(x[2] + cc @ cc)
NSEC = int(os.environ.get('NSEC', '1'))                                  # >1: the prism split into NSEC convex sectors
os.makedirs(f'{outd}/urdf', exist_ok=True); stls = []
ang = np.linspace(0, 2 * np.pi, 25)
for k in range(NSEC):
    if NSEC == 1:
        cyl = trimesh.creation.cylinder(radius=r, height=L, sections=24)
    else:
        a = ang[k * 24 // NSEC:(k + 1) * 24 // NSEC + 1]
        ring = np.c_[r * np.cos(a), r * np.sin(a)]; poly = np.r_[[[0, 0]], ring]
        pts = np.r_[np.c_[poly, np.full(len(poly), -L / 2)], np.c_[poly, np.full(len(poly), L / 2)]]
        cyl = trimesh.convex.convex_hull(pts)
    cyl.apply_translation([cc[0], cc[1], 0.6005 + L / 2]); cyl.vertices = world_to_local(cyl.vertices, p, q)
    stl = f'{outd}/urdf/{o}_foot{k}.stl'; cyl.export(stl); stls.append(stl)
src = glob.glob(f'{run_dir(ep)}/refs/sf/ep{ep}/assets/urdf/{o}_rigid.urdf')[0]; txt = open(src).read()
mesh_abs = os.path.normpath(os.path.join(os.path.dirname(src), '../mesh', o, f'{o}.glb')); txt = txt.replace(f'../mesh/{o}/{o}.glb', mesh_abs)
txt = txt.replace('  </link>', ''.join(f'    <collision>\n      <origin xyz="0 0 0" rpy="0 0 0"/>\n      <geometry><mesh filename="{x}" scale="1 1 1"/></geometry>\n    </collision>\n' for x in stls) + '  </link>', 1)
open(f'{outd}/urdf/{o}_rigid.urdf', 'w').write(txt)
print(f'{outd}/urdf/{o}_rigid.urdf: prism r {100*r:.2f} cm L {100*L:.1f} cm, watertight {cyl.is_watertight}, verts {len(cyl.vertices)}, COM offset from centre see slices')
