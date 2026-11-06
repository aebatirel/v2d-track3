"""ORACLE DIAGNOSTIC ep0 overlays: P_s (scan templates, red), P_o (library_v3, green) and mocap (scan at G^-1 mocap, blue)
projected into the colour camera a (stereo frame t <-> camera-a frame t+1, as hands_mp.py)."""
import sys, json, os
import numpy as np, cv2, trimesh
S = '/tmp/claude-0/-home-user-v2d-track3/68c88876-77c0-55d9-bea4-03de8a3f6ee7/scratchpad'
sys.path.insert(0, '/home/user/v2d-track3/tools')
import xstar_fit as XF
XF.kit(S + '/map/scoring/kit/v2d_submission_kit'); T3D = S + '/map/scoring/t3'; LIB = '/home/user/v2d-track3/meshes/library_v3'
OUT = sys.argv[1]; FR = [int(x) for x in sys.argv[2].split(',')]
os.makedirs(OUT, exist_ok=True)
names, gt = XF.mocap(T3D, 0)
R = S + '/leak/p1/oracle_roots'
Ps = np.load(f'{R}/Ps_scan/ep0/poses_world_vo.npz'); Po = np.load(f'{R}/Po/ep0/poses_world_vo.npz')
W = np.load(f'{R}/Po/ep0/poses.npz')['world_T_cam']
Hn = np.load(f'{S}/refine/in/ep0/hands_refined.npz'); Ka, Da, Tra = Hn['Ka'], Hn['Da'], Hn['T_rect_a']; aoff = int(Hn['a_offset'])
G = np.load(f'{S}/leak/diag_ep0/out/perframe.npz')['G']; Gi = np.linalg.inv(G)
def pts(path, n=2500):
    m = trimesh.load(path, force='mesh'); return np.asarray(m.sample(n, return_index=False)) if hasattr(m, 'sample') else m.vertices
SCAN = {n: pts(XF.scan_path(T3D, n)) for n in names}; OURS = {n: pts(f'{LIB}/{n}.glb') for n in names}
cap = cv2.VideoCapture(f'{S}/hfds/track_3/public/videos/chunk-000/observation.images.ego_cam_a/episode_000000.mp4')
frames = {}
i = 0
need = {t + aoff for t in FR}
while len(frames) < len(need):
    ok, f = cap.read()
    if not ok: break
    if i in need: frames[i] = f
    i += 1
def proj(img, Pw, t, col, r=2):
    A = np.linalg.inv(W[t] @ Tra); Xa = Pw @ A[:3, :3].T + A[:3, 3]; ok = Xa[:, 2] > 0.05
    uv, _ = cv2.projectPoints(Xa[ok].reshape(-1, 1, 3), np.zeros(3), np.zeros(3), Ka, Da); uv = uv.reshape(-1, 2)
    for u, v in uv.astype(int):
        if 0 <= u < img.shape[1] and 0 <= v < img.shape[0]: cv2.circle(img, (u, v), r, col, -1)
tiles = []
for t in FR:
    img = frames[t + aoff].copy()
    for n in names:
        M = Gi @ gt[n][t]; proj(img, SCAN[n] @ M[:3, :3].T + M[:3, 3], t, (255, 80, 0))          # mocap: blue (BGR)
        M = Po[n][t]; proj(img, OURS[n] @ M[:3, :3].T + M[:3, 3], t, (0, 200, 0))                # P_o: green
        M = Ps[n][t]; proj(img, SCAN[n] @ M[:3, :3].T + M[:3, 3], t, (0, 0, 255))                # P_s: red
    cv2.putText(img, f'ep0 f{t}  blue=mocap  green=P_o (ours)  red=P_s (scan)', (30, 60), cv2.FONT_HERSHEY_SIMPLEX, 1.6, (0, 255, 255), 4)
    # crop around the table region
    h, w = img.shape[:2]; crop = img[int(0.30 * h):h, int(0.15 * w):int(0.85 * w)]
    cv2.putText(crop, f'f{t}', (20, 70), cv2.FONT_HERSHEY_SIMPLEX, 2.2, (0, 255, 255), 5)
    cv2.imwrite(f'{OUT}/ep0_f{t:03d}.png', cv2.resize(img, (w // 2, h // 2)))
    tiles.append(cv2.resize(crop, (crop.shape[1] // 2, crop.shape[0] // 2)))
row = np.concatenate(tiles[:3], 1); row2 = np.concatenate(tiles[3:6], 1) if len(tiles) >= 6 else None
mont = row if row2 is None else np.concatenate([row, row2], 0)
cv2.imwrite(f'{OUT}/ep0_montage.png', mont)
print('ok', sorted(os.listdir(OUT)))
