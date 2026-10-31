"""CPU check that the recipe screen's training-side keys cannot change the scored rollout (physics-solver.md section 8).
The official evaluator (flash_chord.evaluation.harness.evaluate_checkpoint, the code scripts/evaluate_policy.py runs)
rebuilds the env from the checkpoint's resolved config. Arm K writes training.optimization.learning_rate_* and
curriculum.thresholds into that config (and its checkpoints carry other curriculum_stage values); arm D writes nothing.
This takes one stored FlashSAC checkpoint, writes copies whose metadata differ ONLY in those keys, evaluates each with
the unchanged harness on the CPU (1 world, explicit reset; Warp graph capture is skipped on the CPU as in
tools/trace_rollout.py, the same transition) and compares the exported object trajectories and metrics bit for bit.
Run from the FlashCHORD dir with its venv:
  python eval_invariance.py CKPT.safetensors REF.parquet OUT_DIR
The copies point task.parquet at REF and training.device at cpu (identical in every copy). No ground truth is read."""
import copy, json, os, sys

import numpy as np
from safetensors import safe_open
from safetensors.numpy import save_file

ck, ref, outd = sys.argv[1:4]
os.makedirs(outd, exist_ok=True)
with safe_open(ck, 'np') as f:
    meta = dict(f.metadata()); tensors = {k: f.get_tensor(k) for k in f.keys()}
cfg0 = json.loads(meta['user.resolved_config_json'])
cfg0['task']['parquet'] = os.path.abspath(ref); cfg0['training']['device'] = 'cpu'
thr = [19660800, 34406400, 49152000, 63897600, 78643200, 93388800, 108134400, 122880000, 137625600, 200007680, 250003456]


def variant(name, edit_cfg, stage=None, steps=None):
    c = copy.deepcopy(cfg0); edit_cfg(c); m = dict(meta); m['user.resolved_config_json'] = json.dumps(c)
    if stage is not None:
        m['user.curriculum_stage'] = str(stage)
    if steps is not None:
        m['user.environment_steps'] = str(steps)
    p = os.path.join(outd, f'{name}.safetensors'); save_file(tensors, p, metadata=m); return p


def k_arm(c):
    o = c['training']['optimization']
    o.update(learning_rate_initial=6e-4, learning_rate_peak=6e-4, learning_rate_end=3e-5, learning_rate_schedule_updates=136728)
    t = [2 * x for x in thr]; c['curriculum']['thresholds'] = t
    if isinstance(c['training'].get('curriculum'), dict):
        c['training']['curriculum']['thresholds'] = t
    c['training']['total_environment_steps'] = 70004736


paths = dict(base=variant('base', lambda c: None),
             K=variant('K', k_arm, stage=1, steps=20000768),           # K's 20M checkpoint: stage 1 (VOC 0.75 in training)
             stage3=variant('stage3', lambda c: None, stage=3, steps=50003968))
from flash_chord.envs.rl import RLEnv  # noqa: E402

_cap0 = RLEnv.capture_step


def _capture_step(self):  # Warp graph capture crashes on the CPU: step eagerly there (the same transition)
    if not self.device.is_cpu:
        _cap0(self)


RLEnv.capture_step = _capture_step
import warp as wp  # noqa: E402

wp.config.log_level = wp.LOG_WARNING
from flash_chord.evaluation.harness import evaluate_checkpoint, evaluation_scalars  # noqa: E402

res = {}
for name, p in paths.items():
    with wp.ScopedDevice('cpu'):
        o = evaluate_checkpoint(p, world_count=1, reset_mode='explicit', object_trajectories_output=os.path.join(outd, f'{name}.parquet'))
    res[name] = dict(scalars=evaluation_scalars(o), steps=o.step_count)
    print(name, json.dumps(res[name]['scalars'])[:300], flush=True)
import pyarrow.parquet as pq  # noqa: E402

import pyarrow as pa  # noqa: E402

tab = {n: pq.read_table(os.path.join(outd, f'{n}.parquet')) for n in paths}


def num(t):  # every numeric column (the object trajectories and their references), stacked
    cols = [t.column(i).to_numpy().astype(np.float64) for i, f in enumerate(t.schema)
            if pa.types.is_integer(f.type) or pa.types.is_floating(f.type)]
    return np.stack(cols, 1)


summary = {}
# evaluation/environment_steps echoes the checkpoint's metadata (edited here on purpose); every other scalar must match
scal = lambda r: {k: (None if isinstance(v, float) and v != v else v) for k, v in r['scalars'].items() if k != 'evaluation/environment_steps'}  # noqa: E731
for n in ('K', 'stage3'):
    a, b = num(tab['base']), num(tab[n])
    same = a.shape == b.shape and np.array_equal(a, b)
    summary[n] = dict(trajectories_bit_identical=bool(same), max_abs=float(np.abs(a - b).max()) if a.shape == b.shape else None,
                      rows=int(a.shape[0]), metrics_identical=scal(res[n]) == scal(res['base']))
    print(f"{'PASS' if same and summary[n]['metrics_identical'] else 'FAIL'}  base vs {n}: object trajectories bit-identical "
          f"{same} ({a.shape[0]} rows), metrics identical {summary[n]['metrics_identical']}", flush=True)
json.dump(dict(checkpoint=ck, reference=ref, results=res, compare=summary), open(os.path.join(outd, 'eval_invariance.json'), 'w'), indent=1)
sys.exit(0 if all(v['trajectories_bit_identical'] and v['metrics_identical'] for v in summary.values()) else 1)
