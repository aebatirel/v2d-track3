"""C0 AUC guard: markdown tables for AUC_RESULTS.md (formatting only; the verdict is guard_eval.py's).

Reads the score_registered.py run JSONs (RUNS/<tag>/ep<e>.json) and guard_result.json, prints markdown tables:
  1. per twin x run: episode-level perception AUC, SP-SR, MP-SR, RPE, MPPE (4-decimal values as written), plus the
     per-object AUC and registration (rot deg, anchor shift cm) of the swapped object(s);
  2. per object: per-twin deltas single - base, mean/min, the rule checks and the verdict (copied from guard_result);
  3. joint c0 - base deltas over all 15 twins (reported only).
Usage: python -I report_auc.py RUNS_DIR GUARD_JSON > tables.md
"""
import json
import os
import sys

RUNS, GUARD = sys.argv[1], sys.argv[2]
TWINS = [0, 2, 11, 12, 13, 21, 22, 26, 27, 31, 41, 42, 43, 44, 45]
OTW = {'white_pot': [0, 2, 26, 27, 41, 42, 43, 44, 45], 'white_pot_lid': [0, 2],
       'plastic_dish_rack': [12, 13, 26, 27, 31], 'blue_cup': [11, 12, 13, 21, 22]}
SWAPPED = list(OTW)
KEYS = ['AUC', 'SP_SR', 'MP_SR', 'RPE_cm', 'MPPE_cm']
G = json.load(open(GUARD))


def load(tag, e):
    p = f'{RUNS}/{tag}/ep{e}.json'
    return json.load(open(p)) if os.path.exists(p) else None


f4 = lambda x: 'NA' if x is None else f'{x:.4f}'
s4 = lambda x: 'NA' if x is None else f'{x:+.4f}'

print('### Table 1. Per twin x run (perception track, episode-level registered scores)\n')
print('Swapped-object columns: per-object AUC and registration (rotation deg / anchor shift cm) of each swapped '
      'object present in the episode.\n')
print('| ep | run | AUC | SP-SR | MP-SR | RPE cm | MPPE cm | swapped objects in episode: per-obj AUC, reg rot deg / shift cm |')
print('|---|---|---|---|---|---|---|---|')
for e in TWINS:
    runs = ['base', 'c0'] + [f'single_{o}' for o in SWAPPED if e in OTW[o]]
    for t in runs:
        r = load(t, e)
        if r is None:
            print(f'| {e} | {t} | MISSING | | | | | |')
            continue
        p = r['perception']
        sw = '; '.join(f"{o} {f4(p['per_obj_AUC'][o])}, {r['registration'][o]['rot_deg']:.2f} / "
                       f"{r['registration'][o]['anchor_shift_cm']:.2f}" for o in SWAPPED if o in r['objects'])
        print(f"| {e} | {t} | {f4(p['AUC'])} | {f4(p['SP_SR'])} | {f4(p['MP_SR'])} | {f4(p['RPE_cm'])} | "
              f"{f4(p['MPPE_cm'])} | {sw} |")

print('\n### Table 2. Per-object deltas (single swap - base) and verdicts\n')
for o, v in G['objects'].items():
    print(f"#### {o} (twins {v['twins']}; missing {v['missing']})\n")
    print('| ep | dAUC | dSP-SR | dMP-SR | dRPE cm | dMPPE cm | obj AUC base -> swap | reg base rot/shift -> swap rot/shift |')
    print('|---|---|---|---|---|---|---|---|')
    for r in v['per_twin']:
        rb, rs = r['registration_base'][o], r['registration_swap'][o]
        print(f"| {r['ep']} | {s4(r['dAUC'])} | {s4(r['dSP_SR'])} | {s4(r['dMP_SR'])} | {s4(r['dRPE_cm'])} | "
              f"{s4(r['dMPPE_cm'])} | {f4(r['per_obj_AUC_base'][o])} -> {f4(r['per_obj_AUC_swap'][o])} | "
              f"{rb['rot_deg']:.2f}/{rb['anchor_shift_cm']:.2f} -> {rs['rot_deg']:.2f}/{rs['anchor_shift_cm']:.2f} |")
    print(f"| **mean** | {s4(v['mean_dAUC'])} | {s4(v['mean_dSP_SR'])} | {s4(v['mean_dMP_SR'])} | "
          f"{s4(v['mean_dRPE_cm'])} | {s4(v['mean_dMPPE_cm'])} | | |")
    print(f"| **min** | {s4(v['min_dAUC'])} | {s4(v['min_dSP_SR'])} | {s4(v['min_dMP_SR'])} | "
          f"{s4(v['min_dRPE_cm'])} | {s4(v['min_dMPPE_cm'])} | | |")
    print(f"| **max** | {s4(v['max_dAUC'])} | {s4(v['max_dSP_SR'])} | {s4(v['max_dMP_SR'])} | "
          f"{s4(v['max_dRPE_cm'])} | {s4(v['max_dMPPE_cm'])} | | |")
    c = v['checks']
    print(f"\nChecks: mean dAUC >= -0.005: **{c['mean_dAUC']}**; min dAUC >= -0.02: **{c['min_dAUC']}**; "
          f"mean dMPPE <= +0.2 cm: **{c['mean_dMPPE']}**; mean dRPE <= +0.2 cm: **{c['mean_dRPE']}**; "
          f"complete: **{c['complete']}**. Verdict: **{'ADOPTED' if v['adopted'] else 'NOT ADOPTED'}**.\n")

j = G['joint_c0']
print('### Table 3. Joint c0 - base over all 15 twins (reported, not used to select)\n')
print('| ep | dAUC | dSP-SR | dMP-SR | dRPE cm | dMPPE cm | swapped objects: per-obj AUC base -> c0 |')
print('|---|---|---|---|---|---|---|')
for r in j['per_twin']:
    sw = '; '.join(f"{o} {f4(r['per_obj_AUC_base'][o])} -> {f4(r['per_obj_AUC_swap'][o])}"
                   for o in SWAPPED if o in r['per_obj_AUC_base'])
    print(f"| {r['ep']} | {s4(r['dAUC'])} | {s4(r['dSP_SR'])} | {s4(r['dMP_SR'])} | {s4(r['dRPE_cm'])} | "
          f"{s4(r['dMPPE_cm'])} | {sw} |")
for k in ('mean', 'min', 'max'):
    print(f"| **{k}** | {s4(j[f'{k}_dAUC'])} | {s4(j[f'{k}_dSP_SR'])} | {s4(j[f'{k}_dMP_SR'])} | "
          f"{s4(j[f'{k}_dRPE_cm'])} | {s4(j[f'{k}_dMPPE_cm'])} | |")
print(f"\nMissing joint twins: {j['missing']}. C0-final (guard_eval.py): {G['c0_final']}")
