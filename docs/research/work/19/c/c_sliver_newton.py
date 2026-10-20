# Does a CoACD sliver hull (from the split sets) break newton's SolverMuJoCo export? (CPU MuJoCo path)
import sys, numpy as np
pass
sys.path.insert(0,'/Users/aebatirel/Documents/Code/v2d-research/work/19/b'); from common import load_hulls
import warp as wp; wp.config.quiet=True
import newton
from scipy.spatial import ConvexHull
src, idx = sys.argv[1], [int(x) for x in sys.argv[2].split(',')]
hv = load_hulls(src)
b = newton.ModelBuilder(); newton.solvers.SolverMuJoCo.register_custom_attributes(b)
body = b.add_body(); b.add_joint_free(body)
for i in idx:
    v = hv[i]; h = ConvexHull(v); print(f'hull {i}: {len(v)} v, volume {h.volume:.2e} m3, extent mm {np.ptp(v,0)*1e3}')
    b.add_shape_mesh(body, mesh=newton.Mesh(v.astype(np.float32), h.simplices.reshape(-1).astype(np.int32), compute_inertia=False))
b.add_ground_plane()
m = b.finalize(device='cpu')
try:
    s = newton.solvers.SolverMuJoCo(m, use_mujoco_cpu=True, use_mujoco_contacts=True)
    print('SolverMuJoCo OK')
except Exception as e:
    print('SolverMuJoCo FAILED:', type(e).__name__, str(e)[:300])
