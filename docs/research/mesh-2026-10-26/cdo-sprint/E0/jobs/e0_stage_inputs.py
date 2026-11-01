"""Stage (and optionally upload) the E0 box inputs: plan.json, calib.json (dataset camera calibration, the file
pipeline/fetch_data.sh links as T3/calib.json; obs_points.py and hands_mp.py read it), our eval tracks
(eval/ep<N>/poses.npz, result.json = store run 20261025-evperc-4f596df), the eval cam_a videos (eval/ep<N>_a.mp4, for
hands_mp.py), the kit's v2dlb/mesh_budget.py (budget check), and SHA256SUMS. No scan, mocap, parquet or *_align file
(asserted). Eval depth is not staged (already in the store, cache/depth/eval/).
Usage: python -I e0_stage_inputs.py SCRATCH KIT PLAN.json OUTDIR [--upload RUN_ID]
"""
import hashlib, json, os, shutil, sys

SCR, KIT, PLAN, OUT = sys.argv[1:5]
up = sys.argv[sys.argv.index('--upload') + 1] if '--upload' in sys.argv else None
plan = json.load(open(PLAN))
eps = sorted({int(e) for v in plan['episodes_by_object'].values() for e in v})
files = {'plan.json': PLAN, 'calib.json': f'{SCR}/data/calib.json', 'kit/v2dlb/mesh_budget.py': f'{KIT}/v2dlb/mesh_budget.py'}
for e in eps:
    files[f'eval/ep{e}/poses.npz'] = f'{SCR}/data/eval/ep{e}/poses.npz'
    files[f'eval/ep{e}/result.json'] = f'{SCR}/data/eval/ep{e}/result.json'
    files[f'eval/ep{e}_a.mp4'] = f'{SCR}/data/eval/ep{e}_a.mp4'
for k, v in files.items():
    low = (k + ' ' + v).lower()
    assert not any(w in low for w in ('scan', 'mocap', '_align', '.parquet', '/mesh/')), f'forbidden input {k} {v}'
os.makedirs(OUT, exist_ok=True)
lines = []
for k, v in sorted(files.items()):
    d = os.path.join(OUT, k); os.makedirs(os.path.dirname(d), exist_ok=True)
    shutil.copyfile(v, d)
    lines.append(f'{hashlib.sha256(open(d, "rb").read()).hexdigest()}  {k}')
# the plan's own hashes must match what is staged (tracks / result / video are the inventoried files)
for e in eps:
    x = plan['episodes'][str(e)]
    for k, h in ((f'eval/ep{e}/poses.npz', x['poses_sha256']), (f'eval/ep{e}/result.json', x['result_sha256']),
                 (f'eval/ep{e}_a.mp4', x['video_sha256'])):
        assert any(l == f'{h}  {k}' for l in lines), f'hash mismatch {k}'
open(os.path.join(OUT, 'SHA256SUMS'), 'w').write('\n'.join(lines) + '\n')
tot = sum(os.path.getsize(os.path.join(OUT, k)) for k in files)
print(f'staged {len(files)} files, {tot / 1e6:.1f} MB in {OUT}')
if up:
    from huggingface_hub import HfApi
    HfApi().upload_folder(folder_path=OUT, path_in_repo=f'runs/{up}/inputs', repo_id='aebatirel/v2d-store',
                          repo_type='dataset', commit_message=f'E0 inputs {up}')
    print(f'uploaded to aebatirel/v2d-store runs/{up}/inputs')
