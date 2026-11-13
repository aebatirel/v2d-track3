"""Port of Team Purple's model-to-cloud registration (cringeyburger/purple-v2d-track3 @ 8f823be,
reconstruction/tools/spoon_register.py, Apache-2.0) to our public-episode inputs. GT-free: our cameras (control C
world_T_cam), our depth cache, our SAM2 video masks, our MediaPipe hand joints, our scoring meshes. Never reads a
parquet, scan or mocap. Algorithm and constants as Purple's; differences are listed in PREREG.md.
Usage: python -I purple_track.py EP POSES_NPZ DEPTH_NPY VOS_NPZ KSRC_NPZ HANDS_NPZ MESH_DIR OUT_DIR --objects a,b"""
import argparse, json, os, time
import numpy as np, cv2, trimesh
from scipy.spatial import cKDTree

p = argparse.ArgumentParser()
for k in ('ep', 'poses', 'depth', 'vos', 'ksrc', 'hands', 'meshes', 'out'):
    p.add_argument(k)
p.add_argument('--objects', required=True)
p.add_argument('--hand_dilate', type=int, default=31)        # px at depth resolution
p.add_argument('--min_mask_px', type=int, default=146)
p.add_argument('--max_pts', type=int, default=5000)
p.add_argument('--tracker_start', action='store_true', help='variant: also start ICP from our tracker pose')
a = p.parse_args()
for q in (a.poses, a.depth, a.vos, a.ksrc, a.hands, a.meshes):
    assert not any(s in q for s in ('.parquet', 'observation', 'score_registered', '_pf.npz', '/gt/', '/t3/mesh')), q
os.makedirs(a.out, exist_ok=True)
t0 = time.time()
P = np.load(a.poses)
W = np.asarray(P['world_T_cam'], np.float64)
names = [k[6:] for k in P.files if k.startswith('cam_T_')]
T = len(W)
O = {n: np.einsum('tij,tjk->tik', W, np.asarray(P[f'cam_T_{n}'], np.float64)) for n in names}
K = np.load(a.ksrc)['K'].astype(np.float64)
D = np.load(a.depth, mmap_mode='r')
V = np.load(a.vos)
HZ = np.load(a.hands)
assert 'frame 0' in str(HZ['world_frame']) and np.allclose(HZ['KR'], K, atol=1e-6), (HZ['world_frame'], HZ['KR'], K)
assert np.allclose(W[0], np.eye(4), atol=1e-6), 'expects our world = rectified-left camera at frame 0'
DH, DW = D.shape[1:]
MH, MW = 250, 400
s = DW / MW


def hand_mask(t):
    """Depth-resolution mask of both hands: convex hull of the 21 projected joints, dilated."""
    m = np.zeros((DH, DW), np.uint8)
    if t >= len(HZ['joints_right']):
        return m > 0
    Ci = np.linalg.inv(W[t])
    for side in ('left', 'right'):
        if not bool(HZ[f'valid_{side}'][t]):
            continue
        J = HZ[f'joints_{side}'][t].astype(np.float64) @ Ci[:3, :3].T + Ci[:3, 3]
        if (J[:, 2] < 0.05).any():
            continue
        uv = (J @ K.T); uv = uv[:, :2] / uv[:, 2:3]
        cv2.fillConvexPoly(m, cv2.convexHull(np.round(uv).astype(np.int32)), 1)
    return cv2.dilate(m, np.ones((a.hand_dilate, a.hand_dilate), np.uint8)) > 0


def frame_cloud(n, t):
    """Purple's frame_cloud: mask eroded 1 px, hand removed, depth points in the world. Returns (P_world, mask, hand)."""
    mc = np.unpackbits(V[n][t], axis=-1)[:, :MW].astype(np.uint8)
    if mc.sum() < a.min_mask_px:
        return None, mc > 0, None
    mce = cv2.erode(mc, np.ones((3, 3), np.uint8))
    mfull = cv2.resize(mce, (DW, DH), interpolation=cv2.INTER_NEAREST) > 0
    hc = hand_mask(t)
    keep = mfull & ~hc
    z = np.asarray(D[t], np.float64)
    keep &= (z > 0.2) & (z < 1.5)
    v, u = np.nonzero(keep)
    if len(v) < 300:
        return None, mc > 0, hc
    zz = z[v, u]
    X = np.stack([(u - K[0, 2]) * zz / K[0, 0], (v - K[1, 2]) * zz / K[1, 1], zz], 1)
    Pw = X @ W[t][:3, :3].T + W[t][:3, 3]
    return Pw, mc > 0, hc


def small_rot(w):  # Purple's
    th = np.linalg.norm(w)
    if th < 1e-12: return np.eye(3)
    k = w / th; Kx = np.array([[0, -k[2], k[1]], [k[2], 0, -k[0]], [-k[1], k[0], 0]])
    return np.eye(3) + np.sin(th) * Kx + (1 - np.cos(th)) * Kx @ Kx


