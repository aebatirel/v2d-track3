"""E0b results digest (GT-free, [M] only): reads the pulled box results R and writes E0b/results/RESULTS_TABLES.md and
E0b/results/results_digest.json. Nothing here chooses anything (the pick and ship rule are e0b_select.py /
e0b_package.py). Reported:
  - per stage OK / FAIL counts and the failed labels;
  - per target observed-point file: pass-B kept points (and the cube-guard record) beside E0's kept count for the same
    pair (E0's library-ROI points, its logs/obs; a size comparison only);
  - M_sep per beige episode; thickness / sigma per build input; marker balls per episode (frozen gmg detector);
  - frame-check thresholds; per object the fidelity ranking (ALL), the exclusions, and the reported-only fidelity of
    the C0b public pick, C0's mesh, library_v3, E0's pick (and the library_v3x beige) on ALL and per episode.
Usage: python -I e0b_results.py R E0_RESULTS OUT_DIR
"""
import glob, json, os, sys

R, E0R, OUT = sys.argv[1:4]
SHORT = {'white_pot': 'pot', 'white_pot_lid': 'lid', 'plastic_dish_rack': 'rack', 'blue_cup': 'cup', 'beige_cup': 'beige'}
OBJS = list(SHORT)


def rows(p):
    return [json.loads(l) for l in open(p) if l.strip().startswith('{')] if os.path.exists(p) else []


def fid(stage, o, lab, s):
    r = rows(f'{R}/{stage}/{SHORT[o]}/{lab.replace("/", "__")}@{s}.jsonl')
    return r[0]['sum_mm'] if r else None


plan = json.load(open(f'{R}/plan.json'))
sel = json.load(open(f'{R}/selection.json'))
dig = dict(stages={}, points={}, msep={}, params={}, markers={}, frame_thresholds=None, objects={})
for f in sorted(glob.glob(f'{R}/status/*.txt')):
    st = [l.split() for l in open(f) if l.strip()]
    dig['stages'][os.path.basename(f)[:-4]] = dict(ok=sum(1 for x in st if x[0] == 'OK'), fail=[x[1] for x in st if x[0] == 'FAIL'])
e0kept = {}
for f in glob.glob(f'{E0R}/logs/obs/*.log'):
    r = rows(f)
    if r:
        lab = os.path.basename(f)[:-4]
        e0kept[lab] = r[-1].get('kept')
for o, el in plan['candidate_eps'].items():
    for e in el:
        g = rows(f'{R}/guard/ep{e}_{o}.jsonl')
        ga = rows(f'{R}/guard/ep{e}_{o}.jsonl')
        gB = [x for x in g if '/pts/B/' in x['file']]
        gA = [x for x in ga if '/pts/A/' in x['file']]
        dig['points'][f'{SHORT[o]}/ep{e}'] = dict(
            passA=[dict(half_m=x['half_m'], kept=x['kept'], share=x['share'], rebuild=x['rebuild']) for x in gA],
            passB=[dict(half_m=x['half_m'], kept=x['kept'], share=x['share'], rebuild=x['rebuild']) for x in gB],
            passB_final_kept=gB[-1]['kept'] if gB else None, e0_kept=e0kept.get(f'{SHORT[o]}__ep{e}'),
            ratio_vs_e0=(gB[-1]['kept'] / e0kept[f'{SHORT[o]}__ep{e}']) if gB and e0kept.get(f'{SHORT[o]}__ep{e}') else None)
for f in sorted(glob.glob(f'{R}/msep_ep*.json')):
    j = json.load(open(f))
    dig['msep'][os.path.basename(f)[5:-5]] = {k: j[k] for k in ('frames_evaluated', 'frames_kept', 'frames_kept_with_points',
                                                                 'pts_in', 'pts_out', 'qualifies')}
if os.path.exists(f'{R}/params.json'):
    for k, v in json.load(open(f'{R}/params.json'))['targets'].items():
        dig['params'][k] = {x: v.get(x) for x in ('sigma_m', 't_fallback_m', 't_lid_m', 't_wall_m', 't_src', 'qualifies')}
for f in sorted(glob.glob(f'{R}/markers/ep*.json')):
    j = json.load(open(f))
    dig['markers'][os.path.basename(f)[:-5]] = dict(n_balls=j['n_balls'], r_consensus_mm=j['r_consensus_mm'],
                                                    radii_mm={o: [b['r_mm'] for b in j['balls'][o]] for o in j['objects']},
                                                    sec=j.get('sec'))
if os.path.exists(f'{R}/frame_thresholds.json'):
    dig['frame_thresholds'] = {o: {k: v.get(k) for k in ('pick', 'n_references', 'excludes', 'axis_checked',
                                                        'max_centroid_offset_mm', 'max_surf_symmetric_median_mm',
                                                        'max_axis_angle_deg')}
                               for o, v in json.load(open(f'{R}/frame_thresholds.json'))['objects'].items()}
