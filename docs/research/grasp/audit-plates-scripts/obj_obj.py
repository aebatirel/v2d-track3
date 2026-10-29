"""Object-object and hand-object proximity in a trace: min signed distance of the dust pan surface samples to the
sweeper hulls per frame, plus each hand's nearest link to the sweeper. Usage: obj_obj.py TRACE.npz F0 F1 [STEP]"""
import sys
import numpy as np, trimesh
sys.path.insert(0, sys.argv[0].rsplit('/', 1)[0])
from audit_lib import HullSDF, hand_points, load_trace, link_world, to_obj
tr = load_trace(sys.argv[1]); f0, f1 = int(sys.argv[2]), int(sys.argv[3]); st = int(sys.argv[4]) if len(sys.argv) > 4 else 1
sw = HullSDF('mini_sweeper'); dpm = trimesh.load('/home/user/v2d-track3/meshes/library_v3/mini_dust_pan.glb', force='mesh')
S = trimesh.sample.sample_surface_even(dpm, 3000, seed=0)[0]; hp = {s: hand_points(s, 60) for s in ('left', 'right')}
for f in range(f0, f1, st):
    Xw = link_world(tr['obj']['mini_dust_pan'][f], S); d = sw(to_obj(tr['obj']['mini_sweeper'][f], Xw)).min()
    row = f'{f:4d} pan-sweeper {1000 * d:7.1f} mm'
    for s in ('left', 'right'):
        best = min(((sw(to_obj(tr['obj']['mini_sweeper'][f], link_world(tr['links'][ln][f], P))).min(), ln) for ln, P in hp[s].items()))
        row += f' | {s} nearest to sweeper {1000 * best[0]:6.1f} mm ({best[1].split("_", 1)[1]})'
    print(row)
