"""ONE mesh_metric scoring [D] (public scan as stand-in) of the placed Tier B pitcher (C3 tier B, owner-approved
GT-informed selection, 2 Nov 2026). Eval seed(s) of the object + the 30 extra seeds used by C1/T2 (flip count).
Refuses a second scoring of the same mesh. Usage: MESH_SCR=<scratch> score_once.py OBJECT PLACED.glb LABEL OUT.jsonl
"""
import json, os, sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..', '..', 'scripts')))
import mesh_metric as MM  # noqa: E402

EXTRA = (11, 22, 33, 44, 55) + tuple(range(1001, 1026))
obj, path, label, out = sys.argv[1:5]
sha = MM.sha(path)
if os.path.exists(out) and any(json.loads(l).get('sha') == sha for l in open(out) if l.strip()):
    raise SystemExit(f'{path} (sha1 {sha}) already scored in {out}: refusing a second scoring')
rec = MM.evaluate(label, obj, path, group='cdo_c3_tierB', seeds_extra=EXTRA, min_seeds=0, min_extra=30)
with open(out, 'a') as f:
    f.write(json.dumps(rec) + '\n')
ev = [r for r in rec['seeds'] if r['ep'] is not None]
print(json.dumps({'label': label, 'sha': sha, 'eval': ev, 'flips_all': sum(bool(r['flip']) for r in rec['seeds']),
                  'n_seeds': len(rec['seeds'])}, indent=1))
