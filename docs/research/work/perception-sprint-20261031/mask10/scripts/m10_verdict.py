"""Verdict of the pre-registered rule (README §0) from the oracle scores: the full run (m10_scores.json) with ep11
replaced by a re-score (after the two code fixes recorded in README §2: V3's float32 jitter, V2's cup orientation).
No ground truth is read here (only score files). Usage: python -I m10_verdict.py FULL_JSON EP11_JSON OUT_JSON"""
import json, sys
import numpy as np
full, e11, out = sys.argv[1:4]
F = json.load(open(full))['episodes']
R = json.load(open(e11))['episodes']['11']          # ep11 re-score of the fixed variants (M10_VARS) replaces them
for arm in ('Po', 'refineP'):
    for v in R['arms'][arm]['delta']:
        if v == 'input':
            continue
        F['11']['arms'][arm][v] = R['arms'][arm][v]
        F['11']['arms'][arm]['delta'][v] = R['arms'][arm]['delta'][v]
        F['11']['arms'][arm]['delta_per_obj'][v] = R['arms'][arm]['delta_per_obj'][v]
    assert R['arms'][arm]['S2']['lib']['AUC'] == F['11']['arms'][arm]['S2']['lib']['AUC']
F['11']['rescored_variants'] = [v for v in R['arms']['Po']['delta'] if v != 'input']
EPS = sorted(F, key=int)
V = ['V1', 'V1h', 'V2', 'V1d', 'V3', 'V3p']
ver = {}
for v in V:
    ver[v] = {}
    for arm in ('Po', 'refineP'):
        d11 = F['11']['arms'][arm]['delta'][v]
        oth = {e: F[e]['arms'][arm]['delta'].get(v, F[e]['arms'][arm]['delta']['V1']) for e in EPS if e != '11'}
        worst = max(max(abs(d['lib']), abs(d['star'])) for d in oth.values())
        ver[v][arm] = dict(ep11_dlib=d11['lib'], ep11_dstar=d11['star'], others_max_abs_delta=round(worst, 4),
                           mean_dlib_20=round(float(np.mean([d11['lib']] + [d['lib'] for d in oth.values()])), 5),
                           passed=bool(d11['lib'] >= 0.05 and worst <= 0.002))
    ver[v]['passed_both_arms'] = all(ver[v][a]['passed'] for a in ('Po', 'refineP'))
    print(v, json.dumps(ver[v]))
json.dump(dict(rule='ep11 dlib >= +0.05; others |dlib|, |d*| <= 0.002; both arms', verdict=ver,
               ep11=F['11']), open(out, 'w'), indent=1)
print('wrote', out)
