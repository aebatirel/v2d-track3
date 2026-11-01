"""T-I16 public rerun (PREREG F-I5.15 / F-I5.16, as built F-I5.17): per-episode summary and the README tables.

Reads the round-2 driver's outputs of one run (<run>/interlock/public/ep<N>-fi5r2/fi5.json and the round folder
<run>/sim/public/ep<N>-fi5r2/r0/{floor,contact_gate,push_list_fi5r2,DO_NOT_USE,CONTACT_GATE_PENDING,manifest}.json)
and writes <out>/ep<N>/summary.json plus <out>/tables.md. Report only; it decides nothing.

  python docs/research/mesh-2026-10-26/gmg/build/I/fi517_public_summary.py --run <run> --out <results dir> --eps 12,13
"""
import argparse
import json
import os


def jl(p):
    return json.load(open(p)) if os.path.exists(p) else None


def fmt(x, nd=2):
    return '-' if x is None else (f'{x:.{nd}f}' if isinstance(x, float) else str(x))


def pieces_rows(rep, floor):
    out = {}
    for o, r in (rep.get('routes') or {}).items():
        row = dict(route=r.get('route'), n=r.get('n'), lathe_test=r.get('lathe_test'), plate_like=r.get('plate_like'),
                   gate=r.get('gate'), tried=[])
        for t in r.get('tried') or []:
            tr = dict(route=t.get('route'))
            if t.get('skipped'):
                tr['skipped'] = t['skipped']
            if t.get('error'):
                tr['error'] = t['error']
            rp = t.get('report') or {}
            if t.get('route') == '2_lathe':
                tr['why'] = rp.get('why')
                tr['profile'] = {k: rp.get('profile', {}).get(k) for k in ('why', 'r_out_mm', 'wall_runs', 'solid_runs',
                                                                           'bottomless', 'runs') if k in
                                 (rp.get('profile') or {})}
                tr['candidates'] = [{k: c.get(k) for k in ('n_s', 'base', 'B_w', 'n_r', 'n_h', 'ring_cm3',
                                                           'min_wall_mm', 'intrusion_construction_mm', 'share', 'fail',
                                                           'accepted')} for c in rp.get('tried') or []]
                for c in rp.get('tried') or []:
                    if c.get('accepted'):
                        tr['accepted'] = dict(n_s=c['n_s'], base=c['base'], B_w=c.get('B_w'), n_r=c['n_r'],
                                              n_h=c.get('n_h'), min_wall_mm=c.get('min_wall_mm'),
                                              intrusion_construction_mm=c.get('intrusion_construction_mm'),
                                              intrusion_continuity_mm=(c.get('continuity') or {}).get(
                                                  'intrusion_max_mm'),
                                              gap_share=(c.get('continuity') or {}).get('gap_share'),
                                              share=c.get('share'))
                    if c.get('continuity') and not c.get('accepted'):
                        tr.setdefault('continuity_fails', []).append(
                            dict(n_s=c['n_s'], base=c['base'], gap_share=c['continuity'].get('gap_share'),
                                 worst_height_gap_share=c['continuity'].get('worst_height_gap_share'),
                                 axial_gaps=c['continuity'].get('axial_gaps'), axial_rays=c['continuity'].get(
                                     'axial_rays')))
            else:
                tr['report'] = {k: v for k, v in rp.items() if k in ('steps', 'stuck', 'pieces', 'max_excess_cm3',
                                                                     'cap', 'coacd_pieces', 'max_convex_hull', 'sec',
                                                                     'pitch_mm', 'boxes', 'why', 'splits')}
            g = t.get('gate')
            if g:
                tr['gate'] = {k: g.get(k) for k in ('pass_', 'n', 'max_cm3', 'sum_cm3', 'over_tol')}
            row['tried'].append(tr)
        fo = ((floor or {}).get('objects') or {}).get(o) or {}
        row['share'] = fo.get('share')
        row['share_detail'] = fo.get('detail')
        row['delivered'] = fo.get('delivered')
        out[o] = row
    return out


