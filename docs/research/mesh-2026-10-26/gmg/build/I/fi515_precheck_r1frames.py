"""PREREG F-I5.15 (3) / INTERLOCK 21.13.4 last item (P77, P78; report only, decides nothing): the round-2 pose precheck
(collcarve.precheck on the faithful 2 mm SHELL boxes) at round 1's S frames, for comparison with verify_cc_1 B2.

Round 1's S frames and receivers (build/I/results/collcarve-public/README.md): ep12 f6, f176 and ep13 f146 (receiver
plastic_dish_rack), ep31 f282, f8 (plastic_dish_rack), ep11 f126 (beige_cup), ep2 f24, f328 (white_pot). Inputs as
T-I16 (v6 bundle, the round-1 CPU candidates, F-I5 body = the shell_t5p36 candidate). GT-free (no scan, mocap, parquet
pose or *_align).

  GMG_MODE=dev python docs/research/mesh-2026-10-26/gmg/build/I/fi515_precheck_r1frames.py --run <run> --v6 <bundles> \
      --cands <run>/cand/public --out <json>
"""
import argparse
import json
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
MR = os.path.abspath(os.path.join(HERE, '..', '..', '..'))
if MR not in sys.path:
    sys.path.insert(0, MR)

FRAMES = {12: ('plastic_dish_rack', 'blue_cup', [6, 176]), 13: ('plastic_dish_rack', 'blue_cup', [146]),
          31: ('plastic_dish_rack', 'mini_sweeper', [282, 8]), 11: ('beige_cup', 'blue_cup', [126]),
          2: ('white_pot', 'white_pot_lid', [24, 328])}
PRED = {(12, 6): 'a_table', (13, 146): 'a_table', (31, 282): 'b_support', (31, 8): 'b_support',
        (11, 126): 'c_overlap', (2, 24): None, (2, 328): None}       # P77 (fail check) / P78 (ep2: passes (a), (b))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--run', required=True); ap.add_argument('--v6', required=True)
    ap.add_argument('--cands', required=True); ap.add_argument('--out', required=True)
    ap.add_argument('--eps', default='12,13,31,11,2')
    a = ap.parse_args()
    from gmg import guard
    guard.set_run(a.run)
    from gmg import interlock as IL, collcarve as CC
    from gmg.tools.interlock_dev import load_mesh
    out = dict(rule='PREREG F-I5.15 (3), INTERLOCK 21.13.4 (P77, P78; report only)', episodes={})
    for ep in [int(x) for x in a.eps.split(',')]:
        recv, guest, frames = FRAMES[ep]
        b = IL.load_bundle_any(os.path.join(a.v6, f'ep{ep}'))
        bodies = {o: load_mesh(os.path.join(a.cands, f'ep{ep}', o, 'shell_t5p36.glb')) for o in (recv, guest)}
        t = time.time()
        F = {o: CC.Faithful(bodies[o]) for o in (recv, guest)}
        tb = b.meta.get('table')
        table = (__import__('numpy').asarray(tb['n'], float), float(tb['d']))
        rows = []
        for f in frames:
            r = CC.precheck(F[recv], F[guest], CC._world(b, recv, f), CC._world(b, guest, f), table, bodies[recv],
                            bodies[guest])
            pred = PRED.get((ep, f))
            if (ep, f) not in PRED:
                verdict = 'not in P77 / P78 (reported)'
            elif ep == 2:
                held = bool(r['a_table']['pass_'] and r['b_support']['pass_'])
                verdict = 'P78 holds' if held else 'P78 falsified'
            else:
                verdict = 'P77 holds' if (r['fail'] == pred and r['fails'] == [pred]) else (
                    f'P77 falsified (predicted {pred} only, got {r["fails"] or "pass"})')
            rows.append(dict(frame=f, precheck=r, predicted_fail=pred, verdict=verdict))
            print(ep, f, r['fails'], verdict, json.dumps({k: r[k] for k in ('a_table', 'b_support')}),
                  json.dumps(r['c_overlap'], default=str)[:300], flush=True)
        out['episodes'][str(ep)] = dict(receiver=recv, guest=guest, faithful_cm3={o: round(F[o].vol_cm3, 2) for o in F},
                                        faithful_boxes={o: len(F[o].boxes) for o in F}, rows=rows,
                                        sec=round(time.time() - t, 1))
        with open(a.out, 'w') as fh:
            json.dump(out, fh, indent=1, default=IL._jdefault)


if __name__ == '__main__':
    main()
