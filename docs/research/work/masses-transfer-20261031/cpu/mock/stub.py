"""Stub dispatcher for the masses-transfer CPU mock. argv[1] = role (main | fc), then the real command line.
Real: make_assets.py, support_fill.py, mass_arm.py, mass_verify.py, mass_verdict.py, inline python (-c / -), anything
unknown. Stubbed (GPU or heavy): grasp_lock.py, wrist_ilc.py, grasp_evolve.py, trace_rollout.py, trace_score.py,
rest_check.py, FlashCHORD train_flash_sac.py / evaluate_policy.py, qa.py policy, score_registered.py, ckpt_curve_summary.py,
ckpt_meta.py, FlashCHORD patch scripts.
The FlashCHORD stubs load a reference as FlashCHORD does (flash_chord/data/parquet.py resolve_parquet: a file, or a
folder with exactly one .parquet; assets/registry.py resolve_asset_path: the stored path when it is a file; URDF
inertials kept) and record what they loaded (train_audit.log, eval_audit.log). The trainer writes safetensors files
whose header metadata holds user.resolved_config_json (task.parquet, reference.parquet, reset.seed, output_dir,
training.total_environment_steps and every other override), the evaluator reads it back from the checkpoint (as
evaluation/harness.py does) and writes checkpoint / checkpoint_sha256 into its metrics file (as the real one does).
Mock scores (NOT evidence about masses): AUC = base(ep) + 0.05 (ep2) / 0.04 (ep12) when any loaded mass != 0.3 - 0.01
at seed 43 + noise in [-0.02, 0.02]; ref_auc depends on the reference fingerprint only."""
import glob, hashlib, json, os, re, shutil, struct, sys, time
role, argv = sys.argv[1], sys.argv[2:]
MR, PY = os.environ['MOCK_MR'], os.environ['MOCK_PY']
script = argv[0] if argv else ''
base = os.path.basename(script)


def real():
    os.execv(PY, [PY] + argv)


def audit(name, **kw):
    with open(f'{MR}/{name}.log', 'a') as f:
        f.write(json.dumps(kw) + '\n')


def opt(name, default=None):
    return argv[argv.index(name) + 1] if name in argv else default


def h01(s):
    return int(hashlib.md5(s.replace(MR, '').encode()).hexdigest()[:8], 16) / 2 ** 32


if argv[:1] in (['-c'], ['-']) or not script.endswith('.py') or base in (
        'make_assets.py', 'support_fill.py', 'mass_arm.py', 'mass_verify.py', 'mass_verdict.py'):
    real()
if base.startswith('patch_flashchord'):
    sys.exit(0)
sys.path.insert(0, f'{MR}/content/v2d-track3/tools')
import pyarrow.parquet as pq                                             # noqa: E402
from mass_arm import read_inertial, traj_fingerprint, md5               # noqa: E402  (the real helpers)


def fc_load(task):
    """What FlashCHORD imports for a task.parquet (raises like FlashCHORD on a folder without exactly one parquet)."""
    p = task.strip("'")
    if not os.path.isfile(p):
        fs = sorted(glob.glob(os.path.join(p, '**', '*.parquet'), recursive=True))
        if len(fs) != 1:
            raise ValueError(f'reference directory must contain exactly one .parquet file, found {len(fs)}: {p}')
        p = fs[0]
    t = pq.read_table(p); loaded = {}
    for n, u in zip(t.column('object_body_names')[0].as_py(), t.column('object_urdf_paths')[0].as_py()):
        if not os.path.isfile(u):
            raise FileNotFoundError(f'URDF {u} (FlashCHORD would re-root it on /assets/)')
        m, com, _ = read_inertial(open(u).read()); loaded[n] = dict(urdf=u, mass=m, com=com)
    return p, traj_fingerprint(t), loaded


def write_ck(path, cfg, steps):
    meta = {'format': 'learner_state', 'user.algorithm': 'flash_sac', 'user.checkpoint_kind': 'policy',
            'user.environment_steps': str(steps), 'user.curriculum_stage': '10', 'user.resolved_config_json': json.dumps(cfg)}
    h = json.dumps({'__metadata__': meta}).encode(); h += b' ' * (-len(h) % 8)
    with open(path, 'wb') as f:
        f.write(struct.pack('<Q', len(h))); f.write(h)


def read_ck(path):
    with open(path, 'rb') as f:
        n = struct.unpack('<Q', f.read(8))[0]; m = json.loads(f.read(n))['__metadata__']
    return m, json.loads(m['user.resolved_config_json'])


def setk(d, key, v):
    ks = key.split('.')
    for k in ks[:-1]:
        d = d.setdefault(k, {}) if isinstance(d.get(k, {}), dict) else d.__setitem__(k, {}) or d[k]
    d[ks[-1]] = v


if base == 'grasp_lock.py' or base == 'wrist_ilc.py':
    src, dst = argv[1], argv[2]; os.makedirs(os.path.dirname(dst), exist_ok=True); shutil.copy(src, dst)
    if base == 'grasp_lock.py':
        names = pq.read_table(src, columns=['object_body_names']).column('object_body_names')[0].as_py()
        json.dump(dict(phases=[dict(object=k, replan=False, start=5, end=40) for k in names]),
                  open(os.path.splitext(dst)[0] + '_grasp_lock.json', 'w'))
        print('grasp pose (mock)')
    audit('ref_audit', stage=base, src=src, dst=dst, args=argv[1:])
