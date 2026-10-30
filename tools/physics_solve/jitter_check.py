"""Robustness of a reference under tiny target noise (2026-10-30, physics solver). Zero-action replays in FlashCHORD are
chaotic: 1e-5-level changes can flip a grasp. This replays REF K times, each with independent Gaussian noise on the
wrist-position targets (SIG_POS m) and finger targets (SIG_FIN rad) of every frame (wrist rotation untouched; frame 0
untouched, as it is the reset pose). It reports sim_vs_ref per copy, using pipeline/qa.py's metric on OUR reference
(no ground truth). All K copies run as K worlds of one environment: worlds are independent in MuJoCo-Warp (checked:
world 0 is bit-identical to a 1-world replay whatever the other worlds do). Each copy gets its own targets through
FlashCHORD's residual action (raw input, EMA 0), so copy 0 (no noise) is the plain zero-action replay.
Usage (FlashCHORD python, from the flash_chord dir): EMB=sharpa_hands_mid [DEV=cuda] jitter_check.py REF.parquet [--k 9]
  [--sig_pos 0.0005 --sig_fin 0.005 --seed 0] [--out X.npz] [--json X.json]
KIT: the submission kit dir (default /content/kit/v2d_submission_kit, as pipeline/qa.py). Same seed and K on two
references of the same episode = the same noise draws (common random numbers), so their difference is less noisy.
"""
import argparse, os, sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import solve as S  # noqa: E402


def main():
    p = argparse.ArgumentParser(); p.add_argument('ref'); p.add_argument('--k', type=int, default=8)
    p.add_argument('--sig_pos', type=float, default=0.0005); p.add_argument('--sig_fin', type=float, default=0.005)
    p.add_argument('--seed', type=int, default=0); p.add_argument('--out', default=''); p.add_argument('--json', default='')
    p.add_argument('--device', default=os.environ.get('DEV', 'cpu'))
    a = p.parse_args()
    import time
    import warp as wp
    wp.config.log_level = wp.LOG_WARNING
    t0 = time.time()
    env, labels = S.build_env(os.path.abspath(a.ref), a.k, planner=True, device=a.device)
    with S.on(env):
        env.reset(frame_id=0)
    ref = S.Ref(a.ref); T, B = ref.T, len(ref.names); nb = len(labels) // a.k
    ob = [labels.index(f'track3_{n}/object') for n in ref.names]
    buf = env.action.buffers; lay = buf.layout; A = lay.action_dim; scale = buf.scale.numpy()[:A].astype(np.float64)
    rng = np.random.default_rng(a.seed); noise = np.zeros((a.k, T, A))
    for h in range(len(lay.sides)):
        s0 = lay.hand_action_starts[h]; nf = lay.finger_counts[h]
        noise[1:, :, s0:s0 + 3] = rng.normal(size=(a.k - 1, T, 3)) * a.sig_pos
        noise[1:, :, s0 + 6:s0 + 6 + nf] = rng.normal(size=(a.k - 1, T, nf)) * a.sig_fin
    noise[:, 0] = 0.0
    Q = [env.state_0.body_q.numpy().reshape(a.k, nb, 7)[:, ob].copy()]
    with S.on(env):
        for f in range(T - 1):
            env.step(wp.array((noise[:, f] / scale).astype(np.float32).reshape(-1), dtype=wp.float32, device=a.device))
            Q.append(env.state_0.body_q.numpy().reshape(a.k, nb, 7)[:, ob].copy())
    Q = np.array(Q, np.float64)                                                   # (T, K, B, 7)
    sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'pipeline'))
    import importlib, types
    try:
        import pandas  # noqa: F401
    except ImportError:                              # FlashCHORD's venv has no pandas; the kit functions used need numpy only
        pd_ = types.ModuleType('pandas'); api = types.ModuleType('pandas.api'); typ = types.ModuleType('pandas.api.types')
        pd_.api, api.types = api, typ; pd_.__getattr__ = lambda n: object
        sys.modules.update({'pandas': pd_, 'pandas.api': api, 'pandas.api.types': typ})
    kit = os.environ.get('KIT', '/content/kit/v2d_submission_kit'); sys.path.insert(0, kit); sys.path.insert(0, f'{kit}/metric_code/track_3'); AU = importlib.import_module('AUC')
    refa = np.concatenate([ref.OP, ref.OQ], 2)[:, None]
    r0 = np.random.default_rng(0); P_ = r0.normal(size=(500, 3)); P_ = 0.05 * P_ / np.linalg.norm(P_, axis=1, keepdims=True)
    V = np.repeat(P_[None], B, 0); sc = []
    for k in range(a.k):
        sim = Q[:, k][:, None]
        sc.append(float(AU._add_auc(AU._object_add(AU._warp_to_reference_start(sim, refa), refa, V))) if np.isfinite(sim).all() else 0.0)
    sc = np.array(sc)
    print(f'{os.path.basename(a.ref)}: copy 0 (no noise) {sc[0]:.4f}; jittered copies {np.round(sc[1:], 4).tolist()}; '
          f'jittered mean {sc[1:].mean():.4f} sd {sc[1:].std():.4f} min {sc[1:].min():.4f} max {sc[1:].max():.4f}', flush=True)
    if a.out:
        np.savez_compressed(a.out, scores=sc, q=Q.astype(np.float32), args=str(vars(a)))
    if a.json:
        import json
        j = sc[1:] if a.k > 1 else sc
        json.dump(dict(ref=os.path.abspath(a.ref), device=a.device, k=a.k, sig_pos=a.sig_pos, sig_fin=a.sig_fin, seed=a.seed,
                       nominal=round(float(sc[0]), 4), jittered=[round(float(x), 4) for x in j],
                       mean=round(float(j.mean()), 4), sd=round(float(j.std()), 4), min=round(float(j.min()), 4),
                       max=round(float(j.max()), 4), wall_s=round(time.time() - t0, 1)), open(a.json, 'w'), indent=1)


if __name__ == '__main__':
    main()
