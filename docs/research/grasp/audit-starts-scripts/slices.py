"""Horizontal slices of an object's mesh at our reference frame-0 pose (no GT): per 1 cm height band above the table,
point count, convex-hull area of the band's xy points, centroid offset from the COM projection, and whether the COM
projection lies inside that band's hull. Usage: slices.py EP OBJ [MAXCM]"""
import sys, numpy as np, trimesh, glob, xml.etree.ElementTree as ET
from scipy.spatial import ConvexHull
sys.path.insert(0, __file__.rsplit('/', 1)[0])
from common import *
ep, o = int(sys.argv[1]), sys.argv[2]; mx = int(sys.argv[3]) if len(sys.argv) > 3 else 20
d = load_ref(ref_path(ep)); j = d['names'].index(o); p, q = d['OP'][0, j], d['OQ'][0, j]
m = trimesh.load(f'{LIB}/{o}.glb', force='mesh')
u = glob.glob(f'{run_dir(ep)}/refs/sf/ep{ep}/assets/urdf/{o}_rigid.urdf')[0]
com = np.array([float(x) for x in ET.parse(u).getroot().find('link/inertial/origin').get('xyz').split()]); c = local_to_world(com[None], p, q)[0]
V = local_to_world(trimesh.sample.sample_surface(m, 300000, seed=0)[0], p, q); h = V[:, 2] - 0.6
for b in range(0, mx):
    P = V[(h >= b / 100) & (h < (b + 1) / 100)][:, :2]
    if len(P) < 10:
        print(f'{b:2d}-{b+1:2d} cm: {len(P)} pts'); continue
    ch = ConvexHull(P); s = ch.equations[:, :2] @ c[:2] + ch.equations[:, 2]
    print(f'{b:2d}-{b+1:2d} cm: {len(P):6d} pts, hull area {1e4*ch.volume:6.1f} cm2, extent {100*(P.max(0)-P.min(0)).round(3)} cm, centroid-COM {100*np.linalg.norm(P.mean(0)-c[:2]):5.1f} cm, COM inside {bool((s<=0).all())} margin {-100*s.max():5.1f} cm')
