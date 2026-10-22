# GT-free physical check: for each requested body-frame direction (support normal, outward/down), the convex-hull
# support region within 10 deg of it: area, COM margin (>0 = statically stable) and tip angle. Uniform density COM of
# the watertight mesh (centroid if not watertight). Usage: axisrest.py MESH [MESH ...]  (axes: +-x, +-y, +-z)
import sys, json
import numpy as np, trimesh
sys.path.insert(0, '/tmp/claude-0/-home-user-v2d-track3/8c892c5e-fd7c-57aa-abef-68d2af098e4f/scratchpad/interact/code')
import vox
AX = {'+x': [1, 0, 0], '-x': [-1, 0, 0], '+y': [0, 1, 0], '-y': [0, -1, 0], '+z': [0, 0, 1], '-z': [0, 0, -1]}
for p in sys.argv[1:]:
    m = trimesh.load(p, force='mesh'); m.merge_vertices()
    com = m.center_mass if m.is_watertight else m.centroid
    sp = vox.stable_poses(np.asarray(m.convex_hull.vertices), com)
    row = {}
    for k, a in AX.items():
        c = [d for d in sp if np.dot(d['normal'], a) >= np.cos(np.radians(10))]
        if not c:
            row[k] = None; continue
        d = max(c, key=lambda d: d['area_cm2'])
        row[k] = dict(area=round(d['area_cm2'], 1), margin_mm=round(d['margin_mm'], 1), tip=round(d['tip_deg'], 1))
    print(p.split('/interact/')[-1], json.dumps(row), flush=True)
