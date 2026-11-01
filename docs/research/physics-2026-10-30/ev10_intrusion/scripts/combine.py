"""Per-frame CSV + range summary JSON for the ev10 intrusion diagnostic (all inputs in ev10_intrusion/out). DIAGNOSTIC."""
import json, csv, sys, numpy as np
E = sys.argv[1]; O = f'{E}/out'
RANGES = [('f0-37', 0, 37), ('f38-46', 38, 46), ('f47-99', 47, 99), ('f100-117', 100, 117), ('f118-160', 118, 160)]
G = json.load(open(f'{O}/gap_ev10.json')); V = json.load(open(f'{O}/vpush_ev10.json'))
def tool(tag):
    Z = np.load(f'{O}/DIAG_{tag}.npz'); H = json.load(open(f'{O}/DIAG_{tag}.json')); T = H['frames']
    names = [str(x) for x in Z['objects']]
    fr, tg, dep = Z['frame'], Z['target'], Z['depth_m']; fpF, fpT, vol = Z['fp_frame'], Z['fp_target'], Z['intr_vol_m3']
    per = {}
    for t, key in ((names.index('blue_cup'), 'beige_in_blue'), (names.index('beige_cup'), 'blue_in_beige')):
        v = np.zeros(T); dmax = np.zeros(T); dmed = np.zeros(T)
        for i in np.nonzero(fpT == t)[0]:
            v[fpF[i]] = vol[i] * 1e6
        for f in np.unique(fr[tg == t]):
            d = dep[(fr == f) & (tg == t)]; dmax[f] = d.max() * 1e3; dmed[f] = np.median(d) * 1e3
        per[key] = (v, dmax, dmed)
    push = {}
    for r in H.get('diagnostic_push', {}).get('rows', []):
        if r['n_samples'] and 'push_mm' in r:
            push.setdefault(r['frame'], []).append((r['push_mm'], r['blue_shift_up_cos'], r['blue_shift_dir_blueframe']))
    return T, per, push
out_rows, summary = [], {}
T, tA, pA = tool('A_carve_ev10'); _, tB, _ = tool('B_libv3_decomp')
XB = G['B_libv3_mesh_exact_intrusion']['rows']
for f in range(T):
    pa = max(pA.get(f, [(0.0, np.nan, None)]), key=lambda x: x[0])     # separation needs both orders: the larger push
    ga, gb = G['A_carve_ev10'][1][f], G['B_libv3_mesh'][1][f]
    out_rows.append(dict(frame=f,
        A_beige_in_blue_cm3=tA['beige_in_blue'][0][f], A_beige_in_blue_dmax_mm=tA['beige_in_blue'][1][f],
        A_blue_in_beige_cm3=tA['blue_in_beige'][0][f], A_blue_in_beige_dmax_mm=tA['blue_in_beige'][1][f],
        A_push_min_mm=pa[0], A_push_blue_up_cos=pa[1], A_push_blue_dir_blueframe=pa[2],
        A_vpush_beige_up_mm=V['A_carve_ev10'][f]['beige_up_mm'], A_vpush_beige_down_mm=V['A_carve_ev10'][f]['beige_down_mm'],
        A_floor_gap_mm=ga['floor_gap_mm'] if ga['over_floor'] else np.nan,
        Bd_beige_in_blue_cm3=tB['beige_in_blue'][0][f], Bd_beige_in_blue_dmax_mm=tB['beige_in_blue'][1][f],
        Bd_blue_in_beige_cm3=tB['blue_in_beige'][0][f], Bd_blue_in_beige_dmax_mm=tB['blue_in_beige'][1][f],
        Bd_vpush_beige_up_mm=V['B_libv3_decomp'][f]['beige_up_mm'], Bd_vpush_beige_down_mm=V['B_libv3_decomp'][f]['beige_down_mm'],
        Bm_beige_in_blue_cm3=XB[f]['beige_in_blue_vol_cm3'], Bm_beige_in_blue_dmax_mm=XB[f]['beige_in_blue_depth_max_mm'],
        Bm_blue_in_beige_cm3=XB[f]['blue_in_beige_vol_cm3'], Bm_blue_in_beige_dmax_mm=XB[f]['blue_in_beige_depth_max_mm'],
        Bm_vpush_beige_up_mm=V['B_libv3_mesh'][f]['beige_up_mm'], Bm_vpush_beige_down_mm=V['B_libv3_mesh'][f]['beige_down_mm'],
        Bm_floor_gap_mm=gb['floor_gap_mm'] if gb['over_floor'] else np.nan))
with open(f'{O}/ev10_intrusion_per_frame.csv', 'w', newline='') as fh:
    w = csv.DictWriter(fh, fieldnames=list(out_rows[0])); w.writeheader()
    for r in out_rows:
        w.writerow({k: (round(v, 3) if isinstance(v, float) else v) for k, v in r.items()})
def stats(x):
    x = np.asarray([v for v in x if np.isfinite(v)], float)
    return None if not len(x) else dict(min=round(float(x.min()), 2), median=round(float(np.median(x)), 2), max=round(float(x.max()), 2))
for lab, a, b in RANGES:
    rs = out_rows[a:b + 1]; S = {}
    for k in ('A', 'Bd', 'Bm'):
        S[k] = {}
        for pair in ('beige_in_blue', 'blue_in_beige'):
            m = [r for r in rs if r[f'{k}_{pair}_cm3'] > 0]
            S[k][pair] = dict(frames=len(m), vol_cm3=stats([r[f'{k}_{pair}_cm3'] for r in m]), depth_max_mm=stats([r[f'{k}_{pair}_dmax_mm'] for r in m]))
        S[k]['vpush_beige_up_mm (= blue down)'] = stats([r[f'{k}_vpush_beige_up_mm'] for r in rs if r[f'{k}_vpush_beige_up_mm'] > 0])
        S[k]['vpush_beige_down_mm (= blue up)'] = stats([r[f'{k}_vpush_beige_down_mm'] for r in rs if r[f'{k}_vpush_beige_down_mm'] > 0])
    S['A']['push_min_mm'] = stats([r['A_push_min_mm'] for r in rs if r['A_push_min_mm'] > 0])
    S['A']['push_blue_up_cos'] = stats([r['A_push_blue_up_cos'] for r in rs if r['A_push_min_mm'] > 0])
    S['A']['floor_gap_mm'] = stats([r['A_floor_gap_mm'] for r in rs]); S['Bm']['floor_gap_mm'] = stats([r['Bm_floor_gap_mm'] for r in rs])
    summary[lab] = S
json.dump(dict(DIAGNOSTIC='GT-free consistency check of our eval-10 reference; not contract-valid; no score', T=T,
               keys=dict(A='carved pieces meshes/carve/ev10 (intrusion.py via diagnostic wrapper)',
                         Bd='collision_decomp pieces of library_v3 (blue cup: one stuck piece fills the cavity)',
                         Bm='plain library_v3 meshes, exact winding-number SDF'),
               ranges=summary), open(f'{O}/ev10_intrusion_summary.json', 'w'), indent=1)
print(json.dumps(summary, indent=None)[:6000])
