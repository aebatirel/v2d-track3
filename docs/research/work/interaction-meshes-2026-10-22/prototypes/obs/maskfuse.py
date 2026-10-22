# Silhouette (colour-mask) free-space evidence in the object frame (scratch prototype, 2026-10-22; repo unchanged).
# Inference-legal inputs only: our tracks, our FoundationStereo depth, the raw ego_cam_c video, OUR OWN mesh of the
# object (only to sample the object's colour per frame). No scans, no mocap.
# Per frame: an object colour model (Lab, robust median / MAD) from our mesh's visible surface samples (projected with
# our track; visible = depth within 5 mm). Every voxel of the obsfuse2 grid is projected into the raw image (colour)
# and the rectified depth (occlusion). A view TESTS the voxel if the depth there is finite and not in front of the
# voxel by more than 3 mm (nothing occludes it). The view says FREE if the pixel colour is not the object's colour
# (max channel z-score > ZT). NMV = tests, NMF = free votes. Hands/other objects in front are excluded by the depth
# test; another object of the same colour simply never votes free (conservative).
# Usage: maskfuse.py --obj NAME --grid GRID.npz --mesh OUR_MESH --out OUT.npz --ep POSES_S2 DEPTH_S2 VIDEO [--ep ...]
import argparse, json, sys, time
import numpy as np, cv2, trimesh
S = '/tmp/claude-0/-home-user-v2d-track3/8c892c5e-fd7c-57aa-abef-68d2af098e4f/scratchpad'
p = argparse.ArgumentParser()
p.add_argument('--obj', required=True); p.add_argument('--grid', required=True); p.add_argument('--mesh', required=True)
p.add_argument('--out', required=True); p.add_argument('--ep', nargs=3, action='append', required=True)
p.add_argument('--zt', type=float, default=4.0); p.add_argument('--occ', type=float, default=0.003)
a = p.parse_args(); t0 = time.time()
C = json.load(open(f'{S}/loc/t3/calib.json')); cam = C['cameras']; sp = [q for q in C['stereo_pairs'] if q['camera'] == 'ego'][0]
Kc = np.array(cam['ego_cam_c']['intrinsic_matrix'], float); Dc = np.array(cam['ego_cam_c']['distortion_coefficients'], float)
Kb = np.array(cam['ego_cam_b']['intrinsic_matrix'], float); Db = np.array(cam['ego_cam_b']['distortion_coefficients'], float)
E = np.array(sp['left_to_right'], float)
R1, R2, P1, P2, Q, _, _ = cv2.stereoRectify(Kc, Dc, Kb, Db, (1280, 800), E[:3, :3].copy(), E[:3, 3].reshape(3, 1).copy(),
                                            alpha=0, newImageSize=(1600, 1000), flags=cv2.CALIB_ZERO_DISPARITY)
K = P1[:3, :3]
z = np.load(a.grid); shape = tuple(z['shape']); lo = z['lo']; vx = float(z['voxel'])
axes = [lo[k] + (np.arange(shape[k]) + 0.5) * vx for k in range(3)]
X = np.stack(np.meshgrid(*axes, indexing='ij'), -1).reshape(-1, 3); nv = len(X)
surf = trimesh.sample.sample_surface(trimesh.load(a.mesh, force='mesh'), 20000, seed=0)[0]
NMF = np.zeros(nv, np.float32); NMV = np.zeros(nv, np.float32)


def raw_uv(Xc):
    uv, _ = cv2.projectPoints((Xc @ R1).reshape(-1, 1, 3), np.zeros(3), np.zeros(3), Kc, Dc)
    return np.round(uv.reshape(-1, 2)).astype(np.int64)


stats = []
for poses, depth, video in a.ep:
    P = np.load(poses); T_co = P[f'cam_T_{a.obj}']; D = np.load(depth, mmap_mode='r'); N = min(len(T_co), len(D))
    cap = cv2.VideoCapture(video); fi = 0; i = 0
    while i < N:
        ok, frame = cap.read()
        if not ok:
            break
        if fi % 2:
            fi += 1; continue
        fi += 1
        Lab = cv2.cvtColor(cv2.medianBlur(frame, 3), cv2.COLOR_BGR2LAB).astype(np.float32)
        Dt = np.array(D[i], np.float32); H, W = Dt.shape
        R, tr = T_co[i][:3, :3], T_co[i][:3, 3]
        # object colour model from our own mesh's visible samples
        Sc = surf @ R.T + tr; zs = Sc[:, 2]
        us = np.round(K[0, 0] * Sc[:, 0] / zs + K[0, 2]).astype(int); vs = np.round(K[1, 1] * Sc[:, 1] / zs + K[1, 2]).astype(int)
        okr = (zs > 0.05) & (us >= 0) & (us < W) & (vs >= 0) & (vs < H)
        vis = np.zeros(len(Sc), bool); vis[okr] = np.abs(Dt[vs[okr], us[okr]] - zs[okr]) < 0.005
        uvc = raw_uv(Sc[vis]); okc = (uvc[:, 0] >= 0) & (uvc[:, 0] < 1280) & (uvc[:, 1] >= 0) & (uvc[:, 1] < 800)
        if okc.sum() < 200:
            i += 1; continue
        cols = Lab[uvc[okc, 1], uvc[okc, 0]]
        mu = np.median(cols, 0); sg = np.maximum(1.4826 * np.median(np.abs(cols - mu), 0), 3.0)
        # voxels
        Xc = X @ R.T + tr; zc = Xc[:, 2]
        ur = np.round(K[0, 0] * Xc[:, 0] / zc + K[0, 2]).astype(np.int64); vr = np.round(K[1, 1] * Xc[:, 1] / zc + K[1, 2]).astype(np.int64)
        ok = (zc > 0.05) & (ur >= 0) & (ur < W) & (vr >= 0) & (vr < H)
        idx = np.nonzero(ok)[0]; d = Dt[vr[idx], ur[idx]]
        tst = np.isfinite(d) & (d >= zc[idx] - a.occ)
        idx = idx[tst]
        uvc = raw_uv(Xc[idx]); okc = (uvc[:, 0] >= 0) & (uvc[:, 0] < 1280) & (uvc[:, 1] >= 0) & (uvc[:, 1] < 800)
        idx = idx[okc]; uvc = uvc[okc]
        zsc = np.abs(Lab[uvc[:, 1], uvc[:, 0]] - mu) / sg
        NMV[idx] += 1; NMF[idx[zsc.max(1) > a.zt]] += 1
        stats.append([float(x) for x in mu] + [float(x) for x in sg])
        i += 1
    print(poses, 'frames', i, round(time.time() - t0), 's', flush=True)
st = np.array(stats)
np.savez_compressed(a.out, shape=np.array(shape), lo=lo, voxel=vx, NMF=NMF.reshape(shape), NMV=NMV.reshape(shape),
                    colour_mu_med=np.median(st[:, :3], 0), colour_sg_med=np.median(st[:, 3:], 0), args=json.dumps(vars(a)))
print('saved', a.out, 'colour mu/sg', np.round(np.median(st[:, :3], 0), 1), np.round(np.median(st[:, 3:], 0), 1), round(time.time() - t0), 's')
