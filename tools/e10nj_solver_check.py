"""Eval-10 njmax diagnostic (2026-11-01; ops/jobs/ev10_nj.sh, PREREG docs/research/work/eval10-njmax-20261101/): which
contact budget does the OFFICIAL evaluator give a checkpoint? Runs FlashCHORD's own evaluation code path on each
checkpoint, exactly as flash_chord.evaluation.harness.evaluate_checkpoint does up to the environment (the kit's
evaluate_policy.py calls it): read_checkpoint_metadata -> checkpoint_config -> apply_evaluation_composition(world_count=1,
reset_mode='explicit') -> instantiate_typed(cfg.env, RLEnvConfig); with --solver also setup_scene(...) + RLEnv(...) on one
world (warp device --device, default cpu as determined-wright's contact_budget/njmax_cfg_test.py) and reads the built
SolverMuJoCo data: njmax, naconmax, nv, and the bytes of every warp array of the MuJoCo-Warp Data (one world).
Run with the FlashCHORD venv from the flash_chord checkout the evaluator uses (cwd = that checkout, PYTHONPATH = its src).
Output JSON {"checkpoints": {NAME: {stored_sim, env_config_sim, solver|null, error?}}}. Exit 0 always (the job reads the
JSON; a failed solver build is reported, not fatal).
Usage: python e10nj_solver_check.py --out OUT.json [--solver] [--device cpu] NAME=CHECKPOINT ...
"""
import argparse, copy, dataclasses, json, os, sys, time, traceback


def array_bytes(obj, seen=None):
    """total capacity (bytes) of the warp arrays reachable from a MuJoCo-Warp Data dataclass"""
    import warp as wp
    seen = set() if seen is None else seen
    if id(obj) in seen:
        return 0
    seen.add(id(obj))
    if isinstance(obj, wp.array):
        return int(getattr(obj, 'capacity', 0) or 0)
    if dataclasses.is_dataclass(obj):
        return sum(array_bytes(getattr(obj, f.name), seen) for f in dataclasses.fields(obj))
    return 0


def one(path, solver, device):
    from omegaconf import OmegaConf
    from flash_chord.configuration import instantiate_typed
    from flash_chord.envs.rl import RLEnvConfig
    from flash_chord.evaluation import harness
    from flash_chord.training.checkpoint import read_checkpoint_metadata
    from flash_chord.training.checkpoint_metadata import checkpoint_config
    r = dict(path=os.path.abspath(path))
    metadata = read_checkpoint_metadata(path)
    saved = checkpoint_config(metadata)
    r['stored_sim'] = dict(sim=[saved['sim']['njmax'], saved['sim']['nconmax']], env_sim=[saved['env']['sim']['njmax'], saved['env']['sim']['nconmax']])
    config = copy.deepcopy(saved)
    harness.apply_evaluation_composition(config, world_count=1, reset_mode='explicit')
    if hasattr(harness, '_resolve_parquet'):
        config['task']['parquet'] = harness._resolve_parquet(config, None)
    cfg = OmegaConf.create(config)
    env_config = instantiate_typed(cfg.env, RLEnvConfig)
    r['env_config_sim'] = [int(env_config.sim.njmax), int(env_config.sim.nconmax)]
    r['solver'] = None
    if solver:
        try:
            r['solver'] = build_solver(cfg, env_config, device)
        except Exception as e:
            r['solver_error'] = f'{type(e).__name__}: {str(e)[:300]}'; r['solver_trace'] = traceback.format_exc()[-1500:]
    return r


def build_solver(cfg, env_config, device):
    """setup_scene + RLEnv as harness.evaluate_checkpoint builds them (one world); the built SolverMuJoCo data"""
    import warp as wp
    from flash_chord.configuration import instantiate_typed
    from flash_chord.embodiments.base import Embodiment
    from flash_chord.envs.rl import RLEnv
    from flash_chord.scene.collision import CollisionPolicy
    from flash_chord.scene.setup import setup_scene
    t0 = time.time()
    embodiment = instantiate_typed(cfg.embodiment, Embodiment)
    collision = instantiate_typed(cfg.collision, CollisionPolicy)
    with wp.ScopedDevice(device):
        setup = setup_scene(
            parquet=cfg.task.parquet, control_fps=env_config.sim.fps, motion_speed=cfg.task.motion_speed,
            embodiment=embodiment, collision=collision, world_count=cfg.scene.world_count,
            include_support=cfg.scene.support, decompose_objects=cfg.scene.decompose_objects,
            object_scale_min=cfg.scene.get('object_scale_min', 1.0), object_scale_max=cfg.scene.get('object_scale_max', 1.0),
            object_scale_seed=cfg.scene.get('object_scale_seed', 0), contact_friction=cfg.scene.get('contact_friction', 1.0),
            object_free_joint_damping=cfg.scene.get('object_free_joint_damping', 0.0),
            source_frame_playback=bool(cfg.task.get('source_frame_playback', False)),
            motion_start_frame=int(cfg.task.get('motion_start_frame', 0)), motion_end_frame=int(cfg.task.get('motion_end_frame', -1)))
        env = RLEnv(setup.scene, setup.reference, config=env_config)
        md = env.solver.mjw_data; mm = env.solver.mj_model
        return dict(njmax=int(getattr(md, 'njmax', -1)), naconmax=int(getattr(md, 'naconmax', -1)),
                    njmax_nnz=int(getattr(md, 'njmax_nnz', -1)) if hasattr(md, 'njmax_nnz') else None,
                    nworld=int(getattr(md, 'nworld', -1)), nv=int(mm.nv), ngeom=int(mm.ngeom), nbody=int(mm.nbody),
                    data_bytes_one_world=array_bytes(md), device=str(device), seconds=round(time.time() - t0, 1))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--out', required=True); ap.add_argument('--solver', action='store_true'); ap.add_argument('--device', default='cpu')
    ap.add_argument('checkpoints', nargs='+', help='NAME=PATH')
    a = ap.parse_args()
    try:
        import warp as wp
        wp.config.log_level = wp.LOG_WARNING if hasattr(wp, 'LOG_WARNING') else wp.config.log_level
    except Exception:
        pass
    out = dict(cwd=os.getcwd(), python=sys.executable, solver=a.solver, device=a.device, checkpoints={})
    for spec in a.checkpoints:
        name, p = spec.split('=', 1)
        try:
            out['checkpoints'][name] = one(p, a.solver, a.device)
        except Exception as e:
            out['checkpoints'][name] = dict(path=p, error=f'{type(e).__name__}: {str(e)[:300]}', trace=traceback.format_exc()[-1500:])
        json.dump(out, open(a.out, 'w'), indent=1)
        c = out['checkpoints'][name]
        print(f"{name}: stored {c.get('stored_sim')} -> evaluator RLEnvConfig.sim {c.get('env_config_sim')}"
              + (f"; solver {c['solver']}" if c.get('solver') else '') + (f"; ERROR {c['error']}" if c.get('error') else ''), flush=True)


if __name__ == '__main__':
    main()
