"""PREREG gate (docs/analysis/ptrack-20261102/PREREG.md): variant vs control, per episode, after scoring.
Usage: python -I gate.py SCORES_DIR VARIANT [EPS...]   reads SCORES_DIR/{Cr,VARIANT}/ep<e>.json and ep<e>_pf.npz."""
import sys, json, numpy as np
S, V = sys.argv[1:3]
EPS = [int(x) for x in sys.argv[3:]] or [0, 2, 11, 12, 13, 18, 21, 22, 23, 24, 26, 27, 31, 39, 40, 41, 42, 43, 44, 45]
def load(t, e):
    try: return json.load(open(f'{S}/{t}/ep{e}.json'))['perception']
    except FileNotFoundError: return None
def gt3(t, e):
    try: return int((np.load(f'{S}/{t}/ep{e}_pf.npz')['perception_pos_cm'] > 3).sum())
    except FileNotFoundError: return None
rows, miss = [], []
for e in EPS:
    c, v = load('Cr', e), load(V, e)
    if c is None: miss.append(e); continue
    crashed = v is None
    v = v or c
    rows.append(dict(ep=e, C=c['AUC'], V=v['AUC'], dAUC=round(v['AUC'] - c['AUC'], 4), crashed=crashed,
                     dMPPE=round(v['MPPE_cm'] - c['MPPE_cm'], 3), dRPE=round(v['RPE_cm'] - c['RPE_cm'], 3),
                     gt3C=gt3('Cr', e), gt3V=gt3(V, e) if not crashed else gt3('Cr', e), objC=c['per_obj_AUC'], objV=v['per_obj_AUC']))
d = np.array([r['dAUC'] for r in rows])
res = dict(variant=V, n=len(rows), missing_control=miss, crashed=[r['ep'] for r in rows if r['crashed']],
           mean_dAUC=round(float(d.mean()), 5), min_dAUC=round(float(d.min()), 4),
           better=int((d > 0.0005).sum()), worse=int((d < -0.0005).sum()),
           mean_dMPPE=round(float(np.mean([r['dMPPE'] for r in rows])), 4), mean_dRPE=round(float(np.mean([r['dRPE'] for r in rows])), 4),
           gt3C=sum(r['gt3C'] for r in rows), gt3V=sum(r['gt3V'] for r in rows),
           ep23=[r for r in rows if r['ep'] == 23][0]['dAUC'] if any(r['ep'] == 23 for r in rows) else None)
res['gate'] = dict(mean=res['mean_dAUC'] >= 0.005, min=res['min_dAUC'] >= -0.01, mppe=res['mean_dMPPE'] <= 0)
res['pass'] = all(res['gate'].values()) and not miss and len(rows) == 20
res['rows'] = rows
print(json.dumps({k: v for k, v in res.items() if k != 'rows'}, indent=1))
for r in rows: print(r['ep'], r['C'], r['V'], r['dAUC'], r['dMPPE'], r['dRPE'], r['gt3C'], r['gt3V'], 'CRASH' if r['crashed'] else '')
json.dump(res, open(f'{S}/gate_{V}_vs_Cr.json', 'w'), indent=1)
