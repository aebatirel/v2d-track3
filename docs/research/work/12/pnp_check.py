"""Validation on PUBLIC ep 11 frame 0: do scan markers placed by GT poses reproject onto image marker blobs?
Camera pose is solved by PnP over all injective 2D->3D assignments; GT is used only for this public check."""
import numpy as np, json, itertools, cv2, pandas as pd
from scipy.spatial.transform import Rotation as Rr
from selfsim import good_markers
cal = json.load(open('/Users/aebatirel/Documents/Code/v2d-research/data/track_3/public/meta/camera_calibration.json'))['cameras']['ego_cam_a']
W, H = cal['resolution']
K0 = np.array(cal['intrinsic_matrix']); D0 = np.array(cal['distortion_coefficients'], float)
def variant(rotated):
    K = K0.copy(); D = D0.copy()
    if rotated:
        K[0, 2] = W - 1 - K[0, 2]; K[1, 2] = H - 1 - K[1, 2]
        D[[2, 3, 8, 9, 10, 11, 12, 13]] *= -1
    return K, D
def T_of(pose):
    x, y, z, qw, qx, qy, qz = pose
    T = np.eye(4); T[:3, :3] = Rr.from_quat([qx, qy, qz, qw]).as_matrix(); T[:3, 3] = [x, y, z]; return T
def world_markers(ep, frame, names):
    df = pd.read_parquet(f'/Users/aebatirel/Documents/Code/v2d-research/data/track_3/public/data/chunk-000/episode_{ep:06d}.parquet')
    objs = {o['name']: o for o in df.iloc[frame]['observation.objects']}
    X, lab = [], []
    for n in names:
        T = T_of(objs[n]['pose']); mk = good_markers(n)
        for i, m in enumerate(mk): X.append(T[:3, :3] @ m + T[:3, 3]); lab.append(f'{n}#{i}')
    return np.array(X), lab, objs
def solve(uv, X, K, D, min_pts=4):
    best = (1e9, None)
    und = cv2.undistortPoints(uv.reshape(-1, 1, 2).astype(np.float64), K, D).reshape(-1, 2)
    for perm in itertools.permutations(range(len(X)), len(uv)):
        Xp = X[list(perm)]
        ok, rv, tv = cv2.solvePnP(Xp, und, np.eye(3), None, flags=cv2.SOLVEPNP_SQPNP)
        if not ok: continue
        ok, rv, tv = cv2.solvePnP(Xp, und, np.eye(3), None, rv, tv, True, flags=cv2.SOLVEPNP_ITERATIVE)
        Rc = cv2.Rodrigues(rv)[0]
        if ((Xp @ Rc.T + tv.ravel())[:, 2] <= 0).any(): continue
        pr = cv2.projectPoints(Xp, rv, tv, K, D)[0].reshape(-1, 2)
        e = np.linalg.norm(pr - uv, axis=1)
        if e.mean() < best[0]: best = (e.mean(), (perm, rv, tv, e))
    return best
if __name__ == '__main__':
    uv = np.array([[795, 988], [1044, 1022], [950, 1290], [1260, 1059], [1479, 984], [1273, 888]], float)
    X, lab, objs = world_markers(11, 0, ['blue_cup', 'beige_cup'])
    for rotated in (False, True):
        K, D = variant(rotated)
        err, (perm, rv, tv, e) = solve(uv, X, K, D)
        print('rotated-K' if rotated else 'as-given K', 'mean reproj px %.2f' % err, 'per-pt', np.round(e, 1), 'assign', [lab[i] for i in perm])
        Rc = cv2.Rodrigues(rv)[0]; C = -Rc.T @ tv.ravel(); print('   camera centre world', np.round(C, 3), 'dist to beige cup %.3f m' % np.linalg.norm(C - objs['beige_cup']['pose'][:3]))
