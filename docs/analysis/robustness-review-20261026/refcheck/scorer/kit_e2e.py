"""End-to-end check of the submission path on a stored PUBLIC rollout (part 3 of the scorer check).

Runs the kit's UNMODIFIED packer (tools/pack_submission.py) on one public-episode evaluator rollout, then the five
UNMODIFIED official Kaggle metric files (metric_code/track_3/{AUC,SP-SR,MP-SR,RPE,MPPE}.py, function score()) on the
packed file against a host "solution" built from the public mocap and the public scan, with the same stand-ins as
pipeline/score_registered.py (anchor = scan surface centroid, 1000 surface points seed 7+slot, PCA symmetry axes).
The packer's inputs are only made to accept a public episode: a scratch copy of the kit whose roster
(data/track_3_evaluation_objects.json), config scored_episodes and sample grid name this one episode. Meshes are the
library glbs the rollout's simulator assets were built from (checked separately in check_pack.py).

Compare the printed scores with `pipeline/score_registered.py EP RESULTS_DIR --meshes LIB` on the same rollout ('sim').
Ground truth (public mocap) is read only to build the host solution, after inference.
Usage: python -I kit_e2e.py EP RESULTS_DIR LIB_DIR --t3 T3 --kit KIT --work WORKDIR --out OUT.json
"""
import argparse, hashlib, importlib.util, json, os, shutil, subprocess, sys
import numpy as np, pandas as pd, trimesh, pyarrow.parquet as pq

p = argparse.ArgumentParser()
p.add_argument('ep', type=int); p.add_argument('results'); p.add_argument('lib')
p.add_argument('--t3', required=True); p.add_argument('--kit', required=True); p.add_argument('--work', required=True)
p.add_argument('--out', required=True)
p.add_argument('--pack_only', action='store_true', help='stop after packing (test)')
p.add_argument('--host_faces', type=int, default=0, help='decimate the host scan to this many faces (0 = full scan)')
a = p.parse_args()
ep = a.ep
W = os.path.join(a.work, f'ep{ep}'); shutil.rmtree(W, ignore_errors=True); os.makedirs(W)

