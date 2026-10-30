"""Markdown tables for FRAMES.md from xstar_geom.json, xstar_trk.json and frames_check.json (this folder). ORACLE SIDE:
the inputs hold mocap-derived scores; public episodes only.
Usage: python -I frames_tables.py [DIR]
(2026-10-30)
"""
import json, os, sys
import numpy as np

D = sys.argv[1] if len(sys.argv) > 1 else os.path.dirname(os.path.abspath(__file__))
g = json.load(open(f'{D}/xstar_geom.json')); t = json.load(open(f'{D}/xstar_trk.json')); f = json.load(open(f'{D}/frames_check.json'))
eps = sorted(f['episodes'], key=int)

print('### X\\*_geom per object\n')
print('| object | symmetry | rot / shift vs lib frame | sym. surface distance mm (trim 90 %) | p90 lib→scan / scan→lib mm | RMS ratio scan/lib '
      '| 2nd minimum: residual ratio, rot, ADD | reseed ADD cm | E = X\\*_geom X_kit⁻¹ over eps: ADD cm, rot ° |')
print('|---|---|---|---|---|---|---|---|---|')
for n, o in g['objects'].items():
    m = o['minima'][1] if len(o['minima']) > 1 else None
    riv = '–' if m is None else f"{m['ratio_to_best']:.3f}, {m['rot_from_best_deg']:.0f}°, {m['add_from_best_cm']:.2f} cm"
    E = [v[n]['E_xstar_inv_kit'] for v in g['kit_registration'].values() if n in v]
    rk = 'axis_tilt_deg' if o['symmetry'] == 'cup axis' else 'rot_deg'      # a cup's spin is not scored: show its tilt
    r = o['residual']
    print(f"| {n} | {o['symmetry']} | {o['rot_deg']:.2f}° / {o['shift_cm']:.2f} cm | {r['sym_mm']:.2f} ({r['sym_trim90_mm']:.2f}) "
          f"| {r['lib_to_scan_p90_mm']:.1f} / {r['scan_to_lib_p90_mm']:.1f} | {o['rms_radius_ratio_scan_over_lib']:.3f} "
          f"| {riv}{' **ambiguous**' if o['ambiguous'] else ''} | {o['reseed_add_cm_max']:.3f} "
          f"| {min(e['sym_add_cm'] for e in E):.2f}–{max(e['sym_add_cm'] for e in E):.2f}, {min(e[rk] for e in E):.1f}–{max(e[rk] for e in E):.1f}"
          f"{' (tilt)' if rk == 'axis_tilt_deg' else ''} |")
for n, o in g['objects'].items():
    if 'spin_profile_mm' in o:
        p = o['spin_profile_mm']
        print(f"\n{n}: spin profile (residual vs spin about the scan axis, 10° steps, no refit) {p['min']:.2f}–{p['max']:.2f} mm, argmin {p['argmin_deg']}°")
    if 'flipped_sym_mm' in o:
        print(f"\n{n}: residual after the 180° flip about the normal {o['flipped_sym_mm']:.2f} mm (best {o['residual']['sym_mm']:.2f})")

print('\n### Tests and the three scoring columns per episode (refine/in tracks)\n')
print('| ep | objects | (a1) | (a2) | (a3) official / in process | round trip f32 / f64 | (b1) T\\* file / in process / budget scan '
      '| lib file / in process | (b2) spin max abs Δ | T_lib | T\\* | T_trk (pick) | T_trk_ls | L1 = T_lib − T\\* | bias = T_trk − T\\* |')
print('|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|')
L1, bias = {}, {}
for e in eps:
    r = f['episodes'][e]; x = t['episodes'][e]; s = x['scores']; a = r['a_official_AUC']; rt = r['a4_round_trip']; b = r['b1_star']
    sp = [abs(v['delta']) for v in r.get('b2_spin', {}).values()] + [abs(q) for v in r.get('b2_spin', {}).values() for q in v['delta_per_obj'].values()]
    L1[e] = s['lib']['AUC'] - s['star']['AUC']; bias[e] = s['trk']['AUC'] - s['star']['AUC']
    print(f"| {e} | {' + '.join(r['objects'])} | {a['a1_mocap_scan_mesh']:.4f} | {a['a2_mocap_at_Xkit_lib_mesh']:.4f} "
          f"| {a['a3_mocap_at_Xgeom_lib_mesh']:.4f} / {r['a3_inprocess']['AUC']:.4f} | {rt['poses_npz_max_abs']:.0e} / {rt['world_vo_max_abs']:.0e} "
          f"| {b['way1_file_full_scan']['AUC']:.4f} / {b['way2_inprocess_X']['AUC']:.4f} / {b['way1b_score_registered_budget_scan']['AUC']:.4f} "
          f"| {r['b0_lib']['score_registered']['AUC']:.4f} / {r['b0_lib']['inprocess']['AUC']:.4f} | {f'{max(sp):.4f}' if sp else '–'} "
          f"| {s['lib']['AUC']:.4f} | {s['star']['AUC']:.4f} | {s['trk']['AUC']:.4f} ({x['fit']['picked']}) | {s['trk_ls']['AUC']:.4f} "
          f"| {L1[e]:+.4f} | {bias[e]:+.4f} |")
