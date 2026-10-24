"""Sharpa Wave collision geometry summary (right hand): per collision mesh, convexity, extents, volume.
Usage: python -I hand_geom.py ASSETS_DIR"""
import sys, os
import numpy as np
import trimesh

A = sys.argv[1]
d = os.path.join(A, 'meshes/sharpawave/right_cvx')
for f in sorted(os.listdir(d)):
    if not f.lower().endswith('.stl') or 'visual' in f:
        continue
    m = trimesh.load(os.path.join(d, f), force='mesh')
    ext = m.bounding_box.extents * 1000
    h = m.convex_hull
    print(f"{f:28s} verts {len(m.vertices):5d} faces {len(m.faces):5d} convex {m.is_convex!s:5s} "
          f"extents_mm {np.round(np.sort(ext)[::-1], 1).tolist()} vol_cm3 {m.volume * 1e6:.2f} hull_vol_cm3 {h.volume * 1e6:.2f}")
