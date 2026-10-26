"""Can two objects follow our reference through their interaction in FlashCHORD's own physics? (2026-10-26; test T-a of
docs/research/approaches-2026-10-25/approach1-motion-constrained-meshes.md, for pipeline/interaction_carve.py.)

Builds the scene as training and evaluation do (setup_scene from the reference tree with its object URDFs rewritten to
ASSETS, CoACD decomposition on, support on, 1 world, CPU) and steps Newton's SolverMuJoCo (MuJoCo Warp on the CPU
device) at the env's sim_dt, gravity on. The hands are parked 3 m away with their actuators zeroed (MuJoCo Warp fixes its
collision pairs at build time; interact/v5/s5coll replay_rest.py). Instead of hands, each object is pulled toward its
reference pose by a critically damped spring on its centre of mass and orientation (world wrench through State.body_f,
gravity compensated): object A firmly (a holding hand, HOLD_HZ), object B as the inserting hand (DRIVE_HZ). The
reference is interpolated per physics step. No ground truth: the reference is our own.

Reports per frame and summarised over the window: each object's error to its reference (cm, deg) and the error of B's
pose relative to A against the reference's relative pose, which is what a closed joint needs.
Usage (FlashCHORD venv, FC=<flash_chord root>): carve_fc_test.py --tree REF_TREE --assets ASSETS_DIR --out OUT.json
       [--names A,B] [--start F] [--end F] [--window a:b]"""
import argparse, json, os, shutil, time

import numpy as np

ap = argparse.ArgumentParser()
ap.add_argument('--tree', required=True); ap.add_argument('--assets', required=True); ap.add_argument('--out', required=True)
ap.add_argument('--names', default='wooden_piece_1,wooden_piece_2')
ap.add_argument('--start', type=int, default=0); ap.add_argument('--end', type=int, default=-1)
ap.add_argument('--window', default='', help='frames a:b summarised (e.g. the assembled frames); default start..end')
ap.add_argument('--hold_hz', type=float, default=8.0); ap.add_argument('--drive_hz', type=float, default=8.0)
ap.add_argument('--free_until', type=int, default=-1, help='no drive before this frame (do the objects stand at rest?)')
a = ap.parse_args()
names = a.names.split(','); FC = os.environ['FC']
import pyarrow as pa, pyarrow.parquet as pq, warp as wp
from scipy.spatial.transform import Rotation as Rot, Slerp

# ---- copy of the reference tree with the object assets rewritten
tag = os.path.splitext(os.path.basename(a.out))[0]
root = os.path.join(os.path.dirname(os.path.abspath(a.out)), 'trees', tag)
src_pq = next(os.path.join(dp, f) for dp, _, fs in os.walk(os.path.join(a.tree, 'processed')) for f in fs if f.endswith('.parquet'))
seq = next(p.split('=', 1)[1] for p in src_pq.split(os.sep) if p.startswith('sequence_id='))
dst = os.path.join(root, 'processed', f'sequence_id={seq}', 'robot_name=sharpa_wave'); os.makedirs(dst, exist_ok=True)
os.makedirs(os.path.join(root, 'reconstructed_stage'), exist_ok=True)
shutil.copy(os.path.join(a.tree, 'reconstructed_stage', f'{seq}_support.usda'), os.path.join(root, 'reconstructed_stage'))
t = pq.read_table(src_pq); row = t.to_pylist()[0]
assert list(row['object_body_names']) == names, row['object_body_names']
rep = {'object_urdf_paths': [os.path.abspath(f'{a.assets}/urdf/{n}_rigid.urdf') for n in names],
       'object_mesh_paths': [os.path.abspath(f'{a.assets}/mesh/{n}/{n}.glb') for n in names]}
for k, v in rep.items():
    i = t.column_names.index(k); t = t.set_column(i, k, pa.array([v], type=t.schema.field(k).type))
parquet = os.path.join(dst, 'ref.parquet'); pq.write_table(t, parquet)
pos = np.array(row['object_body_position'], float); quat = np.array(row['object_body_wxyz'], float)[..., [1, 2, 3, 0]]
nF = len(pos); end = nF if a.end < 0 else min(a.end, nF)

from hydra import compose, initialize_config_dir
from flash_chord.configuration import instantiate_typed
from flash_chord.embodiments.base import Embodiment
from flash_chord.envs.rl import RLEnv, RLEnvConfig
from flash_chord.scene.collision import CollisionPolicy
from flash_chord.scene.setup import setup_scene
import newton
with initialize_config_dir(version_base='1.3', config_dir=f'{FC}/src/flash_chord/configs'):
    cfg = compose(config_name='train_flash_sac', overrides=['experiment=sharpa_flash_sac', f"task.parquet='{parquet}'"])
