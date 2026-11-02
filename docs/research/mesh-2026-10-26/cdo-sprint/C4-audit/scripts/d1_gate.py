"""D1 safety gate (C4 PREREG section 9), a veto only, diagnostic [D] against the public scan.
For one mesh: the kit seeds of every eval (episode, slot) of the object (mesh_metric roster: 1_000_003*ep + 101*slot)
plus extra seeds 11, 22, ... up to >= 6 seeds, run in BOTH reference modes (budgeted scan; raw scan). The candidate is
budgeted as packed in both. Pass = 0 flips in both modes.
Usage: MESH_SCR=<scratch> d1_gate.py OBJECT MESH.glb LABEL OUT.jsonl
"""
import json, os, sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..', 'scripts')))
import mesh_metric as MM  # noqa: E402

obj, path, label, out = sys.argv[1:5]
res = dict(label=label, object=obj, path=path, sha=MM.sha(path), modes={})
for mode, kw in (('budget_ref', {}), ('raw_ref', dict(ref_raw=True))):
    r = MM.evaluate(label, obj, path, group='c4_d1', seeds_extra=MM.EXTRA_SEEDS, min_seeds=6, min_extra=0,
                    do_amb=False, **kw)
    rows = [dict(ep=x['ep'], slot=x['slot'], seed=x['seed'], rot=x['rot_deg'], flip=x['flip'], cdo=x['cdo_cm'])
            for x in r['seeds']]
    res['modes'][mode] = dict(n=len(rows), flips=sum(x['flip'] for x in rows), rows=rows)
res['d1_pass'] = all(m['flips'] == 0 for m in res['modes'].values())
with open(out, 'a') as f:
    f.write(json.dumps(res) + '\n')
print(json.dumps({k: (v if k != 'modes' else {m: (d['n'], d['flips']) for m, d in v.items()}) for k, v in res.items()}))
