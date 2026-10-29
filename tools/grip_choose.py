"""Choose a grip from tools/grip_portfolio.sh's re-scores (2026-10-25; rule pre-registered as P1 in docs/work-log.md):
the human copy stays unless a typed candidate's re-scored CVaR (worst 25 % of K fresh disturbed copies) beats the copy's
by >= MARGIN. Also reports, per candidate, the held object's rise at the lift frame in the exact copy (copy 0) and the
median over copies. No ground truth.  Usage: grip_choose.py OUT_DIR [--margin 0.05] [--lift_cm 10]"""
import argparse, json, os
import numpy as np
p = argparse.ArgumentParser(); p.add_argument('out'); p.add_argument('--margin', type=float, default=0.05)
p.add_argument('--lift_cm', type=float, default=10.0); a = p.parse_args()
res = {}
for c in sorted(os.listdir(a.out)):
    f = os.path.join(a.out, c, 'rescore.log')
    if os.path.isfile(f):
        lines = [l for l in open(f) if l.startswith('{"rescore"')]
        if lines:
            res[c] = json.loads(lines[-1])
rows = {c: dict(cvar=r['cvar'], mean=r['mean'], exact=r['exact'], rise_exact_cm=r['rise_cm_at_lift_frame'][0],
                rise_median_cm=float(np.median([x for x in r['rise_cm_at_lift_frame'] if x is not None]))) for c, r in res.items()}
copy = rows.get('copy'); best = max(((c, v) for c, v in rows.items() if c != 'copy'), key=lambda x: x[1]['cvar'], default=(None, None))
choice = 'copy'
if copy and best[0] and best[1]['cvar'] - copy['cvar'] >= a.margin:
    choice = best[0]
lifted = [c for c, v in rows.items() if v['rise_exact_cm'] is not None and v['rise_exact_cm'] >= a.lift_cm]
out = dict(rows=rows, best_typed=best[0], margin=a.margin, choice=choice,
           typed_beats_copy=bool(choice != 'copy'), lifted_by_lift_frame=lifted,
           P1_falsified=bool(choice == 'copy' or not lifted))
print(json.dumps(out, indent=1)); json.dump(out, open(os.path.join(a.out, 'choice.json'), 'w'), indent=1)
