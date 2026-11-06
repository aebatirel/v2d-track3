"""Stubs for the CPU dry run of ops/jobs/recipe_screen.sh (tools/recipe_screen_tests/dry_run.sh). FAKE numbers only:
nothing here is a measurement. Modes (the dry run writes one-line wrappers that call main(<mode>)):
  train     scripts/train_flash_sac.py: records argv + training env, writes real safetensors checkpoints (metadata =
            a resolved config built from the overrides) every DRY_CK_SLEEP s at FlashCHORD's save points; fails D/ep24-s43
            after two checkpoints (a failed cell with checkpoints on disk)
  evaluate  scripts/evaluate_policy.py: records its env (must never hold FC_DR_RESET); hangs on K/ep2-s42 best draw r7
  qa        pipeline/qa.py policy DIR EP: fake sim_vs_ref
  score     pipeline/score_registered.py EP DIR: fake registered AUC
  assets    pipeline/make_assets.py LIB OUT ...: a fake URDF with a mass line
  curve     tools/ckpt_curve.sh RUN OUT EP (REP env): fake per-checkpoint sim_vs_ref (mean of REP)
  curve_summary  tools/ckpt_curve_summary.py OUT
  es_eval   early_stop.sh's ES_EVAL CKPT DIR: fake sim_vs_ref, prints it; hangs on C/ep18-s42's 20M checkpoint
  fake_solved REF OUT SHIFT   (arm S, 2026-10-31) a stand-in for a solver output: REF with SHIFT (m) added to both
            robot_<side>_wrist_position columns, every other column unchanged (as tools/physics_solve/solve.py edits only
            the robot target columns); SHIFT 0 copies REF byte for byte (as G1's ep18, which edited no frame)
Arm S (fake): C's numbers plus S_D below; the training stub records the md5 of every parquet in its task directory."""
import hashlib, json, os, re, shutil, signal, sys, time

ROOT = os.environ.get('DRY_ROOT', '')
CKPTS = [10002432, 20000768, 30003200, 40001536, 50003968, 60002304, 70004736]
THR = [19660800, 34406400, 49152000, 63897600, 78643200, 93388800, 108134400, 122880000, 137625600, 200007680, 250003456]
# fake design: K beats C by +0.04 on average (none <= -0.05); D is 0.01 lower with a 50 % smaller draw sd on ep2 and ep12
BASE = {2: 0.70, 12: 0.88, 18: 0.60, 24: 0.22}
ARM_D = {'C': {2: 0.0, 12: 0.0, 18: 0.0, 24: 0.0}, 'K': {2: 0.10, 12: 0.02, 18: 0.03, 24: 0.01}, 'D': {2: -0.02, 12: 0.0, 18: -0.01, 24: -0.01},
         'S': {2: 0.10, 12: 0.03, 18: -0.01, 24: 0.02},   # S vs C (fake): mean +0.035, lowest -0.01 -> "signal"
         'V': {2: 0.06, 12: 0.04, 18: -0.02, 24: 0.04}}   # V vs C (fake, 2026-10-31 section 10): mean +0.03, lowest -0.02 -> "signal"
SD = {2: 0.20, 12: 0.03, 18: 0.06, 24: 0.02}
SD_X = {'C': {2: 1, 12: 1, 18: 1, 24: 1}, 'K': {2: 1, 12: 1, 18: 1, 24: 1}, 'D': {2: 0.5, 12: 0.5, 18: 0.9, 24: 1.0},
        'S': {2: 0.6, 12: 1, 18: 1, 24: 1}, 'V': {2: 0.8, 12: 1, 18: 1, 24: 1}}
Z = [-1.5, -1.0, -0.5, -0.25, 0.0, 0.0, 0.25, 0.5, 1.0, 1.5]
_m = sum(Z) / len(Z); _s = (sum((z - _m) ** 2 for z in Z) / len(Z)) ** 0.5
Z = [(z - _m) / _s for z in Z]                                     # mean 0, population sd 1: 10 draws give BASE, SD exactly
PROFILE = {2: [0.90, 0.95, 0.50, 0.50, 0.50, 0.48, 0.47], 12: [0.70, 0.80, 0.92, 0.93, 0.94, 0.94, 0.95],
           18: [0.60, 0.55, 0.58, 0.50, 0.52, 0.50, 0.49], 24: [0.20, 0.22, 0.23, 0.24, 0.21, 0.20, 0.20]}


def cell_of(path):
    m = re.search(r'/(C|K|D|S|V)/ep(\d+)-s(\d+)', path)
    return (m.group(1), int(m.group(2)), int(m.group(3))) if m else (None, None, None)


def auc(arm, ep, seed, r):
    return round(BASE[ep] + ARM_D[arm][ep] + (0.01 if seed == 43 else 0.0) + SD[ep] * SD_X[arm][ep] * Z[(r - 1) % 10], 6)


