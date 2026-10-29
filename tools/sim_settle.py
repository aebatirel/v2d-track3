"""Settle the start of a reference in the simulator (2026-10-24). Our perceived resting poses can be physically
impossible in the simulator: overlapping convex collision pieces of stacked objects (public ep2: the lid starts ~8 mm
inside the pot's hulls and jumps 31 mm / 27 deg at the first step; ep26: pot in rack, 117 mm / 52 deg) or poses our
meshes cannot hold (ep21 pitcher, ep31 sweeper in the rack). The official evaluation starts from the reference's
frame 0 with no assist, so such a start is a jolt the policy never recovers from.
Here the scene is frozen at frame 0 (all reference frames = frame 0: hands and objects static) and simulated:
HOLD control steps with the virtual object controller on (it holds every object near its perceived pose while the
contacts push overlapping pieces apart; gravity compensated), then FREE steps with it off (everything comes to rest).
Each object's settled pose S replaces its reference pose until its first hold closes (first hold start + CLOSE frames)
and is then blended into the perceived trajectory over CARRY frames (as grasp_lock's re-plan carry-back); an object no
hand holds keeps S for the whole episode. Only our own reference is read and changed (no ground truth); the hands are
not changed (grasp_lock locks them to the object frame afterwards).
Usage (FlashCHORD venv, from the flash_chord dir; EMB / DEV as tools/trace_rollout.py):
  sim_settle.py IN.parquet OUT.parquet [--hold 20] [--free 30] [--close 10] [--carry 20]
IN must sit in a reference tree (<tree>/processed/sequence_id=*/robot_name=*/x.parquet, <tree>/reconstructed_stage);
OUT is written with a report OUT_settle.json; a static copy of the scene goes to <OUT tree>_settle_static/.
"""
import argparse, dataclasses, json, os, shutil, sys

import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq
from scipy.spatial.transform import Rotation as R, Slerp

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'pipeline'))
from hold_phases import hold_phases  # noqa: E402

p = argparse.ArgumentParser(); p.add_argument('inp'); p.add_argument('out')
p.add_argument('--hold', type=int, default=20); p.add_argument('--free', type=int, default=30)
p.add_argument('--close', type=int, default=10); p.add_argument('--carry', type=int, default=20)
a = p.parse_args()
inp = os.path.abspath(a.inp); out = os.path.abspath(a.out)
t = pq.read_table(inp); names = t.column('object_body_names')[0].as_py(); B = len(names)
T = len(t.column('robot_left_wrist_position')[0].as_py())
OP = np.array(t.column('object_body_position')[0].as_py(), float).reshape(T, B, 3)
OQ = np.array(t.column('object_body_wxyz')[0].as_py(), float).reshape(T, B, 4)[..., [1, 2, 3, 0]]

# 1) static copy of the scene: every per-frame column repeats frame 0
tree_in = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(inp)))); hive = os.path.relpath(os.path.dirname(inp), tree_in)
tree_out = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(out))))
stat = tree_out.rstrip('/') + '_settle_static'; os.makedirs(os.path.join(stat, hive), exist_ok=True)
if os.path.isdir(os.path.join(tree_in, 'reconstructed_stage')) and not os.path.isdir(os.path.join(stat, 'reconstructed_stage')):
    shutil.copytree(os.path.join(tree_in, 'reconstructed_stage'), os.path.join(stat, 'reconstructed_stage'))
st_tab = t
for c in t.column_names:
    v = t.column(c)[0].as_py()
    if isinstance(v, list) and len(v) == T and T > 1:
        st_tab = st_tab.set_column(st_tab.column_names.index(c), c, pa.array([[v[0]] * T], type=t.schema.field(c).type))
static_parquet = os.path.join(stat, hive, os.path.basename(inp)); pq.write_table(st_tab, static_parquet)

