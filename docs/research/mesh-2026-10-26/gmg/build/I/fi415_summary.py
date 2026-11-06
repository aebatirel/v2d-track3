"""PREREG F-I4.15 (board slot round 2): one summary of a T-I11 run (decisions, plate t per board, body, slot, cross-lap,
budget, pieces, keep-out, P2-P7, delivery) from the driver's output folder and its round folder. Reads files only.

  python fi415_summary.py <interlock out dir> <sim r0 dir or -> > summary.json
"""
import json
import os
import sys


def ld(p):
    return json.load(open(p)) if os.path.exists(p) else None


def main():
    od, r0 = sys.argv[1:3]
    dec = ld(os.path.join(od, 'decisions.json')) or []
    rep = ld(os.path.join(od, 'report.json')) or {}
    out = dict(out_dir=od, sec=rep.get('sec'), fi4_rev=rep.get('fi4_rev'),
               launch_code={k: v for k, v in (rep.get('launch_code') or {}).items() if k != 'sha256'},
               boards={}, pair=None)
    W = None
    for r in dec:
        if r.get('voxels', 0) < 10:
            continue
        x = r['target']
        W = r.get('waiver_fi4') or W
        w = r.get('waiver_fi4') or {}
        pl = (w.get('plate') or {}).get(x) or {}
        bd = (w.get('body') or {}).get(x) or {}
        sl = (w.get('slot') or {}).get(x) or {}
        bu = (w.get('budget') or {}).get(x) or {}
        ta = pl.get('t_all') or {}
        out['boards'][x] = dict(
            decision=r['decision'], tier=r['tier'], flags=r['flags'], decision_f_i3=r.get('decision_f_i3'),
            in_scope=w.get('in_scope'), gate_fail=w.get('gate_fail'),
            plate=dict(plate=pl.get('plate'), t_source=pl.get('t_source'), why=pl.get('why'),
                       t_mm=round(pl['t_m'] * 1e3, 3) if pl.get('t_m') else None, t_down_mm=pl.get('t_down_mm'),
                       t_all=dict(t_mm=ta.get('t_mm'), faces=ta.get('faces'), checks=ta.get('checks'),
                                  slab_points=ta.get('slab_points')) if ta else None,
                       flags=pl.get('flags'), points=pl.get('points'), sigma_mm=pl.get('sigma_mm')),
            body=dict(ok=bd.get('ok'), why=bd.get('why'), frame=bd.get('frame'), L_mm=bd.get('L_mm'),
                      W_mm=bd.get('W_mm'), t_mm=bd.get('t_mm'), volume_cm3=bd.get('volume_cm3'),
                      polygon={k: v for k, v in (bd.get('polygon') or {}).items() if k != 'poly_mm'},
                      raster=bd.get('raster'), widths_mm=bd.get('widths_mm'), free_share=bd.get('free_share'),
                      default_pieces=bd.get('default_pieces'), slotted_pieces=bd.get('slotted_pieces'),
                      flags=bd.get('flags')) if bd else None,
            slot={k: sl.get(k) for k in ('ok', 'why', 'w_mm', 't_partner_mm', 'c_L_mm', 'c_L_component_mm',
                                         'c_L_shift_mm', 'centre_from', 'D_mm', 'P_mm', 'D_rect_mm', 'P_rect_mm',
                                         'P99_mm', 'cap_mm', 'u_rect_mm', 'u_e_poly_mm', 'bottom_mm',
                                         'entry_edge_shift_mm', 'depth_is', 'angle_d_aW_deg',
                                         'angle_partner_normal_aL_deg', 'samples')} if sl else None,
            budget={k: v for k, v in bu.items()} if bu else None,
            gates=(w.get('gates') or {}).get(x))
    if W:
        out['pair'] = dict(crosslap=W.get('crosslap'), decision=W.get('decision'), gate_fail=W.get('gate_fail'),
                           in_scope=W.get('in_scope'), why_out=W.get('why_out'))
    pairs = rep.get('pairs') or {}
    for k, v in pairs.items():
        if v.get('acceptance_fi4'):
            out['acceptance'] = v['acceptance_fi4']
        if v.get('physics'):
            ph = v['physics']
            out['physics'] = dict(P2=ph.get('P2'), P4=ph.get('P4'), P6={kk: vv for kk, vv in (ph.get('P6') or {}).items()},
                                  P7=ph.get('P7'),
                                  P3={kk: (ph.get('P3') or {}).get(kk) for kk in ('carved', 'default', 'nocollide',
                                                                                 'judge', 'sec', 'frames')},
                                  P1_precheck=ph.get('P1_precheck'), P1_precheck_default=ph.get('P1_precheck_default'),
                                  P2_P7_pass=ph.get('P2_P7_pass'))
        if v.get('pieces_gate'):
            out['pieces_gate'] = v['pieces_gate']
    if r0 != '-' and os.path.isdir(r0):
        man = ld(os.path.join(r0, 'manifest.json')) or {}
        dnu = ld(os.path.join(r0, 'DO_NOT_USE.json'))
        out['round'] = dict(dir=r0, delivered=(man.get('interlock') or {}).get('delivered'),
                            p1_pending=man.get('p1_pending'), do_not_use=dnu,
                            fi4_rev=(man.get('owner_waiver') or {}).get('fi4_rev'),
                            objects={o: sorted(os.listdir(os.path.join(r0, o))) for o in (man.get('objects') or {})
                                     if os.path.isdir(os.path.join(r0, o))},
                            default_dir=sorted(os.listdir(os.path.join(r0, '_default')))
                            if os.path.isdir(os.path.join(r0, '_default')) else None,
                            code=man.get('code'))
    json.dump(out, sys.stdout, indent=1)


if __name__ == '__main__':
    main()
