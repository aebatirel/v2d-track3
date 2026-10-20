# Round-2 verifier (C2): do all 10 public collision meshes, loaded as newton does (trimesh 4.12.2 load force="mesh",
# default processing; float32 as newton.Mesh stores them), fail CoACD's index-based closedness test (every directed
# edge must have exactly one opposite and no repeat)? Pure-numpy re-implementation of the first two IsManifold
# criteria (process.cpp: repeated directed edge = "wrong orientation", missing opposite = "unclosed").
import numpy as np, trimesh, glob, os
D = '/Users/aebatirel/Documents/Code/v2d-research/data/track_3/public/mesh/'
for f in ['beige_cup/beige_cup.glb', 'blue_cup/blue_cup.glb', 'mini_dust_pan/mini_dust_pan.glb', 'mini_sweeper/mini_sweeper_collision.glb',
          'plastic_dish_rack/plastic_dish_rack.glb', 'water_pitcher/water_pitcher.glb', 'white_pot_lid/white_pot_lid.glb',
          'white_pot/white_pot.glb', 'wooden_piece_1/wooden_piece_1_collision.glb', 'wooden_piece_2/wooden_piece_2_collision.glb']:
    m = trimesh.load(D + f, force='mesh'); F = np.asarray(m.faces, np.int64)
    e = np.vstack([F[:, [0, 1]], F[:, [1, 2]], F[:, [2, 0]]]); n = int(F.max()) + 1
    key = e[:, 0] * n + e[:, 1]; rev = e[:, 1] * n + e[:, 0]
    u, c = np.unique(key, return_counts=True); rep = int((c > 1).sum())
    unpaired = int((~np.isin(rev, key)).sum())
    w = m.copy(); w.merge_vertices(); 
    print(f'{f:45s} V {len(m.vertices):7d} F {len(F):7d} repeated directed edges {rep:6d} unpaired edges {unpaired:7d} '
          f'-> {"FAIL" if rep or unpaired else "pass (needs self-intersection test)"} | welded V {len(w.vertices)} watertight {w.is_watertight}', flush=True)