def svr_draw(arm, ep, seed, r):
    flip = -0.03 if (arm, ep, seed) == ('C', 18, 43) else 0.0      # one pair where sim_vs_ref orders the seeds unlike AUC
    return round(auc(arm, ep, seed, r) + 0.02 + flip, 6)


def svr_ckpt(arm, ep, seed, step, rep=1):
    i = CKPTS.index(step) if step in CKPTS else 0
    return round(PROFILE[ep][i] + 0.002 * rep + 0.001 * (seed - 42), 4)


def log_env(kind, extra):
    with open(os.path.join(ROOT, 'eval_env.log'), 'a') as f:
        f.write(json.dumps(dict(kind=kind, FC_DR_RESET=os.environ.get('FC_DR_RESET'), FC_DR_SEED=os.environ.get('FC_DR_SEED'), **extra)) + '\n')


def train():
    a = dict(x.split('=', 1) for x in sys.argv[1:] if '=' in x)
    run = a['output_dir']; steps = int(a['training.total_environment_steps']); seed = int(a['reset.seed'])
    os.makedirs(run, exist_ok=True)
    env = {k: os.environ.get(k) for k in ('FC_DR_RESET', 'FC_DR_SEED', 'FC_FDR_OBJ', 'FC_FDR_TIPS', 'FC_VOC_INERTIA', 'FC_STATE_RESET', 'FC_DROP_START')}
    td = a['task.parquet'].strip("'")                                # what FlashCHORD would read: every parquet of the task dir
    files = {f: hashlib.md5(open(os.path.join(td, f), 'rb').read()).hexdigest() for f in sorted(os.listdir(td)) if f.endswith('.parquet')} \
        if os.path.isdir(td) else None
    stage = sorted(os.listdir(os.path.join(td, '..', '..', '..', 'reconstructed_stage'))) if os.path.isdir(os.path.join(td, '..', '..', '..', 'reconstructed_stage')) else None
    json.dump(dict(argv=sys.argv[1:], env=env, task_files=files, support_stage=stage), open(os.path.join(run, 'stub_train.json'), 'w'), indent=1)
    if os.environ.get('FC_DR_RESET'):
        print(f"v2d FC_DR_RESET: sampled resets perturbed (STUB of ops/box/patch_flashchord_dr.py) [{os.environ['FC_DR_RESET']}] seed {os.environ.get('FC_DR_SEED')}", flush=True)
    o = dict(learning_rate_initial=3e-4, learning_rate_peak=3e-4, learning_rate_end=1.5e-4, learning_rate_schedule_updates=None)
    for k in list(o):
        if f'training.optimization.{k}' in a:
            v = a[f'training.optimization.{k}']; o[k] = int(v) if k.endswith('updates') else float(v)
    thr = json.loads(a['curriculum.thresholds']) if 'curriculum.thresholds' in a else THR
    b = lambda s: s.lower() == 'true'  # noqa: E731
    obj = dict(force_closure=dict(enabled=b(a.get('objective.force_closure.enabled', 'false')), weight=float(a.get('objective.force_closure.weight', 0))),
               contact_wrench_support=dict(weight=float(a.get('objective.contact_wrench_support.weight', 10))),
               unintended_contact=dict(weight=float(a.get('objective.unintended_contact.weight', -10))))
    vel = b(a.get('observation.object_body_velocity.enabled', 'false'))   # arm V's override (section 10), resolved as FlashCHORD does
    cfg = dict(output_dir=run, reset=dict(seed=seed), task=dict(parquet=a['task.parquet'].strip("'")), objective=obj,
               observation=dict(object_body_velocity=dict(enabled=vel)), env=dict(observation=dict(object_body_velocity=dict(enabled=vel))),
               curriculum=dict(thresholds=thr), training=dict(total_environment_steps=steps, optimization=o, curriculum=dict(thresholds=thr)))
    import numpy as np
    from safetensors.numpy import save_file
    arm, ep, _ = cell_of(run)
    for i, s in enumerate(c for c in CKPTS if c <= steps):
        time.sleep(float(os.environ.get('DRY_CK_SLEEP', '6')))
        stage = sum(1 for t in thr if s >= t)
        tmp = os.path.join(run, f'.tmp_{s}.safetensors')
        save_file({'w': np.zeros(4, np.float32)}, tmp, metadata={'user.resolved_config_json': json.dumps(cfg), 'user.environment_steps': str(s),
                                                                  'user.curriculum_stage': str(stage), 'user.voc_scale': '0.0'})
        os.rename(tmp, os.path.join(run, f'policy_{s}.safetensors'))
        print(f'stub training {s}/{steps}', flush=True)
        if (arm, ep) == ('D', 24) and seed == 43 and i == 1:
            print('stub: simulated crash (RuntimeError: CUDA error: an illegal memory access)', flush=True); sys.exit(1)
    print('stub training done', flush=True)


