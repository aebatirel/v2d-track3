"""Block-4 GT-free part: how often the spoon's M1 (layout index 0) is observed, b/c only (frozen census sets) vs with
cam a added (cama.py inliers), at rest and in hand (rest/hand masks of the census fix files), pooled over episodes.
Usage: python m1_share.py EPS(comma) OUT_JSON
"""
import json, sys
import numpy as np
S = '/tmp/claude-0/-home-user-v2d-track3/6190fffb-f3a1-5d0e-84bd-7370ece99c2f/scratchpad'
acc = {g: dict(frames=0, bc=0, abc=0, a_only=0) for g in ('rest', 'hand', 'all')}
per = {}
for e in [int(x) for x in sys.argv[1].split(',')]:
    F = np.load(f'{S}/mk/scan/fix_eval{e}_wooden_spoon.npz'); A = np.load(f'{S}/mk/cama/eval{e}_wooden_spoon.npz')
    labs = json.loads(str(F['labs'])); N = len(A['n_all'])
    bc = np.array([('0' in (labs[t] or {})) and F['n'][t] >= 2 for t in range(N)])
    abc = A['seen'][:, 0] & (A['n_all'] >= 2)
    rest = F['rest'][:N]; hand = F['hand'][:N] if len(F['hand']) else np.zeros(N, bool)
    per[e] = {}
    for g, m in (('rest', rest), ('hand', hand), ('all', np.ones(N, bool))):
        acc[g]['frames'] += int(m.sum()); acc[g]['bc'] += int((bc & m).sum()); acc[g]['abc'] += int((abc & m).sum())
        acc[g]['a_only'] += int((abc & ~bc & m).sum())
        per[e][g] = dict(frames=int(m.sum()), bc=round(float(bc[m].mean()), 3) if m.any() else None,
                         abc=round(float(abc[m].mean()), 3) if m.any() else None)
    per[e]['offset'] = int(A['offset']); per[e]['abc3_share'] = round(float((A['n_all'] >= 3).mean()), 3)
    per[e]['bc3_share'] = round(float((F['n'][:N] >= 3).mean()), 3)
    print(e, json.dumps(per[e]))
tot = {g: dict(frames=v['frames'], bc=round(v['bc'] / max(1, v['frames']), 3), abc=round(v['abc'] / max(1, v['frames']), 3))
       for g, v in acc.items()}
out = dict(pooled=tot, per_episode=per, precondition_2=dict(m1_rest_share_abc=tot['rest']['abc'], passes=tot['rest']['abc'] >= 0.30))
print(json.dumps(out['pooled'])); print(json.dumps(out['precondition_2']))
json.dump(out, open(sys.argv[2], 'w'), indent=1)
