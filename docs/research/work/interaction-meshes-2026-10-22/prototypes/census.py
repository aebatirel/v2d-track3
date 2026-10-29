"""Co-location / interaction census of the two-object public episodes from OUR tracks (poses.npz) and OUR meshes.

Inputs used by the method part (inference-legal): poses.npz (world_T_cam, cam_T_<obj>), result.json 'objects' (names /
slot order), our library meshes. DIAGNOSTIC variant 'scan' (public scans posed by the same tracks; not usable at
inference) is computed separately to tell mesh errors from tracking errors.

Per frame t and ordered pair (A, B): T_BA = inv(cam_T_B[t]) @ cam_T_A[t]; A's solid voxel centres -> B frame -> nearest
voxel of B's occupancy grid. overlap_AinB = #inside * pitch^3. Penetration depth = B's inside distance (EDT of B's
occupancy) at A's voxels inside B. Surface distance = min over A's surface samples of the distance to B's surface
samples (KD-tree, body frames). Region bookkeeping: per-voxel counts of how often each voxel of A lies inside B (A frame)
and how often each voxel of B is entered by A (B frame), over 'overlap frames' (mean overlap > OV_THR cm^3).
Usage: python census.py EP [EP ...]   (writes census/ep<EP>_<variant>.csv/.npz and census/ep<EP>_summary.json)
"""
import os, sys, json, time
import numpy as np, trimesh
from scipy import ndimage
from scipy.spatial import cKDTree
from scipy.spatial.transform import Rotation as Rot

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import vox

S = '/tmp/claude-0/-home-user-v2d-track3/8c892c5e-fd7c-57aa-abef-68d2af098e4f/scratchpad'
OUT = f'{S}/interact/census'
LIB = '/home/user/v2d-track3/meshes'
PITCH = 0.0025
OV_THR = 1.0          # cm^3
CONTACT = 0.005       # m
SOLID_SCANS = ('wooden_piece_1', 'wooden_piece_2')   # closed solid objects: winding-number interior is reliable


def scan_path(n):
    p = f'{S}/loc/t3/mesh/{n}/{n}_visual.glb'
    return p if os.path.exists(p) else f'{S}/loc/t3/mesh/{n}/{n}.glb'


def grid_from_trimesh_vox(path, pitch):
    """DIAGNOSTIC scans (not watertight): shell voxels + binary hole fill, as origin/pitch/occ grid."""
    m = trimesh.load(path, force='mesh'); m.merge_vertices()
    v = m.voxelized(pitch).fill()
    occ = np.pad(v.matrix.astype(bool), 2)
    origin = v.transform[:3, 3] - 2 * pitch
    surf, _ = trimesh.sample.sample_surface(m, 40000, seed=0)
    return dict(origin=origin, pitch=np.float64(pitch), occ=occ, surf=np.asarray(surf, float),
                vol_cm3=occ.sum() * pitch ** 3 * 1e6, bounds=m.bounds)


def load_variant(name, variant):
    if variant == 'scan':
        if name in SOLID_SCANS:
            V = dict(vox.voxelize(scan_path(name), PITCH)); V['solid_rule'] = 'winding'
        else:
            V = grid_from_trimesh_vox(scan_path(name), PITCH); V['solid_rule'] = 'shell+fill'
    else:
        lib = {'v2': 'library_v2', 'v3': 'library_v3', 'v4': 'library_v4'}[variant]
        V = dict(vox.voxelize(f'{LIB}/{lib}/{name}.glb', PITCH)); V['solid_rule'] = 'winding'
    occ = V['occ']
    V['edt'] = ndimage.distance_transform_edt(np.pad(occ, 1))[1:-1, 1:-1, 1:-1].astype(np.float32) * PITCH
    V['ijk'] = np.argwhere(occ)
    V['pts'] = V['origin'] + V['ijk'] * V['pitch']
    V['tree'] = cKDTree(V['surf'])
    return V


def rel(Ca, Cb):
    return np.linalg.inv(Cb) @ Ca                     # A frame -> B frame


