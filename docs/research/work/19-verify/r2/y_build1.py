# Round-2 verifier (C4): realistic 1-world build with the REAL S120 mesh hulls (rack + pot, debris < 1e-12 m3 dropped),
# K one-capsule hand bodies, newton finalize + SolverMuJoCo (CPU MuJoCo compile). Peak RSS reported (macOS ru_maxrss bytes).
import sys, time, resource, dataclasses, numpy as np
sys.path.insert(0, '/Users/aebatirel/Documents/Code/v2d-research/work/19/b'); from common import load_hulls
from scipy.spatial import ConvexHull
import warp as wp; wp.config.quiet = True
import newton
W = '/Users/aebatirel/Documents/Code/v2d-research/work/19/'
sets = sys.argv[1].split(',')   # e.g. b/V4_120/plastic_dish_rack.npz,b/V4_120/white_pot.npz
N = int(sys.argv[2]); K = int(sys.argv[3]); solver = sys.argv[4] == '1'
def rss(): return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1e9
t = newton.ModelBuilder(); newton.solvers.SolverMuJoCo.register_custom_attributes(t)
I = wp.mat33(1e-3, 0, 0, 0, 1e-3, 0, 0, 0, 1e-3)
cfg = dataclasses.replace(t.default_shape_cfg, is_visible=False, has_shape_collision=True, density=0.0)
nh = []
for o, f in enumerate(sets):
    hv = load_hulls(W + f); keep = 0
    body = t.add_body(xform=wp.transform((0.6 * o, 0, 0.3), wp.quat_identity()), mass=0.3, inertia=I, lock_inertia=True); t.add_joint_free(body)
    for v in hv:
        h = ConvexHull(v)
        if h.volume < 1e-12: continue
        fc = h.simplices.copy(); c = v[h.vertices].mean(0)
        for k in range(len(fc)):
            a, bb, cc = v[fc[k]]
            if np.dot(np.cross(bb - a, cc - a), a - c) < 0: fc[k] = fc[k][[0, 2, 1]]
        t.add_shape_mesh(body, mesh=newton.Mesh(v.astype(np.float32), fc.reshape(-1).astype(np.int32), compute_inertia=False), cfg=cfg); keep += 1
    nh.append(keep)
for k in range(K):
    b = t.add_body(xform=wp.transform((0, 0.5, 0.03 * k), wp.quat_identity())); t.add_joint_free(b)
    t.add_shape_capsule(b, radius=0.008, half_height=0.02)
t.add_ground_plane()
r0 = rss(); t0 = time.time()
s = newton.ModelBuilder(); newton.solvers.SolverMuJoCo.register_custom_attributes(s); s.replicate(t, N)
m = s.finalize(device='cpu'); t1 = time.time(); r1 = rss()
msg = ''
if solver:
    try:
        sv = newton.solvers.SolverMuJoCo(m, use_mujoco_cpu=True, use_mujoco_contacts=True); msg = f'MuJoCo CPU compile OK ngeom {sv.mj_model.ngeom}'
    except Exception as e: msg = 'MuJoCo FAILED ' + str(e)[:150]
t2 = time.time(); r2 = rss()
print(f'hulls {nh} K {K} N {N}: filter pairs {len(s.shape_collision_filter_pairs)} contact pairs {m.shape_contact_pair_count} | '
      f'template RSS {r0:.2f} GB, after finalize {r1:.2f} GB ({t1-t0:.1f} s), after solver {r2:.2f} GB ({t2-t1:.1f} s) | {msg}', flush=True)
