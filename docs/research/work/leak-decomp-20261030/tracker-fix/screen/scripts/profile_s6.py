"""GT-free per-frame profile of a (near-)static container's track: horizontal travel h, height v (our frame-0 plane),
the other object's horizontal distance to it, nearest measured hand joint. Usage: python -I profile_s6.py EP OBJ [public]"""
import sys, json, numpy as np, trimesh
from scipy.spatial import cKDTree
sys.path.insert(0, '/tmp/claude-0/-home-user-v2d-track3/68c88876-77c0-55d9-bea4-03de8a3f6ee7/scratchpad/screen/scripts')
import eval_screen as E
ep, obj = int(sys.argv[1]), sys.argv[2]; public = len(sys.argv) > 3 and sys.argv[3] == 'public'
I = E.inputs(ep, public); det = np.load(I['det'], allow_pickle=True); names = [str(x) for x in det['names']]
P = np.load(I['poses']); Wd = E.world(P); pl = E.plane_of(det); nrm = np.asarray(pl[0], float)
cen = {n: Wd[n][:, :3, :3] @ np.asarray(E.mesh(f'{E.lib(ep, n, public)}/{n}.glb').vertices, float).mean(0) + Wd[n][:, :3, 3] for n in names}
dc = cen[obj] - cen[obj][0]; v = dc @ nrm; h = np.linalg.norm(dc - v[:, None] * nrm, axis=1)
hz = np.load(I['hands'], allow_pickle=True)
J = np.concatenate([hz['joints_left'], hz['joints_right']], 1).astype(float)
Jv = np.concatenate([np.repeat(hz['valid_left'][:, None], 21, 1), np.repeat(hz['valid_right'][:, None], 21, 1)], 1) & np.isfinite(J).all(-1)
pts = trimesh.sample.sample_surface(E.mesh(f'{E.lib(ep, obj, public)}/{obj}.glb'), 400, seed=0)[0]
N = len(v); step = int(sys.argv[4]) if len(sys.argv) > 4 else 5
other = [n for n in names if n != obj]
print(f'ep{ep} {obj}: frame  h_cm  v_cm  | other: horiz dist cm, height diff cm | hand cm')
for i in list(range(0, N, step)) + [N - 1]:
    X = Wd[obj][i, :3, :3] @ pts.T; X = X.T + Wd[obj][i, :3, 3]
    hd = cKDTree(X).query(J[i][Jv[i]])[0].min() * 100 if Jv[i].any() else np.inf
    s = ' '.join(f'{o}: {np.linalg.norm((cen[o][i]-cen[obj][i]) - ((cen[o][i]-cen[obj][i]) @ nrm) * nrm)*100:5.1f}, {((cen[o][i]-cen[obj][i]) @ nrm)*100:5.1f}' for o in other)
    print(f'  f{i:3d} {h[i]*100:5.2f} {v[i]*100:5.2f} | {s} | {hd:5.1f}')
