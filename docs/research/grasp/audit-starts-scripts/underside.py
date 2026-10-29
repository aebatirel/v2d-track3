"""Underside height map of an object at our reference frame-0 pose (no GT): lowest hull/mesh height above the table per
1 cm cell over the footprint, the COM projection, and the fill depth a flat base would need to put the COM over a
support with a margin. Usage: underside.py EP OBJ"""
import sys, json, numpy as np, trimesh, glob, xml.etree.ElementTree as ET
sys.path.insert(0, __file__.rsplit('/', 1)[0])
from common import *
ep, o = int(sys.argv[1]), sys.argv[2]
d = load_ref(ref_path(ep)); j = d['names'].index(o); p, q = d['OP'][0, j], d['OQ'][0, j]
m = trimesh.load(f'{LIB}/{o}.glb', force='mesh'); Hh = Hulls(hull_path(o))
u = glob.glob(f'{run_dir(ep)}/refs/sf/ep{ep}/assets/urdf/{o}_rigid.urdf')[0]
com = np.array([float(x) for x in ET.parse(u).getroot().find('link/inertial/origin').get('xyz').split()]); c = local_to_world(com[None], p, q)[0]
for lab, V in (('mesh', trimesh.sample.sample_surface(m, 200000, seed=0)[0]), ('hulls', np.concatenate([trimesh.sample.sample_surface(h, 5000, seed=k)[0] for k, h in enumerate(Hh.H)]))):
    Wp = local_to_world(V, p, q); xy0 = Wp[:, :2].min(0); ij = np.floor((Wp[:, :2] - xy0) / 0.01).astype(int)
    G = {}
    for (i, k), z in zip(map(tuple, ij), Wp[:, 2]):
        G[(i, k)] = min(G.get((i, k), 9), z)
    I = max(i for i, _ in G) + 1; K = max(k for _, k in G) + 1
    M = np.full((I, K), np.nan)
    for (i, k), z in G.items():
        M[i, k] = 1000 * (z - 0.6)
    ci = (c[:2] - xy0) / 0.01
    print(f'== {lab}: footprint {I}x{K} cm, COM at cell ({ci[0]:.1f},{ci[1]:.1f}), COM height {100*(c[2]-0.6):.1f} cm; lowest {np.nanmin(M):.1f} mm')
    print('   rows = x (1 cm), values = lowest point above the table in mm (.. = none); * = COM cell')
    for i in range(I):
        print('   ' + ' '.join(('  *' if (i == int(ci[0]) and k == int(ci[1])) else '') + ('  ..' if np.isnan(M[i, k]) else f'{M[i,k]:4.0f}') for k in range(K)))
    # fill depth needed: smallest h such that cells with lowest point < h form a convex region containing the COM with >= 1 cm margin
    from scipy.spatial import ConvexHull
    for h in (5, 10, 20, 30, 40, 50, 60, 80):
        pts = np.array([[i + .5, k + .5] for (i, k), z in G.items() if 1000 * (z - 0.6) < h])
        if len(pts) < 3:
            continue
        ch = ConvexHull(pts); s = ch.equations[:, :2] @ ci + ch.equations[:, 2]
        print(f'   fill to {h:3d} mm: support cells {len(pts)}, COM inside {bool((s<=0).all())}, margin {-s.max():.1f} cm')
