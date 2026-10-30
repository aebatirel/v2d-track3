"""[D] My ADD~sym (one Sim(3) registration to the scan) vs the kit ADD from mesh_metric (median over its seeds,
non-flip seeds) for the original SAM 3D placements (gen-probe scores.jsonl) and the lib_vis scorings."""
import json, sys
import numpy as np
sys.path.insert(0, '/tmp/claude-0/-home-user-v2d-track3/90d4009c-b597-536b-9d55-58f81afca135/scratchpad/diag/sam-placement')
from common import OUT, TAG
rows = {(r['obj'], r['seed']): r for r in json.load(open(f'{OUT}/analysis.json'))}
def kit(r):
    s = r['seeds']
    nf = [x['add_mm'] for x in s if not x['flip']]
    return dict(add_all=r['add_all'], add_med=r['add_med'], flips=f"{r['flips_all']}/{r['n_seeds']}",
                add_nonflip_med=float(np.median(nf)) if nf else None, rot_med=float(np.median([x['rot_deg'] for x in s])))
out = []
src = [('sim3_fit', '/home/user/v2d-track3/docs/research/mesh-2026-10-26/results/gen-probe/scores.jsonl', 'sam3d_sim3/')]
if len(sys.argv) > 1:
    src.append(('lib_vis', f'{OUT}/metric_lib_vis.jsonl', 'sam3d_lib_vis/'))
print('| variant | object | seed | kit ADD mean (median) mm | kit flips | kit rot median deg | ADD~sym mm [mine] | ADD~sym scale-removed [mine] | kit-rot [mine] |')
print('|---|---|---|---|---|---|---|---|---|')
for var, path, key in src:
    for l in open(path):
        r = json.loads(l)
        if key not in r['path'] or 'error' in r:
            continue
        seed = 42 if r['path'].endswith('_s42.ply') else 7
        a = rows.get((r['object'], seed))
        k = kit(r)
        e = a['variants'].get(var) if a else None
        print(f"| {var} | {r['object']} | {seed} | {k['add_all']:.1f} ({k['add_med']:.1f}) | {k['flips']} | {k['rot_med']:.1f} | "
              f"{e['add_sym_mm']:.1f} | {e['add_sym_rigid_mm']:.1f} | {e['rot_kit']:.1f} |" if e else '')
        out.append(dict(var=var, obj=r['object'], seed=seed, **k, mine=e and e['add_sym_mm'], mine_rigid=e and e['add_sym_rigid_mm'], mine_rot=e and e['rot_kit']))
json.dump(out, open(f'{OUT}/kitcmp.json', 'w'), indent=1)
