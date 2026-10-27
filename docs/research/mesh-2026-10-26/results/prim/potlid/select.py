"""GT-free selection for family A: obs_fidelity of every candidate against the observed points of ALL that object's
obs_all episodes; writes fidelity.jsonl, selection.json and the mesh_metric manifest of all candidates."""
import glob, json, os, subprocess, sys
SCR = '/tmp/claude-0/-home-user-v2d-track3/90d4009c-b597-536b-9d55-58f81afca135/scratchpad'
S = '/home/user/v2d-track3/docs/research/mesh-2026-10-26/scripts'
O = f'{SCR}/prim/potlid'
LIB = '/home/user/v2d-track3/meshes/library_v3'
EPS = {'white_pot': [41, 42, 43, 44, 45, 2, 26, 27], 'white_pot_lid': [0, 2]}
fid, sel, man = [], {}, []
for obj, eps in EPS.items():
    obs = [f'{SCR}/obs_all/ep{e}_{obj}.npz' for e in eps if os.path.exists(f'{SCR}/obs_all/ep{e}_{obj}.npz')]
    cands = sorted(glob.glob(f'{O}/cand/{obj}_ep*_*.glb'))
    out = subprocess.run([f'{SCR}/venv/bin/python', '-W', 'ignore', f'{S}/obs_fidelity.py', ','.join(obs)] + cands
                         + [f'{LIB}/{obj}.glb'], capture_output=True, text=True).stdout
    rows = [json.loads(l) for l in out.splitlines() if l.startswith('{')]
    for r, path in zip(rows, cands + [f'{LIB}/{obj}.glb']):
        r.update(object=obj, path=path, obs_eps=[os.path.basename(o).split('_')[0] for o in obs])
        base = os.path.basename(path)[len(obj) + 1:-4] if path.startswith(O) else 'library_v3'
        r['episode'], r['variant'] = (base.split('_')[0], base.split('_')[1]) if base != 'library_v3' else ('-', 'library_v3')
        fid.append(r)
    cr = [r for r in fid if r['object'] == obj and r['variant'] != 'library_v3']
    best = min(cr, key=lambda r: r['sum_mm'])
    sel[obj] = best
    for r in cr:
        man.append(f"potlid/{r['variant']}/{r['episode']}\t{obj}\t{r['path']}\tprim_potlid")
with open(f'{O}/fidelity.jsonl', 'w') as f:
    for r in fid:
        f.write(json.dumps(r) + '\n')
json.dump(sel, open(f'{O}/selection.json', 'w'), indent=1)
# selected first so they are scored first
order = sorted(man, key=lambda l: 0 if any(l.split('\t')[2] == s['path'] for s in sel.values()) else 1)
open(f'{O}/manifest_all.tsv', 'w').write('\n'.join(order) + '\n')
for r in sorted(fid, key=lambda r: (r['object'], r['sum_mm'])):
    print(r['object'], r['episode'], r['variant'], r['obs_to_mesh_mm'], r['mesh_to_obs_mm'], r['sum_mm'])
print('SELECTED', {k: (v['episode'], v['variant'], v['sum_mm']) for k, v in sel.items()})