def evaluate():
    a = dict(x.split('=', 1) for x in sys.argv[1:] if '=' in x)
    ck, mo, to = a['evaluation.checkpoint'], a['evaluation.metrics_output'], a['evaluation.object_trajectories_output']
    log_env('evaluate', dict(checkpoint=ck, out=mo))
    if '/K/ep2-s42/' in ck and '/best/r7/' in mo:
        time.sleep(3600)                                           # a hung official evaluation (EVAL_TIMEOUT kills it)
    os.makedirs(os.path.dirname(mo), exist_ok=True)
    json.dump(dict(stub=True, checkpoint=ck), open(mo, 'w')); open(to, 'w').write('stub')


def qa():
    d, ep = sys.argv[2], int(sys.argv[3]); arm, _, seed = cell_of(d); r = int(re.search(r'/r(\d+)/?$', d).group(1))
    json.dump(dict(sim_vs_ref=svr_draw(arm, ep, seed, r)), open(os.path.join(d, 'qa_policy.json'), 'w'))


def score():
    ep, d = int(sys.argv[1]), sys.argv[2]; arm, _, seed = cell_of(d); r = int(re.search(r'/r(\d+)/?$', d).group(1))
    json.dump(dict(sim=dict(AUC=auc(arm, ep, seed, r), SP_SR=0.5, MP_SR=0.5), stub=True), open(os.path.join(d, f'score_registered_ep{ep}.json'), 'w'))


def assets():
    out = sys.argv[2]; os.makedirs(os.path.join(out, 'urdf'), exist_ok=True)
    open(os.path.join(out, 'urdf', 'stub.urdf'), 'w').write('<mass value="0.128"/> stub ' + ' '.join(sys.argv[3:]) + '\n')


def curve():
    run, out, ep = sys.argv[1], sys.argv[2], int(sys.argv[3]); rep = int(os.environ.get('REP', '1')); arm, _, seed = cell_of(run)
    for f in sorted(os.listdir(run)):
        m = re.fullmatch(r'policy_(\d+)\.safetensors', f)
        if not m:
            continue
        d = os.path.join(out, f[:-12])
        if os.path.exists(os.path.join(d, 'qa_policy.json')):
            continue
        os.makedirs(d, exist_ok=True); log_env('curve', dict(checkpoint=f))
        v = [svr_ckpt(arm, ep, seed, int(m.group(1)), k) for k in range(1, rep + 1)]
        json.dump(dict(sim_vs_ref=round(sum(v) / len(v), 4), rep=v, rep_n=rep), open(os.path.join(d, 'qa_policy.json'), 'w'))
    print('curve done (stub)')


def curve_summary():
    out = sys.argv[1]
    for d in sorted(os.listdir(out), key=lambda x: int(re.findall(r'\d+', x)[0]) if re.findall(r'\d+', x) else 0):
        p = os.path.join(out, d, 'qa_policy.json')
        if os.path.exists(p):
            print(f"{int(re.findall(r'[0-9]+', d)[0]) // 1000000:4d}M  sim_vs_ref {json.load(open(p))['sim_vs_ref']:.3f}  | stub")


def es_eval():
    ck, d = sys.argv[1], sys.argv[2]; arm, ep, seed = cell_of(ck); step = int(re.search(r'policy_(\d+)', ck).group(1))
    log_env('es_eval', dict(checkpoint=ck))
    if (arm, ep, seed) == ('C', 18, 42) and step == CKPTS[1]:
        time.sleep(3600)                                           # a hung ES evaluation: ES stalls, training runs to the cap
    os.makedirs(d, exist_ok=True); v = svr_ckpt(arm, ep, seed, step, int(d.rstrip('/').split('/r')[-1]))
    json.dump(dict(sim_vs_ref=v), open(os.path.join(d, 'qa_policy.json'), 'w')); print(v)


def fake_solved():
    src, out, shift = sys.argv[1], sys.argv[2], float(sys.argv[3])
    if shift == 0:
        shutil.copyfile(src, out); return
    import pyarrow as pa, pyarrow.parquet as pq
    t = pq.read_table(src)
    add = lambda x: [add(y) for y in x] if isinstance(x, list) else x + shift  # noqa: E731  (flat or per-frame [x, y, z])
    for col in ('robot_left_wrist_position', 'robot_right_wrist_position'):
        i = t.column_names.index(col); v = add(t.column(col)[0].as_py())
        t = t.set_column(i, col, pa.array([v], type=t.schema.field(col).type))
    pq.write_table(t, out)


def main(mode):
    signal.signal(signal.SIGTERM, lambda *a: sys.exit(143))
    dict(train=train, evaluate=evaluate, qa=qa, score=score, assets=assets, curve=curve, curve_summary=curve_summary, es_eval=es_eval,
         fake_solved=fake_solved)[mode]()


if __name__ == '__main__':
    main(sys.argv.pop(1))
