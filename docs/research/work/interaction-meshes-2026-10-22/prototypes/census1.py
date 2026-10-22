"""Interaction census v1 (exact point-in-mesh queries) over the two-object public episodes.

METHOD PART (inference-legal inputs only): our tracks poses.npz (world_T_cam, cam_T_<obj>), the episode's object names
and slot order (result.json 'objects'), our library meshes (library_v2; v4 boards; v3 sweeper).
  - solid samples of each mesh: centres of a PITCH grid in the body frame whose winding number says inside
    (unbiased volume estimator: count * PITCH^3).
  - per frame t, ordered pair (A, B): T_BA = inv(cam_T_B[t]) @ cam_T_A[t]; A's samples -> B frame; samples inside B's AABB
    get B's exact signed distance (warp BVH, winding-number sign). overlap_AinB = #(sd<0) * PITCH^3, penetration =
    max(-sd). Symmetric B in A. ov_mean = mean of both.
  - surface distance: min over 40k surface samples of A of the distance to 40k surface samples of B (KD-tree).
  - region bookkeeping over 'overlap frames' (ov_mean > OV_THR): per-sample hit counts in each object's own frame;
    union / core50 / core80 volumes, persistence (share of each frame's overlap inside the core50), centroid jitter,
    mean pairwise Jaccard, core bounding box.
DIAGNOSTIC PART (public scans; NOT an input to the method): (a) where the core overlap of OUR mesh sits relative to the
same object's public scan surface (unsigned distance + pseudo-normal sign): >3 mm outside the scan = material our mesh
has and the real object does not (a filled concavity); (b) scan-vs-scan overlap posed by the same tracks, only for
objects whose scan is a reliable solid (winding and pseudo-normal volumes agree within 5 %: boards, sweeper, dust pan,
pitcher), i.e. what overlap our TRACKS alone cause.
Usage: python census1.py EP [EP ...]
"""
import os, sys, json, time, hashlib, csv
import numpy as np, trimesh
from scipy.spatial import cKDTree
from scipy.spatial.transform import Rotation as Rot
from scipy.ndimage import median_filter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import vox2

S = '/tmp/claude-0/-home-user-v2d-track3/8c892c5e-fd7c-57aa-abef-68d2af098e4f/scratchpad'
OUT = f'{S}/interact/census'
CACHE = f'{S}/interact/cache1'
LIB = '/home/user/v2d-track3/meshes'
PITCH = 0.002
H3 = PITCH ** 3 * 1e6          # cm^3 per sample
OV_THR = 1.0                   # cm^3
CONTACT_MM = 5.0
RELIABLE_SCANS = ('wooden_piece_1', 'wooden_piece_2', 'mini_sweeper', 'mini_dust_pan', 'water_pitcher')
os.makedirs(OUT, exist_ok=True); os.makedirs(CACHE, exist_ok=True)


def scan_path(n):
    p = f'{S}/loc/t3/mesh/{n}/{n}_visual.glb'
    return p if os.path.exists(p) else f'{S}/loc/t3/mesh/{n}/{n}.glb'


def mesh_path(n, variant):
    return scan_path(n) if variant == 'scan' else f'{LIB}/library_{variant}/{n}.glb'


_OBJ = {}
def load_obj(n, variant):
    k = (n, variant)
    if k in _OBJ:
        return _OBJ[k]
    path = mesh_path(n, variant)
    m = trimesh.load(path, force='mesh'); m.merge_vertices()
    sd = vox2.SD(m, 'winding')
    key = hashlib.md5(f'{os.path.abspath(path)}:{os.path.getmtime(path)}:{PITCH}'.encode()).hexdigest()[:10]
    cp = f'{CACHE}/{n}_{variant}_{key}.npz'
    if os.path.exists(cp):
        z = np.load(cp); pts, surf = z['pts'], z['surf']
    else:
        pts, _, _ = vox2.solid_samples(m, sd, PITCH)
        surf, _ = trimesh.sample.sample_surface(m, 40000, seed=0)
        np.savez_compressed(cp, pts=pts, surf=np.asarray(surf))
    o = dict(name=n, variant=variant, mesh=m, sd=sd, pts=np.asarray(pts, np.float64), surf=np.asarray(surf, np.float64),
             lo=m.bounds[0] - 1e-3, hi=m.bounds[1] + 1e-3, vol=len(pts) * H3, bounds=m.bounds.copy())
    o['tree'] = cKDTree(o['surf'])
    _OBJ[k] = o
    return o


