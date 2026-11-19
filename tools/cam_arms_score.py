"""Score the camera-arms test (2026-11-19, docs/analysis/camarms-20261119/PREREG.md) against mocap.

Runs after every inference output exists; this is the only step that reads ground truth (the public parquet's
object poses). Object tracks come from arm S (perc2 with the public scans); each camera arm only swaps world_T_cam:
  C    perc2's own camera (S/ep<N>/poses.npz world_T_cam)
  VD VD2 VM VDH VS   MetricTrail cameras (V/<arm>/ep<N>.npz world_T_cam, from pipeline/vipe_cam.py)
  M    2 Nov GT-free room-map camera (MAP/ep<N>.npz world_T_cam)
  SD   perc2 re-run on MetricTrail's DA3 depth (SD/ep<N>/poses.npz, its own camera and tracks), compared with S/C.
Metrics are perc2's scoring block (kit metric functions, 500 points per public scan, seed 0) plus frames > 3 cm.
GT-free diagnostics: object-position gap to C (p95/max mm), camera gap to M (translation p95 mm, rotation p95 deg),
path-length ratio to M.
Usage: python cam_arms_score.py ROOT OUT_JSON [--map DIR] [--eps "0 2 ..."] [--t3 /content/t3] [--kit DIR]
  ROOT holds S/, SD/ and V/ as written by ops/jobs/cam_arms.sh.
"""
import argparse, json, os, sys, importlib
import numpy as np, trimesh
import pyarrow.parquet as pq
from scipy.spatial.transform import Rotation as Rot

ap = argparse.ArgumentParser()
ap.add_argument('root'); ap.add_argument('out')
ap.add_argument('--map', default=None); ap.add_argument('--t3', default='/content/t3')
ap.add_argument('--kit', default='/content/kit/v2d_submission_kit/metric_code/track_3')
ap.add_argument('--eps', default='0 2 11 12 13 18 21 22 23 24 26 27 31 39 40 41 42 43 44 45')
ap.add_argument('--arms', default='C VD VD2 VM VDH VS M')
a = ap.parse_args()
sys.path.insert(0, a.kit); A = importlib.import_module('AUC')
EPS = [int(e) for e in a.eps.split()]; ARMS = a.arms.split()

def T_of(p):  # [x,y,z,qw,qx,qy,qz] -> 4x4 (public parquet convention)
    M = np.eye(4); M[:3, :3] = Rot.from_quat([p[4], p[5], p[6], p[3]]).as_matrix(); M[:3, 3] = p[:3]; return M
def xyzw(M):
    return np.r_[M[:3, 3], Rot.from_matrix(M[:3, :3]).as_quat()]
def scan_path(n):
    p = f'{a.t3}/mesh/{n}/{n}.glb'
    return p if os.path.exists(p) else f'{a.t3}/mesh/{n}/{n}_visual.glb'
VERTS = {}
def verts(n):
    if n not in VERTS:
        pts, _ = trimesh.sample.sample_surface(trimesh.load(scan_path(n), force='mesh'), 500, seed=0)
        VERTS[n] = np.asarray(pts)
    return VERTS[n]

def score(pred, gt, objs, N):
    ach = np.stack([[xyzw(pred[n][i]) for n in objs] for i in range(N)])[:, None]
    ref = np.stack([[xyzw(gt[n][i]) for n in objs] for i in range(N)])[:, None]
    ach = A._warp_to_reference_start(ach, ref)
    add = A._object_add(ach, ref, np.stack([verts(n) for n in objs]))
    pos = np.linalg.norm(ach[..., :3] - ref[..., :3], axis=-1)[:, 0]
    return dict(AUC=float(A._add_auc(add)), SP_SR=float(np.mean(A._spider_success(ach, ref))),
                MP_SR=float(np.mean(A._maniptrans_success(ach, ref, np.arange(len(objs))))),
                MPPE_cm=float(A._mean_per_point_error_cm(ach, ref)), RPE_cm=float(A._relative_position_error_cm(ach, ref)),
                per_obj_AUC={n: float(A._add_auc(add[:, :, b:b + 1])) for b, n in enumerate(objs)},
                frames_gt3cm=int((pos > 0.03).sum()),
                pos_err_cm_median={n: float(np.median(pos[:, b]) * 100) for b, n in enumerate(objs)})