def side(VA, VB, T):
    """A's solid voxels inside B under T (A->B). Returns mask over A voxels, B voxel flat indices hit, depths."""
    P = VA['pts'] @ T[:3, :3].T + T[:3, 3]
    inside, idx, ok = vox.lookup(VB, P, 'occ')
    hitB = np.ravel_multi_index(idx[inside].T, VB['occ'].shape) if inside.any() else np.zeros(0, np.int64)
    depth = VB['edt'][idx[inside, 0], idx[inside, 1], idx[inside, 2]] if inside.any() else np.zeros(0)
    return inside, hitB, depth, P


def smooth_resid(X, w=9):
    from scipy.ndimage import median_filter
    return X - median_filter(X, size=(w, 1), mode='nearest')


def run_variant(ep, names, P, variant):
    A, B = names
    VA, VB = load_variant(A, variant), load_variant(B, variant)
    W = P['world_T_cam']; CA = P[f'cam_T_{A}'].astype(np.float64); CB = P[f'cam_T_{B}'].astype(np.float64)
    T = len(W); h3 = PITCH ** 3 * 1e6
    rows = []
    cntA = np.zeros(len(VA['pts']), np.int32); cntB = np.zeros(len(VB['pts']), np.int32)
    posB = np.full(VB['occ'].size, -1, np.int64); posB[np.ravel_multi_index(VB['ijk'].T, VB['occ'].shape)] = np.arange(len(VB['ijk']))
    sets = []
    for t in range(T):
        Tab = rel(CA[t], CB[t]); Tba = np.linalg.inv(Tab)
        inA, hitB, dB, PA_B = side(VA, VB, Tab)        # A voxels inside B
        inB, hitA, dA, PB_A = side(VB, VA, Tba)        # B voxels inside A
        ovAB, ovBA = inA.sum() * h3, inB.sum() * h3
        SA = VA['surf'] @ Tab[:3, :3].T + Tab[:3, 3]
        dmin = float(VB['tree'].query(SA[::20], k=1, workers=-1)[0].min())        # coarse
        if dmin < 0.03:
            dmin = min(dmin, float(VB['tree'].query(SA, k=1, distance_upper_bound=0.03, workers=-1)[0].min()))
        r = dict(frame=t, ov_AinB_cm3=ovAB, ov_BinA_cm3=ovBA, ov_mean_cm3=0.5 * (ovAB + ovBA),
                 pen_AinB_mm=float(dB.max() * 1e3) if len(dB) else 0.0, pen_BinA_mm=float(dA.max() * 1e3) if len(dA) else 0.0,
                 surf_dist_mm=min(dmin, 200.0) * 1e3)
        # overlap region, A frame (A voxels inside B + B voxels inside A mapped to A) and B frame
        if inA.any():
            cA = VA['pts'][inA]; r.update(cA_x=cA[:, 0].mean(), cA_y=cA[:, 1].mean(), cA_z=cA[:, 2].mean(),
                                          extA_x=np.ptp(cA[:, 0]), extA_y=np.ptp(cA[:, 1]), extA_z=np.ptp(cA[:, 2]))
            cB = PA_B[inA]; r.update(cB_x=cB[:, 0].mean(), cB_y=cB[:, 1].mean(), cB_z=cB[:, 2].mean(),
                                     extB_x=np.ptp(cB[:, 0]), extB_y=np.ptp(cB[:, 1]), extB_z=np.ptp(cB[:, 2]))
        rv = Rot.from_matrix(Tab[:3, :3]).as_rotvec()
        r.update(rel_tx=Tab[0, 3], rel_ty=Tab[1, 3], rel_tz=Tab[2, 3], rel_rx=rv[0], rel_ry=rv[1], rel_rz=rv[2])
        rows.append(r)
        sets.append((np.flatnonzero(inA), np.unique(np.concatenate([posB[hitB], np.flatnonzero(inB)]))))
    ovm = np.array([r['ov_mean_cm3'] for r in rows]); ovf = np.flatnonzero(ovm > OV_THR)
    for t in ovf:
        cntA[sets[t][0]] += 1; cntB[sets[t][1]] += 1
    return VA, VB, rows, sets, cntA, cntB, ovf


