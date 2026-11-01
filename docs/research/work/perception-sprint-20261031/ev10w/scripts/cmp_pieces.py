"""Numeric comparison of two piece directories: per piece, vertex-set Hausdorff distance (mm) and hull volume ratio."""
import sys, glob, os, json, numpy as np, trimesh
from scipy.spatial import cKDTree
a, b = sys.argv[1:3]; out = {}
for n in ('blue_cup', 'beige_cup'):
    fa, fb = sorted(glob.glob(f'{a}/{n}/piece_*.obj')), sorted(glob.glob(f'{b}/{n}/piece_*.obj'))
    if len(fa) != len(fb):
        out[n] = dict(count=[len(fa), len(fb)]); continue
    hd, vr = [], []
    for x, y in zip(fa, fb):
        A = trimesh.load(x, process=False); B = trimesh.load(y, process=False)
        d = max(cKDTree(B.vertices).query(A.vertices)[0].max(), cKDTree(A.vertices).query(B.vertices)[0].max())
        hd.append(d * 1e3); vr.append(A.convex_hull.volume / B.convex_hull.volume)
    ja = json.load(open(f'{a}/{n}/inertia.json')); jb = json.load(open(f'{b}/{n}/inertia.json'))
    out[n] = dict(pieces=len(fa), max_vertex_hausdorff_mm=float(max(hd)), vol_ratio_minmax=[float(min(vr)), float(max(vr))],
                  com_diff_mm=float(np.abs(np.array(ja['com']) - jb['com']).max() * 1e3),
                  inertia_rel_diff=float(np.abs(np.array(ja['inertia']) - jb['inertia']).max() / np.abs(jb['inertia']).max()))
print(json.dumps(out, indent=1))
