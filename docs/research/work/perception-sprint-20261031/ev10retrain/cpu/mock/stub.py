"""Stub dispatcher of the eval-10 V4p retrain CPU mock (2026-10-31; after ep11gate/cpu/mock/stub.py). argv[1] = role
(main | fc | rt | mp), then the real command line.
REAL: refine.py and nest_physics.py (through `python -m venv` wrappers onto the local pinned venvs MOCK_VR / MOCK_VP),
make_assets.py, qa.py (with the real kit), e10v_score.py / e10v_verify.py / e10v_verdict.py, no_oracle.py, inline python
(-c / -), anything unknown.
STUBBED (GPU, IK or heavy): mkref.py (rt: stage (a) REAL, mkref's own fit_table / table_frame / per-object snap on the given
poses and frame-0 depth, names from the kit roster on SPLIT=eval; then a minimal reference parquet), contact_retarget.py,
grasp_lock.py / wrist_ilc.py (copy), trace_rollout.py, trace_score.py, rest_check.py, ckpt_curve_summary.py, ckpt_meta.py,
FlashCHORD train_flash_sac.py (the saved config = the PACKED gl10A2 checkpoint's config with this run's output_dir,
task / reference parquet, seeds and steps; every other CLI key is compared with the packed config: mismatches are audited),
evaluate_policy.py and the kit's run_policy_evaluation.py (both write REAL flash_chord rollout parquets: reference columns =
the loaded reference, achieved = MOCK_POLICY copy (reference + 2 mm noise) or floor (objects left at frame 0)).
hands_mp.py / hand_refine.py / perc2.py / score_registered.py must never run (audited as UNEXPECTED).
Fault injection: MOCK_FAIL_TRAIN (regex on output_dir: training exits 1), MOCK_CFG_EXTRA (regex: one extra config key),
MOCK_CONF_FAIL_DRAW (the n-th run_policy_evaluation.py call exits 1 without output)."""
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


if argv[:2] == ['-m', 'venv']:                     # the job's pinned venvs -> wrappers onto the local pinned venvs
    d = argv[-1]; os.makedirs(f'{d}/bin', exist_ok=True)
    tgt = os.environ['MOCK_VR'] if os.path.basename(d) == 'e10v_vr' else os.environ['MOCK_VP']
    open(f'{d}/bin/python', 'w').write(f'#!/bin/bash\nexec {tgt}/bin/python "$@"\n')
    open(f'{d}/bin/pip', 'w').write(f'#!/bin/bash\necho "{d} $*" >> {MR}/pip.log\n')
    os.chmod(f'{d}/bin/python', 0o755); os.chmod(f'{d}/bin/pip', 0o755); audit('venv_audit', dir=d, target=tgt); sys.exit(0)
if argv[:1] in (['-c'], ['-']) or not script.endswith('.py') or base in (
        'make_assets.py', 'refine.py', 'nest_physics.py', 'qa.py', 'no_oracle.py', 'e10v_score.py', 'e10v_verify.py', 'e10v_verdict.py'):
    if base == 'qa.py':
        audit('qa_audit', argv=argv[1:])
    real()
if base.startswith('patch_flashchord'):
    sys.exit(0)
if base in ('hands_mp.py', 'hand_refine.py', 'perc2.py', 'score_registered.py'):
    audit('UNEXPECTED', role=role, argv=argv); sys.exit(1)
sys.path.insert(0, f'{MR}/content/v2d-track3/tools'); sys.path.insert(0, f'{MR}/content/v2d-track3/pipeline')
import numpy as np                                                       # noqa: E402
import pandas as pd                                                      # noqa: E402
import pyarrow as pa, pyarrow.parquet as pq                              # noqa: E402
from mass_arm import read_inertial, traj_fingerprint                     # noqa: E402  (the real helpers)
from mass_verify import ck_config, flat                                  # noqa: E402


def resolve(task):
    p = task.strip("'")
    if not os.path.isfile(p):
        fs = sorted(glob.glob(os.path.join(p, '**', '*.parquet'), recursive=True))
        if len(fs) != 1:
            raise ValueError(f'reference directory must contain exactly one .parquet file, found {len(fs)}: {p}')
        p = fs[0]
    return p


def fc_load(task):
    p = resolve(task); t = pq.read_table(p); loaded = {}
    for n, u in zip(t.column('object_body_names')[0].as_py(), t.column('object_urdf_paths')[0].as_py()):
        if not os.path.isfile(u):
            raise FileNotFoundError(f'URDF {u} (FlashCHORD would re-root it on /assets/)')
        m, com, _ = read_inertial(open(u).read()); loaded[n] = dict(urdf=u, mass=m, md5=hashlib.md5(open(u, 'rb').read()).hexdigest())
    names = [str(x) for x in t.column('object_body_names')[0].as_py()]; B = len(names)
    T = len(np.array(t.column('robot_left_wrist_position')[0].as_py()).reshape(-1, 3))
    pos = np.array(t.column('object_body_position')[0].as_py(), float).reshape(T, B, 3)
    q = np.array(t.column('object_body_wxyz')[0].as_py(), float).reshape(T, B, 4)[..., [1, 2, 3, 0]]
    return p, traj_fingerprint(t), loaded, names, np.concatenate([pos, q], 2)


