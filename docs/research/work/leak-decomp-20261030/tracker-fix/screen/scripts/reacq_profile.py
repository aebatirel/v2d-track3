"""GT-free profile of an object's track around its guard re-acquisitions: centre travel from frame 0 (cm), height above
our frame-0 plane (cm), frame-to-frame step (cm, deg), nearest measured hand joint to the surface (cm), low 5 % height.
Usage: python -I reacq_profile.py EP OBJ F0 F1 [STEP]"""
import sys, numpy as np, trimesh
from scipy.spatial import cKDTree
sys.path.insert(0, '/tmp/claude-0/-home-user-v2d-track3/68c88876-77c0-55d9-bea4-03de8a3f6ee7/scratchpad/screen/scripts')
import eval_screen as E
ep, obj, a, b = int(sys.argv[1]), sys.argv[2], int(sys.argv[3]), int(sys.argv[4]); st = int(sys.argv[5]) if len(sys.argv) > 5 else 1
I = E.inputs(ep, False); det = np.load(I['det'], allow_pickle=True); pl = E.plane_of(det); nrm, c0 = np.asarray(pl[0], float), float(pl[1])
Wd = E.world(np.load(I['poses'])); T = Wd[obj]
m = E.mesh(f'{E.lib(ep, obj, False)}/{obj}.glb'); cm = np.asarray(m.vertices, float).mean(0); pts = trimesh.sample.sample_surface(m, 400, seed=0)[0]
hz = np.load(I['hands'], allow_pickle=True)
J = np.concatenate([hz['joints_left'], hz['joints_right']], 1).astype(float)
Jv = np.concatenate([np.repeat(hz['valid_left'][:, None], 21, 1), np.repeat(hz['valid_right'][:, None], 21, 1)], 1) & np.isfinite(J).all(-1)
c = T[:, :3, :3] @ cm + T[:, :3, 3]
for i in range(a, b + 1, st):
    X = (T[i, :3, :3] @ pts.T).T + T[i, :3, 3]
    hd = cKDTree(X).query(J[i][Jv[i]])[0].min() * 100 if Jv[i].any() else np.inf
    low = np.percentile(X @ nrm + c0, 5) * 100
    stp = np.linalg.norm(c[i] - c[i - 1]) * 100 if i else 0.0
    rd = E.rotdeg(T[i - 1, :3, :3], T[i, :3, :3]) if i else 0.0
    print(f'f{i:3d} travel {np.linalg.norm(c[i]-c[0])*100:5.1f} h {(c[i]@nrm+c0)*100:5.1f} low5 {low:5.1f} step {stp:5.1f} cm {rd:5.0f} deg hand {hd:5.1f}')
