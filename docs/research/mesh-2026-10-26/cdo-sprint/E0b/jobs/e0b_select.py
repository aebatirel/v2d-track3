"""E0b pre-registered pick and ship rule (C0b PREREG section 9 (c)-(e), 10), GT-free. Reads only the box's own rows:
candidates.json, check/<obj>/<label>.json (c0b_check.py: watertight raw + kit budget), frame/<obj>/<label>.json (C0
frame_check.py vs the C0b public pick), frame_thresholds.json (e0b_prep.py fthr), fid/<obj>/<label>@<set>.jsonl
(obs_fidelity on ALL = the C0b eval observed points of every eval episode of the object; beige: the masked points of
its qualifying episodes) and the plan.
  (c) exclusions: raw mesh not watertight; kit budget_mesh raises or leaves > 4096 faces / vertices; frame check vs
      the C0b public pick beyond the object's thresholds (only where the thresholds exclude: an object with a
      reference set); no fidelity value on ALL
  (d) pick: lowest sum_mm on ALL; ties (equal at the printed 3 decimals) -> fewer raw faces -> label in byte order
  (e) ship (adopted objects only): the E0b pick, but the C0b public pick (flagged) if its ALL-eval fidelity is
      < 0.85 x the E0b pick's; the C0b public pick if there is no eligible E0b candidate. Not adopted: library_v3
      stays (C0b PREREG 8); the E0b pick is reported only.
Per-episode fidelity rows are reported, never deciding.
Usage: python -I e0b_select.py --results R --cands candidates.json --plan plan.json --adopted white_pot,beige_cup
       [--out selection.json]
"""
import argparse, json, os

SHORT = {'white_pot': 'pot', 'white_pot_lid': 'lid', 'plastic_dish_rack': 'rack', 'blue_cup': 'cup', 'beige_cup': 'beige'}
MARGIN = 0.85


def read_jsonl(p):
    if not os.path.exists(p):
        return None
    rows = [json.loads(l) for l in open(p) if l.strip().startswith('{')]
    return rows[0] if rows else None


