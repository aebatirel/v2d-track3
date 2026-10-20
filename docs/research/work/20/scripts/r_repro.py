"""DIG 20 Stage C re-run: reproduce the stored C3 numbers from the stored feature npz files (no writes to out/c).
Compares with out/c/eval2_MC_A120_T2_L10_m3.json. usage: r_repro.py"""
import sys, os, json, numpy as np
sys.path.insert(0, os.path.dirname(__file__))
from c_lib import *
from c_eval import pairing_n, window_bias, gt
import c_eval2 as E

st = {r['ep']: r for r in json.load(open(f'{OUT}/eval2_MC_A120_T2_L10_m3.json'))}
R = []; mism = 0
for ep in PUB:
    g = gt(ep); ca, c, m = E.decide(ep, 'MC', 120, 2.0, 10)
    n = pairing_n(f'p{ep}', min(ca, g['n'] - 1)); cbc = ca - n; end = cbc - 3
    wb = window_bias(ep, min(end, g['n'] - 1))
    s = st[ep]
    same = (s['ca'] == ca and s['cbc'] == cbc and abs(s['det']['dR'] - wb['dR']) < 1e-9)
    mism += not same
    R.append(dict(ep=ep, er=cbc - g['pert'], eb=cbc - g['pert_r'], dR=wb['dR'], dt=wb['dt'], n=wb['n']))
    print(f'p{ep:2d} C a{c} M a{m} -> bc {cbc} end {end} | pert {g["pert"]}/{g["pert_r"]} | dR {wb["dR"]:.3f} dt {wb["dt"]:.2f} | stored same: {same}')
er = np.array([r['er'] for r in R]); eb = np.array([r['eb'] for r in R]); dR = np.array([r['dR'] for r in R]); dt = np.array([r['dt'] for r in R])
print(f'raw err median {np.median(er):+.1f} p10/p90 {np.percentile(er, 10):+.1f}/{np.percentile(er, 90):+.1f}; robust median {np.median(eb):+.1f}; '
      f'dt med/p90/max {np.median(dt):.2f}/{np.percentile(dt, 90):.2f}/{dt.max():.2f}; dR {np.median(dR):.2f}/{np.percentile(dR, 90):.2f}/{dR.max():.2f}; '
      f'n med {np.median([r["n"] for r in R]):.0f}; mismatches vs stored json: {mism}')
