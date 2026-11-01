"""compare.py SCRATCH ARM [ARM...]: per-episode deltas vs runs/before and the pre-registered gate
(mean dAUC >= +0.003, min >= -0.010, mean dMPPE <= 0, mean dRPE <= 0). Scorer output only."""
import json, sys, numpy as np
S = sys.argv[1]
EPS = [0, 2, 11, 12, 13, 18, 21, 22, 23, 24, 26, 27, 31, 39, 40, 41, 42, 43, 44, 45]
L = lambda t, e: json.load(open(f'{S}/runs/{t}/ep{e}.json'))['perception']
out = {}
for arm in sys.argv[2:]:
    d = {k: [] for k in ('AUC', 'MPPE_cm', 'RPE_cm', 'SP_SR', 'MP_SR')}
    per = {}
    for e in EPS:
        b, a = L('before', e), L(arm, e)
        for k in d:
            d[k].append(a[k] - b[k])
        per[e] = dict(AUC=round(a['AUC'] - b['AUC'], 4), base=b['AUC'], new=a['AUC'],
                      obj={o: round(a['per_obj_AUC'][o] - b['per_obj_AUC'][o], 4) for o in a['per_obj_AUC']})
    m = {k: round(float(np.mean(v)), 5) for k, v in d.items()}
    dA = np.array(d['AUC'])
    g = dict(mean_ok=bool(m['AUC'] >= 0.003), min_ok=bool(dA.min() >= -0.010),
             mppe_ok=bool(m['MPPE_cm'] <= 0), rpe_ok=bool(m['RPE_cm'] <= 0))
    g['PASS'] = all(g.values())
    out[arm] = dict(mean=m, better=int((dA > 1e-4).sum()), worse=int((dA < -1e-4).sum()), min=round(float(dA.min()), 4),
                    min_ep=EPS[int(dA.argmin())], gate=g, per_ep=per)
    print(f'== {arm}: mean dAUC {m["AUC"]:+.5f}  better/worse {out[arm]["better"]}/{out[arm]["worse"]}  min {dA.min():+.4f} '
          f'(ep{EPS[int(dA.argmin())]})  dMPPE {m["MPPE_cm"]:+.4f}  dRPE {m["RPE_cm"]:+.4f}  dSP {m["SP_SR"]:+.3f}  {g}')
    print('   ' + ' '.join(f'{e}:{per[e]["AUC"]:+.4f}' for e in EPS if abs(per[e]['AUC']) > 1e-4))
json.dump(out, open(f'{S}/compare_{"_".join(sys.argv[2:])}.json', 'w'), indent=1)
