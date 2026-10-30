"""ORACLE DIAGNOSTIC (public episodes only): the FlashCHORD-side parts of the leak decomposition's Tier A
(docs/research/work/leak-decomp-20261030/PLAN.md §3, A3 and A7), on CPU in the FlashCHORD venv. Inputs are written by
tools/leak_tierA.py (a3prep, a7prep); it reads no ground truth itself, but its inputs are built from mocap and scans, so
every path must contain 'oracle'.
  rest    A3, contact-retargeting stage: pipeline/contact_retarget.rest_settle, unchanged, on the mkref stage-(a) object
          poses and stage-(b) hand joints of an a3prep npz, with the scene's own hull SDFs (contact_retarget.HullSDF of
          the CoACD pieces FlashCHORD builds from ASSETS) and the table top at TABLE_Z, exactly as contact_retarget.py
          --rest_settle 1 runs it. Writes <npz>_settle.npz (OBJ_settle, stats).
  settle  A7: 2 s hands-free settle (hands parked 3 m away, zero actuator gains, gravity, no drive; FlashCHORD's own
          Newton SolverMuJoCo at the env's sim_dt, 40 control frames; tools/carve settle_at.py's method) from each rest
          configuration of an a7prep npz. Writes <npz>_settle.json: per configuration and object the drift (cm, deg)
          after 1 control frame, 1 s and 2 s, the peak, and NaN.
Scene: setup_scene as training and evaluation build it (CoACD on, support on, 1 world, CPU) from a synthesized
reference tree: a stored public reference parquet as TEMPLATE (robot columns kept; the hands are parked or unused), the
episode's objects with URDFs/meshes from ASSETS, and a support cylinder (top TABLE_Z, radius 0.45 m = mkref's
--table_radius default, centred on the objects).
Usage (FlashCHORD venv, FC=<flash_chord root>, FLASH_CHORD_CACHE_DIR set):
  leak_settle.py rest   --template REF.parquet --assets ASSETS NPZ ...
  leak_settle.py settle --template REF.parquet NPZ ...        (each a7prep npz names its own ASSETS)
(2026-10-30)
"""
import argparse, json, os, sys, time

import numpy as np

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, 'pipeline'))
TABLE_Z, DISC_R = 0.60, 0.45
USDA = """#usda 1.0
(
    defaultPrim = "support_surfaces"
    metersPerUnit = 1
    upAxis = "Z"
)

def Xform "support_surfaces"
{{
    def Cylinder "table" (
        prepend apiSchemas = ["PhysicsCollisionAPI"]
    )
    {{
        uniform token axis = "Z"
        double height = 0.020000
        color3f[] primvars:displayColor = [(0.6, 0.6, 0.6)]
        double radius = {r:.6f}
        double3 xformOp:translate = ({x:.6f}, {y:.6f}, {z:.6f})
        uniform token[] xformOpOrder = ["xformOp:translate"]
    }}
}}
"""


def wxyz(R):
    from scipy.spatial.transform import Rotation as Rot
    return Rot.from_matrix(R).as_quat()[..., [3, 0, 1, 2]]


def make_tree(root, seq, names, assets, P0, template):
    """Reference tree for setup_scene: TEMPLATE's parquet with the objects replaced (every frame at the poses P0 (B,4,4),
    table frame) and a support cylinder under them."""
    import pyarrow as pa, pyarrow.parquet as pq
    from scipy.spatial.transform import Rotation as Rot
    t = pq.read_table(template); row = t.to_pylist()[0]; T = len(row['object_body_position']); B = len(names)
    pos = np.repeat(P0[None, :, :3, 3], T, 0); q = np.repeat(wxyz(P0[:, :3, :3])[None], T, 0)
    row.update(object_name='__'.join(names), safe_object_name='__'.join(names), object_body_names=list(names),
               safe_object_body_names=list(names), sequence_id=seq,
               object_mesh_paths=[os.path.abspath(f'{assets}/mesh/{n}/{n}.glb') for n in names],
               object_urdf_paths=[os.path.abspath(f'{assets}/urdf/{n}_rigid.urdf') for n in names],
               object_mesh_radius=[0.1] * B, object_body_position=pos.tolist(), object_body_wxyz=q.tolist(),
               object_root_position=pos[:, 0].tolist(),
               object_root_axis_angle=np.repeat(Rot.from_matrix(P0[0, :3, :3]).as_rotvec()[None], T, 0).tolist())
    for s in ('left', 'right'):                                     # contact part ids name bodies 1..B
        k = f'mano_{s}_object_contact_part_ids'; v = np.array(row[k]); v[v > B] = 0; row[k] = v.tolist()
    dst = os.path.join(root, 'processed', f'sequence_id={seq}', 'robot_name=sharpa_wave'); os.makedirs(dst, exist_ok=True)
    os.makedirs(os.path.join(root, 'reconstructed_stage'), exist_ok=True)
    c = P0[:, :2, 3].mean(0)
    open(os.path.join(root, 'reconstructed_stage', f'{seq}_support.usda'), 'w').write(USDA.format(r=DISC_R, x=c[0], y=c[1], z=TABLE_Z - 0.01))
    parquet = os.path.join(dst, 'ref.parquet'); pq.write_table(pa.Table.from_pylist([row], schema=t.schema), parquet)
    return parquet