def pair_rows(rep, floor, gate, push):
    out = {}
    for key, W in (rep.get('pairs') or {}).items():
        o, p = key.split('|')
        row = dict(pair=key, in_scope=W.get('in_scope'), why=W.get('why'), scope=W.get('scope'),
                   receiver=W.get('receiver'), guest=W.get('guest'), deliver=W.get('deliver'),
                   gates={k: {kk: g.get(kk) for kk in ('voxels', 'run_kind', 'sweep_share', 'pass_', 'fail')}
                          for k, g in (W.get('gates') or {}).items()},
                   overlap=(rep.get('overlap_track') or {}).get(key))
        comps = []
        for c in W.get('components') or []:
            comps.append(dict(R_voxels=c.get('R_voxels'), s_frames=(c.get('rest') or {}).get('s_frames'),
                              segments=(c.get('rest') or {}).get('segments'), ok_frames=c.get('ok_frames'),
                              precheck={f: dict(fails=pr.get('fails'), a=pr.get('a_table'), b=pr.get('b_support'),
                                                c={k: v for k, v in (pr.get('c_overlap') or {}).items()
                                                   if k in ('V_ov_cm3', 'removed_share', 'topology', 'min_wall_left_mm',
                                                            'pass_')}) for f, pr in (c.get('precheck') or {}).items()},
                              why=c.get('why'), c_mm=(c.get('clearance') or {}).get('c_mm'),
                              off_axis=c.get('off_axis'), d2=c.get('d2'), K_fragments=c.get('K_fragments')))
        row['components'] = comps
        if W.get('carve') is not None:
            row['carve'] = {k: v for k, v in W['carve'].items() if not isinstance(v, (list,)) or len(str(v)) < 400}
        if W.get('caps') is not None:
            row['caps'] = W['caps']
        if W.get('acceptance') is not None:
            row['acceptance'] = W['acceptance']
        if W.get('report') is not None:
            row['report'] = W['report']
        fp = ((floor or {}).get('pairs') or {}).get(key) or {}
        row['floor'] = dict(receiver=fp.get('receiver'), guest=fp.get('guest'), frames=fp.get('frames'),
                            flag=fp.get('flag') or (fp.get('info') or {}).get('flag'), info=fp.get('info'),
                            rows=[dict(frame=r['frame'], precheck_fails=(r.get('precheck') or {}).get('fails'),
                                       precheck={k: (r.get('precheck') or {}).get(k) for k in
                                                 ('a_table', 'b_support')},
                                       c_overlap={k: v for k, v in ((r.get('precheck') or {}).get('c_overlap') or
                                                                    {}).items() if k in
                                                  ('V_ov_cm3', 'removed_share', 'topology', 'min_wall_left_mm',
                                                   'pass_')},
                                       S={k: (r.get('S') or {}).get(k) for k in ('disp_mm', 'dz_mm', 'lateral_mm',
                                                                                 'tilt_deg', 'pass_', 'pieces', 'sec',
                                                                                 'below', 'nan')} if r.get('S') else
                                       None,
                                       S_ref={k: (r.get('S_ref') or {}).get(k) for k in
                                              ('disp_mm', 'dz_mm', 'lateral_mm', 'tilt_deg', 'pass_', 'status',
                                               'pieces', 'sec')} if r.get('S_ref') else None,
                                       floor_fail=r.get('floor_fail')) for r in fp.get('rows') or []])
        out[key] = row
    for key, G in ((gate or {}).get('pairs') or {}).items():
        r, g = key.split('|')
        k2 = f'{r}|{g}' if f'{r}|{g}' in out else f'{g}|{r}'
        out.setdefault(k2, dict(pair=k2))['gate'] = dict(
            verdict=G.get('verdict'),
            rows=[dict(scene=x.get('scene'), frame=x.get('frame'), gated=x.get('gated'), why=x.get('why'),
                       sets={s: {kk: v.get(kk) for kk in ('pieces', 'max_nefc', 'max_ncon', 'overflow_copies',
                                                          'median_max_nefc')} for s, v in (x.get('sets') or
                                                                                            {}).items()})
                  for x in G.get('rows') or []])
    return out


def episode(run, ep, out):
    od = os.path.join(run, 'interlock', 'public', f'ep{ep}-fi5r2')
    r0 = os.path.join(run, 'sim', 'public', f'ep{ep}-fi5r2', 'r0')
    rep = jl(os.path.join(od, 'fi5.json'))
    if rep is None:
        return None
    floor = jl(os.path.join(r0, 'floor.json'))
    gate = jl(os.path.join(r0, 'contact_gate.json'))
    push = jl(os.path.join(r0, 'push_list_fi5r2.json'))
    dnu = jl(os.path.join(r0, 'DO_NOT_USE.json'))
    pend = jl(os.path.join(r0, 'CONTACT_GATE_PENDING.json'))
    man = jl(os.path.join(r0, 'manifest.json'))
    S = dict(ep=ep, run=run, fi5_rev=rep.get('fi5_rev'), sec=rep.get('sec'), pieces=pieces_rows(rep, floor),
             pairs=pair_rows(rep, floor, gate, push), floor=dict(pass_=(floor or {}).get('pass_'),
                                                                  fails=(floor or {}).get('fails')),
             gate=dict(g1_pass=(gate or {}).get('g1_pass'), packed=(gate or {}).get('packed'),
                       g2=(gate or {}).get('g2'), flag=(gate or {}).get('flag')),
             push_list=(push or {}).get('entries'), do_not_use=dnu, contact_gate_pending=pend is not None,
             manifest_do_not_use=(man or {}).get('do_not_use'), delivered=(man or {}).get('delivered'),
             report_do_not_use=rep.get('do_not_use'))
    os.makedirs(os.path.join(out, f'ep{ep}'), exist_ok=True)
    with open(os.path.join(out, f'ep{ep}', 'summary.json'), 'w') as fh:
        json.dump(S, fh, indent=1, default=str)
    return S


