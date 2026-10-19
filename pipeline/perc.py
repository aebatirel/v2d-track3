"""Perception-only accuracy on a public Track 3 episode (any objects).

Inference (no ground-truth poses read before scoring; object names/slot order come from the episode,
as the kit provides them for eval episodes):
  mono stereo pair c/b -> rectify -> FoundationStereo depth (rectified-left frame, cached)
  frame 0: OWLv2 candidate boxes per object prompt -> SAM2 masks -> FoundationPose register per
           (object, candidate); assignment by FoundationPose score (Hungarian within a prompt group)
  FoundationPose track_one on later frames
  camera: keyframe SIFT + depth PnP (world = rectified-left camera at frame 0)
Scoring: official kit Track 3 metric functions vs mocap, for world variants
  'vo' (camera from PnP) and 'anchor:<obj>' (that object assumed static; analysis only).
Env: EP, FS_SCALE (0.5), OUT. Outputs result.json, poses.npz, masks_f0.jpg, vo.json in OUT.
"""
import os, sys, json, time, importlib
import numpy as np, cv2, torch, trimesh
import pyarrow.parquet as pq
from scipy.spatial.transform import Rotation as Rot
from scipy.optimize import linear_sum_assignment

os.environ.setdefault('TORCH_FORCE_NO_WEIGHTS_ONLY_LOAD', '1')
EP = int(os.environ.get('EP', 12))
FS_SCALE = float(os.environ.get('FS_SCALE', 0.5))
D = '/content/t3'
OUT = os.environ.get('OUT', f'/content/perc/ep{EP}')
os.makedirs(OUT, exist_ok=True)
PROMPT = {'white_pot': 'a cooking pot', 'white_pot_lid': 'a pot lid', 'blue_cup': 'a cup', 'beige_cup': 'a cup',
          'plastic_dish_rack': 'a dish rack', 'water_pitcher': 'a pitcher', 'mini_sweeper': 'a hand broom',
          'mini_dust_pan': 'a dustpan', 'wooden_piece_1': 'a wooden block', 'wooden_piece_2': 'a wooden block',
          'wooden_spoon': 'a wooden spoon'}
t_all = time.time()
def log(*a):
    print(f'[{time.time() - t_all:7.1f}s]', *a, flush=True)
def mesh_path(n):
    p = f'{D}/mesh/{n}/{n}.glb'
    return p if os.path.exists(p) else f'{D}/mesh/{n}/{n}_visual.glb'

tab = pq.read_table(f'{D}/ep{EP}.parquet').to_pandas()
names = [o['name'] for o in tab['observation.objects'].iloc[0]]          # slot order only
log('episode', EP, 'objects', names)

# ---------- calibration + rectification (left = ego_cam_c, right = ego_cam_b) ----------
C = json.load(open(f'{D}/calib.json')); cam = C['cameras']
sp = [p for p in C['stereo_pairs'] if p['camera'] == 'ego'][0]
K_ = lambda n: np.array(cam[n]['intrinsic_matrix'], float)
D_ = lambda n: np.array(cam[n]['distortion_coefficients'], float)
Kc, dc, Kb, db = K_('ego_cam_c'), D_('ego_cam_c'), K_('ego_cam_b'), D_('ego_cam_b')
E = np.array(sp['left_to_right'], float); R, T = E[:3, :3].copy(), E[:3, 3].reshape(3, 1).copy()
SZ, RSZ = (1280, 800), (1600, 1000)
R1, R2, P1, P2, Q, _, _ = cv2.stereoRectify(Kc, dc, Kb, db, SZ, R, T, alpha=0, newImageSize=RSZ, flags=cv2.CALIB_ZERO_DISPARITY)
MC = cv2.initUndistortRectifyMap(Kc, dc, R1, P1, RSZ, cv2.CV_32FC1)
MB = cv2.initUndistortRectifyMap(Kb, db, R2, P2, RSZ, cv2.CV_32FC1)
FR = P1[0, 0]; BASE = -P2[0, 3] / P2[0, 0]; KR = P1[:3, :3].copy()