for o in OBJS:
    s = sel['selection'].get(o, {})
    t = sel['table'].get(o, [])
    eps = plan['all_set'].get(o, []) if o != 'beige_cup' else [e for e in plan['candidate_eps'][o]
                                                       if dig['msep'].get(str(e), {}).get('qualifies')]
    ref = {}
    for lab, stage in ((f'{SHORT[o]}/C0bpub', 'fid'), (f'{SHORT[o]}/C0ref', 'report'), (f'{SHORT[o]}/library_v3', 'report'),
                       (f'{SHORT[o]}/E0pick', 'report'), (f'{SHORT[o]}/library_v3x', 'report')):
        a = fid(stage, o, lab, 'all')
        if a is not None or any(fid(stage, o, lab, f'ep{e}') is not None for e in eps):
            ref[lab.split('/')[1]] = dict(all=a, per_episode={f'ep{e}': fid(stage, o, lab, f'ep{e}') for e in eps})
    ranked = sorted([r for r in t if r['excluded'] is None], key=lambda r: (round(r['fid_all_sum_mm'], 3), r['faces_raw'], r['label']))
    dig['objects'][o] = dict(pick=s.get('pick'), fid_all=s.get('fid_all_sum_mm'), n_candidates=s.get('n_candidates'),
                             n_eligible=s.get('n_eligible'), rule_e=s.get('rule_e_result'), ships=s.get('ships'),
                             c0b_public_over_e0b_pick=s.get('c0b_public_over_e0b_pick'), frame_check=s.get('frame_check'),
                             excluded=s.get('excluded'), ranking=[(r['label'], r['fid_all_sum_mm'], r['faces_raw']) for r in ranked],
                             pick_per_episode=next((r['fid_per_episode_sum_mm'] for r in t if r['label'] == s.get('pick')), None),
                             references=ref, eval_episodes=eps)
os.makedirs(OUT, exist_ok=True)
json.dump(dig, open(f'{OUT}/results_digest.json', 'w'), indent=1)

L = ['# E0b box results: tables (GT-free, [M]; generated by `scripts/e0b_results.py`)', '']
L += ['## Stages', '', '| stage | OK | FAIL |', '|---|---|---|']
L += [f"| {k} | {v['ok']} | {len(v['fail'])}{(': ' + ', '.join(v['fail'])) if v['fail'] else ''} |" for k, v in dig['stages'].items()]
L += ['', '## Observed points (pass B final file; E0 = its library-ROI file for the same pair, size only)', '',
      '| target | pass A (half m: kept, guard) | pass B (half m: kept, guard) | E0 kept | B / E0 |', '|---|---|---|---|---|']
for k, v in dig['points'].items():
    fa = '; '.join(f"{x['half_m']}: {x['kept']:,}{' REBUILD' if x['rebuild'] else ''}" for x in v['passA'])
    fb = '; '.join(f"{x['half_m']}: {x['kept']:,}{' REBUILD' if x['rebuild'] else ''}" for x in v['passB'])
    L.append(f"| {k} | {fa} | {fb} | {v['e0_kept'] if v['e0_kept'] is None else format(v['e0_kept'], ',')} | "
             f"{'' if v['ratio_vs_e0'] is None else round(v['ratio_vs_e0'], 2)} |")
L += ['', '## M_sep (beige)', '', '| eval ep | frames kept / evaluated (with points) | points in -> out | qualifies |', '|---|---|---|---|']
L += [f"| {e} | {v['frames_kept']} / {v['frames_evaluated']} ({v['frames_kept_with_points']}) | {v['pts_in']:,} -> {v['pts_out']:,} | {v['qualifies']} |"
      for e, v in dig['msep'].items()]
L += ['', '## Build parameters (thickness chain, sigma)', '', '| target | sigma mm | t mm | source |', '|---|---|---|---|']
for k, v in dig['params'].items():
    t = v.get('t_fallback_m') or v.get('t_lid_m') or v.get('t_wall_m')
    L.append(f"| {k} | {'' if v.get('sigma_m') is None else round(v['sigma_m'] * 1e3, 3)} | {'' if t is None else round(t * 1e3, 3)} | {v.get('t_src')} |")
L += ['', '## Marker balls (frozen gmg detector, per eval episode)', '', '| episode | balls per object | consensus r mm | radii range mm | sec |', '|---|---|---|---|---|']
for k, v in dig['markers'].items():
    rr = [r for x in v['radii_mm'].values() for r in x]
    L.append(f"| {k} | {v['n_balls']} | {v['r_consensus_mm']} | {(round(min(rr), 1), round(max(rr), 1)) if rr else '-'} | {v['sec']} |")
L += ['', '## Frame-check thresholds (3 x max over the public references vs the C0b public pick)', '', '```',
      json.dumps(dig['frame_thresholds'], indent=1), '```', '']
for o, v in dig['objects'].items():
    L += [f'## {o}: pick {v["pick"]} (fid ALL {v["fid_all"]} mm), eligible {v["n_eligible"]}/{v["n_candidates"]}, '
          f'rule (e) {v["rule_e"]}, ships {v["ships"]}', '',
          f'Eval episodes in ALL: {v["eval_episodes"]}. Frame check: {v["frame_check"]}. C0b public / E0b pick: '
          f'{v["c0b_public_over_e0b_pick"]}.', '', '| rank | label | fid ALL mm | raw faces |', '|---|---|---|---|']
    L += [f'| {i + 1} | {lab} | {fv} | {fc} |' for i, (lab, fv, fc) in enumerate(v['ranking'][:8])]
    if v['excluded']:
        L += ['', 'Excluded: ' + '; '.join(f'{k}: {", ".join(x)}' for k, x in v['excluded'].items())]
    L += ['', '| mesh (reported only unless E0b) | ALL | ' + ' | '.join(f'ep{e}' for e in v['eval_episodes']) + ' |',
          '|---|---|' + '---|' * len(v['eval_episodes'])]
    if v['pick']:
        L.append(f"| E0b pick {v['pick']} | {v['fid_all']} | " + ' | '.join(str((v['pick_per_episode'] or {}).get(f'ep{e}')) for e in v['eval_episodes']) + ' |')
    for k, x in v['references'].items():
        L.append(f"| {k} | {x['all']} | " + ' | '.join(str(x['per_episode'].get(f'ep{e}')) for e in v['eval_episodes']) + ' |')
    L.append('')
open(f'{OUT}/RESULTS_TABLES.md', 'w').write('\n'.join(L) + '\n')
print(f'wrote {OUT}/RESULTS_TABLES.md, results_digest.json')
