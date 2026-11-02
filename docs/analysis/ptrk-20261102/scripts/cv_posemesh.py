"""PREREG_posemesh.md analysis: leave-one-episode-out choice of the pose-board mesh (Part 1) and of test A's placement
(Part 2) per object, from 10-seed mean AUCs; plus the D1 no-flip check at eval seeds for any passing mesh.
Usage: python -I cv_posemesh.py SCRATCH"""
import sys, json, os, numpy as np
S = sys.argv[1]
eo = json.load(open(f'{S}/obj_eps.json'))
def auc(tag, e):
    return json.load(open(f'{S}/cv/{tag}/ep{e}.json'))['perception_seedmean']['AUC']
out = {}
for o, E in sorted(eo.items()):
    g = {k: {e: auc(f'{o}_{k}', e) - auc('base', e) for e in E} for k in ('12c', '9a', 'place')}
    r = dict(episodes=E, gains={k: {str(e): round(v, 4) for e, v in d.items()} for k, d in g.items()},
             mean_all={k: round(float(np.mean(list(d.values()))), 4) for k, d in g.items()})
    if len(E) >= 2:
        h1, h2 = {}, {}
        for e in E:
            rest = [x for x in E if x != e]
            opts = {'13f': 0.0, **{k: float(np.mean([g[k][x] for x in rest])) for k in ('12c', '9a')}}
            kh = max(opts, key=opts.get); h1[e] = (kh, 0.0 if kh == '13f' else g[kh][e])
            pl = float(np.mean([g['place'][x] for x in rest])) > 0; h2[e] = (pl, g['place'][e] if pl else 0.0)
        m1 = [v for _, v in h1.values()]; m2 = [v for _, v in h2.values()]
        r['part1'] = dict(heldout={str(e): [k, round(v, 4)] for e, (k, v) in h1.items()}, mean=round(float(np.mean(m1)), 4),
                          min=round(float(np.min(m1)), 4), passes=bool(np.mean(m1) >= 0.005 and np.min(m1) >= -0.01))
        if r['part1']['passes']:
            r['part1']['k_star'] = max(('12c', '9a'), key=lambda k: r['mean_all'][k])
        r['part2'] = dict(heldout={str(e): [bool(p), round(v, 4)] for e, (p, v) in h2.items()}, mean=round(float(np.mean(m2)), 4),
                          min=round(float(np.min(m2)), 4), passes=bool(np.mean(m2) >= 0.005 and np.min(m2) >= -0.01))
    else:
        r['part1'] = r['part2'] = dict(passes=False, note='one public episode: not eligible')
    out[o] = r
    print(o, 'P1', r['part1'].get('passes'), r['part1'].get('mean'), r['part1'].get('min'), r['part1'].get('k_star'),
          '| P2', r['part2'].get('passes'), r['part2'].get('mean'), r['part2'].get('min'), '| mean_all', r['mean_all'])
json.dump(out, open(f'{S}/cv_posemesh.json', 'w'), indent=1)
