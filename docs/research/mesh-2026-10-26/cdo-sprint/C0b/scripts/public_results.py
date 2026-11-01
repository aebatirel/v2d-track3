"""C0b public results (PREREG C0b sections 6-8, 12): assembles PUBLIC_RESULTS.json from the committed pick, the
pre-registered scorings, the AUC guard verdict and the box records, and applies section 8 exactly:
  adopted(o) = WIN(o) (section 6, score_c0b.py gates) AND guard pass(o) (section 7, guard_eval_c0b.py)
Nothing is re-scored here. C0's numbers are reported, never deciding.
Usage: python -I public_results.py BOX_RESULTS_DIR RUN_ID OUT.json
"""
import json, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
C0B = os.path.dirname(HERE)
R, RUN, OUT = sys.argv[1:4]
OBJS = ['white_pot', 'white_pot_lid', 'plastic_dish_rack', 'blue_cup', 'beige_cup']
C0 = {'white_pot': dict(cdo=0.3417, add_mm=3.05), 'white_pot_lid': dict(cdo=0.2199, add_mm=4.46),
      'plastic_dish_rack': dict(cdo=0.4560, add_mm=5.37), 'blue_cup': dict(cdo=0.2906, add_mm=4.09, note='held back'),
      'beige_cup': dict(cdo_ev10=0.2475, cdo_ev8=0.2549, note='C1/T1 adopted beige lathe')}
LIB = {'white_pot': dict(cdo=0.43712, add_mm=6.69), 'white_pot_lid': dict(cdo=0.4211, add_mm=8.13),
       'plastic_dish_rack': dict(cdo=0.55506, add_mm=5.79), 'blue_cup': dict(cdo=0.52332, add_mm=10.14),
       'beige_cup': dict(cdo_ev10=0.85625, cdo_ev8=0.72995, add_mm=6.965)}

picks = json.load(open(f'{C0B}/results/picks.json'))['picks']
scores = {}
if os.path.exists(f'{C0B}/results/score_c0b.jsonl'):
    for l in open(f'{C0B}/results/score_c0b.jsonl'):
        if l.strip():
            r = json.loads(l); scores[r['object']] = r
guard = json.load(open(f'{C0B}/results/guard_result_c0b.json')) if os.path.exists(f'{C0B}/results/guard_result_c0b.json') else None
frame = json.load(open(f'{C0B}/results/frame_check_report.json'))['results'] if os.path.exists(f'{C0B}/results/frame_check_report.json') else {}
t0 = json.load(open(f'{R}/t0_c0b.json'))
params = json.load(open(f'{R}/params.json'))
res = dict(run=RUN, prereg='docs/research/mesh-2026-10-26/cdo-sprint/C0b/PREREG.md (8174998)',
           t0_c0b=dict(t0_m=t0['t0_m'], fittable=t0['fittable'], raw_m=t0['t0_raw_m'], origin=t0.get('origin'),
                       objects={k: dict(n=v['n'], median_mm=round(v['median_m'] * 1e3, 3)) for k, v in t0['objects'].items()}),
           objects={})
for o in OBJS:
    p = picks.get(o, {})
    s = scores.get(o)
    g = (guard or {}).get('objects', {}).get(o)
    d = dict(pick=p.get('pick'), sha256=p.get('sha256'), repo_path=p.get('repo_path'), fid_all_sum_mm=p.get('fid_all_sum_mm'),
             n_candidates=p.get('n_candidates'), n_eligible=p.get('n_eligible'), runner_up=p.get('runner_up'))
    if s:
        d['score'] = dict(sha1_16=s['sha'], scoring=s.get('scoring'), cdo_eval=s.get('cdo_eval'), cdo_all=s.get('cdo_all'),
                          add_med=s.get('add_med'), add_max=s.get('add_max'), flips_all=s.get('flips_all'),
                          n_seeds=s.get('n_seeds'), amb_mm=s.get('amb_mm'), seeds=s.get('seeds'))
        d['win'] = s['gates_c0b']
    if g:
        d['guard'] = {k: g[k] for k in ('adopted', 'checks', 'mean_dAUC', 'min_dAUC', 'mean_dMPPE_cm', 'mean_dRPE_cm',
                                        'mean_dSP_SR', 'mean_dMP_SR', 'missing', 'twins')}
        d['guard']['pass'] = d['guard'].pop('adopted')
    d['adopted'] = bool(s and g and s['gates_c0b']['win'] and g['adopted'])
    d['c0_D'] = C0[o]; d['library_v3_D'] = LIB[o]
    if s and o != 'beige_cup':
        d['c0b_minus_c0_cdo'] = round(s['cdo_eval'] - C0[o]['cdo'], 4)
    if o in frame:
        f = frame[o]
        d['frame_check_vs_library_v3_reported_only'] = dict(centroid_offset_mm=f['centroid_offset_mm'],
                                                          axis_angle_deg=f['axis_angle_deg'],
                                                          surf_symmetric_median_mm=f['surf_symmetric_median_mm'],
                                                          budget_new=f['budget_new'])
    res['objects'][o] = d
res['adopted'] = [o for o in OBJS if res['objects'][o]['adopted']]
res['params'] = params
json.dump(res, open(OUT, 'w'), indent=1)
for o in OBJS:
    d = res['objects'][o]
    print(o, d.get('pick'), (d.get('score') or {}).get('cdo_eval'), (d.get('score') or {}).get('add_med'),
          (d.get('score') or {}).get('flips_all'), (d.get('win') or {}).get('win'), (d.get('guard') or {}).get('pass'),
          'ADOPTED' if d['adopted'] else 'not adopted')
