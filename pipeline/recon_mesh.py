"""Reconstruct one object's mesh from our stereo depth along our own tracked poses (inference only, no ground truth).

v0 (2026-10-21), a hypothesis under test (H1 in docs/work-log.md): dense TSDF fusion in the OBJECT frame.
  For every frame t, each voxel v of a cube around the object origin is projected with cam_T_obj[t] into the
  rectified-left depth map D_t. sdf = D_t(u) - z_v. Voxels behind the observed surface by more than TRUNC are not
  updated (occluded); all others take a running average of clip(sdf / TRUNC, -1, 1), so free-space observations
  (sdf > TRUNC) erase anything that is not rigidly attached to the object (hands, table, other objects once the object
  moves). The surface is the zero level set of the averaged field over voxels with enough observations.
  Closing: voxels never observed are 'unknown'. --close fill turns unknown voxels enclosed by observed-inside voxels
  into inside (scipy binary_fill_holes on inside | unknown-and-enclosed) so the mesh is watertight; the remaining
  holes are capped by marching cubes on the padded grid.
  Output: the mesh in the object's body frame (= the frame of the poses), metres, decimated with the kit's
  budget_mesh if the kit is present (<= 4096 faces / 4096 vertices), as .glb plus a .json of statistics.
Usage: python recon_mesh.py --poses poses.npz --depth depths_fs0.5.npy --calib calib.json --obj NAME --out mesh.glb
"""
import argparse, json, os, sys, time
import numpy as np


def rectified_K(calib_path):
    import cv2
    C = json.load(open(calib_path)); cam = C['cameras']
    sp = [p for p in C['stereo_pairs'] if p['camera'] == 'ego'][0]
    K_ = lambda n: np.array(cam[n]['intrinsic_matrix'], float)  # noqa: E731
    D_ = lambda n: np.array(cam[n]['distortion_coefficients'], float)  # noqa: E731
    E = np.array(sp['left_to_right'], float)
    R1, R2, P1, P2, Q, _, _ = cv2.stereoRectify(K_('ego_cam_c'), D_('ego_cam_c'), K_('ego_cam_b'), D_('ego_cam_b'),
                                                (1280, 800), E[:3, :3].copy(), E[:3, 3].reshape(3, 1).copy(),
                                                alpha=0, newImageSize=(1600, 1000), flags=cv2.CALIB_ZERO_DISPARITY)
    return P1[:3, :3].copy()


BONES = [(0, 1), (1, 2), (2, 3), (3, 4), (0, 5), (5, 6), (6, 7), (7, 8), (5, 9), (9, 10), (10, 11), (11, 12),
         (9, 13), (13, 14), (14, 15), (15, 16), (13, 17), (0, 17), (17, 18), (18, 19), (19, 20)]   # MediaPipe hand


def hand_segments(path, W_C, a):
    """Per frame: (A, B, radius) segment arrays in that frame's camera coordinates; hand bones plus a forearm segment
    from the wrist away from the middle-finger knuckle (MediaPipe has no forearm)."""
    H = np.load(path)
    out = []
    for t in range(len(W_C)):
        C_W = np.linalg.inv(W_C[t]); A, B, r = [], [], []
        for side in ('left', 'right'):
            if t >= len(H[f'valid_{side}']) or not H[f'valid_{side}'][t]:
                continue
            J = H[f'joints_{side}'][t].astype(np.float64) @ C_W[:3, :3].T + C_W[:3, 3]
            if not np.all(np.isfinite(J)):
                continue
            for i, j in BONES:
                A.append(J[i]); B.append(J[j]); r.append(a.hand_r)
            d = J[0] - J[9]; d /= max(np.linalg.norm(d), 1e-9)
            A.append(J[0]); B.append(J[0] + a.arm_len * d); r.append(a.arm_r)
        out.append((np.array(A).reshape(-1, 3), np.array(B).reshape(-1, 3), np.array(r)))
    return out


