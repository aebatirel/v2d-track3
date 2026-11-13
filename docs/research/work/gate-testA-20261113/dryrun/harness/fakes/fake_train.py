"""DRY RUN ONLY: stands in for FlashCHORD scripts/train_flash_sac.py (no GPU here).
Records the exact command line and environment, checks that the Hydra overrides compose on the (patched) FlashCHORD
tree, checks that every asset the reference names resolves on this box, then writes empty checkpoint files with the
names the real trainer uses (policy_<step> / state_<step> every 10,000,384 env steps, and the final step)."""
import glob, json, os, re, subprocess, sys, time
ov = sys.argv[1:]
kv = {a.split('=', 1)[0]: a.split('=', 1)[1] for a in ov if '=' in a}
out = kv['output_dir']; steps = int(kv['training.total_environment_steps'])
refdir = kv['task.parquet'].strip("'\"")
os.makedirs(out, exist_ok=True)
FC = os.getcwd()
env = {k: v for k, v in os.environ.items() if k.startswith(('FC_', 'TRAIN_', 'MUJOCO_GL', 'XLA_'))}
rec = dict(time=time.strftime('%FT%TZ', time.gmtime()), cwd=FC, argv=['scripts/train_flash_sac.py'] + ov, env=env)
# 1) Hydra composition on the patched tree (FlashCHORD's own venv, which has hydra)
cc = subprocess.run([f'{FC}/.venv/bin/python.real', '-I', '/dryrun/compose_check.py', FC, f'{out}/DRYRUN_compose.yaml'] + ov,
                    capture_output=True, text=True)
rec['compose'] = dict(rc=cc.returncode, out=cc.stdout[-3000:], err=cc.stderr[-1500:])
# 2) assets named by the reference
import pyarrow.parquet as pq
pqs = sorted(glob.glob(f'{refdir}/*.parquet')); rec['reference_parquets'] = pqs
t = pq.read_table(pqs[0])
chk = []
for col in ('object_urdf_paths', 'object_mesh_paths'):
    for p in t.column(col)[0].as_py():
        chk.append(dict(kind=col, path=p, exists=os.path.exists(p), realpath=os.path.realpath(p)))
        if col == 'object_urdf_paths' and os.path.exists(p):
            for m in re.findall(r'filename="([^"]+)"', open(p).read()):
                q = os.path.normpath(os.path.join(os.path.dirname(p), m))
                chk.append(dict(kind='urdf_mesh', urdf=os.path.basename(p), path=q, exists=os.path.exists(q)))
stage = glob.glob(os.path.normpath(f'{refdir}/../../../reconstructed_stage') + '/*.usda')
rec['support_stage'] = stage
rec['assets'] = chk; rec['assets_all_resolve'] = all(c['exists'] for c in chk)
rec['fps'] = t.column('fps')[0].as_py(); rec['frames'] = len(t.column('object_body_position')[0].as_py())
json.dump(rec, open(f'{out}/DRYRUN_train_call.json', 'w'), indent=1)
with open('/dryrun/train_calls.jsonl', 'a') as f:
    f.write(json.dumps(dict(out=out, argv=rec['argv'], env=env, compose_rc=cc.returncode,
                            assets_all_resolve=rec['assets_all_resolve'])) + '\n')
print(f'DRY RUN train stub: compose rc {cc.returncode}; assets resolve {rec["assets_all_resolve"]}; writing checkpoints')
k = 10_000_384; marks = [k * i for i in range(1, steps // k + 1)] + ([steps] if steps % k else [])
for s in marks:
    for kind in ('policy', 'state'):
        open(f'{out}/{kind}_{s}.safetensors', 'wb').write(f'DRYRUN {kind} {s} {out}\n'.encode())
    print(f'[dry run] step {s}/{steps}', flush=True)
sys.exit(0 if cc.returncode == 0 and rec['assets_all_resolve'] else 1)
