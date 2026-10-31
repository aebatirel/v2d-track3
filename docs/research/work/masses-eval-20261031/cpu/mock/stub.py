"""Stub dispatcher for the masses eval-retrain CPU mock (2026-10-31; after masses-transfer-20261031/cpu/mock/stub.py).
argv[1] = role (main | fc), then the real command line.
Real: make_assets.py, mass_arm.py, mass_eval_verify.py, mass_pack_check.py, mass_verify.py, no_oracle.py, inline python
(-c / -), anything unknown. Stubbed (GPU or heavy): grasp_lock / wrist_ilc / grasp_evolve / trace_* / rest_check (never
called here: REUSE_REF), FlashCHORD train_flash_sac.py / evaluate_policy.py / view_policy.py, the kit's
run_policy_evaluation.py and pack_submission.py, qa.py, hand_refine.py, ckpt_curve_summary.py, ckpt_meta.py, patches.
FlashCHORD as on the box:
  - the trainer resolves task.parquet (a file, or a folder with exactly one .parquet), imports object_urdf_paths
    verbatim when the file exists (else it fails, as a missing asset would), reads the URDF inertials, and writes
    safetensors checkpoints whose header holds user.resolved_config_json. That config starts from a REAL resolved config
    of a packed checkpoint (templates/glock.json with embodiment=sharpa_hands_mid, else templates/std.json; their saved
    paths and seeds are overwritten) and applies the dotted command-line overrides; task.parquet / reference.parquet hold
    the resolved file's real path and reference.num_frames its frame count, as the real ones do; reset.seed also sets
    env.reset.seed / training.seed and curriculum.thresholds training.curriculum.thresholds;
  - the evaluators (evaluate_policy.py and the kit's run_policy_evaluation.py) rebuild the scene from the CHECKPOINT's
    saved task.parquet (a saved /workspace/... path is read under the mock's /content, the box's symlink) and write
    checkpoint / checkpoint_sha256 into the metrics file. Every load is recorded (train_audit / eval_audit / kit_audit).
Mock scores (NOT evidence about masses): sim_vs_ref = 0.88 + 0.02 if any loaded mass != 0.3 - 0.005 at seed 43 + noise
in [-0.02, 0.02]. A real rollout (a pack's kept parquet) gets its pack-7 value (MR/packed7.json)."""
import copy, glob, hashlib, json, os, shutil, struct, sys, time
role, argv = sys.argv[1], sys.argv[2:]
MR, PY = os.environ['MOCK_MR'], os.environ['MOCK_PY']
C = f'{MR}/content'
script = argv[0] if argv else ''
base = os.path.basename(script)


def real():
    os.execv(PY, [PY] + argv)


def audit(name, **kw):
    with open(f'{MR}/{name}.log', 'a') as f:
        f.write(json.dumps(kw) + '\n')


def h01(s):
    return int(hashlib.md5(s.replace(MR, '').encode()).hexdigest()[:8], 16) / 2 ** 32


if argv[:1] in (['-c'], ['-']) or not script.endswith('.py') or base in (
        'make_assets.py', 'mass_arm.py', 'mass_eval_verify.py', 'mass_pack_check.py', 'mass_verify.py', 'no_oracle.py',
        'packed_refs_make.py'):
    real()
if base.startswith('patch_flashchord') or base in ('view_policy.py',):
    sys.exit(0 if base != 'view_policy.py' else 1)
sys.path.insert(0, f'{C}/v2d-track3/tools')
import pyarrow.parquet as pq                                              # noqa: E402
from mass_arm import read_inertial, traj_fingerprint                     # noqa: E402


def loc(p):
    for r in ('/workspace/', '/content/'):
        if p.startswith(r):
            return f'{C}/' + p[len(r):]
    return p


