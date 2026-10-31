"""GT-free profile of a single-object eval around its VO keyframe burst: per frame, the spoon's world centre step (cm),
rotation step (deg), height above our frame-0 plane (cm), nearest measured hand joint to its surface (cm), the camera's
own step (cm, world_T_cam translation) and whether the frame is a VO keyframe. A static, untouched object that steps
exactly at keyframe switches would show a camera jump (ep24 signature); a moving or held one cannot separate the two.
Usage: python -I burst_profile.py EP F0 F1"""
import sys, json, numpy as np, trimesh
from scipy.spatial import cKDTree
sys.path.insert(0, '/tmp/claude-0/-home-user-v2d-track3/68c88876-77c0-55d9-bea4-03de8a3f6ee7/scratchpad/screen/scripts')
import eval_screen as E
ep, a, b = int(sys.argv[1]), int(sys.argv[2]), int(sys.argv[3])
I = E.inputs(ep, False); det = np.load(I['det'], allow_pickle=True); n = str(det['names'][0]); pl = E.plane_of(det)
nrm, c0 = np.asarray(pl[0], float), float(pl[1])
P = np.load(I['poses']); W = P['world_T_cam'].astype(float); T = E.world(P)[n]
kf = set(json.load(open(I['vo']))['keyframes'])
m = E.mesh(f'{E.lib(ep, n, False)}/{n}.glb'); cm = np.asarray(m.vertices, float).mean(0); pts = trimesh.sample.sample_surface(m, 400, seed=0)[0]
hz = np.load(I['hands'], allow_pickle=True)
J = np.concatenate([hz['joints_left'], hz['joints_right']], 1).astype(float)
Jv = np.concatenate([np.repeat(hz['valid_left'][:, None], 21, 1), np.repeat(hz['valid_right'][:, None], 21, 1)], 1) & np.isfinite(J).all(-1)
c = T[:, :3, :3] @ cm + T[:, :3, 3]
print(f'ep{ep} {n} frames {len(T)}; keyframes {sorted(kf)}')
for i in range(max(a, 1), min(b, len(T) - 1) + 1):
    X = (T[i, :3, :3] @ pts.T).T + T[i, :3, 3]
    hd = cKDTree(X).query(J[i][Jv[i]])[0].min() * 100 if Jv[i].any() else np.inf
    print(f'f{i:3d}{" KF" if i in kf else "   "} step {np.linalg.norm(c[i]-c[i-1])*100:5.2f} cm {E.rotdeg(T[i-1,:3,:3], T[i,:3,:3]):5.1f} deg'
          f' | h {(c[i] @ nrm + c0)*100:5.1f} cm | hand {hd:5.1f} | cam step {np.linalg.norm(W[i,:3,3]-W[i-1,:3,3])*100:5.2f} cm')