elif base == 'grasp_evolve.py':
    ref, out, bake = argv[1], argv[3], opt('--bake')
    json.dump(dict(window=[5, 40], generations=[dict(unedited=0.55)] * 20, best=dict(fit=0.6, gen=7)), open(out, 'w'))
    shutil.copy(ref, bake); audit('ref_audit', stage=base, src=ref, dst=bake, args=argv[1:])
elif base == 'trace_rollout.py':
    import numpy as np
    np.savez(argv[2], mock=np.zeros(1))
elif base == 'trace_score.py':
    print('zero_action: 0.6100')
elif base == 'rest_check.py':
    print('{"ok": true, "mock": 1}')
elif base == 'ckpt_curve_summary.py':
    print('policy_mock 0.6')
elif base == 'ckpt_meta.py':
    for p in argv[1:]:
        m, c = read_ck(p); print(os.path.basename(p), 'steps', m['user.environment_steps'], 'seed', c['reset']['seed'], '(mock)')
elif base == 'train_flash_sac.py':
    kv = dict(x.split('=', 1) for x in argv[1:] if '=' in x)
    run, steps = kv['output_dir'], int(kv['training.total_environment_steps'])
    task = kv['task.parquet'].strip("'"); rp, fp, loaded = fc_load(task)     # raises (rc 1) like FlashCHORD
    cfg = {}
    for k, v in sorted(kv.items()):
        setk(cfg, k, v.strip("'"))
    cfg['reference'] = dict(parquet=task); cfg['task']['parquet'] = task; cfg['reset']['seed'] = int(kv['reset.seed'])
    cfg['training']['total_environment_steps'] = steps
    cfg['mock_env'] = {e: os.environ.get(e) for e in ('FC_FDR_OBJ', 'FC_FDR_TIPS', 'FC_VOC_INERTIA', 'FC_IMMEDIATE_FIRST_FRAME', 'GL_WRIST_KP')}
    audit('train_audit', run=run, task=task, reference_file=rp, fingerprint=fp, loaded=loaded, seed=kv['reset.seed'],
          steps=steps, args=sorted(x for x in argv[1:] if x.split('=', 1)[0] not in ('output_dir', 'task.parquet')),
          env=cfg['mock_env'], t=time.time())
    os.makedirs(run, exist_ok=True); time.sleep(2)
    for k in range(1, 8):
        s = k * steps // 7 // 4096 * 4096
        write_ck(f'{run}/policy_{s}.safetensors', cfg, s)
    audit('train_audit', done=run, t=time.time())
elif base == 'evaluate_policy.py':
    kv = dict(x.split('=', 1) for x in argv[1:] if '=' in x)
    ck = kv['evaluation.checkpoint']; meta, cfg = read_ck(ck)
    rp, fp, loaded = fc_load(cfg['task']['parquet'])                     # the scene of the CHECKPOINT's saved config
    mo, to = kv['evaluation.metrics_output'], kv['evaluation.object_trajectories_output']; os.makedirs(os.path.dirname(mo), exist_ok=True)
    json.dump(dict(mock=1, checkpoint=ck, checkpoint_sha256=hashlib.sha256(open(ck, 'rb').read()).hexdigest()), open(mo, 'w'))
    json.dump(dict(task=cfg['task']['parquet'], fingerprint=fp, masses={n: v['mass'] for n, v in loaded.items()},
                   seed=cfg['reset']['seed']), open(to, 'w'))
    audit('eval_audit', ck=ck, out=mo, task=cfg['task']['parquet'], reference_file=rp, fingerprint=fp, loaded=loaded)
elif base in ('qa.py', 'score_registered.py'):
    if base == 'qa.py' and argv[1] == 'ref':
        print('qa_ref (mock): ok'); sys.exit(0)
    d, ep = (argv[2], int(argv[3])) if base == 'qa.py' else (argv[2], int(argv[1]))
    f = [x for x in os.listdir(d) if x.endswith('.parquet')]
    tr = json.load(open(f'{d}/{f[0]}')); heavy = any(abs(m - 0.3) > 1e-9 for m in tr['masses'].values())
    eff = ({2: 0.05, 12: 0.04}.get(ep, 0.0) if heavy else 0.0) - (0.01 if int(tr['seed']) == 43 else 0.0)
    if base == 'qa.py':
        v = round(0.85 + eff + 0.04 * (h01(d) - 0.5), 4)
        json.dump(dict(sim_vs_ref=v, floor_vs_ref=0.3, task=tr['task']), open(f'{d}/qa_policy.json', 'w')); print(json.dumps(dict(sim_vs_ref=v)))
    else:
        sc = lambda x: dict(AUC=round(x, 4), SP_SR=1.0, MP_SR=1.0)
        json.dump(dict(sim=sc({2: 0.80, 12: 0.88}.get(ep, 0.7) + eff + 0.04 * (h01(d + 'a') - 0.5)),
                       reference=sc(0.85 + 0.1 * h01(tr['fingerprint'])), static_floor=sc(0.59), meshes=opt('--meshes')),
                  open(f'{d}/score_registered_ep{ep}.json', 'w'))
else:
    real()
