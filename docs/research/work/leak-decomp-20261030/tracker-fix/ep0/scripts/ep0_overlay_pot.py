"""ORACLE DIAGNOSTIC ep0: pot only, handle points highlighted. mocap pot (blue body, cyan handle), P_s pot (red body,
yellow handle), P_o pot (green). Frames given on the command line; one crop per frame, side by side."""
import sys, os
import numpy as np, cv2, trimesh
S = '/tmp/claude-0/-home-user-v2d-track3/68c88876-77c0-55d9-bea4-03de8a3f6ee7/scratchpad'
sys.path.insert(0, '/home/user/v2d-track3/tools')
import xstar_fit as XF
XF.kit(S + '/map/scoring/kit/v2d_submission_kit'); T3D = S + '/map/scoring/t3'; LIB = '/home/user/v2d-track3/meshes/library_v3'
OUT = sys.argv[1]; FR = [int(x) for x in sys.argv[2].split(',')]
names, gt = XF.mocap(T3D, 0); n = 'white_pot'
R = S + '/leak/p1/oracle_roots'
Ps = np.load(f'{R}/Ps_scan/ep0/poses_world_vo.npz')[n]; Po = np.load(f'{R}/Po/ep0/poses_world_vo.npz')[n]
W = np.load(f'{R}/Po/ep0/poses.npz')['world_T_cam']
Hn = np.load(f'{S}/refine/in/ep0/hands_refined.npz'); Ka, Da, Tra = Hn['Ka'], Hn['Da'], Hn['T_rect_a']; aoff = int(Hn['a_offset'])
Gi = np.linalg.inv(np.load(f'{S}/leak/diag_ep0/out/perframe.npz')['G'])
m = trimesh.load(XF.scan_path(T3D, n), force='mesh'); P = np.asarray(m.sample(4000)); c = P.mean(0)
w, U = np.linalg.eigh(np.cov((P - c).T)); long = U[:, 2]; s = (P - c) @ long
hand = np.abs(s) > 0.12; hand &= np.sign(s) == np.sign(np.median(s[np.abs(s) > 0.12]))
mo = trimesh.load(f'{LIB}/{n}.glb', force='mesh'); Q = np.asarray(mo.sample(3000))
cap = cv2.VideoCapture(f'{S}/hfds/track_3/public/videos/chunk-000/observation.images.ego_cam_a/episode_000000.mp4')
frames = {}; i = 0; need = {t + aoff for t in FR}
while len(frames) < len(need):
    ok, f = cap.read()
    if not ok: break
    if i in need: frames[i] = f
    i += 1
def proj(img, Pw, t, col, r):
    A = np.linalg.inv(W[t] @ Tra); Xa = Pw @ A[:3, :3].T + A[:3, 3]
    uv, _ = cv2.projectPoints(Xa.reshape(-1, 1, 3), np.zeros(3), np.zeros(3), Ka, Da)
    for u, v in uv.reshape(-1, 2).astype(int):
        if 0 <= u < img.shape[1] and 0 <= v < img.shape[0]: cv2.circle(img, (u, v), r, col, -1)
tiles = []
for t in FR:
    img = frames[t + aoff].copy()
    M = Gi @ gt[n][t]; X = P @ M[:3, :3].T + M[:3, 3]; proj(img, X[~hand][::3], t, (255, 60, 0), 3); proj(img, X[hand], t, (255, 255, 0), 5)
    M = Ps[t]; X = P @ M[:3, :3].T + M[:3, 3]; proj(img, X[~hand][::3], t, (0, 0, 255), 3); proj(img, X[hand], t, (0, 220, 255), 5)
    h, wd = img.shape[:2]; crop = img[int(0.05 * h):int(0.95 * h), int(0.2 * wd):int(0.8 * wd)].copy()
    cv2.putText(crop, f'f{t}', (20, 80), cv2.FONT_HERSHEY_SIMPLEX, 2.5, (255, 255, 255), 6)
    tiles.append(cv2.resize(crop, (crop.shape[1] // 2, crop.shape[0] // 2)))
mont = np.concatenate(tiles, 1)
cv2.putText(mont, 'white_pot only: mocap body blue / handle cyan;  P_s (scan template) body red / handle yellow', (20, mont.shape[0] - 25), cv2.FONT_HERSHEY_SIMPLEX, 1.1, (255, 255, 255), 3)
cv2.imwrite(f'{OUT}/ep0_pot_flip.png', mont); print('ok')
