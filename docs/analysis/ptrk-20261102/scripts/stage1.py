"""Stage 1 of DESIGN_offline_joint.md (PREREG_stage1.md): one world pose per object per rest segment, fitted by trimmed
ICP to the object's stereo-depth points from every 2nd frame of the segment. GT-free: our track, our depth, our SAM2
video masks, our cameras (world_T_cam), our tracking templates. Never reads a parquet, scan or mocap.
Usage: python -I stage1.py EP POSES_NPZ DEPTH_NPY VOS_MASKS_NPZ K_SOURCE_NPZ MESH_DIR OUT_DIR [--cams CAMS_NPZ]
  POSES_NPZ: perc2 poses.npz (world_T_cam + cam_T_<obj>); K_SOURCE_NPZ: a perc2 det_f0.npz (its K = rectified left K).
  --cams: optional world_T_cam replacement (map arm), same frame count.
Writes OUT_DIR/poses_world_vo.npz (world_T_cam @ cam_T_<obj>, rest segments replaced) and OUT_DIR/stage1.json."""
import argparse, json, os, sys, hashlib
import numpy as np, trimesh, cv2
from scipy.spatial import cKDTree
from scipy.spatial.transform import Rotation as Rot, Slerp

p = argparse.ArgumentParser()
for k in ('ep', 'poses', 'depth', 'vos', 'ksrc', 'meshes', 'out'):
    p.add_argument(k)
p.add_argument('--cams', default=None)
p.add_argument('--trim', type=float, default=0.70)
p.add_argument('--iters', type=int, default=40)
p.add_argument('--every', type=int, default=2)
p.add_argument('--max_pts', type=int, default=1500)
p.add_argument('--min_pts', type=int, default=300)
p.add_argument('--max_move_cm', type=float, default=3.0)
p.add_argument('--max_rot_deg', type=float, default=10.0)
p.add_argument('--ramp', type=int, default=5)
a = p.parse_args()
for q in (a.poses, a.depth, a.vos, a.ksrc, a.cams or ''):
    assert not any(s in q for s in ('.parquet', 'observation', 'score_registered', '_pf.npz', '/gt/')), q
os.makedirs(a.out, exist_ok=True)

P = np.load(a.poses)
W = np.asarray(P['world_T_cam'], np.float64)
if a.cams:
    W = np.asarray(np.load(a.cams)['world_T_cam'], np.float64)
    assert len(W) == len(P['world_T_cam'])
names = [k[6:] for k in P.files if k.startswith('cam_T_')]
T = len(W)
O = {n: np.einsum('tij,tjk->tik', W, np.asarray(P[f'cam_T_{n}'], np.float64)) for n in names}
K = np.load(a.ksrc)['K'].astype(np.float64)
D = np.load(a.depth, mmap_mode='r')
V = np.load(a.vos)
rng = np.random.default_rng(0)


def mesh_pts(n):
    m = trimesh.load(f'{a.meshes}/{n}.glb', force='mesh')
    return m, np.asarray(trimesh.sample.sample_surface(m, 20000, seed=0)[0])


def rest_runs(X):
    c = X[:, :3, 3]
    sp = np.r_[0, np.linalg.norm(np.diff(c, axis=0), axis=1)] * 100
    rot = np.r_[0, [np.degrees(Rot.from_matrix(X[i - 1, :3, :3].T @ X[i, :3, :3]).magnitude()) for i in range(1, len(X))]]
    sm = lambda v: np.convolve(v, np.ones(3) / 3, 'same')
    still = (sm(sp) < 0.5) & (sm(rot) < 2.0)
    runs, s = [], None
    for i, v in enumerate(np.r_[still, False]):
        if v and s is None: s = i
        if not v and s is not None:
            if i - s >= 10: runs.append((s, i))
            s = None
    return runs


def silhouette(m, X_cam, shape, scale):
    """Projected silhouette of mesh m at camera-frame pose X_cam, at image size shape (rows, cols) = full / scale."""
    v = np.asarray(m.vertices) @ X_cam[:3, :3].T + X_cam[:3, 3]
    ok = v[:, 2] > 0.05
    uv = (v @ K.T); uv = uv[:, :2] / np.maximum(uv[:, 2:3], 1e-6) / scale
    img = np.zeros(shape, np.uint8)
    F = np.asarray(m.faces); F = F[ok[F].all(1)]
    cv2.fillPoly(img, [np.round(uv[f]).astype(np.int32) for f in F], 1)
    return img > 0


def kabsch(A, B):
    ca, cb = A.mean(0), B.mean(0)
    U, _, Vt = np.linalg.svd((A - ca).T @ (B - cb))
    d = np.sign(np.linalg.det(Vt.T @ U.T))
    R = Vt.T @ np.diag([1, 1, d]) @ U.T
    return R, cb - R @ ca


def trimmed_icp(obs_w, X0, mpts, tree):
    """Fit X (world pose of the mesh) so that obs_w lie on the mesh surface: points moved into the body frame by
    inv(X), matched to the nearest surface sample, best `trim` share kept, Kabsch on the kept pairs."""
    X = X0.copy()
    def resid(X):
        b = (obs_w - X[:3, 3]) @ X[:3, :3]
        d, j = tree.query(b)
        return b, d, j
    _, d0, _ = resid(X)
    r0 = float(np.sqrt(np.mean(np.sort(d0)[:int(a.trim * len(d0))] ** 2)))
    for it in range(a.iters):
        b, d, j = resid(X)
        keep = np.argsort(d)[:int(a.trim * len(d))]
        R, t = kabsch(b[keep], mpts[j[keep]])          # body-frame correction: mpts ~ R b + t
        Xn = X @ np.linalg.inv(np.r_[np.c_[R, t], [[0, 0, 0, 1]]])
        dt = np.linalg.norm(Xn[:3, 3] - X[:3, 3]); dr = np.degrees(Rot.from_matrix(X[:3, :3].T @ Xn[:3, :3]).magnitude())
        X = Xn
        if dt < 1e-4 and dr < 0.01:
            break
    _, d1, _ = resid(X)
    r1 = float(np.sqrt(np.mean(np.sort(d1)[:int(a.trim * len(d1))] ** 2)))
    return X, r0, r1, it + 1


