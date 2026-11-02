"""Pre-registered gate (PREREG.md): variant vs control on the scored public episodes.
Usage: python -I gate.py SCRATCH CONTROL CONTROL2 VARIANT [EPS...]  (reads SCRATCH/runs/<tag>/ep<e>.json, *_pf.npz)"""
import sys, json, numpy as np
S, C, C2, V = sys.argv[1:5]
EPS = [int(x) for x in sys.argv[5:]] or [0, 2, 11, 12, 13, 18, 21, 22, 23, 24, 26, 27, 31, 39, 40, 41, 42, 43, 44, 45]
def load(t, e):
    try: return json.load(open(f'{S}/runs/{t}/ep{e}.json'))['perception']
    except FileNotFoundError: return None
def gt3(t, e):
    try: return int((np.load(f'{S}/runs/{t}/ep{e}_pf.npz')['perception_pos_cm'] > 3).sum())
    except FileNotFoundError: return None
rows, miss = [], []
for e in EPS:
    c, c2, v = load(C, e), load(C2, e), load(V, e)
    if c is None or v is None: miss.append(e); continue
    rows.append(dict(ep=e, C=c['AUC'], V=v['AUC'], dAUC=round(v['AUC'] - c['AUC'], 4),
                     dC2=None if c2 is None else round(c2['AUC'] - c['AUC'], 4),
                     dMPPE=round(v['MPPE_cm'] - c['MPPE_cm'], 3), dRPE=round(v['RPE_cm'] - c['RPE_cm'], 3),
                     gt3C=gt3(C, e), gt3V=gt3(V, e), objC=c['per_obj_AUC'], objV=v['per_obj_AUC']))
d = np.array([r['dAUC'] for r in rows]); n2 = [r['dC2'] for r in rows if r['dC2'] is not None]
noise = abs(float(np.mean(n2))) if n2 else float('nan')
res = dict(control=C, control2=C2, variant=V, n=len(rows), missing=miss,
           mean_dAUC=round(float(d.mean()), 5), noise_mean_C2_minus_C=round(float(np.mean(n2)), 5) if n2 else None,
           noise_abs_per_episode_mean=round(float(np.mean(np.abs(n2))), 5) if n2 else None,
           min_dAUC=round(float(d.min()), 4), better=int((d > 0.0005).sum()), worse=int((d < -0.0005).sum()),
           mean_dMPPE=round(float(np.mean([r['dMPPE'] for r in rows])), 4), mean_dRPE=round(float(np.mean([r['dRPE'] for r in rows])), 4),
           gt3C=sum(r['gt3C'] for r in rows), gt3V=sum(r['gt3V'] for r in rows))
res['gate'] = dict(mean=res['mean_dAUC'] >= 0.005 and (not n2 or res['mean_dAUC'] >= 2 * noise),
                   min=res['min_dAUC'] >= -0.02, mppe_rpe=res['mean_dMPPE'] <= 0 and res['mean_dRPE'] <= 0,
                   drift=res['gt3V'] <= res['gt3C'])
res['pass'] = all(res['gate'].values()) and not miss
res['rows'] = rows
print(json.dumps({k: v for k, v in res.items() if k != 'rows'}, indent=1))
for r in rows: print(r['ep'], r['C'], r['V'], r['dAUC'], r['dC2'], r['dMPPE'], r['dRPE'], r['gt3C'], r['gt3V'])
json.dump(res, open(f'{S}/gate_{V}_vs_{C}.json', 'w'), indent=1)