def build(parquet):
    """The scene and env as tools/carve settle_at.py builds them (= training / evaluation, 1 world, CPU)."""
    import warp as wp, newton
    from hydra import compose, initialize_config_dir
    from flash_chord.configuration import instantiate_typed
    from flash_chord.embodiments.base import Embodiment
    from flash_chord.envs.rl import RLEnv, RLEnvConfig
    from flash_chord.scene.collision import CollisionPolicy
    from flash_chord.scene.setup import setup_scene
    FC = os.environ['FC']
    with initialize_config_dir(version_base='1.3', config_dir=f'{FC}/src/flash_chord/configs'):
        cfg = compose(config_name='train_flash_sac', overrides=['experiment=sharpa_flash_sac', f"task.parquet='{parquet}'"])
    env_config = instantiate_typed(cfg.env, RLEnvConfig)
    with wp.ScopedDevice('cpu'):
        st = setup_scene(parquet=parquet, control_fps=env_config.sim.fps, motion_speed=1.0,
                         embodiment=instantiate_typed(cfg.embodiment, Embodiment),
                         collision=instantiate_typed(cfg.collision, CollisionPolicy), world_count=1, include_support=True,
                         decompose_objects=True)
        env = RLEnv(st.scene, st.reference, config=env_config)
    return st, env, env_config.sim


def obj_bodies(m, names):
    labels = list(getattr(m, 'body_label', None) or getattr(m, 'body_key', []))
    return [next(i for i, l in enumerate(labels) if l.startswith(f'track3_{n}/')) for n in names]


def rest(a):
    from scipy.spatial.transform import Rotation as Rot
    import contact_retarget as CR
    for f in a.npz:
        if 'oracle' not in os.path.abspath(f):
            sys.exit(f'{f}: inputs must live under an "oracle" path')
        t0 = time.time(); Z = np.load(f); names = [str(x) for x in Z['names']]; OBJ = Z['OBJ_a']; T, B = OBJ.shape[:2]
        root = f[:-4] + '_tree'
        st, env, _ = build(make_tree(root, 'leak_rest', names, a.assets, OBJ[0], a.template))
        m = st.scene.model; sdfs = [CR.HullSDF(m, b) for b in obj_bodies(m, names)]
        OP = OBJ[:, :, :3, 3].copy(); OR = [[Rot.from_matrix(OBJ[t, j, :3, :3]) for t in range(T)] for j in range(B)]
        J = {'left': Z['J_left'], 'right': Z['J_right']}
        OP2, OR2, stats = CR.rest_settle(OP, OR, J, sdfs, float(Z['table_z']))
        OUT = OBJ.copy()
        for j in range(B):
            OUT[:, j, :3, :3] = np.stack([r.as_matrix() for r in OR2[j]]); OUT[:, j, :3, 3] = OP2[:, j]
        np.savez(f[:-4] + '_settle.npz', names=Z['names'], OBJ_settle=OUT, stats=json.dumps(dict(zip(names, stats))),
                 pieces=json.dumps({n: len(s.pieces) for n, s in zip(names, sdfs)}))
        print(f'{os.path.basename(f)}: rest_settle {dict(zip(names, stats))} ({time.time() - t0:.0f} s)', flush=True)