def rot_deg(R):
    return float(np.degrees(np.arccos(np.clip((np.trace(R) - 1) / 2, -1, 1))))

res = {'arms': ARMS, 'episodes': {}}
for ep in EPS:
    E = {}
    S = f'{a.root}/S/ep{ep}/poses.npz'
    if not os.path.exists(S):
        res['episodes'][ep] = {'error': 'no S track'}; continue
    z = np.load(S); WC = z['world_T_cam']; objs = [k[6:] for k in z.files if k.startswith('cam_T_')]
    tab = pq.read_table(f'{a.t3}/ep{ep}.parquet').to_pandas()
    order = [o['name'] for o in tab['observation.objects'].iloc[0]]
    objs = [n for n in order if n in objs]                                  # slot order (slot 0 = alignment anchor)
    camT = {n: z[f'cam_T_{n}'] for n in objs}; N = len(WC)
    gt = {}                                                                  # ground truth: read here, after inference
    for row in tab['observation.objects'].iloc[:N]:
        for o in row: gt.setdefault(o['name'], []).append(T_of(np.array(o['pose'], float)))
    gt = {k: np.stack(v) for k, v in gt.items()}
    cams = {'C': WC}
    for arm in ARMS:
        if arm == 'C': continue
        f = f'{a.map}/ep{ep}.npz' if arm == 'M' else f'{a.root}/V/{arm}/ep{ep}.npz'
        if arm == 'M' and not a.map: continue
        if os.path.exists(f):
            W = np.load(f)['world_T_cam'][:N]
            if len(W) == N and np.isfinite(W).all(): cams[arm] = W
            else: E[arm] = {'error': f'camera length {len(W)} vs {N} or non-finite'}
        else:
            E[arm] = {'error': 'missing (arm crashed or not run)'}
    world = {arm: {n: W @ camT[n] for n in objs} for arm, W in cams.items()}
    for arm, pred in world.items():
        r = score(pred, gt, objs, N)
        if arm != 'C':                                                       # GT-free gap to the control
            gap = np.concatenate([np.linalg.norm(pred[n][:, :3, 3] - world['C'][n][:, :3, 3], axis=1) for n in objs])
            r['obj_gap_to_C_mm'] = dict(p95=float(np.percentile(gap, 95) * 1000), max=float(gap.max() * 1000))
        if 'M' in cams and arm != 'M':                                       # GT-free camera gap to the room map
            WM = cams['M']; W = cams[arm]
            dt = np.linalg.norm(W[:, :3, 3] - WM[:, :3, 3], axis=1)
            dr = np.array([rot_deg(W[i][:3, :3].T @ WM[i][:3, :3]) for i in range(N)])
            pl = lambda X: float(np.linalg.norm(np.diff(X[:, :3, 3], axis=0), axis=1).sum())
            r['cam_gap_to_M'] = dict(trans_p95_mm=float(np.percentile(dt, 95) * 1000), rot_p95_deg=float(np.percentile(dr, 95)),
                                     path_ratio=pl(W) / max(pl(WM), 1e-9))
        E[arm] = r
    SD = f'{a.root}/SD/ep{ep}/poses.npz'                                     # mono-depth perception, own camera + tracks
    if os.path.exists(SD):
        z2 = np.load(SD)
        if all(f'cam_T_{n}' in z2.files for n in objs) and len(z2['world_T_cam']) == N:
            E['SD'] = score({n: z2['world_T_cam'] @ z2[f'cam_T_{n}'] for n in objs}, gt, objs, N)
        else:
            E['SD'] = {'error': 'SD output incomplete'}
    res['episodes'][ep] = dict(objects=objs, frames=N, arms=E)
    print(ep, {k: round(v['AUC'], 4) for k, v in E.items() if 'AUC' in v}, flush=True)

