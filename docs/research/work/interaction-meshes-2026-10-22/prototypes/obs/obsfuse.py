# Observation-first fusion prototype (scratch, 2026-10-22; repo unchanged). Same inputs and the same per-sample rules
# as pipeline/recon_mesh.py integrate() (table band + per-frame plane refit, below_carve, hand capsules, other tracked
# objects carve but never vote surface), but:
#   - an ROI grid in the object frame (bounds of our own previous mesh + margin) so 2 mm voxels stay cheap;
#   - several truncations accumulated in ONE pass (12 / 6 / 4 mm), so variants differ only in the post-pass;
#   - a free-space counter NF: samples (any label, incl. table/hand/other) whose depth lies more than FREE_M behind
#     the voxel (the ray passed through the voxel) -> 'seen free';
#   - moments of the object's own sdf samples (|sdf| <= 12 mm) -> per-voxel spread = effective noise (depth + pose).
# Inference-legal inputs only: our tracks, our depth, our hands, our own meshes for --others and the ROI.
# Usage: obsfuse.py --obj NAME --out GRID.npz --roi MESH --ep POSES DEPTH HANDS STRIDE OTHERS [--ep ...]
import argparse, json, time, sys
import numpy as np
sys.path.insert(0, '/home/user/v2d-track3/pipeline')
_svd = np.linalg.svd
np.linalg.svd = lambda A, full_matrices=False, **k: _svd(A, full_matrices=False, **k)   # thin SVD (table_plane bug)
import recon_mesh as rm

