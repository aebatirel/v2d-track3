# DIAGNOSTIC (uses the scan-derived slot location in the board frame; our tracks and our own depth). Does our real
# FoundationStereo depth (fs0.5) ever see THROUGH the empty slot? Per frame (stride 2) while the slot is open (partner
# board centre > 12 cm away): rays through 9 points on the slot centre line (y 1..5 cm, mid-plate, slot centre z);
# expected depth if the slot were filled = the ray's hit on the camera-facing board face; excess = observed - face.
# 'through' = excess > 6 mm (the ray passed the back face). Geometry: az = ray tilt in the (normal, slot-width) plane.
import sys, json, numpy as np, cv2
sys.path.insert(0, '/home/user/v2d-track3/pipeline')
from recon_mesh import rectified_K
SP = '/tmp/claude-0/-home-user-v2d-track3/8c892c5e-fd7c-57aa-abef-68d2af098e4f/scratchpad'
K = rectified_K(f'{SP}/loc/t3/calib.json')
SLOT = {'wooden_piece_1': dict(xc=-0.0012, th=0.0080, zc=0.0020, w=0.0085), 'wooden_piece_2': dict(xc=0.0003, th=0.0091, zc=-0.0010, w=0.0089)}
out = {}
SG = float(sys.argv[1]) if len(sys.argv) > 1 else 1.0
for E in (24, 23):
    P = np.load(f'{SP}/interact/obs/depth/ep{E}_s2_poses.npz'); D = np.load(f'{SP}/interact/obs/depth/ep{E}_s2.npy', mmap_mode='r')
    for me, oth in (('wooden_piece_1', 'wooden_piece_2'), ('wooden_piece_2', 'wooden_piece_1')):
        s = SLOT[me]; Cm = P[f'cam_T_{me}']; Co = P[f'cam_T_{oth}']
        ys = np.linspace(0.01, 0.05, 9) * SG; Pts = np.stack([np.full(9, s['xc']), ys, np.full(9, s['zc'])], 1)
        rows = []
        for i in range(len(Cm)):
            if np.linalg.norm(Cm[i][:3, 3] - Co[i][:3, 3]) < 0.12:
                continue
            R, t = Cm[i][:3, :3], Cm[i][:3, 3]; Q = Pts @ R.T + t
            ray = Q / np.linalg.norm(Q, axis=1, keepdims=True); r_o = ray @ R            # rays in board frame
            az = float(np.degrees(np.arctan2(abs(r_o[:, 2].mean()), abs(r_o[:, 0].mean()))))
            inc = float(np.degrees(np.arccos(abs(r_o[:, 0].mean()))))
            # face toward the camera: x = xc - sign(r_o.x) * th/2 ; hit param along ray from the camera
            nb = R[:, 0]; xf = s['xc'] - np.sign(r_o[:, 0]) * s['th'] / 2
            # point on face plane along ray: camera origin 0; plane: nb.(p - (t + R@[xf,0,0])) = 0
            pf = t[None] + np.outer(xf, nb)
            lam = (pf @ nb) / (ray @ nb)
            dface = lam * ray[:, 2]
            u = np.round(K[0, 0] * Q[:, 0] / Q[:, 2] + K[0, 2]).astype(int); v = np.round(K[1, 1] * Q[:, 1] / Q[:, 2] + K[1, 2]).astype(int)
            okp = (u >= 2) & (u < 1598) & (v >= 2) & (v < 998)
            if not okp.any():
                continue
            Dt = np.array(D[i], np.float32)
            Dz = np.where(np.isfinite(Dt), Dt, 0); k5 = np.ones((5, 5), np.uint8)
            edge = (cv2.dilate(Dz, k5) - cv2.erode(Dz, k5)) > 0.02
            d = Dt[v[okp], u[okp]]; ex = d - dface[okp]
            rows.append(dict(t=2 * i, az=round(az, 1), inc=round(inc, 1), z=round(float(Q[:, 2].mean()), 3),
                             px=round(float(K[0, 0] * s['w'] / Q[:, 2].mean()), 1),
                             through=int((ex > 0.006).sum()), n=int(okp.sum()), nan=int((~np.isfinite(d)).sum()),
                             edge_killed=int(edge[v[okp], u[okp]].sum()), med_excess_mm=round(float(np.nanmedian(ex)) * 1e3, 1)))
        R_ = rows
        geo = [r for r in R_ if r['az'] < 45]
        thr = [r for r in R_ if r['through'] >= 3]
        thr_ok = [r for r in thr if r['edge_killed'] < r['through']]
        out[f'ep{E}_{me}'] = dict(open_frames=len(R_), geom_ok_frames=len(geo), through_frames=len(thr),
                                  through_frames_survive_edge_filter=len(thr_ok),
                                  through_list=[(r['t'], r['az'], r['through'], r['edge_killed'], r['med_excess_mm']) for r in thr][:40],
                                  rows=R_, geom_ok_list=[(r['t'], r['az'], r['inc'], r['px'], r['through'], r['med_excess_mm']) for r in geo][:60])
        print(E, me, json.dumps({k: v for k, v in out[f'ep{E}_{me}'].items() if not k.endswith('list')}), flush=True)
json.dump(out, open(f'{SP}/interact/obs/slotlook{"_ctrl" if SG < 0 else ""}.json', 'w'), indent=0)
