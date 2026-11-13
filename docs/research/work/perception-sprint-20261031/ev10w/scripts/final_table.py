"""Collects the PREREG readings into one JSON + markdown table (ev10w README). Inputs: out/sum_<cell>.json (intrusion +
floor gap), out/settle_<ref>_<mesh>.json (G2), out/rs_gl_ev10_*.json (M2 rigid shift), out/m2_*.json (M2 azimuth),
out/rest/*.json (rest robustness). Usage: final_table.py OUT_DIR RESULT.json"""
import sys, json, glob, os
import numpy as np
O, outp = sys.argv[1:3]
CELLS = [('gl10A2 (a)', 'ev10', 'sum_gl_ev10.json'), ('gl10A2 (a)', 'ev10w', 'sum_ev10w_gl.json'),
         ('V4p (b)', 'ev10', 'sum_ev10_v4p.json'), ('V4p (b)', 'ev10w', 'sum_ev10w_v4p.json'),
         ('stored track, no glock/ILC (control)', 'ev10', 'sum_ev10_trk.json'), ('stored track, no glock/ILC (control)', 'ev10w', 'sum_ev10w_trk.json')]
RANGES = ['f0-46', 'f47-99', 'f100-117', 'f118-160']
res = dict(cells=[], settle={}, rigid_shift=None, m2={}, rest={})
md = ['| reference | mesh | ' + ' | '.join(RANGES) + ' | G1 part (max I f100-160) |', '|---|---|' + '---|' * len(RANGES) + '---|']
for ref, mesh, f in CELLS:
    S = json.load(open(os.path.join(O, f))); row = dict(reference=ref, mesh=mesh, file=f, G1_part_pass=S['G1_part_pass'], I_max_f100_160=S['I_max_f100_160'], ranges={})
    cells = []
    for r in RANGES:
        x = S['ranges'][r]; Ii = x['I_cm3_intruding']; g = x['floor_gap_mm']
        row['ranges'][r] = dict(intruding=f"{x['intruding_frames']}/{x['frames']}", I_med=Ii['median'] if Ii else 0.0, I_max=Ii['max'] if Ii else 0.0,
                                depth_max_mm=x['depth_max_mm'], floor_gap_med_mm=g['median'] if g else None)
        q = row['ranges'][r]
        cells.append(f"{q['intruding']}; {q['I_med']} / {q['I_max']}; {q['depth_max_mm']} mm; " + (f"{q['floor_gap_med_mm']} mm" if q['floor_gap_med_mm'] is not None else 'n/a'))
    md.append(f'| {ref} | {mesh} | ' + ' | '.join(cells) + f" | {'PASS' if S['G1_part_pass'] else 'FAIL'} ({S['I_max_f100_160']}) |")
    res['cells'].append(row)
md2 = ['| reference | mesh | frames passing (f100-117 / f118-160 / all) | dz median (min) mm | tilt median (max) deg | lateral median mm |', '|---|---|---|---|---|---|']
for ref in ('gl', 'v4p'):
    for mesh in ('ev10', 'ev10w'):
        p = os.path.join(O, f'settle_{ref}_{mesh}.json')
        if not os.path.exists(p):
            continue
        S = json.load(open(p))['summary']; res['settle'][f'{ref}_{mesh}'] = S; a = S['f100-160']
        md2.append(f"| {ref} | {mesh} | {S['f100-117']['passed']}/{S['f100-117']['frames']} / {S['f118-160']['passed']}/{S['f118-160']['frames']} / "
                   f"{a['passed']}/{a['frames']} | {a['dz_mm']['median']} ({a['dz_mm']['min']}) | {a['tilt_deg']['median']} ({a['tilt_deg']['max']}) | {a['dlat_mm']['median']} |")
g = res['settle'].get('gl_ev10w', {}).get('f100-160'); g0 = res['settle'].get('gl_ev10', {}).get('f100-160')
res['G2'] = dict(ev10w_passed=g['passed'] if g else None, ev10_passed=g0['passed'] if g0 else None, frames=g['frames'] if g else None,
                 need=int(np.ceil(0.9 * g['frames'])) if g else None,
                 pass_=bool(g and g0 and g['passed'] >= np.ceil(0.9 * g['frames']) and g['passed'] >= g0['passed']))
rows = []
for f in sorted(glob.glob(os.path.join(O, 'rs_gl_ev10_1*.json'))):
    rows += json.load(open(f))['rows']
if rows:
    rows.sort(key=lambda r: r['frame'])
    def frac(lo, hi, key):
        rr = [r for r in rows if lo <= r['frame'] <= hi]
        return dict(frames=len(rr), cleared=sum(r[key] is not None for r in rr))
    res['rigid_shift'] = dict(frames=[r['frame'] for r in rows],
                              clear_le2={k: frac(lo, hi, 'clear_le2') for k, lo, hi in (('f100-117', 100, 117), ('f118-160', 118, 160), ('f100-160', 100, 160))},
                              clear_0={k: frac(lo, hi, 'clear_0') for k, lo, hi in (('f100-117', 100, 117), ('f118-160', 118, 160), ('f100-160', 100, 160))},
                              translation_only_min_I_median=dict(f100_117=float(np.median([r['translation_only_min_I'] for r in rows if r['frame'] <= 117])),
                                                                 f118_160=float(np.median([r['translation_only_min_I'] for r in rows if r['frame'] >= 118]))),
                              clear_le2_shift_mm_median=float(np.median([r['clear_le2']['shift_mm'] for r in rows if r['clear_le2']])) if any(r['clear_le2'] for r in rows) else None,
                              clear_le2_tilt_deg_median=float(np.median([r['clear_le2']['tilt_deg'] for r in rows if r['clear_le2']])) if any(r['clear_le2'] for r in rows) else None,
                              grid_vs_exact_I_max_abs_diff=float(max(abs(r['I_grid_ref'] - r['I_exact_ref']) for r in rows)),
                              rows=rows)
for f in sorted(glob.glob(os.path.join(O, 'm2_*.json'))):
    res['m2'][os.path.basename(f)[:-5]] = json.load(open(f))['summary']
for f in sorted(glob.glob(os.path.join(O, 'rest', '*.json'))):
    d = json.load(open(f)); S = d['series']
    res['rest'][os.path.basename(f)[:-5]] = dict(nan_at_frame=d['nan_at_frame'], max_blue_deg=max(r['blue_cup'][1] for r in S),
                                                 max_beige_deg=max(r['beige_cup'][1] for r in S), max_blue_cm=max(r['blue_cup'][0] for r in S),
                                                 max_beige_cm=max(r['beige_cup'][0] for r in S),
                                                 rel_end=S[-1].get('rel'), collide_shapes=d['collide_shapes'])
res['markdown_intrusion'] = md; res['markdown_settle'] = md2
json.dump(res, open(outp, 'w'), indent=1)
print('\n'.join(md)); print(); print('\n'.join(md2)); print(); print('G2', res['G2'])
if res['rigid_shift']:
    print('rigid shift', json.dumps({k: v for k, v in res['rigid_shift'].items() if k != 'rows'}))
for k, v in res['rest'].items():
    print('rest', k, v)
