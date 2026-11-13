"""GT-free exploration of public ep11 tracks (no mocap, no scans): per frame, in our frame-0 table frame (S6 plane),
the horizontal distance and height offset between the cups' vertex centroids, inner-bottom vs outer-top heights, the
nearest measured hand. Used to design the nest detector before any scoring."""
import sys, json
import numpy as np
sys.path.insert(0, '/home/user/v2d-track3/pipeline')
import refine
S = '/tmp/claude-0/-home-user-v2d-track3/68c88876-77c0-55d9-bea4-03de8a3f6ee7/scratchpad'
arm = sys.argv[1]; d = {'refineP': f'{S}/refine/in/ep11', 'Po': f'{S}/leak/t1/in_Po/ep11'}.get(arm, arm)
P = np.load(refine.checked(f'{d}/poses.npz')); W = P['world_T_cam'].astype(float)
names = [k[6:] for k in P.files if k.startswith('cam_T_')]
H = np.load(refine.checked(f'{d}/hands_refined.npz'))
dep = np.load(refine.checked(f'{d}/depth0.npy'))
n, dd, src = refine.s6_plane(dep, np.asarray(H['KR'], float), W[0], None, None, {})
n = n / np.linalg.norm(n)
objs = [refine.Obj(x, f'/home/user/v2d-track3/meshes/library_v3/{x}.glb') for x in names]
O = [np.einsum('tij,tjk->tik', W, P[f'cam_T_{x}'].astype(float)) for x in names]
T = len(W)
J = {s: H[f'joints_{s}'].astype(float) for s in ('left', 'right')}; M = {s: H[f'measured_{s}'].astype(bool) for s in J}
hd = [refine.hand_distances(O[j], o.S, J, M) for j, o in enumerate(objs)]
c = [O[j][:, :3, :3] @ o.V.mean(0) + O[j][:, :3, 3] for j, o in enumerate(objs)]
lo = [np.array([(o.world(O[j][t]) @ n).min() + dd for t in range(T)]) for j, o in enumerate(objs)]
hi = [np.array([(o.world(O[j][t]) @ n).max() + dd for t in range(T)]) for j, o in enumerate(objs)]
print(arm, names, 'plane', src)
for t in range(0, T, 3):
    e = c[1][t] - c[0][t]; z = e @ n; rho = np.linalg.norm(e - z * n)
    print(f'f{t:3d} rho {rho*100:5.1f} dz(beige-blue) {z*100:6.1f} | blue c_h {(c[0][t]-c[0][0])@n*100:+5.2f} hor {np.linalg.norm((c[0][t]-c[0][0]) - ((c[0][t]-c[0][0])@n)*n)*100:4.2f} lo {lo[0][t]*100:5.2f} hi {hi[0][t]*100:5.2f} | beige lo {lo[1][t]*100:5.2f} hi {hi[1][t]*100:5.2f} | hand blue {hd[0][t]:5.1f} beige {hd[1][t]:5.1f}')
