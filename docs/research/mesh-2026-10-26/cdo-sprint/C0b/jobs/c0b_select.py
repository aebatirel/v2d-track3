"""C0b pre-registered pick (PREREG cdo-sprint/C0b section 5), GT-free. Reads only the box's own rows:
candidates.json, check/<obj>/<label>.json (watertight raw + kit budget), fid/<obj>/<label>@all.jsonl (obs_fidelity on
ALL = the C0b observed points of every public episode of the object; beige: the M_sep-masked points).
  1. exclusions: raw mesh not watertight; kit budget_mesh raises or leaves > 4096 faces / vertices; no fidelity value
  2. pick: lowest sum_mm; ties (equal at the printed 3 decimals) -> fewer raw faces -> label in byte order
Per-episode fidelity rows are reported, never deciding.
Usage: python -I c0b_select.py --results R --cands candidates.json [--out selection.json]
"""
import argparse, json, os

SHORT = {'white_pot': 'pot', 'white_pot_lid': 'lid', 'plastic_dish_rack': 'rack', 'blue_cup': 'cup', 'beige_cup': 'beige'}


def read_jsonl(p):
    if not os.path.exists(p):
        return None
    rows = [json.loads(l) for l in open(p) if l.strip().startswith('{')]
    return rows[0] if rows else None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--results', required=True); ap.add_argument('--cands', required=True)
    ap.add_argument('--out', default=None)
    a = ap.parse_args()
    R = a.results
    C = json.load(open(a.cands))
    table, sel = {}, {}
    for c in C:
        o = c['object']; lab = c['label']; key = lab.replace('/', '__')
        ck = json.load(open(f'{R}/check/{SHORT[o]}/{key}.json')) if os.path.exists(f'{R}/check/{SHORT[o]}/{key}.json') else None
        fa = read_jsonl(f'{R}/fid/{SHORT[o]}/{key}@all.jsonl')
        per = {}
        for f in sorted(os.listdir(f'{R}/fid/{SHORT[o]}')):
            if f.startswith(key + '@ep'):
                r = read_jsonl(f'{R}/fid/{SHORT[o]}/{f}')
                if r:
                    per[f[len(key) + 1:-6]] = r['sum_mm']
        excl = None
        if ck is None:
            excl = 'no check row'
        elif not ck['watertight_raw']:
            excl = 'not watertight (raw)'
        elif not ck['budget_ok']:
            excl = 'kit budget'
        elif fa is None:
            excl = 'no fidelity value'
        row = dict(label=lab, object=o, episode=c['episode'], variant=c['variant'], path=c['path'],
                   sha256=ck['sha256'] if ck else None, sha1_16=ck['sha1_16'] if ck else None,
                   faces_raw=ck['faces_raw'] if ck else None, watertight_raw=ck['watertight_raw'] if ck else None,
                   budget=ck['budget'] if ck else None, fid_all_sum_mm=fa['sum_mm'] if fa else None,
                   fid_all_obs_to_mesh_mm=fa['obs_to_mesh_mm'] if fa else None,
                   fid_all_mesh_to_obs_mm=fa['mesh_to_obs_mm'] if fa else None, fid_per_episode_sum_mm=per,
                   excluded=excl)
        table.setdefault(o, []).append(row)
    for o, rows in table.items():
        el = [r for r in rows if r['excluded'] is None]
        if not el:
            sel[o] = dict(pick=None, reason='no eligible candidate', n_candidates=len(rows))
            continue
        el.sort(key=lambda r: (round(r['fid_all_sum_mm'], 3), r['faces_raw'], r['label'].encode()))
        b = el[0]
        tie = [r['label'] for r in el[1:] if round(r['fid_all_sum_mm'], 3) == round(b['fid_all_sum_mm'], 3)]
        sel[o] = dict(pick=b['label'], path=b['path'], sha256=b['sha256'], sha1_16=b['sha1_16'],
                      fid_all_sum_mm=b['fid_all_sum_mm'], faces_raw=b['faces_raw'], n_candidates=len(rows),
                      n_eligible=len(el), ties_at_3_decimals=tie,
                      runner_up=el[1]['label'] if len(el) > 1 else None,
                      runner_up_fid=el[1]['fid_all_sum_mm'] if len(el) > 1 else None,
                      excluded={r['label']: r['excluded'] for r in rows if r['excluded']})
    res = dict(rule='PREREG C0b section 5 (exclusions; lowest obs_fidelity sum_mm on ALL; ties fewer raw faces, '
                    'then label)', selection=sel, table=table)
    out = a.out or f'{R}/selection.json'
    json.dump(res, open(out, 'w'), indent=1)
    for o, s in sel.items():
        print(o, json.dumps({k: s.get(k) for k in ('pick', 'fid_all_sum_mm', 'n_eligible', 'n_candidates', 'runner_up',
                                                   'runner_up_fid')}))


if __name__ == '__main__':
    main()