def settle(a):
    import warp as wp, newton
    from scipy.spatial.transform import Rotation as Rot
    for f in a.npz:
        if 'oracle' not in os.path.abspath(f):
            sys.exit(f'{f}: inputs must live under an "oracle" path')
        t0 = time.time(); Z = np.load(f); names = [str(x) for x in Z['names']]; C = Z['configs']; frames = Z['frames'].tolist()
        assets = str(Z['assets'])
        st, env, sc = build(make_tree(f[:-4] + '_tree', 'leak_settle', names, assets, C[0], a.template))
        m = st.scene.model; sol = env.solver; ob = obj_bodies(m, names)
        child = m.joint_child.numpy(); qs = m.joint_q_start.numpy()
        q0 = [int(qs[int(np.nonzero(child == b)[0][0])]) for b in ob]
        dt, sub = float(sc.sim_dt), int(sc.substeps)
        sb = m.shape_body.numpy(); sf = m.shape_flags.numpy(); collide = int(newton.ShapeFlags.COLLIDE_SHAPES)
        info = dict(npz=os.path.abspath(f), assets=assets, names=names, build_sec=round(time.time() - t0, 1),
                    collide_shapes={n: int(((sb == b) & ((sf & collide) != 0)).sum()) for n, b in zip(names, ob)},
                    sim=dict(fps=float(sc.fps), substeps=sub, sim_dt=dt), steps=a.steps, configs={})

        def body_T(state, k):
            bq = state.body_q.numpy()[ob[k]]; T = np.eye(4); T[:3, :3] = Rot.from_quat(bq[3:7]).as_matrix(); T[:3, 3] = bq[:3]; return T

        def err(Ta, Tb):
            return [round(float(np.linalg.norm(Ta[:3, 3] - Tb[:3, 3]) * 100), 2),
                    round(float(np.degrees(Rot.from_matrix(Ta[:3, :3] @ Tb[:3, :3].T).magnitude())), 1)]

        with wp.ScopedDevice('cpu'):
            for nm in ('actuator_gainprm', 'actuator_biasprm'):
                arr = getattr(sol.mjw_model, nm); v = arr.numpy(); v[...] = 0; arr.assign(v)
            for i, F in enumerate(frames):
                P = C[i]; env.reset(frame_id=0); s0, s1 = env.state_0, env.state_1
                q = s0.joint_q.numpy().copy(); q[0:3] = [3.0, 0.0, 0.3]; q[29:32] = [-3.0, 0.0, 0.3]   # park the wrists
                for k in range(len(names)):
                    q[q0[k]:q0[k] + 3] = P[k, :3, 3]; q[q0[k] + 3:q0[k] + 7] = Rot.from_matrix(P[k, :3, :3]).as_quat()
                s0.joint_q.assign(q.astype(np.float32)); s0.joint_qd.zero_(); newton.eval_fk(m, s0.joint_q, s0.joint_qd, s0)
                Cb = [np.linalg.inv(body_T(s0, k)) @ P[k] for k in range(len(names))]                 # body -> mesh frame
                rows, nan = [], None
                for step in range(a.steps):
                    for _ in range(sub):
                        s0.clear_forces(); sol.step(s0, s1, env.control, env.contacts, dt); s0, s1 = s1, s0
                    if not np.all(np.isfinite(s0.body_q.numpy()[ob])):
                        nan = step; break
                    Tk = [body_T(s0, k) @ Cb[k] for k in range(len(names))]
                    rows.append({n: err(Tk[k], P[k]) for k, n in enumerate(names)})
                out = dict(nan_at_step=nan)
                for n in names:
                    if rows:
                        cm = np.array([x[n][0] for x in rows]); dg = np.array([x[n][1] for x in rows])
                        pick = lambda j: [float(cm[min(j, len(cm) - 1)]), float(dg[min(j, len(dg) - 1)])]   # noqa: E731
                        out[n] = dict(jolt=pick(0), at_1s=pick(19), at_2s=pick(a.steps - 1), peak=[float(cm.max()), float(dg.max())])
                info['configs'][str(F)] = out
                print(f'{os.path.basename(f)} f{F}: ' + json.dumps({n: out.get(n, {}).get('at_2s') for n in names}) + f' nan {nan}', flush=True)
        info['seconds'] = round(time.time() - t0, 1)
        json.dump(info, open(f[:-4] + '_settle.json', 'w'), indent=1)


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('mode', choices=['rest', 'settle']); p.add_argument('npz', nargs='+')
    p.add_argument('--template', required=True); p.add_argument('--assets', default=None); p.add_argument('--steps', type=int, default=40)
    a = p.parse_args()
    if a.mode == 'rest' and not a.assets:
        sys.exit('rest needs --assets (the simulator assets of library_v3, make_assets.py)')
    (rest if a.mode == 'rest' else settle)(a)


if __name__ == '__main__':
    main()
