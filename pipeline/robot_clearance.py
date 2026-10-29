"""Robot-geometry clearance for a FlashCHORD reference, anchored at clean frames (2026-10-21).

Evidence: resetting the simulator to a reference frame popped an object by > 3 deg or 0.5 cm in ONE physics step at 49 of
55 sampled frames of ep24 and 52 of 71 of ep18: at almost every contact frame the retargeted robot hand sits inside an
object, the table or the other hand. MANO joint-centre clearance (mkref --depenetrate) does not transfer through IK to
the larger Sharpa geometry. Training hides it (FlashCHORD resets with the object assist on for 20 steps); the official
evaluation starts at frame 0 without it.

Per round:
  1. for every frame t: reset the training env (1 world) to t without settling, take one step, read MuJoCo's contacts;
     for each robot hand, the smallest wrist translation that clears its contacts with objects / table / the other hand
     by MARGIN (projection over the contact normals; hand-hand contacts split half-half);
  2. "settle the differences": per hand, shifts d_t minimise sum_t |d_t - need_t|^2 + LAM sum_t |d_t+1 - d_t|^2, where
     clean frames (need 0) act as anchors pulling to zero and dirty frames pull to their need, so neighbouring anchors
     and corrections meet smoothly; the result is added to the robot wrist positions and every robot frame position;
  3. repeat until no frame needs more than TOL (or ROUNDS).
Translation only; rotations and finger joints are unchanged, contact targets on the objects are kept.
Usage (FlashCHORD python, FC = the flash_chord dir; run from FC so its relative asset paths resolve):
  python robot_clearance.py IN_PROCESSED_PARQUET OUT_PARQUET [--rounds 3] [--margin 0.001] [--lam 4]
OUT_PARQUET must sit in a reference tree whose reconstructed_stage/ holds the support USDA (FlashCHORD resolves it
relative to the parquet).
"""
import argparse, json, os, sys
import numpy as np, pyarrow as pa, pyarrow.parquet as pq


def needs_per_frame(parquet, fc, margin):
    """{side: (T, 3)} wrist translations that clear each frame's hand contacts, and per-frame worst penetration (m)."""
    import warp as wp
    from hydra import compose, initialize_config_dir
    from flash_chord.configuration import instantiate_typed
    from flash_chord.embodiments.base import Embodiment
    from flash_chord.envs.rl import RLEnv, RLEnvConfig
    from flash_chord.scene.collision import CollisionPolicy
    from flash_chord.scene.setup import setup_scene
    with initialize_config_dir(version_base='1.3', config_dir=f'{fc}/src/flash_chord/configs'):
        cfg = compose(config_name='train_flash_sac', overrides=['experiment=sharpa_flash_sac', f"task.parquet='{parquet}'"])
    env_config = instantiate_typed(cfg.env, RLEnvConfig)
    with wp.ScopedDevice('cpu'):
        st = setup_scene(parquet=parquet, control_fps=env_config.sim.fps, motion_speed=1.0,
                         embodiment=instantiate_typed(cfg.embodiment, Embodiment),
                         collision=instantiate_typed(cfg.collision, CollisionPolicy), world_count=1, include_support=True,
                         decompose_objects=True)
        env = RLEnv(st.scene, st.reference, config=env_config); m = st.scene.model
        labels = list(getattr(m, 'body_label', None) or getattr(m, 'body_key', []))
        g2s = env.solver.mjc_geom_to_newton_shape.numpy(); sb = m.shape_body.numpy()

        def owner(g):
            sh = g2s[0, g] if g2s.ndim == 2 else g2s[g]
            if sh < 0 or sb[sh] < 0:
                return 'env'                                       # table / ground
            lab = labels[sb[sh]].split('/')[-1]
            return 'left' if lab.startswith('left_') else 'right' if lab.startswith('right_') else 'env'

        T = int(st.reference.num_frames) if hasattr(st.reference, 'num_frames') else None
        if T is None:
            T = len(np.array(pq.read_table(parquet).column('robot_left_wrist_position')[0].as_py()).reshape(-1, 3))
        need = {s: np.zeros((T, 3)) for s in ('left', 'right')}; worst = np.zeros(T)
        for t in range(T):
            env.reset(frame_id=t); env.step(None)
            d = env.solver.mjw_data; c = d.contact
            n = int((d.nacon if hasattr(d, 'nacon') else d.ncon).numpy()[0])
            if n == 0:
                continue
            geom = c.geom.numpy()[:n]; dist = c.dist.numpy()[:n]; nrm = c.frame.numpy()[:n, 0]
            cons = {'left': [], 'right': []}
            for (g0, g1), dd, nn in zip(geom, dist, nrm):
                if dd >= 0:
                    continue
                a, b = owner(g0), owner(g1)
                if a == b:
                    continue                                       # self-contact or object-object/table: not ours
                req = -dd + margin
                if a in cons and b in cons:                        # hand-hand: half each
                    cons[a].append((-nn, req / 2)); cons[b].append((nn, req / 2))
                elif a in cons:
                    cons[a].append((-nn, req))                     # geom0 moves against the normal (0 -> 1)
                elif b in cons:
                    cons[b].append((nn, req))
                worst[t] = max(worst[t], -dd)
            for s in cons:
                v = np.zeros(3)
                for _ in range(8):                                 # cyclic projection onto the half-spaces
                    for u, r in cons[s]:
                        u = u / max(np.linalg.norm(u), 1e-9); gap = r - u @ v
                        if gap > 0:
                            v = v + gap * u
                need[s][t] = v
    return need, worst


