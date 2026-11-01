"""tools/e10v_verify.rule2 (local copy) == tools/mass_eval_verify.rule2 on 20,000 random seed tables, incl. exact 0.005
gaps, thin seeds and ties (2026-10-31). Usage: python -I rule2_equiv.py REPO OUT.json"""
import json, random, sys
sys.path.insert(0, f'{sys.argv[1]}/tools')
import e10v_verify as E, mass_eval_verify as MV   # noqa: E402
rng = random.Random(7); n = diff = 0; kinds = {}
for i in range(20000):
    st = {}
    for s in ('42', '43'):
        k = rng.choice(['ok', 'ok', 'ok', 'thin', 'tie', 'gap'])
        m = round(rng.uniform(0.4, 1.0), 4)
        st[s] = dict(n=rng.choice([10, 10, 9, 8]) if k != 'thin' else rng.choice([0, 5, 7]), mean=m, sd=round(rng.uniform(0, 0.3), 4))
    if rng.random() < 0.3:
        st['43']['mean'] = round(st['42']['mean'] + rng.choice([0.005, -0.005, 0.0, 0.0049, 0.0051]), 4)
    if rng.random() < 0.1:
        st['43']['sd'] = st['42']['sd']
    a, b = E.rule2(st, ['42', '43']), MV.rule2(st, ['42', '43']); n += 1; diff += a != b
    kinds[str(a)] = kinds.get(str(a), 0) + 1
json.dump(dict(cases=n, differences=diff, choices=kinds), open(sys.argv[2], 'w'), indent=1)
print(f'rule2: {n} random cases, {diff} differences; choices {kinds}'); sys.exit(1 if diff else 0)
