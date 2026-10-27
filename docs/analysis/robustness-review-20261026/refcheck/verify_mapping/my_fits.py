"""Re-derive the mapping check's key fits from MY OWN per-rollout scores (run_score.py -> all.jsonl), with my own
policy grouping (checkpoint sha256 from the parquet metadata, my own reference digest, mesh library).
Writes my_fits.json next to this script."""
import collections, json, os, re, sys
import numpy as np

SP = '/tmp/claude-0/-home-user-v2d-track3/12630086-0942-582d-80bb-a9806af3e32b/scratchpad/refcheck'
REPO = '/home/user/v2d-track3'
HERE = os.path.dirname(os.path.abspath(__file__))
rows = [json.loads(l) for l in open(f'{SP}/work/verify_mapping/all.jsonl')]
rows = [r for r in rows if 'error' not in r]
seen = set(); rows = [r for r in rows if not (r['sha256'] in seen or seen.add(r['sha256']))]
own = lambda x: x['lib'] != 'scan'
run_of = lambda p: p.split('/')[1]


def polkey(r):
    return (r['ep'], r['ck'] or ('dir:' + re.sub(r'/r\d+$', '', os.path.dirname(r['path']))), r['ref_digest'], r['lib'])


G = collections.defaultdict(list)
for r in rows:
    G[polkey(r)].append(r)
P = []
for k, g in G.items():
    names = list(g[0]['T_obj'])
    P.append(dict(ep=k[0], ck=k[1], ref=k[2], lib=k[3], n=len(g), S=float(np.mean([x['S'] for x in g])),
                  T=float(np.mean([x['T'] for x in g])), R=g[0]['R'], R_obj=g[0]['R_obj'],
                  T_obj={n: float(np.mean([x['T_obj'][n] for x in g])) for n in names},
                  S_obj={n: float(np.mean([x['S_obj'][n] for x in g])) for n in names},
                  run=sorted(run_of(x['path']) for x in g)[0]))
PO = [p for p in P if own(p)]


def k_ls(T, S):
    T, S = np.asarray(T), np.asarray(S); return float(T @ S / (S @ S))


def fit(v):
    T = np.array([x['T'] for x in v]); S = np.array([x['S'] for x in v]); R = np.array([x['R'] for x in v])
    k = k_ls(T, S); SR = S * R; a = float(T @ SR / (SR @ SR))
    rm = lambda e: round(float(np.sqrt(np.mean(e ** 2))), 4)
    return dict(n=len(v), eps=dict(sorted(collections.Counter(x['ep'] for x in v).items())), k=round(k, 4),
                rmse_kS=rm(T - k * S), rmse_SR=rm(T - SR), bias_SR=round(float(np.mean(T - SR)), 4), a=round(a, 4),
                rmse_aSR=rm(T - a * SR), sum_ratio=round(float(T.sum() / S.sum()), 4))


out = dict(n_rollouts=len(rows), n_policies=len(P), n_policies_own=len(PO),
           libs=dict(collections.Counter(r['lib'] for r in rows)))
sets = {'own_all': PO, 'own_R>=0.95': [p for p in PO if p['R'] >= 0.95],
        'own_S>=0.8_R>=0.95': [p for p in PO if p['S'] >= 0.8 and p['R'] >= 0.95],
        'own_S>=0.8': [p for p in PO if p['S'] >= 0.8], 'own_R<0.95': [p for p in PO if p['R'] < 0.95]}
out['fits'] = {k: fit(v) for k, v in sets.items()}
# per-episode k inside the S>=0.8, R>=0.95 subset (how much one episode dominates)
v = sets['own_S>=0.8_R>=0.95']
out['k_by_ep_S>=0.8_R>=0.95'] = {e: round(k_ls([x['T'] for x in v if x['ep'] == e], [x['S'] for x in v if x['ep'] == e]), 4)
                                 for e in sorted({x['ep'] for x in v})}