env_config = instantiate_typed(cfg.env, RLEnvConfig); sc = env_config.sim
t0 = time.time()
with wp.ScopedDevice('cpu'):
    st = setup_scene(parquet=parquet, control_fps=sc.fps, motion_speed=1.0, embodiment=instantiate_typed(cfg.embodiment, Embodiment),
                     collision=instantiate_typed(cfg.collision, CollisionPolicy), world_count=1, include_support=True,
                     decompose_objects=True)
    env = RLEnv(st.scene, st.reference, config=env_config)
m = st.scene.model; sol = env.solver
labels = list(getattr(m, 'body_label', None) or getattr(m, 'body_key', []))
obj_body = [next(i for i, l in enumerate(labels) if l.startswith(f'track3_{n}/')) for n in names]
sb = m.shape_body.numpy(); sf = m.shape_flags.numpy(); collide = int(newton.ShapeFlags.COLLIDE_SHAPES)
info = dict(tree=a.tree, assets=a.assets, names=names, build_sec=round(time.time() - t0, 1),
            collide_shapes=[int(((sb == b) & ((sf & collide) != 0)).sum()) for b in obj_body],
            sim=dict(fps=float(sc.fps), substeps=int(sc.substeps), sim_dt=float(sc.sim_dt), njmax=int(sc.njmax), nconmax=int(sc.nconmax)))
print(json.dumps(info), flush=True)
mass = m.body_mass.numpy()[obj_body]; com = m.body_com.numpy()[obj_body]; inertia = m.body_inertia.numpy()[obj_body]
child = m.joint_child.numpy(); qs = m.joint_q_start.numpy()
q0 = [int(qs[int(np.nonzero(child == b)[0][0])]) for b in obj_body]
g = np.array(m.gravity.numpy()).reshape(-1)[:3] if hasattr(m, 'gravity') else np.array([0, 0, -9.81])

dt = float(sc.sim_dt); sub = int(sc.substeps); fdt = dt * sub
times = np.arange(nF) * fdt
slerps = [Slerp(times, Rot.from_quat(quat[:, k])) for k in range(len(names))]


def ref_T(k, tau):
    tau = float(np.clip(tau, 0, times[-1])); i = min(int(tau / fdt), nF - 2); w = tau / fdt - i
    T = np.eye(4); T[:3, :3] = slerps[k]([tau]).as_matrix()[0]; T[:3, 3] = (1 - w) * pos[i, k] + w * pos[i + 1, k]
    return T


def body_T(state, k):
    bq = state.body_q.numpy()[obj_body[k]]; T = np.eye(4)
    T[:3, :3] = Rot.from_quat(bq[3:7]).as_matrix(); T[:3, 3] = bq[:3]; return T