def inside(A, B, T):
    """A's solid samples inside B under T (A frame -> B frame). Returns (indices into A.pts, depths m, points in B frame)."""
    P = A['pts'] @ T[:3, :3].T + T[:3, 3]
    box = np.flatnonzero(np.all((P >= B['lo']) & (P <= B['hi']), 1))
    if len(box) == 0:
        return np.zeros(0, np.int64), np.zeros(0), P[:0]
    d = B['sd'](P[box])
    k = d < 0
    return box[k], -d[k], P[box[k]]


def surf_dist(A, B, T):
    SA = A['surf'] @ T[:3, :3].T + T[:3, 3]
    d = float(B['tree'].query(SA[::20], k=1, workers=-1)[0].min())
    if d < 0.03:
        d = min(d, float(B['tree'].query(SA, k=1, distance_upper_bound=0.03, workers=-1)[0].min()))
    return d


def segments(mask):
    out, t, n = [], 0, len(mask)
    while t < n:
        if mask[t]:
            s = t
            while t < n and mask[t]:
                t += 1
            out.append((s, t - 1))
        else:
            t += 1
    return out


def region_stats(O, cnt, sets, N):
    if N == 0:
        return dict(n_overlap_frames=0)
    core = cnt >= 0.5 * N
    pers = [np.isin(s, np.flatnonzero(core)).mean() for s in sets if len(s)]
    cents = np.array([O['pts'][s].mean(0) for s in sets if len(s)])
    rng = np.random.default_rng(0); J = []
    nz = [s for s in sets if len(s)]
    for _ in range(min(300, len(nz) * (len(nz) - 1) // 2)):
        i, j = rng.choice(len(nz), 2, replace=False)
        J.append(len(np.intersect1d(nz[i], nz[j])) / len(np.union1d(nz[i], nz[j])))
    r = dict(n_overlap_frames=int(N), union_cm3=float((cnt > 0).sum() * H3), core50_cm3=float(core.sum() * H3),
             core80_cm3=float((cnt >= 0.8 * N).sum() * H3), persistence=float(np.mean(pers)) if pers else None,
             centroid_std_cm=float(np.linalg.norm(cents.std(0)) * 100) if len(cents) > 1 else 0.0,
             jaccard=float(np.mean(J)) if J else None)
    if core.any():
        cp = O['pts'][core]; b = O['bounds']
        r.update(core_bbox_cm=np.round(np.stack([cp.min(0), cp.max(0)]) * 100, 1).tolist(),
                 core_extent_cm=np.round(np.ptp(cp, 0) * 100, 1).tolist(),
                 core_centroid_cm=np.round(cp.mean(0) * 100, 1).tolist(),
                 core_rel_pos=np.round((cp.mean(0) - b[0]) / (b[1] - b[0]), 2).tolist(),
                 mesh_bounds_cm=np.round(b * 100, 1).tolist())
    return r


_SCANSD = {}
def vs_scan(n, P):
    """DIAGNOSTIC: unsigned distance (mm) and pseudo-normal sign of points P (body frame) w.r.t. object n's public scan."""
    if n not in _SCANSD:
        m = trimesh.load(scan_path(n), force='mesh'); m.merge_vertices(); _SCANSD[n] = vox2.SD(m, 'normal')
    d = _SCANSD[n](P, maxd=0.2)
    return np.abs(d) * 1e3, d < 0


def scan_excess(n, P):
    if len(P) == 0:
        return None
    du, ins = vs_scan(n, P)
    return dict(n=int(len(P)), dist_mm_p50=float(np.median(du)), dist_mm_p90=float(np.percentile(du, 90)),
                frac_inside_scan=float(ins.mean()), frac_outside_gt3mm=float(((~ins) & (du > 3)).mean()),
                frac_far_gt3mm_any_sign=float((du > 3).mean()))


def run(ep, names, P, variant, mov):
    A, B = load_obj(names[0], variant), load_obj(names[1], variant)
    CA, CB = P[f'cam_T_{names[0]}'].astype(np.float64), P[f'cam_T_{names[1]}'].astype(np.float64)
    T = len(CA); rows = []; sets = []
    for t in range(T):
        Tab = np.linalg.inv(CB[t]) @ CA[t]; Tba = np.linalg.inv(Tab)
        iA, dA, PA_B = inside(A, B, Tab)          # A samples inside B
        iB, dB, PB_A = inside(B, A, Tba)          # B samples inside A
        ds = surf_dist(A, B, Tab)
        rv = Rot.from_matrix(Tab[:3, :3]).as_rotvec()
        r = dict(frame=t, ov_AinB_cm3=len(iA) * H3, ov_BinA_cm3=len(iB) * H3, ov_mean_cm3=0.5 * (len(iA) + len(iB)) * H3,
                 pen_AinB_mm=float(dA.max() * 1e3) if len(dA) else 0.0, pen_BinA_mm=float(dB.max() * 1e3) if len(dB) else 0.0,
                 surf_dist_mm=ds * 1e3, moving_A=int(mov[names[0]][t]), moving_B=int(mov[names[1]][t]),
                 rel_tx=Tab[0, 3], rel_ty=Tab[1, 3], rel_tz=Tab[2, 3], rel_rx=rv[0], rel_ry=rv[1], rel_rz=rv[2])
        for tag, idx, O in (('A', iA, A), ('B', iB, B)):     # overlap region in each object's own frame
            if len(idx):
                c = O['pts'][idx]
                r.update({f'c{tag}_x_cm': c[:, 0].mean() * 100, f'c{tag}_y_cm': c[:, 1].mean() * 100, f'c{tag}_z_cm': c[:, 2].mean() * 100,
                          f'ext{tag}_x_cm': np.ptp(c[:, 0]) * 100, f'ext{tag}_y_cm': np.ptp(c[:, 1]) * 100, f'ext{tag}_z_cm': np.ptp(c[:, 2]) * 100})
        rows.append(r); sets.append((iA, iB))
    return A, B, rows, sets


def main(ep):
    t0 = time.time()
    names = json.load(open(f'{S}/loc/perc/ep{ep}/result.json'))['objects']
    P = dict(np.load(f'{S}/loc/perc/ep{ep}/poses.npz'))
    W = P['world_T_cam']
    variants = ['v2'] + (['v4'] if names[0].startswith('wooden') else []) + (['v3'] if 'mini_sweeper' in names else [])
    if all(n in RELIABLE_SCANS for n in names):
        variants.append('scan')
    mov = {}
    for n in names:
        p = (W @ P[f'cam_T_{n}'].astype(np.float64))[:, :3, 3]
        mov[n] = median_filter(np.r_[0, np.linalg.norm(np.diff(p, axis=0), axis=1)], 5) > 0.004   # > 4 mm/frame
    summ = dict(ep=ep, names=names, frames=len(W), moving_frames={n: int(m.sum()) for n, m in mov.items()}, variants={})
    for var in variants:
        A, B, rows, sets = run(ep, names, P, var, mov)
        keys = list(dict.fromkeys(k for r in rows for k in r))
        with open(f'{OUT}/ep{ep}_{var}.csv', 'w', newline='') as f:
            w = csv.DictWriter(f, keys, restval=''); w.writeheader()
            for r in rows:
                w.writerow({k: (round(v, 4) if isinstance(v, (float, np.floating)) else v) for k, v in r.items()})
        ovm = np.array([r['ov_mean_cm3'] for r in rows]); dist = np.array([r['surf_dist_mm'] for r in rows])
        pen = np.maximum([r['pen_AinB_mm'] for r in rows], [r['pen_BinA_mm'] for r in rows])
        ovf = np.flatnonzero(ovm > OV_THR); N = len(ovf)
        cntA = np.zeros(len(A['pts']), np.int32); cntB = np.zeros(len(B['pts']), np.int32)
        for t in ovf:
            cntA[sets[t][0]] += 1; cntB[sets[t][1]] += 1
        rt = np.array([[r['rel_tx'], r['rel_ty'], r['rel_tz']] for r in rows])
        Rm = Rot.from_rotvec(np.array([[r['rel_rx'], r['rel_ry'], r['rel_rz']] for r in rows]))
        jt = np.linalg.norm(rt - median_filter(rt, size=(9, 1), mode='nearest'), axis=1) * 1e3
        static = (~mov[names[0]]) & (~mov[names[1]])
        k = int(np.argmax(ovm))
        v = dict(solid_vol_cm3={names[0]: A['vol'], names[1]: B['vol']},
                 max_overlap_cm3=float(ovm.max()), max_overlap_frame=k,
                 at_max=dict(AinB=rows[k]['ov_AinB_cm3'], BinA=rows[k]['ov_BinA_cm3'], pen_AinB_mm=rows[k]['pen_AinB_mm'],
                             pen_BinA_mm=rows[k]['pen_BinA_mm'], extA_cm=[rows[k].get(f'extA_{a}_cm') for a in 'xyz'],
                             extB_cm=[rows[k].get(f'extB_{a}_cm') for a in 'xyz']),
                 max_pen_mm=float(pen.max()),
                 frames_contact_lt5mm=int((dist < CONTACT_MM).sum()), frames_overlap_gt0=int((ovm > 0).sum()),
                 frames_overlap_gt1cm3=int(N), frames_overlap_gt5cm3=int((ovm > 5).sum()),
                 overlap_p50_p90=[float(np.percentile(ovm[ovf], 50)), float(np.percentile(ovm[ovf], 90))] if N else None,
                 pen_p50_in_overlap_frames_mm=float(np.median(pen[ovf])) if N else None,
                 overlap_segments=[(int(a), int(b), round(float(ovm[a:b + 1].max()), 2)) for a, b in segments(ovm > OV_THR)],
                 contact_segments=[(int(a), int(b)) for a, b in segments((dist < CONTACT_MM) | (ovm > 0))],
                 overlap_frames_both_static=int(static[ovf].sum()), overlap_frames_moving=int((~static[ovf]).sum()),
                 rel_jitter_mm_p50_all=float(np.median(jt)),
                 rel_jitter_mm_p50_contact=float(np.median(jt[dist < CONTACT_MM])) if (dist < CONTACT_MM).any() else None,
                 rel_jitter_mm_p50_overlap=float(np.median(jt[ovf])) if N else None,
                 rel_pose_spread_in_overlap=dict(trans_std_mm=float(np.linalg.norm(rt[ovf].std(0)) * 1e3),
                                                 rot_max_deg=float(np.degrees(max((Rm[int(t)] * Rm[int(ovf[0])].inv()).magnitude() for t in ovf))))
                 if N > 1 else None,
                 region_A=region_stats(A, cntA, [sets[t][0] for t in ovf], N),
                 region_B=region_stats(B, cntB, [sets[t][1] for t in ovf], N))
        if var != 'scan' and N:      # DIAGNOSTIC: our overlap regions vs the public scan of the same object
            v['diag_vs_scan'] = {}
            for tag, O, cnt in (('A', A, cntA), ('B', B, cntB)):
                v['diag_vs_scan'][tag] = dict(core50=scan_excess(O['name'], O['pts'][cnt >= 0.5 * N]),
                                              union=scan_excess(O['name'], O['pts'][cnt > 0]),
                                              whole_mesh=scan_excess(O['name'], O['pts'][::7]))
        summ['variants'][var] = v
        np.savez_compressed(f'{OUT}/ep{ep}_{var}_regions.npz', A_pts=A['pts'].astype(np.float32), A_cnt=cntA,
                            B_pts=B['pts'].astype(np.float32), B_cnt=cntB, overlap_frames=ovf, pitch=PITCH, names=np.array(names),
                            ov_mean=ovm, surf_dist_mm=dist)
        print(f'ep{ep} {var}: max ov {ovm.max():.2f} cm3 @f{k} (AinB {rows[k]["ov_AinB_cm3"]:.2f} BinA {rows[k]["ov_BinA_cm3"]:.2f}), '
              f'>1cm3 {N} f, contact<5mm {(dist < 5).sum()} f, pen max {pen.max():.1f} mm, '
              f'segs {v["overlap_segments"][:6]} [{time.time() - t0:.0f}s]', flush=True)
    json.dump(summ, open(f'{OUT}/ep{ep}_summary.json', 'w'), indent=1, default=float)


if __name__ == '__main__':
    for e in sys.argv[1:]:
        main(int(e))
