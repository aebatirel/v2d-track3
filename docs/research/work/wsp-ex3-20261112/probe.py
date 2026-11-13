"""Robustness probe on the UNPERTURBED task (start frame 0, delay 0): an actor plus a seeded jitter of the 58 output
biases (N(0, sd^2)), one rollout per seed, in parallel processes. Each run counts against the 25-rollout budget.
This measures robustness of a fixed edit; it selects nothing.

Usage: python -I probe.py WORKSHOP_DIR ACTOR_NPZ OUT_DIR LABEL SD SEED [SEED ...]
"""
import json, os, sys
from concurrent.futures import ProcessPoolExecutor
import multiprocessing as mp
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))


def one(args):
    workshop, actor, out_dir, label, sd, seed = args
    sys.path.insert(0, HERE)
    import runner
    with np.load(actor) as d:
        w = {k: d[k] for k in d.files}
    w['params/mean_bias'] = (w['params/mean_bias'] + np.random.default_rng(seed).normal(0, sd, 58)).astype(np.float32)
    path = os.path.join(out_dir, f'{label}_seed{seed}_actor.npz'); np.savez(path, **w)
    r = runner.run_one(workshop, path, 0, 0, 0, record=True)
    tr = r.pop('trace')
    np.savez_compressed(os.path.join(out_dir, f'{label}_seed{seed}.npz'), **tr, meta=json.dumps(r))
    e = tr['err']; r.update(label=label, seed=seed, max_obj=float(e[:, 0].max()), max_ang=float(e[:, 1].max()),
                            final_wrist=float(e[-1, 2]), final_ang=float(e[-1, 1]))
    return r


if __name__ == '__main__':
    workshop, actor, out_dir, label, sd = sys.argv[1:6]
    seeds = [int(s) for s in sys.argv[6:]]
    with ProcessPoolExecutor(max_workers=4, mp_context=mp.get_context('spawn')) as ex:
        for r in ex.map(one, [(workshop, actor, out_dir, label, float(sd), s) for s in seeds]):
            print(json.dumps(r), flush=True)
