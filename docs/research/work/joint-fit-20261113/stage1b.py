"""Stage 1b (PREREG.md in this folder): per object, ONE shape correction (scale along the template's principal axes)
shared by all its rest segments, jointly with ONE world pose per rest segment, fitted to SAM2 silhouettes (both
directions) and stereo depth over many frames. Extends stage 1 (docs/analysis/ptrk-20261102/scripts/stage1.py, branch
claude/perception-tracking-20261102), which fitted the pose alone by depth ICP against the fixed template and failed.
GT-free: our track, our depth, our SAM2 video masks, our cameras, our templates. Never reads a parquet, scan or mocap.
Usage: python -I stage1b.py EP POSES_NPZ DEPTH_NPY VOS_MASKS_NPZ K_SOURCE_NPZ MESH_DIR OUT_DIR [--plane_log LOG] [--no_shape] [--no_sil]
Writes OUT_DIR/poses_world_vo.npz, OUT_DIR/changed.npz, OUT_DIR/meshes/<obj>.glb (fitted scale), OUT_DIR/stage1b.json."""
import argparse, hashlib, json, os, shutil, time
import numpy as np, trimesh, cv2
from scipy.ndimage import distance_transform_edt, map_coordinates
from scipy.optimize import least_squares
from scipy.sparse import lil_matrix
from scipy.spatial import cKDTree
from scipy.spatial.transform import Rotation as Rot, Slerp

p = argparse.ArgumentParser()
for k in ('ep', 'poses', 'depth', 'vos', 'ksrc', 'meshes', 'out'):
    p.add_argument(k)
p.add_argument('--frames_per_seg', type=int, default=6)
p.add_argument('--depth_pts', type=int, default=400)
p.add_argument('--sil_pts', type=int, default=400)
p.add_argument('--recall_pts', type=int, default=150)
p.add_argument('--dense_pts', type=int, default=1500)
p.add_argument('--fscale', type=float, default=0.005)      # robust scale of every data residual, metres
p.add_argument('--prior_t', type=float, default=0.02)       # metres
p.add_argument('--prior_r', type=float, default=5.0)        # degrees
p.add_argument('--prior_s', type=float, default=0.05)       # log scale
p.add_argument('--smin', type=float, default=0.85)
p.add_argument('--smax', type=float, default=1.15)
p.add_argument('--min_pts', type=int, default=300)
p.add_argument('--max_move_cm', type=float, default=3.0)
p.add_argument('--max_rot_deg', type=float, default=10.0)
p.add_argument('--ramp', type=int, default=5)
p.add_argument('--max_nfev', type=int, default=60)
p.add_argument('--no_shape', action='store_true', help='ablation: poses only (silhouette + depth), template shape')
p.add_argument('--no_sil', action='store_true', help='ablation: depth terms only')
p.add_argument('--plane_log', default=None, help='perc2 log.txt holding "track guard: table plane (n, c)" (frame-0 '
               'camera, from our own depth): adds the support term (dev amendment 13 Nov, the winner\'s "at rest, '
               'level on its support"): a segment whose tracker pose has its lowest 1%% of surface within --on_table of '
               'the plane is pulled onto it (sigma --sup_sigma); others only may not sink below it')
p.add_argument('--on_table', type=float, default=0.02)
p.add_argument('--sup_sigma', type=float, default=0.003)
a = p.parse_args()
for q in (a.poses, a.depth, a.vos, a.ksrc, a.meshes):
    assert not any(s in q for s in ('.parquet', 'observation', 'score_registered', '_pf.npz', '/gt/', '/t3/mesh')), q
os.makedirs(f'{a.out}/meshes', exist_ok=True)
t_start = time.time()

