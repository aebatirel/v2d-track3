"""PREREG F-I4.16.3 (b) and the F-I4.16 test records: one summary of the T-I1 F-I4.16 runs (tests/test_fi416.py, one or
more JSON files from parallel processes) and the w1 regression against the round-2 record.

  python fi416_tests_summary.py <out json> <round-2 test_fi415.json> <test_fi416_*.json ...>

Freeze condition (b): every one of the nine full-outline w10 cells has no geometric miss (misses_b empty: both CARVE via
the waiver route, prisms <= 82, keep-out <= 0.3 cm3 per hull, |w - (t + 2)| <= 1 mm) AND the k = 5 cell passes P2-P7.
Everything else here is reported only. Decides nothing beyond that rule; reads only our own test records."""
import json
import sys

out_p, r2_p = sys.argv[1:3]
RES = {}
for p in sys.argv[3:]:
    d = json.load(open(p))
    for k, v in d.get('fi416', {}).items():
        RES[k] = v


def board(s):
    if not s:
        return None
    lad = s.get('ladder') or {}
    ko = s.get('keepout') or {}
    fs = s.get('free_share') or {}
    return dict(decision=s.get('decision'), tier=s.get('tier'), gate=s.get('gate_fail'), body_why=s.get('body_why'),
                t_source=s.get('t_source'), t_mm=s.get('plate_t_mm'), t_down_mm=s.get('t_down_mm'),
                t_all_mm=s.get('t_all_mm'), chosen_eps_mm=lad.get('chosen_eps_mm'),
                ladder=[(q.get('eps_mm'), q.get('simple'), q.get('vertices'), q.get('reflex_vertices'),
                         q.get('default_prisms'), q.get('slotted_prisms'), q.get('d_max_mm'), q.get('end_minus_waist_mm'),
                         q.get('fits')) for q in lad.get('rows', [])],
                ladder_cols='eps, simple, vertices, reflex, default, slotted, d_max, end-waist, fits',
                w_mm=s.get('w_mm'), centre_mm=s.get('centre_mm'), c_L_mm=s.get('c_L_mm'), D_mm=s.get('D_mm'),
                D_rect_mm=s.get('D_rect_mm'), entry_edge_shift_mm=s.get('entry_edge_shift_mm'),
                default_prisms=(s.get('default_pieces') or {}).get('n'),
                slotted_prisms=(s.get('slotted_pieces') or {}).get('n'), keepout_max_cm3=ko.get('max_cm3'),
                free_polygon=(fs.get('polygon') or {}).get('free'), free_rectangle=(fs.get('rectangle') or {}).get('free'),
                widths_mm=s.get('widths_mm'), coverage=(s.get('coverage_report') or {}),
                budget=s.get('budget'), slot_centre=s.get('slot_centre'))


def cell(v):
    s = v.get('summary') or {}
    cl = (s.get('A') or {}).get('crosslap') or {}
    out = dict(fixture=v.get('fixture'), A=board(s.get('A')), B=board(s.get('B')), crosslap=dict(
        W_x_mm=cl.get('W_x_mm'), D_sum_mm=cl.get('D_sum_mm'), diff_mm=cl.get('diff_mm'), ok=cl.get('ok')),
        misses_b=v.get('misses_b'), predictions=v.get('predictions'), sec=v.get('sec'))
    ph = v.get('physics')
    if ph:
        out['physics'] = dict(pass_P2_P7=ph.get('pass_P2_P7'), failing=(ph.get('acceptance') or {}).get('failing'),
                              P3_carved=(ph.get('P3') or {}).get('carved'), P3_default=(ph.get('P3') or {}).get('default'),
                              P3_judge=(ph.get('P3') or {}).get('judge'),
                              P6_asm_median=(ph.get('P6') or {}).get('carved_asm_median'),
                              P2=ph.get('P2'), P5=(ph.get('acceptance') or {}).get('P5'), sec=ph.get('sec'))
    return out


res = dict(rule='F-I4.16.3 (b)', cells={}, missing=[], report_only={})
for k in range(1, 10):
    v = RES.get(f'w10_k{k}')
    if v is None:
        res['missing'].append(k)
        continue
    res['cells'][k] = cell(v)
