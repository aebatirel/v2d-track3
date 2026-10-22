# Does the board itself bias our table plane? Frame-0 RANSAC plane (recon_mesh.table_plane, thin SVD) and the per-frame
# refit (recon_mesh's 30/12 mm bands) with and without the pixels of our own tracked objects (OUR meshes posed by OUR
# tracks, dilated 15 px). Reports the scan's lowest point above each plane (DIAGNOSTIC only) and our mesh's.
import sys, json, numpy as np, trimesh, cv2
sys.path.insert(0, '/home/user/v2d-track3/pipeline')
_svd = np.linalg.svd
np.linalg.svd = lambda A, full_matrices=False, **k: _svd(A, full_matrices=False, **k)
import recon_mesh as rm
S = '/tmp/claude-0/-home-user-v2d-track3/8c892c5e-fd7c-57aa-abef-68d2af098e4f/scratchpad'
K = rm.rectified_K(f'{S}/loc/t3/calib.json')
B = ('wooden_piece_1', 'wooden_piece_2')
ours = {b: trimesh.sample.sample_surface(trimesh.load(f'/home/user/v2d-track3/meshes/library_v4/{b}.glb', force='mesh'), 20000, seed=0)[0] for b in B}
scan = {b: np.asarray(trimesh.load(f'{S}/loc/t3/mesh/{b}/{b}_visual.glb', force='mesh').vertices) for b in B}
for E in (23, 24):
    P = np.load(f'{S}/interact/obs/depth/ep{E}_s2_poses.npz'); D = np.load(f'{S}/interact/obs/depth/ep{E}_s2.npy', mmap_mode='r')
    for i in (0, 10, 20):                                         # s2 index -> frames 0, 20, 40
        Dt = np.array(D[i], np.float32); H, W = Dt.shape
        mask = np.zeros((H, W), np.uint8)
        for b in B:
            T = P[f'cam_T_{b}'][i]; X = ours[b] @ T[:3, :3].T + T[:3, 3]
            u = np.round(K[0, 0] * X[:, 0] / X[:, 2] + K[0, 2]).astype(int); v = np.round(K[1, 1] * X[:, 1] / X[:, 2] + K[1, 2]).astype(int)
            ok = (u >= 0) & (u < W) & (v >= 0) & (v < H); mask[v[ok], u[ok]] = 1
        mask = cv2.dilate(mask, np.ones((31, 31), np.uint8))
        o = P[f'cam_T_{B[0]}'][i][:3, 3]
        res = {}
        for nm, Dm in (('all_pixels', Dt), ('objects_masked', np.where(mask > 0, np.nan, Dt))):
            n, c, fr = rm.table_plane(Dm, K, o)
            row = {}
            for b in B:
                T = P[f'cam_T_{b}'][i]
                row[b] = dict(scan_low_mm=round(float(((scan[b] @ T[:3, :3].T + T[:3, 3]) @ n + c).min()) * 1e3, 1),
                              ours_low_mm=round(float(((ours[b] @ T[:3, :3].T + T[:3, 3]) @ n + c).min()) * 1e3, 1))
            res[nm] = dict(c=round(float(c), 4), inl=round(fr, 3), **row)
        print(E, 2 * i, json.dumps(res), flush=True)
