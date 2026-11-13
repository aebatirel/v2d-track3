"""C0b public pick, re-applied locally and independently from the box's raw rows (PREREG C0b 11.3.2, section 5), then
committed before any scoring (11.3.3). GT-free: reads only the box results (candidates.json, check/*.json,
fid/*/*.jsonl, selection.json) and writes:
  C0b/results/candidates_manifest.json   every candidate: label, path in the store run, sha256, faces, watertight,
                                          budget, fidelity on ALL and per episode, exclusion
  C0b/results/picks.json                 the pick per object (+ runner-up, ties), with the box's agreement check
  C0b/results/fidelity_table.md          the table
  C0b/meshes/<object>_c0b_<label>.glb    the picked meshes (<= 10 MB each), sha256 recorded
Usage: python -I c0b_pick_local.py BOX_RESULTS_DIR RUN_ID
"""
import hashlib, json, os, shutil, sys

HERE = os.path.dirname(os.path.abspath(__file__))
C0B = os.path.dirname(HERE)
R, RUN = sys.argv[1], sys.argv[2]
SHORT = {'white_pot': 'pot', 'white_pot_lid': 'lid', 'plastic_dish_rack': 'rack', 'blue_cup': 'cup', 'beige_cup': 'beige'}


def sha256(p):
    return hashlib.sha256(open(p, 'rb').read()).hexdigest()


def first(p):
    if not os.path.exists(p):
        return None
    for l in open(p):
        if l.strip().startswith('{'):
            return json.loads(l)
    return None


def local(path):
    """box path /content/results/c0b/... -> the pulled copy under R"""
    i = path.find('/results/c0b/')
    return os.path.join(R, path[i + len('/results/c0b/'):]) if i >= 0 else path


C = json.load(open(f'{R}/candidates.json'))
rows = []
for c in C:
    o = c['object']; key = c['label'].replace('/', '__')
    p = local(c['path'])
    ck = json.load(open(f'{R}/check/{SHORT[o]}/{key}.json')) if os.path.exists(f'{R}/check/{SHORT[o]}/{key}.json') else None
    fa = first(f'{R}/fid/{SHORT[o]}/{key}@all.jsonl')
    per = {}
    for f in sorted(os.listdir(f'{R}/fid/{SHORT[o]}')):
        if f.startswith(key + '@ep'):
            r = first(f'{R}/fid/{SHORT[o]}/{f}')
            if r:
                per[f[len(key) + 1:-6]] = r['sum_mm']
    h = sha256(p) if os.path.exists(p) else None
    excl = None
    if ck is None:
        excl = 'no check row'
    elif ck['sha256'] != h:
        excl = 'check row sha256 != file'
    elif not ck['watertight_raw']:
        excl = 'not watertight (raw)'
    elif not ck['budget_ok']:
        excl = 'kit budget'
    elif fa is None:
        excl = 'no fidelity value'
    rows.append(dict(object=o, label=c['label'], episode=c['episode'], variant=c['variant'],
                     store_path=f'runs/{RUN}/results/c0b/' + os.path.relpath(p, R), sha256=h,
                     faces_raw=ck['faces_raw'] if ck else None, watertight_raw=ck['watertight_raw'] if ck else None,
                     bodies_raw=ck['bodies_raw'] if ck else None, budget=ck['budget'] if ck else None,
                     fid_all_sum_mm=fa['sum_mm'] if fa else None, fid_all_obs_to_mesh_mm=fa['obs_to_mesh_mm'] if fa else None,
                     fid_all_mesh_to_obs_mm=fa['mesh_to_obs_mm'] if fa else None, fid_per_episode_sum_mm=per,
                     excluded=excl))
