"""Spot-check (ORACLE scoring, public only, after inference): re-run each sprint experiment's own scorer on 2 episodes
and compare with its stored JSON. Usage: python -I spot.py {offset|heldpose|mask10} OUT_JSON"""
import json, os, sys
from concurrent.futures import ProcessPoolExecutor
D = '/home/user/v2d-track3/docs/research/work/perception-sprint-20261031'
which, out = sys.argv[1], sys.argv[2]
os.environ['SPLIT'] = 'public'
if which == 'offset':
    sys.path.insert(0, f'{D}/offset/scripts'); import off_score as M
    eps, stored = [12, 39], json.load(open(f'{D}/offset/scores/off_scores.json'))
    get = lambda r, ep, arm, v: r['arms'][arm][v]['d']['lib']
    s_get = lambda ep, arm, v: stored[str(ep)]['arms'][arm][v]['d']['lib']
    VARS = ['V1', 'V2', 'V3']
elif which == 'heldpose':
    sys.path.insert(0, f'{D}/heldpose/scripts'); import hp_score as M
    eps, stored = [39, 11], json.load(open(f'{D}/heldpose/results/hp_scores_slim.json'))['episodes']
    get = lambda r, ep, arm, v: r['arms'][arm]['delta'][v]['lib']
    s_get = lambda ep, arm, v: stored[str(ep)]['arms'][arm]['delta'][v]['lib']
    VARS = ['S10g', 'S10r', 'S10t']
else:
    os.environ['M10_VARS'] = 'S2,V1,V2,V3'
    sys.path.insert(0, f'{D}/mask10/scripts'); import m10_score as M
    eps = [11, 12]
    st = json.load(open(f'{D}/mask10/scores/m10_scores_full.json'))['episodes']
    fx = json.load(open(f'{D}/mask10/scores/m10_scores_ep11_V2fix.json'))['episodes']
    get = lambda r, ep, arm, v: r['arms'][arm]['delta'][v]['lib']
    s_get = lambda ep, arm, v: (fx if (ep == 11 and v == 'V2') else st)[str(ep)]['arms'][arm]['delta'][v]['lib']
    VARS = ['V1', 'V2', 'V3']
res = {}
with ProcessPoolExecutor(2) as ex:
    for ep, r in ex.map(M.episode, eps):
        for arm in r['arms']:
            for v in VARS:
                a, b = get(r, ep, arm, v), s_get(ep, arm, v)
                res[f'{ep}/{arm}/{v}'] = dict(rerun=a, stored=b, match=abs(a - b) < 1e-4)
                print(which, ep, arm, v, 'rerun', a, 'stored', b, 'MATCH' if abs(a - b) < 1e-4 else 'DIFF', flush=True)
json.dump(res, open(out, 'w'), indent=1)
print('all match:', all(x['match'] for x in res.values()))
