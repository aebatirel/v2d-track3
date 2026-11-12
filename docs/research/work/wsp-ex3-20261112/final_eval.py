"""Pre-registered final evaluation (run once, after the last edit): for each arm, the unperturbed run plus 20 perturbed
runs (start frame {0, 4, ..., 36} x delay {0, 3} physics steps, via Simulation(delay_steps=d) and reset(frame=f)).
Success = reaches the last reference frame without a threshold failure (object > 0.10 m, > 0.5 rad, wrist > 0.15 m).

Usage: python -I final_eval.py WORKSHOP_DIR OUT_JSONL TRACE_DIR ARM=ACTOR_NPZ [ARM=ACTOR_NPZ ...]
Traces are saved for every run (compressed) for diagnosis after the fact.
"""
import json, os, sys
from concurrent.futures import ProcessPoolExecutor
import multiprocessing as mp
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
GRID = [(f, d) for d in (0, 3) for f in range(0, 37, 4)]


def one(args):
    workshop, arm, actor, kind, f, d, trace_dir = args
    sys.path.insert(0, HERE)
    import runner
    r = runner.run_one(workshop, actor, f, d, 0, record=True)
    tr = r.pop('trace')
    np.savez_compressed(os.path.join(trace_dir, f'{arm}_{kind}_f{f}_d{d}.npz'), **tr, meta=json.dumps(r))
    e = tr['err']
    r.update(arm=arm, kind=kind, max_obj=float(e[:, 0].max()), max_ang=float(e[:, 1].max()), max_wrist=float(e[:, 2].max()))
    return r


if __name__ == '__main__':
    workshop, out, trace_dir = sys.argv[1:4]
    arms = [a.split('=', 1) for a in sys.argv[4:]]
    jobs = []
    for arm, actor in arms:
        jobs.append((workshop, arm, actor, 'unperturbed', 0, 0, trace_dir))
        jobs += [(workshop, arm, actor, 'perturbed', f, d, trace_dir) for f, d in GRID]
    with ProcessPoolExecutor(max_workers=4, mp_context=mp.get_context('spawn')) as ex, open(out, 'a') as fh:
        for r in ex.map(one, jobs):
            fh.write(json.dumps(r) + '\n'); fh.flush()
            print(f"{r['arm']:16s} {r['kind']:11s} f={r['start_frame']:2d} d={r['delay']} "
                  f"{'OK  ' if r['success'] else 'FAIL'} {r['reason'][:80]}", flush=True)