def frames(path):
    cap = cv2.VideoCapture(path); out = []
    while True:
        ok, f = cap.read()
        if not ok: break
        out.append(cv2.cvtColor(f, cv2.COLOR_BGR2GRAY))
    return out
fc, fb = frames(f'{D}/v/ep{EP}_c.mp4'), frames(f'{D}/v/ep{EP}_b.mp4')
N = min(len(fc), len(fb), len(tab))
rc = [cv2.remap(fc[i], MC[0], MC[1], cv2.INTER_LINEAR) for i in range(N)]
rb = [cv2.remap(fb[i], MB[0], MB[1], cv2.INTER_LINEAR) for i in range(N)]
rgb = lambda g: np.repeat(g[..., None], 3, 2)
log('frames c/b/rows', len(fc), len(fb), len(tab), 'focal', round(FR, 1), 'baseline', round(BASE, 4))

# ---------- FoundationStereo depth (cached) ----------
DCACHE = f'{OUT}/depths_fs{FS_SCALE}.npy'
if os.path.exists(DCACHE):
    depths = list(np.load(DCACHE))
else:
    sys.path.insert(0, '/content/FoundationStereo')
    from omegaconf import OmegaConf
    from core.utils.utils import InputPadder
    from core.foundation_stereo import FoundationStereo
    CK = '/content/FoundationStereo/pretrained_models/23-51-11/model_best_bp2.pth'
    cfg = OmegaConf.load(os.path.join(os.path.dirname(CK), 'cfg.yaml'))
    cfg['valid_iters'] = 32; cfg['hiera'] = 0
    cfg['vit_size'] = cfg.get('vit_size', 'vitl')
    fs = FoundationStereo(cfg); fs.load_state_dict(torch.load(CK, weights_only=False)['model']); fs.cuda().eval()
    depths = []
    with torch.no_grad():
        for i in range(N):
            a = cv2.resize(rc[i], None, fx=FS_SCALE, fy=FS_SCALE); b = cv2.resize(rb[i], None, fx=FS_SCALE, fy=FS_SCALE)
            t0 = torch.as_tensor(rgb(a)).cuda().float()[None].permute(0, 3, 1, 2)
            t1 = torch.as_tensor(rgb(b)).cuda().float()[None].permute(0, 3, 1, 2)
            pad = InputPadder(t0.shape, divis_by=32, force_square=False); t0, t1 = pad.pad(t0, t1)
            with torch.amp.autocast('cuda', enabled=True):
                disp = fs.forward(t0, t1, iters=32, test_mode=True)
            disp = pad.unpad(disp.float()).cpu().numpy().reshape(a.shape[0], a.shape[1])
            disp = cv2.resize(disp, RSZ, interpolation=cv2.INTER_LINEAR) / FS_SCALE
            z = np.where(disp > 1, FR * BASE / np.maximum(disp, 1e-6), 0).astype(np.float32)
            z[(z < 0.15) | (z > 2.0)] = 0
            depths.append(z)
    np.save(DCACHE, np.stack(depths).astype(np.float32)); del fs; torch.cuda.empty_cache()
    for k in [k for k, m in list(sys.modules.items()) if (getattr(m, '__file__', None) or '').startswith('/content/FoundationStereo')]:
        del sys.modules[k]
    sys.path.remove('/content/FoundationStereo')
log('depth ready', len(depths))

fx, cx, cy = KR[0, 0], KR[0, 2], KR[1, 2]

# ---------- FoundationPose setup (gray textures: the ego stereo cameras are monochrome) ----------
os.chdir('/content/FoundationPose'); sys.path.insert(0, '/content/FoundationPose')
from estimater import FoundationPose, ScorePredictor, PoseRefinePredictor
from Utils import nvdiffrast_render, make_mesh_tensors
import nvdiffrast.torch as dr
scorer, refiner, glctx = ScorePredictor(), PoseRefinePredictor(), dr.RasterizeCudaContext()
def load_mesh(n):
    m = trimesh.load(mesh_path(n), force='mesh')
    try: m.visual = m.visual.to_color()
    except Exception as e: log('to_color failed', n, e)
    if os.environ.get('GRAY', '1') == '1':
        vc = np.asarray(m.visual.vertex_colors).copy()
        vc[:, :3] = (0.299 * vc[:, 0] + 0.587 * vc[:, 1] + 0.114 * vc[:, 2]).astype(np.uint8)[:, None]
        m.visual.vertex_colors = vc
    return m
