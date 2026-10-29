"""Extra checks of the mapping claims, from my own rollout scores (all.jsonl from run_score.py). Writes extra_checks.json:
- noise_by_S: within-policy single-draw sd(T|S) by policy-mean S bin; sigma of the pack 3->4 transfer with
  S-dependent noise (each changed eval's two draws get the public sd of their S bin);
- pairs_leverage: the 1063 'high-S' pairs (same ep, reference, meshes; dS >= 0.02; better policy S >= 0.8) split by
  episode, with and without ep21;
- inventory: public evaluator parquets listed, distinct by LFS sha256, local file sha256 == listed sha256;
- eval_add_auc: the evaluator's metrics.add_auc (episode json) vs S as predictors of T."""
import collections, hashlib, json, os, re
import numpy as np

SP = '/tmp/claude-0/-home-user-v2d-track3/12630086-0942-582d-80bb-a9806af3e32b/scratchpad/refcheck'
HERE = os.path.dirname(os.path.abspath(__file__))
PUB = {0, 2, 11, 12, 13, 18, 21, 22, 23, 24, 26, 27, 31, 39, 40, 41, 42, 43, 44, 45}
rows = [json.loads(l) for l in open(f'{SP}/work/verify_mapping/all.jsonl')]
own = [r for r in rows if 'error' not in r and r['lib'] != 'scan']
out = {}
G = collections.defaultdict(list)
for r in own:
    G[(r['ep'], r['ck'], r['ref_digest'], r['lib'])].append(r)
nb = {}
for lo, hi in ((0, .3), (.3, .7), (.7, .8), (.8, 1.01)):
    gs = [g for g in G.values() if len(g) >= 2 and lo <= np.mean([x['S'] for x in g]) < hi]
    dS = np.concatenate([np.array([x['S'] for x in g]) - np.mean([x['S'] for x in g]) for g in gs])
    dT = np.concatenate([np.array([x['T'] for x in g]) - np.mean([x['T'] for x in g]) for g in gs])
    b = float(dS @ dT / (dS @ dS)); e = dT - b * dS; c = len(e) / (len(e) - len(gs))
    nb[f'{lo}-{hi}'] = dict(n_pol=len(gs), n_roll=len(e), slope=round(b, 3), sd_T_given_S=round(float(np.sqrt(np.mean(e ** 2) * c)), 4))
s3 = {3: 0.8747, 5: 0.9741, 10: 0.3424, 15: 0.9576, 16: 0.8499, 25: 0.8368, 33: 0.6106}   # summary.txt [doc], re-measured in pack_refs.py
s4 = {3: 0.9418, 5: 0.9595, 10: 0.447, 15: 0.9465, 16: 0.9079, 25: 0.8937, 33: 0.9319}
sdf = lambda s: nb['0.8-1.01' if s >= .8 else '0.7-0.8' if s >= .7 else '0.3-0.7' if s >= .3 else '0-0.3']['sd_T_given_S']
var = sum(sdf(s3[e]) ** 2 + sdf(s4[e]) ** 2 for e in s3); sdS = sum(s4[e] - s3[e] for e in s3)
sig = float(np.sqrt(var) / sdS)
out['noise_by_S'] = dict(bins=nb, sigma_transfer_S_dependent=round(sig, 4), sigma_t33=round(float(np.sqrt(var) / (s4[33] - s3[33])), 3),
                         z_vs={str(v): round((v - 0.743) / sig, 2) for v in (0.94, 0.97, 0.882)})
# pairs leverage
P = [dict(ep=k[0], ref=k[2], lib=k[3], S=np.mean([x['S'] for x in g]), T=np.mean([x['T'] for x in g]), R=g[0]['R']) for k, g in G.items()]
GG = collections.defaultdict(list)
for p in P:
    GG[(p['ep'], p['ref'], p['lib'])].append(p)
