"""Stub dispatcher of the ep11-gate CPU mock (after masses-transfer-20261031/cpu/mock/stub.py). argv[1] = role (main |
fc | rt | mp), then the real command line.
REAL: refine.py and nest_physics.py (through `python -m venv` wrappers onto the local pinned venvs MOCK_VR / MOCK_VP),
make_assets.py, e11g_verify.py, e11g_verdict.py, inline python (-c / -), anything unknown.
STUBBED (GPU, IK or heavy): mkref.py (rt: stage (a) is REAL, mkref's own fit_table / table_frame / per-object snap on the
given poses and frame-0 depth, then a minimal reference parquet with the track in the table frame, table_frame.npz,
ref_summary.json and the support stage), contact_retarget.py (copy), grasp_lock.py / wrist_ilc.py (copy), trace_rollout.py,
trace_score.py, rest_check.py, FlashCHORD train_flash_sac.py / evaluate_policy.py, qa.py, score_registered.py,
ckpt_curve_summary.py, ckpt_meta.py, FlashCHORD patch scripts. hands_mp.py / hand_refine.py must never run (audited).
The FlashCHORD stubs load references as FlashCHORD does (task.parquet folder -> exactly one .parquet -> object_urdf_paths
-> URDF inertials); the trainer writes safetensors whose metadata holds the resolved config; the evaluator reads it back
and writes checkpoint / checkpoint_sha256 into its metrics file.
Mock scores (NOT evidence about V4p): a rollout's AUC = 0.595 (the static floor) + MOCK_EFFECT (default 0.12) when the
loaded reference holds the blue cup down in the nest window (median lift f42-136 < 1 cm, i.e. the V4p track), noise
+-0.002 (C) / +-0.04 (T); MOCK_DROP (with MOCK_DROP_SEED) lowers that seed's T cells.
Fault injection: MOCK_FAIL_TRAIN (regex on output_dir: the training exits 1 -> a missing cell), MOCK_CFG_EXTRA (regex on
output_dir: one extra config key -> the config diff fails)."""
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


if argv[:2] == ['-m', 'venv']:                     # the job's pinned venvs -> wrappers onto the local pinned venvs
    d = argv[-1]; os.makedirs(f'{d}/bin', exist_ok=True)
    tgt = os.environ['MOCK_VR'] if os.path.basename(d) == 'e11g_vr' else os.environ['MOCK_VP']
    open(f'{d}/bin/python', 'w').write(f'#!/bin/bash\nexec {tgt}/bin/python "$@"\n')
    open(f'{d}/bin/pip', 'w').write(f'#!/bin/bash\necho "{d} $*" >> {MR}/pip.log\n')
    os.chmod(f'{d}/bin/python', 0o755); os.chmod(f'{d}/bin/pip', 0o755); audit('venv_audit', dir=d, target=tgt); sys.exit(0)
if argv[:1] in (['-c'], ['-']) or not script.endswith('.py') or base in (
        'make_assets.py', 'refine.py', 'nest_physics.py', 'e11g_verify.py', 'e11g_verdict.py'):
    real()
if base.startswith('patch_flashchord'):
    sys.exit(0)
if base in ('hands_mp.py', 'hand_refine.py', 'perc2.py'):
    audit('UNEXPECTED', role=role, argv=argv); sys.exit(1)
sys.path.insert(0, f'{MR}/content/v2d-track3/tools'); sys.path.insert(0, f'{MR}/content/v2d-track3/pipeline')
import numpy as np                                                       # noqa: E402
import pyarrow as pa, pyarrow.parquet as pq                              # noqa: E402
from mass_arm import read_inertial, traj_fingerprint                     # noqa: E402  (the real helpers)


def fc_load(task):
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
        m, com, _ = read_inertial(open(u).read()); loaded[n] = dict(urdf=u, mass=m, md5=hashlib.md5(open(u, 'rb').read()).hexdigest())
    names = t.column('object_body_names')[0].as_py(); T = len(np.array(t.column('robot_left_wrist_position')[0].as_py()).reshape(-1, 3))
    pos = np.array(t.column('object_body_position')[0].as_py(), float).reshape(T, len(names), 3)
    z = pos[:, names.index('blue_cup'), 2]; lift = float(np.median(z[42:137] - z[0]))
    return p, traj_fingerprint(t), loaded, lift


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
        if not isinstance(d.get(k), dict):
            d[k] = {}
        d = d[k]
    d[ks[-1]] = v


