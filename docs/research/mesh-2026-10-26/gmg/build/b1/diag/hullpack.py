"""Dev diagnostic (B1): why does the beige_cup HULL lose watertightness in fit_budget? No GT."""
import sys, time, json
sys.path.insert(0, '/home/user/v2d-track3/docs/research/mesh-2026-10-26')
from gmg import guard, bundle as B
from gmg.producers import hull as P
import numpy as np, trimesh
ep, obj = int(sys.argv[1]), sys.argv[2]
guard.set_run(sys.argv[4])
b = B.from_obs_all(ep)
c = P.produce(dict(bundle=b, obj=obj, t0=0.005))[0]
m = c.mesh
print('dense', len(m.faces), m.is_watertight, m.euler_number, 'bodies', len(m.split(only_watertight=False)))
import fast_simplification
V0, F0 = np.asarray(m.vertices, np.float64), np.asarray(m.faces, np.int64)
for agg in (1, 3, 5, 7):
    for tgt in (4000, 3800, 3500, 3000):
        v, f = fast_simplification.simplify(V0, F0, target_count=tgt, agg=agg)
        s = trimesh.Trimesh(v, f, process=True)
        print('agg', agg, 'tgt', tgt, 'faces', len(s.faces), 'wt', s.is_watertight, 'area', round(s.area / m.area - 1, 4))
from autokit import program
mm, info = program.fit_budget(m, [], 4000)
print(json.dumps(info))
trimesh.Trimesh(V0, F0).export(sys.argv[3])