P = np.load(a.poses)
W = np.asarray(P['world_T_cam'], np.float64)
names = [k[6:] for k in P.files if k.startswith('cam_T_')]
T = len(W)
O = {n: np.einsum('tij,tjk->tik', W, np.asarray(P[f'cam_T_{n}'], np.float64)) for n in names}
K = np.load(a.ksrc)['K'].astype(np.float64)
D = np.load(a.depth, mmap_mode='r')
V = np.load(a.vos)
MASK = {n: np.unpackbits(V[n], axis=-1)[:, :, :400].astype(bool) for n in names if n in V.files}
H4, W4 = next(iter(MASK.values())).shape[1:]
SC = D.shape[2] / W4                                     # depth pixels per mask pixel
rng = np.random.default_rng(0)
PLANE = None
if a.plane_log:
    import re
    for line in open(a.plane_log):
        mt = re.search(r'track guard: table plane \(\[([-\d.e, ]+)\], ([-\d.e]+)\)', line)
        if mt:
            n_c0 = np.array([float(v) for v in mt.group(1).split(',')]); c_c0 = float(mt.group(2))
            R0, t0 = W[0][:3, :3], W[0][:3, 3]              # height(x_w) = n . (R0^T (x_w - t0)) + c
            PLANE = (R0 @ n_c0, c_c0 - n_c0 @ (R0.T @ t0)); break


def rest_runs(X):  # stage 1's rule, unchanged
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


def project(Xw_pts, t):
    """World points -> depth-image pixels (u, v) and depth z at frame t."""
    Ci = np.linalg.inv(W[t])
    c = Xw_pts @ Ci[:3, :3].T + Ci[:3, 3]
    z = c[:, 2]
    uv = c @ K.T
    return uv[:, :2] / np.maximum(uv[:, 2:3], 1e-6), z


def silhouette(verts_w, faces, t):
    uv, z = project(verts_w, t)
    img = np.zeros((H4, W4), np.uint8)
    F = faces[(z[faces] > 0.05).all(1)]
    cv2.fillPoly(img, [np.round(uv[f] / SC - 0.5).astype(np.int32) for f in F], 1)
    return img > 0


def blend(A, B, w):
    R = Slerp([0, 1], Rot.from_matrix([A[:3, :3], B[:3, :3]]))(w).as_matrix()
    M = np.eye(4); M[:3, :3] = R; M[:3, 3] = (1 - w) * A[:3, 3] + w * B[:3, 3]; return M


def se3(x):
    M = np.eye(4); M[:3, :3] = Rot.from_rotvec(x[:3]).as_matrix(); M[:3, 3] = x[3:6]; return M


rec = dict(episode=int(a.ep), settings={k: getattr(a, k) for k in vars(a) if k not in ('ep', 'poses', 'depth', 'vos', 'ksrc', 'meshes', 'out')},
           inputs={k: getattr(a, k) for k in ('poses', 'depth', 'vos', 'ksrc', 'meshes')}, objects={})
