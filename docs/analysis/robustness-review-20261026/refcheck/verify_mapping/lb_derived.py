"""Re-derive the mapping check's leaderboard / loss-budget numbers with my own arithmetic (no import of calibrate.py
or loss_budget.py; the ACC table and object lists are copied from loss_budget.py, which is the model under test).
Inputs [doc]: Kaggle AUC 0.78893 (pack 3) and 0.81056 (pack 4), results/submissions/*/summary.txt.
Noise input: sd(T|S) per draw from my_fits.json (my own rollout scores)."""
import json, os, re
import numpy as np

REPO = '/home/user/v2d-track3'; HERE = os.path.dirname(os.path.abspath(__file__))
rd = lambda pk: {int(k): v for k, v in json.loads(re.search(r'\{.*\}', open(f'{REPO}/results/submissions/{pk}/summary.txt').read()).group(0)).items()}
s3, s4 = rd('20261025-track3c'), rd('20261026-track3d')
LB3, LB4 = 0.78893, 0.81056
OBJS = {1: ['pot', 'lid'], 3: ['pot', 'spoon'], 5: ['pot', 'spoon'], 6: ['pot', 'spoon'], 8: ['beige', 'pot'],
        10: ['blue', 'beige'], 14: ['blue', 'rack'], 15: ['rack', 'spoon'], 16: ['rack', 'spoon'],
        19: ['sweeper', 'pan'], 20: ['blue', 'pitcher'], 25: ['board', 'board'], 28: ['rack', 'pot'],
        30: ['sweeper', 'rack'], 32: ['blue', 'spoon'], 33: ['blue', 'spoon'], 35: ['spoon'], 36: ['spoon'],
        37: ['spoon'], 38: ['pan']}
ACC = dict(pot=0.97, lid=0.965, blue=0.95, beige=0.93, rack=0.95, sweeper=0.96, pan=0.95, pitcher=0.66, board=0.82)
d = {e: s4[e] - s3[e] for e in s3 if abs(s4[e] - s3[e]) > 1e-9}
sdS = sum(d.values()); dLB = LB4 - LB3
out = dict(changed={e: round(v, 4) for e, v in d.items()}, sum_dS=round(sdS, 4), sum_dS_over_20=round(sdS / 20, 5),
           dLB=round(dLB, 5), transfer=round(dLB / (sdS / 20), 4), transfer_vs_0979=round(dLB / (0.979 * sdS / 20), 4))
mf = json.load(open(os.path.join(HERE, 'my_fits.json')))
sd = mf['rollout_noise']['policy S>=0.8']['sd_T_given_S']
sig_dLB = np.sqrt(2 * len(d)) * sd / 20
out['noise'] = dict(sd_T_given_S=sd, sigma_dLB=round(float(sig_dLB), 5), sigma_transfer=round(float(sig_dLB / (sdS / 20)), 4))
acc_e = lambda e, spoon: np.mean([dict(ACC, spoon=spoon)[o] for o in OBJS[e]])


def model(svr, spoon):
    return sum(svr[e] * acc_e(e, spoon) for e in OBJS) / 20


def solve(target, svr):
    lo, hi = 0.0, 1.5
    for _ in range(80):
        m = (lo + hi) / 2
        lo, hi = (m, hi) if model(svr, m) < target else (lo, m)
    return (lo + hi) / 2


sp = {f'a={a}': round(solve(LB4 / a, s4), 4) for a in (1.0, 1.015, 1.025, 1.027)}
out['implied_spoon_acc_pack4'] = sp
out['implied_spoon_acc_pack3'] = {f'a={a}': round(solve(LB3 / a, s3), 4) for a in (1.0, 1.015, 1.027)}
for spoon in (0.80, sp['a=1.0']):
    pred = sum(v * acc_e(e, spoon) for e, v in d.items())
    others = sum(v * acc_e(e, spoon) for e, v in d.items() if e != 33)
    t33 = (dLB * 20 - others) / d[33]
    out[f'model_spoon_{spoon:.3f}'] = dict(pred_transfer=round(pred / sdS, 4), acc33=round(acc_e(33, spoon), 4),
                                           implied_t33=round(t33, 4), sigma_t33=round(float(np.sqrt(2 * len(d)) * sd / d[33]), 4))
    out[f'model_spoon_{spoon:.3f}']['z_measured_vs_pred'] = round((pred / sdS - out['transfer']) / out['noise']['sigma_transfer'], 2)
mean4 = np.mean(list(s4.values()))
out['pack4_mean_S'] = round(float(mean4), 4)
out['eval_specific_loss_pack4'] = {f'k={k}': round(float(k * mean4 - LB4), 4) for k in (0.969, 0.972, 0.976, 0.979, 0.982, 0.985)}
for nm, sl in (('vs_0.94', 0.94), ('vs_0.97', 0.97), ('vs_0.88', 0.882)):
    out[f'z_{nm}'] = round((sl - out['transfer']) / out['noise']['sigma_transfer'], 2)
json.dump(out, open(os.path.join(HERE, 'lb_derived.json'), 'w'), indent=1)
print(json.dumps(out, indent=1))