def region_stats(V, cnt, sets_side, ovf):
    """Union/core volume, per-frame persistence, centroid jitter, mean pairwise Jaccard, core bbox (cm, body frame)."""
    h3 = PITCH ** 3 * 1e6; N = len(ovf)
    if N == 0:
        return dict(n_overlap_frames=0)
    union = cnt > 0; core = cnt >= 0.5 * N
    pers = [np.isin(s, np.flatnonzero(core)).mean() if len(s) else np.nan for s in sets_side]
    cents = np.array([V['pts'][s].mean(0) for s in sets_side if len(s)])
    rng = np.random.default_rng(0); J = []
    for _ in range(min(300, N * (N - 1) // 2)):
        i, j = rng.choice(N, 2, replace=False)
        a, b = sets_side[i], sets_side[j]
        if len(a) and len(b):
            J.append(len(np.intersect1d(a, b)) / len(np.union1d(a, b)))
    out = dict(n_overlap_frames=N, union_cm3=union.sum() * h3, core50_cm3=core.sum() * h3,
               core80_cm3=(cnt >= 0.8 * N).sum() * h3, persistence_mean=float(np.nanmean(pers)),
               centroid_std_cm=float(np.linalg.norm(cents.std(0)) * 100) if len(cents) > 1 else 0.0,
               jaccard_mean=float(np.mean(J)) if J else np.nan)
    if core.any():
        cp = V['pts'][core]; lo, hi = cp.min(0), cp.max(0)
        b = V['bounds']; ext = b[1] - b[0]
        out.update(core_bbox_cm=np.round(np.stack([lo, hi]) * 100, 1).tolist(), core_extent_cm=np.round((hi - lo) * 100, 1).tolist(),
                   core_centroid_cm=np.round(cp.mean(0) * 100, 1).tolist(),
                   core_rel_pos=np.round((cp.mean(0) - b[0]) / ext, 2).tolist(),   # 0..1 along each body axis
                   mesh_bounds_cm=np.round(b * 100, 1).tolist())
    return out


def segments(mask):
    segs = []; t = 0; n = len(mask)
    while t < n:
        if mask[t]:
            s = t
            while t < n and mask[t]:
                t += 1
            segs.append((s, t - 1))
        else:
            t += 1
    return segs


def main(ep):
    t0 = time.time()
    names = json.load(open(f'{S}/loc/perc/ep{ep}/result.json'))['objects']
    P = dict(np.load(f'{S}/loc/perc/ep{ep}/poses.npz'))
    variants = ['v2'] + (['v4'] if names[0].startswith('wooden') else []) + (['v3'] if 'mini_sweeper' in names else []) + ['scan']
    W = P['world_T_cam']; summ = dict(ep=ep, names=names, frames=len(W), variants={})
    # world motion (our VO + tracks): per-frame displacement of each object's origin, 5-frame median smoothing
    from scipy.ndimage import median_filter
    mov = {}
    for n in names:
        Wo = W @ P[f'cam_T_{n}'].astype(np.float64); p = Wo[:, :3, 3]
        sp = np.r_[0, np.linalg.norm(np.diff(p, axis=0), axis=1)]
        mov[n] = median_filter(sp, 5) > 0.004       # > 4 mm/frame (8 cm/s at 20 fps) = moving
    summ['moving_frames'] = {n: int(m.sum()) for n, m in mov.items()}
    for var in variants:
        VA, VB, rows, sets, cntA, cntB, ovf = run_variant(ep, names, P, var)
        import csv
        keys = sorted({k for r in rows for k in r}, key=lambda k: (k != 'frame', k))
        with open(f'{OUT}/ep{ep}_{var}.csv', 'w', newline='') as f:
            w = csv.DictWriter(f, keys); w.writeheader()
            for r, mA, mB in zip(rows, mov[names[0]], mov[names[1]]):
                w.writerow({**{k: (round(v, 5) if isinstance(v, float) else v) for k, v in r.items()}})
        ovm = np.array([r['ov_mean_cm3'] for r in rows]); dist = np.array([r['surf_dist_mm'] for r in rows])
        penA = np.array([r['pen_AinB_mm'] for r in rows]); penB = np.array([r['pen_BinA_mm'] for r in rows])
        contact = (dist < CONTACT * 1e3) | (ovm > 0)
        # relative-pose jitter (high-frequency residual of A-in-B pose), all frames and contact frames
        rt = np.array([[r['rel_tx'], r['rel_ty'], r['rel_tz']] for r in rows]); rr = np.array([[r['rel_rx'], r['rel_ry'], r['rel_rz']] for r in rows])
        jt = np.linalg.norm(smooth_resid(rt), axis=1) * 1e3
        Rm = Rot.from_rotvec(rr); jr = []
        for t in range(len(rows)):
            lo, hi = max(0, t - 4), min(len(rows), t + 5)
            jr.append(np.degrees((Rm[t] * Rot.from_rotvec(np.median(rr[lo:hi], 0)).inv()).magnitude()))
        jr = np.array(jr)
        stA = region_stats(VA, cntA, [sets[t][0] for t in ovf], ovf)
        stB = region_stats(VB, cntB, [sets[t][1] for t in ovf], ovf)
        relspread = dict()
        if len(ovf) > 1:
            relspread = dict(rel_trans_std_mm=float(np.linalg.norm(rt[ovf].std(0)) * 1e3),
                             rel_rot_spread_deg=float(np.degrees(max((Rm[int(t)] * Rm[int(ovf[0])].inv()).magnitude() for t in ovf))))
        both_static = (~mov[names[0]]) & (~mov[names[1]])
        segs = [(int(a), int(b), round(float(ovm[a:b + 1].max()), 2)) for a, b in segments(ovm > OV_THR)]
        csegs = [(int(a), int(b)) for a, b in segments(contact)]
        k = int(np.argmax(ovm))
        summ['variants'][var] = dict(
            solid_vol_cm3={names[0]: float(VA['occ'].sum() * PITCH ** 3 * 1e6), names[1]: float(VB['occ'].sum() * PITCH ** 3 * 1e6)},
            solid_rule=VA['solid_rule'] + '/' + VB['solid_rule'],
            max_overlap_cm3=float(ovm.max()), max_overlap_frame=k, max_ov_AinB=float(rows[k]['ov_AinB_cm3']), max_ov_BinA=float(rows[k]['ov_BinA_cm3']),
            max_pen_mm=float(max(penA.max(), penB.max())), pen_at_max_frame_mm=[rows[k]['pen_AinB_mm'], rows[k]['pen_BinA_mm']],
            frames_contact_lt5mm=int((dist < 5).sum()), frames_contact_or_overlap=int(contact.sum()),
            frames_overlap_gt1cm3=int((ovm > 1).sum()), frames_overlap_gt5cm3=int((ovm > 5).sum()),
            frames_overlap_gt0=int((ovm > 0).sum()),
            overlap_p50_p90_in_overlap_frames=[float(np.percentile(ovm[ovf], 50)), float(np.percentile(ovm[ovf], 90))] if len(ovf) else None,
            overlap_segments=segs, contact_segments=csegs[:20], n_contact_segments=len(csegs),
            overlap_frames_both_static=int(both_static[ovf].sum()), overlap_frames_any_moving=int((~both_static[ovf]).sum()),
            jitter_rel_trans_mm_median=float(np.median(jt)), jitter_rel_rot_deg_median=float(np.median(jr)),
            jitter_rel_trans_mm_contact_median=float(np.median(jt[contact])) if contact.any() else None,
            region_A=stA, region_B=stB, **relspread)
        np.savez_compressed(f'{OUT}/ep{ep}_{var}_regions.npz', A_pts=VA['pts'].astype(np.float32), A_cnt=cntA,
                            B_pts=VB['pts'].astype(np.float32), B_cnt=cntB, overlap_frames=ovf, pitch=PITCH, names=np.array(names))
        print(f'ep{ep} {var}: max overlap {ovm.max():.2f} cm3 @f{k}, >1cm3 {len(ovf)} f, contact<5mm {(dist < 5).sum()} f, '
              f'pen max {max(penA.max(), penB.max()):.1f} mm, segs {segs[:6]}  [{time.time() - t0:.0f}s]', flush=True)
    json.dump(summ, open(f'{OUT}/ep{ep}_summary.json', 'w'), indent=1, default=float)


if __name__ == '__main__':
    for e in sys.argv[1:]:
        main(int(e))
