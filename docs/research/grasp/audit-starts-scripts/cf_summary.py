"""Summarise cf_window output: per rollout AUC, per-object loss split (pre own first hold / from it on), counterfactuals."""
import sys, json, numpy as np
for p in sys.argv[1:]:
    R_ = json.load(open(p)); print('==', p.split('/')[-1])
    objs = list(R_[0]['per_obj'])
    for r in R_:
        s = f"{r['label']:8s} AUC {r['AUC']:.3f} |"
        for o in objs:
            v = r['per_obj'][o]; s += f" {o[:10]} {v['AUC']:.3f} (loss pre {v['loss']['pre']:.3f} / hold+ {v['loss']['hold_on']:.3f}; ADD {v['add_cm_pre']}/{v['add_cm_hold']} cm) |"
        print(s)
    rr = [r for r in R_ if r['label'].startswith('r')]
    keys = list(rr[0]['cf'])
    print('  counterfactual mean over r1-r5 (AUC):', ', '.join(f"{k} {np.mean([r['cf'][k] for r in rr]):.3f}" for k in keys))
    print('  mean AUC r1-r5 %.3f; mean loss split per object (sum over objects / n_obj):' % np.mean([r['AUC'] for r in rr]))
    for o in objs:
        print('    ', o, 'pre %.3f hold+ %.3f' % (np.mean([r['per_obj'][o]['loss']['pre'] for r in rr]) / len(objs), np.mean([r['per_obj'][o]['loss']['hold_on'] for r in rr]) / len(objs)))
    z = [r for r in R_ if not r['label'].startswith('r')]
    for r in z:
        print('  ', r['label'], 'cf:', ', '.join(f"{k} {v:.3f}" for k, v in r['cf'].items()))
