"""GT-free dev diagnostic (B7): corner_stats of the VOTE-cluster spheres (centre, median vote radius) of an archived
b7 run, versus the robust-fit spheres. Reads obs_all through the guard (dev role). Usage: GMG_MODE=dev python
vote_sphericity.py EP_JSON OBJ"""
import json, os, sys
sys.path.insert(0, '/home/user/v2d-track3/docs/research/mesh-2026-10-26')
from gmg import guard, markers as MK
import numpy as np
from scipy.spatial import cKDTree
ej, obj = sys.argv[1], sys.argv[2]   # dev diagnostic only (tier DEV); never part of a gmg run
d = json.load(open(ej)); ep = d['ep']; sig = d['sigma_mm'][obj] * 1e-3
z = guard.load_npz(os.path.join(guard.CFG['data'], 'obs_all', f'ep{ep}_{obj}.npz'), 'obs_all', keys=['pts', 'cam', 'frame'])
obs = dict(pts=z['pts'], cam=z['cam'], frame=z['frame'])
K = dict(MK.FROZEN)
P, C, F, Pv, V, Fv = MK._owned_points(obs, K, np.random.default_rng(0))
tree = cKDTree(Pv)
rows = []
for ci in d['markers']['per_object'][obj]['pass1']['candidates_info']:
    c = np.array(ci['c_vote']); r = ci['r_vote_mm'] * 1e-3
    nd, out = MK.corner_stats(Pv, V, tree, c, r, 3 * sig, np.random.default_rng(0))
    rows.append((ci['votes'], round(r * 1e3, 2), nd, out, ci.get('r_mm'), ci.get('normal_dev_deg'), ci.get('rejected')))
rows.sort(key=lambda x: (x[2] if x[2] is not None else 99))
for r in rows[:25]:
    print(r)
nd = np.array([r[2] for r in rows if r[2] is not None])
print('vote spheres:', len(rows), 'normal_dev quantiles 0/10/50/90', np.percentile(nd, [0, 10, 50, 90]).round(1),
      'n < 20 deg', int((nd < 20).sum()), 'n < 25 deg', int((nd < 25).sum()))