def write_ck(path, cfg, steps):
    meta = {'format': 'learner_state', 'user.algorithm': 'flash_sac', 'user.checkpoint_kind': 'policy',
            'user.environment_steps': str(steps), 'user.curriculum_stage': '10', 'user.resolved_config_json': json.dumps(cfg)}
    h = json.dumps({'__metadata__': meta}).encode(); h += b' ' * (-len(h) % 8)
    with open(path, 'wb') as f:
        f.write(struct.pack('<Q', len(h))); f.write(h)


def setk(d, key, v):
    ks = key.split('.')
    for k in ks[:-1]:
        if not isinstance(d.get(k), dict):
            d[k] = {}
        d = d[k]
    d[ks[-1]] = v


def same(a, b):
    if isinstance(a, (dict, list)) or isinstance(b, (dict, list)):
        return None                                                        # hydra groups / lists: not compared
    sa, sb = str(a).strip("'").lower(), str(b).strip("'").lower()
    try:
        return float(sa) == float(sb)
    except ValueError:
        return sa == sb


def rollout(path, names, ref, ck, task, seedkey):
    """a REAL flash_chord_object_trajectories_v1 parquet: reference columns = the loaded reference, achieved per MOCK_POLICY"""
    T, B = ref.shape[:2]; rng = np.random.default_rng(int(hashlib.md5(seedkey.encode()).hexdigest()[:8], 16))
    if os.environ.get('MOCK_POLICY', 'copy') == 'floor':
        ach = np.repeat(ref[:1], T, 0).copy(); ach[..., :3] += rng.normal(0, 0.0005, ach[..., :3].shape)
    else:
        ach = ref.copy(); ach[..., :3] += rng.normal(0, 0.002, ach[..., :3].shape)
    rows = []
    for t in range(T):
        for b in range(B):
            rows.append(dict(environment_id=0, step=t, reference_frame=t, time_s=t * 0.05, object_id=b, object_body_id=b,
                             object_body_name=names[b], environment_valid=True,
                             **{f'achieved_{k}': float(ach[t, b, i]) for i, k in enumerate(('position_x', 'position_y', 'position_z', 'quaternion_x', 'quaternion_y', 'quaternion_z', 'quaternion_w'))},
                             **{f'reference_{k}': float(ref[t, b, i]) for i, k in enumerate(('position_x', 'position_y', 'position_z', 'quaternion_x', 'quaternion_y', 'quaternion_z', 'quaternion_w'))}))
    tab = pa.Table.from_pandas(pd.DataFrame(rows), preserve_index=False)
    sha = hashlib.sha256(open(ck, 'rb').read()).hexdigest()
    md = {b'flash_chord.schema': b'flash_chord_object_trajectories_v1', b'flash_chord.quaternion_order': b'xyzw',
          b'flash_chord.checkpoint_sha256': sha.encode(), b'flash_chord.reference_parquet': task.encode(), b'mock': b'1'}
    pq.write_table(tab.replace_schema_metadata(md), path)
    return sha


if base == 'mkref.py':                             # stage (a) REAL (mkref's own functions), then a minimal reference
    import types
    from scipy.spatial.transform import Rotation as Rot
    import trimesh
    import mkref as MK
    ep = int(opt('--ep')); poses, depth, hands, out = opt('--poses'), opt('--depth'), opt('--hands'), opt('--out')
    assets = opt('--assets') or os.environ.get('ASSETS'); t3 = opt('--t3', f'{MR}/content/t3'); split = os.environ.get('SPLIT', 'public')
    audit('mkref_audit', argv=argv[1:], poses=poses, poses_md5=hashlib.md5(open(poses, 'rb').read()).hexdigest(), depth=os.path.realpath(depth),
          hands=hands, hands_md5=hashlib.md5(open(hands, 'rb').read()).hexdigest(), assets=assets, split=split)
    a = types.SimpleNamespace(ring_in=10, ring_out=90, plane_thr=0.006, plane_iters=1000, support_tol=0.03, support_max=0.05,
                              support_fallback=1, snap='per_object', snap_max=0.02, table_z=0.60)
    names = MK.load_names(t3, ep, split, roster=f'{MR}/content/kit/v2d_submission_kit/data/track_3_evaluation_objects.json')
    P = np.load(poses); W_C = P['world_T_cam'].astype(float); T = len(W_C); B = len(names)
    cam_T = {n: P[f'cam_T_{n}'].astype(float) for n in names}
    vis = {n: trimesh.load(MK.visual_mesh_path(assets, n), force='mesh') for n in names}
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
    json.dump(dict(ep=ep, seq=seq, mock=True), open(f'{out}/ref_summary.json', 'w'), indent=1)
    open(f'{out}/mkref_log.txt', 'w').write(f'table plane: {npts} ring points, inliers {frac:.2f} (mock stage a)\nframe-0 object bottoms above the fitted table (cm): '
                                            f'{dict(zip(names, np.round(h * 100, 2).tolist()))}\n')
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
        m, c = ck_config(p); print(os.path.basename(p), 'steps', m.get('user.environment_steps'), 'seed', c['reset']['seed'], '(mock)')
