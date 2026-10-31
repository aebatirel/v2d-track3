"""Apply the PREREG.md pass rule to a candidate json (cand.py output). Usage: python -I gate.py CAND_JSON K1 [K2 ...]"""
import json, sys
import numpy as np
R = json.load(open(sys.argv[1]))['episodes']; eps = sorted(R, key=int)
out = {}
for k in sys.argv[2:]:
    d = {q: np.array([R[e]['scores'][k][q] - R[e]['scores']['base'][q] for e in eps]) for q in ('AUC', 'MPPE', 'RPE')}
    no23 = [i for i, e in enumerate(eps) if e != '23']
    rule = dict(mean_dAUC=float(d['AUC'].mean()), mean_dRPE=float(d['RPE'].mean()), improved=int((d['AUC'] > 0).sum()),
                worst_dAUC=float(d['AUC'].min()), worst_ep=eps[int(d['AUC'].argmin())], mean_dMPPE=float(d['MPPE'].mean()))
    checks = [rule['mean_dAUC'] >= 0.005, rule['mean_dRPE'] <= -0.10, rule['improved'] >= 12, rule['worst_dAUC'] >= -0.02, rule['mean_dMPPE'] <= 0]
    rule['checks'] = dict(zip(['dAUC>=+0.005', 'dRPE<=-0.10', '>=12/20 improved', 'no ep dAUC<-0.02', 'dMPPE<=0'], map(bool, checks)))
    rule['verdict'] = 'PASS' if all(checks) else 'FAIL'
    rule['beside_without_ep23'] = {q: float(d[q][no23].mean()) for q in d}
    rule['worse'] = int((d['AUC'] < 0).sum())
    rule['per_episode'] = {e: {q: round(float(d[q][i]), 4) for q in d} for i, e in enumerate(eps)}
    out[k] = rule
    print(k, rule['verdict'], {q: round(v, 4) if isinstance(v, float) else v for q, v in rule.items() if q not in ('per_episode',)})
json.dump(out, open(sys.argv[1].replace('.json', '_gate.json'), 'w'), indent=1)
