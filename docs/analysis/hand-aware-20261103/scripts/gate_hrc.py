"""Gate evaluation for HRC (PREREG.md with addenda 1 and 2). Scoring and diagnostics only (reads mocap-derived held frames
and per-frame errors from the registered scorer).
Usage: gate_hrc.py WORK OUT_JSON EP...
  WORK/ho/{V,C,Cr}_ep<e>.json   10-seed registered scores (perception_seedmean)
  WORK/ho/V_ep<e>_pf.npz        V per-frame (seed 0);  WORK/diagC/Ct_ep<e>_pf.npz  C per-frame (seed 0)
  WORK/diagC/held_diag_C.json   mocap-held runs;  WORK/ho/V/ep<e>/hrc.json  correction logs"""
import sys, json, numpy as np
W, OUT = sys.argv[1], sys.argv[2]; EPS = [int(x) for x in sys.argv[3:]]
H = json.load(open(f'{W}/diagC/held_diag_C.json'))
TH = np.arange(1, 10); WT = np.r_[0.5, np.ones(7), 0.5] / 8
auc = lambda a: 1 - float(((a[:, None] >= TH) @ WT).mean())
sm = lambda t, e: json.load(open(f'{W}/ho/{t}_ep{e}.json'))['perception_seedmean']
rows, heldC, heldV, hauc = [], [], [], []
for e in EPS:
    c, v, r = sm('C', e), sm('V', e), sm('Cr', e)
    pc, pv = np.load(f'{W}/diagC/Ct_ep{e}_pf.npz'), np.load(f'{W}/ho/V_ep{e}_pf.npz')
    names = [str(x) for x in pc['names']]; ac, av = pc['perception_adds_cm'], pv['perception_adds_cm']
    lg = json.load(open(f'{W}/ho/V/ep{e}/hrc.json'))['objects']
    for s, n in enumerate(names):
        h = np.zeros(len(ac), bool)
        for x, y in H[f'{e}:{n}']['held_runs']: h[x:y] = True
        if h.any():
            heldC.append(ac[h, s]); heldV.append(av[h, s]); hauc.append((auc(ac[h, s]), auc(av[h, s])))
    rows.append(dict(ep=e, C=c['AUC'], V=v['AUC'], Cr=r['AUC'], dAUC=round(v['AUC'] - c['AUC'], 4), noise=round(r['AUC'] - c['AUC'], 4),
                     dMPPE=round(v['MPPE_cm'] - c['MPPE_cm'], 3), dRPE=round(v['RPE_cm'] - c['RPE_cm'], 3),
                     SP=(c['SP_SR'], v['SP_SR']), MP=(c['MP_SR'], v['MP_SR']),
                     gt3=(int((ac > 3).sum()), int((av > 3).sum())),
                     corrected={k: dict(frames=x.get('corrected'), spans=x.get('spans'), max_cm=x.get('max_shift_cm'),
                                        mean_cm=x.get('mean_abs_shift_cm')) for k, x in lg.items() if x.get('corrected')}))
d = np.array([x['dAUC'] for x in rows]); nz = np.array([x['noise'] for x in rows])
hc, hv = np.concatenate(heldC), np.concatenate(heldV); ha = np.array(hauc)
res = dict(n=len(rows), mean_dAUC=round(float(d.mean()), 5), min_dAUC=round(float(d.min()), 4),
           noise_abs_mean=round(float(np.abs(nz).mean()), 5), noise_mean=round(float(nz.mean()), 5),
           held_mean_ADD_C=round(float(hc.mean()), 3), held_mean_ADD_V=round(float(hv.mean()), 3),
           held_mean_ADD_rel=round(float(hv.mean() / hc.mean() - 1), 4),
           held_median_ADD_C=round(float(np.median(hc)), 3), held_median_ADD_V=round(float(np.median(hv)), 3),
           held_AUC_C=round(float(ha[:, 0].mean()), 4), held_AUC_V=round(float(ha[:, 1].mean()), 4),
           mean_dMPPE=round(float(np.mean([x['dMPPE'] for x in rows])), 4), mean_dRPE=round(float(np.mean([x['dRPE'] for x in rows])), 4))
res['gate'] = dict(g1=bool(res['held_mean_ADD_rel'] <= -0.10 or res['held_AUC_V'] - res['held_AUC_C'] >= 0.01),
                   g2=bool(res['mean_dAUC'] >= 0.005 and res['mean_dAUC'] >= 2 * res['noise_abs_mean']),
                   g3=bool(res['min_dAUC'] >= -0.01))
res['pass'] = all(res['gate'].values()); res['rows'] = rows
print(json.dumps({k: v for k, v in res.items() if k != 'rows'}, indent=1))
for x in rows: print(x['ep'], x['C'], x['V'], x['dAUC'], 'noise', x['noise'], 'SP', x['SP'], 'MP', x['MP'], '>3cm', x['gt3'], x['corrected'])
json.dump(res, open(OUT, 'w'), indent=1)
