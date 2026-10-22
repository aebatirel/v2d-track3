"""Synthetic testbed only: our reconstructed board meshes vs the exact box model they were rendered from (9 mm thick,
13.9 x 22.7 cm, slot of width W from y = 0 to the +y edge at z = c). 1 mm samples, winding sign. fcvenv.
Usage: synth_eval.py W_MM OBJ MESH [MESH...]"""
import json, sys
import numpy as np, trimesh
sys.path.insert(0, '/tmp/claude-0/-home-user-v2d-track3/8c892c5e-fd7c-57aa-abef-68d2af098e4f/scratchpad/interact')
import vox2
W = float(sys.argv[1]) / 1000; obj = sys.argv[2]
T, H, L = 0.009, 0.139, 0.227; c = {'wooden_piece_1': 0.001, 'wooden_piece_2': 0.0}[obj]
g = [np.arange(-0.02, 0.02, 1e-3) + 5e-4, np.arange(-H / 2 - 0.01, H / 2 + 0.01, 1e-3) + 5e-4, np.arange(-L / 2 - 0.01, L / 2 + 0.01, 1e-3) + 5e-4]
G = np.stack(np.meshgrid(*g, indexing='ij'), -1).reshape(-1, 3)
inb = (np.abs(G[:, 0]) < T / 2) & (np.abs(G[:, 1]) < H / 2) & (np.abs(G[:, 2]) < L / 2)
slot = inb & (G[:, 1] > 0) & (np.abs(G[:, 2] - c) < W / 2)
slot_core = slot & (G[:, 1] > 0.006) & (G[:, 1] < H / 2 - 0.006)
mat = inb & ~slot
for mp in sys.argv[3:]:
    m = trimesh.load(mp, force='mesh'); m.merge_vertices()
    o = vox2.SD(m, 'winding')(G) < 0
    v = 1e-3 ** 3 * 1e6
    # thickness at mid-board columns away from slot and edges: inside extent along x
    col = (np.abs(G[:, 1] + 0.03) < 0.0005) & (np.abs(G[:, 2] - 0.05) < 0.0005)
    r = dict(mesh=mp.split('/')[-1], slot_filled_frac=round(float(o[slot].mean()), 3), slot_core_filled_frac=round(float(o[slot_core].mean()), 3),
             slot_vol_cm3=round(float(slot.sum() * v), 2), missing_material_cm3=round(float((mat & ~o).sum() * v), 2),
             excess_outside_board_cm3=round(float((o & ~inb).sum() * v), 2), solid_cm3=round(float(o.sum() * v), 2),
             thickness_mm=int(o[col].sum()))
    print(json.dumps(r))