elif base == 'train_flash_sac.py':
    kv = dict(x.split('=', 1) for x in argv[1:] if '=' in x)
    run, steps = kv['output_dir'], int(kv['training.total_environment_steps'])
    if os.environ.get('MOCK_FAIL_TRAIN') and re.search(os.environ['MOCK_FAIL_TRAIN'], run):
        audit('train_audit', run=run, injected_failure=True); sys.exit('mock: injected training failure')
    task = kv['task.parquet'].strip("'"); rp, fp, loaded, names, _ = fc_load(task)
    _, cfg = ck_config(os.environ['MOCK_PACKED_CK']); pf = flat(cfg)            # the packed recipe's saved config
    mism = {k: (v, pf.get(k)) for k, v in kv.items() if k in pf and k not in ('output_dir', 'task.parquet', 'reset.seed')
            and same(v, pf[k]) is False}
    s = int(kv['reset.seed'])
    for k, v in (('output_dir', run), ('task.parquet', task), ('reference.parquet', task), ('reset.seed', s), ('env.reset.seed', s),
                 ('training.seed', s), ('training.total_environment_steps', steps)):
        setk(cfg, k, v)
    if os.environ.get('MOCK_CFG_EXTRA') and re.search(os.environ['MOCK_CFG_EXTRA'], run):
        cfg['training']['mock_extra_setting'] = 1
    audit('train_audit', run=run, task=task, reference_file=rp, fingerprint=fp, loaded=loaded, seed=kv['reset.seed'], steps=steps,
          cli_vs_packed_mismatch=mism, cli_keys_compared=sorted(k for k in kv if k in pf and same(kv[k], pf[k]) is not None), t=time.time())
    os.makedirs(run, exist_ok=True); time.sleep(1)
    for k in range(1, 8):
        write_ck(f'{run}/policy_{k * steps // 7 // 4096 * 4096}.safetensors', cfg, k * steps // 7 // 4096 * 4096)
    audit('train_audit', done=run, t=time.time())
elif base == 'evaluate_policy.py':
    kv = dict(x.split('=', 1) for x in argv[1:] if '=' in x)
    ck = kv['evaluation.checkpoint']; _, cfg = ck_config(ck); task = cfg['task']['parquet']
    rp, fp, loaded, names, ref = fc_load(task)
    mo, to = kv['evaluation.metrics_output'], kv['evaluation.object_trajectories_output']; os.makedirs(os.path.dirname(mo), exist_ok=True)
    sha = rollout(to, names, ref, ck, task, to)
    json.dump(dict(mock=1, checkpoint=ck, checkpoint_sha256=sha), open(mo, 'w'))
    audit('eval_audit', kind='train_box', ck=ck, out=to, task=task, fingerprint=fp)
elif base == 'run_policy_evaluation.py':           # the kit's evaluator on the pristine worktree (pack draws)
    n = len(open(f'{MR}/conf_calls.log').read().splitlines()) + 1 if os.path.exists(f'{MR}/conf_calls.log') else 1
    open(f'{MR}/conf_calls.log', 'a').write(f'{n}\n')
    if os.environ.get('MOCK_CONF_FAIL_DRAW') == str(n):
        audit('eval_audit', kind='official', call=n, injected_failure=True); sys.exit('mock: injected evaluation failure')
    cks = json.load(open(opt('--checkpoints'))); res = opt('--results'); os.makedirs(res, exist_ok=True)
    for ep, ck in cks.items():
        _, cfg = ck_config(ck); task = cfg['task']['parquet']; rp, fp, loaded, names, ref = fc_load(task)
        out = f'{res}/episode_{int(ep):06d}'
        sha = rollout(out + '.parquet', names, ref, ck, task, f'{out}-{n}')
        json.dump(dict(mock=1, checkpoint=ck, checkpoint_sha256=sha, parquet=task), open(out + '.json', 'w'))
        audit('eval_audit', kind='official', call=n, ck=ck, out=out, task=task, fingerprint=fp, cwd=os.getcwd(), runtime_root=opt('--runtime-root'))
else:
    real()
