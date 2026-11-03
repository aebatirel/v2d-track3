"""Pot network inference on a public episode (GT-free: reads frames, the stereo-depth cache and the CONTROL track only).

Usage: python infer.py EP CKPT OUT [--depth /content/cache/depth/epN/depths_fs0.5.npy] [--control DIR] [--split public]
Writes OUT/poses_world_vo_{N,NP,NS,NT}.npz (every object; the pot replaced, others = control),
OUT/cam_pot_{V}.npy and OUT/diag.json (per-frame inliers, fallbacks), OUT/vis_ep{EP}.jpg (a few overlays).
Variants (PREREG.md): N = RANSAC Kabsch on predicted XYZ vs depth (primary); NP = PnP (no depth); NS = N smoothed
+-2 frames; NT = track x windowed (+-15) robust mean of track^-1 . N.
"""
import argparse, json, os, sys, time
import numpy as np, cv2, torch
from scipy.spatial.transform import Rotation as Rot
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common as C
from model import PotNet

p = argparse.ArgumentParser()
p.add_argument('ep', type=int); p.add_argument('ckpt'); p.add_argument('out')
p.add_argument('--depth', default=None)
p.add_argument('--control', default=os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                                 '../../docs/analysis/ipose-20261103/control'))
p.add_argument('--split', default='public'); p.add_argument('--obj', default='white_pot')
p.add_argument('--mesh', default=f'{os.path.dirname(os.path.abspath(__file__))}/../../meshes/ipose/white_pot.glb')
p.add_argument('--selftest', action='store_true', help='replace the network output by a render of the control pose (checks the geometry path)')
p.add_argument('--min_inl', type=int, default=25); p.add_argument('--thr', type=float, default=0.01)
a = p.parse_args()
os.makedirs(a.out, exist_ok=True)
dev = 'cuda' if torch.cuda.is_available() else 'cpu'
rng = np.random.default_rng(a.ep)
ck = torch.load(a.ckpt, map_location=dev, weights_only=False)
net = PotNet(pretrained=False).to(dev).eval(); net.load_state_dict(ck['model'])
CEN, HALF = ck['cen'], ck['half']
CP = np.load(f'{a.control}/ep{a.ep}_poses.npz'); CW = np.load(f'{a.control}/ep{a.ep}_poses_world_vo.npz')
Ttr, WTC = CP[f'cam_T_{a.obj}'], CP['world_T_cam']
N = len(Ttr)
_, K = C.rectification()
pts, _, _, _ = C.load_points(a.mesh, 30000)
sub = pts[::10]
if a.selftest:
    ST = C.Splat(*C.load_points(a.mesh, 300000)[:3])
F = C.rect_left_frames(a.ep, a.split)
D = np.load(a.depth or f'/content/cache/depth/ep{a.ep}/depths_fs0.5.npy', mmap_mode='r')
assert len(D) >= N and len(F) >= N, (len(D), len(F), N)
print('ep', a.ep, 'frames', N, 'depth', D.shape, D.dtype, 'median depth', float(np.median(D[0][D[0] > 0])), flush=True)

grid = np.arange(64) * 4 + 1                                   # crop pixel of each 64-grid cell (training: x[1::4])


def kabsch_batch(A, B):                                        # A, B: (h, 3, 3)
    ca, cb = A.mean(1, keepdims=True), B.mean(1, keepdims=True)
    H = np.einsum('hni,hnj->hij', A - ca, B - cb)
    U, S, Vt = np.linalg.svd(H)
    d = np.sign(np.linalg.det(np.einsum('hji,hkj->hik', Vt, U)))
    Dm = np.tile(np.eye(3), (len(A), 1, 1)); Dm[:, 2, 2] = d
    R = np.einsum('hji,hjk,hlk->hil', Vt, Dm, U)
    return R, cb[:, 0] - np.einsum('hij,hj->hi', R, ca[:, 0])


def solve_depth(obj, cam):
    n = len(obj)
    if n < a.min_inl: return None, 0
    idx = rng.integers(n, size=(512, 3))
    R, t = kabsch_batch(obj[idx], cam[idx])
    res = np.linalg.norm(np.einsum('hij,nj->hni', R, obj) + t[:, None] - cam[None], axis=-1)
    inl = (res < a.thr).sum(1); b = int(np.argmax(inl))
    m = res[b] < a.thr
    for _ in range(3):
        if m.sum() < 3: return None, 0
        Rb, tb = C.kabsch(obj[m], cam[m])
        m = np.linalg.norm(obj @ Rb.T + tb - cam, axis=1) < a.thr
    if m.sum() < a.min_inl: return None, int(m.sum())
    return C.se3(Rb, tb), int(m.sum())


def solve_pnp(obj, uv, side):
    if len(obj) < a.min_inl: return None, 0
    ok, rv, tv, inl = cv2.solvePnPRansac(obj.astype(np.float64), uv.astype(np.float64), K, None,
                                         reprojectionError=max(2.0, 3.0 * side / 256), iterationsCount=300,
                                         flags=cv2.SOLVEPNP_EPNP)
    if not ok or inl is None or len(inl) < a.min_inl: return None, 0 if inl is None else len(inl)
    i = inl[:, 0]
    rv, tv = cv2.solvePnPRefineLM(obj[i].astype(np.float64), uv[i].astype(np.float64), K, None, rv, tv)
    return C.se3(cv2.Rodrigues(rv)[0], tv[:, 0]), len(i)


