"""PREREG F-I4.16.3 (a): byte comparison of the fi4p round folder with round-2 r0 (fi4o). Every piece file (top-level
<obj>/piece_XX.obj of both boards and _default/<obj>/piece_XX.obj) by sha256; the other files listed with equal / differ
(the visual, props and manifest carry the run's code identity and records, so they are expected to differ in places).
Also the chosen rung per board, the slot-centre and coverage reports from the fi4p decisions.

  python fi416_ep24_cmp.py <fi4p r0 dir> <round-2 r0 dir> <fi4p decisions.json> <out json>
Decides nothing beyond the F-I4.16.3 (a) byte rule. GT-free (our own outputs only)."""
import hashlib
import json
import os
import sys

new, old, dec_p, out_p = sys.argv[1:5]


def files(d):
    out = {}
    for root, _, fs in os.walk(d):
        for f in fs:
            p = os.path.join(root, f)
            out[os.path.relpath(p, d)] = hashlib.sha256(open(p, 'rb').read()).hexdigest()
    return out


A, B = files(new), files(old)
piece = lambda k: os.path.basename(k).startswith('piece_') and k.endswith('.obj')
pa, pb = {k for k in A if piece(k)}, {k for k in B if piece(k)}
diff = sorted(k for k in pa & pb if A[k] != B[k])
res = dict(rule='F-I4.16.3 (a): rung 1.0 on both boards -> every piece file byte-identical (sha256) to round-2 r0',
           new=new, old=old, pieces_new=len(pa), pieces_old=len(pb), only_new=sorted(pa - pb), only_old=sorted(pb - pa),
           pieces_differ=diff, pieces_identical=bool(pa == pb and not diff),
           other_files={k: ('equal' if A.get(k) == B.get(k) else 'differ' if k in A and k in B else
                            'only_new' if k in A else 'only_old') for k in sorted((set(A) | set(B)) - pa - pb)})
dec = [r for r in json.load(open(dec_p)) if r.get('waiver_fi4')]
W = dec[0]['waiver_fi4'] if dec else {}
res['decisions'] = {r['target']: [r['decision'], r['tier']] for r in dec if r.get('voxels', 0) >= 10}
res['gate_fail'] = W.get('gate_fail')
res['fi4_rev'] = W.get('fi4_rev')
res['boards'] = {}
for x, bd in (W.get('body') or {}).items():
    lad = bd.get('ladder') or {}
    sl = (W.get('slot') or {}).get(x) or {}
    res['boards'][x] = dict(chosen_eps_mm=lad.get('chosen_eps_mm'),
                            ladder=[{k: q.get(k) for k in ('eps_mm', 'simple', 'fits', 'vertices', 'reflex_vertices',
                                                           'default_prisms', 'slotted_prisms', 'area_cm2', 'd_max_mm',
                                                           'end_minus_waist_mm')} for q in lad.get('rows', [])],
                            free_share_rung_1_0=lad.get('free_share_rung_1_0'),
                            free_share=(bd.get('free_share') or {}).get('polygon'),
                            coverage=bd.get('coverage'), coverage_report=bd.get('coverage_report'),
                            default_pieces=(bd.get('default_pieces') or {}).get('n'),
                            slotted_pieces=(bd.get('slotted_pieces') or {}).get('n'),
                            slot=dict(w_mm=sl.get('w_mm'), c_L_mm=sl.get('c_L_mm'), D_mm=sl.get('D_mm'),
                                      u_e_poly_mm=sl.get('u_e_poly_mm'), bottom_mm=sl.get('bottom_mm')),
                            slot_centre={k: v for k, v in (sl.get('slot_centre') or {}).items()
                                         if not k.endswith('per_mm')},
                            slot_centre_profile={k: v for k, v in (sl.get('slot_centre') or {}).items()
                                                 if k.endswith('per_mm') or k == 'bins_from_mm'})
man = os.path.join(new, 'manifest.json')
if os.path.exists(man):
    m = json.load(open(man))
    ow = m.get('owner_waiver') or {}
    res['manifest'] = dict(p1_pending=m.get('p1_pending'), delivered=(m.get('interlock') or {}).get('delivered'),
                           slot_centre_disagrees=ow.get('slot_centre_disagrees'), fi416=ow.get('fi416'),
                           fi4_rev=ow.get('fi4_rev'), do_not_use=m.get('do_not_use'))
json.dump(res, open(out_p, 'w'), indent=1)
print(json.dumps({k: v for k, v in res.items() if k not in ('other_files', 'boards')}, indent=1)[:3000])
for x, v in res['boards'].items():
    print(x, 'eps', v['chosen_eps_mm'], 'pieces', v['default_pieces'], v['slotted_pieces'], 'slot centre',
          {k: v['slot_centre'].get(k) for k in ('applicable', 'observable', 'n_points', 'u_obs_mm', 'c_L_mm', 'delta_mm',
                                                'run_mm', 'slot_centre_disagrees')}, 'coverage', v['coverage_report'])
