import json, sys
from kaggle.api import kaggle_api_extended as m
m.KaggleApi._introspect_token = lambda self, token: 'proxy-auth'
api = m.KaggleApi(); api.authenticate()
ids = {57925185, 57925189, 57925196, 57925202, 57925211, 57925216}
out = {}
for slug in ['v2d-challenge-track3-auc', 'v2d-challenge-track3-sp-sr', 'v2d-challenge-track3-mp-sr', 'v2d-challenge-track3-rpe',
             'v2d-challenge-track3-mppe', 'v2d-challenge-track3-cd-o']:
    subs = api.competition_submissions(slug, page_size=100)
    rows = []
    for s in subs:
        d = {k: getattr(s, k, None) for k in ('ref', 'description', 'date', 'public_score', 'private_score', 'status', 'file_name')}
        for k in dir(s):
            if 'select' in k.lower() and not k.startswith('_'):
                d[k] = getattr(s, k)
        rows.append({k: str(v) for k, v in d.items()})
    out[slug] = rows
    mine = [r for r in rows if int(r['ref']) in ids]
    sel = [r for r in rows if any(v == 'True' for k, v in r.items() if 'select' in k.lower())]
    print(slug, len(rows), 'submissions; 13h:', [(r['ref'], r['public_score'], r['status']) for r in mine],
          '| selected:', [(r['ref'], r['description'][:30]) for r in sel])
json.dump(out, open(sys.argv[1], 'w'), indent=1)
