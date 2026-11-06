"""README tables from the measurement JSONs. Usage: tables.py MEAS_DIR SET[,SET...]   (SET: packed, c1-ev30, ...)
Expects MEAS_DIR/<set>_geo.json and MEAS_DIR/<set>_phys<ep>.json."""
import json, os, sys
import numpy as np

md, sets = sys.argv[1], sys.argv[2].split(',')
V = lambda b: 'pass' if b else 'FAIL'
for ep in ('30', '14'):
    rows = []
    for s in sets:
        g = f'{md}/{s}_geo.json'; p = f'{md}/{s}_phys{ep}.json'
        if not os.path.exists(g):
            continue
        G = json.load(open(g))
        if ep not in G['eps']:
            continue
        e = G['eps'][ep]
        P = json.load(open(p)) if os.path.exists(p) else None
        g1, g1x, g2, g5 = e['G1'], e['G1x'], e['G2'], e['G5']
        r = dict(set=s, n=G['n_pieces'],
                 g1=f"{g1['median']:.1f} / {g1['max']:.1f} ({'FAIL, pose floor' if g1['floor_blocks'] and not g1['pass_'] else V(g1['pass_'])})",
                 floor=f"{g1['floor_vv_median']:.1f} / {g1['floor_vv_max']:.1f}; {g1['floor_pm_median']:.1f} / {g1['floor_pm_max']:.1f}",
                 g1x=f"{g1x['median']:.2f} / {g1x['max']:.2f} ({V(g1x['pass_'])})",
                 g2=f"{g2['swept_cm3']:.2f} ({V(g2.get('pass_as_written', g2['swept_cm3'] <= 1.0))}); "
                    f"G2b {g2.get('G2b_beyond_band_cm3', float('nan')):.2f} ({V(g2['pass_'])}); per frame "
                    f"{g2['per_frame_max_guest_packed']:.2f} / {g2['per_frame_max_guest_mesh']:.2f}",
                 g5=f"{g5['kept_ratio']:.3f} ({V(g5['pass_'])}); lost {g5['lost_cm3']:.1f}, new {g5['added_outside_packed_cm3']:.2f}",
                 c=f"C1 {V(G['C1']['pass_'])}, C2 {V(G['C2']['pass_'])} ({G['C2'].get('mesh_cells_lost_cm3')} cm3, "
                   f"{G['C2'].get('max_out_mm', 0)} mm), C3 {V(G['C3']['pass_'])}")
        if P:
            fr = P['frames']
            r['g3'] = ', '.join(f"f{x['frame']} {x['G3']['max_nefc']}/{x['G3']['max_ncon']}"
                                + (f" ovf {x['G3']['overflow_copies']}" if x['G3']['overflow_copies'] else '') for x in fr) \
                + f" ({V(P['G3_pass'])})"
            r['g4'] = ', '.join(f"f{x['frame']} {x['G4'].get('disp_mm', float('nan')):.0f} mm / {x['G4'].get('tilt_deg', float('nan')):.0f} deg"
                                + (' fall' if x['G4']['fall_through'] else '') for x in fr) + f" ({V(P['G4_pass'])})"
            pg = [x['G6']['pair_guest_disp_median_mm'] for x in fr]; sg = [x['G6']['S_guest_disp_median_mm'] for x in fr]
            r['g6'] = (', '.join(f"f{x['frame']} {a:.0f}" for x, a in zip(fr, pg)) + f" (median {np.median(pg):.0f}); S "
                       + ', '.join(f"{a:.0f}" for a in sg) + f" (median {np.median(sg):.0f})")
            r['g6_med'] = (float(np.median(pg)), float(np.median(sg)))
        rows.append(r)
    if not rows:
        continue
    print(f'\n### Eval {ep}\n')
    print('| Set | Pieces | G1 V_pp median / max, cm3 | Floors V_vv; V_pm (median / max) | G1x median / max | G2 swept as written; G2b; per-frame max (guest pieces / mesh) | G3 max nefc / ncon per frame (plain MuJoCo, indicative) | G4 S mean displacement / tilt | G5 kept | G6 throw: pair-scene guest median, mm; S median | C1-C3 |')
    print('|---|---|---|---|---|---|---|---|---|---|---|')
    for r in rows:
        print(f"| {r['set']} | {r['n']} | {r['g1']} | {r['floor']} | {r['g1x']} | {r['g2']} | {r.get('g3', '-')} | {r.get('g4', '-')} | {r['g5']} | {r.get('g6', '-')} | {r['c']} |")