def blend(A, B, w):
    """(1 - w) A + w B on SE(3): linear position, slerp rotation."""
    R = Slerp([0, 1], Rot.from_matrix([A[:3, :3], B[:3, :3]]))(w).as_matrix()
    M = np.eye(4); M[:3, :3] = R; M[:3, 3] = (1 - w) * A[:3, 3] + w * B[:3, 3]; return M


rec = dict(episode=int(a.ep), arm='map' if a.cams else 'vo', settings={k: getattr(a, k) for k in ('trim', 'iters', 'every', 'max_pts', 'min_pts', 'max_move_cm', 'max_rot_deg', 'ramp')},
           inputs={k: getattr(a, k) for k in ('poses', 'depth', 'vos', 'ksrc', 'meshes', 'cams')}, objects={})
NEW = {n: O[n].copy() for n in names}
for n in names:
    m, mpts = mesh_pts(n); tree = cKDTree(mpts)
    mv = np.unpackbits(V[n], axis=-1)                    # [T, 250, 400 (padded to bytes)]
    H4, W4 = mv.shape[1], 400; mv = mv[:, :, :W4].astype(bool); scale = D.shape[2] / W4
    segs = []
    for s, e in rest_runs(O[n]):
        fs, fe = s + 2, e - 2
        if fe - fs < 6: continue
        mid = (fs + fe) // 2; X0 = O[n][mid]
        pts = []
        for t in range(fs, fe, a.every):
            msk = mv[t] & cv2.dilate(silhouette(m, np.linalg.inv(W[t]) @ O[n][t], (H4, W4), scale).astype(np.uint8), np.ones((5, 5), np.uint8)).astype(bool)
            msk = cv2.erode(msk.astype(np.uint8), np.ones((3, 3), np.uint8)).astype(bool)
            v, u = np.nonzero(msk)
            if len(v) == 0: continue
            z = np.asarray(D[t])[(v * scale + scale / 2).astype(int).clip(0, D.shape[1] - 1), (u * scale + scale / 2).astype(int).clip(0, D.shape[2] - 1)]
            ok = z > 0; v, u, z = v[ok], u[ok], z[ok].astype(np.float64)
            if len(z) > a.max_pts:
                k = rng.choice(len(z), a.max_pts, replace=False); v, u, z = v[k], u[k], z[k]
            uu, vv = u * scale + scale / 2, v * scale + scale / 2
            Xc = np.stack([(uu - K[0, 2]) * z / K[0, 0], (vv - K[1, 2]) * z / K[1, 1], z], 1)
            pts.append(Xc @ W[t][:3, :3].T + W[t][:3, 3])
        npts = int(sum(len(q) for q in pts))
        sr = dict(frames=[int(s), int(e)], fit=[int(fs), int(fe)], points=npts)
        if npts < a.min_pts:
            sr['kept'] = 'tracker (too few points)'; segs.append(sr); continue
        X, r0, r1, its = trimmed_icp(np.concatenate(pts), X0, mpts, tree)
        mv_cm = float(np.linalg.norm(X[:3, 3] - X0[:3, 3]) * 100)
        rot_deg = float(np.degrees(Rot.from_matrix(X0[:3, :3].T @ X[:3, :3]).magnitude()))
        sr.update(rms_before_mm=round(r0 * 1000, 2), rms_after_mm=round(r1 * 1000, 2), iters=its, move_cm=round(mv_cm, 2), rot_deg=round(rot_deg, 2))
        if mv_cm > a.max_move_cm or rot_deg > a.max_rot_deg or not r1 < r0:
            sr['kept'] = 'tracker (guard)'; segs.append(sr); continue
        sr['kept'] = 'fit'
        for t in range(s, e):
            NEW[n][t] = X
        for k in range(1, a.ramp + 1):                   # ramps outside the segment back to the tracker
            w = 1 - k / (a.ramp + 1)
            if s - k >= 0: NEW[n][s - k] = blend(O[n][s - k], X, w)
            if e - 1 + k < T: NEW[n][e - 1 + k] = blend(O[n][e - 1 + k], X, w)
        segs.append(sr)
    changed = int((np.abs(NEW[n] - O[n]).max((1, 2)) > 1e-9).sum())
    rec['objects'][n] = dict(segments=segs, frames_changed=changed, frames=T)
    print(a.ep, n, 'segments', len(segs), 'fit', sum(s_['kept'] == 'fit' for s_ in segs), 'changed', changed, flush=True)
np.savez(f'{a.out}/poses_world_vo.npz', **NEW)
np.savez(f'{a.out}/changed.npz', **{n: (np.abs(NEW[n] - O[n]).max((1, 2)) > 1e-9) for n in names})
rec['sha256'] = hashlib.sha256(open(f'{a.out}/poses_world_vo.npz', 'rb').read()).hexdigest()
json.dump(rec, open(f'{a.out}/stage1.json', 'w'), indent=1)
