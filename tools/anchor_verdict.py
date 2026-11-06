"""Verdict of the spoon-anchor re-evaluation (2 Nov 2026; docs/research/work/pf-anchor-20261102/PREREG.md, written before
any draw). Input: a tools/dr_score.py json with refs P (the board policy's own reference) and R (P with the spoon's
rest-averaged anchor orientation, tools/anchor_rest.py) and sets conf (the SAME board checkpoint, NCONF fresh official
draws on R, own R), packed (the board policy's control draws on P, own P), old (the board's row of the episode, own P).
SWAP iff
  a  mean sim_vs_ref(conf vs R) >= mean sim_vs_ref(packed vs P) - 0.01
  b  share of conf draws with RPE > 5 cm (vs R) <= that of packed (vs P)
  s  draw 1 sim_vs_ref (vs R) >= old (vs P) - 0.05
and every conf draw is scored, own-reference checked and carries the board checkpoint (checkpoint unchanged).
Usage: anchor_verdict.py --score S.json --ep N --checkpoint SHA256 --out V.json
"""
import argparse, json
import numpy as np

ap = argparse.ArgumentParser(); ap.add_argument('--score', required=True); ap.add_argument('--ep', type=int, required=True)
ap.add_argument('--checkpoint', required=True); ap.add_argument('--out', required=True); ap.add_argument('--nconf', type=int, default=10)
a = ap.parse_args(); S = json.load(open(a.score)); TOL = 1e-9; bad = []


def rows(name, X):
    out = []
    for r in S['sets'].get(name, {}).get('rollouts', []):
        if not r.get('scored'): bad.append(f'{name} r{r.get("draw")} not scored'); continue
        if not r.get('own_ref_check', {}).get('ok'): bad.append(f'{name} r{r["draw"]} own-reference check'); continue
        if name in ('conf', 'packed', 'old') and r.get('checkpoint_sha256') and r['checkpoint_sha256'] != a.checkpoint:
            bad.append(f'{name} r{r["draw"]} checkpoint {r["checkpoint_sha256"][:12]}'); continue
        out.append(dict(draw=r['draw'], svr=r['vs'][X]['sim_vs_ref'], rpe=r['vs'][X]['RPE'],
                        svr_P=r['vs'].get('P', {}).get('sim_vs_ref'), svr_R=r['vs'].get('R', {}).get('sim_vs_ref')))
    return sorted(out, key=lambda x: x['draw'])


N, K, O = rows('conf', 'R'), rows('packed', 'P'), rows('old', 'P')
summ = lambda v: dict(n=len(v), mean=round(float(np.mean(v)), 4), min=round(float(np.min(v)), 4), max=round(float(np.max(v)), 4)) if len(v) else dict(n=0)
out = dict(ep=a.ep, rule='docs/research/work/pf-anchor-20261102/PREREG.md', checkpoint=a.checkpoint,
           conf_vs_R=summ([x['svr'] for x in N]), conf_vs_P=summ([x['svr_P'] for x in N if x['svr_P'] is not None]),
           packed_vs_P=summ([x['svr'] for x in K]), old_vs_P=summ([x['svr'] for x in O]), draws_conf=N)
if bad: out.update(label='INVALID', why=bad)
elif len(N) < a.nconf or len(K) < 10 or len(O) != 1: out.update(label='INCOMPLETE', why=f'n conf {len(N)}, packed {len(K)}, old {len(O)}')
else:
    mN, mK = np.mean([x['svr'] for x in N]), np.mean([x['svr'] for x in K])
    fN, fK = np.mean([x['rpe'] > 5 for x in N]), np.mean([x['rpe'] > 5 for x in K])
    C = dict(a=dict(conf=round(mN, 4), packed=round(mK, 4), holds=bool(mN >= mK - 0.01 - TOL)),
             b=dict(conf=round(fN, 3), packed=round(fK, 3), holds=bool(fN <= fK + TOL)),
             s=dict(conf_draw1=N[0]['svr'], old=O[0]['svr'], holds=bool(N[0]['svr'] >= O[0]['svr'] - 0.05 - TOL)))
    out.update(clauses=C, label='SWAP' if all(c['holds'] for c in C.values()) else 'NO-SWAP')
json.dump(out, open(a.out, 'w'), indent=1)
print(out['label'], json.dumps({k: out[k] for k in ('clauses', 'why', 'conf_vs_R', 'conf_vs_P', 'packed_vs_P', 'old_vs_P') if k in out}))
