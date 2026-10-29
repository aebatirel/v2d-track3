"""Share of OUR mesh surface within 3 / 5 mm of the fitted lathe BODY (appendages excluded). GT-free."""
import json, numpy as np, trimesh
from scipy.spatial import cKDTree
L = '/home/user/v2d-track3/meshes/'
items = [('blue_cup', L + 'library_v3/blue_cup.glb', 'out/lathe2/blue_cup_body.glb'),
         ('beige_cup_v3x', L + 'library_v3x/beige_cup.glb', 'out/lathe2/beige_cup_v3x_body.glb'),
         ('white_pot', L + 'library_v3/white_pot.glb', 'out/lathe2/white_pot_body.glb'),
         ('mini_dust_pan', L + 'library_v3/mini_dust_pan.glb', 'out/lathe2_all/mini_dust_pan_body.glb'),
         ('wooden_spoon', L + 'library_v3/wooden_spoon.glb', 'out/lathe2_all/wooden_spoon_body.glb')]
res = {}
for n, ours, body in items:
    A = trimesh.load(ours, force='mesh').sample(30000); B = trimesh.load(body, force='mesh').sample(60000)
    d = cKDTree(B).query(A)[0]
    res[n] = dict(explained_3mm=round(float((d < 0.003).mean()), 3), explained_5mm=round(float((d < 0.005).mean()), 3))
    print(n, res[n], json.load(open(body.replace('_body.glb', '.json'))).get('body_h_cm'))
json.dump(res, open('out/explained.json', 'w'), indent=1)
