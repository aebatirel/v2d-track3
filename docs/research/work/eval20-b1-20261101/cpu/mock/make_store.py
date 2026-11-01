"""Fake HF store of the eval-20 b1 retrain CPU mock (2026-11-01), from REAL files downloaded single-file from the store
(scratch DL; nothing downloaded here): the packed run 20261025-evb1420-ee7ba8e's eval-20 pull_files and result_files of
packed_refs.json and its packed checkpoint results/final_eval/ep20/policy.safetensors; the packed policy's H5p7 draws
runs/20261031-h5p7-1a7cdff/results/h5/{h5_summary.json, r1..r10/ep20/episode_000020.*}; pack 6's eval-20 rollout.
ONE test-only edit, recorded in OUT/../test_edits.json: every parquet of the packed run that has asset-path columns
(object_urdf_paths, object_mesh_paths) gets its literal box root /content/ rewritten to the mock box's MR/content/ (on a real box
both are /content). The trajectory fingerprint excludes those columns and is asserted unchanged; the md5 changes, and the new
md5 of the packed reference P is written for setup.sh (which pins it in the repo COPY's tools/e20b1.py and packed_refs.json).
Usage: make_store.py DL MR TABLE"""
import glob, hashlib, json, os, shutil, sys
import pyarrow as pa, pyarrow.parquet as pq
DL, MR, TAB = sys.argv[1:4]
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), *(['..'] * 6), 'tools'))
from mass_arm import traj_fingerprint   # noqa: E402
ST = f'{MR}/store'; C = f'{MR}/content'
T = json.load(open(TAB))['episodes']['20']
md5 = lambda f: hashlib.md5(open(f, 'rb').read()).hexdigest()
files = T['pull_files'] + T['result_files'] + ['runs/20261025-evb1420-ee7ba8e/results/final_eval/ep20/policy.safetensors']
files += ['runs/20261031-h5p7-1a7cdff/results/h5/h5_summary.json'] + [f'runs/20261031-h5p7-1a7cdff/results/h5/r{i}/ep20/episode_000020.{x}'
                                                                      for i in range(1, 11) for x in ('parquet', 'json')]
files += [f'runs/20261026-pack6-5203d42/results/submission/results/episode_000020.{x}' for x in ('parquet', 'json')]
edits = []
for f in files:
    src, dst = f'{DL}/{f}', f'{ST}/{f}'
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    if f.startswith('runs/20261025-evb1420') and f.endswith('.parquet'):
        t = pq.read_table(src); cols = [c for c in ('object_urdf_paths', 'object_mesh_paths') if c in t.column_names]
        if cols:
            fp0, m0 = traj_fingerprint(t), md5(src)
            for c in cols:
                v = [[p.replace('/content/', f'{C}/', 1) if p.startswith('/content/') else p for p in t.column(c)[0].as_py()]]
                t = t.set_column(t.column_names.index(c), c, pa.array(v, t.schema.field(c).type))
            pq.write_table(t, dst)
            fp1 = traj_fingerprint(pq.read_table(dst)); assert fp1 == fp0, (f, fp0, fp1)
            edits.append(dict(file=f, columns=cols, md5_real=m0, md5_mock=md5(dst), fingerprint=fp0))
            continue
    shutil.copyfile(src, dst)
P = [e for e in edits if e['file'].endswith('refs/glockt/ep20/processed/sequence_id=t3_ep020/robot_name=sharpa_wave/ref_gl_ilc.parquet')][0]
json.dump(dict(edits=edits, P=P, files=len(files)), open(f'{MR}/store_edits.json', 'w'), indent=1)
print(f'store: {len(files)} files, {len(edits)} parquets path-rewritten; P {P["md5_real"]} -> {P["md5_mock"]} (fingerprint {P["fingerprint"]})')
