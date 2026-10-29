"""My S and T against the box-recorded qa_policy.json (sim_vs_ref) and score_registered_ep*.json (sim AUC) next to each
stored rollout. qa_policy.json in a dir with repeats can hold the repeats' mean; then its 'rep' list is compared too.
Writes box_check.json."""
import json, os
import numpy as np

SP = '/tmp/claude-0/-home-user-v2d-track3/12630086-0942-582d-80bb-a9806af3e32b/scratchpad/refcheck'
HERE = os.path.dirname(os.path.abspath(__file__))
inv = {r['sha256']: r for r in json.load(open(f'{SP}/work/mapping/inventory.json'))['distinct']}
rows = [json.loads(l) for l in open(f'{SP}/work/verify_mapping/all.jsonl')]
S_n = S_eq = S_eq_rep = 0; S_bad = []; T_n = T_eq = 0; T_other = 0; T_bad = []
for r in rows:
    iv = inv[r['sha256']]
    for p in [iv['path']] + iv.get('copies', []):
        d = os.path.dirname(p)
        q = os.path.join(SP, 'store', d, 'qa_policy.json')
        if os.path.exists(q):
            j = json.load(open(q)); S_n += 1
            if abs(j.get('sim_vs_ref', -9) - r['S']) < 1e-4:
                S_eq += 1
            elif any(abs(x - r['S']) < 1e-4 for x in (j.get('rep') or [])):
                S_eq_rep += 1
            else:
                S_bad.append((p, r['S'], j.get('sim_vs_ref'), (j.get('rep') or [])[:3]))
            break
    if iv.get('has_sr') and os.path.exists(os.path.join(SP, 'store', iv['has_sr'])):
        j = json.load(open(os.path.join(SP, 'store', iv['has_sr'])))
        bm = os.path.basename(str(j.get('meshes', '')).rstrip('/'))
        if bm == r['lib'] or (r['lib'] == 'scan' and j.get('meshes') == 'public scans'):
            T_n += 1
            if abs(j['sim']['AUC'] - r['T']) < 1e-4:
                T_eq += 1
            else:
                T_bad.append((iv['has_sr'], r['T'], j['sim']['AUC']))
        else:
            T_other += 1
out = dict(S_compared=S_n, S_equal_own_value=S_eq, S_equal_one_of_rep=S_eq_rep, S_mismatch=len(S_bad), S_mismatch_examples=S_bad[:5],
           T_compared_same_meshes=T_n, T_equal=T_eq, T_mismatch=T_bad[:5], T_box_scored_with_other_meshes=T_other)
json.dump(out, open(os.path.join(HERE, 'box_check.json'), 'w'), indent=1)
print(json.dumps(out, indent=1))
