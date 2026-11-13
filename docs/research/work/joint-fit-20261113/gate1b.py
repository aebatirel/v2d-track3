"""Stage-1b gate (PREREG.md), arm vs control C over the scored public episodes, plus the non-development subset.
Reads B/C/ep<N>/{score.json,pf.npz} and B/arms/<TAG>/ep<N>/{score.json,pf.npz,changed.npz}. Scoring output only.
Usage: python -I gate1b.py B TAG [DEV_EPS comma list, default 21,11,31]"""
import json, os, sys
import numpy as np
B, TAG = sys.argv[1:3]
DEV = [int(x) for x in (sys.argv[3] if len(sys.argv) > 3 else '21,11,31').split(',')]
EPS = [0, 2, 11, 12, 13, 18, 21, 22, 23, 24, 26, 27, 31, 39, 40, 41, 42, 43, 44, 45]
rows, miss = [], []
for e in EPS:
    cf, vf = f'{B}/C/ep{e}/score.json', f'{B}/arms/{TAG}/ep{e}/score.json'
    if not (os.path.exists(cf) and os.path.exists(vf)):
        miss.append(e); continue
    c, v = json.load(open(cf))['perception'], json.load(open(vf))['perception']
    r = dict(ep=e, dev=e in DEV, C=c['AUC'], V=v['AUC'], dAUC=round(v['AUC'] - c['AUC'], 4),
             dMPPE=round(v['MPPE_cm'] - c['MPPE_cm'], 3), dRPE=round(v['RPE_cm'] - c['RPE_cm'], 3),
             dSP=v['SP_SR'] - c['SP_SR'], dMP=v['MP_SR'] - c['MP_SR'])
    zc, zv = np.load(f'{B}/C/ep{e}/pf.npz'), np.load(f'{B}/arms/{TAG}/ep{e}/pf.npz')
    ch = np.load(f'{B}/arms/{TAG}/ep{e}/changed.npz')
    names = list(zc['names']); m = np.stack([ch[n] for n in names], 1)[:len(zc['perception_adds_cm'])]
    r['changed'] = int(m.sum())
    if m.any():
        r['restADD_C'] = round(float(zc['perception_adds_cm'][m].mean()), 3)
        r['restADD_V'] = round(float(zv['perception_adds_cm'][m].mean()), 3)
        r['restADD_lower'] = r['restADD_V'] < r['restADD_C']
    else:
        r['restADD_lower'] = False
    rows.append(r)


def summ(rs):
    if not rs:
        return {}
    d = np.array([r['dAUC'] for r in rs])
    s = dict(n=len(rs), mean_dAUC=round(float(d.mean()), 5), min_dAUC=round(float(d.min()), 4),
             better=int((d > 0.0005).sum()), worse=int((d < -0.0005).sum()),
             mean_dMPPE=round(float(np.mean([r['dMPPE'] for r in rs])), 4),
             mean_dRPE=round(float(np.mean([r['dRPE'] for r in rs])), 4),
             restADD_lower=int(sum(r['restADD_lower'] for r in rs)),
             dSP=round(float(np.sum([r['dSP'] for r in rs])), 3), dMP=round(float(np.sum([r['dMP'] for r in rs])), 3))
    s['gate'] = dict(mean=s['mean_dAUC'] >= 0.005, min=s['min_dAUC'] >= -0.01,
                     restADD=s['restADD_lower'] >= round(14 * len(rs) / 20), mppe_rpe=s['mean_dMPPE'] <= 0 and s['mean_dRPE'] <= 0)
    s['pass'] = all(s['gate'].values())
    return s


res = dict(arm=TAG, missing=miss, all20=summ(rows), nondev=summ([r for r in rows if not r['dev']]), rows=rows)
res['pass'] = res['all20'].get('pass', False) and not miss
print(json.dumps({k: v for k, v in res.items() if k != 'rows'}, indent=1))
for r in rows:
    print(r['ep'], 'dev' if r['dev'] else '   ', r['C'], r['V'], r['dAUC'], r['dMPPE'], r['dRPE'], r.get('restADD_C'), r.get('restADD_V'))
json.dump(res, open(f'{B}/gate1b_{TAG}.json', 'w'), indent=1)
