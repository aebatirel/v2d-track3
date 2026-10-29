"""DIAGNOSTIC (2026-10-23): print the physical parameters a grasp has to live with in FlashCHORD's training/eval scene:
finger and wrist drive gains, effort limits and joint ranges, contact material per shape (friction, stiffness), masses
and inertias. Used to size grip forces in the physics-aware grasp design (docs/research/notes/24). No ground truth.
Usage (FlashCHORD python, from the flash_chord dir): sim_physics_inventory.py PARQUET [OUT.json]   env EMB: embodiment
"""
import dataclasses, json, os, sys

import numpy as np


def main():
    import warp as wp
    from hydra import compose, initialize_config_dir
    from flash_chord.configuration import instantiate_typed
    from flash_chord.embodiments.base import Embodiment
    from flash_chord.envs.rl import RLEnvConfig
    from flash_chord.scene.collision import CollisionPolicy
    from flash_chord.scene.setup import setup_scene
    parquet = os.path.abspath(sys.argv[1])
    with initialize_config_dir(version_base='1.3', config_dir=os.path.abspath('src/flash_chord/configs')):
        cfg = compose(config_name='train_flash_sac', overrides=['experiment=sharpa_flash_sac', f"task.parquet='{parquet}'"]
                      + ([f"embodiment={os.environ['EMB']}"] if os.environ.get('EMB') else []))
    env_config = instantiate_typed(cfg.env, RLEnvConfig)
    with wp.ScopedDevice(os.environ.get('DEV', 'cpu')):
        st = setup_scene(parquet=parquet, control_fps=env_config.sim.fps, motion_speed=1.0,
                         embodiment=instantiate_typed(cfg.embodiment, Embodiment),
                         collision=instantiate_typed(cfg.collision, CollisionPolicy), world_count=1, include_support=True,
                         decompose_objects=True)
    m = st.scene.model; out = {'sim': {k: str(v) for k, v in dataclasses.asdict(env_config.sim).items()} if dataclasses.is_dataclass(env_config.sim) else str(env_config.sim)}
    jl = list(getattr(m, 'joint_label', None) or getattr(m, 'joint_key', [])); bl = list(getattr(m, 'body_label', None) or getattr(m, 'body_key', []))
    ds = m.joint_qd_start.numpy(); g = lambda n: getattr(m, n).numpy() if hasattr(m, n) and getattr(m, n) is not None else None  # noqa: E731
    ke, kd, eff, lo, hi, arm, fr = (g(n) for n in ('joint_target_ke', 'joint_target_kd', 'joint_effort_limit', 'joint_limit_lower',
                                                   'joint_limit_upper', 'joint_armature', 'joint_friction'))
    joints = []
    for i, l in enumerate(jl):
        if 'right' not in l:
            continue
        d0, d1 = int(ds[i]), int(ds[i + 1]) if i + 1 < len(ds) else len(ke)
        for d in range(d0, d1):
            joints.append(dict(joint=l, dof=d, kp=float(ke[d]), kd=float(kd[d]), effort=float(eff[d]), lo=round(float(lo[d]), 3),
                               hi=round(float(hi[d]), 3), armature=float(arm[d]), friction=float(fr[d])))
    out['right_hand_dofs'] = joints
    mass, inert = g('body_mass'), g('body_inertia')
    out['bodies'] = [dict(body=l, mass=round(float(mass[i]), 4), inertia_diag=[float(x) for x in np.diag(inert[i])])
                     for i, l in enumerate(bl) if 'right' in l or 'track3_' in l]
    sb = g('shape_body'); shape_attrs = [n for n in dir(m) if n.startswith('shape_material') or n in ('shape_thickness', 'shape_contact_margin', 'shape_gap')]
    vals = {n: g(n) for n in shape_attrs}; seen = {}
    for s in range(len(sb)):
        b = int(sb[s]); name = bl[b] if b >= 0 else 'static'
        kind = 'object' if 'track3_' in name else 'right_hand' if 'right' in name else 'left_hand' if 'left' in name else name
        row = {n: (np.round(v[s], 4).tolist() if v is not None and len(v) > s else None) for n, v in vals.items()}
        seen.setdefault(kind, row)
    out['shape_material_first_per_kind'] = seen
    out['gravity'] = np.asarray(g('gravity')).tolist() if g('gravity') is not None else None
    print(json.dumps(out, indent=1)[:12000])
    if len(sys.argv) > 2:
        json.dump(out, open(sys.argv[2], 'w'), indent=1)


if __name__ == '__main__':
    main()
