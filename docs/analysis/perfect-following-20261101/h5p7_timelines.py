"""Step 2 of the perfect-following plan: plain + symmetric sim_vs_ref and onset frames for all H5p7 draws (no GT).
python h5p7_timelines.py H5_DIR KIT OUT_JSON"""
import json, os, sys, glob
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../../tools'))
from simref_timeline import timeline
H, KIT, OUT = sys.argv[1:4]
P = json.load(open(os.path.join(os.path.dirname(__file__), '../../research/work/masses-eval-20261031/packed_refs.json')))['episodes']
res = {}
for ep in sorted(P, key=int):
    for r in range(1, 11):
        d = f'{H}/r{r}/ep{ep}'
        if not os.path.exists(f'{d}/episode_{int(ep):06d}.parquet'): continue
        o = timeline(d, int(ep), KIT, P[ep]['objects'])
        res.setdefault(ep, {})[f'r{r}'] = o
    print(ep, [res[ep][k]['sim_vs_ref'] for k in res.get(ep, {})], flush=True)
json.dump(res, open(OUT, 'w'))