pr = []
for k, g in GG.items():
    for i in range(len(g)):
        for j in range(i + 1, len(g)):
            lo, hi = sorted((g[i], g[j]), key=lambda x: x['S'])
            if hi['S'] - lo['S'] >= .02 and hi['S'] >= .8:
                pr.append(dict(ep=k[0], dS=hi['S'] - lo['S'], dT=hi['T'] - lo['T'], R=lo['R'], Slo=lo['S']))
pl = {}
for nm, sel in (('all', lambda x: True), ('no ep21', lambda x: x['ep'] != 21), ('ep21', lambda x: x['ep'] == 21),
                ('both S>=0.8', lambda x: x['Slo'] >= .8)):
    q = [x for x in pr if sel(x)]
    dS = np.array([x['dS'] for x in q]); dT = np.array([x['dT'] for x in q]); R = np.array([x['R'] for x in q])
    pl[nm] = dict(n=len(q), eps=dict(collections.Counter(x['ep'] for x in q)), mean_R=round(float(R.mean()), 3),
                  sum_dT_over_sum_dS=round(float(dT.sum() / dS.sum()), 3), sum_dT_over_sum_dSR=round(float(dT.sum() / (dS * R).sum()), 3),
                  rmse_dS=round(float(np.sqrt(np.mean((dT - dS) ** 2))), 4), rmse_dSR=round(float(np.sqrt(np.mean((dT - dS * R) ** 2))), 4))
out['pairs_leverage'] = pl
# inventory
files = json.load(open(f'{SP}/work/mapping/store_files.json'))
pq = [p for p in files if '/results/' in p and re.search(r'/episode_(\d{6})\.parquet$', p) and int(re.search(r'/episode_(\d{6})\.parquet$', p).group(1)) in PUB]
inv = json.load(open(f'{SP}/work/mapping/inventory.json'))
okh = sum(hashlib.sha256(open(f"{SP}/store/{r['path']}", 'rb').read()).hexdigest() == r['sha256'] for r in inv['distinct'])
out['inventory'] = dict(public_parquets_listed=len(pq), inventory_files=inv['n_files'], distinct=inv['n_distinct'],
                        local_sha_matches=okh, outside_results_dirs=sum(1 for p in files if re.search(r'/episode_(\d{6})\.parquet$', p)
                                                                       and int(re.search(r'/episode_(\d{6})\.parquet$', p).group(1)) in PUB and '/results/' not in p))
# evaluator add_auc vs S
E = {}
for r in inv['distinct']:
    js = r.get('has_json')
    if js and os.path.exists(f'{SP}/store/{js}'):
        m = json.load(open(f'{SP}/store/{js}')).get('metrics', {})
        if m.get('add_auc') is not None:
            E[r['sha256']] = m['add_auc']
o2 = [x for x in own if x['sha256'] in E]
T = np.array([x['T'] for x in o2]); S = np.array([x['S'] for x in o2]); Ev = np.array([E[x['sha256']] for x in o2])
GP = collections.defaultdict(list)
for x in o2:
    GP[(x['ep'], x['ck'], x['ref_digest'], x['lib'])].append(x)
PT = np.array([np.mean([x['T'] for x in g]) for g in GP.values()])
res = dict(n_rollouts=len(o2), corr_T_S=round(float(np.corrcoef(T, S)[0, 1]), 4), corr_T_E=round(float(np.corrcoef(T, Ev)[0, 1]), 4))
for nm, f in (('S', lambda x: x['S']), ('E', lambda x: E[x['sha256']])):
    X = np.array([np.mean([f(x) for x in g]) for g in GP.values()]); k = PT @ X / (X @ X)
    res[f'policy_rmse_T=k{nm}'] = round(float(np.sqrt(np.mean((PT - k * X) ** 2))), 4)
out['eval_add_auc'] = res
json.dump(out, open(os.path.join(HERE, 'extra_checks.json'), 'w'), indent=1)
print(json.dumps(out, indent=1))