def settle(need, lam):
    """Anchored temporal smoothing: argmin |d - need|^2 + lam |D d|^2 (tridiagonal solve per axis)."""
    from scipy.linalg import solve_banded
    T = len(need); ab = np.zeros((3, T))
    ab[0, 1:] = -lam; ab[2, :-1] = -lam
    ab[1] = 1 + 2 * lam; ab[1, 0] = ab[1, -1] = 1 + lam
    return np.stack([solve_banded((1, 1), ab, need[:, k]) for k in range(3)], 1)


def apply_shift(table, side, d):
    for col in (f'robot_{side}_wrist_position', f'robot_{side}_frames'):
        i = table.column_names.index(col); a = np.array(table.column(col)[0].as_py(), float)
        if col.endswith('frames'):
            a[..., :3] += d[:, None, :]
        else:
            a = a.reshape(-1, 3) + d
        table = table.set_column(i, col, pa.array([a.tolist()], type=table.schema.field(col).type))
    return table


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('inp'); p.add_argument('out')
    p.add_argument('--rounds', type=int, default=3); p.add_argument('--margin', type=float, default=0.001)
    p.add_argument('--lam', type=float, default=4.0); p.add_argument('--tol', type=float, default=0.002)
    a = p.parse_args()
    fc = os.environ.get('FC', os.getcwd())
    src = os.path.abspath(a.inp); log = []
    total = None
    for r in range(a.rounds + 1):
        need, worst = needs_per_frame(src, fc, a.margin)
        nmax = {s: float(np.linalg.norm(need[s], axis=1).max()) for s in need}
        log.append(dict(round=r, dirty_frames=int((worst > a.tol).sum()), worst_pen_mm=round(float(worst.max() * 1000), 1),
                        p95_pen_mm=round(float(np.percentile(worst, 95) * 1000), 1),
                        max_need_cm={s: round(v * 100, 2) for s, v in nmax.items()}))
        print(json.dumps(log[-1]), flush=True)
        if r == a.rounds or max(nmax.values()) <= a.tol:
            break
        t = pq.read_table(src)
        for s in need:
            d = settle(need[s], a.lam)
            total = {**(total or {}), s: (total or {}).get(s, 0) + d}
            t = apply_shift(t, s, d)
        os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
        pq.write_table(t, a.out)
        src = os.path.abspath(a.out)
    if total:
        for s in total:
            log.append({f'{s}_total_shift_cm': dict(max=round(float(np.linalg.norm(total[s], axis=1).max() * 100), 2),
                                                    median=round(float(np.median(np.linalg.norm(total[s], axis=1)) * 100), 2))})
        print(json.dumps(log[-2:]))
    json.dump(log, open(os.path.splitext(a.out)[0] + '_clearance.json', 'w'), indent=1)


if __name__ == '__main__':
    main()
