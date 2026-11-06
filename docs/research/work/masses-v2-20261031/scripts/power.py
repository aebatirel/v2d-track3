"""Masses v2: operating characteristic of the owner's rule, stated BEFORE any v2 result (31 Oct 2026). [E] model:
cell mean(ep, arm, seed) = mu_ep + delta_ep * arm + s + r, s ~ N(0, sigma_s) per training (each arm x seed trains on its own),
r ~ N(0, sigma_r / sqrt(10)) (10 rollouts). delta(ep) = mean over 2 seeds of (cell1 - cell0); rule (PREREG section 4):
ADOPT iff round(mean delta, 4) >= 0.03 and >= 3 of 4 round(delta, 4) > 0 and no round(delta, 4) <= -0.05.
Noise per episode (sigma_r = rollout sd, sigma_s = between-training sd of a cell mean), from measured numbers:
  ep24: sigma_r 0.139 (ev3 n5 sd 0.1246 pop -> sample), sigma_s 0.10 (ep24 std-learner seed pair r5ks/r5ks43: 0.099)
  ep31: sigma_r 0.136 (ev30rp n5 0.1218 pop -> sample; orcB n10 0.044), sigma_s 0.06 (assumed; between the classes)
  ep11: sigma_r 0.005 (twin11v3 0.0043), sigma_s 0.02 (assumed; a stuck-at-floor policy)
  ep13: sigma_r 0.001 (orcB 0.0008), sigma_s 0.01 (assumed)
  bounding scenarios with the FIRST CHECK's per-cell sd: all-ep2-like (sigma_r 0.33 = its cells' 0.29-0.37, sigma_s 0.08)
  and all-ep12-like (sigma_r 0.02 = its cells' 0.017-0.024, sigma_s 0.01).
Writes power.json. Usage: python3 power.py OUT.json"""
import json, sys
import numpy as np

rng = np.random.default_rng(20261031)
N = 40000
SC = {'candidates': dict(ep24=(0.139, 0.10), ep11=(0.005, 0.02), ep13=(0.001, 0.01), ep31=(0.136, 0.06)),
      'all_ep2_like (first check sd)': {e: (0.33, 0.08) for e in ('a', 'b', 'c', 'd')},
      'all_ep12_like (first check sd)': {e: (0.02, 0.01) for e in ('a', 'b', 'c', 'd')}}
TRUE = {'0 everywhere': [0, 0, 0, 0], '+0.03 everywhere': [0.03] * 4, '+0.05 everywhere': [0.05] * 4,
        '+0.09 everywhere (Round 3 mean, scans)': [0.09] * 4, '-0.03 everywhere': [-0.03] * 4,
        '+0.12 on the 2 noisy, 0 on the 2 stuck (mean +0.06)': [0.12, 0, 0, 0.12]}


def sim(sd, dtrue):
    keys = list(sd)
    d = np.zeros((N, 4))
    for i, k in enumerate(keys):
        sr, ss = sd[k]
        cell = lambda: rng.normal(0, ss, (N, 2)) + rng.normal(0, sr / np.sqrt(10), (N, 2))
        d[:, i] = (dtrue[i] + cell() - cell()).mean(1)
    d4 = np.round(d, 4); m4 = np.round(d.mean(1), 4)
    c1, c2, c3 = m4 >= 0.03, (d4 > 0).sum(1) >= 3, ~(d4 <= -0.05).any(1)
    return dict(p_adopt=round(float((c1 & c2 & c3).mean()), 3), p_mean_clause=round(float(c1.mean()), 3),
                p_3of4=round(float(c2.mean()), 3), p_no_drop=round(float(c3.mean()), 3),
                se_delta_ep=[round(float(np.sqrt(ss ** 2 + sr ** 2 / 10)), 4) for sr, ss in sd.values()],
                se_mean_delta=round(float(np.sqrt(sum(ss ** 2 + sr ** 2 / 10 for sr, ss in sd.values())) / 4), 4))


out = {s: {t: sim(sd, dt) for t, dt in TRUE.items()} for s, sd in SC.items()}
json.dump(dict(note=__doc__, n_sim=N, results=out), open(sys.argv[1], 'w'), indent=1)
for s, v in out.items():
    print(s, 'SE(delta ep)', v['0 everywhere']['se_delta_ep'], 'SE(mean delta)', v['0 everywhere']['se_mean_delta'])
    for t, r in v.items():
        print(f'   {t:55s} P(ADOPT) {r["p_adopt"]:.3f}  (mean {r["p_mean_clause"]:.3f}, 3of4 {r["p_3of4"]:.3f}, no drop {r["p_no_drop"]:.3f})')
