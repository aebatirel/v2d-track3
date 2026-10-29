# DIAGNOSTIC proxy for silhouette/mask carving (slot location from the scan frame; our tracks; raw RGB video).
# Is the open slot visible in the IMAGE, i.e. does a slot pixel look like the background rather than wood?
# For each frame while the slot is open: colour (Lab, 3x3 median) at 9 slot centre-line points, at 9 solid-board
# control points (mirrored y), and at 9 background points just beyond the slot's open edge (y = edge + 1.5 cm,
# same plane). contrast = |slot - board| / |background - board| (1 = slot shows background, 0 = slot looks like wood).
import sys, json, numpy as np, cv2
sys.path.insert(0, '/home/user/v2d-track3/pipeline')
SP = '/tmp/claude-0/-home-user-v2d-track3/8c892c5e-fd7c-57aa-abef-68d2af098e4f/scratchpad'
C = json.load(open(f'{SP}/loc/t3/calib.json')); cam = C['cameras']
sp = [p for p in C['stereo_pairs'] if p['camera'] == 'ego'][0]
Kc = np.array(cam['ego_cam_c']['intrinsic_matrix'], float); Dc = np.array(cam['ego_cam_c']['distortion_coefficients'], float)
Kb = np.array(cam['ego_cam_b']['intrinsic_matrix'], float); Db = np.array(cam['ego_cam_b']['distortion_coefficients'], float)
E = np.array(sp['left_to_right'], float)
R1, R2, P1, P2, Q, _, _ = cv2.stereoRectify(Kc, Dc, Kb, Db, (1280, 800), E[:3, :3].copy(), E[:3, 3].reshape(3, 1).copy(),
                                            alpha=0, newImageSize=(1600, 1000), flags=cv2.CALIB_ZERO_DISPARITY)
SLOT = {'wooden_piece_1': dict(xc=-0.0012, zc=0.0020, y1=0.059), 'wooden_piece_2': dict(xc=0.0003, zc=-0.0010, y1=0.057)}
vid = {23: f'{SP}/loc/v/ep23_c.mp4', 24: f'{SP}/interact/obs/v/ep24_c.mp4'}
out = {}
for Ep in (23, 24):
    P = np.load(f'{SP}/loc/perc/ep{Ep}/poses.npz'); cap = cv2.VideoCapture(vid[Ep]); frames = []
    i = 0
    while True:
        ok, f = cap.read()
        if not ok:
            break
        frames.append(cv2.cvtColor(f, cv2.COLOR_BGR2LAB) if i % 2 == 0 else None); i += 1
    for me, oth in (('wooden_piece_1', 'wooden_piece_2'), ('wooden_piece_2', 'wooden_piece_1')):
        s = SLOT[me]; Cm = P[f'cam_T_{me}']; Co = P[f'cam_T_{oth}']
        ys = np.linspace(0.01, 0.05, 9)
        pts = {'slot': np.stack([np.full(9, s['xc']), ys, np.full(9, s['zc'])], 1),
               'board': np.stack([np.full(9, s['xc']), -ys, np.full(9, s['zc'])], 1),
               'side': np.stack([np.full(9, s['xc']), ys, np.full(9, s['zc'] + 0.025)], 1),
               'bg': np.stack([np.full(9, s['xc']), np.full(9, s['y1'] + 0.015), np.linspace(-0.02, 0.02, 9)], 1)}
        rows = []
        for t in range(0, min(len(Cm), len(frames)), 2):
            if np.linalg.norm(Cm[t][:3, 3] - Co[t][:3, 3]) < 0.12:
                continue
            col = {}
            for k, X in pts.items():
                Xc = X @ Cm[t][:3, :3].T + Cm[t][:3, 3]          # rectified-left camera frame
                Xr = Xc @ R1                                     # raw camera frame (R1 maps raw -> rectified)
                uv, _ = cv2.projectPoints(Xr.reshape(-1, 1, 3), np.zeros(3), np.zeros(3), Kc, Dc)
                uv = np.round(uv.reshape(-1, 2)).astype(int)
                okp = (uv[:, 0] >= 1) & (uv[:, 0] < 1279) & (uv[:, 1] >= 1) & (uv[:, 1] < 799)
                if okp.sum() < 5:
                    break
                F = frames[t].astype(np.float32)
                col[k] = np.median(np.stack([np.median(F[v - 1:v + 2, u - 1:u + 2].reshape(-1, 3), 0) for u, v in uv[okp]]), 0)
            if len(col) < 3:
                continue
            dbg = np.linalg.norm(col['bg'] - col['board'])
            rows.append(dict(t=t, contrast=round(float(np.linalg.norm(col['slot'] - col['board']) / max(dbg, 1e-6)), 2), bg_board_dE=round(float(dbg), 1),
                             ctrl=round(float(np.linalg.norm(col['side'] - col['board']) / max(dbg, 1e-6)), 2)))
        cc = np.array([r['ctrl'] for r in rows]); c = np.array([r['contrast'] for r in rows]); dE = np.array([r['bg_board_dE'] for r in rows])
        good = dE > 15
        out[f'ep{Ep}_{me}'] = dict(open_frames=len(rows), frames_bg_distinct=int(good.sum()),
                                   contrast_med=round(float(np.median(c[good])), 2) if good.any() else None,
                                   frames_contrast_gt_0p5=int((c[good] > 0.5).sum()),
                                   ctrl_med=round(float(np.median(cc[good])), 2) if good.any() else None, ctrl_frames_gt_0p5=int((cc[good] > 0.5).sum()),
                                   by_time=[(r['t'], r['contrast'], r['bg_board_dE']) for r in rows][::3])
        print(Ep, me, json.dumps({k: v for k, v in out[f'ep{Ep}_{me}'].items() if k != 'by_time'}), flush=True)
json.dump(out, open(f'{SP}/interact/obs/slotrgb.json', 'w'), indent=0)
