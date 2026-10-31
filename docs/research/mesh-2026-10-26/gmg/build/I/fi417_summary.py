"""Board slot round 3 (PREREG F-I4.17): compact summaries of the test_fi417 records and of a T-I11 run (results only,
not decision code).

  python fi417_summary.py tests OUT.json IN1.json [IN2.json ...]     merges test_fi417 outputs -> per-cell table
  python fi417_summary.py run OUT.json INTERLOCK_DIR [R0_DIR]           one T-I11 run (report, physics, contact gate, r0)
"""
import json
import os
import sys


def _part1(p):
    if not p:
        return None
    s = p['summary']
    out = dict(pass_=p['pass_'], ratio=p['ratio_delivered_to_control'], no_overflow=p['no_overflow_delivered'],
               scenes=p.get('scenes'), sec=p.get('sec'))
    for k, v in s.items():
        out[k] = dict(max_nefc=v['max_nefc'], max_ncon=v['max_ncon'], overflow_copies=v['overflow_copies'],
                      by_scene=v['by_scene'])
    if p.get('lowered'):
        out['lowered'] = {k: {sc: dict(max_nefc=x['max_nefc'], max_ncon=x['max_ncon'],
                                       overflow_copies=x['overflow_copies'], lowered_by_mm=x.get('lowered_by_mm'))
                              for sc, x in v.items()} for k, v in p['lowered'].items()}
    if p.get('p3_replay'):
        out['p3_replay'] = {k: dict(max_nefc=v['max_nefc'], max_ncon=v['max_ncon'], median_max_nefc=v['median_max_nefc'],
                                    nan_copies=v['nan_copies']) for k, v in p['p3_replay'].items()}
    return out


def _board(r):
    lp = r.get('low_piece') or {}
    return dict(decision=r.get('decision'), tier=r.get('tier'), body_kind=r.get('body_kind'), iou=r.get('iou'),
                n_rect=r.get('n_rect'), theta_cells=lp.get('theta_cells'), raster_cells=lp.get('raster_cells'),
                rectangles_mm=[(q['name'], q['u_mm'], q['v_mm']) for q in lp.get('rectangles', [])],
                end_minus_waist_mm=lp.get('end_minus_waist_mm'), fn_cm2=lp.get('fn_cm2'), fp_cm2=lp.get('fp_cm2'),
                passes=lp.get('passes'), t_all_mm=r.get('t_all_mm'), plate_t_mm=r.get('plate_t_mm'),
                t_source=r.get('t_source'), w_mm=r.get('w_mm'), D_mm=r.get('D_mm'), centre_mm=r.get('centre_mm'),
                slotted_boxes=(r.get('slotted_pieces') or {}).get('n'), default_boxes=(r.get('default_pieces') or {}).get('n'),
                smallest_side_mm=(r.get('slotted_pieces') or {}).get('smallest_side_mm'),
                keepout_max_cm3=(r.get('keepout') or {}).get('max_cm3'), crosslap_diff_mm=(r.get('crosslap') or {}).get('diff_mm'),
                gate_fail=r.get('gate_fail'), body_why=r.get('body_why'),
                f_i416_chosen_eps_mm=(r.get('f_i416_polygon') or {}).get('chosen_eps_mm'),
                free_share={k: (v or {}).get('free') for k, v in (r.get('free_share_reports') or {}).items()},
                coverage_frame=(r.get('coverage') or {}).get('frame'))


def tests(out, ins):
    rows = {}
    for f in ins:
        d = json.load(open(f))
        for k, v in d.get('fi417', {}).items():
            row = dict(source=os.path.basename(f))
            if isinstance(v, dict) and 'summary' in v and isinstance(v['summary'], dict):
                row['boards'] = {o: _board(v['summary'][o]) for o in v['summary'] if isinstance(v['summary'][o], dict)}
            for kk in ('misses_b', 'misses', 'width_misses', 'P130', 'P131', 'P132', 'P134', 'P125_flagged', 'frames',
                       'pieces', 'sec', 'part1_sec', 'fixture'):
                if isinstance(v, dict) and kk in v:
                    row[kk] = v[kk]
            if isinstance(v, dict) and v.get('part1'):
                row['part1'] = _part1(v['part1'])
            if isinstance(v, dict) and v.get('gate_r2'):
                row['gate_r2'] = _part1(v['gate_r2'])
                row['control_vs_control'] = v.get('control_vs_control')
            if isinstance(v, dict) and v.get('physics'):
                ph = v['physics']
                row['physics'] = dict(pass_P2_P7=ph.get('pass_P2_P7'), acceptance=ph.get('acceptance'),
                                      P3=ph.get('P3'), P2=ph.get('P2'), P6=ph.get('P6'), P7=ph.get('P7'),
                                      sec=ph.get('sec'))
            if isinstance(v, dict) and v.get('P3') and 'physics' not in row:
                row['physics'] = dict(P3=v.get('P3'), acceptance=v.get('acceptance'), sec=v.get('sec'))
            if k.startswith('code_'):
                row['value'] = v
            rows[k] = row
    json.dump(rows, open(out, 'w'), indent=1, default=str)
    for k, r in rows.items():
        b = r.get('boards') or {}
        p1 = r.get('part1') or r.get('gate_r2') or {}
        print(k, r.get('misses_b', r.get('misses')),
              {o: (x['body_kind'], x['iou'], x['n_rect'], x['slotted_boxes'], x['default_boxes'], x['keepout_max_cm3'],
                   x['w_mm']) for o, x in b.items()},
              'part1', p1.get('pass_'), p1.get('ratio'), {k2: (v2.get('max_nefc'), v2.get('max_ncon'),
                                                               v2.get('overflow_copies'))
                                                          for k2, v2 in p1.items() if isinstance(v2, dict) and
                                                          'max_nefc' in v2},
              'phys', (r.get('physics') or {}).get('pass_P2_P7'))


