"""Observed surface points of one object in its body frame, from our stereo depth along our own track (no GT).

Unlike recon_mesh.py (TSDF -> binary solid -> blur -> marching cubes), this keeps the raw depth samples, so a 3 mm
wall seen from both sides stays two thin layers instead of averaging into one thick slab. Per frame t (stride S):
  - depth pixels inside the projected ROI box are back-projected (rectified-left K) and moved into the object frame
    with inv(cam_T_obj[t]); the depth-edge filter of recon_mesh.py drops flying pixels;
  - samples on the table band (per-frame refit of the frame-0 RANSAC plane), on hand/forearm capsules (MediaPipe
    joints, hands.npz) or within OTHER_R of another tracked object are dropped;
  - a coarse voxel grid (VOX) counts, per voxel, frames that saw it on the surface (|sdf| < HIT) and frames that saw
    through it (sdf > FREE): anything not rigidly attached to the object (hands that held it, table, other objects
    once it moved) is seen through from other views.
Kept: samples whose voxel has >= MIN_HITS hit-frames and hit / (hit + free) >= MIN_RATIO.
Output npz: pts (N,3) object frame, cam (N,3) camera centre in the object frame (for normal orientation), frame (N,).
Usage: obs_points.py --poses P.npz --depth D.npy --hands H.npz --calib calib.json --obj NAME --roi ROI.glb --out O.npz
       [--others NAME=MESH,...] [--stride 2]
C0b (PREREG cdo-sprint/C0b 3.4): --roi_cube 0.30 instead of --roi; --others_pts NAME=NPZ,... instead of --others.
The ROI mesh only sets the box (bounds + margin); any mesh of ours or a box size works.
"""
import argparse, json, os, sys, time
import numpy as np
import cv2
import trimesh

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.abspath(os.path.join(HERE, '..', '..', '..', '..', 'pipeline')))
from recon_mesh import rectified_K, hand_segments, table_plane  # noqa: E402


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--poses', required=True); p.add_argument('--depth', required=True)
    p.add_argument('--hands', default=None); p.add_argument('--calib', required=True)
    p.add_argument('--obj', required=True); p.add_argument('--roi', default=None); p.add_argument('--out', required=True)
    p.add_argument('--others', default=''); p.add_argument('--other_r', type=float, default=0.012)
    # C0b options (PREREG cdo-sprint/C0b section 3.4); unset = the behaviour above, byte for byte
    p.add_argument('--roi_cube', type=float, default=None,
                   help='C0b: ROI = cube of this half-side (m) about the track-frame origin, no margin (replaces --roi)')
    p.add_argument('--others_pts', default='',
                   help='C0b: NAME=NPZ,... co-object surface = 20,000 random points (seed 0) of its own observed '
                        'points (an obs_points npz), posed by its track (replaces --others library meshes)')
    p.add_argument('--stride', type=int, default=2); p.add_argument('--margin', type=float, default=0.02)
    p.add_argument('--edge_thr', type=float, default=0.02); p.add_argument('--zmax', type=float, default=1.5)
    p.add_argument('--table_band', type=float, default=0.008)
    p.add_argument('--hand_r', type=float, default=0.03); p.add_argument('--arm_r', type=float, default=0.045)
    p.add_argument('--arm_len', type=float, default=0.15)
    p.add_argument('--vox', type=float, default=0.004); p.add_argument('--hit', type=float, default=0.004)
    p.add_argument('--free', type=float, default=0.010)
    p.add_argument('--min_hits', type=int, default=3); p.add_argument('--min_ratio', type=float, default=0.5)
    p.add_argument('--pix_stride', type=int, default=1)
    a = p.parse_args()
    if (a.roi is None) == (a.roi_cube is None):
        p.error('exactly one of --roi / --roi_cube')
    if a.others and a.others_pts:
        p.error('--others and --others_pts are exclusive')
    t0 = time.time()
    K = rectified_K(a.calib)
    P = np.load(a.poses); T_co = P[f'cam_T_{a.obj}'].astype(np.float64); W_C = P['world_T_cam'].astype(np.float64)
    D = np.load(a.depth, mmap_mode='r'); N = min(len(T_co), len(D)); H, W = D.shape[1:]
    segs = hand_segments(a.hands, W_C, a) if a.hands else None
    others = []
    if a.others:
        from scipy.spatial import cKDTree
        for spec in a.others.split(','):
            nm, path = spec.split('=', 1)
            pts = trimesh.sample.sample_surface(trimesh.load(path, force='mesh'), 20000, seed=0)[0]
            others.append((P[f'cam_T_{nm}'].astype(np.float64), cKDTree(pts), pts.min(0), pts.max(0)))
    if a.others_pts:
        from scipy.spatial import cKDTree
        for spec in a.others_pts.split(','):
            nm, path = spec.split('=', 1)
            Q = np.load(path)['pts'].astype(np.float64)
            pts = Q[np.random.default_rng(0).choice(len(Q), min(20000, len(Q)), replace=False)]
            others.append((P[f'cam_T_{nm}'].astype(np.float64), cKDTree(pts), pts.min(0), pts.max(0)))
    if a.roi_cube is not None:
        lo = np.full(3, -float(a.roi_cube)); hi = np.full(3, float(a.roi_cube))
    else:
        roi = trimesh.load(a.roi, force='mesh'); lo = roi.bounds[0] - a.margin; hi = roi.bounds[1] + a.margin
    corners = np.array([[x, y, z] for x in (lo[0], hi[0]) for y in (lo[1], hi[1]) for z in (lo[2], hi[2])])
    shape = np.ceil((hi - lo) / a.vox).astype(int)
    axes = [lo[k] + (np.arange(shape[k]) + 0.5) * a.vox for k in range(3)]
    X = np.stack(np.meshgrid(*axes, indexing='ij'), -1).reshape(-1, 3)
    hits = np.zeros(len(X), np.int32); free = np.zeros(len(X), np.int32)
    o0 = (W_C[0] @ T_co[0])[:3, 3]
    nw, cw, _ = table_plane(np.array(D[0], np.float32), K, o0)
    k5 = np.ones((5, 5), np.uint8)
    keep_pts, keep_cam, keep_fr = [], [], []
    for t in range(0, N, a.stride):
        T = T_co[t]; Ti = np.linalg.inv(T)
        Dt = np.array(D[t], dtype=np.float32)
        Dz = np.where(np.isfinite(Dt), Dt, 0).astype(np.float32)
        Dt[(cv2.dilate(Dz, k5) - cv2.erode(Dz, k5)) > a.edge_thr] = np.nan
        # table plane in this camera (frame-0 plane moved by VO, refit to nearby samples, <= 10 deg correction)
        C_W = np.linalg.inv(W_C[t]); nc = C_W[:3, :3] @ nw; cc = cw - nc @ C_W[:3, 3]
        # ---- samples in the ROI box
        Cc = corners @ T[:3, :3].T + T[:3, 3]
        if (Cc[:, 2] < 0.05).any():
            if a.roi_cube is None:
                continue
            # C0b cube ROI: a 0.6 m cube about the object has corners behind / beside the camera in most frames, so
            # its projected box is undefined; use the whole image (the 3-D cube test below still bounds the points)
            u0, u1, v0, v1 = 0, W - 1, 0, H - 1
        else:
            u = K[0, 0] * Cc[:, 0] / Cc[:, 2] + K[0, 2]; v = K[1, 1] * Cc[:, 1] / Cc[:, 2] + K[1, 2]
            u0, u1 = int(max(0, np.floor(u.min()))), int(min(W - 1, np.ceil(u.max())))
            v0, v1 = int(max(0, np.floor(v.min()))), int(min(H - 1, np.ceil(v.max())))
        if u1 <= u0 or v1 <= v0:
            continue
        vv, uu = np.mgrid[v0:v1 + 1:a.pix_stride, u0:u1 + 1:a.pix_stride]
        d = Dt[vv, uu]
        ok = np.isfinite(d) & (d > 0.05) & (d < a.zmax)
        uu, vv, d = uu[ok], vv[ok], d[ok]
        Pc = np.stack([(uu - K[0, 2]) * d / K[0, 0], (vv - K[1, 2]) * d / K[1, 1], d], 1).astype(np.float64)
        for thr in (0.03, 0.012):
            hgt = Pc @ nc + cc; sel = np.abs(hgt) < thr
            if sel.sum() < 500:
                break
            Q = Pc[sel][:: max(1, int(sel.sum()) // 20000)]; q0 = Q.mean(0)
            nn = np.linalg.svd(Q - q0, full_matrices=False)[2][2]
            if nn @ nc < 0:
                nn = -nn
            if nn @ nc > np.cos(np.radians(10)):
                nc, cc = nn, -nn @ q0
        Po = Pc @ Ti[:3, :3].T + Ti[:3, 3]
        inroi = np.all((Po >= lo) & (Po <= hi), axis=1)
        bad = (Pc @ nc + cc) <= a.table_band
        if segs is not None and len(segs[t][0]):
            A0, B0, rad = segs[t]
            for s in range(len(A0)):
                ab = B0[s] - A0[s]; ap = Pc - A0[s]
                h = np.clip(ap @ ab / max(ab @ ab, 1e-12), 0, 1)
                bad |= np.linalg.norm(ap - h[:, None] * ab, axis=1) <= rad[s]
        for T_oo, tree, olo, ohi in others:
            Tj = np.linalg.inv(T_oo[t]); Pq = Pc @ Tj[:3, :3].T + Tj[:3, 3]
            near = np.nonzero(np.all((Pq >= olo - a.other_r) & (Pq <= ohi + a.other_r), axis=1))[0]
            if len(near):
                bad[near[tree.query(Pq[near], k=1, distance_upper_bound=a.other_r)[0] <= a.other_r]] = True
        sel = inroi & ~bad
        keep_pts.append(Po[sel].astype(np.float32)); keep_fr.append(np.full(int(sel.sum()), t, np.int32))
        keep_cam.append(np.repeat(Ti[:3, 3][None].astype(np.float32), int(sel.sum()), 0))
        # ---- free-space / hit votes on the voxel grid (all depth, including hands: they carve, never vote surface)
        Xc = X @ T[:3, :3].T + T[:3, 3]; z = Xc[:, 2]
        okv = z > 0.05
        pu = np.full(len(X), -1, np.int64); pv = pu.copy()
        pu[okv] = np.round(K[0, 0] * Xc[okv, 0] / z[okv] + K[0, 2]).astype(np.int64)
        pv[okv] = np.round(K[1, 1] * Xc[okv, 1] / z[okv] + K[1, 2]).astype(np.int64)
        okv &= (pu >= 0) & (pu < W) & (pv >= 0) & (pv < H)
        idx = np.nonzero(okv)[0]
        dv = Dt[pv[idx], pu[idx]]
        good = np.isfinite(dv) & (dv > 0.05)
        idx, dv = idx[good], dv[good]
        sdf = dv - z[idx]
        free[idx[sdf > a.free]] += 1
        # a voxel 'hits' only on samples that survived the table/hand/other filters: test the observed point
        Pd = Xc[idx] * (dv / z[idx])[:, None]
        badv = (Pd @ nc + cc) <= a.table_band
        if segs is not None and len(segs[t][0]):
            A0, B0, rad = segs[t]
            for s in range(len(A0)):
                ab = B0[s] - A0[s]; ap = Pd - A0[s]
                h = np.clip(ap @ ab / max(ab @ ab, 1e-12), 0, 1)
                badv |= np.linalg.norm(ap - h[:, None] * ab, axis=1) <= rad[s]
        hits[idx[(np.abs(sdf) < a.hit) & ~badv]] += 1
    pts = np.concatenate(keep_pts); cam = np.concatenate(keep_cam); fr = np.concatenate(keep_fr)
    vi = np.floor((pts - lo) / a.vox).astype(int); vi = np.clip(vi, 0, shape - 1)
    lin = (vi[:, 0] * shape[1] + vi[:, 1]) * shape[2] + vi[:, 2]
    h, f = hits[lin], free[lin]
    ok = (h >= a.min_hits) & (h >= a.min_ratio * (h + f))
    np.savez_compressed(a.out, pts=pts[ok], cam=cam[ok], frame=fr[ok], lo=lo, hi=hi, vox=a.vox,
                        hits=hits.reshape(shape), free=free.reshape(shape), args=json.dumps(_args_record(a)))
    print(json.dumps(dict(obj=a.obj, frames=int(len(range(0, N, a.stride))), raw=int(len(pts)), kept=int(ok.sum()),
                          sec=round(time.time() - t0, 1))))


def _args_record(a):
    """vars(a) as before; the C0b options appear only when used (old command lines record the same args)."""
    d = vars(a).copy()
    for k in ('roi_cube', 'others_pts'):
        if not d.get(k):
            d.pop(k, None)
    return d


if __name__ == '__main__':
    main()
