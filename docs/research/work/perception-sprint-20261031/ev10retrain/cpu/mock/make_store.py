"""Fake store of the eval-10 V4p retrain mock (2026-10-31): the real input files (single-file downloads of the real store,
scratchpad ev10retrain/dl and the earlier e1conf downloads) at their store paths, plus MOCK H5p7 eval-10 rollouts of the
packed policy (runs/20261031-h5p7-1a7cdff/results/h5/r1..r10/ep10/episode_000010.{parquet,json}): REAL flash_chord
parquets whose reference columns are the packed reference P and whose achieved poses stay at frame 0 (the packed
policy's real failure mode, beige left behind), with the packed checkpoint's sha256. Usage: make_store.py STORE DL E1"""
import hashlib, json, os, shutil, sys
import numpy as np, pandas as pd, pyarrow as pa, pyarrow.parquet as pq
ST, DL, E1 = sys.argv[1:4]
P6, GA = 'runs/20261026-pack6-5203d42', 'runs/20261026-gl10A2-5e0e100'
HIVE = 'processed/sequence_id=t3_ep010/robot_name=sharpa_wave'
files = [(DL, f'{P6}/perc2/ep10/poses.npz'), (DL, f'{P6}/perc2/ep10/vo.json'), (DL, f'{P6}/perc2/ep10/det_f0.npz'),
         (DL, f'{P6}/refs/perc2mck/ep10/hands_refined.npz'), (DL, f'{GA}/refs/perc2mck/ep10/hands.npz'),
         (DL, f'{GA}/refs/perc2mck/ep10/hands_refined.npz'), (DL, f'{GA}/refs/glockt/ep10/{HIVE}/ref_gl_ilc.parquet'),
         (f'{E1}/dl_ck', f'{GA}/results/glock_public/ep10/best/policy.safetensors'),
         (f'{E1}/dl_keep', f'{P6}/results/submission/results/episode_000010.parquet'),
         (f'{E1}/dl_keep', f'{P6}/results/submission/results/episode_000010.json')]
for src, f in files:
    os.makedirs(os.path.dirname(f'{ST}/{f}'), exist_ok=True); shutil.copyfile(f'{src}/{f}', f'{ST}/{f}')
t = pq.read_table(f'{ST}/{GA}/refs/glockt/ep10/{HIVE}/ref_gl_ilc.parquet', columns=['object_body_names', 'object_body_position', 'object_body_wxyz'])
names = [str(x) for x in t.column('object_body_names')[0].as_py()]; B = len(names)
pos = np.array(t.column('object_body_position')[0].as_py(), float); T = pos.size // (3 * B); pos = pos.reshape(T, B, 3)
q = np.array(t.column('object_body_wxyz')[0].as_py(), float).reshape(T, B, 4)[..., [1, 2, 3, 0]]; ref = np.concatenate([pos, q], 2)
sha = hashlib.sha256(open(f'{ST}/{GA}/results/glock_public/ep10/best/policy.safetensors', 'rb').read()).hexdigest()
K = ('position_x', 'position_y', 'position_z', 'quaternion_x', 'quaternion_y', 'quaternion_z', 'quaternion_w')
for r in range(1, 11):
    rng = np.random.default_rng(r); ach = np.repeat(ref[:1], T, 0).copy(); ach[..., :3] += rng.normal(0, 0.0005, ach[..., :3].shape)
    rows = [dict(environment_id=0, step=i, reference_frame=i, time_s=i * 0.05, object_id=b, object_body_id=b, object_body_name=names[b],
                 environment_valid=True, **{f'achieved_{k}': float(ach[i, b, j]) for j, k in enumerate(K)},
                 **{f'reference_{k}': float(ref[i, b, j]) for j, k in enumerate(K)}) for i in range(T) for b in range(B)]
    d = f'{ST}/runs/20261031-h5p7-1a7cdff/results/h5/r{r}/ep10'; os.makedirs(d, exist_ok=True)
    tab = pa.Table.from_pandas(pd.DataFrame(rows), preserve_index=False)
    pq.write_table(tab.replace_schema_metadata({b'flash_chord.checkpoint_sha256': sha.encode(), b'mock': b'1'}), f'{d}/episode_000010.parquet')
    json.dump(dict(mock=1, checkpoint_sha256=sha), open(f'{d}/episode_000010.json', 'w'))
json.dump({'10': dict(n=10, mock=True)}, open(f'{ST}/runs/20261031-h5p7-1a7cdff/results/h5/h5_summary.json', 'w'))   # pushed last by h5_reeval.sh
print('fake store at', ST, 'with', len(files), 'input files and 10 mock H5p7 rollouts')
