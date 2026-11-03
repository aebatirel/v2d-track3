"""PREREG_boardface.md: per-frame knob-face score (identity_fix cue, unchanged) of each board pose and its 180-degree
face-flip alternatives (ROLL = about the long axis z, Ry). GT-free. Camera-frame poses come either from a perception
poses.npz (public calibration) or from a packed reference parquet mapped to the camera frame (eval).
Usage: python -I board_face.py VIDEO CALIB MESH_DIR OUT_NPZ (--poses POSES_NPZ | --ref REF --table TABLE --perc PERC_POSES)"""
import argparse, json, os, sys, numpy as np, cv2, trimesh, pyarrow.parquet as pq
from scipy.spatial.transform import Rotation as Rot
p = argparse.ArgumentParser()
for k in ('video', 'calib', 'meshes', 'out'): p.add_argument(k)
p.add_argument('--poses'); p.add_argument('--ref'); p.add_argument('--table'); p.add_argument('--perc')
a = p.parse_args()
NAMES = ['wooden_piece_1', 'wooden_piece_2']
ALT = {'REF': np.eye(4), 'ROLL': np.diag([-1., -1, 1, 1]), 'Ry': np.diag([-1., 1, -1, 1])}
if a.poses:
    Z = np.load(a.poses); X = {n: np.asarray(Z[f'cam_T_{n}'], float) for n in NAMES}
else:
    t = pq.read_table(a.ref).to_pandas(); on = t['object_name'].iloc[0]; names = on.split('__') if isinstance(on, str) else list(on)
    pos = np.array([[np.asarray(list(v), float) for v in fr] for fr in t['object_body_position'].iloc[0]])
    qq = np.array([[np.asarray(list(v), float) for v in fr] for fr in t['object_body_wxyz'].iloc[0]])
    iT = np.linalg.inv(np.load(a.table)['T_table_from_world']); W = np.asarray(np.load(a.perc)['world_T_cam'], float)
    N = min(len(pos), len(W)); X = {}
    for n in NAMES:
        b = names.index(n); M = np.tile(np.eye(4), (N, 1, 1))
        M[:, :3, :3] = Rot.from_quat(np.c_[qq[:N, b, 1:4], qq[:N, b, 0]]).as_matrix(); M[:, :3, 3] = pos[:N, b]
        X[n] = np.linalg.inv(W[:N]) @ iT @ M
T = min(len(v) for v in X.values())
C = json.load(open(a.calib)); cam = C['cameras']; sp = [q for q in C['stereo_pairs'] if q['camera'] == 'ego'][0]
K_ = lambda n: np.array(cam[n]['intrinsic_matrix'], float); D_ = lambda n: np.array(cam[n]['distortion_coefficients'], float)
E = np.array(sp['left_to_right'], float); SZ, RSZ = (1280, 800), (1600, 1000)
R1, R2, P1, P2, Q, _, _ = cv2.stereoRectify(K_('ego_cam_c'), D_('ego_cam_c'), K_('ego_cam_b'), D_('ego_cam_b'), SZ, E[:3, :3].copy(),
                                            E[:3, 3].reshape(3, 1).copy(), alpha=0, newImageSize=RSZ, flags=cv2.CALIB_ZERO_DISPARITY)
MC = cv2.initUndistortRectifyMap(K_('ego_cam_c'), D_('ego_cam_c'), R1, P1, RSZ, cv2.CV_32FC1); KR = P1[:3, :3]
M = {}
for n in NAMES:
    V = np.asarray(trimesh.load(f'{a.meshes}/{n}.glb', force='mesh').vertices); xm = np.median(V[:, 0])
    M[n] = (V[np.abs(V[:, 0] - xm) > 0.009], V[np.abs(V[:, 0] - xm) < 0.003], xm)
def score(n, T_, img):                     # identical to identity_fix.score
    knobs, plate, xm = M[n]
    cam_side = np.sign((np.linalg.inv(T_) @ np.r_[0, 0, 0, 1.0])[0] - xm)
    k = knobs[np.sign(knobs[:, 0] - xm) == cam_side]
    if len(k) < 5: return 0.0
    def sample(Xv):
        Y = Xv @ T_[:3, :3].T + T_[:3, 3]; u = Y @ KR.T; uv = np.round(u[:, :2] / u[:, 2:3]).astype(int)
        ok = (uv[:, 0] >= 0) & (uv[:, 0] < img.shape[1]) & (uv[:, 1] >= 0) & (uv[:, 1] < img.shape[0]) & (Y[:, 2] > 0.05)
        return img[uv[ok, 1], uv[ok, 0]]
    s_k, s_p = sample(k), sample(plate)
    return float(s_k.mean() - s_p.mean()) if len(s_k) and len(s_p) else 0.0
S = {f'{n}_{k}': np.full(T, np.nan) for n in NAMES for k in ALT}
cap = cv2.VideoCapture(a.video); i = 0
while i < T:
    ok, f = cap.read()
    if not ok: break
    img = cv2.GaussianBlur(cv2.remap(cv2.cvtColor(f, cv2.COLOR_BGR2GRAY), MC[0], MC[1], cv2.INTER_LINEAR), (3, 3), 0).astype(float)
    for n in NAMES:
        for k, F in ALT.items(): S[f'{n}_{k}'][i] = score(n, X[n][i] @ F, img)
    i += 1
np.savez_compressed(a.out, frames=np.arange(T), **S); print('wrote', a.out, 'frames', i, 'of', T)
