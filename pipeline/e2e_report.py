"""Side-by-side table of end-to-end runs: every /content/results/<variant>/ep<N>-s<seed>/score_ep<N>.json (written by
score_sim.py after the official evaluator). Columns: sim vs mocap (what Track 3 scores), the reference vs mocap (upper
bound from perception + retargeting), sim vs reference (the policy's tracking), and the "nothing moves" floor.
Usage: python e2e_report.py [results_root]
"""
import glob, json, os, sys

root = sys.argv[1] if len(sys.argv) > 1 else '/content/results'
rows = []
for f in sorted(glob.glob(f'{root}/*/ep*-s*/score_ep*.json')):
    if 'floorbug' in f or 'sanity' in f:
        continue
    j = json.load(open(f)); var = f.split('/')[-3]; run = f.split('/')[-2]
    g = lambda k, m='AUC': (j.get(k) or {}).get(m)
    rows.append((var, run, g('sim_vs_mocap'), g('sim_vs_mocap', 'SP_SR'), g('sim_vs_mocap', 'MP_SR'),
                 g('sim_vs_mocap', 'MPPE_cm'), g('reference_vs_mocap'), g('sim_vs_reference'), g('static_floor'),
                 (j.get('sim_vs_mocap') or {}).get('per_obj')))
print(f"{'variant':10s} {'run':10s} {'AUC':>6s} {'SP':>5s} {'MP':>5s} {'MPPE':>6s} | {'ref':>6s} {'trk':>6s} {'floor':>6s}  per-object")
for r in rows:
    f = lambda x, d=3: '   n/a' if x is None else f'{x:6.{d}f}'
    print(f"{r[0]:10s} {r[1]:10s} {f(r[2])} {f(r[3], 2)} {f(r[4], 2)} {f(r[5], 1)} | {f(r[6])} {f(r[7])} {f(r[8])}  {r[9]}")