ex = [e for e in eps if e != '23']
col = lambda k, E: float(np.mean([t['episodes'][e]['scores'][k]['AUC'] for e in E]))
print(f"\nMeans over {len(eps)} eps: T_lib {col('lib', eps):.4f}, T\\* {col('star', eps):.4f}, T_trk {col('trk', eps):.4f}, "
      f"T_trk_ls {col('trk_ls', eps):.4f}; L1 {np.mean(list(L1.values())):+.4f} ({sum(v > 0 for v in L1.values())} eps > 0, "
      f"{sum(v < 0 for v in L1.values())} < 0); bias {np.mean(list(bias.values())):+.4f}.")
print(f"Without ep23 (identity swap): T_lib {col('lib', ex):.4f}, T\\* {col('star', ex):.4f}, T_trk {col('trk', ex):.4f}, "
      f"T_trk_ls {col('trk_ls', ex):.4f}; L1 {np.mean([L1[e] for e in ex]):+.4f}; bias {np.mean([bias[e] for e in ex]):+.4f}.")
a3 = [f['episodes'][e]['a_official_AUC']['a3_mocap_at_Xgeom_lib_mesh'] for e in eps]
print(f"(a3) perfect motion under the lib convention: mean {np.mean(a3):.4f}, min {min(a3):.4f}, {sum(v < 0.9995 for v in a3)}/{len(a3)} eps < 1.")

print('\n### L1 per object (T_lib − T\\*, per-object AUC)\n')
po = {}
for e in eps:
    s = t['episodes'][e]['scores']
    for n in s['lib']['per_obj_AUC']:
        po.setdefault(n, []).append((int(e), s['lib']['per_obj_AUC'][n] - s['star']['per_obj_AUC'][n]))
print('| object | eps | mean | min | max | eps with \\|L1\\| ≥ 0.03 |')
print('|---|---|---|---|---|---|')
for n, v in sorted(po.items()):
    d = [x for _, x in v]
    print(f"| {n} | {len(v)} | {np.mean(d):+.4f} | {min(d):+.4f} | {max(d):+.4f} | {', '.join(f'{e} ({x:+.3f})' for e, x in v if abs(x) >= 0.03) or '–'} |")

print('\n### X\\*_trk: offset from X\\*_geom (symmetry-aware ADD, cm) and perceived rotation span\n')
print('| ep | picked | rejected (> 5 cm) | per object: trk vs geom ADD cm, rot ° [track rot span °] |')
print('|---|---|---|---|')
for e in eps:
    x = t['episodes'][e]
    print(f"| {e} | {x['fit']['picked']} | {', '.join(x['fit']['rejected_over_cap']) or '–'} | "
          + '; '.join(f"{n} {o['trk_vs_geom']['sym_add_cm']:.2f}, {o['trk_vs_geom']['rot_deg']:.1f} [{x['fit']['track_rot_span_deg'][n]:.0f}]"
                      for n, o in x['objects'].items()) + ' |')

print('\n### (b3) rival surface-fit minima scored on the tracks (per-object ΔAUC vs the best)\n')
print('| rival | residual ratio | rot from best | ADD from best | eps | mean Δ | min | max |')
print('|---|---|---|---|---|---|---|---|')
for k, v in f['summary']['b3_rivals'].items():
    n, i = k.split('#'); m = g['objects'][n]['minima'][int(i)]
    print(f"| {k} | {m['ratio_to_best']:.3f} | {m['rot_from_best_deg']:.0f}° | {m['add_from_best_cm']:.2f} cm | {v['n_eps']} | {v['mean_delta_obj']:+.4f} "
          f"| {v['min']:+.4f} | {v['max']:+.4f} |")
print('\n### summary (frames_check.json)\n')
print('```\n' + json.dumps({k: v for k, v in f['summary'].items() if k != 'b3_rivals'}, indent=1) + '\n```')