SP = '/tmp/claude-0/-home-user-v2d-track3/8c892c5e-fd7c-57aa-abef-68d2af098e4f/scratchpad'
TAUS = (0.012, 0.006, 0.004)
p = argparse.ArgumentParser()
p.add_argument('--obj', required=True); p.add_argument('--out', required=True); p.add_argument('--roi', required=True)
p.add_argument('--ep', nargs=5, action='append', metavar=('POSES', 'DEPTH', 'HANDS', 'STRIDE', 'OTHERS'), required=True)
p.add_argument('--voxel', type=float, default=0.002); p.add_argument('--margin', type=float, default=0.04)
p.add_argument('--free_m', type=float, default=0.008)
p.add_argument('--edge_thr', type=float, default=0.02); p.add_argument('--zmax', type=float, default=1.5)
p.add_argument('--table_band', type=float, default=0.015); p.add_argument('--below_carve', type=float, default=0.004)
p.add_argument('--hand_r', type=float, default=0.03); p.add_argument('--arm_r', type=float, default=0.045)
p.add_argument('--arm_len', type=float, default=0.15); p.add_argument('--other_r', type=float, default=0.012)
a = p.parse_args()
t0 = time.time()
import trimesh
from scipy.spatial import cKDTree
K = rm.rectified_K(f'{SP}/loc/t3/calib.json')
mr = trimesh.load(a.roi, force='mesh'); lo = mr.bounds[0] - a.margin; hi = mr.bounds[1] + a.margin
shape = tuple(int(np.ceil((hi[k] - lo[k]) / a.voxel)) for k in range(3))
axes = [lo[k] + (np.arange(shape[k]) + 0.5) * a.voxel for k in range(3)]
X = np.stack(np.meshgrid(*axes, indexing='ij'), -1).reshape(-1, 3)
nv = len(X); print('grid', shape, nv, flush=True)
S = {t: np.zeros(nv, np.float32) for t in TAUS}; W = {t: np.zeros(nv, np.float32) for t in TAUS}
NF = np.zeros(nv, np.float32); NV = np.zeros(nv, np.float32)
M0 = np.zeros(nv, np.float32); M1 = np.zeros(nv, np.float32); M2 = np.zeros(nv, np.float32)
cnt = dict(frames=0, below=0)
for poses, depth, hands, stride, others_s in a.ep:
    stride = int(stride)
    P = np.load(poses); T_co = P[f'cam_T_{a.obj}'].astype(np.float64); W_C = P['world_T_cam'].astype(np.float64)
    segs_t = rm.hand_segments(hands, W_C, a) if hands != '-' else None
    others = []
    if others_s != '-':
        for spec in others_s.split(','):
            nm, path = spec.split('=', 1)
            pts = trimesh.sample.sample_surface(trimesh.load(path, force='mesh'), 20000, seed=0)[0]
            others.append((P[f'cam_T_{nm}'].astype(np.float64), cKDTree(pts), pts.min(0), pts.max(0)))
    D = np.load(depth, mmap_mode='r'); N = min(len(T_co), len(D)); H, Wd = D.shape[1:]
    o0 = (W_C[0] @ T_co[0])[:3, 3]
    nw, cw, frac = rm.table_plane(np.array(D[0], np.float32), K, o0)
    print(poses, 'table', np.round(nw, 3), round(cw, 3), round(frac, 2), flush=True)
    for t in range(0, N, stride):
        R, tr = T_co[t][:3, :3], T_co[t][:3, 3]
        Xc = X @ R.T + tr; z = Xc[:, 2]
        ok = z > 0.05
        u = np.full(nv, -1, np.int64); v = u.copy()
        u[ok] = np.round(K[0, 0] * Xc[ok, 0] / z[ok] + K[0, 2]).astype(np.int64)
        v[ok] = np.round(K[1, 1] * Xc[ok, 1] / z[ok] + K[1, 2]).astype(np.int64)
        ok &= (u >= 0) & (u < Wd) & (v >= 0) & (v < H)
        idx = np.nonzero(ok)[0]
        Dt = np.array(D[t], dtype=np.float32)
        if a.edge_thr >= 0:
            import cv2
            Dz = np.where(np.isfinite(Dt), Dt, 0).astype(np.float32); k5 = np.ones((5, 5), np.uint8)
            Dt[(cv2.dilate(Dz, k5) - cv2.erode(Dz, k5)) > a.edge_thr] = np.nan
        d = Dt[v[idx], u[idx]]
        good = np.isfinite(d) & (d > 0.05) & (d < a.zmax)
        idx, d = idx[good], d[good]
        sdf = d - z[idx]
        keep = sdf > -max(TAUS)
        idx, sdf, d = idx[keep], sdf[keep], d[keep]
        Pd = Xc[idx] * (d / z[idx])[:, None]
        other = np.zeros(len(idx), bool)
        C_W = np.linalg.inv(W_C[t]); nc = C_W[:3, :3] @ nw; cc = cw - nc @ C_W[:3, 3]
        for thr in (0.03, 0.012):
            hgt = Pd @ nc + cc; sel = np.abs(hgt) < thr
            if sel.sum() < 500:
                break
            Q = Pd[sel][:: max(1, int(sel.sum()) // 20000)]; q0 = Q.mean(0)
            nn = _svd(Q - q0, full_matrices=False)[2][2]
            if nn @ nc < 0:
                nn = -nn
            if nn @ nc > np.cos(np.radians(10)):
                nc, cc = nn, -nn @ q0
        other |= Pd @ nc + cc <= a.table_band
        if a.below_carve >= 0:
            fb = np.nonzero(Xc @ nc + cc < -a.below_carve)[0]
            for tau in TAUS:
                S[tau][fb] += 1.0; W[tau][fb] += 1
            cnt['below'] += len(fb)
        if segs_t is not None and len(segs_t[t][0]):
            A0, B0, rad = segs_t[t]
            lo_ = np.minimum(A0, B0).min(0) - rad.max(); hi_ = np.maximum(A0, B0).max(0) + rad.max()
            near = np.nonzero(np.all((Pd >= lo_) & (Pd <= hi_), axis=1))[0]
            Q = Pd[near]; hq = np.zeros(len(near), bool)
            for s in range(len(A0)):
                ab = B0[s] - A0[s]; ap = Q - A0[s]
                h = np.clip(ap @ ab / max(ab @ ab, 1e-12), 0, 1)
                hq |= np.linalg.norm(ap - h[:, None] * ab, axis=1) <= rad[s]
            other[near[hq]] = True
        for T_oo, tree, olo, ohi in others:
            Ti = np.linalg.inv(T_oo[t]); Po = Pd @ Ti[:3, :3].T + Ti[:3, 3]
            near = np.nonzero(np.all((Po >= olo - a.other_r) & (Po <= ohi + a.other_r), axis=1))[0]
            if len(near):
                od = tree.query(Po[near], k=1, distance_upper_bound=a.other_r)[0] <= a.other_r
                other[near[od]] = True
        for tau in TAUS:
            m = (sdf > -tau) & (~other | (sdf > tau))
            ii = idx[m]; S[tau][ii] += np.clip(sdf[m] / tau, -1, 1); W[tau][ii] += 1
        fr = sdf > a.free_m
        NF[idx[fr]] += 1; NV[idx] += 1
        own = ~other & (np.abs(sdf) <= 0.012)
        ii = idx[own]; M0[ii] += 1; M1[ii] += sdf[own]; M2[ii] += sdf[own] ** 2
        cnt['frames'] += 1
    print(poses, 'done', cnt, round(time.time() - t0), 's', flush=True)
np.savez_compressed(a.out, shape=np.array(shape), lo=lo, voxel=a.voxel,
                    **{f'S{int(t * 1000)}': S[t].reshape(shape) for t in TAUS}, **{f'W{int(t * 1000)}': W[t].reshape(shape) for t in TAUS},
                    NF=NF.reshape(shape), NV=NV.reshape(shape), M0=M0.reshape(shape), M1=M1.reshape(shape), M2=M2.reshape(shape),
                    args=json.dumps(vars(a)), cnt=json.dumps(cnt))
print('saved', a.out, round(time.time() - t0), 's', flush=True)