# 1. scratch kit: unmodified code, roster / config / sample naming this public episode only
K = os.path.join(W, 'kit')
shutil.copytree(a.kit, K, ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
tab = pq.read_table(f'{a.t3}/ep{ep}.parquet').to_pandas()
names = [str(o['name']) for o in tab['observation.objects'].iloc[0]]
T = len(tab)
json.dump({'episodes': {str(ep): names}}, open(f'{K}/data/track_3_evaluation_objects.json', 'w'))
cfg = json.load(open(f'{K}/config/tracks.json')); cfg['tracks']['track_3']['scored_episodes'] = [ep]
json.dump(cfg, open(f'{K}/config/tracks.json', 'w'), indent=1)
sample = pd.read_parquet(f'{a.kit}/data/track_3_sample_submission.parquet')
rows = [f'track_3/e{ep:06d}/w000/f{f:06d}/o{s}' for f in range(T) for s in range(len(names))]
tmpl = sample.iloc[[0]].copy()
smp = pd.concat([tmpl] * len(rows), ignore_index=True); smp['row_id'] = rows
smp.to_parquet(f'{K}/data/track_3_sample_submission.parquet', index=False)

# 2. packer inputs: the rollout (world 0 only is packed), the library meshes as meshes/episode_XXXXXX/<obj>.glb
RD = os.path.join(W, 'results'); os.makedirs(RD)
for x in ('.parquet', '.json'):
    shutil.copy(os.path.join(a.results, f'episode_{ep:06d}{x}'), RD)
MD = os.path.join(W, 'meshes', f'episode_{ep:06d}'); os.makedirs(MD)
for n in names:
    shutil.copy(f'{a.lib}/{n}.glb', f'{MD}/{n}.glb')
SUB = os.path.join(W, 'sub.parquet')
cmd = [sys.executable, '-I', 'tools/pack_submission.py', '--track', 'track_3', '--results', RD, '--meshes',
       os.path.join(W, 'meshes'), '--code-commit', 'https://github.com/example/example/commit/' + '0' * 40,
       '--eval-script', f'{K}/flash_chord/scripts/evaluate_policy.py', '-o', SUB]
r = subprocess.run(cmd, cwd=K, capture_output=True, text=True)
open(os.path.join(W, 'pack.log'), 'w').write(r.stdout + r.stderr)
if r.returncode:
    raise SystemExit('packer failed:\n' + r.stdout[-2000:] + r.stderr[-2000:])
sub = pd.read_parquet(SUB)
if a.pack_only:
    print(r.stdout[-3000:]); print(sub.head()); raise SystemExit(0)

# 3. host solution from the public mocap + public scan (stand-ins identical to pipeline/score_registered.py)
sys.path.insert(0, K)
from v2dlb.object_mesh import _surface_moments
from v2dlb.mesh_common import _sample_mesh_surface
from v2dlb.track3_pose import _encode_archive


def scan_path(n):
    q = f'{a.t3}/mesh/{n}/{n}.glb'
    return q if os.path.exists(q) else f'{a.t3}/mesh/{n}/{n}_visual.glb'


geo = {'names': np.array(names)}
for i, n in enumerate(names):
    m = trimesh.load(scan_path(n), force='mesh')
    v, f = np.asarray(m.vertices, np.float64), np.asarray(m.faces, np.int64)
    c, _ = _surface_moments(v, f)
    pts = _sample_mesh_surface(v, f, 1000, 7 + i)                        # absolute; the scorer subtracts the anchor
    axis, order = np.zeros(3), 0
    if n in ('beige_cup', 'blue_cup', 'white_pot_lid'):
        w, U = np.linalg.eigh(np.cov((pts - c).T))
        if n == 'white_pot_lid':
            axis, order = U[:, 0], 2
        else:
            k = int(np.argmax([abs(w[j] - np.mean(np.delete(w, j))) for j in range(3)]))
            axis, order = U[:, k], 360
    if a.host_faces:
        import fast_simplification
        v, f = fast_simplification.simplify(v, f, target_count=a.host_faces)
    geo.update({f'v{i}': v, f'f{i}': f, f'anchor{i}': c, f'points{i}': pts, f'axis{i}': axis, f'order{i}': np.int64(order)})
payload = _encode_archive(**geo)
decoded_bytes = sum(x.nbytes for x in geo.values())


def xyzw(o):
    q = np.array(o['pose'], float)
    return np.r_[q[:3], q[4:7], q[3]]


sol = []
for fr in range(T):
    objs = {str(o['name']): o for o in tab['observation.objects'].iloc[fr]}
    for s, n in enumerate(names):
        q = xyzw(objs[n])
        sol.append(dict(row_id=f'track_3/e{ep:06d}/w000/f{fr:06d}/o{s}', episode_index=ep, world_index=0,
                        frame_index=fr, object_slot=s, object_name=n,
                        **{f'ref_{c}': q[j] for j, c in enumerate(['pos_x', 'pos_y', 'pos_z', 'quat_x', 'quat_y',
                                                                   'quat_z', 'quat_w'])}))
sol = pd.DataFrame(sol); sol['reference_geometry_b64'] = ''; sol.loc[0, 'reference_geometry_b64'] = payload

# 4. the five official metric files, unmodified
res = {'episode': ep, 'objects': names, 'frames': T, 'rows': len(sub), 'host_faces': a.host_faces or 'full scan',
       'host_geometry_decoded_bytes': int(decoded_bytes), 'host_limit_bytes': 16_000_000,
       'packed_sha256': hashlib.sha256(open(SUB, 'rb').read()).hexdigest(), 'kaggle_metric': {}}
for name in ('AUC', 'SP-SR', 'MP-SR', 'RPE', 'MPPE'):
    spec = importlib.util.spec_from_file_location(f'm_{name.replace("-", "_")}', f'{a.kit}/metric_code/track_3/{name}.py')
    mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
    if decoded_bytes > 16_000_000:                                       # the official limit; raised ONLY for this
        orig = mod._decode_archive                                         # stand-in (the public scans are full-res)
        mod._decode_archive = lambda text, maximum_bytes=2_000_000, _o=orig: _o(text, max(maximum_bytes, 10 ** 9))
    res['kaggle_metric'][name] = round(float(mod.score(sol.copy(), sub.copy(), 'row_id')), 6)
    print(name, res['kaggle_metric'][name], flush=True)

# 5. what was packed vs the rollout (world 0), and quaternion order
sys.path.insert(0, K)
from v2dlb.submission_parquet import read_trajectory
tr = read_trajectory(os.path.join(RD, f'episode_{ep:06d}.parquet'))
w0 = tr.world_index == 0
key = {(int(f), int(s)): q for f, s, q in zip(tr.frame_index[w0], tr.object_slot[w0], tr.pose_xyzw[w0])}
ids = sub.row_id.str.extract(r'f(\d+)/o(\d+)$').astype(int).to_numpy()
P = sub[['pos_x', 'pos_y', 'pos_z', 'quat_x', 'quat_y', 'quat_z', 'quat_w']].to_numpy()
res['packed_minus_rollout_maxabs'] = float(np.max(np.abs(P - np.stack([key[(f, s)] for f, s in ids]))))
res['packed_quat_norm_dev_max'] = float(np.max(np.abs(np.linalg.norm(P[:, 3:], axis=1) - 1)))
res['worlds_in_rollout'] = int(len(np.unique(tr.world_index)))
json.dump(res, open(a.out, 'w'), indent=1)
print(json.dumps(res, indent=1))
