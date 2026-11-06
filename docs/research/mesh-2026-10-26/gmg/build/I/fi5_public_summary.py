"""PREREG F-I5.14 (T-I13 public): one summary per episode of an F-I5 run (routes, pieces gate, collider overlap, per
pair: scope / gates, receiver, rest, c, overshoot, carve, caps, S (acceptance or report-only diag rows), P2-P7, pieces
gate, delivery, rigid shift, one-sidedness, the flag-off decision). Reads the driver's output files only.

  python fi5_public_summary.py <interlock out dir (…/ep<N>-fi5)> > summary.json
"""
import json
import os
import sys


def ld(p):
    return json.load(open(p)) if os.path.exists(p) else None


def s_rows(rows, key):
    out = []
    for r in rows or []:
        v = r.get(key) or {}
        if v:
            out.append(dict(f=r.get('frame'), **{k: v.get(k) for k in ('disp_mm', 'dz_mm', 'lateral_mm', 'tilt_deg',
                                                                       'pass_', 'nan', 'below')}))
    return out


def pair_row(W):
    acc = W.get('acceptance') or {}
    comps = W.get('components') or []
    c0 = comps[0] if comps else {}
    caps = W.get('caps') or {}
    rep = W.get('report') or {}
    rs = rep.get('rigid_shift') or {}
    carve = W.get('carve') or {}
    row = dict(
        in_scope=W.get('in_scope'), scope=W.get('scope'), why=W.get('why'),
        gates=W.get('gates'), receiver=W.get('receiver'), guest=W.get('guest'),
        containment=(W.get('receiver_info') or {}).get('containment'),
        rest=c0.get('rest'), overshoot_frames=len(c0.get('overshoot_frames') or []),
        carve_frames=c0.get('carve_frames'), build_frames_entered=c0.get('build_frames_entered'),
        R_voxels=c0.get('R_voxels'), Rplus_voxels=c0.get('Rplus_voxels'),
        c_mm=(c0.get('clearance') or {}).get('c_mm'), sigma_sup=(c0.get('clearance') or {}).get('sigma_sup'),
        carve=dict(route=carve.get('route'), carved_route=carve.get('carved_route'), K_pieces=carve.get('K_pieces'),
                   n_sectors=carve.get('n_sectors'), pieces=carve.get('pieces'), cut_cm3=carve.get('cut_cm3'),
                   why=carve.get('why'), sec=carve.get('sec'),
                   removed_pieces=(carve.get('lathe') or {}).get('removed') if isinstance(carve.get('lathe'), dict)
                   else None) if carve else None,
        caps={k: caps.get(k) for k in ('removed_cm3', 'carve_in_body_cm3', 'cumulative_share', 'vol0_cm3', 'reach',
                                       'topology', 'ok_vol', 'ok_reach', 'ok_topology', 'pass_', 'fail', 'why')}
        if caps else None,
        rigid_shift=dict(frames=rs.get('frames'), cleared_share=rs.get('cleared_share'), error=rs.get('error'),
                         t_mm=[r.get('t_mm') for r in rs.get('per_frame') or []],
                         cm3=[r.get('cm3') for r in rs.get('per_frame') or []]) if rs else None,
        carve_of_pose_error=rep.get('carve_of_pose_error'), one_sided=rep.get('one_sided'),
        decision_flag_off=rep.get('decision_f_i3_same_sides'),
        deliver=W.get('deliver'))
    if acc:
        S = acc.get('S') or {}
        row['acceptance'] = dict(
            tests=acc.get('tests'), failing=acc.get('failing'),
            S=dict(untestable=S.get('untestable'), why=S.get('why'), pass_=S.get('pass_'),
                   carved=s_rows(S.get('frames'), 'carved'), default=s_rows(S.get('frames'), 'default')),
            P2={k: (acc.get('P2') or {}).get(k) for k in ('carved_mm', 'default_mm', 'overlap_at_pose_cm3', 'pass_',
                                                         'pose')},
            P3=dict(judge=(acc.get('P3') or {}).get('judge'),
                    **{k: {kk: vv for kk, vv in ((acc.get('P3') or {}).get(k) or {}).items()}
                       for k in ('carved', 'default', 'nocollide')}),
            P4=acc.get('P4'), P5=acc.get('P5'),
            P6={k: v for k, v in (acc.get('P6') or {}).items() if k != 'worse'},
            P7=acc.get('P7'), gate_carved=acc.get('gate_carved'), gate_default=acc.get('gate_default'))
    if W.get('diag_S_rows'):
        row['diag_S_rows'] = dict(note='report only (PREREG F-I5.14): the carve stopped before the acceptance',
                                  default=s_rows(W['diag_S_rows'], 'default'),
                                  carved_failed=s_rows(W['diag_S_rows'], 'carved_failed'))
    return row


def main():
    od = sys.argv[1]
    f5 = ld(os.path.join(od, 'fi5.json')) or {}
    rep = ld(os.path.join(od, 'report.json')) or {}
    dec_off = ld(os.path.join(od, 'decisions.json')) or []
    out = dict(out_dir=od, sec=rep.get('sec'), fi5_sec=f5.get('sec'),
               launch_code={k: v for k, v in (rep.get('launch_code') or {}).items() if k != 'sha256'},
               picks=rep.get('picks'), fi5_body=rep.get('fi5_body'), bundle=rep.get('bundle'),
               identity=rep.get('identity_semantics'), sim_dir=f5.get('sim_dir'), do_not_use=f5.get('do_not_use'),
               diag_sink=f5.get('diag_sink'),
               routes={o: dict(route=v.get('route'), n=v.get('n'), lathe_test=v.get('lathe_test'),
                               plate_like=v.get('plate_like'),
                               gate={k: (v.get('gate') or {}).get(k) for k in ('pass_', 'n', 'max_cm3', 'sum_cm3',
                                                                              'over_tol')},
                               tried=[dict(route=t.get('route'), skipped=t.get('skipped'), error=t.get('error'),
                                           gate={k: (t.get('gate') or {}).get(k) for k in ('pass_', 'n', 'max_cm3',
                                                                                          'over_tol')}
                                           if t.get('gate') else None,
                                           report={k: vv for k, vv in (t.get('report') or {}).items()
                                                   if not isinstance(vv, (list, dict)) or k in ('continuity',)})
                                      for t in v.get('tried') or []])
                       for o, v in (f5.get('routes') or {}).items()},
               overlap_track=f5.get('overlap_track'),
               decisions_fi5=[{k: r.get(k) for k in ('target', 'partner', 'decision', 'tier', 'flags', 'voxels',
                                                    'decision_f_i3', 'fi5_delivered')} for r in f5.get('decisions') or []],
               decisions_flag_off_no_silhouette=[{k: r.get(k) for k in ('target', 'partner', 'decision', 'tier',
                                                                         'flags', 'voxels')} for r in dec_off],
               pairs={k: pair_row(W) for k, W in (f5.get('pairs') or {}).items()})
    json.dump(out, sys.stdout, indent=1, default=str)


if __name__ == '__main__':
    main()