box = json.load(open(f'{R}/selection.json'))['selection']
picks = {}
for o in SHORT:
    rs = [r for r in rows if r['object'] == o]
    if not rs:
        continue
    el = sorted([r for r in rs if r['excluded'] is None],
                key=lambda r: (round(r['fid_all_sum_mm'], 3), r['faces_raw'], r['label'].encode()))
    if not el:
        picks[o] = dict(pick=None, reason='no eligible candidate', n_candidates=len(rs), box_pick=box.get(o, {}).get('pick'))
        continue
    b = el[0]
    src = os.path.join(R, b['store_path'].split('/results/c0b/', 1)[1])
    dst_rel = f'meshes/{o}_c0b_{b["label"].replace("/", "_")}.glb'
    assert os.path.getsize(src) <= 10e6, 'pick > 10 MB: goes to the HF store only'
    os.makedirs(f'{C0B}/meshes', exist_ok=True)
    shutil.copyfile(src, f'{C0B}/{dst_rel}')
    assert sha256(f'{C0B}/{dst_rel}') == b['sha256']
    picks[o] = dict(pick=b['label'], sha256=b['sha256'], repo_path=f'docs/research/mesh-2026-10-26/cdo-sprint/C0b/{dst_rel}',
                    store_path=b['store_path'], fid_all_sum_mm=b['fid_all_sum_mm'], faces_raw=b['faces_raw'],
                    n_candidates=len(rs), n_eligible=len(el),
                    ties_at_3_decimals=[r['label'] for r in el[1:] if round(r['fid_all_sum_mm'], 3) == round(b['fid_all_sum_mm'], 3)],
                    runner_up=el[1]['label'] if len(el) > 1 else None,
                    runner_up_fid=el[1]['fid_all_sum_mm'] if len(el) > 1 else None,
                    excluded={r['label']: r['excluded'] for r in rs if r['excluded']},
                    box_pick=box.get(o, {}).get('pick'), agrees_with_box=box.get(o, {}).get('pick') == b['label'])
os.makedirs(f'{C0B}/results', exist_ok=True)
json.dump(dict(run=RUN, rule='PREREG C0b section 5', candidates=rows), open(f'{C0B}/results/candidates_manifest.json', 'w'), indent=1)
json.dump(dict(run=RUN, rule='PREREG C0b section 5 (re-applied locally from the box raw rows)', picks=picks),
          open(f'{C0B}/results/picks.json', 'w'), indent=1)
L = ['# C0b public candidates: obs_fidelity on ALL (GT-free; PREREG section 5)', '',
     f'Run `{RUN}`. sum_mm = obs->mesh + mesh->obs trimmed means (mm), lower is better. Per-episode values are '
     'reported only.', '']
for o in SHORT:
    rs = sorted([r for r in rows if r['object'] == o], key=lambda r: (r['fid_all_sum_mm'] is None, r['fid_all_sum_mm'] or 0))
    if not rs:
        continue
    L += [f'## {o}: pick `{picks[o]["pick"]}`', '', '| label | fid ALL sum | obs->mesh | mesh->obs | faces raw | watertight | budget faces | excluded | per episode |',
          '|---|---|---|---|---|---|---|---|---|']
    for r in rs:
        per = ' '.join(f'{k}:{v:.2f}' for k, v in r['fid_per_episode_sum_mm'].items())
        bf = (r['budget'] or {}).get('faces')
        L.append(f"| {r['label']}{' **(pick)**' if r['label'] == picks[o]['pick'] else ''} | {r['fid_all_sum_mm']} | "
                 f"{r['fid_all_obs_to_mesh_mm']} | {r['fid_all_mesh_to_obs_mm']} | {r['faces_raw']} | {r['watertight_raw']} | "
                 f"{bf} | {r['excluded'] or ''} | {per} |")
    L.append('')
open(f'{C0B}/results/fidelity_table.md', 'w').write('\n'.join(L) + '\n')
for o, p in picks.items():
    print(o, json.dumps({k: p.get(k) for k in ('pick', 'fid_all_sum_mm', 'n_eligible', 'n_candidates', 'runner_up',
                                               'runner_up_fid', 'agrees_with_box')}))
