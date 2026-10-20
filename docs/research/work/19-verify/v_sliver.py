# Verifier for C6. (a) min hull volumes per set; (b) evaluator-like newton->MuJoCo export: body with explicit
# mass/inertia, hulls added with density 0 (as FlashCHORD objects.py does), float32 verts, one normal hull + test hull;
# (c) threshold bracket with a scaled tetrahedron.
import sys, glob, dataclasses, numpy as np
sys.path.insert(0, '/Users/aebatirel/Documents/Code/v2d-research/work/19/b'); from common import load_hulls
from scipy.spatial import ConvexHull
import warp as wp; wp.config.quiet = True
import newton
W = '/Users/aebatirel/Documents/Code/v2d-research/work/'
def vols(f):
    out = []
    for v in load_hulls(f):
        try: out.append(ConvexHull(v).volume)
        except Exception: out.append(0.0)
    return np.array(out)
mode = sys.argv[1]
if mode == 'vol':
    for pat in sys.argv[2:]:
        for f in sorted(glob.glob(pat)):
            v = vols(f); k = int(np.argmin(v))
            print(f'{f.replace(W,""):55s} n {len(v):5d} min {v[k]:.2e} (idx {k}) n<1e-15 {(v<1e-15).sum()} n<1e-12 {(v<1e-12).sum()}')
    sys.exit()
def try_build(hull_list, cpu=True):
    b = newton.ModelBuilder(); newton.solvers.SolverMuJoCo.register_custom_attributes(b)
    I = wp.mat33(1e-3, 0, 0, 0, 1e-3, 0, 0, 0, 1e-3)
    body = b.add_body(mass=0.3, inertia=I, lock_inertia=True); b.add_joint_free(body)
    cfg = dataclasses.replace(b.default_shape_cfg, is_visible=False, has_shape_collision=True, density=0.0)
    for v in hull_list:
        h = ConvexHull(v)
        f = h.simplices.copy()
        # orient faces outward like CoACD output
        c = v[h.vertices].mean(0)
        for t in range(len(f)):
            a, bb, cc = v[f[t]]
            if np.dot(np.cross(bb - a, cc - a), a - c) < 0: f[t] = f[t][[0, 2, 1]]
        b.add_shape_mesh(body, mesh=newton.Mesh(v.astype(np.float32), f.reshape(-1).astype(np.int32), compute_inertia=False), cfg=cfg)
    b.add_ground_plane()
    m = b.finalize(device='cpu')
    try:
        newton.solvers.SolverMuJoCo(m, use_mujoco_cpu=cpu, use_mujoco_contacts=True)
        return 'OK'
    except Exception as e:
        return 'FAILED ' + type(e).__name__ + ': ' + str(e).replace('\n', ' ')[:160]
if mode == 'hull':
    f, idx = sys.argv[2], int(sys.argv[3])
    hv = load_hulls(f); v = vols(f); big = int(np.argmax(v))
    print(f'test hull {idx}: vol {ConvexHull(hv[idx]).volume:.2e} m3, extent um {np.ptp(hv[idx],0)*1e6}; float32 vol {ConvexHull(hv[idx].astype(np.float32).astype(np.float64)).volume:.2e}')
    print('normal hull only        :', try_build([hv[big]]))
    print('normal + test hull (CPU):', try_build([hv[big], hv[idx]]))
if mode == 'bracket':
    tet = np.array([[0, 0, 0], [1, 0, 0], [0, 1, 0], [0, 0, 1.]]) ; base = 1/6
    for V in [3e-16, 8e-16, 9.5e-16, 1.05e-15, 1.3e-15, 3e-15, 1e-13]:
        s = (V / base) ** (1/3); v = tet * s + np.array([0.1, 0.05, 0.2])
        print(f'tet vol {V:.2e}: float32 vol {ConvexHull(v.astype(np.float32).astype(np.float64)).volume:.2e} ->', try_build([v]))