if base == 'mkref.py':                             # stage (a) REAL (mkref's own functions), then a minimal reference
    import types
    from scipy.spatial.transform import Rotation as Rot
    import trimesh
    import mkref as MK
    ep = int(opt('--ep')); poses, depth, hands, out = opt('--poses'), opt('--depth'), opt('--hands'), opt('--out')
    assets = opt('--assets') or os.environ.get('ASSETS'); t3 = opt('--t3', f'{MR}/content/t3')
    audit('mkref_audit', argv=argv[1:], poses=poses, poses_md5=hashlib.md5(open(poses, 'rb').read()).hexdigest(), depth=os.path.realpath(depth),
          hands=hands, hands_md5=hashlib.md5(open(hands, 'rb').read()).hexdigest(), assets=assets, split=os.environ.get('SPLIT'))
    a = types.SimpleNamespace(ring_in=10, ring_out=90, plane_thr=0.006, plane_iters=1000, support_tol=0.03, support_max=0.05,
                              support_fallback=1, snap='per_object', snap_max=0.02, table_z=0.60)
    names = MK.load_names(t3, ep, 'public'); P = np.load(poses); W_C = P['world_T_cam'].astype(float); T = len(W_C); B = len(names)
    cam_T = {n: P[f'cam_T_{n}'].astype(float) for n in names}; vis = {}
    for n in names:
        m = trimesh.load(f'{os.environ["MESH_DIR"]}/{n}.glb', force='mesh'); vis[n] = trimesh.Trimesh(np.asarray(m.vertices), np.asarray(m.faces), process=True)
    KR = MK.rectified_K(f'{t3}/calib.json'); D = np.load(depth, mmap_mode='r'); d0 = np.asarray(D[0])
    n_, d_, frac, npts, rms = MK.fit_table(d0, KR, W_C[0], {nm: cam_T[nm][0] for nm in names}, vis, a)
    OBJw = np.stack([np.stack([W_C[t] @ cam_T[nm][t] for nm in names]) for t in range(T)])
    cen = np.mean([OBJw[0, b, :3, :3] @ np.asarray(vis[nm].vertices).mean(0) + OBJw[0, b, :3, 3] for b, nm in enumerate(names)], 0)
    T_tab = MK.table_frame(n_, d_, W_C[0], cen, a.table_z); OBJ = np.einsum('ij,tbjk->tbik', T_tab, OBJw)
    h = np.array([(np.asarray(vis[nm].vertices) @ OBJ[0, b, :3, :3].T + OBJ[0, b, :3, 3])[:, 2].min() - a.table_z for b, nm in enumerate(names)])
    shifts = np.where(np.abs(h) <= a.snap_max, -h, 0.0); OBJ[:, :, 2, 3] += shifts[None]
    q = Rot.from_matrix(OBJ[..., :3, :3].reshape(-1, 3, 3)).as_quat().reshape(T, B, 4)[..., [3, 0, 1, 2]]
    seq = f't3_ep{ep:03d}'; hive = f'{out}/processed/sequence_id={seq}/robot_name=sharpa_wave'; os.makedirs(hive, exist_ok=True)
    os.makedirs(f'{out}/reconstructed_stage', exist_ok=True); open(f'{out}/reconstructed_stage/{seq}_support.usda', 'w').write('#usda 1.0 (mock)\n')
    urdf = [f'{assets}/urdf/{n}_rigid.urdf' for n in names]; mesh = [f'{assets}/mesh/{n}/{n}.glb' for n in names]
    tab = pa.table({'object_body_names': [names], 'object_body_position': [OBJ[..., :3, 3].tolist()], 'object_body_wxyz': [q.tolist()],
                    'object_urdf_paths': [urdf], 'object_mesh_paths': [mesh], 'robot_left_wrist_position': [np.zeros((T, 3)).tolist()]})
    pq.write_table(tab, f'{hive}/{hashlib.md5(poses.encode()).hexdigest()}-0.parquet')
    np.savez(f'{out}/table_frame.npz', T_table_from_world=T_tab, plane_n=n_, plane_d=d_, names=np.array(names))
    json.dump(dict(ep=ep, seq=seq, mock=True, table=dict(inlier_frac=frac, bottoms_cm=(h * 100).tolist(), shifts_cm=(shifts * 100).tolist())),
              open(f'{out}/ref_summary.json', 'w'), indent=1)
    print('mkref (mock: stage a real, IK stubbed)', json.dumps(dict(bottoms_cm=np.round(h * 100, 2).tolist(), inlier_frac=round(frac, 3))))
elif base == 'contact_retarget.py':
    src, dst = argv[1], argv[2]; os.makedirs(os.path.dirname(dst), exist_ok=True); shutil.copy(src, dst)
    st = dict(rest_settle=dict(mock=True, max_shift_cm=0.0), args=argv[3:])
    json.dump(st, open(os.path.splitext(dst)[0] + '_contact_retarget.json', 'w')); print('contact_retarget (mock)', json.dumps(st))
    audit('ref_audit', stage=base, src=src, dst=dst, args=argv[3:])
elif base in ('grasp_lock.py', 'wrist_ilc.py'):
    src, dst = argv[1], argv[2]; os.makedirs(os.path.dirname(dst), exist_ok=True); shutil.copy(src, dst)
    if base == 'grasp_lock.py':
        names = pq.read_table(src, columns=['object_body_names']).column('object_body_names')[0].as_py()
        json.dump(dict(phases=[dict(object=k, replan=False, start=5, end=40) for k in names]), open(os.path.splitext(dst)[0] + '_grasp_lock.json', 'w'))
        print('grasp pose (mock)')
    audit('ref_audit', stage=base, src=src, dst=dst, args=argv[3:], env=dict(GL_WRIST_KP=os.environ.get('GL_WRIST_KP')))