def run(out, idir, r0=None):
    rep = json.load(open(os.path.join(idir, 'report.json')))
    res = dict(interlock_dir=idir, sec=rep.get('sec'), fi4_rev=rep.get('fi4_rev'), launch_code=rep.get('launch_code'))
    phys = [f for f in os.listdir(idir) if f.startswith('physics_')]
    if phys:
        ph = json.load(open(os.path.join(idir, phys[0])))
        res['physics'] = {k: ph.get(k) for k in ('P2', 'P3', 'P4', 'P6', 'P7', 'P1_precheck', 'P1_precheck_default',
                                                 'P2_P7_pass')}
        if res['physics'].get('P3'):
            res['physics']['P3'] = {k: v for k, v in res['physics']['P3'].items()}
    cg = [f for f in os.listdir(idir) if f.startswith('contact_gate_')]
    if cg:
        res['contact_gate'] = _part1(json.load(open(os.path.join(idir, cg[0]))))
    dec = json.load(open(os.path.join(idir, 'decisions.json')))
    res['decisions'] = [(r['target'], r['decision'], r['tier'], (r.get('waiver_fi4') or {}).get('gate_fail'))
                        for r in dec]
    for r in dec:
        w = r.get('waiver_fi4') or {}
        x = r['target']
        if r['decision'] == 'CARVE' and w.get('body'):
            bd, sl = w['body'][x], w['slot'][x]
            lp = bd.get('low_piece') or {}
            res.setdefault('boards', {})[x] = dict(
                body_kind=bd.get('body_kind'), iou=lp.get('iou'), n_rect=lp.get('n_rect'), theta_cells=lp.get('theta_cells'),
                raster_cells=lp.get('raster_cells'), rectangles_mm=lp.get('rectangles'), fn_cm2=lp.get('fn_cm2'),
                fp_cm2=lp.get('fp_cm2'), end_minus_waist_mm=lp.get('end_minus_waist_mm'), passes=lp.get('passes'),
                t_mm=bd.get('t_mm'), L_mm=bd.get('L_mm'), W_mm=bd.get('W_mm'), volume_cm3=bd.get('volume_cm3'),
                widths_mm=bd.get('widths_mm'), coverage=bd.get('coverage'), coverage_report=bd.get('coverage_report'),
                free_share={k: v for k, v in (bd.get('free_share_reports') or {}).items()},
                slotted_pieces={k: v for k, v in (bd.get('slotted_pieces') or {}).items()},
                default_pieces={k: v for k, v in (bd.get('default_pieces') or {}).items()},
                f_i416_polygon=bd.get('f_i416_polygon'), ladder_chosen=(bd.get('ladder') or {}).get('chosen_eps_mm'),
                ladder_rows=[{k: q.get(k) for k in ('eps_mm', 'simple', 'fits', 'vertices', 'reflex_vertices',
                                                     'default_prisms', 'slotted_prisms', 'd_max_mm')}
                             for q in (bd.get('ladder') or {}).get('rows', [])],
                slot={k: sl.get(k) for k in ('w_mm', 'c_L_mm', 'D_mm', 'P_mm', 'D_rect_mm', 'u_e_poly_mm', 'u_rect_mm',
                                             'entry_edge_shift_mm', 'bottom_mm', 'angle_partner_normal_aL_deg')},
                slot_centre={k: v for k, v in (sl.get('slot_centre') or {}).items() if not k.endswith('per_mm')},
                budget=(w.get('budget') or {}).get(x), crosslap=w.get('crosslap'),
                plate={k: (w.get('plate') or {}).get(x, {}).get(k) for k in ('t_source', 't_m', 't_down_mm', 'flags')})
    if r0 and os.path.exists(os.path.join(r0, 'manifest.json')):
        man = json.load(open(os.path.join(r0, 'manifest.json')))
        res['r0'] = dict(path=r0, p1_pending=man.get('p1_pending'), contact_budget_pending=man.get('contact_budget_pending'),
                         do_not_use=man.get('do_not_use'), dnu_file=os.path.exists(os.path.join(r0, 'DO_NOT_USE.json')),
                         delivered=(man.get('interlock') or {}).get('delivered'), commit=man.get('commit'),
                         code=man.get('code'), acceptance=(man.get('owner_waiver') or {}).get('acceptance'),
                         contact_budget_part2=man.get('contact_budget_part2'))
    json.dump(res, open(out, 'w'), indent=1, default=str)
    print(json.dumps({k: res.get(k) for k in ('decisions', 'sec')}, default=str))
    for x, b in (res.get('boards') or {}).items():
        print(x, b['body_kind'], b['iou'], b['n_rect'], b['slotted_pieces'].get('n'), b['default_pieces'].get('n'),
              b['slot'])
    print('contact gate', json.dumps(res.get('contact_gate'), default=str)[:1500])
    print('r0', json.dumps({k: v for k, v in (res.get('r0') or {}).items() if k not in ('code', 'acceptance')}, default=str))


if __name__ == '__main__':
    if sys.argv[1] == 'tests':
        tests(sys.argv[2], sys.argv[3:])
    else:
        run(sys.argv[2], sys.argv[3], sys.argv[4] if len(sys.argv) > 4 else None)