def table_plane(D0, K, obj_pos, rng_seed=0, thr=0.006, iters=1500, hmin=-0.05, hmax=0.30, cone=65):
    """Support plane in frame 0 (camera = world at frame 0): RANSAC over depth points; candidate planes must have a
    normal within CONE deg of camera 'up' (-y) and lie under the object origin by HMIN..HMAX (the floor, ~1 m down, is
    otherwise the largest plane: the 2026-10-20 mkref bug). Returns (n, c, inlier frac) with n.x + c = 0, n up.
    CONE was 45 until 2026-10-21: the table normal is 48-50 deg from camera up in ep39/ep40 (steeper camera), the real
    table was rejected, a wrong plane was used and table pixels under the dust pan fused into a 3.5 cm slab."""
    H, W = D0.shape
    vv, uu = np.mgrid[0:H:4, 0:W:4]
    d = np.asarray(D0)[vv, uu]
    ok = np.isfinite(d) & (d > 0.2) & (d < 1.5)
    Pts = np.stack([(uu[ok] - K[0, 2]) * d[ok] / K[0, 0], (vv[ok] - K[1, 2]) * d[ok] / K[1, 1], d[ok]], 1)
    rng = np.random.default_rng(rng_seed); best = (0, None)
    for _ in range(iters):
        s = Pts[rng.choice(len(Pts), 3, replace=False)]
        nrm = np.cross(s[1] - s[0], s[2] - s[0]); ln = np.linalg.norm(nrm)
        if ln < 1e-9:
            continue
        nrm /= ln
        if nrm[1] > 0:
            nrm = -nrm
        if -nrm[1] < np.cos(np.radians(cone)):
            continue
        c = -nrm @ s[0]
        if not hmin <= nrm @ obj_pos + c <= hmax:
            continue
        inl = np.abs(Pts @ nrm + c) < thr
        if inl.sum() > best[0]:
            best = (int(inl.sum()), (nrm, c, inl))
    if best[1] is None:
        raise SystemExit('no support plane under the object')
    nrm, c, inl = best[1]
    Q = Pts[inl]; q0 = Q.mean(0); _, _, Vt = np.linalg.svd(Q - q0)       # least-squares refit
    nrm = Vt[2] if Vt[2][1] < 0 else -Vt[2]
    return nrm, -nrm @ q0, int(inl.sum()) / len(Pts)


