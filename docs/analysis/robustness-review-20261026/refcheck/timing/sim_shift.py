"""refcheck/timing: would advancing the reference by the measured lag help the SIMULATED object? CPU proxy.

For every stored rollout r1-r5 of the 10 canonical results dirs, score the simulated object path vs mocap (in-process
kit registered AUC with the reference's mesh library, as score_registered.py does for a results dir) as stored and
advanced by L frames: sim'(t) = sim(t + L). If the policy keeps its timing relative to the reference, a reference
advanced by L moves the simulated object by about L as well, so the difference estimates the effect on the policy score.
Hypothesis, not a measurement of a retrained policy (the policy could also absorb or amplify the shift).
Usage: python -I sim_shift.py COST.json OUT.json
"""
import json, os, sys
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from tload import *                                                        # noqa: E402,F401,F403
import cost as CO                                                          # noqa: E402


def main():
    L = json.load(open(sys.argv[1]))['pooled_onset_lag_frames']; out = dict(L=L, episodes={})
    for ep, e in sorted(canon().items()):
        fl = rollout_files(e)
        if not fl:
            continue
        names, gt = load_gt(ep)
        H = [S.host_geometry(n, s) for s, n in enumerate(names)]
        REG = [S.registration(ep, s, n, our_mesh_path(REF_LIB[ep], n)) for s, n in enumerate(names)]
        rows = {}
        for f in fl:
            sim = load_rollout(f, names)
            b7 = {n: S.to7(sim[n]) for n in names}
            _, _, a0 = CO.perframe(ep, names, b7, gt, H, REG)
            _, _, a1 = CO.perframe(ep, names, {n: S.shift_path(b7[n], L) for n in names}, gt, H, REG)
            rows[os.path.basename(os.path.dirname(f))] = dict(base=round(a0, 4), shifted=round(a1, 4))
        d = [r['shifted'] - r['base'] for r in rows.values()]
        out['episodes'][ep] = dict(rollouts=rows, mean_base=round(float(np.mean([r['base'] for r in rows.values()])), 4),
                                   mean_delta=round(float(np.mean(d)), 4), improved=int(sum(x > 0 for x in d)), n=len(d))
        print(ep, out['episodes'][ep], flush=True)
        json.dump(out, open(sys.argv[2], 'w'), indent=1)
    eps = out['episodes'].values()
    out['summary'] = dict(mean_delta_over_episodes=round(float(np.mean([v['mean_delta'] for v in eps])), 4),
                          rollouts_improved=int(sum(v['improved'] for v in eps)), rollouts=int(sum(v['n'] for v in eps)))
    print(out['summary'])
    json.dump(out, open(sys.argv[2], 'w'), indent=1)


if __name__ == '__main__':
    main()