# 2) simulate: object assist on (HOLD steps), then off (FREE steps)
import warp as wp  # noqa: E402
from hydra import compose, initialize_config_dir  # noqa: E402
from flash_chord.configuration import instantiate_typed  # noqa: E402
from flash_chord.embodiments.base import Embodiment  # noqa: E402
from flash_chord.envs.rl import RLEnv, RLEnvConfig  # noqa: E402
from flash_chord.scene.collision import CollisionPolicy  # noqa: E402
from flash_chord.scene.setup import setup_scene  # noqa: E402
off = [f'termination.{k}.enabled=false' for k in ('wrist_position', 'object_position', 'object_orientation', 'reference_end')]
with initialize_config_dir(version_base='1.3', config_dir=os.path.abspath('src/flash_chord/configs')):
    cfg = compose(config_name='train_flash_sac', overrides=['experiment=sharpa_flash_sac', f"task.parquet='{static_parquet}'"] + off
                  + ([f"embodiment={os.environ['EMB']}"] if os.environ.get('EMB') else []))
env_config = dataclasses.replace(instantiate_typed(cfg.env, RLEnvConfig), auto_reset=False, voc_scale=1.0)
emb = instantiate_typed(cfg.embodiment, Embodiment); col = instantiate_typed(cfg.collision, CollisionPolicy)
track = []
with wp.ScopedDevice(os.environ.get('DEV', 'cuda')):
    stp = setup_scene(parquet=static_parquet, control_fps=env_config.sim.fps, motion_speed=1.0, embodiment=emb, collision=col,
                      world_count=1, include_support=True, decompose_objects=True)
    env = RLEnv(stp.scene, stp.reference, config=env_config)
    labels = list(getattr(stp.scene.model, 'body_label', None) or getattr(stp.scene.model, 'body_key', []))
    ob = [labels.index(f'track3_{n}/object') for n in names]
    env.reset(frame_id=0); env.set_voc_scale(1.0)
    for k in range(a.hold + a.free):
        if k == a.hold:
            env.set_voc_scale(0.0)
        env.step(None); track.append(env.state_0.body_q.numpy()[ob].copy())
track = np.array(track)                                             # (steps, B, 7) xyz + xyzw
S_p, S_q = track[-1, :, :3].astype(float), track[-1, :, 3:7].astype(float)

# 3) new object trajectories
phases = hold_phases(inp)[0]['phases']; NP, NQ = OP.copy(), OQ.copy(); report = {}
for j, n in enumerate(names):
    starts = [x['start'] for x in phases if x['object'] == n]
    b1 = (min(starts) + a.close) if starts else T; b1 = min(b1, T)
    for f in range(T):
        if f < b1:
            NP[f, j], NQ[f, j] = S_p[j], S_q[j]
        elif f < b1 + a.carry:
            w = (f - b1 + 1) / (a.carry + 1); NP[f, j] = (1 - w) * S_p[j] + w * OP[f, j]
            NQ[f, j] = Slerp([0, 1], R.from_quat([S_q[j], OQ[f, j]]))([w]).as_quat()[0]
    d0 = float(np.linalg.norm(S_p[j] - OP[0, j])); r0 = float(np.degrees((R.from_quat(S_q[j]) * R.from_quat(OQ[0, j]).inv()).magnitude()))
    peak = float(np.max(np.linalg.norm(track[:, j, :3] - OP[0, j], axis=1)))
    report[n] = dict(settled_off_mm=round(1000 * d0, 1), settled_off_deg=round(r0, 1), peak_mm=round(1000 * peak, 1),
                     first_hold=min(starts) if starts else None, frames_replaced=int(b1), fell=bool(d0 > 0.03 or r0 > 20))
wxyz = NQ[..., [3, 0, 1, 2]]
cols = dict(object_body_position=NP.tolist(), object_body_wxyz=wxyz.tolist(),            # per frame: one list per body
            object_root_position=NP[:, 0].tolist(), object_root_axis_angle=R.from_quat(NQ[:, 0]).as_rotvec().tolist())
o = t
for c, v in cols.items():
    if c in o.column_names:
        o = o.set_column(o.column_names.index(c), c, pa.array([v], type=t.schema.field(c).type))
os.makedirs(os.path.dirname(out), exist_ok=True); pq.write_table(o, out)
json.dump(dict(hold=a.hold, free=a.free, objects=report), open(os.path.splitext(out)[0] + '_settle.json', 'w'), indent=1)
print(json.dumps(report), flush=True)