def fid_rows(R, o, key):
    d = f'{R}/fid/{SHORT[o]}'
    fa = read_jsonl(f'{d}/{key}@all.jsonl')
    per = {}
    if os.path.isdir(d):
        for f in sorted(os.listdir(d)):
            if f.startswith(key + '@ep'):
                r = read_jsonl(f'{d}/{f}')
                if r:
                    per[f[len(key) + 1:-6]] = r['sum_mm']
    return fa, per


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--results', required=True); ap.add_argument('--cands', required=True)
    ap.add_argument('--plan', required=True); ap.add_argument('--adopted', required=True)
    ap.add_argument('--out', default=None)
    a = ap.parse_args()
    R = a.results
    C = json.load(open(a.cands)); plan = json.load(open(a.plan))
    adopted = [x for x in a.adopted.split(',') if x]
    TH = json.load(open(f'{R}/frame_thresholds.json'))['objects'] if os.path.exists(f'{R}/frame_thresholds.json') else {}
    table, sel = {}, {}
    for c in C:
        o = c['object']; lab = c['label']; key = lab.replace('/', '__')
        cp = f'{R}/check/{SHORT[o]}/{key}.json'
        ck = json.load(open(cp)) if os.path.exists(cp) else None
        fa, per = fid_rows(R, o, key)
        excl = []
        if ck is None:
            excl.append('no check row')
        else:
            if not ck['watertight_raw']:
                excl.append('not watertight (raw)')
            if not ck['budget_ok']:
                excl.append('kit budget')
        fr = None
        th = TH.get(o)
        if o in plan['frame_refs']:
            fp = f'{R}/frame/{SHORT[o]}/{key}.json'
            if os.path.exists(fp):
                k = json.load(open(fp))['results'][o]
                fr = dict(centroid_offset_mm=k['centroid_offset_mm'], surf_symmetric_median_mm=k['surf_symmetric_median_mm'],
                          axis_angle_deg=k['axis_angle_deg'])
                if th and th.get('excludes'):
                    if k['centroid_offset_mm'] > th['max_centroid_offset_mm']:
                        excl.append(f"frame: centroid {k['centroid_offset_mm']:.1f} > {th['max_centroid_offset_mm']:.1f} mm")
                    if k['surf_symmetric_median_mm'] > th['max_surf_symmetric_median_mm']:
                        excl.append(f"frame: median dist {k['surf_symmetric_median_mm']:.2f} > "
                                    f"{th['max_surf_symmetric_median_mm']:.2f} mm")
                    for i, (ang, mx) in enumerate(zip(k['axis_angle_deg'], th['max_axis_angle_deg'])):
                        if mx is not None and ang > mx:
                            excl.append(f'frame: axis {i} {ang:.1f} > {mx:.1f} deg')
            elif th and th.get('excludes'):
                excl.append('no frame-check row')
        if fa is None:
            excl.append('no fidelity value')
        row = dict(label=lab, object=o, episode=c['episode'], variant=c['variant'], path=c['path'],
                   sha256=ck['sha256'] if ck else None, sha1_16=ck['sha1_16'] if ck else None,
                   faces_raw=ck['faces_raw'] if ck else None, watertight_raw=ck['watertight_raw'] if ck else None,
                   budget=ck['budget'] if ck else None, fid_all_sum_mm=fa['sum_mm'] if fa else None,
                   fid_all_obs_to_mesh_mm=fa['obs_to_mesh_mm'] if fa else None,
                   fid_all_mesh_to_obs_mm=fa['mesh_to_obs_mm'] if fa else None, fid_per_episode_sum_mm=per,
                   frame_vs_c0b_pick=fr, excluded=excl or None)
        table.setdefault(o, []).append(row)
    for o in plan['candidate_eps']:
        rows = table.get(o, [])
        pub = plan['report_meshes']['c0b_public'].get(o)
        pfa, pper = fid_rows(R, o, f'{SHORT[o]}__C0bpub') if pub else (None, {})
        pubrow = dict(path=pub, fid_all_sum_mm=pfa['sum_mm'] if pfa else None, fid_per_episode_sum_mm=pper) if pub else None
        el = [r for r in rows if r['excluded'] is None]
        el.sort(key=lambda r: (round(r['fid_all_sum_mm'], 3), r['faces_raw'], r['label'].encode()))
        s = dict(n_candidates=len(rows), n_eligible=len(el), c0b_public_pick=pubrow,
                 frame_thresholds=TH.get(o),
                 frame_check='excludes' if (TH.get(o) or {}).get('excludes') else
                             ('reported only (no reference from another public episode)' if o in plan['frame_refs']
                              else 'not possible (no C0b public pick)'),
                 excluded={r['label']: r['excluded'] for r in rows if r['excluded']})
        if el:
            b = el[0]
            s.update(pick=b['label'], path=b['path'], sha256=b['sha256'], sha1_16=b['sha1_16'],
                     fid_all_sum_mm=b['fid_all_sum_mm'], faces_raw=b['faces_raw'],
                     ties_at_3_decimals=[r['label'] for r in el[1:] if round(r['fid_all_sum_mm'], 3) == round(b['fid_all_sum_mm'], 3)],
                     runner_up=el[1]['label'] if len(el) > 1 else None,
                     runner_up_fid=el[1]['fid_all_sum_mm'] if len(el) > 1 else None)
        else:
            s.update(pick=None, reason='no eligible E0b candidate' if rows else 'no E0b candidate built')
        # (e) ship rule
        flags = []
        ratio = (pubrow['fid_all_sum_mm'] / s['fid_all_sum_mm']) if (pubrow and pubrow['fid_all_sum_mm'] and s.get('pick')) else None
        s['c0b_public_over_e0b_pick'] = ratio
        if s.get('pick') is None:
            ship_rule = 'c0b_public' if pub else None
            flags.append('no eligible E0b candidate: C0b public pick' if pub else 'no eligible E0b candidate and no C0b public pick')
        elif ratio is not None and ratio < MARGIN:
            ship_rule = 'c0b_public'
            flags.append(f'C0b public pick ALL-eval fidelity {pubrow["fid_all_sum_mm"]} < 0.85 x E0b pick {s["fid_all_sum_mm"]}: '
                         'C0b public pick ships, flagged')
        else:
            ship_rule = 'e0b'
        s['rule_e_result'] = ship_rule
        s['adopted'] = o in adopted
        s['ships'] = ship_rule if o in adopted else 'library_v3 (not adopted, C0b PREREG 8)'
        s['flags'] = flags
        sel[o] = s
    res = dict(rule='C0b PREREG 9 (c)-(e): exclusions (watertight raw, kit budget, frame vs C0b public pick); lowest '
                    'obs_fidelity sum_mm on ALL eval points; ties fewer raw faces, then label; ship rule (e) for '
                    'adopted objects', adopted=adopted, selection=sel, table=table)
    out = a.out or f'{R}/selection.json'
    json.dump(res, open(out, 'w'), indent=1)
    for o, s in sel.items():
        print(o, json.dumps({k: s.get(k) for k in ('pick', 'fid_all_sum_mm', 'n_eligible', 'n_candidates', 'runner_up',
                                                   'runner_up_fid', 'c0b_public_over_e0b_pick', 'rule_e_result', 'ships')}))


if __name__ == '__main__':
    main()