elif base == 'trace_rollout.py':
    np.savez(argv[2], mock=np.zeros(1))
elif base == 'trace_score.py':
    print('zero_action: 0.5790')
elif base == 'rest_check.py':
    print('{"all_ok": false, "mock": 1}')
elif base == 'ckpt_curve_summary.py':
    print('policy_mock 0.6')
elif base == 'ckpt_meta.py':
    for p in argv[1:]:
        m, c = read_ck(p); print(os.path.basename(p), 'steps', m['user.environment_steps'], 'seed', c['reset']['seed'], '(mock)')
elif base == 'train_flash_sac.py':
    kv = dict(x.split('=', 1) for x in argv[1:] if '=' in x)
    run, steps = kv['output_dir'], int(kv['training.total_environment_steps'])
    if os.environ.get('MOCK_FAIL_TRAIN') and re.search(os.environ['MOCK_FAIL_TRAIN'], run):
        audit('train_audit', run=run, injected_failure=True); sys.exit('mock: injected training failure')
    task = kv['task.parquet'].strip("'"); rp, fp, loaded, lift = fc_load(task)
    cfg = {}
    for k, v in sorted(kv.items()):
        setk(cfg, k, v.strip("'"))
    cfg['reference'] = dict(parquet=task); cfg['task']['parquet'] = task; cfg['reset']['seed'] = int(kv['reset.seed'])
    cfg['training']['total_environment_steps'] = steps
    if os.environ.get('MOCK_CFG_EXTRA') and re.search(os.environ['MOCK_CFG_EXTRA'], run):
        cfg['training']['mock_extra_setting'] = 1
    audit('train_audit', run=run, task=task, reference_file=rp, fingerprint=fp, loaded=loaded, lift_cm=round(lift * 100, 2),
          seed=kv['reset.seed'], steps=steps, args=sorted(x for x in argv[1:] if x.split('=', 1)[0] not in ('output_dir', 'task.parquet')), t=time.time())
    os.makedirs(run, exist_ok=True); time.sleep(2)
    for k in range(1, 8):
        write_ck(f'{run}/policy_{k * steps // 7 // 4096 * 4096}.safetensors', cfg, k * steps // 7 // 4096 * 4096)
    audit('train_audit', done=run, t=time.time())
elif base == 'evaluate_policy.py':
    kv = dict(x.split('=', 1) for x in argv[1:] if '=' in x)
    ck = kv['evaluation.checkpoint']; meta, cfg = read_ck(ck)
    rp, fp, loaded, lift = fc_load(cfg['task']['parquet'])
    mo, to = kv['evaluation.metrics_output'], kv['evaluation.object_trajectories_output']; os.makedirs(os.path.dirname(mo), exist_ok=True)
    json.dump(dict(mock=1, checkpoint=ck, checkpoint_sha256=hashlib.sha256(open(ck, 'rb').read()).hexdigest()), open(mo, 'w'))
    json.dump(dict(task=cfg['task']['parquet'], fingerprint=fp, lift=lift, seed=cfg['reset']['seed']), open(to, 'w'))
    audit('eval_audit', ck=ck, out=mo, task=cfg['task']['parquet'], fingerprint=fp, lift_cm=round(lift * 100, 2))
elif base in ('qa.py', 'score_registered.py'):
    if base == 'qa.py' and argv[1] == 'ref':
        print('qa_ref (mock): ok'); sys.exit(0)
    d, ep = (argv[2], int(argv[3])) if base == 'qa.py' else (argv[2], int(argv[1]))
    f = [x for x in os.listdir(d) if x.endswith('.parquet')]
    tr = json.load(open(f'{d}/{f[0]}')); held = tr['lift'] < 0.01
    eff = float(os.environ.get('MOCK_EFFECT', '0.12')) if held else 0.0
    if held and str(tr['seed']) == os.environ.get('MOCK_DROP_SEED'):
        eff -= float(os.environ.get('MOCK_DROP', '0'))
    noise = (0.08 if held else 0.004) * (h01(d + base) - 0.5)
    if base == 'qa.py':
        v = round(0.52 + (0.3 if held else 0.0) + noise, 4)
        json.dump(dict(sim_vs_ref=v, floor_vs_ref=0.45, task=tr['task']), open(f'{d}/qa_policy.json', 'w')); print(json.dumps(dict(sim_vs_ref=v)))
    else:
        x = min(1.0, 0.595 + eff + noise)
        sc = lambda y, po=None: dict(AUC=round(y, 4), SP_SR=1.0, MP_SR=1.0, **({'per_obj_AUC': po} if po else {}))
        json.dump(dict(sim=sc(x, dict(blue_cup=round(min(1, x + 0.03), 4), beige_cup=round(max(0, x - 0.03), 4))),
                       reference=sc(0.97 if held else 0.90), static_floor=sc(0.595), meshes=opt('--meshes')),
                  open(f'{d}/score_registered_ep{ep}.json', 'w'))
        audit('score_audit', dir=d, t=time.time())
else:
    real()
