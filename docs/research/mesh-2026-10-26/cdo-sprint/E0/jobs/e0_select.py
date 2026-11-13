"""E0 pre-registered pick (PREREG.md section 4), GT-free; runs on the box after the fidelity and check stages and can
be re-run locally on the pushed results. Reads only our files: fid/*/*.jsonl (obs_fidelity.py), check/*/*.json
(C0 frame_check.py), the candidate list (e0_tasks.py candidates) and E0/inputs/thresholds.json.
Per object:
  candidates = E0 eval builds that exist;
  excluded = raw mesh not watertight, kit budget_mesh error or > 4096 faces / vertices, frame check vs library_v3
             beyond 3x the C0 public mesh's value (centroid offset, median symmetric surface distance, angle of every
             axis marked checked in thresholds.json), or no fidelity on the ALL set;
  pick = lowest obs_fidelity sum_mm on ALL eval episodes' points of the object; ties: fewer raw faces, then label;
  diagnostics (never choose): C0 and library_v3 fidelity on the same points; per eval episode the own-episode build
  with the lowest fidelity on that episode's points (and the pick's, C0's, library_v3's on the same points);
  recommendation: E0 unless C0's ALL fidelity < 0.85 x the pick's (then flag; C0 recommended), except blue_cup (C0
  held back): E0 unless library_v3's ALL fidelity < 0.85 x the pick's (then library_v3); C0 cup reported only.
  No eligible E0 candidate: C0 (pot, lid, rack) or library_v3 (blue cup).
Usage: e0_select.py --results R --cands cands.json --thresholds thresholds.json --plan plan.json
"""
import argparse, glob, json, os


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--results', required=True); p.add_argument('--cands', required=True)
    p.add_argument('--thresholds', required=True); p.add_argument('--plan', required=True)
    a = p.parse_args()
    R = a.results
    C = json.load(open(a.cands)); TH = json.load(open(a.thresholds))['objects']; plan = json.load(open(a.plan))
    short = {'white_pot': 'pot', 'white_pot_lid': 'lid', 'plastic_dish_rack': 'rack', 'blue_cup': 'cup'}
    fid = {}
    rows = []
    for f in glob.glob(f'{R}/fid/*/*.jsonl'):
        lab, sname = os.path.basename(f)[:-6].replace('__', '/').rsplit('@', 1)
        for l in open(f):
            if l.startswith('{'):
                j = json.loads(l)
                fid[(lab, sname)] = j
                rows.append(dict(label=lab, set=sname, **j))
    with open(f'{R}/fidelity.jsonl', 'w') as fh:
        for r in sorted(rows, key=lambda r: (r['label'], r['set'])):
            fh.write(json.dumps(r) + '\n')
    sel = {}
    md = ['# E0 selection (pre-registered rule, PREREG.md section 4; GT-free)', '']
    for o in plan['objects']:
        cs = [c for c in C if c['object'] == o]
        if not cs:
            continue
        th = TH[o]; table = []
        for c in cs:
            r = dict(label=c['label'], kind=c['kind'], episode=c['episode'], variant=c['variant'], path=c['path'])
            fa = fid.get((c['label'], 'all'))
            r['fid_all_sum_mm'] = fa['sum_mm'] if fa else None
            r['fid_all_obs_to_mesh_mm'] = fa['obs_to_mesh_mm'] if fa else None
            r['fid_all_mesh_to_obs_mm'] = fa['mesh_to_obs_mm'] if fa else None
            r['fid_ep'] = {s: v['sum_mm'] for (l, s), v in fid.items() if l == c['label'] and s != 'all'}
            ck = f'{R}/check/{short[o]}/' + c['label'].replace('/', '__') + '.json'
            why = []
            if c['kind'] != 'library_v3':
                if os.path.exists(ck):
                    k = json.load(open(ck))['results'][o]
                    r.update(faces_raw=k['new']['faces_raw'], watertight_raw=k['new']['watertight_raw'],
                             bodies_raw=k['new']['bodies_raw'], budget=k['budget_new'],
                             centroid_offset_mm=k['centroid_offset_mm'], surf_symmetric_median_mm=k['surf_symmetric_median_mm'],
                             axis_angle_deg=k['axis_angle_deg'], sha256=k['new']['sha256'])
                    if not k['new']['watertight_raw']:
                        why.append('not watertight')
                    b = k['budget_new']
                    if not (b['faces_ok'] and b['vertices_ok']):
                        why.append('kit budget_mesh fails')
                    if k['centroid_offset_mm'] > th['max_centroid_offset_mm']:
                        why.append(f"centroid {k['centroid_offset_mm']:.1f} > {th['max_centroid_offset_mm']:.1f} mm")
                    if k['surf_symmetric_median_mm'] > th['max_surf_symmetric_median_mm']:
                        why.append(f"median dist {k['surf_symmetric_median_mm']:.2f} > {th['max_surf_symmetric_median_mm']:.2f} mm")
                    for i, (ang, mx) in enumerate(zip(k['axis_angle_deg'], th['max_axis_angle_deg'])):
                        if mx is not None and ang > mx:
                            why.append(f'axis {i} {ang:.1f} > {mx:.1f} deg')
                else:
                    why.append('no frame/budget check (check failed: kit budget_mesh error or crash)')
            if r['fid_all_sum_mm'] is None:
                why.append('no fidelity')
            r['excluded'] = why
            table.append(r)
        e0 = [r for r in table if r['kind'] == 'e0']
        ok = [r for r in e0 if not r['excluded']]
        ok.sort(key=lambda r: (r['fid_all_sum_mm'], r.get('faces_raw', 10 ** 9), r['label']))
        c0 = next(r for r in table if r['kind'] == 'C0'); lib = next(r for r in table if r['kind'] == 'library_v3')
        pick = ok[0] if ok else None
        rec, flag = None, []
        if pick is None:
            rec = 'library_v3' if o == 'blue_cup' else 'C0'
            flag.append('no eligible E0 candidate')
        else:
            ratio_c0 = c0['fid_all_sum_mm'] / pick['fid_all_sum_mm'] if c0['fid_all_sum_mm'] else None
            ratio_lib = lib['fid_all_sum_mm'] / pick['fid_all_sum_mm'] if lib['fid_all_sum_mm'] else None
            if o == 'blue_cup':
                rec = 'E0'
                if ratio_lib is not None and ratio_lib < 0.85:
                    rec = 'library_v3'; flag.append('library_v3 beats the E0 pick by > 15 % (fidelity)')
                if ratio_c0 is not None and ratio_c0 < 0.85:
                    flag.append('C0 cup (held back) beats the E0 pick by > 15 % (report only)')
            else:
                rec = 'E0'
                if ratio_c0 is not None and ratio_c0 < 0.85:
                    rec = 'C0'; flag.append('C0 beats the E0 pick by > 15 % (fidelity): owner flag')
        # per-episode own-build alternative (diagnostic)
        per_ep = {}
        for e in plan['episodes_by_object'][o]:
            s = f'ep{e}'
            own = [r for r in e0 if r['episode'] == str(e) and not r['excluded'] and s in r['fid_ep']]
            own.sort(key=lambda r: (r['fid_ep'][s], r.get('faces_raw', 10 ** 9), r['label']))
            per_ep[s] = dict(own_best=own[0]['label'] if own else None, own_best_fid=own[0]['fid_ep'][s] if own else None,
                             pick_fid=pick['fid_ep'].get(s) if pick else None, c0_fid=c0['fid_ep'].get(s),
                             library_v3_fid=lib['fid_ep'].get(s))
        sel[o] = dict(pick=pick, recommendation=rec, flags=flag, c0=c0, library_v3=lib,
                      c0_over_pick=(c0['fid_all_sum_mm'] / pick['fid_all_sum_mm']) if pick and c0['fid_all_sum_mm'] else None,
                      library_over_pick=(lib['fid_all_sum_mm'] / pick['fid_all_sum_mm']) if pick and lib['fid_all_sum_mm'] else None,
                      n_candidates=len(e0), n_eligible=len(ok), per_episode=per_ep, table=table,
                      eval_pairs=[pp for pp in plan['pairs'] if pp['object'] == o])
        md += [f'## {o} ({len(sel[o]["eval_pairs"])} eval pairs): pick {pick["label"] if pick else None}, recommendation {rec}'
               + (f' — FLAGS: {"; ".join(flag)}' if flag else ''), '',
               '| label | fid ALL sum (o->m, m->o) mm | faces | wt | budget f/v ok | centroid / median mm | axes deg | excluded |',
               '|---|---|---|---|---|---|---|---|']
        for r in sorted(table, key=lambda r: (r['fid_all_sum_mm'] if r['fid_all_sum_mm'] is not None else 1e9)):
            b = r.get('budget') or {}
            md.append(f"| {r['label']} | {r['fid_all_sum_mm']} ({r['fid_all_obs_to_mesh_mm']}, {r['fid_all_mesh_to_obs_mm']}) | "
                      f"{r.get('faces_raw', '-')} | {r.get('watertight_raw', '-')} | {b.get('faces_ok', '-')}/{b.get('vertices_ok', '-')} | "
                      f"{r.get('centroid_offset_mm', float('nan')):.1f} / {r.get('surf_symmetric_median_mm', float('nan')):.2f} | "
                      f"{[round(x, 1) for x in r.get('axis_angle_deg', [])]} | {'; '.join(r['excluded'])} |")
        md += ['', 'Per episode (diagnostic): ' + json.dumps(per_ep), '']
    json.dump(sel, open(f'{R}/selection.json', 'w'), indent=1)
    open(f'{R}/selection.md', 'w').write('\n'.join(md) + '\n')
    for o, s in sel.items():
        print(json.dumps(dict(object=o, pick=s['pick']['label'] if s['pick'] else None,
                              fid=s['pick']['fid_all_sum_mm'] if s['pick'] else None, c0=s['c0']['fid_all_sum_mm'],
                              lib=s['library_v3']['fid_all_sum_mm'], rec=s['recommendation'], flags=s['flags'],
                              eligible=f"{s['n_eligible']}/{s['n_candidates']}")))


if __name__ == '__main__':
    main()
