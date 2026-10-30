"""(settle_at2: settle_at.py + final poses T_end / T_ref per frame, for the twin GT diagnostic.) Hands-free settle at any reference frame in FlashCHORD's own physics (scratch, 2026-10-29; scene construction and
hand parking copied from tools/carve_fc_test.py, the settle idea of tools/sim_settle.py generalised to frame F).

Builds the scene as training / evaluation do (setup_scene from a copy of the reference tree with its object URDFs
rewritten to ASSETS, CoACD decomposition on, support on, 1 world, CPU), parks both hands 3 m away with zero actuator
gains, places every object at its reference pose of frame F (zero velocity) and steps Newton's SolverMuJoCo (MuJoCo
Warp on CPU) at the env's sim_dt with gravity and NO drive for STEPS control frames (20 per second). Reports each
object's displacement from its frame-F pose (cm, deg) after 1 control frame (the reset jolt, 50 ms), 1 s, 2 s and its
peak, plus the drift of B relative to A. Our reference only; no ground truth.
Usage (FlashCHORD venv, FC=<flash_chord root>): settle_at.py --tree REF_TREE --assets ASSETS --frames F1,F2 --out OUT.json
       [--steps 40] [--tag NAME]"""
import argparse, json, os, shutil, time

import numpy as np

ap = argparse.ArgumentParser()
ap.add_argument('--tree', required=True); ap.add_argument('--assets', required=True); ap.add_argument('--out', required=True)
ap.add_argument('--frames', required=True); ap.add_argument('--steps', type=int, default=40); ap.add_argument('--tag', default='')
a = ap.parse_args()
FC = os.environ['FC']
import pyarrow as pa, pyarrow.parquet as pq, warp as wp
from scipy.spatial.transform import Rotation as Rot

tag = a.tag or os.path.splitext(os.path.basename(a.out))[0]
root = os.path.join(os.path.dirname(os.path.abspath(a.out)), 'trees', tag)
src_pq = next(os.path.join(dp, f) for dp, _, fs in os.walk(os.path.join(a.tree, 'processed')) for f in fs if f.endswith('.parquet'))
seq = next(p.split('=', 1)[1] for p in src_pq.split(os.sep) if p.startswith('sequence_id='))
dst = os.path.join(root, 'processed', f'sequence_id={seq}', 'robot_name=sharpa_wave'); os.makedirs(dst, exist_ok=True)
os.makedirs(os.path.join(root, 'reconstructed_stage'), exist_ok=True)
shutil.copy(os.path.join(a.tree, 'reconstructed_stage', f'{seq}_support.usda'), os.path.join(root, 'reconstructed_stage'))
t = pq.read_table(src_pq); row = t.to_pylist()[0]; names = list(row['object_body_names'])
rep = {'object_urdf_paths': [os.path.abspath(f'{a.assets}/urdf/{n}_rigid.urdf') for n in names],
       'object_mesh_paths': [os.path.abspath(f'{a.assets}/mesh/{n}/{n}.glb') for n in names]}
for k, v in rep.items():
    i = t.column_names.index(k); t = t.set_column(i, k, pa.array([v], type=t.schema.field(k).type))
parquet = os.path.join(dst, 'ref.parquet'); pq.write_table(t, parquet)
pos = np.array(row['object_body_position'], float); quat = np.array(row['object_body_wxyz'], float)[..., [1, 2, 3, 0]]
nF = len(pos)

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
info = dict(tree=a.tree, assets=a.assets, names=names, build_sec=round(time.time() - t0, 1), steps=a.steps,
            collide_shapes=[int(((sb == b) & ((sf & collide) != 0)).sum()) for b in obj_body],
            sim=dict(fps=float(sc.fps), substeps=int(sc.substeps), sim_dt=float(sc.sim_dt)), frames={})
print(json.dumps(info), flush=True)
child = m.joint_child.numpy(); qs = m.joint_q_start.numpy()
q0 = [int(qs[int(np.nonzero(child == b)[0][0])]) for b in obj_body]
dt = float(sc.sim_dt); sub = int(sc.substeps)


