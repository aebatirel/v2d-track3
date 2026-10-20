"""Verifier: Track 3 stored axes vs trimesh min-volume OBB axes (Track 3 axes are exact area PCA per v_geom)."""
import sys, numpy as np, trimesh
sys.path.insert(0, "/Users/aebatirel/Documents/Code/v2d-research/work/13-verify")
from v_geom import glb_load
M = "/Users/aebatirel/Documents/Code/v2d-research/data/track_3/public/mesh"
for n, f in [("water_pitcher", "water_pitcher.glb"), ("white_pot", "white_pot.glb"), ("plastic_dish_rack", "plastic_dish_rack.glb"), ("wooden_piece_1", "wooden_piece_1_visual.glb"), ("mini_dust_pan", "mini_dust_pan.glb")]:
    V, F = glb_load(f"{M}/{n}/{f}"); m = trimesh.Trimesh(V, F, process=True)
    to, ext = trimesh.bounds.oriented_bounds(m)
    A = np.abs(to[:3, :3]); print(n, "OBB axis angle to stored (deg)", np.degrees(np.arccos(np.clip(A.max(0), -1, 1))).round(2), "ext_mm", (1000 * np.array(ext)).round(1))