TN, TP = np.repeat(Ttr[:, None], 1, 1)[:, 0].copy(), Ttr.copy()
diag = dict(inl_N=[], inl_P=[], fb_N=[], fb_P=[], mask_px=[], vis_mean=[])
vis_frames, t0, B = {0, N // 3, 2 * N // 3, N - 1}, time.time(), 32
ov = []
for s in range(0, N, B):
    ids = list(range(s, min(N, s + B))); rois, crops = [], []
    for i in ids:
        cx, cy, side = C.roi_from_pose(K, Ttr[i], sub, 1.3)
        rois.append((cx, cy, side)); crops.append(C.crop_image(F[i], cx, cy, side, 256))
    g = torch.from_numpy(np.stack(crops)[:, None].astype(np.float32) / 255).to(dev)
    with torch.no_grad():
        lv, lf, px = net(g)
    pv = torch.sigmoid(lv).cpu().numpy(); X = px.float().cpu().numpy().transpose(0, 2, 3, 1) * HALF + CEN
    if a.selftest:
        for j, i in enumerate(ids):
            r = ST.render(C.crop_K(K, *rois[j], 256), Ttr[i], 256, 256)
            pv[j] = r['mask'][1::4, 1::4].astype(np.float32); X[j] = r['xyz'][1::4, 1::4]
    for j, i in enumerate(ids):
        cx, cy, side = rois[j]; sc = 256 / side
        m = pv[j] > 0.5
        yy, xx = np.nonzero(m)
        u = (grid[xx] + 0.5 * (1 - sc)) / sc + cx - side / 2      # crop pixel -> full image pixel
        v = (grid[yy] + 0.5 * (1 - sc)) / sc + cy - side / 2
        obj = X[j][yy, xx]
        ui, vi = np.round(u).astype(int), np.round(v).astype(int)
        inside = (ui >= 0) & (ui < C.RSZ[0]) & (vi >= 0) & (vi < C.RSZ[1])
        z = np.zeros(len(u)); z[inside] = D[i][vi[inside], ui[inside]]
        okz = inside & np.isfinite(z) & (z > 0.1) & (z < 3.0)
        cam = np.c_[(u - K[0, 2]) * z / K[0, 0], (v - K[1, 2]) * z / K[1, 1], z]
        Tn, ni = solve_depth(obj[okz], cam[okz])
        Tp, npi = solve_pnp(obj[inside], np.c_[u, v][inside], side)
        diag['inl_N'].append(ni); diag['inl_P'].append(npi); diag['mask_px'].append(int(m.sum()))
        diag['fb_N'].append(Tn is None); diag['fb_P'].append(Tp is None)
        if Tn is not None: TN[i] = Tn
        if Tp is not None: TP[i] = Tp
        if i in vis_frames:
            Kc = C.crop_K(K, cx, cy, side, 256)
            img = cv2.cvtColor(crops[j], cv2.COLOR_GRAY2BGR)
            for T, col in ((Ttr[i], (0, 255, 0)), (TN[i], (0, 0, 255))):
                uv, _ = C.project(Kc, T, sub[::3])
                for q in uv.astype(int):
                    if 0 <= q[0] < 256 and 0 <= q[1] < 256: img[q[1], q[0]] = col
            pm = cv2.resize((pv[j] * 255).astype(np.uint8), (256, 256), interpolation=cv2.INTER_NEAREST)
            ov.append(np.hstack([img, cv2.cvtColor(pm, cv2.COLOR_GRAY2BGR)]))
    print(f'{ids[-1] + 1}/{N} {time.time() - t0:.0f}s fbN {sum(diag["fb_N"])} fbP {sum(diag["fb_P"])}', flush=True)


def chordal_mean(Rs):
    U, _, Vt = np.linalg.svd(np.sum(Rs, 0))
    R = U @ Vt
    if np.linalg.det(R) < 0: U[:, -1] *= -1; R = U @ Vt
    return R


def smooth(Ts, w, valid=None):
    out = Ts.copy()
    for i in range(len(Ts)):
        sl = [k for k in range(max(0, i - w), min(len(Ts), i + w + 1)) if valid is None or valid[k]]
        if not sl: continue
        out[i] = C.se3(chordal_mean(Ts[sl, :3, :3]), np.median(Ts[sl, :3, 3], 0))
    return out


validN = ~np.array(diag['fb_N'])
TS = smooth(TN, 2)
Dl = np.stack([np.linalg.inv(Ttr[i]) @ TN[i] for i in range(N)])
Dbar = smooth(Dl, 15, validN)
TT = np.stack([Ttr[i] @ (Dbar[i] if validN[max(0, i - 15):i + 16].any() else np.eye(4)) for i in range(N)])
for V, Tc in (('N', TN), ('NP', TP), ('NS', TS), ('NT', TT)):
    W = {k: CW[k] for k in CW.files}
    W[a.obj] = np.stack([WTC[i] @ Tc[i] for i in range(N)])
    np.savez(f'{a.out}/poses_world_vo_{V}.npz', **W)
    np.save(f'{a.out}/cam_pot_{V}.npy', Tc)
dt = np.linalg.norm(TN[:, :3, 3] - Ttr[:, :3, 3], axis=1) * 100
dr = np.degrees([Rot.from_matrix(TN[i, :3, :3] @ Ttr[i, :3, :3].T).magnitude() for i in range(N)])
summ = dict(ep=a.ep, ckpt=a.ckpt, frames=N, fallback_N=int(sum(diag['fb_N'])), fallback_P=int(sum(diag['fb_P'])),
            median_inl_N=float(np.median(diag['inl_N'])), N_vs_track_cm_median=float(np.median(dt[validN])) if validN.any() else None,
            N_vs_track_deg_median=float(np.median(dr[validN])) if validN.any() else None, secs=round(time.time() - t0))
print(json.dumps(summ), flush=True)
json.dump(dict(summary=summ, **diag), open(f'{a.out}/diag.json', 'w'))
if ov: cv2.imwrite(f'{a.out}/vis_ep{a.ep}.jpg', np.vstack(ov))
