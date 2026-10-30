"""Ceiling of NVIDIA's default Sharpa timing (motion_speed 0.5, fps 20.2541 in the reference) on Track 3 public
episodes, assuming PERFECT perception and a PERFECT policy: the packer keeps rows 0..N-1 of ~2N control steps, so
packed frame f holds the true pose at source position p_f = f (N-1)/(M-1) ~ 0.508 f (note 06, case A).
Scored with the kit's Track 3 metric functions (rigid warp from slot 0 at frame 0, 500 surface samples per public
mesh), the same helper calls as pipeline/score_sim.py. Also the 'nothing moves' floor. GT is read only here (scoring).
Usage: python timing_ceiling.py KIT_DIR DATA_DIR"""
import sys, os, glob, json, importlib, numpy as np, trimesh, pyarrow.parquet as pq
from scipy.spatial.transform import Rotation as R, Slerp
KIT, D = sys.argv[1], sys.argv[2]
sys.path.insert(0, f'{KIT}/metric_code/track_3'); A = importlib.import_module('AUC')
def mesh_pts(n):
    c = glob.glob(f'{D}/mesh/{n}/{n}.glb') + glob.glob(f'{D}/mesh/{n}/*.glb') + glob.glob(f'{D}/mesh/{n}/*.obj')
    return np.asarray(trimesh.sample.sample_surface(trimesh.load(c[0], force='mesh'), 500, seed=0)[0])
def score(a, r, V, B):
    a, r = a[:, None], r[:, None]
    a = A._warp_to_reference_start(a, r); add = A._object_add(a, r, V)
    return dict(AUC=float(A._add_auc(add)), SP=float(np.mean(A._spider_success(a, r))),
                MP=float(np.mean(A._maniptrans_success(a, r, np.arange(B)))), MPPE=float(A._mean_per_point_error_cm(a, r)))
rows = []
for f in sorted(glob.glob(f'{D}/data/chunk-000/episode_*.parquet')):
    ep = int(os.path.basename(f)[8:14]); tab = pq.read_table(f).to_pandas()
    names = [o['name'] for o in tab['observation.objects'].iloc[0]]; B = len(names); N = len(tab)
    gt = np.stack([[(lambda p: np.r_[p[:3], p[4:7], p[3]])(np.array([o for o in tab['observation.objects'].iloc[i]
                    if o['name'] == n][0]['pose'], float)) for n in names] for i in range(N)])   # xyz + xyzw
    M = int(2 * (N - 1) * 20.0 / 20.2541); p = np.arange(N) * (N - 1) / (M - 1)
    warped = np.empty_like(gt)
    for b in range(B):
        for k in range(3): warped[:, b, k] = np.interp(p, np.arange(N), gt[:, b, k])
        warped[:, b, 3:] = Slerp(np.arange(N), R.from_quat(gt[:, b, 3:]))(p).as_quat()
    V = np.stack([mesh_pts(n) for n in names])
    rows.append(dict(ep=ep, objects=names, N=N, default_timing=score(warped, gt, V, B),
                     nothing_moves=score(np.repeat(gt[:1], N, 0), gt, V, B)))
    print(ep, B, N, round(rows[-1]['default_timing']['AUC'], 4), round(rows[-1]['nothing_moves']['AUC'], 4), flush=True)
mean = lambda key, m: float(np.mean([r[key][m] for r in rows]))
summ = {k: {m: round(mean(k, m), 4) for m in ('AUC', 'SP', 'MP', 'MPPE')} for k in ('default_timing', 'nothing_moves')}
print(json.dumps(summ, indent=1))
json.dump(dict(summary=summ, episodes=rows), open(os.path.join(os.path.dirname(__file__), 'timing_ceiling.json'), 'w'), indent=1)
