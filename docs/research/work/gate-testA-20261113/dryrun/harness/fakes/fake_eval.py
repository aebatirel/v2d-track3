"""DRY RUN ONLY: stands in for FlashCHORD scripts/evaluate_policy.py. Writes the metrics json and an object-trajectory
parquet with the evaluator's schema (flash_chord_object_trajectories_v1). Reference poses come from the reference the
checkpoint was trained on; 'achieved' poses are the reference plus a synthetic drift (no physics)."""
import hashlib, json, os, sys, time
import numpy as np, pyarrow as pa, pyarrow.parquet as pq
kv = {a.split('=', 1)[0]: a.split('=', 1)[1] for a in sys.argv[1:] if '=' in a}
ck = kv['evaluation.checkpoint']; mo = kv['evaluation.metrics_output']; to = kv['evaluation.object_trajectories_output']
rec = json.load(open(os.path.join(os.path.dirname(ck), 'DRYRUN_train_call.json')))
ref = rec['reference_parquets'][0]; t = pq.read_table(ref)
P = np.array(t.column('object_body_position')[0].as_py(), float)            # (T, B, 3)
Q = np.array(t.column('object_body_wxyz')[0].as_py(), float)[..., [1, 2, 3, 0]]   # wxyz -> xyzw
names = t.column('object_body_names')[0].as_py(); T, B = P.shape[:2]
seed = int(hashlib.sha256(to.encode()).hexdigest()[:8], 16); rng = np.random.default_rng(seed)
D = np.zeros_like(P); amp = rng.uniform(0.0, 0.06)                           # 0-6 cm drift of slot 0, second half
D[T // 2:, 0, 0] = np.linspace(0, amp, T - T // 2)
A = P + D
ex = pq.read_schema('/dryrun/example_rollout.parquet')
rows = dict(environment_id=[], step=[], reference_frame=[], time_s=[], object_id=[], object_body_id=[], object_body_name=[],
            environment_valid=[])
for c in 'xyz': rows[f'achieved_position_{c}'] = []; rows[f'reference_position_{c}'] = []
for c in 'xyzw': rows[f'achieved_quaternion_{c}'] = []; rows[f'reference_quaternion_{c}'] = []
for s in range(T):
    for b in range(B):
        rows['environment_id'].append(0); rows['step'].append(s); rows['reference_frame'].append(s)
        rows['time_s'].append(s / 20.0); rows['object_id'].append(b); rows['object_body_id'].append(b)
        rows['object_body_name'].append(names[b]); rows['environment_valid'].append(True)
        for i, c in enumerate('xyz'):
            rows[f'achieved_position_{c}'].append(A[s, b, i]); rows[f'reference_position_{c}'].append(P[s, b, i])
        for i, c in enumerate('xyzw'):
            rows[f'achieved_quaternion_{c}'].append(Q[s, b, i]); rows[f'reference_quaternion_{c}'].append(Q[s, b, i])
md = dict(ex.metadata)
md.update({b'flash_chord.step_count': str(T).encode(), b'flash_chord.object_body_count': str(B).encode(),
           b'flash_chord.reference_parquet': ref.encode(), b'flash_chord.dry_run': b'synthetic rollout, no physics',
           b'flash_chord.checkpoint_sha256': hashlib.sha256(open(ck, 'rb').read()).hexdigest().encode()})
tab = pa.Table.from_pydict({f.name: rows[f.name] for f in ex}, schema=ex.remove_metadata()).replace_schema_metadata(md)
os.makedirs(os.path.dirname(to), exist_ok=True); pq.write_table(tab, to)
json.dump(dict(dry_run=True, checkpoint=ck, steps=T, objects=B, drift_m=amp), open(mo, 'w'), indent=1)
with open('/dryrun/eval_calls.jsonl', 'a') as f:
    f.write(json.dumps(dict(time=time.strftime('%FT%TZ', time.gmtime()), argv=sys.argv[1:], drift_m=amp, ref=ref)) + '\n')
print(f'DRY RUN evaluator stub: wrote {to} ({T} steps x {B} objects)')
