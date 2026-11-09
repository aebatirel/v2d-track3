"""CPU dry run of perc2's TRACK_CAM=a block (cuda -> cpu, FoundationPose replaced by a stub)."""
import sys, os, json, re, time, numpy as np, cv2, torch
REPO, DRY, CC = sys.argv[1:4]
src = open(f'{REPO}/pipeline/perc2.py').read()
blk = src[src.index("ACAM = {'fallback'"):src.index('# TRACK_GUARD (2026-10-25; pre-registered')]
setlast = src[src.index('def set_last(est, X):'):src.index('_DETC = {}')]
blk = blk.replace("device='cuda'", "device='cpu'")
sys.path.insert(0, f'{REPO}/pipeline'); import det_rules
C = json.load(open(f'{DRY}/t3/calib.json')); cam = C['cameras']
sp = [p for p in C['stereo_pairs'] if p['camera'] == 'ego'][0]
K_ = 80                                                      # as perc2 after the DET_K line
Kc, dc, Kb, db = [np.array(cam[n][k], float) for n, k in [('ego_cam_c', 'intrinsic_matrix'), ('ego_cam_c', 'distortion_coefficients'), ('ego_cam_b', 'intrinsic_matrix'), ('ego_cam_b', 'distortion_coefficients')]]
E = np.array(sp['left_to_right'], float); RSZ = (1600, 1000)
R1, R2, P1, P2, Q, _, _ = cv2.stereoRectify(Kc, dc, Kb, db, (1280, 800), E[:3, :3].copy(), E[:3, 3].reshape(3, 1).copy(), alpha=0, newImageSize=RSZ, flags=cv2.CALIB_ZERO_DISPARITY)
KR = P1[:3, :3].copy()
depths = np.load(f'{CC}/store/cache/depth/public/ep12/depths_fs0.5.npy', mmap_mode='r'); N = len(depths)
rc = [np.zeros((1000, 1600), np.uint8)] * N; rgb = lambda g: np.repeat(g[..., None], 3, 2)
class Est:
    pose_last = None
    def register(self, K, rgb, depth, ob_mask, iteration):
        assert rgb.shape[:2] == depth.shape == ob_mask.shape, (rgb.shape, depth.shape, ob_mask.shape); self.k = K; return np.eye(4)
    def track_one(self, rgb, depth, K, iteration):
        assert rgb.shape[:2] == depth.shape; return np.eye(4)
    def get_tf_to_centered_mesh(self): return torch.eye(4)
g = dict(np=np, cv2=cv2, torch=torch, json=json, os=os, det_rules=det_rules, D=f'{DRY}/t3', VD=f'{DRY}/t3/v', EP=12, R1=R1, RSZ=RSZ,
         KR=KR, depths=depths, N=N, rc=rc, rgb=rgb, K_=K_, REG_ITERS=5, TRACK_ITERS=2, TRACK_CAM='a',
         log=lambda *a: print('[log]', *[str(x)[:160] for x in a]))
exec(setlast.replace("device='cuda'", "device='cpu'"), g); exec(blk, g)
est = Est(); m = np.zeros((1000, 1600), bool); m[600:900, 500:1100] = True
t0 = time.time(); P0 = g['t_register'](est, 0, m); print('register ok', P0[:3, 3], 'K', est.k[0, 0])
for i in (1, 50, N - 1): X = g['t_track'](est, i)
g['set_last'](est, np.eye(4)); print('track/set_last ok', round(time.time() - t0, 1), 's', g['ACAM'], 'A frames', len(g['FA']))
print('T_rc_a @ eye translation (cam a origin in rc):', P0[:3, 3].round(4))