# episode-balanced k
kb = {}
for nm in ('own_all', 'own_R>=0.95', 'own_S>=0.8', 'own_S>=0.8_R>=0.95'):
    v = sets[nm]; c = collections.Counter(x['ep'] for x in v)
    w = np.array([1 / c[x['ep']] for x in v]); T = np.array([x['T'] for x in v]); S = np.array([x['S'] for x in v])
    kb[nm] = round(float(np.sum(w * T * S) / np.sum(w * S * S)), 4)
out['k_episode_balanced'] = kb
# binned T/S (sum T / sum S) by R group
bins = [(0, .3), (.3, .6), (.6, .8), (.8, .9), (.9, 1.01)]
B = {}
for nm, sel in (('R>=0.95', lambda p: p['R'] >= .95), ('0.85<=R<0.95', lambda p: .85 <= p['R'] < .95), ('R<0.85', lambda p: p['R'] < .85)):
    for lo, hi in bins:
        g = [p for p in PO if sel(p) and lo <= p['S'] < hi]
        if g:
            B[f'{nm} S{lo}-{min(hi, 1)}'] = dict(n=len(g), eps=sorted({p['ep'] for p in g}),
                                                 T_over_S=round(sum(p['T'] for p in g) / sum(p['S'] for p in g), 4))
out['binned_T_over_S'] = B
# per episode
pe = {}
for e in sorted({p['ep'] for p in PO}):
    g = [p for p in PO if p['ep'] == e]
    T = np.array([p['T'] for p in g]); S = np.array([p['S'] for p in g]); R = np.array([p['R'] for p in g]); hi = S >= .8
    pe[e] = dict(n_pol=len(g), n_roll=int(sum(p['n'] for p in g)), R=[round(float(R.min()), 3), round(float(R.max()), 3)],
                 S_mean=round(float(S.mean()), 3), T_mean=round(float(T.mean()), 3), sumT_sumS=round(float(T.sum() / S.sum()), 3),
                 res_kS_0985=round(float(np.mean(T - .985 * S)), 3), res_SR=round(float(np.mean(T - S * R)), 3),
                 n_hi=int(hi.sum()), T_over_S_hi=round(float(T[hi].sum() / S[hi].sum()), 3) if hi.any() else None,
                 res_SR_hi=round(float(np.mean(T[hi] - S[hi] * R[hi])), 3) if hi.any() else None,
                 res_kS_hi=round(float(np.mean(T[hi] - .985 * S[hi])), 3) if hi.any() else None,
                 hi_S_T=[(round(float(s), 3), round(float(t), 3)) for s, t in zip(S[hi], T[hi])] if e == 21 else None)
out['per_episode'] = pe
# within-group slope (group = ep, ref, lib) on policy means
def within(items, key):
    GG = collections.defaultdict(list)
    for x in items:
        GG[key(x)].append(x)
    num = den = 0.0; per = {}
    for k, g in GG.items():
        if len(g) < 2:
            continue
        S = np.array([x['S'] for x in g]); T = np.array([x['T'] for x in g]); dS = S - S.mean(); dT = T - T.mean()
        if dS @ dS < 1e-6:
            continue
        num += dS @ dT; den += dS @ dS
        per[f'ep{k[0]} {k[1][:6]} {k[2]}'] = dict(n=len(g), slope=round(float(dS @ dT / (dS @ dS)), 3), R=g[0]['R'],
                                                 Smax=round(float(S.max()), 3))
    return round(num / den, 4) if den else None, per


gk = lambda x: (x['ep'], x['ref'], x['lib'])
tr = {}
for nm, v in (('own', PO), ('own_R>=0.95', [p for p in PO if p['R'] >= .95]), ('own_R<0.95', [p for p in PO if p['R'] < .95])):
    s, per = within(v, gk); tr[nm] = dict(slope=s, n_groups=len(per))
tr['groups_own'] = within(PO, gk)[1]
out['transfer'] = tr
# high-S pairs: dT vs dS*R (pairs inside a group, dS >= 0.02, better policy S >= 0.8)
GG = collections.defaultdict(list)
for p in PO:
    GG[gk(p)].append(p)