def fc_load(task):
    p = os.path.realpath(loc(task.strip("'")))
    if not os.path.isfile(p):
        fs = sorted(glob.glob(os.path.join(p, '**', '*.parquet'), recursive=True))
        if len(fs) != 1:
            raise ValueError(f'reference directory must contain exactly one .parquet file, found {len(fs)}: {p}')
        p = fs[0]
    t = pq.read_table(p); loaded = {}
    for n, u in zip(t.column('object_body_names')[0].as_py(), t.column('object_urdf_paths')[0].as_py()):
        if not os.path.isfile(u):
            raise FileNotFoundError(f'URDF {u} not a file (FlashCHORD would re-root it on its own assets)')
        m, com, _ = read_inertial(open(u).read()); loaded[n] = dict(urdf=u, mass=m, com=com)
    return p, traj_fingerprint(t), loaded, len(t.column('object_body_position')[0].as_py())


def write_ck(path, cfg, steps):
    meta = {'format': 'learner_state', 'user.algorithm': 'flash_sac', 'user.checkpoint_kind': 'policy',
            'user.environment_steps': str(steps), 'user.curriculum_stage': '10', 'user.resolved_config_json': json.dumps(cfg)}
    h = json.dumps({'__metadata__': meta}).encode(); h += b' ' * (-len(h) % 8)
    with open(path, 'wb') as f:
        f.write(struct.pack('<Q', len(h))); f.write(h); f.write(os.urandom(64))   # weights stand-in: a unique sha256


def read_ck(path):
    with open(path, 'rb') as f:
        n = struct.unpack('<Q', f.read(8))[0]; m = json.loads(f.read(n))['__metadata__']
    return m, json.loads(m['user.resolved_config_json'])


def setk(d, key, v):
    ks = key.split('.')
    for k in ks[:-1]:
        if not isinstance(d.get(k), dict):
            d[k] = {}
        d = d[k]
    d[ks[-1]] = v


def val(v):
    v = v.strip("'")
    try:
        return json.loads(v)
    except Exception:
        return v


def rollout(ck, mo, to, tag):
    meta, cfg = read_ck(ck)
    rp, fp, loaded, nf = fc_load(cfg['task']['parquet'])
    os.makedirs(os.path.dirname(mo), exist_ok=True)
    json.dump(dict(mock=1, checkpoint=ck, checkpoint_sha256=hashlib.sha256(open(ck, 'rb').read()).hexdigest()), open(mo, 'w'))
    json.dump(dict(task=cfg['task']['parquet'], reference_file=rp, fingerprint=fp, masses={n: v['mass'] for n, v in loaded.items()},
                   urdfs={n: v['urdf'] for n, v in loaded.items()}, seed=cfg['reset']['seed']), open(to, 'w'))
    audit(tag, ck=ck, out=mo, task=cfg['task']['parquet'], reference_file=rp, fingerprint=fp, loaded=loaded)


if base == 'train_flash_sac.py':
    kv = dict(x.split('=', 1) for x in argv[1:] if '=' in x)
    run, steps = kv['output_dir'], int(kv['training.total_environment_steps'])
    rp, fp, loaded, nf = fc_load(kv['task.parquet'])                    # raises (rc 1) like FlashCHORD
    kind = 'glock' if kv.get('embodiment') == 'sharpa_hands_mid' else 'std'
    cfg = copy.deepcopy(json.load(open(f'{MR}/templates/{kind}.json')))
    for k, v in sorted(kv.items()):
        if '.' in k or k == 'output_dir':                                 # dotted overrides (groups: experiment=, embodiment=,
            setk(cfg, k, val(v))                                          # curriculum= are what the template already is)
    s = int(kv['reset.seed']); cfg['reset']['seed'] = s; cfg['env']['reset']['seed'] = s; cfg['training']['seed'] = s
    if 'curriculum.thresholds' in kv:
        cfg['training']['curriculum']['thresholds'] = val(kv['curriculum.thresholds'])
    cfg['task']['parquet'] = rp; cfg['reference']['parquet'] = rp; cfg['reference']['num_frames'] = nf
    cfg['training']['total_environment_steps'] = steps
    env = {e: os.environ.get(e) for e in ('FC_FDR_OBJ', 'FC_FDR_TIPS', 'FC_VOC_INERTIA', 'FC_IMMEDIATE_FIRST_FRAME', 'GL_WRIST_KP')}
    audit('train_audit', run=run, task=kv['task.parquet'], reference_file=rp, fingerprint=fp, loaded=loaded, seed=s, steps=steps,
          kind=kind, args=sorted(x for x in argv[1:] if x.split('=', 1)[0] not in ('output_dir', 'task.parquet')), env=env, t=time.time())
    os.makedirs(run, exist_ok=True); time.sleep(1)
    for k in range(1, 8):
        st = k * steps // 7 // 4096 * 4096
        write_ck(f'{run}/policy_{st}.safetensors', cfg, st)
    audit('train_audit', done=run, t=time.time())
