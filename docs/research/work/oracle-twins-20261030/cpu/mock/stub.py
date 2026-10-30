"""Stub dispatcher for the oracle-twins CPU mock. argv[1] = role (main | fc | mp | rt), then the real command line.
Real: oracle_poses.py, ref_vs_mocap.py, score_registered.py on an .npz, inline python (-c / -), anything unknown.
Stubbed (GPU or heavy): perc2.py, hands_mp.py, hand_refine.py, make_assets.py, mkref.py (stage (a) emulated with
mkref's own fit_table / table_frame, object track only), contact_retarget.py, support_fill.py, grasp_lock.py,
wrist_ilc.py, trace_rollout.py, trace_score.py, rest_check.py, train_flash_sac.py, evaluate_policy.py, qa.py,
score_registered.py on a rollout dir, score_sim.py, ckpt_curve_summary.py, FlashCHORD patch scripts."""
import hashlib, json, os, shutil, sys, time
role, argv = sys.argv[1], sys.argv[2:]
MR, IN, PY = os.environ['MOCK_MR'], os.environ['MOCK_IN'], os.environ['MOCK_PY']
script = argv[0] if argv else ''
base = os.path.basename(script)


def real():
    os.execv(PY, [PY] + argv)


def audit(name, **kw):
    with open(f'{MR}/{name}.log', 'a') as f:
        f.write(json.dumps(kw) + '\n')


def kv(prefix):  # hydra-style key=value
    return {x.split('=', 1)[0]: x.split('=', 1)[1] for x in argv[1:] if '=' in x and x.split('=', 1)[0].startswith(prefix)}


def opt(name, default=None):
    return argv[argv.index(name) + 1] if name in argv else default


def h01(s):  # deterministic pseudo-random in [0, 1)
    return int(hashlib.md5(s.encode()).hexdigest()[:8], 16) / 2 ** 32


if base in ('oracle_poses.py', 'ref_vs_mocap.py') or argv[:1] in (['-c'], ['-']) or not script.endswith('.py'):
    real()
if base == 'score_registered.py' and argv[2].endswith('.npz'):
    real()
if base.startswith('patch_flashchord') or base in ('score_sim.py',):
    sys.exit(0)
import numpy as np                                                       # noqa: E402

if base == 'perc2.py':
    ep, out = os.environ['EP'], os.environ['OUT']; os.makedirs(out, exist_ok=True)
    for f in ('poses.npz', 'poses_world_vo.npz'):
        shutil.copy(os.path.realpath(f'{IN}/ep{ep}/{f}'), f'{out}/{f}')
    if not os.path.exists(f'{out}/depths_fs0.5.npy'):
        np.save(f'{out}/depths_fs0.5.npy', np.load(f'{IN}/ep{ep}/depth0.npy')[None])
    print(f'[mock] vo  perception stub ep{ep} (local perception of the refine inputs)')
elif base == 'hands_mp.py':
    ep, out = opt('--ep'), opt('--out'); os.makedirs(out, exist_ok=True)
    shutil.copy(os.path.realpath(f'{IN}/ep{ep}/hands.npz'), f'{out}/hands.npz'); audit('hands_audit', ep=ep, out=out)
elif base == 'hand_refine.py':
    shutil.copy(opt('--hands'), opt('--out'))
elif base == 'make_assets.py':
    lib, A = argv[1], argv[2]; os.makedirs(f'{A}/urdf', exist_ok=True)
    for f in os.listdir(lib):
        if f.endswith('.glb'):
            open(f'{A}/urdf/{f[:-4]}_rigid.urdf', 'w').write('<robot/>')
    open(f'{A}/PIECES.txt', 'w').write(opt('--pieces', 'none')); audit('assets_audit', assets=A, pieces=opt('--pieces'))
