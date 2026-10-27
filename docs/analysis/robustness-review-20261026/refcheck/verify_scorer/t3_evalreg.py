"""verify_scorer test 3 (GT-free): registration of one submitted mesh at a fixed Kaggle eval seed against many stand-in
hosts (public scan welded + decimated by quadric collapse (fast_simplification) or by vertex clustering, float32 copies),
and over N consecutive seeds at the full host. Reports the registration rotation angle and yaw about scan z.
Official _register_object_body from metric_code/track_3/AUC.py. Host anchor = scan surface centroid (my code).
Usage: python -I t3_evalreg.py LIB OBJ SEED OUT.json NSEEDS"""
import json, sys, time
sys.path.insert(0, '/home/user/v2d-track3/docs/analysis/robustness-review-20261026/refcheck/verify_scorer')
import numpy as np, trimesh, fast_simplification
from vs_core import *

lib, obj, seed, out, nseeds = sys.argv[1], sys.argv[2], int(sys.argv[3]), sys.argv[4], int(sys.argv[5])
v, f = load_vf(scan_path(obj))
anchor = my_centroid(v, f)
m = trimesh.Trimesh(v, f, process=False); m.merge_vertices(); m.remove_unreferenced_vertices()
wv, wf = np.asarray(m.vertices, np.float64), np.asarray(m.faces, np.int64)
cand = budget(f'{LIB}/{lib}/{obj}.glb')
hosts = {'full_soup': (v, f), 'full_welded': (wv, wf), 'full_welded_f32': (wv.astype(np.float32).astype(np.float64), wf)}
for k in (60000, 50000, 40000, 30000, 25000, 20000, 16000, 14000, 12000, 10000, 8192, 6000, 5000, 4096, 3000, 2500, 2000):
    dv, df = fast_simplification.simplify(wv, wf, target_count=k)
    hosts[f'qd{k}'] = (np.asarray(dv, np.float64), np.asarray(df, np.int64))
for k in (50000, 20000, 8000, 4096):
    hosts[f'vc{k}'] = cluster_decimate(wv, wf, k)


def run(H, s):
    ca, Rb = OFF._register_object_body(cand, H, anchor, s)
    e = Rot.from_matrix(Rb).as_euler('ZYX', degrees=True)
    return dict(rot_deg=round(reg_angle(Rb), 2), yaw=round(float(e[0]), 2), pitch=round(float(e[1]), 2), roll=round(float(e[2]), 2))


res = dict(lib=lib, obj=obj, seed=seed, hosts={}, seeds_full={})
t0 = time.time()
for k, H in hosts.items():
    res['hosts'][k] = dict(faces=len(H[1]), **run(H, seed))
    print(k, res['hosts'][k], flush=True)
for s in range(nseeds):
    res['seeds_full'][seed + s] = run(hosts['full_soup'], seed + s)
res['n_host_flips_gt90'] = sum(r['rot_deg'] > 90 for r in res['hosts'].values())
res['n_hosts'] = len(res['hosts'])
res['n_seed_flips_gt90'] = sum(r['rot_deg'] > 90 for r in res['seeds_full'].values())
res['n_seed_gt5deg_from_median_yaw'] = int(np.sum(np.abs(np.array([r['yaw'] for r in res['seeds_full'].values()])
                                                           - np.median([r['yaw'] for r in res['seeds_full'].values()])) > 5)) if nseeds else 0
res['seconds'] = round(time.time() - t0, 1)
json.dump(res, open(out, 'w'), indent=1)
print({k: res[k] for k in res if k not in ('hosts', 'seeds_full')})