def tables(SS):
    L = ['### Pieces per object (F-I5.15 / F-I5.16 ladder)', '',
         '| ep | object | lathe test (rotc sigma) | routes tried | delivered route, pieces | ring layout (N_s x B_w + base, n_h) | '
         'min wall mm | cavity intrusion mm (construction / continuity rays) | keep-out (hulls > 0.3 cm3, max cm3) | '
         'share of SHELL volume |', '|---|---|---|---|---|---|---|---|---|---|']
    for S in SS:
        for o, r in S['pieces'].items():
            tried = []
            acc = None
            for t in r['tried']:
                s = t['route']
                if t.get('skipped'):
                    s += ' (skipped)'
                elif t.get('error'):
                    s += f' (error {t["error"][:60]})'
                elif t['route'] == '2_lathe':
                    if t.get('accepted'):
                        acc = t['accepted']
                        s += ' (accepted)'
                    else:
                        fails = [f'{c["n_s"]}{c["base"]}:{c.get("fail")}' for c in t.get('candidates') or []]
                        s += f' ({t.get("why") or ""}; ' + ', '.join(fails[:6]) + ')'
                else:
                    g = t.get('gate') or {}
                    s += f' (gate {"pass" if g.get("pass_") else "fail"}: {g.get("over_tol")} > 0.3, max ' \
                         f'{fmt(g.get("max_cm3"), 3)}; n {g.get("n")})'
                tried.append(s)
            g = r.get('gate') or {}
            lay = '-' if not acc else f'{acc["n_s"]} x {acc.get("B_w")} + {acc["base"]}, n_h {acc.get("n_h")}'
            L.append(f'| {S["ep"]} | {o} | {"yes" if (r.get("lathe_test") or {}).get("accepted") else "no"} '
                     f'({fmt((r.get("lathe_test") or {}).get("rotc_sigma"))}) | {" -> ".join(tried)} | '
                     f'{r.get("route")}, {r.get("n")} | {lay} | {fmt(acc and acc.get("min_wall_mm"))} | '
                     f'{fmt(acc and acc.get("intrusion_construction_mm"), 3)} / '
                     f'{fmt(acc and acc.get("intrusion_continuity_mm"), 3)} | {g.get("over_tol")}, '
                     f'{fmt(g.get("max_cm3"), 3)} | {fmt(r.get("share"), 3)} |')
    L += ['', '### Per pair: scope, precheck at the S frames, carve', '',
          '| ep | pair | collider overlap max cm3 | scope (gates) | receiver | S frames: precheck | carve | delivered |',
          '|---|---|---|---|---|---|---|---|']
    for S in SS:
        for k, r in S['pairs'].items():
            gs = '; '.join(f'{n}: {g.get("voxels")} vox {g.get("run_kind")}, sweep {g.get("sweep_share")}'
                           f'{" FAIL " + str(g.get("fail")) if not g.get("pass_") else ""}'
                           for n, g in (r.get('gates') or {}).items()) or '-'
            pre = []
            for c in r.get('components') or []:
                for f, pr in (c.get('precheck') or {}).items():
                    pre.append(f'f{f}: {",".join(pr["fails"]) or "pass"}')
            carve = '-'
            if r.get('caps'):
                carve = f'caps {"pass" if r["caps"].get("pass_") else "FAIL " + str(r["caps"].get("fail"))}'
            elif r.get('components'):
                carve = 'not carved: ' + '; '.join(sorted(set(str(c.get('why')) for c in r['components'])))
            scope = 'in' if r.get('in_scope') else ('out' if r.get('in_scope') is False else str(r.get('scope')))
            L.append(f'| {S["ep"]} | {k} | {fmt((r.get("overlap") or {}).get("max_cm3"), 2)} | {scope}: {gs} | '
                     f'{r.get("receiver") or "-"} | {"; ".join(pre) or "-"} | {carve} | {r.get("deliver")} |')
    L += ['', '### Floor S frames: precheck, S on the delivered pieces, S on the faithful reference (S_ref)', '',
          '| ep | pair | receiver | frame | precheck | S delivered: disp / dz / tilt (pass) | S_ref: disp / dz / tilt (pass) | '
          'floor |', '|---|---|---|---|---|---|---|---|']
    for S in SS:
        for k, r in S['pairs'].items():
            fl = r.get('floor') or {}
            if not fl.get('rows'):
                L.append(f'| {S["ep"]} | {k} | {fl.get("receiver") or "-"} | - | {fl.get("flag") or "no floor frame"} '
                         f'| - | - | - |')
            for x in fl.get('rows') or []:
                pf = x.get('precheck_fails')
                a = (x.get('precheck') or {}).get('a_table') or {}
                b = (x.get('precheck') or {}).get('b_support') or {}
                c = x.get('c_overlap') or {}
                ptxt = ('pass' if not pf else 'FAIL ' + ','.join(pf)) + \
                    f' (a {fmt(a.get("lowest_mm"))} mm; b table {fmt(b.get("table_mm"))} / recv ' \
                    f'{fmt(b.get("receiver_mm"))} mm; V_ov {fmt(c.get("V_ov_cm3"), 1)} cm3)'
                s, sr = x.get('S') or {}, x.get('S_ref') or {}
                stxt = '-' if not s else f'{fmt(s.get("disp_mm"), 1)} / {fmt(s.get("dz_mm"), 1)} / ' \
                                         f'{fmt(s.get("tilt_deg"), 1)} ({"pass" if s.get("pass_") else "FAIL"})'
                rtxt = '-' if not sr else (sr.get('status', '')[:30] if sr.get('pass_') is None else
                                           f'{fmt(sr.get("disp_mm"), 1)} / {fmt(sr.get("dz_mm"), 1)} / '
                                           f'{fmt(sr.get("tilt_deg"), 1)} ({"pass" if sr.get("pass_") else "FAIL"})')
                fl_ = '-' if pf else ('FAIL' if x.get('floor_fail') else 'pass')
                L.append(f'| {S["ep"]} | {k} | {fl.get("receiver")} | f{x["frame"]} | {ptxt} | {stxt} | {rtxt} | '
                         f'{fl_} |')
    L += ['', '### Contact gate G1 (sim=rl limits; plain MuJoCo 3.17.0)', '',
          '| ep | receiver / guest | gated rows | delivered max nefc / ncon (overflow copies) | packed default max nefc '
          '(pieces) | ratio | verdict |', '|---|---|---|---|---|---|---|']
    for S in SS:
        for k, r in S['pairs'].items():
            G = r.get('gate')
            if not G:
                continue
            v = G.get('verdict') or {}
            pk = '; '.join(f'{x["sets"]["packed"]["max_nefc"]} ({x["sets"]["packed"]["pieces"]})'
                           for x in G.get('rows') or [] if x.get('gated') and 'packed' in (x.get('sets') or {}))
            L.append(f'| {S["ep"]} | {k} | {v.get("gated_rows")} | {v.get("delivered_max_nefc")} / '
                     f'{v.get("delivered_max_ncon")} ({v.get("delivered_overflow_copies")}) | {v.get("packed_max_nefc")} '
                     f'[{pk}] | {v.get("ratio")} | {"pass" if v.get("pass_") else "FAIL " + str(v.get("fail"))}'
                     f'{" " + v["flag_packed"] if v.get("flag_packed") else ""}{" " + v["flag"] if v.get("flag") else ""} |')
    L += ['', '### Delivery', '', '| ep | floor | G1 | G2 | DO_NOT_USE.json | reasons |', '|---|---|---|---|---|---|']
    for S in SS:
        d = S.get('do_not_use') or {}
        rs = []
        for f in (d.get('reasons_fi5r2') or {}).get('floor') or []:
            rs.append(f'floor {f.get("kind")} {f.get("obj") or f.get("pair")} '
                      f'{f.get("share") if f.get("share") is not None else ""}{f.get("frame") or ""}')
        for k, v in ((d.get('reasons_fi5r2') or {}).get('contact_gate_g1') or {}).items():
            rs.append(f'G1 {k} {v.get("fail")} ({v.get("delivered_max_nefc")} vs {v.get("packed_max_nefc")})')
        for k in d:
            if k not in ('rule_fi5r2', 'reasons_fi5r2'):
                rs.append(f'{k}: {str(d[k])[:120]}')
        L.append(f'| {S["ep"]} | {"pass" if S["floor"]["pass_"] else "FAIL"} | '
                 f'{"pass" if S["gate"]["g1_pass"] else "FAIL"} | {"pending" if S["contact_gate_pending"] else "-"} | '
                 f'{"yes" if S.get("do_not_use") else "no"} | {"; ".join(rs) or "-"} |')
    return '\n'.join(L) + '\n'


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--run', required=True); ap.add_argument('--out', required=True)
    ap.add_argument('--eps', default='12,13,31,11,2')
    a = ap.parse_args()
    SS = [s for s in (episode(a.run, int(e), a.out) for e in a.eps.split(',')) if s]
    with open(os.path.join(a.out, 'tables.md'), 'w') as fh:
        fh.write(tables(SS))
    print(tables(SS))


if __name__ == '__main__':
    main()