pr = []
for k, g in GG.items():
    for i in range(len(g)):
        for j in range(i + 1, len(g)):
            lo, hi = sorted((g[i], g[j]), key=lambda x: x['S'])
            if hi['S'] - lo['S'] >= .02 and hi['S'] >= .8:
                pr.append((hi['S'] - lo['S'], hi['T'] - lo['T'], lo['R']))
dS, dT, R = (np.array(x) for x in zip(*pr))
out['pairs_hiS'] = dict(n=len(pr), rmse_dSR=round(float(np.sqrt(np.mean((dT - dS * R) ** 2))), 4),
                        bias_dSR=round(float(np.mean(dT - dS * R)), 4), sum_ratio_dSR=round(float(dT.sum() / (dS * R).sum()), 4),
                        rmse_dS=round(float(np.sqrt(np.mean((dT - dS) ** 2))), 4), sum_ratio_dS=round(float(dT.sum() / dS.sum()), 4))
# single-draw noise of T given S inside a policy, policies with mean S >= 0.8 (dof-corrected)
GR = collections.defaultdict(list)
for r in rows:
    if own(r):
        GR[polkey(r)].append(r)
res = {}
for nm, smin in (('all', -1), ('policy S>=0.8', .8)):
    gs = [g for g in GR.values() if len(g) >= 2 and np.mean([x['S'] for x in g]) >= smin]
    dS = np.concatenate([[x['S'] for x in g] - np.mean([x['S'] for x in g]) for g in gs])
    dT = np.concatenate([[x['T'] for x in g] - np.mean([x['T'] for x in g]) for g in gs])
    b = float(dS @ dT / (dS @ dS)); e = dT - b * dS; c = len(e) / (len(e) - len(gs))
    res[nm] = dict(n_roll=len(e), n_pol=len(gs), slope=round(b, 4), sd_T_given_S=round(float(np.sqrt(np.mean(e ** 2) * c)), 4),
                   sd_T=round(float(np.sqrt(np.mean(dT ** 2) * c)), 4), sd_S=round(float(np.sqrt(np.mean(dS ** 2) * c)), 4))
out['rollout_noise'] = res
# 60 most recent rollouts by run name (as mapping: date prefix, run, path)
rec = sorted(rows, key=lambda r: (run_of(r['path'])[:8], run_of(r['path']), r['path']))[-60:]
out['recent60'] = dict(k=round(k_ls([r['T'] for r in rec], [r['S'] for r in rec]), 4),
                       eps=dict(collections.Counter(r['ep'] for r in rec)), runs=dict(collections.Counter(run_of(r['path']) for r in rec)),
                       R_range=[min(r['R'] for r in rec), max(r['R'] for r in rec)])
# per object at policy S >= 0.8: T_obj - S_obj * R_obj
po = collections.defaultdict(list)
for p in PO:
    if p['S'] >= .8:
        for n in p['T_obj']:
            po[f"ep{p['ep']} {n}"].append(p['T_obj'][n] - p['S_obj'][n] * p['R_obj'][n])
out['per_object_res_SR_S>=0.8'] = {k: dict(n=len(v), res=round(float(np.mean(v)), 4)) for k, v in sorted(po.items())}
# per object, all own policies: ep11 blue cup T_obj, R_obj
po2 = collections.defaultdict(list)
for p in PO:
    for n in p['T_obj']:
        po2[f"ep{p['ep']} {n}"].append((p['T_obj'][n], p['S_obj'][n], p['R_obj'][n]))
out['per_object_all'] = {k: dict(n=len(v), T=round(float(np.mean([x[0] for x in v])), 3), S=round(float(np.mean([x[1] for x in v])), 3),
                                 R=round(float(np.mean([x[2] for x in v])), 3),
                                 res_SR=round(float(np.mean([x[0] - x[1] * x[2] for x in v])), 3)) for k, v in sorted(po2.items())}
json.dump(out, open(os.path.join(HERE, 'my_fits.json'), 'w'), indent=1)
print(json.dumps({k: v for k, v in out.items() if k not in ('transfer',)}, indent=1)[:12000])
print(json.dumps(out['transfer'], indent=1)[:4000])
