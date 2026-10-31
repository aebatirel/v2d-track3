"""PREREG F-I5.14 (T-I13 public): Markdown tables from the collected results (results/collcarve-public/ep<N>/:
summary.json, figure_data.json (volumes), delivered_sink.json). Reads files only.

  python fi5_public_table.py <results/collcarve-public> 12 13 31 11 2
"""
import json
import os
import sys


def ld(p):
    return json.load(open(p)) if os.path.exists(p) else {}


def f1(x, n=1):
    return '-' if x is None else (f'{x:.{n}f}' if isinstance(x, (int, float)) else str(x))


def main():
    root, eps = sys.argv[1], sys.argv[2:]
    obj_rows, pair_rows, sink_rows = [], [], []
    for e in eps:
        d = os.path.join(root, f'ep{e}')
        S = ld(os.path.join(d, 'summary.json'))
        V = ld(os.path.join(d, 'figure_data.json')).get('volumes') or {}
        DS = ld(os.path.join(d, 'delivered_sink.json'))
        for o, r in (S.get('routes') or {}).items():
            tried = ' -> '.join(
                (t['route'] + (f" ({t['report'].get('why')})" if (t.get('report') or {}).get('why') else '') +
                 (f" (gate fail: {t['gate']['over_tol']} hulls > 0.3 cm3, max {t['gate']['max_cm3']})"
                  if t.get('gate') and not t['gate'].get('pass_') else '') +
                 (f" ({(t.get('report') or {}).get('boxes')} boxes at {(t.get('report') or {}).get('pitch_mm')} mm)"
                  if t['route'] == '4_voxels' else ''))
                for t in r.get('tried') or [])
            v = V.get(o) or {}
            share = (100 * v['delivered_cm3'] / v['body_cm3']) if v.get('body_cm3') and v.get('delivered_cm3') else None
            obj_rows.append(f"| {e} | {o} | {f1((r.get('lathe_test') or {}).get('rotc_sigma'), 2)} | {tried} | "
                            f"{r.get('n')} | {f1(v.get('delivered_cm3'), 2)} / {f1(v.get('body_cm3'), 1)} "
                            f"({f1(share, 1)} %) |")
        for k, P in (S.get('pairs') or {}).items():
            acc = P.get('acceptance') or {}
            caps = P.get('caps') or {}
            tests = acc.get('tests') or {}
            Sv = (acc.get('S') or {})
            s_txt = '; '.join(f"f{c['f']}: carved {f1(c['disp_mm'])} mm / {f1(c['tilt_deg'])} deg, default "
                              f"{f1(dd['disp_mm'])} mm / {f1(dd['tilt_deg'])} deg"
                              for c, dd in zip(Sv.get('carved') or [], Sv.get('default') or [])) or '-'
            rs = P.get('rigid_shift') or {}
            ov = (S.get('overlap_track') or {}).get(k) or {}
            gates = '; '.join(f"{g}: {v.get('voxels')} vox, {v.get('run_kind')}, sweep {v.get('sweep_share')}"
                              + ('' if v.get('pass_') else f" FAIL {v.get('fail')}")
                              for g, v in (P.get('gates') or {}).items()) or 'no component'
 
            kk = k.replace('|', ' / ')
            ctxt = (f"{f1(caps.get('removed_cm3'), 2)} cm3 ({f1(100 * caps['cumulative_share'], 1)} %), reach "
                    f"{f1(caps.get('reach'), 2)}, topology {'kept' if caps.get('ok_topology') else 'FAIL'}") if caps else '-'
            pair_rows.append(
                f"| {e} | {kk} | {f1(ov.get('max_cm3'), 2)} | {gates} | "
                f"{'in' if P.get('in_scope') else 'out'} | {P.get('receiver') or '-'} | {f1(P.get('c_mm'), 2)} | "
                f"{P.get('overshoot_frames') if P.get('in_scope') else '-'} | "
                f"{ctxt} | "
                f"{s_txt} | "
                + ' '.join(f"{t}:{'ok' if v else 'FAIL'}" for t, v in tests.items() if t != 'S') + (' |' if tests else '- |') +
                f" {P.get('deliver') or 'default'} | "
                f"{(f1(100 * rs['cleared_share'], 0) + ' % of ' + str(rs.get('frames'))) if rs.get('cleared_share') is not None else '-'} |")
        for k, P in (DS.get('pairs') or {}).items():
            for r in P.get('S') or []:
                dd = r.get('default') or {}
                sink_rows.append(f"| {e} | {k.replace('|', ' / ')} | {P.get('receiver')} | f{r['frame']} | {f1(dd.get('disp_mm'))} | "
                                 f"{f1(dd.get('dz_mm'))} | {f1(dd.get('lateral_mm'))} | {f1(dd.get('tilt_deg'))} | "
                                 f"{'pass' if dd.get('pass_') else 'FAIL'} |")
            if not P.get('S'):
                sink_rows.append(f"| {e} | {k.replace('|', ' / ')} | {P.get('receiver') or '-'} | - | - | - | - | - | {P.get('why')} |")
    print('### Pieces per object (F-I5.4 ladder)\n')
    print('| ep | object | lathe rotc (sigma) | routes tried | delivered pieces | delivered collider / SHELL body cm3 |')
    print('|---|---|---|---|---|---|')
    print('\n'.join(obj_rows))
    print('\n### Per pair (rule as written)\n')
    print('| ep | pair | collider overlap max cm3 | gates (component: voxels, run, sweep share) | scope | receiver | c mm '
          '| overshoot frames | caps: removed cm3 (share), reach, topology | S (acceptance) | P2-P7, gate | delivered '
          '| rigid shift clears |')
    print('|---|---|---|---|---|---|---|---|---|---|---|---|---|')
    print('\n'.join(pair_rows))
    print('\n### S on the delivered pieces (diagnostic, PREREG F-I5.14 (7); decides nothing)\n')
    print('| ep | pair | receiver (fixed) | S frame | displacement mm | drop dz mm | lateral mm | tilt deg | S (4 mm, 5 deg) |')
    print('|---|---|---|---|---|---|---|---|---|')
    print('\n'.join(sink_rows))


if __name__ == '__main__':
    main()