with wp.ScopedDevice('cpu'):
    env.reset(frame_id=a.start)
    s0, s1 = env.state_0, env.state_1
    q = s0.joint_q.numpy().copy()
    q[0:3] = [3.0, 0.0, 0.3]; q[29:32] = [-3.0, 0.0, 0.3]                      # park the floating wrists far away
    for nm in ('actuator_gainprm', 'actuator_biasprm'):
        arr = getattr(sol.mjw_model, nm); v = arr.numpy(); v[...] = 0; arr.assign(v)
    for k in range(len(names)):
        T = ref_T(k, times[a.start]); q[q0[k]:q0[k] + 3] = T[:3, 3]; q[q0[k] + 3:q0[k] + 7] = Rot.from_matrix(T[:3, :3]).as_quat()
    s0.joint_q.assign(q.astype(np.float32)); s0.joint_qd.zero_(); newton.eval_fk(m, s0.joint_q, s0.joint_qd, s0)
    C = [np.linalg.inv(body_T(s0, k)) @ ref_T(k, times[a.start]) for k in range(len(names))]   # body -> mesh frame
    Ci = [np.linalg.inv(c) for c in C]
    hz = [a.hold_hz, a.drive_hz]; rows = []; t1 = time.time(); nan = None
    for f in range(a.start, end):
        for s in range(sub):
            tau = times[f] + (s + 1) * dt
            s0.clear_forces(); bf = s0.body_f.numpy()
            for k in range(len(names) if f >= a.free_until else 0):
                Tb = body_T(s0, k); Tr = ref_T(k, tau) @ Ci[k]; Tr2 = ref_T(k, tau + dt) @ Ci[k]
                w0 = 2 * np.pi * hz[k]
                pc, pr, pr2 = Tb[:3, :3] @ com[k] + Tb[:3, 3], Tr[:3, :3] @ com[k] + Tr[:3, 3], Tr2[:3, :3] @ com[k] + Tr2[:3, 3]
                qd = s0.body_qd.numpy()[obj_body[k]]; v, om = qd[:3], qd[3:]
                vr = (pr2 - pr) / dt; omr = Rot.from_matrix(Tr2[:3, :3] @ Tr[:3, :3].T).as_rotvec() / dt
                F = mass[k] * (w0 ** 2 * (pr - pc) + 2 * w0 * (vr - v) - g)
                Iw = Tb[:3, :3] @ inertia[k] @ Tb[:3, :3].T
                tq = Iw @ (w0 ** 2 * Rot.from_matrix(Tr[:3, :3] @ Tb[:3, :3].T).as_rotvec() + 2 * w0 * (omr - om))
                bf[obj_body[k]] = np.r_[F, tq]
            s0.body_f.assign(bf.astype(np.float32))
            sol.step(s0, s1, env.control, env.contacts, dt); s0, s1 = s1, s0
        if not np.all(np.isfinite(s0.body_q.numpy()[obj_body])):
            nan = f; break
        if os.environ.get('DIAG') and f == a.start:                 # which solver counters exist (contacts, constraints)
            print('mjw_data fields:', sorted(k for k in vars(sol.mjw_data) if any(x in k.lower() for x in ('con', 'efc', 'warn', 'max'))), flush=True)
            bq = s0.body_q.numpy(); objp = bq[obj_body, :3]
            rob = [i for i, l in enumerate(labels) if not any(l.startswith(f'track3_{n}/') for n in names) and 'support' not in l]
            dmin = min((float(np.linalg.norm(bq[i, :3] - p)), labels[i]) for i in rob for p in objp)
            print('closest robot body to an object after parking:', round(dmin[0], 3), 'm', dmin[1], '; robot bodies', len(rob),
                  '; joint_q[0:3]', np.round(q[0:3], 2).tolist(), 'joint_q[29:32]', np.round(q[29:32], 2).tolist(), flush=True)
        if os.environ.get('DIAG'):
            cnt = {}
            for k in ('nacon', 'ncon', 'nefc', 'ne', 'nf', 'nl'):
                v = getattr(sol.mjw_data, k, None)
                if v is not None:
                    v = v.numpy() if hasattr(v, 'numpy') else v; cnt[k] = int(np.max(v))
            print('counts f', f + 1, cnt, flush=True)
        Tk = [body_T(s0, k) @ C[k] for k in range(len(names))]; Rk = [ref_T(k, times[f + 1] if f + 1 < nF else times[-1]) for k in range(len(names))]
        r = dict(f=f + 1)
        for k, n in enumerate(names):
            r[n] = [round(float(np.linalg.norm(Tk[k][:3, 3] - Rk[k][:3, 3])) * 100, 2),
                    round(float(np.degrees(Rot.from_matrix(Tk[k][:3, :3] @ Rk[k][:3, :3].T).magnitude())), 1)]
        if len(names) == 2:
            Ra = np.linalg.inv(Tk[0]) @ Tk[1]; Rr = np.linalg.inv(Rk[0]) @ Rk[1]
            r['rel'] = [round(float(np.linalg.norm(Ra[:3, 3] - Rr[:3, 3])) * 100, 2),
                        round(float(np.degrees(Rot.from_matrix(Ra[:3, :3] @ Rr[:3, :3].T).magnitude())), 1)]
        rows.append(r)
        if (f - a.start) % 20 == 0:
            print(r, flush=True)
info['sim_sec'] = round(time.time() - t1, 1); info['nan_at_frame'] = nan
w0_, w1_ = (int(x) for x in a.window.split(':')) if a.window else (a.start + 1, end)
W = [r for r in rows if w0_ <= r['f'] <= w1_]
summ = {}
for key in names + (['rel'] if len(names) == 2 else []):
    cm = np.array([r[key][0] for r in W]); dg = np.array([r[key][1] for r in W])
    summ[key] = dict(cm_median=round(float(np.median(cm)), 2), cm_max=round(float(cm.max()), 2),
                     deg_median=round(float(np.median(dg)), 1), deg_max=round(float(dg.max()), 1)) if len(W) else None
info.update(window=[w0_, w1_], summary=summ, series=rows)
json.dump(info, open(a.out, 'w'), indent=1)
print(json.dumps({k: v for k, v in info.items() if k != 'series'}), flush=True)
