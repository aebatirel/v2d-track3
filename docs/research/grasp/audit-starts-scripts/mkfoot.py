"""HYPOTHESIS TEST ASSET (no ground truth): complete a partially observed circular base. At our reference frame-0 pose,
fit a circle to the mesh points 0-2 cm above the table (the observed part of the base rim), and add a URDF <cylinder>
collision primitive (exact analytic collider; CoACD never sees it) of that radius and HEIGHT m, axis = the table normal,
bottom 0.5 mm above the table top. Mass / COM / inertia unchanged (explicit URDF inertial).
Usage: mkfoot.py EP OBJ OUT_URDF [HEIGHT=0.02] [RADIUS_SCALE=1.0]"""
import sys, os, re, glob, numpy as np, trimesh
sys.path.insert(0, __file__.rsplit('/', 1)[0])
from common import *
ep, o, out = int(sys.argv[1]), sys.argv[2], sys.argv[3]
L = float(sys.argv[4]) if len(sys.argv) > 4 else 0.02; rs = float(sys.argv[5]) if len(sys.argv) > 5 else 1.0
d = load_ref(ref_path(ep)); j = d['names'].index(o); p, q = d['OP'][0, j], d['OQ'][0, j]
m = trimesh.load(f'{LIB}/{o}.glb', force='mesh')
V = local_to_world(trimesh.sample.sample_surface(m, 300000, seed=0)[0], p, q); h = V[:, 2] - 0.6
P = V[(h >= 0) & (h < 0.02)][:, :2]
A = np.c_[2 * P, np.ones(len(P))]; b = (P ** 2).sum(1); x = np.linalg.lstsq(A, b, rcond=None)[0]; cc = x[:2]; r = rs * np.sqrt(x[2] + cc @ cc)
centre_w = np.array([cc[0], cc[1], 0.6005 + L / 2])
centre_o = world_to_local(centre_w[None], p, q)[0]
Rz = R.from_quat(q).inv()                                       # world z axis expressed in the object frame
rpy = Rz.as_euler('xyz')                                        # cylinder frame (z = axis) -> object frame
src = glob.glob(f'{run_dir(ep)}/refs/sf/ep{ep}/assets/urdf/{o}_rigid.urdf')[0]
txt = open(src).read()
mesh_abs = os.path.normpath(os.path.join(os.path.dirname(src), '../mesh', o, f'{o}.glb'))
txt = txt.replace(f'../mesh/{o}/{o}.glb', mesh_abs)
cyl = (f'    <collision>\n      <origin xyz="{centre_o[0]:.6f} {centre_o[1]:.6f} {centre_o[2]:.6f}" rpy="{rpy[0]:.6f} {rpy[1]:.6f} {rpy[2]:.6f}"/>\n'
       f'      <geometry><cylinder radius="{r:.5f}" length="{L:.5f}"/></geometry>\n    </collision>\n  </link>')
txt = txt.replace('  </link>', cyl, 1)
os.makedirs(os.path.dirname(out), exist_ok=True); open(out, 'w').write(txt)
print(f'{out}: cylinder r {100*r:.2f} cm, L {100*L:.1f} cm, centre (world) {centre_w.round(4)}, object frame {centre_o.round(4)}')
