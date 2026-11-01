"""Probe: build the FlashCHORD scene (2 worlds) from a reference tree with ASSETS and print the joint layout,
collision shape counts per object and per-hull volumes. Usage (FC venv, from flash_chord dir): probe_scene.py TREE ASSETS WORK"""
import os, sys, shutil, time, json
import numpy as np
tree, assets, work = sys.argv[1:4]
FC = os.environ['FC']
import pyarrow as pa, pyarrow.parquet as pq, warp as wp
src_pq = next(os.path.join(dp, f) for dp, _, fs in os.walk(os.path.join(tree, 'processed')) for f in fs if f.endswith('.parquet'))
seq = next(p.split('=', 1)[1] for p in src_pq.split(os.sep) if p.startswith('sequence_id='))
dst = os.path.join(work, 'processed', f'sequence_id={seq}', 'robot_name=sharpa_wave'); os.makedirs(dst, exist_ok=True)
os.makedirs(os.path.join(work, 'reconstructed_stage'), exist_ok=True)
shutil.copy(os.path.join(tree, 'reconstructed_stage', f'{seq}_support.usda'), os.path.join(work, 'reconstructed_stage'))
t = pq.read_table(src_pq); row = t.to_pylist()[0]; names = list(row['object_body_names'])
rep = {'object_urdf_paths': [os.path.abspath(f'{assets}/urdf/{n}_rigid.urdf') for n in names],
       'object_mesh_paths': [os.path.abspath(f'{assets}/mesh/{n}/{n}.glb') for n in names]}
for k, v in rep.items():
    i = t.column_names.index(k); t = t.set_column(i, k, pa.array([v], type=t.schema.field(k).type))
parquet = os.path.join(dst, 'ref.parquet'); pq.write_table(t, parquet)
from hydra import compose, initialize_config_dir
from flash_chord.configuration import instantiate_typed
from flash_chord.embodiments.base import Embodiment
from flash_chord.envs.rl import RLEnv, RLEnvConfig
from flash_chord.scene.collision import CollisionPolicy
from flash_chord.scene.setup import setup_scene
import newton
ov = ['experiment=sharpa_flash_sac', f"task.parquet='{parquet}'"] + ([f"embodiment={os.environ['EMB']}"] if os.environ.get('EMB') else [])
with initialize_config_dir(version_base='1.3', config_dir=f'{FC}/src/flash_chord/configs'):
    cfg = compose(config_name='train_flash_sac', overrides=ov)
env_config = instantiate_typed(cfg.env, RLEnvConfig); sc = env_config.sim
t0 = time.time()
with wp.ScopedDevice('cpu'):
    st = setup_scene(parquet=parquet, control_fps=sc.fps, motion_speed=1.0, embodiment=instantiate_typed(cfg.embodiment, Embodiment),
                     collision=instantiate_typed(cfg.collision, CollisionPolicy), world_count=2, include_support=True,
                     decompose_objects=True)
    env = RLEnv(st.scene, st.reference, config=env_config)
print('build s', round(time.time() - t0, 1))
m = st.scene.model
labels = list(getattr(m, 'body_label', None) or getattr(m, 'body_key', []))
jl = list(getattr(m, 'joint_label', None) or getattr(m, 'joint_key', []))
jt = m.joint_type.numpy(); qs = m.joint_q_start.numpy(); child = m.joint_child.numpy(); jw = m.joint_world.numpy() if hasattr(m, 'joint_world') else None
print('bodies', len(labels), 'joints', len(jl), 'coords', m.joint_coord_count, 'world_count', m.world_count)
for j in range(len(jl)):
    if j < 40 or 'track3' in labels[child[j]]:
        print(j, jl[j], int(jt[j]), 'q_start', int(qs[j]), 'child', labels[child[j]], 'world', None if jw is None else int(jw[j]))
print('JointType FREE', int(newton.JointType.FREE), 'PRISMATIC', int(newton.JointType.PRISMATIC))
sb = m.shape_body.numpy(); sf = m.shape_flags.numpy(); collide = int(newton.ShapeFlags.COLLIDE_SHAPES); stype = m.shape_type.numpy()
src = m.shape_source
for n in names:
    bs = [i for i, l in enumerate(labels) if l.startswith(f'track3_{n}/')]
    for b in bs:
        ids = np.nonzero((sb == b) & ((sf & collide) != 0))[0]
        vols = []; nv = []
        for s in ids:
            mm = src[s]
            V = np.asarray(mm.vertices, float); F = np.asarray(mm.indices).reshape(-1, 3)
            import trimesh
            tm = trimesh.Trimesh(V, F, process=False); vols.append(abs(tm.volume)); nv.append(len(V))
        sc_ = m.shape_scale.numpy()[ids]
        print(n, 'body', b, labels[b], 'collide shapes', len(ids), 'types', sorted(set(int(x) for x in stype[ids])),
              'sum hull vol cm3 %.3f' % (sum(vols) * 1e6), 'min vol cm3 %.4f' % (min(vols) * 1e6), 'verts min/max', min(nv), max(nv),
              'scale', np.unique(np.round(sc_, 4), axis=0).tolist())
        allids = np.nonzero(sb == b)[0]
        print('   all shapes on body', len(allids), 'non-colliding', len(allids) - len(ids))
print('sim', sc.fps, sc.substeps, sc.sim_dt)
mj = env.solver.mjw_model
print('gainprm shape', mj.actuator_gainprm.shape, 'nu', getattr(mj, 'nu', None))
