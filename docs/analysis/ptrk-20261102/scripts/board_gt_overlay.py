"""DIAGNOSTIC (reads public mocap): overlay of the tracked boards (library mesh at the track pose, red / blue) and the
mocap board 2 (scan mesh, green) placed RELATIVE to the tracked board 1 (mocap 1->2 relative pose, so no world
alignment is needed; board 1 tracks to 0.9 cm / 3 deg on ep23). Usage:
python -I board_gt_overlay.py EP VIDEO CALIB POSES_NPZ LIB T3 KIT OUT FRAMES"""
import sys, os, numpy as np, cv2, trimesh, pyarrow.parquet as pq
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '..', '..', 'pipeline'))
from identity_fix import rectified_frames
from scipy.spatial.transform import Rotation as Rot
EP, VID, CAL, POS, LIB, T3D, KIT, OUT = int(sys.argv[1]), *sys.argv[2:9]; FR = [int(x) for x in sys.argv[9].split(',')]
sys.path.insert(0, KIT)
from v2dlb import track3_pose as T3
from v2dlb.mesh_budget import budget_mesh
from v2dlb.object_mesh import _surface_moments
N = ['wooden_piece_1', 'wooden_piece_2']
imgs, KR = rectified_frames(VID, CAL, FR); Z = np.load(POS)
tab = pq.read_table(f'{T3D}/ep{EP}.parquet', columns=['observation.objects']).to_pandas()
def gt(n, i):
    q = np.array([o for o in tab['observation.objects'].iloc[i] if o['name'] == n][0]['pose'], float)
    M = np.eye(4); M[:3, :3] = Rot.from_quat(np.r_[q[4:7], q[3]]).as_matrix(); M[:3, 3] = q[:3]; return M
def scanp(n):
    q = f'{T3D}/mesh/{n}/{n}.glb'; return q if os.path.exists(q) else f'{T3D}/mesh/{n}/{n}_visual.glb'
sc = {n: trimesh.load(scanp(n), force='mesh') for n in N}; lib = {n: trimesh.load(f'{LIB}/{n}.glb', force='mesh') for n in N}
c1, _ = _surface_moments(np.asarray(sc[N[0]].vertices, float), np.asarray(sc[N[0]].faces, np.int64))
ca, Rb = T3._register_object_body(budget_mesh(f'{LIB}/{N[0]}.glb', 4096, 4096), (np.asarray(sc[N[0]].vertices, float), np.asarray(sc[N[0]].faces, np.int64)), c1, 1_000_003 * EP)
G1 = np.eye(4); G1[:3, :3] = Rb.T; G1[:3, 3] = ca; Tc = np.eye(4); Tc[:3, 3] = -c1
def outline(im, mesh, X, col):
    v = np.asarray(mesh.vertices) @ X[:3, :3].T + X[:3, 3]; uv = v @ KR.T; uv = uv[:, :2] / uv[:, 2:3]
    s = np.zeros(im.shape[:2], np.uint8); cv2.fillPoly(s, [np.round(uv[f]).astype(np.int32) for f in np.asarray(mesh.faces)], 1)
    cs, _ = cv2.findContours(s, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE); cv2.drawContours(im, cs, -1, col, 3)
    # long-axis tip marker (+z end) to show orientation
    tip = X[:3, :3] @ np.array([0, 0, np.asarray(mesh.vertices)[:, 2].max()]) + X[:3, 3]; q = KR @ tip
    cv2.circle(im, (int(q[0] / q[2]), int(q[1] / q[2])), 8, col, -1); return uv
tiles = []
for f in FR:
    im = cv2.cvtColor(imgs[f].astype(np.uint8), cv2.COLOR_GRAY2BGR)
    X1, X2 = Z['cam_T_wooden_piece_1'][f], Z['cam_T_wooden_piece_2'][f]
    S1raw = X1 @ G1 @ Tc; Y2 = S1raw @ np.linalg.inv(gt(N[0], f)) @ gt(N[1], f)
    outline(im, lib[N[0]], X1, (255, 120, 0)); outline(im, lib[N[1]], X2, (0, 0, 255)); uv = outline(im, sc[N[1]], Y2, (0, 255, 0))
    cv2.putText(im, f'ep{EP} f{f}: blue=track b1, red=track b2, green=mocap b2 (rel. to b1); dot=+z end', (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (255, 255, 255), 2)
    tiles.append(cv2.resize(im, (800, 500)))
rows = [np.hstack(tiles[i:i + 2] + ([np.zeros_like(tiles[0])] if len(tiles[i:i + 2]) == 1 else [])) for i in range(0, len(tiles), 2)]
cv2.imwrite(OUT, np.vstack(rows)); print('wrote', OUT)
