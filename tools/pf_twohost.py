"""Two-host confirmation verdict (3 Nov 2026; swap-rule amendment in docs/research/work/pack9b-20261031/PREREG.md).
Inputs: tools/pf_verdict.py eval jsons of the SAME candidate from two different hosts (the training box and a CONF_FROM
box). SWAP iff both are PASS and both clear the inclusion bar; the packed rollout is draw 1 of the FIRST (training-box) set.
Usage: pf_twohost.py --first V1.json --second V2.json --out OUT.json"""
import argparse, json
ap = argparse.ArgumentParser(); ap.add_argument('--first', required=True); ap.add_argument('--second', required=True); ap.add_argument('--out', required=True)
a = ap.parse_args(); V = [json.load(open(a.first)), json.load(open(a.second))]
def mean(v): return v.get('sides', {}).get('conf', {}).get('P', {}).get('sim_vs_ref', {}).get('mean')
ok = all(v.get('label') == 'PASS' and v.get('inclusion', {}).get('include') for v in V)
out = dict(rule='pack9b PREREG two-host amendment', label='SWAP' if ok else 'NO-SWAP',
           hosts=[dict(file=f, label=v.get('label'), include=v.get('inclusion', {}).get('include'), gain=v.get('inclusion', {}).get('gain'),
                       conf_mean=mean(v), clauses={k: c.get('holds') for k, c in v.get('clauses', {}).get('P', {}).items() if isinstance(c, dict)})
                  for f, v in zip((a.first, a.second), V)])
json.dump(out, open(a.out, 'w'), indent=1); print(json.dumps(out))