NEW = {n: O[n].copy() for n in names}
for n in names:
    m = trimesh.load(f'{a.meshes}/{n}.glb', force='mesh')
    verts, faces = np.asarray(m.vertices), np.asarray(m.faces)
    dense = np.asarray(trimesh.sample.sample_surface(m, 30000, seed=0)[0])
    tree = cKDTree(dense)
    cen = dense.mean(0)
    _, _, Vt = np.linalg.svd(dense - cen, full_matrices=False)
    Rp = Vt.T                                            # principal axes (columns)
    sil_s = dense[rng.choice(len(dense), a.sil_pts, replace=False)]
    rec_s = dense[rng.choice(len(dense), a.dense_pts, replace=False)]

    def shape_mat(ls):
        A = np.eye(4); A[:3, :3] = Rp @ np.diag(np.exp(ls)) @ Rp.T; A[:3, 3] = cen - A[:3, :3] @ cen; return A

    if n not in MASK:
        rec['objects'][n] = dict(note='no VOS mask'); shutil.copy(f'{a.meshes}/{n}.glb', f'{a.out}/meshes/{n}.glb'); continue
    others = np.zeros_like(MASK[n])
    for o in names:
        if o != n and o in MASK: others |= MASK[o]
    low_s = dense[rng.choice(len(dense), 3000, replace=False)]   # support term: soft-min height over these

    def height(M):
        if PLANE is None: return None
        h = (low_s @ M[:3, :3].T + M[:3, 3]) @ PLANE[0] + PLANE[1]
        return float(np.mean(np.sort(h)[:30]))           # mean of the lowest 1 %

    segs, frames = [], []                                # frames: (seg index, t, obs dict)
    for s, e in rest_runs(O[n]):
        fs, fe = s + 2, e - 2
        sr = dict(frames=[int(s), int(e)], fit=[int(fs), int(fe)])
        if fe - fs < 6:
            sr['kept'] = 'tracker (too short)'; segs.append(sr); continue
        ts = np.unique(np.linspace(fs, fe - 1, min(a.frames_per_seg, fe - fs)).round().astype(int))
        k_seg, npts, used = len([q for q in segs if 'X0' in q]), 0, []
        for t in ts:
            mk = MASK[n][t]
            if mk.sum() < 30: continue
            Xc = np.linalg.inv(W[t]) @ O[n][t]
            proj = silhouette((verts @ O[n][t][:3, :3].T + O[n][t][:3, 3]), faces, t)
            dm = mk & cv2.dilate(proj.astype(np.uint8), np.ones((5, 5), np.uint8)).astype(bool)
            dm = cv2.erode(dm.astype(np.uint8), np.ones((3, 3), np.uint8)).astype(bool)
            v, u = np.nonzero(dm)
            z = np.asarray(D[t])[(v * SC + SC / 2).astype(int).clip(0, D.shape[1] - 1), (u * SC + SC / 2).astype(int).clip(0, D.shape[2] - 1)]
            ok = z > 0; v, u, z = v[ok], u[ok], z[ok].astype(np.float64)
            if len(z) > a.depth_pts:
                kk = rng.choice(len(z), a.depth_pts, replace=False); v, u, z = v[kk], u[kk], z[kk]
            uu, vv = u * SC + SC / 2, v * SC + SC / 2
            pc = np.stack([(uu - K[0, 2]) * z / K[0, 0], (vv - K[1, 2]) * z / K[1, 1], z], 1)
            pw = pc @ W[t][:3, :3].T + W[t][:3, 3]
            ot = others[t]
            allowed = mk | ot
            dt_out = distance_transform_edt(~allowed)       # mask px to the nearest allowed pixel
            edge = mk & ~cv2.erode(mk.astype(np.uint8), np.ones((3, 3), np.uint8)).astype(bool)
            near_other = cv2.dilate(ot.astype(np.uint8), np.ones((5, 5), np.uint8)).astype(bool)
            edge[:2, :] = edge[-2:, :] = False; edge[:, :2] = edge[:, -2:] = False   # image border is truncation
            edge &= ~near_other                               # a boundary against another object is an occlusion edge
            ev, eu = np.nonzero(edge)
            if len(ev) > a.recall_pts:
                kk = rng.choice(len(ev), a.recall_pts, replace=False); ev, eu = ev[kk], eu[kk]
            frames.append((k_seg, int(t), dict(pw=pw, dt=dt_out, edge=np.stack([eu, ev], 1).astype(np.float64), zmed=float(np.median(z)) if len(z) else float(Xc[2, 3]))))
            npts += len(z); used.append(int(t))
        sr.update(points=int(npts), frames_used=used)
        if len(used) < 2 or npts < a.min_pts:
            frames = [f for f in frames if f[0] != k_seg]
            sr['kept'] = 'tracker (too few frames / points)'; segs.append(sr); continue
        sr['X0'] = O[n][(fs + fe) // 2].copy()
        h0 = height(sr['X0'])
        sr['support'] = None if h0 is None else ('table' if h0 < a.on_table else 'other')
        if h0 is not None: sr['h0_cm'] = round(h0 * 100, 2)
        segs.append(sr)
    fit_segs = [q for q in segs if 'X0' in q]
    S = len(fit_segs)
    if S == 0:
        rec['objects'][n] = dict(segments=[{k: v for k, v in q.items() if k != 'X0'} for q in segs], frames_changed=0, shape='template')
        shutil.copy(f'{a.meshes}/{n}.glb', f'{a.out}/meshes/{n}.glb'); continue
    fx = K[0, 0] * SC                                    # metres per mask pixel = z / fx

    def residuals(x, parts=False):
        ls = np.zeros(3) if a.no_shape else x[:3]
        A = shape_mat(ls)
        out = {'depth': [], 'prec': [], 'rec': [], 'prior': [], 'support': []}
        for k_seg, t, ob in frames:
            Xs = fit_segs[k_seg]['X0'] @ se3(x[3 + 6 * k_seg: 9 + 6 * k_seg])
            # depth: observed world point -> body -> template space (inverse shape) -> nearest dense sample -> back
            b = (ob['pw'] - Xs[:3, 3]) @ Xs[:3, :3]
            Ai = np.linalg.inv(A)
            bt = b @ Ai[:3, :3].T + Ai[:3, 3]
            _, j = tree.query(bt)
            q = dense[j] @ A[:3, :3].T + A[:3, 3]
            out['depth'].append(np.linalg.norm(b - q, axis=1))
            if not a.no_sil:
                M = Xs @ A
                for pts, key in ((sil_s, 'prec'), (rec_s, 'rec')):
                    uv, z = project(pts @ M[:3, :3].T + M[:3, 3], t)
                    um = uv / SC - 0.5
                    if key == 'prec':
                        inside = (um[:, 0] >= 0) & (um[:, 0] <= W4 - 1) & (um[:, 1] >= 0) & (um[:, 1] <= H4 - 1)
                        d = map_coordinates(ob['dt'], [um[:, 1].clip(0, H4 - 1), um[:, 0].clip(0, W4 - 1)], order=1)
                        out['prec'].append(np.where(inside, d, 0.0) * z.clip(0.1, 3) / fx)
                    elif len(ob['edge']):
                        d, _ = cKDTree(um).query(ob['edge'])
                        out['rec'].append(d * ob['zmed'] / fx)
        if PLANE is not None:
            for k_seg in range(S):
                h = height(fit_segs[k_seg]['X0'] @ se3(x[3 + 6 * k_seg: 9 + 6 * k_seg]) @ A)
                v = h if fit_segs[k_seg]['support'] == 'table' else min(h, 0.0)
                out['support'].append(np.array([v / a.sup_sigma * a.fscale]))
        for k_seg in range(S):
            xs = x[3 + 6 * k_seg: 9 + 6 * k_seg]
            out['prior'].append(np.r_[xs[:3] / np.radians(a.prior_r), xs[3:] / a.prior_t] * a.fscale)
        out['prior'].append((x[:3] / a.prior_s) * a.fscale)
        if parts:
            return {k: np.concatenate(v) if v else np.zeros(0) for k, v in out.items()}
        return np.concatenate([np.concatenate(out[k]) for k in ('depth', 'prec', 'rec', 'support', 'prior') if out[k]])

    x0 = np.zeros(3 + 6 * S)
    r0 = residuals(x0)
    # block sparsity: shape columns touch every row; segment k touches its frames' rows and its prior
    sp = lil_matrix((len(r0), len(x0)), dtype=int)
    sp[:, :3] = 1
    row = 0
    for key in ('depth', 'prec', 'rec'):
        for k_seg, t, ob in frames:
            nr = len(ob['pw']) if key == 'depth' else (0 if a.no_sil else (a.sil_pts if key == 'prec' else len(ob['edge'])))
            sp[row:row + nr, 3 + 6 * k_seg: 9 + 6 * k_seg] = 1; row += nr
    if PLANE is not None:
        for k_seg in range(S):
            sp[row, 3 + 6 * k_seg: 9 + 6 * k_seg] = 1; row += 1
    for k_seg in range(S):
        sp[row:row + 6, 3 + 6 * k_seg: 9 + 6 * k_seg] = 1; row += 6
    assert row + 3 == len(r0), (row, len(r0))
    lo = np.r_[np.full(3, np.log(a.smin)), np.full(6 * S, -np.inf)]
    hi = np.r_[np.full(3, np.log(a.smax)), np.full(6 * S, np.inf)]
    if a.no_shape:
        lo[:3], hi[:3] = -1e-9, 1e-9
    sol = least_squares(residuals, x0, jac_sparsity=sp, loss='soft_l1', f_scale=a.fscale, bounds=(lo, hi),
                        x_scale=np.r_[np.full(3, 0.02), np.tile(np.r_[np.full(3, 0.02), np.full(3, 0.005)], S)],
                        max_nfev=a.max_nfev, method='trf')
    cost0 = float(np.sum(a.fscale ** 2 * 2 * (np.sqrt(1 + (r0 / a.fscale) ** 2) - 1)) / 2)
    pa0, pa1 = residuals(x0, True), residuals(sol.x, True)
    med = lambda v: round(float(np.median(v) * 1000), 2) if len(v) else None
    orec = dict(segments_total=len(segs), segments_fit=S, frames=len(frames), cost0=round(cost0 * 1e6, 3), cost1=round(float(sol.cost) * 1e6, 3),
                nfev=int(sol.nfev), scale=[round(float(v), 4) for v in np.exp(sol.x[:3])],
                median_mm_before={k: med(pa0[k]) for k in ('depth', 'prec', 'rec')},
                median_mm_after={k: med(pa1[k]) for k in ('depth', 'prec', 'rec')},
                support_mm_before=[round(float(v) / a.fscale * a.sup_sigma * 1000, 2) for v in pa0['support']],
                support_mm_after=[round(float(v) / a.fscale * a.sup_sigma * 1000, 2) for v in pa1['support']])
    improved = sol.cost < cost0
    orec['shape'] = 'fitted' if improved and not a.no_shape else 'template'
    if orec['shape'] == 'fitted':
        mm = m.copy(); mm.apply_transform(shape_mat(sol.x[:3])); mm.export(f'{a.out}/meshes/{n}.glb')
    else:
        shutil.copy(f'{a.meshes}/{n}.glb', f'{a.out}/meshes/{n}.glb')
    for k_seg, q in enumerate(fit_segs):
        X = q['X0'] @ se3(sol.x[3 + 6 * k_seg: 9 + 6 * k_seg])
        mv_cm = float(np.linalg.norm(X[:3, 3] - q['X0'][:3, 3]) * 100)
        rot_deg = float(np.degrees(Rot.from_matrix(q['X0'][:3, :3].T @ X[:3, :3]).magnitude()))
        q.update(move_cm=round(mv_cm, 2), rot_deg=round(rot_deg, 2))
        if not improved or mv_cm > a.max_move_cm or rot_deg > a.max_rot_deg:
            q['kept'] = 'tracker (guard)' if improved else 'tracker (cost did not fall)'; continue
        q['kept'] = 'fit'
        s, e = q['frames']
        for t in range(s, e):
            NEW[n][t] = X
        for k in range(1, a.ramp + 1):
            w = 1 - k / (a.ramp + 1)
            if s - k >= 0: NEW[n][s - k] = blend(O[n][s - k], X, w)
            if e - 1 + k < T: NEW[n][e - 1 + k] = blend(O[n][e - 1 + k], X, w)
    orec['segments'] = [{k: v for k, v in q.items() if k != 'X0'} for q in segs]
    orec['frames_changed'] = int((np.abs(NEW[n] - O[n]).max((1, 2)) > 1e-9).sum())
    rec['objects'][n] = orec
    print(a.ep, n, 'segments', len(segs), 'fit', sum(q.get('kept') == 'fit' for q in segs), 'scale', orec['scale'],
          'cost', orec['cost0'], '->', orec['cost1'], 'median mm', orec['median_mm_before'], '->', orec['median_mm_after'], flush=True)
for n in names:
    if not os.path.exists(f'{a.out}/meshes/{n}.glb'):
        shutil.copy(f'{a.meshes}/{n}.glb', f'{a.out}/meshes/{n}.glb')
np.savez(f'{a.out}/poses_world_vo.npz', **NEW)
np.savez(f'{a.out}/changed.npz', **{n: (np.abs(NEW[n] - O[n]).max((1, 2)) > 1e-9) for n in names})
rec['sha256'] = hashlib.sha256(open(f'{a.out}/poses_world_vo.npz', 'rb').read()).hexdigest()
rec['seconds'] = round(time.time() - t_start, 1)
json.dump(rec, open(f'{a.out}/stage1b.json', 'w'), indent=1, default=float)
