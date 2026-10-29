"""Compare my independent scores (verify_chain/scores/epN.json, myscore.py) with refcheck/chain/results.json.
Prints the 10-episode chain table from MY numbers, the episode means, the per-object mkref / contact-retarget deltas,
and the largest absolute difference to the chain's numbers. Usage: python -I compare.py OUT.json
"""
import json, sys, os
import numpy as np

H = os.path.dirname(os.path.abspath(__file__))
CH = json.load(open(f'{H}/../chain/results.json'))['chain']
EPS = [2, 11, 12, 18, 21, 24, 26, 27, 31, 39]
LINKS = [('perc_lib', 'lib|perc'), ('e2s_lib', 'lib|e2s'), ('ref_lib', 'lib|res_ref'), ('sim_lib', 'lib|res_sim'),
         ('perc_scan', 'scan|perc'), ('e2s_scan', 'scan|e2s'), ('ref_scan', 'scan|res_ref'), ('sim_scan', 'scan|res_sim')]
rows, diffs, objrows = [], [], []
for ep in EPS:
    M = json.load(open(f'{H}/scores/ep{ep}.json'))['scores']
    c = CH[str(ep)]
    r = {'ep': ep}
    for ck, mk in LINKS:
        if mk not in M:
            continue
        r[ck] = M[mk]['scene']
        if ck in c:
            diffs.append(abs(M[mk]['scene'] - c[ck]['AUC']))
            for n, v in M[mk]['per_obj'].items():
                diffs.append(abs(v - c[ck]['obj'][n]))
        # proc parquet (my direct read) must equal the evaluator reference columns
    r['proc_eq_res_ref'] = all(abs(M[f'{m}|proc']['scene'] - M[f'{m}|res_ref']['scene']) < 1e-9 for m in ('lib', 'scan'))
    rows.append(r)
    for n in M['lib|perc']['per_obj']:
        objrows.append(dict(ep=ep, obj=n, d_mkref=M['lib|e2s']['per_obj'][n] - M['lib|perc']['per_obj'][n],
                            d_cr=M['lib|res_ref']['per_obj'][n] - M['lib|e2s']['per_obj'][n]))
mean = {k: round(float(np.mean([r[k] for r in rows])), 4) for k in rows[0] if k not in ('ep', 'proc_eq_res_ref')}
dm = np.array([o['d_mkref'] for o in objrows]); dc = np.array([o['d_cr'] for o in objrows])
changeable = [o for o in objrows if not (o['d_mkref'] == 0)]
out = dict(rows=rows, mean=mean, n_obj=len(objrows), max_abs_diff_vs_chain=round(float(max(diffs)), 5), n_compared=len(diffs),
           mkref=dict(mean=round(float(dm.mean()), 4), min=round(float(dm.min()), 4), max=round(float(dm.max()), 4),
                      n_exactly_zero=int((dm == 0).sum()),
                      mean_over_nonzero=round(float(dm[dm != 0].mean()), 4)),
           cr=dict(mean=round(float(dc.mean()), 4), min=round(float(dc.min()), 4), max=round(float(dc.max()), 4)),
           ref_minus_perc_lib={r['ep']: round(r['ref_lib'] - r['perc_lib'], 4) for r in rows},
           objects=objrows)
json.dump(out, open(sys.argv[1], 'w'), indent=1)
print('| ep | perc lib | e2s lib | ref lib | ref-perc | perc scan | ref scan | sim lib | proc==evaluator ref |')
for r in rows:
    print(f"| {r['ep']} | {r['perc_lib']:.4f} | {r['e2s_lib']:.4f} | {r['ref_lib']:.4f} | {r['ref_lib'] - r['perc_lib']:+.4f} | "
          f"{r['perc_scan']:.4f} | {r['ref_scan']:.4f} | {r['sim_lib']:.4f} | {r['proc_eq_res_ref']} |")
print('mean', mean)
print('max |mine - chain| over', len(diffs), 'scene+object AUCs:', out['max_abs_diff_vs_chain'])
print('mkref', out['mkref'], 'cr', out['cr'])
print('ref-perc', out['ref_minus_perc_lib'])
