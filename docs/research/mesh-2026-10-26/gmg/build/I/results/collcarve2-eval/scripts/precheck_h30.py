"""verify_cc2_1 B2 fix (1 Nov, Eval-carves step): the eval precheck's tables on the RULE's hands-off set H30 (no robot
hand point within 30 mm of either object, PREREG F-I5.3 (b) / F-I5.16 (3)(a)) instead of H0 (no contact label).
Recomputed from the evalcheck's own per-frame records with its own summarize.block / summarize.cavity (no new
measurement, no threshold changed). Also lists, for the contact-count frames, whether each is H30.
Usage: python -I precheck_h30.py EVALCHECK_DIR OUT.json > tables.md"""
import importlib.util
import json
import os
import sys

import numpy as np

ev = sys.argv[1]
spec = importlib.util.spec_from_file_location('ecsum', os.path.join(ev, 'scripts', 'summarize.py'))
SM = importlib.util.module_from_spec(spec)
spec.loader.exec_module(SM)
S = json.load(open(os.path.join(ev, 'evalcheck_summary.json')))['episodes']
ORDER = ['10', '1', '14', '15', '16', '30', '32', '33']
SHORT = dict(blue_cup='blue cup', beige_cup='beige cup', white_pot='pot', white_pot_lid='lid',
             plastic_dish_rack='rack', wooden_spoon='spoon', mini_sweeper='sweeper')
out = dict(_note='H30 = no robot hand point within 30 mm of either object (rule); H0 = no contact label (evalcheck '
           'primary set). Recomputed from per_frame/*.json with the evalcheck summarize.py; diagnostic only.',
           episodes={})


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
    return '-' if best is None else f"{v(best[1], cap)} {SHORT.get(best[0], best[0])}"


rows_md = []
for ep in ORDER:
    fr = json.load(open(os.path.join(ev, 'per_frame', f'ep{ep}_frames.json')))
    s, pf = fr['summary'], fr['per_frame']
    names = s['names']
    R = pf['rows']
    H0 = np.array([r['H0'] for r in R]); H30 = np.array([r['H30'] for r in R])
    b30, b0 = SM.block(pf, names, H30), SM.block(pf, names, H0)
    c30 = SM.cavity(pf, H30)
    # hand distance on the H0 frames that are not H30 (the verifier's point: a hand near the object, no label)
    h0_not30 = [r['frame'] for r in R if r['H0'] and not r['H30']]
    hmin = [min(r['hand_min_mm']) for r in R if r['H0'] and not r['H30']]
    cf = []
    for a in (S[ep].get('contacts') or {}).get('frames', []):
        f = int(a['frame'])
        cf.append(dict(frame=f, kind=a['kind'], hands_label=a['hands'], H0=bool(R[f]['H0']), H30=bool(R[f]['H30']),
                       hand_min_mm=R[f]['hand_min_mm'], max_nefc=a['max_nefc'], max_ncon=a['max_ncon'],
                       overflow_copies=a['overflow_copies']))
    na = sum(x['n_fail_a_table'] for x in b30['objects'].values())
    nb = sum(x['n_fail_b_float'] for x in b30['objects'].values())
    out['episodes'][ep] = dict(receiver=s['receiver'], guest=s['guest'], frames=s['frames'], n_H0=int(H0.sum()),
                               n_H30=int(H30.sum()), n_H0_not_H30=len(h0_not30),
                               hand_min_mm_on_H0_not_H30=dict(min=min(hmin) if hmin else None,
                                                              max=max(hmin) if hmin else None),
                               H30=b30, H0_failing=b0['frames_failing'], cavity_H30=c30, contact_frames=cf)
    rows_md.append(f"| {ep} | {SHORT[s['receiver']]} <- {SHORT[s['guest']]} | {b30['frames_failing']} / {int(H30.sum())} "
                   f"({na} / {nb} / {b30['n_ov_faithful_ge1cm3']}) | {b0['frames_failing']} / {int(H0.sum())} | "
                   f"{v(b30['max_V_faithful_cm3'])} | {v(b30['max_V_packed_cm3'])} | "
                   f"{worst(b30['objects'], 'max_pen_faithful_mm')} | {worst(b30['objects'], 'max_float_faithful_mm', 100)} | "
                   f"{c30['frames_guest_in_receiver_cavity']} | {v(c30['max_V_rpk_only_cavity_frames_cm3'])} "
                   f"({c30['n_cavity_frames_rpk_only_ge1cm3']}) | "
                   + ', '.join(f"f{x['frame']} {'H30' if x['H30'] else ('H0 only' if x['H0'] else 'in hand')} "
                               f"{x['max_nefc']} rows {x['overflow_copies']}/16" for x in cf) + ' |')
json.dump(out, open(sys.argv[2], 'w'), indent=1)
print('| Eval | Receiver <- guest | H30 frames failing / H30 frames (a table / b float / c overlap >= 1 cm3) | '
      '(was) H0 failing / H0 | Max overlap, faithful, cm3 (H30) | Max overlap, packed, cm3 (H30) | '
      'Max table penetration, faithful, mm (H30) | Max float, faithful, mm (H30) | H30 frames with the guest in the '
      'receiver cavity (>= 1 cm3) | Max in packed pieces but outside the visual, cm3, H30 cavity frames (frames >= 1 cm3) | '
      'Contact-count frames: hands set, max rows, copies over 512 |')
print('|---|---|---|---|---|---|---|---|---|---|---|')
print('\n'.join(rows_md))
