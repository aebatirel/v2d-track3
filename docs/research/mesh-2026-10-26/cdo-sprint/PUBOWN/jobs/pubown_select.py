"""PUBOWN per-pair pick (PLAN.md section 3), GT-free: C0b PREREG section 5 applied to ONE (episode, object) pair, with
ALL = that episode's own C0b observed points. No cross-episode pick: every pair gets a mesh built from its own
episode, or none.
  1. exclusions: raw mesh not watertight; kit budget_mesh raises or leaves > 4096 faces / vertices; no fidelity value
  2. pick: lowest obs_fidelity sum_mm on the pair's own points; ties (equal at the printed 3 decimals) -> fewer raw
     faces -> label in byte order
  3. no eligible candidate: the pair keeps library_v3 (recorded as 'fallback': 'library_v3')
Writes selection.json (picks + full table), manifest.tsv (episode, object, source, mesh path relative to the results
folder, sha256) and copies each pick to meshes/ep<N>/<object>.glb. Objects without a PUBOWN method (dust pan, sweeper,
boards, spoon, pitcher unless adopted) are listed in the manifest as library_v3.
Reads only the box's own rows: candidates.json, check/<obj>/<label>.json, fid/<obj>/<label>@own.jsonl.
Usage: python -I pubown_select.py --results R --cands candidates.json --plan plan.json
"""
import argparse, json, os, shutil

SHORT = {'white_pot': 'pot', 'white_pot_lid': 'lid', 'plastic_dish_rack': 'rack', 'blue_cup': 'cup', 'beige_cup': 'beige'}


def read_jsonl(p):
    if not os.path.exists(p):
        return None
    rows = [json.loads(l) for l in open(p) if l.strip().startswith('{')]
    return rows[0] if rows else None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--results', required=True); ap.add_argument('--cands', required=True)
    ap.add_argument('--plan', required=True)
    a = ap.parse_args()
    R = a.results
    plan = json.load(open(a.plan))
    C = json.load(open(a.cands))
    table = {}
    for c in C:
        o = c['object']; key = c['label'].replace('/', '__')
        cp = f'{R}/check/{SHORT[o]}/{key}.json'
        ck = json.load(open(cp)) if os.path.exists(cp) else None
        fo = read_jsonl(f'{R}/fid/{SHORT[o]}/{key}@own.jsonl')
        excl = None
        if ck is None:
            excl = 'no check row'
        elif not ck['watertight_raw']:
            excl = 'not watertight (raw)'
        elif not ck['budget_ok']:
            excl = 'kit budget'
        elif fo is None:
            excl = 'no fidelity value'
        table.setdefault(c['pair'], []).append(dict(
            label=c['label'], object=o, episode=c['episode'], variant=c['variant'], path=c['path'],
            sha256=ck['sha256'] if ck else None, faces_raw=ck['faces_raw'] if ck else None,
            watertight_raw=ck['watertight_raw'] if ck else None, budget=ck['budget'] if ck else None,
            fid_own_sum_mm=fo['sum_mm'] if fo else None, fid_own_obs_to_mesh_mm=fo['obs_to_mesh_mm'] if fo else None,
            fid_own_mesh_to_obs_mm=fo['mesh_to_obs_mm'] if fo else None, excluded=excl))
    sel, man = {}, []
    for e, ep in sorted(plan['episodes'].items(), key=lambda kv: int(kv[0])):
        for o in ep['slot']:
            pair = f'ep{e}/{o}'
            if o not in ep['pairs']:
                man.append((e, o, 'library_v3', f'meshes/library_v3/{o}.glb (repo)', '-', 'no PUBOWN method'))
                continue
            rows = table.get(pair, [])
            el = [r for r in rows if r['excluded'] is None]
            if not el:
                sel[pair] = dict(pick=None, fallback='library_v3', n_candidates=len(rows),
                                 excluded={r['label']: r['excluded'] for r in rows})
                man.append((e, o, 'library_v3', f'meshes/library_v3/{o}.glb (repo)', '-', 'no eligible PUBOWN candidate'))
                continue
            el.sort(key=lambda r: (round(r['fid_own_sum_mm'], 3), r['faces_raw'], r['label'].encode()))
            b = el[0]
            dst = f'meshes/ep{e}/{o}.glb'
            os.makedirs(os.path.dirname(f'{R}/{dst}'), exist_ok=True)
            shutil.copyfile(b['path'], f'{R}/{dst}')
            sel[pair] = dict(pick=b['label'], variant=b['variant'], mesh=dst, src=os.path.relpath(b['path'], R),
                             sha256=b['sha256'], fid_own_sum_mm=b['fid_own_sum_mm'], faces_raw=b['faces_raw'],
                             n_candidates=len(rows), n_eligible=len(el),
                             ties_at_3_decimals=[r['label'] for r in el[1:]
                                                 if round(r['fid_own_sum_mm'], 3) == round(b['fid_own_sum_mm'], 3)],
                             runner_up=el[1]['label'] if len(el) > 1 else None,
                             runner_up_fid=el[1]['fid_own_sum_mm'] if len(el) > 1 else None,
                             excluded={r['label']: r['excluded'] for r in rows if r['excluded']})
            man.append((e, o, 'pubown', dst, b['sha256'], b['label']))
    res = dict(rule='PUBOWN (PLAN.md s3): C0b PREREG s5 per (episode, object) with ALL = the pair\'s own points; '
                    'no cross-episode pick; no eligible candidate -> library_v3', c0b_run=plan['c0b_run'],
               c0b_code_commit=plan['c0b_code_commit'], selection=sel, table=table)
    json.dump(res, open(f'{R}/selection.json', 'w'), indent=1)
    with open(f'{R}/manifest.tsv', 'w') as fh:
        fh.write('episode\tobject\tsource\tmesh\tsha256\tnote\n')
        for row in man:
            fh.write('\t'.join(str(x) for x in row) + '\n')
    for pair, s in sel.items():
        print(pair, json.dumps({k: s.get(k) for k in ('pick', 'fid_own_sum_mm', 'n_eligible', 'n_candidates',
                                                     'runner_up', 'runner_up_fid', 'fallback')}))


if __name__ == '__main__':
    main()
