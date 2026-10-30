# Independent spot checks of one number per tracker-fix diagnosis (public episodes; mocap read only in check 4).
import json, sys, numpy as np, trimesh, pyarrow.parquet as pq
from scipy.spatial.transform import Rotation as Rot
S = sys.argv[1]; REPO = sys.argv[2]
R = f'{S}/leak/p1/oracle_roots'; LIB = f'{REPO}/meshes/library_v3'
def ang(A, B): return np.degrees(Rot.from_matrix(A[:3, :3].T @ B[:3, :3]).magnitude())
def cen(n):
    m = trimesh.load(f'{LIB}/{n}.glb', force='mesh'); return np.asarray(m.vertices).mean(0)
def wc(T, c): return (T[..., :3, :3] @ c) + T[..., :3, 3]

# 1. ep0 P_s pot: jump at the guard re-acquisition (claim 5.19 cm, 176.1 deg at f64)
d = np.load(f'{R}/Ps_scan/ep0/poses_world_vo.npz'); P = d['white_pot']
print('ep0 Ps pot f63->f64: %.2f cm, %.1f deg' % (100*np.linalg.norm(P[64, :3, 3]-P[63, :3, 3]), ang(P[63], P[64])))
w = [ang(P[0], P[i]) for i in range(64)]; t = [100*np.linalg.norm(P[i, :3, 3]-P[0, :3, 3]) for i in range(64)]
print('  f0-63 wobble max: %.2f cm, %.1f deg (claim 3.2 cm, 20.8 deg)' % (max(t), max(w)))

# 2. ep11 P_o blue cup: lift while the beige cup is nested (claim peak ~5.3 cm, ~2.4 cm at f102-136, horiz <= 1.0 cm)
d = np.load(f'{R}/Po/ep11/poses_world_vo.npz'); B = wc(d['blue_cup'], cen('blue_cup'))
dd = 100*(B - B[0]); nrm = np.linalg.norm(dd, axis=1)
# up direction: our table normal is not stored here; use the dominant displacement direction at the peak
k = int(np.argmax(nrm)); u = dd[k]/nrm[k]
h = np.linalg.norm(dd - np.outer(dd@u, u), axis=1)
print('ep11 Po blue: peak |d| %.2f cm at f%d; mean |d| f102-136 %.2f cm; off-axis max %.2f cm' % (nrm[k], k, nrm[102:137].mean(), h.max()))

# 3. ep24 P_o board 2: centroid steps at VO keyframes 36/38/40/49 (claim 0.41/0.28/0.66/1.05 cm)
d = np.load(f'{R}/Po/ep24/poses_world_vo.npz'); C = wc(d['wooden_piece_2'], cen('wooden_piece_2'))
st = 100*np.linalg.norm(np.diff(C, axis=0), axis=1)
print('ep24 Po board2 steps at f36/38/40/49: ' + ' '.join('%.2f' % st[f-1] for f in (36, 38, 40, 49)),
      '; max other step f33-60: %.2f' % max(st[f-1] for f in range(33, 61) if f not in (36, 38, 40, 49)),
      '; |C(110)-C(0)| %.2f cm' % (100*np.linalg.norm(C[110]-C[0])))

# 4. ep31 P_o: sweeper frame-0 orientation error in the rack's frame (world-free; claim ~9 deg in world)
X = json.load(open(f'{REPO}/docs/research/work/leak-decomp-20261030/tierA/xstar_geom.json'))['objects']
d = np.load(f'{R}/Po/ep31/poses.npz')
tab = pq.read_table(f'{S}/map/scoring/t3/ep31.parquet', columns=['observation.objects']).column('observation.objects')[0].as_py()
def gt(n):
    q = np.array([o['pose'] for o in tab if o['name'] == n][0], float); M = np.eye(4)
    M[:3, :3] = Rot.from_quat(q[[4, 5, 6, 3]]).as_matrix(); M[:3, 3] = q[:3]; return M
def scanpose(T_lib, n): return T_lib @ np.linalg.inv(np.array(X[n]['X_scan_T_lib']))  # lib-frame pose = scan pose @ X
Ps = scanpose(d['cam_T_mini_sweeper'][0], 'mini_sweeper'); Pr = scanpose(d['cam_T_plastic_dish_rack'][0], 'plastic_dish_rack')
rel_p = np.linalg.inv(Pr) @ Ps; rel_g = np.linalg.inv(gt('plastic_dish_rack')) @ gt('mini_sweeper')
print('ep31 Po f0 sweeper-in-rack: rot err %.1f deg, pos err %.2f cm' % (ang(rel_p, rel_g), 100*np.linalg.norm(rel_p[:3, 3]-rel_g[:3, 3])))
