"""Exp1: perception-only accuracy on a public Track 3 episode (default 12: blue_cup + plastic_dish_rack).

Pipeline (no ground truth used before scoring):
  mono stereo pair c/b -> rectify -> FoundationStereo depth (rectified-left frame)
  frame 0: OWLv2 text boxes -> SAM2 masks
  FoundationPose (public scan as template) register on frame 0, track_one on later frames
  world = static dish rack frame: obj_world(t) = inv(cam_T_rack(t)) @ cam_T_obj(t)
Scoring: official kit Track 3 metric functions on the cup trajectory vs mocap GT.
Env: EP (12), FS_SCALE (0.5), OUT dir. Run from anywhere with the system python.
"""
import os, sys, json, time, importlib
import numpy as np, cv2, torch, trimesh
import pyarrow.parquet as pq
from scipy.spatial.transform import Rotation as Rot

os.environ.setdefault('TORCH_FORCE_NO_WEIGHTS_ONLY_LOAD', '1')
EP = int(os.environ.get('EP', 12))
FS_SCALE = float(os.environ.get('FS_SCALE', 0.5))
D = '/content/t3'
OUT = os.environ.get('OUT', f'/content/exp1_ep{EP}')
os.makedirs(OUT, exist_ok=True)
STATIC, MOVING = 'plastic_dish_rack', 'blue_cup'
PROMPT = {'blue_cup': 'a cup', 'plastic_dish_rack': 'a dish rack'}
t_all = time.time()
def log(*a):
    print(f'[{time.time() - t_all:7.1f}s]', *a, flush=True)

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
log('rectified focal', round(FR, 1), 'baseline m', round(BASE, 4))

def frames(path):
    cap = cv2.VideoCapture(path); out = []
    while True:
        ok, f = cap.read()
        if not ok: break
        out.append(cv2.cvtColor(f, cv2.COLOR_BGR2GRAY))
    return out
fc, fb = frames(f'{D}/v/ep{EP}_c.mp4'), frames(f'{D}/v/ep{EP}_b.mp4')
N = min(len(fc), len(fb))
rc = [cv2.remap(fc[i], MC[0], MC[1], cv2.INTER_LINEAR) for i in range(N)]
rb = [cv2.remap(fb[i], MB[0], MB[1], cv2.INTER_LINEAR) for i in range(N)]
rgb = lambda g: np.repeat(g[..., None], 3, 2)
log('frames c/b', len(fc), len(fb))
cv2.imwrite(f'{OUT}/rect_pair_f0.jpg', np.hstack([rc[0], rb[0]]))

# ---------- FoundationStereo depth ----------
sys.path.insert(0, '/content/FoundationStereo')
from omegaconf import OmegaConf
from core.utils.utils import InputPadder
from core.foundation_stereo import FoundationStereo
CK = '/content/FoundationStereo/pretrained_models/23-51-11/model_best_bp2.pth'
cfg = OmegaConf.load(os.path.join(os.path.dirname(CK), 'cfg.yaml'))
cfg['valid_iters'] = 32; cfg['hiera'] = 0
cfg['vit_size'] = cfg.get('vit_size', 'vitl')
DCACHE = f'{OUT}/depths_fs{FS_SCALE}.npy'
depths = list(np.load(DCACHE).astype(np.float32)) if os.path.exists(DCACHE) else []
if not depths:
    fs = FoundationStereo(cfg); fs.load_state_dict(torch.load(CK, weights_only=False)['model']); fs.cuda().eval()
with torch.no_grad():
    for i in (range(N) if len(depths) == 0 else []):
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
        if i % 50 == 0: log('stereo', i, 'median depth m', float(np.median(z[z > 0])))
if not os.path.exists(DCACHE):
    np.save(DCACHE, np.stack(depths).astype(np.float32)); del fs; torch.cuda.empty_cache()
log('depth ready', len(depths))
dv = np.clip(depths[0] / 1.5 * 255, 0, 255).astype(np.uint8)
cv2.imwrite(f'{OUT}/depth_f0.jpg', cv2.applyColorMap(dv, cv2.COLORMAP_JET))

# ---------- frame-0 detection (OWLv2) + masks (SAM2) ----------
from PIL import Image
from transformers import Owlv2Processor, Owlv2ForObjectDetection
proc = Owlv2Processor.from_pretrained('google/owlv2-base-patch16-ensemble')
det = Owlv2ForObjectDetection.from_pretrained('google/owlv2-base-patch16-ensemble').cuda().eval()
pil = Image.fromarray(rgb(rc[0])); names = [MOVING, STATIC]
inp = proc(text=[[PROMPT[n] for n in names]], images=pil, return_tensors='pt').to('cuda')
with torch.no_grad(): o = det(**inp)
s = max(pil.size)
pp = getattr(proc, 'post_process_grounded_object_detection', None) or proc.post_process_object_detection
res = pp(outputs=o, threshold=0.02, target_sizes=torch.tensor([[s, s]]).cuda())[0]
boxes = {}
for j, n in enumerate(names):
    sel = (res['labels'] == j).nonzero().flatten()
    if len(sel) == 0: raise SystemExit(f'no detection for {n}')
    k = sel[res['scores'][sel].argmax()]
    boxes[n] = res['boxes'][k].cpu().numpy(); log('box', n, boxes[n].round(1), 'score', float(res['scores'][k]))