def ref_T(k, f):
    T = np.eye(4); T[:3, :3] = Rot.from_quat(quat[f, k]).as_matrix(); T[:3, 3] = pos[f, k]; return T


def body_T(state, k):
    bq = state.body_q.numpy()[obj_body[k]]; T = np.eye(4)
    T[:3, :3] = Rot.from_quat(bq[3:7]).as_matrix(); T[:3, 3] = bq[:3]; return T


def err(Ta, Tb):
    return [round(float(np.linalg.norm(Ta[:3, 3] - Tb[:3, 3])) * 100, 2),
            round(float(np.degrees(Rot.from_matrix(Ta[:3, :3] @ Tb[:3, :3].T).magnitude())), 1)]


with wp.ScopedDevice('cpu'):
    for nm in ('actuator_gainprm', 'actuator_biasprm'):
        arr = getattr(sol.mjw_model, nm); v = arr.numpy(); v[...] = 0; arr.assign(v)
    for F in [int(x) for x in a.frames.split(',')]:
        F = min(F, nF - 1)
        env.reset(frame_id=F)
        s0, s1 = env.state_0, env.state_1
        q = s0.joint_q.numpy().copy()
        q[0:3] = [3.0, 0.0, 0.3]; q[29:32] = [-3.0, 0.0, 0.3]                      # park the floating wrists far away
        for k in range(len(names)):
            T = ref_T(k, F); q[q0[k]:q0[k] + 3] = T[:3, 3]; q[q0[k] + 3:q0[k] + 7] = Rot.from_matrix(T[:3, :3]).as_quat()
        s0.joint_q.assign(q.astype(np.float32)); s0.joint_qd.zero_(); newton.eval_fk(m, s0.joint_q, s0.joint_qd, s0)
        C = [np.linalg.inv(body_T(s0, k)) @ ref_T(k, F) for k in range(len(names))]   # body -> mesh frame
        rows = []; nan = None; t1 = time.time()
        for f in range(a.steps):
            for s in range(sub):
                s0.clear_forces()
                sol.step(s0, s1, env.control, env.contacts, dt); s0, s1 = s1, s0
            if not np.all(np.isfinite(s0.body_q.numpy()[obj_body])):
                nan = f; break
            Tk = [body_T(s0, k) @ C[k] for k in range(len(names))]
            r = dict(t=round((f + 1) * dt * sub, 2))
            for k, n in enumerate(names):
                r[n] = err(Tk[k], ref_T(k, F))
            if len(names) == 2:
                r['rel'] = err(np.linalg.inv(Tk[0]) @ Tk[1], np.linalg.inv(ref_T(0, F)) @ ref_T(1, F))
            rows.append(r)
        out = dict(sim_sec=round(time.time() - t1, 1), nan_at_step=nan, series=rows)
        if rows:
            out['T_end'] = {n: np.round(Tk[k], 6).tolist() for k, n in enumerate(names)}
            out['T_ref'] = {n: np.round(ref_T(k, F), 6).tolist() for k, n in enumerate(names)}
        for key in names + (['rel'] if len(names) == 2 else []):
            if rows:
                cm = np.array([x[key][0] for x in rows]); dg = np.array([x[key][1] for x in rows])
                pick = lambda i: [float(cm[min(i, len(cm) - 1)]), float(dg[min(i, len(dg) - 1)])]
                out[key] = dict(jolt_50ms=pick(0), at_1s=pick(19), at_2s=pick(39), end=pick(len(cm) - 1),
                                peak_cm=round(float(cm.max()), 2), peak_deg=round(float(dg.max()), 1))
        info['frames'][str(F)] = out
        print(F, json.dumps({k: v for k, v in out.items() if k not in ('series', 'T_end', 'T_ref')}), flush=True)
json.dump(info, open(a.out, 'w'), indent=1)