elif base == 'mkref.py':                                                 # stage (a) only, with mkref's own functions
    import types, trimesh, pyarrow as pa, pyarrow.parquet as pq
    from scipy.spatial.transform import Rotation as Rot
    sys.path.insert(0, os.path.dirname(os.path.abspath(script))); import mkref as MK
    ep, out = int(opt('--ep')), opt('--out'); A = os.environ['ASSETS']; LIB = os.environ['MESH_DIR']
    a = types.SimpleNamespace(ring_in=10, ring_out=90, plane_thr=0.006, plane_iters=1000, support_tol=0.03, support_max=0.05,
                              snap_max=0.02, table_z=0.60)
    names = [str(o['name']) for o in pq.read_table(f'{MR}/content/t3/ep{ep}.parquet', columns=['observation.objects'])
             .column('observation.objects')[0].as_py()]
    P = np.load(opt('--poses')); W_C = P['world_T_cam'].astype(float); T = len(W_C); B = len(names)
    cam_T = {n: P[f'cam_T_{n}'].astype(float) for n in names}
    vis = {n: trimesh.load(f'{LIB}/{n}.glb', force='mesh') for n in names}
    D = np.load(opt('--depth'), mmap_mode='r'); depth0 = np.asarray(D[0])
    n, d, frac, npts, rms = MK.fit_table(depth0, MK.rectified_K(f'{MR}/content/t3/calib.json'), W_C[0], {k: cam_T[k][0] for k in names}, vis, a)
    OBJw = np.stack([np.stack([W_C[t] @ cam_T[k][t] for k in names]) for t in range(T)])
    cen = np.mean([OBJw[0, b, :3, :3] @ np.asarray(vis[k].vertices).mean(0) + OBJw[0, b, :3, 3] for b, k in enumerate(names)], 0)
    OBJ = np.einsum('ij,tbjk->tbik', MK.table_frame(n, d, W_C[0], cen, a.table_z), OBJw)
    h = np.array([(np.asarray(vis[k].vertices) @ OBJ[0, b, :3, :3].T + OBJ[0, b, :3, 3])[:, 2].min() - a.table_z for b, k in enumerate(names)])
    if not -a.support_tol <= h.min() <= a.support_max:
        sys.exit(f'no support plane under the objects (mock stage a): bottoms {h}')
    sh = np.where(np.abs(h) <= a.snap_max, -h, 0.0); OBJ[:, :, 2, 3] += sh[None]
    q = Rot.from_matrix(OBJ[..., :3, :3].reshape(-1, 3, 3)).as_quat().reshape(T, B, 4)[..., [3, 0, 1, 2]]
    seq = f't3_ep{ep:03d}'; pd = f'{out}/processed/sequence_id={seq}/robot_name=sharpa_wave'; os.makedirs(pd, exist_ok=True)
    os.makedirs(f'{out}/reconstructed_stage', exist_ok=True); open(f'{out}/reconstructed_stage/{seq}_support.usda', 'w').write('#usda 1.0\n')
    pq.write_table(pa.table({'object_body_names': [names], 'object_body_position': [OBJ[..., :3, 3].tolist()],
                             'object_body_wxyz': [q.tolist()], 'robot_left_wrist_position': [np.zeros((T, 3)).tolist()],
                             'object_urdf_paths': [[f'{A}/urdf/{k}_rigid.urdf' for k in names]]}), f'{pd}/mock-0.parquet')
    json.dump(dict(table=dict(inlier_frac=frac, rms_mm=rms * 1000, bottoms_cm=(h * 100).tolist(), shifts_cm=(sh * 100).tolist(),
                              support_fallback_lift_cm=[0.0] * B)), open(f'{out}/ref_summary.json', 'w'))
    audit('mkref_audit', ep=ep, poses=opt('--poses'), hands=opt('--hands'), out=out, assets=A, args=argv[1:])
    print(f'mkref (mock stage a): bottoms {np.round(h * 100, 2).tolist()} cm, shifts {np.round(sh * 100, 2).tolist()} cm')
