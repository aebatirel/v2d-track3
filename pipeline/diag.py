"""Diagnostics (evaluation only): per-frame pose error of tracked objects vs mocap after the scorer's
slot-0 frame-0 alignment, plus an overlay montage (pred = green, GT = red) on rectified-left frames."""
import sys, json, numpy as np, cv2, trimesh, pyarrow.parquet as pq
from scipy.spatial.transform import Rotation as Rot
EP = int(sys.argv[1]); ROOT = sys.argv[2] if len(sys.argv) > 2 else '/content/perc2'; STEP = int(sys.argv[3]) if len(sys.argv) > 3 else 20
D = '/content/t3'; O = f'{ROOT}/ep{EP}'
P = np.load(f'{O}/poses.npz'); W = P['world_T_cam']
tab = pq.read_table(f'{D}/ep{EP}.parquet').to_pandas(); names = [o['name'] for o in tab['observation.objects'].iloc[0]]
N = len(W)
def T_of(p):
    M = np.eye(4); M[:3, :3] = Rot.from_quat([p[4], p[5], p[6], p[3]]).as_matrix(); M[:3, 3] = p[:3]; return M
gt = {n: np.stack([T_of(np.array([o for o in row if o['name'] == n][0]['pose'], float)) for row in tab['observation.objects'].iloc[:N]]) for n in names}
pred = {n: np.einsum('tij,tjk->tik', W, P[f'cam_T_{n}']) for n in names}
Q = pred[names[0]][0] @ np.linalg.inv(gt[names[0]][0])           # GT -> our world (slot-0 frame-0 alignment)
gtw = {n: np.einsum('ij,tjk->tik', Q, gt[n]) for n in names}
print('frame | ' + ' | '.join(f'{n[:12]:12s} err_cm rot_deg gtmove_cm' for n in names))
for i in range(0, N, STEP):
    s = []
    for n in names:
        e = np.linalg.norm(pred[n][i][:3, 3] - gtw[n][i][:3, 3]) * 100
        r = np.degrees(np.linalg.norm(Rot.from_matrix(pred[n][i][:3, :3] @ gtw[n][i][:3, :3].T).as_rotvec()))
        mv = np.linalg.norm(gtw[n][i][:3, 3] - gtw[n][0][:3, 3]) * 100
        s.append(f'{n[:12]:12s} {e:6.1f} {r:7.1f} {mv:9.1f}')
    print(f'{i:5d} | ' + ' | '.join(s))
C = json.load(open(f'{D}/calib.json')); cam = C['cameras']; sp = [p for p in C['stereo_pairs'] if p['camera'] == 'ego'][0]
K_ = lambda n: np.array(cam[n]['intrinsic_matrix'], float); D_ = lambda n: np.array(cam[n]['distortion_coefficients'], float)
E = np.array(sp['left_to_right'], float)
R1, R2, P1, P2, _, _, _ = cv2.stereoRectify(K_('ego_cam_c'), D_('ego_cam_c'), K_('ego_cam_b'), D_('ego_cam_b'), (1280, 800), E[:3, :3], E[:3, 3:], alpha=0, newImageSize=(1600, 1000), flags=cv2.CALIB_ZERO_DISPARITY)
MC = cv2.initUndistortRectifyMap(K_('ego_cam_c'), D_('ego_cam_c'), R1, P1, (1600, 1000), cv2.CV_32FC1); KR = P1[:3, :3]
def mp(n):
    import os
    p = f'{D}/mesh/{n}/{n}.glb'; p = p if os.path.exists(p) else f'{D}/mesh/{n}/{n}_visual.glb'
    return np.asarray(trimesh.sample.sample_surface(trimesh.load(p, force='mesh'), 600, seed=0)[0])
V = {n: mp(n) for n in names}
cap = cv2.VideoCapture(f'{D}/v/ep{EP}_c.mp4'); fr = []
while True:
    ok, f = cap.read()
    if not ok: break
    fr.append(f)
idx = np.linspace(0, N - 1, 8).astype(int); tiles = []
for i in idx:
    img = cv2.cvtColor(cv2.remap(cv2.cvtColor(fr[i], cv2.COLOR_BGR2GRAY), MC[0], MC[1], cv2.INTER_LINEAR), cv2.COLOR_GRAY2BGR)
    Ci = np.linalg.inv(W[i])
    for n in names:
        for M, col in ((P[f'cam_T_{n}'][i], (0, 255, 0)), (Ci @ gtw[n][i], (0, 0, 255))):
            X = V[n] @ M[:3, :3].T + M[:3, 3]; X = X[X[:, 2] > 0.05]; uv = (X / X[:, 2:]) @ KR.T
            for u, v in uv[:, :2].astype(int):
                if 0 <= u < 1600 and 0 <= v < 1000: cv2.circle(img, (u, v), 2, col, -1)
    cv2.putText(img, f'f{i}', (20, 60), 0, 2, (255, 255, 0), 3); tiles.append(cv2.resize(img, (640, 400)))
cv2.imwrite(f'{O}/diag.jpg', np.vstack([np.hstack(tiles[:4]), np.hstack(tiles[4:])]))
print('wrote', f'{O}/diag.jpg')
