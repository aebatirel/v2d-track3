"""DIG 20 Stage C re-run: evaluate the frozen MC detector run on GT-FREE masks (out/c2/run_p*.npz) against public GT
(analysis only): onset error vs raw / robust first perturbation, late / empty windows, anchor bias of the window, and a
side-by-side with the stored GT-mask run (out/c/eval2_MC_A120_T2_L10_m3.json). p45 = fresh holdout (never used for
any Stage C choice). usage: r_eval.py -> out/c2/eval_gtfree.json"""
import sys, os, json, numpy as np
sys.path.insert(0, os.path.dirname(__file__))
import c_lib as L
from c_eval import window_bias, gt
OUT2 = f'{L.ROOT}/work/20/out/c2'
ST = {r['ep']: r for r in json.load(open(f'{L.OUT}/eval2_MC_A120_T2_L10_m3.json'))}
EPS = L.PUB + [45]
R = []
for ep in EPS:
    f = f'{OUT2}/run_p{ep}.npz'
    if not os.path.exists(f): continue
    d = json.loads(str(np.load(f)['dec'])); g = gt(ep)
    end = d['window_end_row']; wb = window_bias(ep, min(end, g['n'] - 1))
    mv = json.load(open(f'{OUT2}/pose0_p{ep}.json')).get('val', {})
    row = dict(ep=ep, name=g['name'], C_a=d['C_a'], M_a=d['M_a'], c_bc=d['c_bc'], end=end, pert=g['pert'], pert_r=g['pert_r'], on=g['on'],
               e_raw=d['c_bc'] - g['pert'], e_rob=d['c_bc'] - g['pert_r'], late_raw=end >= g['pert'], late_rob=end >= g['pert_r'],
               empty=end < 0, n=wb['n'], dt=wb['dt'], dR=wb['dR'], shift=wb['shift'], iou=mv.get('iou'))
    if ep in ST:
        s = ST[ep]; row.update(gtmask_c_bc=s['cbc'], gtmask_end=s['end'], gtmask_dR=s['det']['dR'], gtmask_dt=s['det']['dt'], gtmask_C=s['c'], gtmask_M=s['m'])
    R.append(row)
    print(f"p{ep:2d} {g['name'][:12]:12s} iou {row['iou'] if row['iou'] is not None else float('nan'):.2f} | C a{d['C_a']} M a{d['M_a']} -> bc {d['c_bc']:4d} end {end:4d} | "
          f"pert {g['pert']}/{g['pert_r']} on {g['on']} | err raw {row['e_raw']:+4d} rob {row['e_rob']:+4d}{' LATE' if row['late_rob'] else ''}{' EMPTY' if row['empty'] else ''} | "
          f"n {wb['n']:3d} dt {wb['dt']:.2f} dR {wb['dR']:.2f}"
          + (f" || GT-mask: C a{row['gtmask_C']} M a{row['gtmask_M']} bc {row['gtmask_c_bc']} end {row['gtmask_end']} dR {row['gtmask_dR']:.2f}" if ep in ST else ' || fresh holdout'))


def stats(rows, tag):
    if not rows: return {}
    er = np.array([r['e_raw'] for r in rows]); eb = np.array([r['e_rob'] for r in rows]); dR = np.array([r['dR'] for r in rows]); dt = np.array([r['dt'] for r in rows])
    s = dict(n=len(rows), raw_med=float(np.median(er)), raw_p10=float(np.percentile(er, 10)), raw_p90=float(np.percentile(er, 90)),
             rob_med=float(np.median(eb)), late_raw=int(sum(r['late_raw'] for r in rows)), late_rob=int(sum(r['late_rob'] for r in rows)),
             empty=int(sum(r['empty'] for r in rows)), win_med=float(np.median([r['n'] for r in rows])),
             dt_med=float(np.median(dt)), dt_p90=float(np.percentile(dt, 90)), dt_max=float(dt.max()),
             dR_med=float(np.median(dR)), dR_p90=float(np.percentile(dR, 90)), dR_max=float(dR.max()))
    print(f"== {tag}: n {s['n']} | onset err raw median {s['raw_med']:+.0f} p10/p90 {s['raw_p10']:+.0f}/{s['raw_p90']:+.0f}; robust median {s['rob_med']:+.0f} | "
          f"late raw/robust {s['late_raw']}/{s['late_rob']} empty {s['empty']} | window median {s['win_med']:.0f} | dt {s['dt_med']:.2f}/{s['dt_p90']:.2f}/{s['dt_max']:.2f} mm | "
          f"dR {s['dR_med']:.2f}/{s['dR_p90']:.2f}/{s['dR_max']:.2f} deg")
    return s


S = dict(all=stats(R, 'GT-free masks, all eps'), pub19=stats([r for r in R if r['ep'] in ST], 'GT-free masks, the 19 Stage C eps'),
         ok_id=stats([r for r in R if r['ep'] in ST and (r['iou'] or 0) > 0.3], 'GT-free, right-object picks (IoU > 0.3)'))
same = [r for r in R if r['ep'] in ST]
print('identical window end to the GT-mask run in', sum(r['end'] == r['gtmask_end'] for r in same), 'of', len(same),
      '; |diff| <= 2 rows in', sum(abs(r['end'] - r['gtmask_end']) <= 2 for r in same))
json.dump(dict(rows=R, stats=S), open(f'{OUT2}/eval_gtfree.json', 'w'), indent=1, default=float)
