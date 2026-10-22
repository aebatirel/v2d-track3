import sys, time, os, numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import vox
S = '/tmp/claude-0/-home-user-v2d-track3/8c892c5e-fd7c-57aa-abef-68d2af098e4f/scratchpad'
L = '/home/user/v2d-track3/meshes/'
names = ['white_pot','white_pot_lid','blue_cup','beige_cup','plastic_dish_rack','mini_sweeper','mini_dust_pan','water_pitcher','wooden_piece_1','wooden_piece_2']
def scanp(n):
    p = f'{S}/loc/t3/mesh/{n}/{n}_visual.glb'
    return p if os.path.exists(p) else f'{S}/loc/t3/mesh/{n}/{n}.glb'
for n in names:
    for tag, p in [('v2', L + 'library_v2/' + n + '.glb'), ('scan', scanp(n))] + ([('v4', L + 'library_v4/' + n + '.glb')] if n.startswith('wooden') else []) + ([('v3', L + 'library_v3/' + n + '.glb')] if n == 'mini_sweeper' else []):
        t = time.time(); V = vox.voxelize(p)
        print(f'{tag:4s} {n:18s} grid {V["occ"].shape} vox_vol {V["vol_cm3"]:7.1f} mesh_vol {V["mesh_vol_cm3"]:7.1f} area {V["area_cm2"]:7.0f} t {time.time()-t:5.1f}s', flush=True)