def integrate(a, K, X, tsdf, wgt, poses, depth, hands, others_spec, cnt):
    """Fuse one episode (its poses.npz, depth cache, hands.npz, other objects) into the shared grid."""
    P = np.load(poses); T_co = P[f'cam_T_{a.obj}'].astype(np.float64)
    W_C = P['world_T_cam'].astype(np.float64)
    segs_t = hand_segments(hands, W_C, a) if hands else None
    others = []                                                    # (cam_T_other per frame, KD-tree of surface pts)
    if others_spec:
        import trimesh
        from scipy.spatial import cKDTree
        for spec in others_spec.split(','):
            nm, path = spec.split('=', 1)
            pts = trimesh.sample.sample_surface(trimesh.load(path, force='mesh'), 20000, seed=0)[0]
            others.append((P[f'cam_T_{nm}'].astype(np.float64), cKDTree(pts), pts.min(0), pts.max(0)))
    nother = 0
    D = np.load(depth, mmap_mode='r'); N = min(len(T_co), len(D)); H, W = D.shape[1:]
    plane = None
    if a.table_band >= 0:
        o0 = (W_C[0] @ T_co[0])[:3, 3]                             # world = rectified-left camera at frame 0
        nw, cw, frac = table_plane(D[0], K, o0)
        plane = (nw, cw)
        print(f'table plane n={np.round(nw, 3)} c={cw:.3f} inlier frac {frac:.2f} object origin height '
              f'{nw @ o0 + cw:.3f}', flush=True)
    ntable = 0
    nhand = 0
    for t in range(0, N, a.stride):
        R, tr = T_co[t][:3, :3], T_co[t][:3, 3]
        Xc = X @ R.T + tr; z = Xc[:, 2]
        ok = z > 0.05
        u = np.full(len(X), -1, np.int64); v = u.copy()
        u[ok] = np.round(K[0, 0] * Xc[ok, 0] / z[ok] + K[0, 2]).astype(np.int64)
        v[ok] = np.round(K[1, 1] * Xc[ok, 1] / z[ok] + K[1, 2]).astype(np.int64)
        ok &= (u >= 0) & (u < W) & (v >= 0) & (v < H)
        idx = np.nonzero(ok)[0]
        Dt = np.array(D[t], dtype=np.float32)
        if a.edge_thr >= 0:                                        # flying pixels between foreground and background
            import cv2
            Dz = np.where(np.isfinite(Dt), Dt, 0).astype(np.float32); k5 = np.ones((5, 5), np.uint8)
            Dt[(cv2.dilate(Dz, k5) - cv2.erode(Dz, k5)) > a.edge_thr] = np.nan
        d = Dt[v[idx], u[idx]]
        good = np.isfinite(d) & (d > 0.05) & (d < a.zmax)
        idx, d = idx[good], d[good]
        sdf = d - z[idx]
        keep = sdf > -a.trunc
        idx, sdf, d = idx[keep], sdf[keep], d[keep]
        # samples that hit the table or a hand still carve the free space in front of them (sdf > TRUNC) but never
        # vote for a surface (a first version dropped them entirely and lost the carving: ep41 AUC 0.71)
        Pd = Xc[idx] * (d / z[idx])[:, None]                       # the observed surface point on this voxel's ray
        other = np.zeros(len(idx), bool)
        if plane is not None:
            # the frame-0 plane moved into this camera by VO, then re-fitted to this frame's samples near it (VO drift
            # and a slightly tilted global fit left table patches as surfaces: ep39)
            C_W = np.linalg.inv(W_C[t]); nc = C_W[:3, :3] @ plane[0]; cc = plane[1] - nc @ C_W[:3, 3]
            for thr in (0.03, 0.012):
                hgt = Pd @ nc + cc; sel = np.abs(hgt) < thr
                if sel.sum() < 500:
                    break
                Q = Pd[sel][:: max(1, int(sel.sum()) // 20000)]; q0 = Q.mean(0)
                nn = np.linalg.svd(Q - q0, full_matrices=False)[2][2]
                if nn @ nc < 0:
                    nn = -nn
                if nn @ nc > np.cos(np.radians(10)):              # accept only a small correction
                    nc, cc = nn, -nn @ q0
            tb = Pd @ nc + cc <= a.table_band
            other |= tb; ntable += int((tb & (sdf <= a.trunc)).sum())
        if segs_t is not None and len(segs_t[t][0]):
            A0, B0, rad = segs_t[t]
            hd = np.zeros(len(idx), bool)
            lo = np.minimum(A0, B0).min(0) - rad.max(); hi = np.maximum(A0, B0).max(0) + rad.max()
            near = np.nonzero(np.all((Pd >= lo) & (Pd <= hi), axis=1))[0]   # only samples in the hands' box
            Q = Pd[near]; hq = np.zeros(len(near), bool)
            for s in range(len(A0)):                               # point-to-segment distance, one bone at a time
                ab = B0[s] - A0[s]; ap = Q - A0[s]
                h = np.clip(ap @ ab / max(ab @ ab, 1e-12), 0, 1)
                hq |= np.linalg.norm(ap - h[:, None] * ab, axis=1) <= rad[s]
            hd[near] = hq
            other |= hd; nhand += int((hd & (sdf <= a.trunc)).sum())
        for T_oo, tree, lo, hi in others:                          # samples on another tracked object
            Ti = np.linalg.inv(T_oo[t]); Po = Pd @ Ti[:3, :3].T + Ti[:3, 3]
            near = np.nonzero(np.all((Po >= lo - a.other_r) & (Po <= hi + a.other_r), axis=1))[0]
            if len(near):
                od = np.zeros(len(idx), bool)
                od[near] = tree.query(Po[near], k=1, distance_upper_bound=a.other_r)[0] <= a.other_r
                other |= od; nother += int((od & (sdf <= a.trunc)).sum())
        keep = ~other | (sdf > a.trunc)
        idx, sdf = idx[keep], sdf[keep]
        obs = np.clip(sdf / a.trunc, -1, 1).astype(np.float32)
        tsdf[idx] = (tsdf[idx] * wgt[idx] + obs) / (wgt[idx] + 1); wgt[idx] += 1
    cnt['hand'] += nhand; cnt['table'] += ntable; cnt['other'] += nother; cnt['frames'] += N


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('--poses', required=True, help='poses.npz (comma-separated: several episodes fused)')
    p.add_argument('--depth', required=True, help='depth cache(s), one per --poses entry')
    p.add_argument('--calib', required=True); p.add_argument('--obj', required=True); p.add_argument('--out', required=True)
    p.add_argument('--half', type=float, default=0.30, help='half size of the cube around the object origin (m)')
    p.add_argument('--voxel', type=float, default=0.004)
    p.add_argument('--trunc', type=float, default=0.012)
    p.add_argument('--stride', type=int, default=1, help='use every STRIDE-th frame')
    p.add_argument('--min_obs', type=int, default=3, help='voxels with fewer updates count as unknown')
    p.add_argument('--zmax', type=float, default=1.5, help='ignore depth beyond this (m)')
    p.add_argument('--close', choices=['none', 'fill', 'near', 'auto'], default='auto',
                   help='fill: every enclosed unknown voxel is inside (made wedges behind thin plates: ep39); near: '
                        'unknown voxels within --near_vox of observed-inside voxels, then enclosed cavities; auto: see '
                        '--auto_thr')
    p.add_argument('--auto_thr', type=float, default=0.5, help='auto: near if the never-observed share of the '
                   'filled solid exceeds this (to calibrate)')
    p.add_argument('--near_vox', type=int, default=3)
    p.add_argument('--edge_thr', type=float, default=0.02,
                   help='ignore depth where max-min over a 5x5 window exceeds this (flying pixels at silhouettes; <0 off)')
    p.add_argument('--kit', default='/content/kit/v2d_submission_kit')
    p.add_argument('--hands', default=None, help='hands.npz (hands_mp.py): drop depth samples on the hands/forearms')
    p.add_argument('--hand_r', type=float, default=0.03, help='radius around hand bones (m)')
    p.add_argument('--arm_r', type=float, default=0.045, help='radius around the forearm segment (m)')
    p.add_argument('--arm_len', type=float, default=0.15)
    p.add_argument('--table_band', type=float, default=0.015,
                   help='drop depth samples less than this above the frame-0 support plane, or below it (<0: off)')
    p.add_argument('--others', default='', help='NAME=MESH,...: the episode\'s other tracked objects (posed by their '
                   'cam_T_NAME in --poses); depth samples within --other_r of them carve but never vote surface')
    p.add_argument('--other_r', type=float, default=0.012)
    p.add_argument('--merge_vox', type=int, default=2,
                   help='components within this many voxels of the chosen one are kept (dilation before labelling)')
    a = p.parse_args()
    t0 = time.time()
    K = rectified_K(a.calib)
    n = int(round(2 * a.half / a.voxel)); g = (np.arange(n) + 0.5) * a.voxel - a.half
    X = np.stack(np.meshgrid(g, g, g, indexing='ij'), -1).reshape(-1, 3)          # voxel centres, object frame
    tsdf = np.zeros(len(X), np.float32); wgt = np.zeros(len(X), np.float32)
    cnt = dict(hand=0, table=0, other=0, frames=0)
    # several episodes of the same object fuse into one grid (comma-separated lists; --others per episode by ';')
    poses_l, depth_l = a.poses.split(','), a.depth.split(',')
    hands_l = a.hands.split(',') if a.hands else [None] * len(poses_l)
    others_l = a.others.split(';') if a.others else [''] * len(poses_l)
    if not len(poses_l) == len(depth_l) == len(hands_l) == len(others_l):
        raise SystemExit('--poses, --depth, --hands and --others need one entry per episode')
    for pp, dp, hp, op in zip(poses_l, depth_l, hands_l, others_l):
        integrate(a, K, X, tsdf, wgt, pp, dp, hp or None, op, cnt)
    vol = tsdf.reshape(n, n, n); w = wgt.reshape(n, n, n)
    known = w >= a.min_obs
    inside = known & (vol < 0)
    from scipy import ndimage
    # closing of never-observed space. fill: every enclosed unknown voxel is inside (right for bulky objects whose
    # bottom is never seen: ep41 pot 0.998 vs 0.986 with near); near: only unknown voxels within NEAR_VOX of observed
    # inside, then enclosed cavities (right for thin plates, where fill grows a wedge behind the plate: ep39 0.82 vs
    # 0.95). auto: fill unless the never-observed share of the filled solid exceeds --auto_thr.
    lab, nl = ndimage.label(~known)
    border = np.unique(np.r_[lab[0].ravel(), lab[-1].ravel(), lab[:, 0].ravel(), lab[:, -1].ravel(),
                             lab[:, :, 0].ravel(), lab[:, :, -1].ravel()])
    solid_fill = inside | (~known & ~np.isin(lab, border[border > 0]))
    solid_near = ndimage.binary_fill_holes(inside | (~known & ndimage.binary_dilation(inside, iterations=a.near_vox)))
    def main_part(sol):                                            # the component nearest the origin (as below)
        lb, k = ndimage.label(ndimage.binary_dilation(sol, iterations=max(a.merge_vox, 1)))
        if k == 0:
            return sol
        c0 = np.array(sol.shape) // 2; sz = ndimage.sum(sol, lb, range(1, k + 1)); cand = np.argsort(-sz)[:5] + 1
        best = cand[int(np.argmin([np.min(np.linalg.norm(np.argwhere(lb == q) - c0, axis=1)) for q in cand]))]
        return sol & (lb == best)
    mf = main_part(solid_fill)
    unk_frac = float((mf & ~inside).sum() / max(mf.sum(), 1))       # never-observed share of the filled object
    mode = a.close if a.close != 'auto' else ('near' if unk_frac > a.auto_thr else 'fill')
    solid = {'fill': solid_fill, 'near': solid_near, 'none': inside}[mode]
    print(f'closing: unknown share of filled solid {unk_frac:.3f} -> {mode}', flush=True)
    # keep the component nearest the object origin; label after a small dilation so parts separated by a thin gap
    # (ep2: rim and handle cut off from the pot body) stay together, then return to the undilated voxels
    grown = ndimage.binary_dilation(solid, iterations=a.merge_vox) if a.merge_vox > 0 else solid
    lab, nl = ndimage.label(grown)
    if nl == 0:
        raise SystemExit('nothing reconstructed')
    sizes = ndimage.sum(grown, lab, range(1, nl + 1))
    c = n // 2
    cand = np.argsort(-sizes)[:5] + 1
    dist = [np.min(np.linalg.norm(np.argwhere(lab == k) - c, axis=1)) for k in cand]
    keepc = cand[int(np.argmin(dist))]
    solid = solid & (lab == keepc)
    field = np.where(solid, -1.0, 1.0).astype(np.float32)
    field = ndimage.gaussian_filter(field, 0.8)
    field = np.pad(field, 1, constant_values=1.0)
    from skimage.measure import marching_cubes
    verts, faces, _, _ = marching_cubes(field, 0.0, spacing=(a.voxel,) * 3)
    verts = verts - a.voxel - a.half + 0.5 * a.voxel               # back to object-frame coordinates
    import trimesh
    m = trimesh.Trimesh(verts, faces, process=True)
    # drop floating fragments (ep11 beige cup: bits 25-35 cm away) but keep every substantial piece near the main one
    # (keeping only the largest piece cut that cup in half: registered AUC 0.84 -> 0.42)
    parts = m.split(only_watertight=False)
    if len(parts) > 1:
        big = max(parts, key=lambda q: q.area)
        keep = [q for q in parts if q.area >= 0.05 * big.area and np.linalg.norm(q.centroid - big.centroid) < 0.15]
        m = trimesh.util.concatenate(keep)
    m.export(a.out.replace('.glb', '_full.glb'))
    if os.path.isdir(a.kit):
        sys.path.insert(0, a.kit)
        from v2dlb.mesh_budget import budget_mesh
        vb, fb = budget_mesh(a.out.replace('.glb', '_full.glb'), 4096, 4096)
        m = trimesh.Trimesh(vb, fb, process=False)
    m.export(a.out)
    st = dict(obj=a.obj, episodes=len(poses_l), frames=int(cnt['frames']), stride=a.stride, voxel=a.voxel, trunc=a.trunc, half=a.half, grid=n,
              known_frac=float(known.mean()), inside_vox=int(inside.sum()), solid_vox=int(solid.sum()),
              closing=mode, unknown_share=round(unk_frac, 3), components=int(nl), hand_dropped=cnt['hand'], table_dropped=cnt['table'], other_dropped=cnt['other'],
              verts=int(len(m.vertices)), faces=int(len(m.faces)),
              extents_cm=(np.round(m.extents * 100, 1)).tolist(), watertight=bool(m.is_watertight),
              sec=round(time.time() - t0, 1))
    json.dump(st, open(a.out.replace('.glb', '.json'), 'w'), indent=1)
    print(json.dumps(st))


if __name__ == '__main__':
    main()
