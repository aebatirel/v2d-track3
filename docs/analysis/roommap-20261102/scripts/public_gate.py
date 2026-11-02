"""PREREG G2 on the public leave-out scores (after inference). Usage: python -I public_gate.py WORK OUT_JSON"""
import sys, json, os, numpy as np
W, OUT = sys.argv[1:3]
EPS = [0, 2, 11, 12, 13, 18, 21, 22, 23, 24, 26, 27, 31, 39, 40, 41, 42, 43, 44, 45]
rows, miss = [], []
for e in EPS:
    d = f'{W}/compose/public/ep{e}'
    try:
        c = json.load(open(f'{d}/score_C.json'))['perception']; v = json.load(open(f'{d}/score_map.json'))['perception']
        dr = json.load(open(f'{d}/drift.json'))
    except FileNotFoundError:
        miss.append(e); continue
    rows.append(dict(ep=e, C=c['AUC'], V=v['AUC'], dAUC=round(v['AUC'] - c['AUC'], 4),
                     dMPPE=round(v['MPPE_cm'] - c['MPPE_cm'], 3), dRPE=round(v['RPE_cm'] - c['RPE_cm'], 3),
                     bound=round(dr.get('camera_term_bound', float('nan')), 4), obj_p95_mm=round(dr['max_obj_p95_mm'], 1),
                     cam_mm_max=round(dr['camera']['pos_mm_max'], 1), reloc_ok=dr['reloc_ok'], gate_rej=dr['gate_rejected'],
                     inl_min=dr['inliers_min']))
d = np.array([r['dAUC'] for r in rows]); b = float(np.mean([r['bound'] for r in rows]))
res = dict(n=len(rows), missing=miss, mean_dAUC=round(float(d.mean()), 5), min_dAUC=round(float(d.min()), 4),
           better=int((d > 0.0005).sum()), worse=int((d < -0.0005).sum()),
           mean_dMPPE=round(float(np.mean([r['dMPPE'] for r in rows])), 4),
           mean_dRPE=round(float(np.mean([r['dRPE'] for r in rows])), 4), public_bound_mean=round(b, 4))
need = 0.005 if b >= 0.01 else max(0.0, 0.3 * b)
res['gate'] = dict(no_ep_below=res['min_dAUC'] >= -0.01, mppe=res['mean_dMPPE'] <= 0, mean=res['mean_dAUC'] >= need,
                   mean_needed=round(need, 5))
res['G0_all'] = all(r['reloc_ok'] >= 0.99 and r['gate_rej'] < 0.02 for r in rows)
res['pass_G2'] = res['gate']['no_ep_below'] and res['gate']['mppe'] and res['gate']['mean']
res['rows'] = rows
json.dump(res, open(OUT, 'w'), indent=1)
print(json.dumps({k: v for k, v in res.items() if k != 'rows'}, indent=1))
for r in rows: print(r)