del det; torch.cuda.empty_cache()
from sam2.build_sam import build_sam2
from sam2.sam2_image_predictor import SAM2ImagePredictor
sp2 = SAM2ImagePredictor(build_sam2('configs/sam2.1/sam2.1_hiera_l.yaml', '/content/ckpt/sam2.1_hiera_large.pt', device='cuda'))
sp2.set_image(rgb(rc[0])); masks = {}
for n in names:
    m, sc, _ = sp2.predict(box=boxes[n], multimask_output=False); masks[n] = m[0] > 0
    log('mask', n, int(masks[n].sum()), 'px')
del sp2; torch.cuda.empty_cache()
vis = rgb(rc[0]).copy()
for n, col in zip(names, [(0, 0, 255), (0, 255, 0)]):
    vis[masks[n]] = (0.5 * vis[masks[n]] + 0.5 * np.array(col)).astype(np.uint8)
cv2.imwrite(f'{OUT}/masks_f0.jpg', vis)

# ---------- FoundationPose ----------
for k in [k for k, m in list(sys.modules.items()) if (getattr(m, '__file__', None) or '').startswith('/content/FoundationStereo')]: del sys.modules[k]
sys.path.remove('/content/FoundationStereo')
os.chdir('/content/FoundationPose'); sys.path.insert(0, '/content/FoundationPose')
from estimater import FoundationPose, ScorePredictor, PoseRefinePredictor
import nvdiffrast.torch as dr
scorer, refiner, glctx = ScorePredictor(), PoseRefinePredictor(), dr.RasterizeCudaContext()
def load_mesh(n):
    m = trimesh.load(f'{D}/mesh/{n}/{n}.glb', force='mesh')
    try: m.visual = m.visual.to_color()
    except Exception as e: log('to_color failed', n, e)
    return m
poses = {}
for n in names:
    mesh = load_mesh(n); t0 = time.time()
    est = FoundationPose(model_pts=mesh.vertices, model_normals=mesh.vertex_normals, mesh=mesh, scorer=scorer,
                         refiner=refiner, debug_dir=f'{OUT}/dbg_{n}', debug=0, glctx=glctx)
    P = [est.register(K=KR, rgb=rgb(rc[0]), depth=depths[0], ob_mask=masks[n], iteration=5)]
    for i in range(1, N):
        P.append(est.track_one(rgb=rgb(rc[i]), depth=depths[i], K=KR, iteration=2))
    poses[n] = np.stack(P); log('foundationpose', n, 'frames', N, 'sec', round(time.time() - t0, 1))
np.savez(f'{OUT}/poses_cam.npz', **poses)

# ---------- world (static rack) + scoring with the official kit functions ----------
def T_of(p):  # [x,y,z,qw,qx,qy,qz] -> 4x4
    M = np.eye(4); M[:3, :3] = Rot.from_quat([p[4], p[5], p[6], p[3]]).as_matrix(); M[:3, 3] = p[:3]; return M
def xyzw(M):
    q = Rot.from_matrix(M[:3, :3]).as_quat(); return np.r_[M[:3, 3], q]
tab = pq.read_table(f'{D}/ep{EP}.parquet').to_pandas(); gt = {}
for row in tab['observation.objects']:
    for o in row: gt.setdefault(o['name'], []).append(T_of(np.array(o['pose'], float)))
gt = {k: np.stack(v)[:N] for k, v in gt.items()}
world_T_cam = np.stack([np.linalg.inv(M) for M in poses[STATIC]])
pred = {n: np.stack([world_T_cam[i] @ poses[n][i] for i in range(N)]) for n in names}
np.savez(f'{OUT}/poses_world.npz', **pred)

sys.path.insert(0, '/content/kit/v2d_submission_kit/metric_code/track_3')
A = importlib.import_module('AUC')
def score(objs):
    ach = np.stack([[xyzw(pred[n][i]) for n in objs] for i in range(N)])[:, None]   # (T,1,B,7)
    ref = np.stack([[xyzw(gt[n][i]) for n in objs] for i in range(N)])[:, None]
    ach = A._warp_to_reference_start(ach, ref)
    verts = []
    for n in objs:
        m = trimesh.load(f'{D}/mesh/{n}/{n}.glb', force='mesh'); pts, _ = trimesh.sample.sample_surface(m, 500, seed=0)
        verts.append(np.asarray(pts))
    add = A._object_add(ach, ref, np.stack(verts))
    pos = np.linalg.norm(ach[..., :3] - ref[..., :3], axis=-1)[:, 0]   # (T,B)
    return dict(objects=objs, AUC=float(A._add_auc(add)), SP_SR=float(np.mean(A._spider_success(ach, ref))),
                MP_SR=float(np.mean(A._maniptrans_success(ach, ref, np.arange(len(objs))))),
                MPPE_cm=float(A._mean_per_point_error_cm(ach, ref)),
                RPE_cm=float(A._relative_position_error_cm(ach, ref)),
                pos_err_cm_median=float(np.median(pos) * 100), pos_err_cm_p90=float(np.percentile(pos, 90) * 100),
                pos_err_cm_max=float(pos.max() * 100))
res = {'episode': EP, 'frames': N, 'fs_scale': FS_SCALE, 'cup_only': score([MOVING]), 'both': score([MOVING, STATIC])}
gt_motion = np.linalg.norm(gt[MOVING][:, :3, 3] - gt[MOVING][0, :3, 3], axis=1).max() * 100
res['gt_cup_motion_extent_cm'] = float(gt_motion)
json.dump(res, open(f'{OUT}/result.json', 'w'), indent=1)
print(json.dumps(res, indent=1))
log('DONE')