meshes = {n: load_mesh(n) for n in names}

# ---------- frame-0 detection: SAM2 proposals x DINOv2 vs gray mesh renders (CNOS-style) + 3-D size gate ----------
from sam2.build_sam import build_sam2
from sam2.automatic_mask_generator import SAM2AutomaticMaskGenerator
gen = SAM2AutomaticMaskGenerator(build_sam2('configs/sam2.1/sam2.1_hiera_l.yaml', '/content/ckpt/sam2.1_hiera_large.pt', device='cuda'),
                                 points_per_side=32, pred_iou_thresh=0.7, stability_score_thresh=0.85)
img0 = rgb(rc[0]); props = [m['segmentation'] for m in gen.generate(img0) if m['area'] >= 400]
del gen; torch.cuda.empty_cache()
def extent3d(m):
    v, u = np.nonzero(m & (depths[0] > 0))
    if len(v) < 30: return 0.0
    z = depths[0][v, u]; X = np.stack([(u - cx) * z / fx, (v - cy) * z / fx, z], 1)
    X = X[::max(1, len(X) // 5000)]; X = X - np.median(X, 0)
    pr = X @ np.linalg.svd(X, full_matrices=False)[2].T
    return float((np.percentile(pr, 97, 0) - np.percentile(pr, 3, 0)).max())
def crop(img, m):
    v, u = np.nonzero(m); y0, y1, x0, x1 = v.min(), v.max() + 1, u.min(), u.max() + 1
    s = int(max(y1 - y0, x1 - x0) * 1.1) + 2; ys, xs = (y0 + y1) // 2 - s // 2, (x0 + x1) // 2 - s // 2
    im = np.where(m[..., None], img, 0).astype(np.uint8); pad = np.zeros((s, s, 3), np.uint8)
    a0, b0, a1, b1 = max(ys, 0), max(xs, 0), min(ys + s, img.shape[0]), min(xs + s, img.shape[1])
    pad[a0 - ys:a1 - ys, b0 - xs:b1 - xs] = im[a0:a1, b0:b1]
    return cv2.resize(pad, (224, 224), interpolation=cv2.INTER_AREA)
dino = torch.hub.load('facebookresearch/dinov2', 'dinov2_vitl14').cuda().eval()
MEAN = torch.tensor([0.485, 0.456, 0.406]).cuda()[:, None, None]; STD = torch.tensor([0.229, 0.224, 0.225]).cuda()[:, None, None]
def desc(crops):
    out = []
    with torch.no_grad():
        for k in range(0, len(crops), 64):
            x = (torch.as_tensor(np.stack(crops[k:k + 64])).cuda().float().permute(0, 3, 1, 2) / 255 - MEAN) / STD
            out.append(torch.nn.functional.normalize(dino(x), dim=-1))
    return torch.cat(out)
def templates(n):
    m = meshes[n]; c = m.bounds.mean(0); r = float(np.linalg.norm(m.extents)) / 2; dist = 4 * r
    Kt = np.array([[0.8 * 112 * dist / r, 0, 112], [0, 0.8 * 112 * dist / r, 112], [0, 0, 1]]); TP = []
    for d in trimesh.creation.icosphere(subdivisions=1).vertices:
        d = d / np.linalg.norm(d); z = -d; up = np.array([0, 0, 1.0]) if abs(z[2]) < 0.95 else np.array([0, 1.0, 0])
        x = np.cross(up, z); x /= np.linalg.norm(x); y = np.cross(z, x); Roc = np.stack([x, y, z], 1)
        M = np.eye(4); M[:3, :3] = Roc.T; M[:3, 3] = -Roc.T @ (c + d * dist); TP.append(M)
    col, dep, _ = nvdiffrast_render(K=Kt, H=224, W=224, ob_in_cams=torch.as_tensor(np.stack(TP)).float().cuda(), glctx=glctx,
                                    mesh_tensors=make_mesh_tensors(m), use_light=True)
    col = (col.clamp(0, 1) * 255).cpu().numpy().astype(np.uint8); msk = dep.cpu().numpy() > 0
    ks = [k for k in range(len(col)) if msk[k].sum() > 50]
    return desc([crop(col[k], msk[k]) for k in ks]), float(np.mean([col[k][msk[k]].mean() for k in ks]))
PD = desc([crop(img0, m) for m in props])
pint = np.array([img0[m].mean() for m in props]); pext = np.array([extent3d(m) for m in props])
S = np.full((len(names), len(props)), -10.0); LAM_I = float(os.environ.get('LAM_I', 0.3))
for a, n in enumerate(names):
    Tn, tint = templates(n); sim = (PD @ Tn.T).topk(min(5, len(Tn)), dim=1).values.mean(1).cpu().numpy()
    ext = float(meshes[n].bounding_box_oriented.extents.max()); ok = (pext > 0.3 * ext) & (pext < 1.3 * ext)
    S[a] = np.where(ok, sim - LAM_I * np.abs(pint - tint) / 255, -10.0)
    log('det', n, 'ext', round(ext, 3), 'tint', round(tint), [(int(k), round(S[a, k], 3), round(pext[k], 3), round(pint[k])) for k in np.argsort(-S[a])[:4]])
del dino; torch.cuda.empty_cache()
ests = {n: FoundationPose(model_pts=meshes[n].vertices, model_normals=meshes[n].vertex_normals, mesh=meshes[n],
                          scorer=scorer, refiner=refiner, debug_dir=f'{OUT}/dbg', debug=0, glctx=glctx) for n in names}
# render-and-compare verification: register FP on each object's top proposals, render, score depth agreement
# (matched / (matched + free-space violations)); comparable across masks unlike FoundationPose's own score
D0 = torch.as_tensor(depths[0]).cuda(); MT = {n: make_mesh_tensors(meshes[n]) for n in names}
def verify(n, pose):
    _, dr_, _ = nvdiffrast_render(K=KR, H=RSZ[1], W=RSZ[0], ob_in_cams=torch.as_tensor(pose[None]).float().cuda(), glctx=glctx, mesh_tensors=MT[n])
    r = dr_[0]; vis = (r > 0) & (D0 > 0)
    m = (vis & ((D0 - r).abs() < 0.015)).sum().item(); viol = (vis & (D0 > r + 0.015)).sum().item()
    return m / (m + viol + 1.0), m
TOPK = int(os.environ.get('TOPK', 4)); C = np.full_like(S, -10.0); VER = {}
for a, n in enumerate(names):
    for k in np.argsort(-S[a])[:TOPK]:
        if S[a, k] < -5: continue
        p = ests[n].register(K=KR, rgb=img0, depth=depths[0], ob_mask=props[k], iteration=5)
        v, m = verify(n, p); VER[f'{n}#{k}'] = [round(v, 3), m, round(float(S[a, k]), 3)]
        if m >= 200: C[a, k] = v + 0.5 * S[a, k]
log('verify', VER)
ri, ci = linear_sum_assignment(-C); MASK = {names[a]: props[k] for a, k in zip(ri, ci)}
DET = {names[a]: [int(k), float(S[a, k]), float(C[a, k])] for a, k in zip(ri, ci)}; log('proposals', len(props), 'assignment', DET)
vis = img0.copy(); cols = [(0, 0, 255), (0, 255, 0), (255, 0, 0), (0, 255, 255)]
for j, n in enumerate(names):
    m = MASK[n]; vis[m] = (0.5 * vis[m] + 0.5 * np.array(cols[j % 4])).astype(np.uint8)
cv2.imwrite(f'{OUT}/masks_f0.jpg', vis)
poses = {}
for n in names:
    t0 = time.time()
    P = [ests[n].register(K=KR, rgb=rgb(rc[0]), depth=depths[0], ob_mask=MASK[n], iteration=5)]
    for i in range(1, N):
        P.append(ests[n].track_one(rgb=rgb(rc[i]), depth=depths[i], K=KR, iteration=2))
    poses[n] = np.stack(P); log('tracked', n, 'sec', round(time.time() - t0, 1))

# ---------- camera: SIFT + stereo-depth PnP, tracked objects masked out, earliest usable keyframe ----------
OBJM = np.zeros((N, RSZ[1], RSZ[0]), np.uint8); ker = np.ones((31, 31), np.uint8)
for n in names:
    for j in range(0, N, 32):
        _, dr_, _ = nvdiffrast_render(K=KR, H=RSZ[1], W=RSZ[0], ob_in_cams=torch.as_tensor(poses[n][j:j + 32]).float().cuda(), glctx=glctx, mesh_tensors=MT[n])
        OBJM[j:j + 32] |= (dr_ > 0).cpu().numpy().astype(np.uint8)
sift = cv2.SIFT_create(nfeatures=4000); bf = cv2.BFMatcher(cv2.NORM_L2)
F = [sift.detectAndCompute(rc[i], (255 * (1 - cv2.dilate(OBJM[i], ker))).astype(np.uint8)) for i in range(N)]
del OBJM
def pnp(kf, i):
    kpK, dK = F[kf]; kpi, di = F[i]
    if dK is None or di is None or len(kpK) < 30 or len(kpi) < 30: return None, 0
    good = [p[0] for p in bf.knnMatch(dK, di, k=2) if len(p) == 2 and p[0].distance < 0.75 * p[1].distance]
    P3, P2_ = [], []
    for g in good:
        u, v = kpK[g.queryIdx].pt; z = depths[kf][int(round(v)), int(round(u))]
        if z <= 0: continue
        P3.append([(u - cx) * z / fx, (v - cy) * z / fx, z]); P2_.append(kpi[g.trainIdx].pt)
    if len(P3) < 30: return None, 0
    P3, P2_ = np.float32(P3), np.float32(P2_)
    ok, rv, tv, inl = cv2.solvePnPRansac(P3, P2_, KR, None, iterationsCount=2000, reprojectionError=1.5,
                                         confidence=0.999, flags=cv2.SOLVEPNP_SQPNP)
    if not ok or inl is None or len(inl) < 20: return None, 0
    inl = inl[:, 0]
    rv, tv = cv2.solvePnPRefineLM(P3[inl], P2_[inl], KR, None, rv, tv)
    M = np.eye(4); M[:3, :3] = cv2.Rodrigues(rv)[0]; M[:3, 3] = tv[:, 0]
    return M, len(inl)                                                     # cam_i <- cam_kf
KF_MIN = int(os.environ.get('KF_MIN', 250)); KF_OK = int(os.environ.get('KF_OK', 120))
W_C = [np.eye(4)]; kfs = [0]; ninl = [0]; used = [0]; fails = 0
for i in range(1, N):
    cand = []
    for k in dict.fromkeys([0] + kfs[-4:]):
        M, n_ = pnp(k, i)
        if M is not None: cand.append((k, M, n_))
    good = [c for c in cand if c[2] >= KF_OK]
    pick = good[0] if good else (max(cand, key=lambda c: c[2]) if cand else None)
    if pick is None:
        fails += 1; W_C.append(W_C[-1].copy()); ninl.append(0); used.append(-1); continue
    k, M, n_ = pick; W_C.append(W_C[k] @ np.linalg.inv(M)); ninl.append(n_); used.append(k)
    lat = [c for c in cand if c[0] == kfs[-1]]
    if (not lat or lat[0][2] < KF_MIN) and i > kfs[-1]: kfs.append(i)
W_C = np.stack(W_C)
log('vo keyframes', len(kfs), 'fails', fails, 'median inliers', int(np.median(ninl[1:])), 'min', int(np.min(ninl[1:])),
    'frames on kf0', int(np.sum(np.array(used) == 0)))
json.dump({'keyframes': kfs, 'inliers': ninl, 'used': used, 'fails': fails}, open(f'{OUT}/vo.json', 'w'))
np.savez(f'{OUT}/poses.npz', world_T_cam=W_C, **{f'cam_T_{n}': poses[n] for n in names})

# ---------- scoring (GT read only here) ----------
def T_of(p):  # [x,y,z,qw,qx,qy,qz] -> 4x4
    M = np.eye(4); M[:3, :3] = Rot.from_quat([p[4], p[5], p[6], p[3]]).as_matrix(); M[:3, 3] = p[:3]; return M
def xyzw(M):
    return np.r_[M[:3, 3], Rot.from_matrix(M[:3, :3]).as_quat()]
gt = {}
for row in tab['observation.objects'].iloc[:N]:
    for o in row: gt.setdefault(o['name'], []).append(T_of(np.array(o['pose'], float)))
gt = {k: np.stack(v) for k, v in gt.items()}
sys.path.insert(0, '/content/kit/v2d_submission_kit/metric_code/track_3')
A = importlib.import_module('AUC')
VERTS = {}
for n in names:
    pts, _ = trimesh.sample.sample_surface(trimesh.load(mesh_path(n), force='mesh'), 500, seed=0); VERTS[n] = np.asarray(pts)
def score(pred, objs):
    ach = np.stack([[xyzw(pred[n][i]) for n in objs] for i in range(N)])[:, None]
    ref = np.stack([[xyzw(gt[n][i]) for n in objs] for i in range(N)])[:, None]
    ach = A._warp_to_reference_start(ach, ref)
    add = A._object_add(ach, ref, np.stack([VERTS[n] for n in objs]))
    pos = np.linalg.norm(ach[..., :3] - ref[..., :3], axis=-1)[:, 0]
    return dict(AUC=float(A._add_auc(add)), SP_SR=float(np.mean(A._spider_success(ach, ref))),
                MP_SR=float(np.mean(A._maniptrans_success(ach, ref, np.arange(len(objs))))),
                MPPE_cm=float(A._mean_per_point_error_cm(ach, ref)), RPE_cm=float(A._relative_position_error_cm(ach, ref)),
                per_obj_AUC={n: float(A._add_auc(add[:, :, b:b + 1])) for b, n in enumerate(objs)},
                pos_err_cm_median={n: float(np.median(pos[:, b]) * 100) for b, n in enumerate(objs)},
                pos_err_cm_max={n: float(pos[:, b].max() * 100) for b, n in enumerate(objs)})
variants = {'vo': W_C}
for a in names: variants[f'anchor:{a}'] = np.stack([np.linalg.inv(M) for M in poses[a]])
res = {'episode': EP, 'objects': names, 'frames': N, 'fs_scale': FS_SCALE,
       'vo_stats': {'keyframes': len(kfs), 'fails': fails, 'median_inliers': int(np.median(ninl[1:]))},
       'det': DET, 'n_proposals': len(props), 'verify': VER,
       'gt_motion_extent_cm': {n: float(np.linalg.norm(gt[n][:, :3, 3] - gt[n][0, :3, 3], axis=1).max() * 100) for n in names}}
for v, WC in variants.items():
    pred = {n: np.stack([WC[i] @ poses[n][i] for i in range(N)]) for n in names}
    res[v] = score(pred, names)
    if v == 'vo': np.savez(f'{OUT}/poses_world_vo.npz', **pred)
json.dump(res, open(f'{OUT}/result.json', 'w'), indent=1)
for v in variants:
    r = res[v]; log(f'{v:28s} AUC {r["AUC"]:.3f} SP {r["SP_SR"]:.2f} MP {r["MP_SR"]:.2f} MPPE {r["MPPE_cm"]:.2f} RPE {r["RPE_cm"]:.2f}',
                    {n: round(x, 3) for n, x in r['per_obj_AUC'].items()})
log('DONE')
