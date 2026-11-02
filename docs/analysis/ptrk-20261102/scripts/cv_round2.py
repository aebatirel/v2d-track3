"""PREREG_round2.md analysis. (a) nested leave-one-episode-out over every scored candidate tag of an object (pool =
C4-audit 'r2_<obj>_<idx>' + G2 'g2_<obj>_<i>'), baseline 13p; (b) binary LOO for 'r2place_<obj>'.
Usage: python -I cv_round2.py SCRATCH"""
import sys, json, os, glob, numpy as np
S = sys.argv[1]
eo = json.load(open(f'{S}/obj_eps.json'))
def auc(tag, e):
    f = f'{S}/cv/{tag}/ep{e}.json'
    return json.load(open(f))['perception_seedmean']['AUC'] if os.path.exists(f) else None
base = {e: auc('base13p', e) for es in eo.values() for e in es}
out = {}
for o, E in sorted(eo.items()):
    if len(E) < 2: continue
    tags = sorted({os.path.basename(p) for p in glob.glob(f'{S}/cv/r2_{o}_*') + glob.glob(f'{S}/cv/g2_{o}_*')})
    G = {}
    for t in tags:
        v = {e: auc(t, e) for e in E}
        if all(x is not None for x in v.values()):
            G[t] = {e: v[e] - base[e] for e in E}
    r = dict(n_candidates=len(G), incomplete=len(tags) - len(G))
    if G:
        held = {}
        for e in E:
            rest = [x for x in E if x != e]
            opts = {'13p': 0.0, **{t: float(np.mean([G[t][x] for x in rest])) for t in G}}
            k = max(opts, key=opts.get); held[e] = (k, 0.0 if k == '13p' else G[k][e])
        m = [v for _, v in held.values()]
        r['a'] = dict(heldout={str(e): [k, round(v, 4)] for e, (k, v) in held.items()}, mean=round(float(np.mean(m)), 4),
                      min=round(float(np.min(m)), 4), passes=bool(np.mean(m) >= 0.005 and np.min(m) >= -0.01))
        best = sorted(G, key=lambda t: -np.mean(list(G[t].values())))[:5]
        r['a']['top_all'] = [[t, round(float(np.mean(list(G[t].values()))), 4)] for t in best]
        if r['a']['passes']: r['a']['k_star'] = best[0]
    pt = f'r2place_{o}'
    if os.path.isdir(f'{S}/cv/{pt}') and all(auc(pt, e) is not None for e in E):
        g = {e: auc(pt, e) - base[e] for e in E}; h = {}
        for e in E:
            rest = [x for x in E if x != e]; pl = float(np.mean([g[x] for x in rest])) > 0; h[e] = (pl, g[e] if pl else 0.0)
        m = [v for _, v in h.values()]
        r['b'] = dict(gains={str(e): round(v, 4) for e, v in g.items()}, heldout={str(e): [p, round(v, 4)] for e, (p, v) in h.items()},
                      mean=round(float(np.mean(m)), 4), min=round(float(np.min(m)), 4), passes=bool(np.mean(m) >= 0.005 and np.min(m) >= -0.01))
    out[o] = r
    print(o, 'cands', r['n_candidates'], 'incomplete', r['incomplete'], '| a', {k: r['a'][k] for k in ('mean', 'min', 'passes')} if 'a' in r else None,
          r.get('a', {}).get('k_star'), '| b', {k: r['b'][k] for k in ('mean', 'min', 'passes')} if 'b' in r else None)
json.dump(out, open(f'{S}/cv_round2.json', 'w'), indent=1)