# summary vs C (camera arms) and SD vs C (= S as tracked, perc2's camera)
summ = {}
for arm in ARMS[1:] + ['SD']:
    d = []
    for ep in EPS:
        e = res['episodes'].get(ep, {}).get('arms', {})
        if 'C' in e and 'AUC' in e['C']:
            x = e.get(arm, {})
            c = e['C']
            if 'AUC' in x:
                d.append((ep, x['AUC'] - c['AUC'], x['MPPE_cm'] - c['MPPE_cm'], x['RPE_cm'] - c['RPE_cm'],
                          x['frames_gt3cm'], c['frames_gt3cm'], False))
            elif arm == 'VD':                                                # PREREG: a crashed VD episode counts as C
                d.append((ep, 0.0, 0.0, 0.0, c['frames_gt3cm'], c['frames_gt3cm'], True))
    if not d: continue
    dA = np.array([x[1] for x in d])
    summ[arm] = dict(n=len(d), crashed=[x[0] for x in d if x[6]], mean_dAUC=float(dA.mean()),
                     mean_dMPPE_cm=float(np.mean([x[2] for x in d])), mean_dRPE_cm=float(np.mean([x[3] for x in d])),
                     better=int((dA > 0.0005).sum()), worse=int((dA < -0.0005).sum()),
                     worst=(int(d[int(dA.argmin())][0]), float(dA.min())), best=(int(d[int(dA.argmax())][0]), float(dA.max())),
                     frames_gt3cm=int(sum(x[4] for x in d)), frames_gt3cm_C=int(sum(x[5] for x in d)),
                     per_ep={int(x[0]): round(float(x[1]), 4) for x in d})
# MetricTrail's own noise: VD2 vs VD
nz = [abs(res['episodes'][ep]['arms']['VD2']['AUC'] - res['episodes'][ep]['arms']['VD']['AUC'])
      for ep in EPS if 'AUC' in res['episodes'].get(ep, {}).get('arms', {}).get('VD', {})
      and 'AUC' in res['episodes'].get(ep, {}).get('arms', {}).get('VD2', {})]
noise = float(np.mean(nz)) if nz else None
g = summ.get('VD')
if g:
    c1 = g['mean_dAUC'] >= 0.005 and (noise is None or g['mean_dAUC'] >= 2 * noise)
    c2 = g['worst'][1] >= -0.02
    c3 = g['mean_dMPPE_cm'] <= 0
    c4 = g['frames_gt3cm'] <= g['frames_gt3cm_C']
    summ['gate_VD'] = dict(noise_VD2_vs_VD=noise, c1_mean=c1, c2_worst=c2, c3_mppe=c3, c4_frames=c4,
                           verdict='PASS' if (c1 and c2 and c3 and c4) else 'FAIL',
                           falsified=g['mean_dAUC'] <= 0)
res['summary'] = summ
res['mean_AUC'] = {arm: float(np.mean([res['episodes'][ep]['arms'][arm]['AUC'] for ep in EPS
                                       if 'AUC' in res['episodes'].get(ep, {}).get('arms', {}).get(arm, {})]))
                   for arm in ARMS + ['SD'] if any('AUC' in res['episodes'].get(ep, {}).get('arms', {}).get(arm, {}) for ep in EPS)}
json.dump(res, open(a.out, 'w'), indent=1)
print(json.dumps({'mean_AUC': res['mean_AUC'], 'summary': {k: {kk: vv for kk, vv in v.items() if kk != 'per_ep'}
                  for k, v in summ.items()}}, indent=1))
