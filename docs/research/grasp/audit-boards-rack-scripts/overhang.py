"""Overhang of each board beyond the simulated table disc (support USDA: centre, radius) in OUR reference (no GT)."""
import sys, numpy as np, trimesh
from scipy.spatial.transform import Rotation as R
sys.path.insert(0, __file__.rsplit('/', 1)[0]); from refload import load_ref
d = load_ref(sys.argv[1]); lib = sys.argv[2]; cx, cy, rad = map(float, sys.argv[3].split(',')); fr = [int(x) for x in sys.argv[4].split(',')]
for j, o in enumerate(d['names']):
    m = trimesh.load(f'{lib}/{o}.glb', force='mesh'); pts, _ = trimesh.sample.sample_surface(m, 3000, seed=1)
    s = []
    for t in fr:
        w = R.from_quat(d['OQ'][t, j]).apply(pts) + d['OP'][t, j]; r = np.hypot(w[:, 0] - cx, w[:, 1] - cy)
        com = d['OP'][t, j]; rc = np.hypot(com[0] - cx, com[1] - cy)
        s.append(f'f{t}: max r {r.max()*100:.1f} cm, overhang {max(0, r.max()-rad)*100:.1f} cm, area beyond {np.mean(r > rad)*100:.0f}%, centre r {rc*100:.1f}')
    print(o, ' | '.join(s))