geo = {k: not c['misses_b'] for k, c in res['cells'].items()}
k5 = res['cells'].get(5, {}).get('physics') or {}
res['geometric_all_nine'] = bool(len(geo) == 9 and all(geo.values()))
res['geometric_per_cell'] = geo
res['physics_k5_pass'] = k5.get('pass_P2_P7')
res['condition_b_holds'] = bool(res['geometric_all_nine'] and k5.get('pass_P2_P7') is True)
for key in ('w10p', 'w10n'):
    if key in RES:
        c = cell(RES[key])
        c['P65'], c['P66'] = RES[key].get('P65'), RES[key].get('P66')
        res['report_only'][key] = c
for key in ('rerun_w7', 'rerun_w8', 'rerun_w8b'):
    v = RES.get(key)
    if v is None:
        continue
    if key == 'rerun_w7':
        s = v.get('summary') or {}
        res['report_only'][key] = dict(A=board(s.get('A')), B=board(s.get('B')), misses=v.get('misses'),
                                       t_source=v.get('t_source'))
    else:
        s = v.get('summary') or {}
        res['report_only'][key] = dict(A=board(s.get('A')), B=board(s.get('B')), misses=v.get('misses'),
                                       keepout_max_cm3=v.get('keepout_max_cm3'), keepout_vs_0_0=v.get('keepout_vs_0_0'),
                                       keepout_vs_0_3=v.get('keepout_vs_0_3'),
                                       P3=(v.get('P3') or {}).get('carved'), P3_judge=(v.get('P3') or {}).get('judge'),
                                       acceptance=v.get('acceptance'), sec=v.get('sec'))
idn = RES.get('identity')
if idn:
    res['identity'] = dict(bad=idn.get('bad'), cases={k: dict(same_decisions=c['same_decisions'],
                                                              built_rev15=c['built_rev15'], built_rev16=c['built_rev16'],
                                                              pieces_identical=c['pieces_identical'],
                                                              rung_1_0_both=c['rung_1_0_both'], gate_rev15=c['gate_rev15'],
                                                              gate_rev16=c['gate_rev16'], slot_rev15=c['slot_rev15'],
                                                              slot_rev16=c['slot_rev16'],
                                                              chosen_rev16={x: e.get('chosen') for x, e in
                                                                            (c.get('ladder_rev16') or {}).items()},
                                                              sec=c.get('sec'))
                                                   for k, c in idn['cases'].items()})
    # the pre-registered w1 regression against the round-2 record (decision, w, D, centre, prism counts)
    r2 = json.load(open(r2_p))['test_interlock_results'].get('w1_r2', {})
    reg = {}
    for t, rec in r2.items():
        c = idn['cases'].get(f'w1_t{t}')
        if c is None:
            continue
        row = {}
        for o, x in rec.items():
            s16 = (c.get('slot_rev16') or {}).get(o)
            d16 = (c.get('decisions_rev16') or {}).get(o)
            row[o] = dict(round2=dict(decision=x.get('decision'), w_mm=x.get('w_mm'), D_mm=x.get('D_mm'),
                                      slotted=(x.get('slotted_pieces') or {}).get('n'),
                                      default=(x.get('default_pieces') or {}).get('n')),
                          rev16=None if s16 is None else dict(decision=d16[0] if d16 else None, w_mm=s16['w_mm'],
                                                              D_mm=s16['D_mm'], slotted=s16['n_slotted'],
                                                              default=s16['n_default']))
            a, b = row[o]['round2'], row[o]['rev16']
            row[o]['same'] = b is not None and all(a[k] == b[k] for k in a) or (b is None and a['decision'] != 'CARVE')
        reg[t] = row
    res['w1_regression_vs_round2'] = reg
if 'w6c_rev16' in RES:
    res['w6c_rev16'] = {k: dict(t_all_mm=v.get('t_all_mm'), ok=v.get('ok')) for k, v in (RES['w6c_rev16'] or {}).items()}
json.dump(res, open(out_p, 'w'), indent=1)
print(json.dumps(dict(missing=res['missing'], geometric_per_cell=geo, physics_k5_pass=res['physics_k5_pass'],
                      condition_b_holds=res['condition_b_holds']), indent=1))
for k, c in res['cells'].items():
    print(k, c['fixture']['t_mm'], c['fixture']['sigma_e_mm'],
          {o: (c[o] or {}).get('chosen_eps_mm') for o in 'AB'},
          {o: ((c[o] or {}).get('default_prisms'), (c[o] or {}).get('slotted_prisms')) for o in 'AB'},
          {o: (c[o] or {}).get('w_mm') for o in 'AB'}, {o: (c[o] or {}).get('keepout_max_cm3') for o in 'AB'},
          'misses', c['misses_b'])
