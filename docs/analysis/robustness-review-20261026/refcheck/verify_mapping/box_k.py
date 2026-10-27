"""Re-derive the box-recorded policy-mean ratio T/S (the forensics' '0.979 x sim_vs_ref, 57 policy means, 10 episodes')
from EVERY summary.json in the store, including the per-run top-level glock_public/hard_ab/sweep summaries keyed
'epNN' that the mapping check's path regex (/ep(\\d+)[/-]) skips. Dedup by (S mean, AUC mean, n)."""
import glob, json, os, re, sys
import numpy as np

SP = '/tmp/claude-0/-home-user-v2d-track3/12630086-0942-582d-80bb-a9806af3e32b/scratchpad/refcheck'
PUBLIC = {0, 2, 11, 12, 13, 18, 21, 22, 23, 24, 26, 27, 31, 39, 40, 41, 42, 43, 44, 45}
roots = [f'{SP}/store', f'{SP}/work/verify_mapping/store']
ent = []
for root in roots:
    for p in glob.glob(f'{root}/runs/*/results/**/summary.json', recursive=True):
        rel = os.path.relpath(p, root)
        try:
            d = json.load(open(p))
        except Exception:
            continue
        m = re.search(r'/ep(\d+)[/-]', rel)
        cands = []
        if m and isinstance(d, dict) and isinstance(d.get('sim_vs_ref'), dict):
            cands.append((int(m.group(1)), d, 'per-ep file'))
        elif isinstance(d, dict):
            for k, v in d.items():
                mk = re.fullmatch(r'ep(\d+)', str(k))
                if mk and isinstance(v, dict) and isinstance(v.get('sim_vs_ref'), dict):
                    cands.append((int(mk.group(1)), v, 'top-level key'))
        for ep, v, src in cands:
            if ep not in PUBLIC or not isinstance(v.get('auc'), dict):
                continue
            ent.append(dict(ep=ep, run=rel.split('/')[1], path=rel, src=src, S=v['sim_vs_ref']['mean'], T=v['auc']['mean'],
                            n=v.get('n'), checkpoint=v.get('checkpoint')))
seen = {}
for e in sorted(ent, key=lambda e: (e['run'], e['path'])):
    seen.setdefault((round(e['S'], 4), round(e['T'], 4), e['n']), e)
B = list(seen.values())


def stats(g):
    T = np.array([x['T'] for x in g]); S = np.array([x['S'] for x in g])
    return dict(n=len(g), n_eps=len({x['ep'] for x in g}), k_ls=round(float(T @ S / (S @ S)), 4),
                sum_ratio=round(float(T.sum() / S.sum()), 4), mean_ratio=round(float(np.mean(T / S)), 4),
                median_ratio=round(float(np.median(T / S)), 4))


out = dict(n_entries=len(ent), n_distinct=len(B), by_src={s: sum(1 for x in B if x['src'] == s) for s in ('per-ep file', 'top-level key')},
           episodes=sorted({x['ep'] for x in B}), all=stats(B),
           per_ep_file_only=stats([x for x in B if x['src'] == 'per-ep file']),
           top_level_only_new=stats([x for x in B if x['src'] == 'top-level key']) if any(x['src'] == 'top-level key' for x in B) else None,
           S_ge_0_8=stats([x for x in B if x['S'] >= 0.8]), without_ep21=stats([x for x in B if x['ep'] != 21]))
# which top-level entries are NOT duplicates of a per-ep file entry
per = {(round(x['S'], 4), round(x['T'], 4), x['n']) for x in ent if x['src'] == 'per-ep file'}
out['top_level_not_in_per_ep_files'] = sorted({(x['ep'], x['run'], round(x['S'], 4), round(x['T'], 4), x['n']) for x in ent
                                               if x['src'] == 'top-level key' and (round(x['S'], 4), round(x['T'], 4), x['n']) not in per})
out['n_top_level_not_in_per_ep_files'] = len(out['top_level_not_in_per_ep_files'])
# brute force: does any 'drop k entries' subset give LS k or sum ratio exactly 0.979 (rounded to 3 decimals)?
T = np.array([x['T'] for x in B]); S = np.array([x['S'] for x in B])
hits = []
for i in range(len(B)):
    m = np.ones(len(B), bool); m[i] = False
    for nm, val in (('k_ls', T[m] @ S[m] / (S[m] @ S[m])), ('sum_ratio', T[m].sum() / S[m].sum()), ('mean_ratio', np.mean(T[m] / S[m]))):
        if round(float(val), 3) == 0.979:
            hits.append((nm, 'drop', B[i]['ep'], B[i]['run'], round(float(val), 4)))
out['drop_one_hits_0.979'] = hits
json.dump(out, open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'box_k.json'), 'w'), indent=1)
print(json.dumps({k: v for k, v in out.items() if k != 'top_level_not_in_per_ep_files'}, indent=1))
print('top-level-only entries:', out['top_level_not_in_per_ep_files'][:40])