def icp(Tm, Pw, tree, Mb, Nb, iters=25, trim=0.85):  # Purple's, unchanged
    Tm = Tm.copy()
    for _ in range(iters):
        Q = (Pw - Tm[:3, 3]) @ Tm[:3, :3]
        d, i = tree.query(Q); k = d <= np.quantile(d, trim)
        q, m, nrm = Q[k], Mb[i[k]], Nb[i[k]]
        A = np.hstack([np.cross(q, nrm), nrm]); b = ((m - q) * nrm).sum(1)
        x = np.linalg.lstsq(A, b, rcond=None)[0]
        dT = np.eye(4); dT[:3, :3] = small_rot(x[:3]); dT[:3, 3] = x[3:]
        Tm = Tm @ np.linalg.inv(dT)
        if np.linalg.norm(x) < 1e-6: break
    Q = (Pw - Tm[:3, 3]) @ Tm[:3, :3]; d = tree.query(Q)[0]
    return Tm, float(1e3 * np.sort(d)[:int(len(d) * trim)].mean())


def sil_iou(Tm, Md, mc, hc, t):
    """Purple's silhouette IoU outside the hand, at mask resolution (theirs: 1/4 of 1280 x 800)."""
    Tc = np.linalg.inv(W[t]) @ Tm
    X = Md @ Tc[:3, :3].T + Tc[:3, 3]
    ok = X[:, 2] > 0.05
    uv = X[ok] @ K.T; uv = uv[:, :2] / uv[:, 2:3] / s
    u = np.round(uv).astype(int); inb = (u[:, 0] >= 0) & (u[:, 0] < MW) & (u[:, 1] >= 0) & (u[:, 1] < MH)
    R_ = np.zeros((MH, MW), np.uint8); R_[u[inb, 1], u[inb, 0]] = 1
    R_ = cv2.morphologyEx(R_, cv2.MORPH_CLOSE, np.ones((3, 3), np.uint8)) > 0
    H_ = np.zeros((MH, MW), bool) if hc is None else cv2.resize(hc.astype(np.uint8), (MW, MH), interpolation=cv2.INTER_AREA) > 0
    vv = ~H_
    return float((R_ & mc & vv).sum() / max(((R_ | mc) & vv).sum(), 1))


rec = dict(episode=int(a.ep), settings={k: getattr(a, k) for k in ('hand_dilate', 'min_mask_px', 'max_pts', 'tracker_start')}, objects={})
NEW = {n: O[n].copy() for n in names}
for n in a.objects.split(','):
    if n not in names:
        continue
    mesh = trimesh.load(f'{a.meshes}/{n}.glb', force='mesh')
    Mb, fi = trimesh.sample.sample_surface_even(mesh, 8000, seed=0)
    Nb = mesh.face_normals[fi]
    Md = np.asarray(trimesh.sample.sample_surface(mesh, 25000, seed=1)[0])
    tree = cKDTree(Mb)
    cm = Md.mean(0); _, Em = np.linalg.eigh(np.cov((Md - cm).T))   # model principal axes, ascending
    em1, em2, em3 = Em[:, 2], Em[:, 1], Em[:, 0]
    Fm = np.stack([em1, np.cross(em3, em1), em3], 1)              # model PCA frame (x = longest, z = shortest)
    dist = np.full(T, np.nan); iou = np.full(T, np.nan); used = np.zeros(T, bool)
    prev, prevf = None, -9
    for t in range(T):
        Pw, mc, hc = frame_cloud(n, t)
        if Pw is None:
            continue
        if len(Pw) > a.max_pts:
            Pw = Pw[np.random.default_rng(t).choice(len(Pw), a.max_pts, replace=False)]
        c = Pw.mean(0); _, E = np.linalg.eigh(np.cov((Pw - c).T)); e1, e2, e3 = E[:, 2], E[:, 1], E[:, 0]
        starts = []
        if prev is not None and t - prevf <= 3:
            starts.append(prev)
        for sx in (1, -1):
            for zax in (e3, e2):
                for sz in (1, -1):
                    x = sx * e1; z = sz * zax; y = np.cross(z, x)
                    Rw = np.stack([x, y, z], 1) @ Fm.T                 # model PCA axes -> cloud PCA axes
                    Tm = np.eye(4); Tm[:3, :3] = Rw; Tm[:3, 3] = c - Rw @ cm; starts.append(Tm)
        if a.tracker_start:
            starts.append(O[n][t])
        best = None
        for k, T0 in enumerate(starts):
            Tm, d = icp(T0, Pw, tree, Mb, Nb, iters=20)
            i_ = sil_iou(Tm, Md, mc, hc, t)
            sc = d + 20 * (1 - i_) - (0.5 if (k == 0 and prev is not None and t - prevf <= 3) else 0)
            if best is None or sc < best[0]:
                best = (sc, Tm, d, i_)
        Tm, d = icp(best[1], Pw, tree, Mb, Nb, iters=15); i_ = sil_iou(Tm, Md, mc, hc, t)
        NEW[n][t], dist[t], iou[t], used[t] = Tm, d, i_, True
        if d < 3.0 and i_ > 0.6:
            prev, prevf = Tm, t
    ok = np.isfinite(dist)
    rec['objects'][n] = dict(frames=T, fitted=int(ok.sum()), dist_med_mm=float(np.nanmedian(dist)) if ok.any() else None,
                             iou_med=float(np.nanmedian(iou)) if ok.any() else None, good=int(((dist < 2.5) & (iou > 0.75)).sum()))
    np.savez_compressed(f'{a.out}/{n}_fit.npz', T_world_body=NEW[n], dist_mm=dist, iou=iou, used=used)
    print(a.ep, n, rec['objects'][n], flush=True)
np.savez(f'{a.out}/poses_world_vo.npz', **NEW)
rec['seconds'] = round(time.time() - t0, 1)
json.dump(rec, open(f'{a.out}/purple.json', 'w'), indent=1)