elif base == 'evaluate_policy.py':
    kv = dict(x.split('=', 1) for x in argv[1:] if '=' in x)
    rollout(kv['evaluation.checkpoint'], kv['evaluation.metrics_output'], kv['evaluation.object_trajectories_output'], 'eval_audit')
elif base == 'run_policy_evaluation.py':                                 # the kit's batch runner (submit_pack.sh, h5)
    ck, res = argv[argv.index('--checkpoints') + 1], argv[argv.index('--results') + 1]
    os.makedirs(res, exist_ok=True)
    for ep, p in sorted(json.load(open(ck)).items(), key=lambda x: int(x[0])):
        stem = f'{res}/episode_{int(ep):06d}'
        rollout(p, stem + '.json', stem + '.parquet', 'kit_audit')
        print(f'evaluating episode {ep} from {p}')
elif base == 'pack_submission.py':
    res, o = argv[argv.index('--results') + 1], argv[argv.index('-o') + 1]
    fs = sorted(glob.glob(f'{res}/episode_*'))
    json.dump({os.path.basename(f): hashlib.md5(open(f, 'rb').read()).hexdigest() for f in fs}, open(o, 'w'), indent=1)
    print(f'packed {len(fs)} files (mock)')
elif base == 'qa.py':
    if argv[1] == 'ref':
        print('qa_ref (mock): ok'); sys.exit(0)
    d, ep = argv[2], int(argv[3])
    f = sorted(x for x in os.listdir(d) if x.endswith('.parquet'))
    try:
        tr = json.load(open(f'{d}/{f[0]}'))
        heavy = any(abs(m - 0.3) > 1e-9 for m in tr['masses'].values())
        v = round(0.88 + (0.02 if heavy else 0.0) - (0.005 if int(tr['seed']) == 43 else 0.0) + 0.04 * (h01(d) - 0.5), 4)
    except (UnicodeDecodeError, json.JSONDecodeError):                   # a real kept rollout: its pack-7 value
        v = json.load(open(f'{MR}/packed7.json'))[str(ep)]
    json.dump(dict(sim_vs_ref=v, floor_vs_ref=0.3), open(f'{d}/qa_policy.json', 'w')); print(json.dumps(dict(sim_vs_ref=v, floor_vs_ref=0.3)))
elif base == 'hand_refine.py':
    sys.exit(1)
elif base in ('ckpt_curve_summary.py', 'trace_score.py'):
    print('policy_mock 0.6')
elif base == 'ckpt_meta.py':
    for p in argv[1:]:
        m, c = read_ck(p); print(os.path.basename(p), 'steps', m['user.environment_steps'], 'seed', c['reset']['seed'], '(mock)')
elif base in ('grasp_lock.py', 'wrist_ilc.py', 'grasp_evolve.py', 'trace_rollout.py', 'rest_check.py', 'support_fill.py',
              'score_registered.py', 'score_sim.py'):
    audit('forbidden_audit', script=base, args=argv[1:]); sys.exit(1)       # never runs on an eval retrain (REUSE_REF)
else:
    real()