elif base == 'contact_retarget.py' or base in ('grasp_lock.py', 'wrist_ilc.py', 'support_fill.py'):
    src, dst = argv[1], (argv[4] if base == 'support_fill.py' else argv[2]); os.makedirs(os.path.dirname(dst), exist_ok=True)
    shutil.copy(src, dst); stem = os.path.splitext(dst)[0]
    import pyarrow.parquet as pq
    names = pq.read_table(src, columns=['object_body_names']).column('object_body_names')[0].as_py()
    if base == 'contact_retarget.py':
        json.dump(dict(rest_settle={k: [0.0, 0.0] for k in names}), open(f'{stem}_contact_retarget.json', 'w'))
    if base == 'support_fill.py':
        json.dump(dict(objects={k: dict(filled=False, fills=[]) for k in names}), open(f'{stem}_support_fill.json', 'w'))
    if base == 'grasp_lock.py':
        json.dump(dict(phases=[dict(object=k, replan=False) for k in names]), open(f'{stem}_grasp_lock.json', 'w'))
        print('grasp pose (mock)')
    audit('ref_audit', stage=base, src=src, dst=dst, args=argv[1:])
elif base == 'trace_rollout.py':
    np.savez(argv[2], mock=np.zeros(1))
elif base == 'trace_score.py':
    print('zero_action: 0.6100')
elif base == 'rest_check.py':
    print('{"ok": true, "mock": 1}')
elif base == 'ckpt_curve_summary.py':
    print('policy_mock 0.6')
elif base == 'train_flash_sac.py':
    k = kv(''); run = k['output_dir']; steps = int(k['training.total_environment_steps']); os.makedirs(run, exist_ok=True)
    audit('train_audit', task=k.get('task.parquet'), run=run, seed=k.get('reset.seed'), embodiment=k.get('embodiment'), steps=steps,
          extra=sorted(x for x in argv[1:] if x.split('=', 1)[0] not in ('output_dir', 'task.parquet', 'reset.seed')),
          env={e: os.environ.get(e) for e in ('FC_FDR_OBJ', 'FC_FDR_TIPS', 'FC_VOC_INERTIA', 'FC_IMMEDIATE_FIRST_FRAME', 'SF')}, t=time.time())
    time.sleep(3)
    for s in np.linspace(0.2, 1.0, 5):
        open(f'{run}/policy_{int(s * steps) // 4096 * 4096}.safetensors', 'w').write(json.dumps(dict(task=k.get('task.parquet'))))
    audit('train_audit', done=run, t=time.time())
elif base == 'evaluate_policy.py':
    k = kv('evaluation.'); ck = k['evaluation.checkpoint']; os.makedirs(os.path.dirname(k['evaluation.metrics_output']), exist_ok=True)
    json.dump(dict(mock=1, checkpoint=ck), open(k['evaluation.metrics_output'], 'w'))
    open(k['evaluation.object_trajectories_output'], 'w').write(open(ck).read())     # the checkpoint's task, for the qa stub
    audit('eval_audit', ck=ck, out=k['evaluation.metrics_output'])
elif base == 'qa.py':
    if argv[1] == 'ref':
        print('qa_ref (mock): ok')
    else:
        d, ep = argv[2], argv[3]; f = [x for x in os.listdir(d) if x.endswith('.parquet')]
        task = json.load(open(f'{d}/{f[0]}'))['task'] if f else '?'
        o = '/refs/oracle' in task; v = round((0.80 if o else 0.55) + 0.1 * h01(d), 4)
        json.dump(dict(sim_vs_ref=v, floor_vs_ref=0.3, task=task), open(f'{d}/qa_policy.json', 'w')); print(json.dumps(dict(sim_vs_ref=v)))
elif base == 'score_registered.py':
    ep, d = argv[1], argv[2]; f = [x for x in os.listdir(d) if x.endswith('.parquet')]
    task = json.load(open(f'{d}/{f[0]}'))['task'] if f else '?'; o = '/refs/oracle' in task
    sc = lambda x: dict(AUC=round(x, 4), SP_SR=1.0, MP_SR=1.0)
    out = opt('--out', f'{d}/score_registered_ep{ep}.json')
    json.dump(dict(sim=sc((0.85 if o else 0.6) + 0.1 * h01(d + 'a')), reference=sc(0.97 if o else 0.88), static_floor=sc(0.59),
                   meshes=opt('--meshes')), open(out, 'w'))
else:
    real()
