"""Markdown tables of the eval precheck from evalcheck_summary.json. Usage: python -I tables.py SUMMARY.json"""
import json
import sys

S = json.load(open(sys.argv[1]))['episodes']
ORDER = ['10', '1', '14', '15', '16', '30', '32', '33']
SHORT = dict(blue_cup='blue cup', beige_cup='beige cup', white_pot='pot', white_pot_lid='lid',
             plastic_dish_rack='rack', wooden_spoon='spoon', mini_sweeper='sweeper')


def v(d, cap=None):
    if d is None or d.get('max') is None:
        return '-'
    x = d['max']
    s = f'>= {cap:g}' if cap is not None and x >= cap - 1e-9 else f'{x:g}'
    return f"{s} (f{d['frame']})"


def worst(objs, key, cap=None):
    best = None
    for n, o in objs.items():
        d = o[key]
        if d.get('max') is not None and (best is None or d['max'] > best[1]['max']):
            best = (n, d)
    if best is None:
        return '-'
    return f"{v(best[1], cap)} {SHORT.get(best[0], best[0])}"


def precheck_table(key):
    print(f'| Eval | Receiver <- guest | Pieces R / G | Frames ({key}) / all | Failing: any (a table / b float / c overlap >= 1 cm3) '
          '| Max overlap, faithful 2 mm boxes, cm3 | Max overlap, packed pieces, cm3 | Max table penetration, faithful, mm '
          '| Max float, faithful, mm |')
    print('|---|---|---|---|---|---|---|---|---|')
    for ep in ORDER:
        if ep not in S:
            continue
        e = S[ep]
        b = e['precheck'][key]
        o = b['objects']
        na = sum(x['n_fail_a_table'] for x in o.values())
        nb = sum(x['n_fail_b_float'] for x in o.values())
        pcs = [x['n_pieces'] for x in e['objects']]
        names = [x['name'] for x in e['objects']]
        pr = pcs[names.index(e['receiver'])]; pg = pcs[names.index(e['guest'])]
        print(f"| {ep} | {SHORT[e['receiver']]} <- {SHORT[e['guest']]} | {pr} / {pg} | {b['frames']} / {e['frames']} | "
              f"{b['frames_failing']} ({na} / {nb} / {b['n_ov_faithful_ge1cm3']}) | {v(b['max_V_faithful_cm3'])} | "
              f"{v(b['max_V_packed_cm3'])} | {worst(o, 'max_pen_faithful_mm')} | {worst(o, 'max_float_faithful_mm', 100)} |")


def cavity_table():
    print('| Eval | Frames with the guest in the receiver\'s cavity region (>= 1 cm3), all frames / hands-off | '
          'Max guest (visual) in receiver packed pieces, cm3 | ... in receiver visual, cm3 | ... in packed pieces but '
          'outside the visual, cm3 (cavity frames >= 1 cm3) | Cavity frames with <= 0.1 cm3 in the pieces | '
          'Max depth into the pieces, mm (lower bound) | Packed collider blocks beyond the visual? |')
    print('|---|---|---|---|---|---|---|---|')
    for ep in ORDER:
        if ep not in S:
            continue
        a, h = S[ep]['cavity']['all'], S[ep]['cavity']['H0']
        print(f"| {ep} | {a['frames_guest_in_receiver_cavity']} / {h['frames_guest_in_receiver_cavity']} | "
              f"{v(a['max_V_gvis_in_rpk_cm3'])} | {v(a['max_V_gvis_in_rvis_cm3'])} | "
              f"{v(a['max_V_rpk_only_cavity_frames_cm3'])} ({a['n_cavity_frames_rpk_only_ge1cm3']}) | "
              f"{a['n_cavity_frames_rpk_le0p1cm3']} / {a['frames_guest_in_receiver_cavity']} | {v(a['max_depth_pk_mm'])} | "
              f"{'yes' if a['packed_blocks_beyond_visual'] else 'no'} |")


def contact_table():
    print('| Eval | Pieces R + G | Frame (pick, hands) | Max ncon | Max nefc | Overflow copies | At the max-nefc step: '
          'guest-receiver / guest-table / receiver-table contacts |')
    print('|---|---|---|---|---|---|---|')
    for ep in ORDER:
        if ep not in S or 'contacts' not in S[ep]:
            continue
        c = S[ep]['contacts']
        for a in c['frames']:
            cl = a['classes_at_max_nefc'] or {}
            print(f"| {ep} | {c['pieces'][0]} + {c['pieces'][1]} | f{a['frame']} ({a['kind']}, {a['hands']}) | "
                  f"{a['max_ncon']} | {a['max_nefc']} | {a['overflow_copies']} / 16 | {cl.get('guest_receiver')} / "
                  f"{cl.get('guest_table')} / {cl.get('receiver_table')} |")
        if not c['frames']:
            print(f"| {ep} | {c['pieces'][0]} + {c['pieces'][1]} | no frame with the packed colliders within 4 mm | - | - | - | - |")


for k in ('H0', 'all'):
    print(f'\n### precheck {k}\n'); precheck_table(k)
print('\n### cavity\n'); cavity_table()
print('\n### contacts\n'); contact_table()
