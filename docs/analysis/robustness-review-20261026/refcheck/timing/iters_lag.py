"""refcheck/timing, test of H1 (where the half-frame lag comes from): onset-crossing lag vs mocap for the 25 Oct
perception precision sweep (runs/20261025-sweep-a894083), variants base (FoundationPose TRACK_ITERS 2), t4
(TRACK_ITERS 4) and t8 (REG_ITERS 10, TRACK_ITERS 8), same code / templates (library_v2) / inputs.
If the lag is tracker under-convergence (each track_one starts from the previous pose and closes only part of the
motion), more refiner iterations shrink it; if it is a clock offset between video frame i and mocap row i, it stays.
Body point: the surface centroid of the library_v2 mesh (timing only; a few mm from the kit anchor).
Usage: python -I iters_lag.py OUT.json
"""
import json, os, sys
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from tload import *                                                        # noqa: E402,F401,F403
import timing as TM                                                        # noqa: E402
from v2dlb.object_mesh import _surface_moments                             # noqa: E402

SW = 'runs/20261025-sweep-a894083/results/sweep/{}/ep{}/poses_world_vo.npz'
KEYS = ('on_p1_f', 'on_p2_f', 'on_r_f', 'off_p1_f', 'off_p2_f', 'off_r_f')


def main():
    out = dict(per_object={}, pooled={})
    pool = {}
    for ep, e in sorted(canon().items()):
        if ep == 23:                                                       # frame-0 identity swap
            continue
        names, gt = load_gt(ep)
        for s, n in enumerate(names):
            trg = TM.Track(gt[n], host_anchor(n, s), TM.sym_axis_body(ep, s, n, 'mocap'))
            evg, _, _, _ = TM.events(trg)
            if evg['on_move'] is None:
                continue
            v, f = mesh_vf(our_mesh_path('library_v2', n)); c, _ = _surface_moments(v, f)
            row = {}
            for var in ('base', 't4', 't8'):
                p = f'{STORE}/{SW.format(var, ep)}'
                if not os.path.exists(p):
                    continue
                M = load_npz(p)[n]
                axis = TM.sym_axis_body(ep, s, n, 'library_v2') if SYM.get(n) == 'axis' else None
                evo, _, _, _ = TM.events(TM.Track(M, c, axis))
                lg = {k: round(evo[k] - evg[k], 3) for k in KEYS if evo.get(k) is not None and evg.get(k) is not None}
                row[var] = lg
                for k, x in lg.items():
                    if abs(x) <= 3:
                        pool.setdefault(var, {}).setdefault(k, []).append(x)
            out['per_object'][f'{ep}/{n}'] = row
            print(ep, n, {v: {k: x for k, x in r.items() if k.startswith('on')} for v, r in row.items()}, flush=True)
    for var, d in pool.items():
        out['pooled'][var] = {k: dict(n=len(x), median=round(float(np.median(x)), 3), mean=round(float(np.mean(x)), 3),
                                      iqr=[round(float(q), 3) for q in np.percentile(x, [25, 75])]) for k, x in d.items()}
        on = [y for k in ('on_p1_f', 'on_p2_f', 'on_r_f') for y in d.get(k, [])]
        out['pooled'][var]['onsets_all'] = dict(n=len(on), median=round(float(np.median(on)), 3))
    # paired difference vs base (same object and key)
    for var in ('t4', 't8'):
        dd = [r[var][k] - r['base'][k] for r in out['per_object'].values() if var in r and 'base' in r
              for k in ('on_p1_f', 'on_p2_f', 'on_r_f') if k in r[var] and k in r['base'] and abs(r[var][k]) <= 3 and abs(r['base'][k]) <= 3]
        out['pooled'][f'{var}_minus_base_onsets'] = dict(n=len(dd), median=round(float(np.median(dd)), 3), mean=round(float(np.mean(dd)), 3))
    print(json.dumps(out['pooled'], indent=1))
    json.dump(out, open(sys.argv[1], 'w'), indent=1)


if __name__ == '__main__':
    main()
