"""Geometric self-similarity of each scan under rotations about its rest 'up' body axis (spin) and
180-deg flips about the other axes: symmetric Chamfer (mean, mm) between the mesh and its rotated copy."""
from c11 import *
from scipy.spatial import cKDTree
import json
res = {}
for nm in ["beige_cup", "blue_cup", "white_pot_lid", "white_pot", "plastic_dish_rack", "water_pitcher",
           "mini_dust_pan", "mini_sweeper", "wooden_piece_1", "wooden_piece_2"]:
    P = surface_points(nm, 6000, 1); t = cKDTree(P)
    up = np.array(UP[nm], float)
    row = {}
    for ang in [5, 10, 20, 45, 90, 180]:
        Q = Rot.from_rotvec(np.radians(ang) * up).apply(P)
        d = 0.5 * (t.query(Q)[0].mean() + cKDTree(Q).query(P)[0].mean()); row[f"spin{ang}"] = d * 1000
    for ax in range(3):
        e = np.zeros(3); e[ax] = 1
        if abs(e @ up) > 0.9: continue
        Q = Rot.from_rotvec(np.pi * e).apply(P)
        row[f"flip_{'xyz'[ax]}"] = 0.5 * (t.query(Q)[0].mean() + cKDTree(Q).query(P)[0].mean()) * 1000
    # best spin (min chamfer over 10..350)
    best = min(((0.5 * (t.query(Rot.from_rotvec(np.radians(a) * up).apply(P))[0].mean() + cKDTree(Rot.from_rotvec(np.radians(a) * up).apply(P)).query(P)[0].mean()) * 1000, a) for a in range(10, 351, 5)))
    row["best_nonzero_spin"] = best
    res[nm] = row
    print(nm.ljust(18), " ".join(f"{k}={v:.1f}" if not isinstance(v, tuple) else f"{k}={v[0]:.1f}@{v[1]}" for k, v in row.items()))
json.dump(res, open('s5_symmetry.json', 'w'), indent=1)
