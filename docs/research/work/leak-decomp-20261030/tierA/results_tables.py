"""Markdown tables for RESULTS.md from the Tier A outputs of tools/leak_tierA.py (a1.json ... a7.json in this folder).
ORACLE SIDE: the inputs hold mocap-derived scores; public episodes only. Leaderboard conversion = PLAN.md §2 (fixed
before any result): per eval e with H5 sim_vs_ref S_e >= 0.8, dT_e = a S_e dR(twin(e)), a = 1.025; L_LB = (c/20) sum_e
dT_e with c in [0.74, 1.0]. Labelled [E]. Evals 10, 14, 30 (S_e < 0.8) and the 10 spoon evals carry no [M] row.
Usage: python -I results_tables.py [DIR]
(2026-10-30)
"""
import json, os, sys
import numpy as np

D = sys.argv[1] if len(sys.argv) > 1 else os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(D, '..', '..', '..', '..', '..'))
J = {k: json.load(open(f'{D}/{k}.json')) for k in ('a1', 'a2', 'a3', 'a4', 'a6', 'a7') if os.path.exists(f'{D}/{k}.json')}
H5 = json.load(open(f'{REPO}/docs/analysis/h5-20261029/h5_summary.json'))
TWIN = {1: [2], 8: [27, 39], 10: [11], 14: [12, 13], 19: [18], 20: [21], 25: [24], 28: [27], 30: [31], 38: [39]}
A_MAP, C_LO, C_HI = 1.025, 0.74, 1.0
SHORT = dict(beige_cup='beige', blue_cup='blue', mini_dust_pan='pan', mini_sweeper='sweeper', plastic_dish_rack='rack',
             water_pitcher='pitcher', white_pot='pot', white_pot_lid='lid', wooden_piece_1='board1', wooden_piece_2='board2')


def lb(dR):
    """dR {ep(int): delta R} -> (low, high) leaderboard AUC [E], the per-eval terms, and the evals left out."""
    terms, out = {}, []
    for e, tw in TWIN.items():
        S = H5[str(e)]['mean']
        if S < 0.8 or any(t not in dR for t in tw):
            out.append(e); continue
        terms[e] = A_MAP * S * float(np.mean([dR[t] for t in tw]))
    tot = sum(terms.values()) / 20
    return C_LO * tot, C_HI * tot, terms, out


def lbs(dR):
    lo, hi, terms, out = lb(dR)
    return f'{lo:+.4f} to {hi:+.4f}'


def verdict(d):
    d = np.asarray(d, float); n = len(d); need = int(np.ceil(0.6 * n)); m = float(d.mean())
    pos, neg = int((d > 0).sum()), int((d < 0).sum())
    v = ('**leaks**' if m >= 0.01 and pos >= need else '**truth worse**' if m <= -0.01 and neg >= need
         else 'no leak' if abs(m) < 0.005 else 'inconclusive')
    return m, pos, neg, v


def vrow(name, dR, note=''):
    m, pos, neg, v = verdict(list(dR.values()))
    ex = [x for e, x in dR.items() if e != 23]
    m2 = float(np.mean(ex)) if ex else float('nan')
    print(f'| {name} | {m:+.4f} | {m2:+.4f} | {pos} / {neg} | {v} | {lbs(dR)} | {note} |')


def head_verdict():
    print('| quantity (ΔR, per episode) | mean 20 eps | mean without ep23 | eps > 0 / < 0 | reference-level verdict | L_LB [E] (c 0.74–1.0) | note |')
    print('|---|---|---|---|---|---|---|')


print('## Verdicts (PLAN §4 reference-level rule: mean ΔR ≥ 0.01 and ≥ 12/20 same sign → leaks; |mean ΔR| < 0.005 → no leak)\n')
head_verdict()
if 'a1' in J:
    E = J['a1']['episodes']
    vrow('A1 registration loss T\\* − T_lib (public scan)', {int(e): r['star']['AUC'] - r['lib']['AUC'] for e, r in E.items()}, '[M]')
    vrow('A1 registration loss, mean over 50 host perturbations', {int(e): -r['perturb']['scene']['L1_mean'] for e, r in E.items()}, '[M] under a perturbation model [H]')
    vrow('A1 constant body bias T_trk − T\\* (upper bound)', {int(e): r['bias'] for e, r in E.items()}, '[M], oracle fit, not a fix')
if 'a2' in J:
    E = J['a2']['episodes']
    vrow('A2 tracking loss of P_o on \\*: 1 − R\\*', {int(e): 1 - r['star']['AUC'] for e, r in E.items()}, 'L2 + L3 together (P_s comes in Phase 1)')
    vrow('A5 frame-0 re-anchor, body form', {int(e): r['reanchor']['body']['star']['AUC'] - r['star']['AUC'] for e, r in E.items()}, '[M], oracle')
    vrow('A5 frame-0 re-anchor, world form', {int(e): r['reanchor']['world']['star']['AUC'] - r['star']['AUC'] for e, r in E.items()}, '[M], oracle')
if 'a3' in J:
    E = J['a3']['episodes']
    for arm, lab in (('O', 'O (mocap)'), ('P', 'P (P_o)')):
        for k, nm in (('a', 'stage a: table + snap'), ('settle', 'contact retarget: rest settle'), ('S2', 'S2 0.545-frame advance'),
                      ('chain', 'whole chain raw → S2 + a + settle')):
            vrow(f'A3 {lab}, {nm}', {int(e): r['delta_star'][arm][k] for e, r in E.items()}, '[M]' + (' (IK stage: 0 by construction, checked)' if k == 'a' else ''))

if 'a1' in J:
    E = J['a1']['episodes']
    print('\n## A1 registration (L1) per episode and object [M]\n')
    print('| ep | object | T_lib | T\\* | T_trk | L1 = T_lib − T\\* | bias T_trk − T\\* | E = X\\*_geom X_kit⁻¹ ADD cm | flips /50 | perturbed L1 mean ± sd | perturbed T_lib sd | T_lib drops ≥ 0.03 /50 |')
    print('|---|---|---|---|---|---|---|---|---|---|---|---|')
    for e in sorted(E, key=int):
        r = E[e]
        for n in r['objects']:
            p = r['perturb']['summary'][n]
            print(f"| {e} | {SHORT[n]} | {r['lib']['per_obj_AUC'][n]:.4f} | {r['star']['per_obj_AUC'][n]:.4f} | {r['trk']['per_obj_AUC'][n]:.4f} "
                  f"| {r['L1_obj'][n]:+.4f} | {r['bias_obj'][n]:+.4f} | {r['E_kit'][n]['sym_add_cm']:.2f} | {p['flips']} "
                  f"| {p['L1_mean']:+.4f} ± {p['L1_sd']:.4f} | {p['lib_sd']:.4f} | {p['lib_drop_ge_0p03']} |")
    print('\nPer object over episodes:\n')
    print('| object | eps | L1 mean | eps with L1 ≤ −0.03 | eps with L1 ≥ +0.03 | flips / draws | max perturbed T_lib sd | perturbed L1 mean | bias mean |')
    print('|---|---|---|---|---|---|---|---|---|')
    for n, o in J['a1']['summary']['per_object'].items():
        print(f"| {SHORT[n]} | {len(o['eps'])} | {o['L1_mean']:+.4f} | {o['eps_L1_le_m0p03'] or '–'} | {o['eps_L1_ge_0p03'] or '–'} | {o['flips']} / {o['draws']} "
              f"| {o['lib_sd_perturb_max']:.4f} | {o['L1_perturb_mean']:+.4f} | {o['bias_mean']:+.4f} |")

if 'a2' in J:
    S = J['a2']['summary']; E = J['a2']['episodes']
    print('\n## A2 phase split of the tracking loss on \\* (P_o) [M]; occlusion proxy [H]\n')
    print('Loss share = contribution to 1 − R\\* (scene mean over objects, then over episodes); it adds up exactly.\n')
    print('| set | 1 − R\\* | ' + ' | '.join(f'{p} loss (share); occ / clear' for p in ('f0', 'rest_pre', 'moving', 'held_still', 'post')) + ' |')
    print('|---|---|' + '---|' * 5)
    for tag in ('all', 'no_ep23'):
        s = S[tag]
        print(f"| {tag} ({s['n_eps']} eps) | {s['loss_1_minus_Rstar']:.4f} | " + ' | '.join(
            f"{s['phase_loss'][p]:.4f} ({s['phase_share'][p]:.0%}); {s['phase_occ_loss'][p]['occ']:.4f} / {s['phase_occ_loss'][p]['clear']:.4f}"
            for p in ('f0', 'rest_pre', 'moving', 'held_still', 'post')) + ' |')
    print('\nPer episode and object (loss = contribution to the object\'s 1 − AUC; frames in brackets):\n')
    print('| ep | object | R\\* | true rot span ° / travel cm | f0 ADD cm | rest_pre | moving | held_still | post | occluded frames | body re-anchor R\\* | T_trk |')
    print('|---|---|---|---|---|---|---|---|---|---|---|---|')
    for e in sorted(E, key=int):
        for n, d in E[e]['objects_detail'].items():
            sp = d['split']
            print(f"| {e} | {SHORT[n]} | {d['star']:.4f} | {d['true_rot_span_deg']:.0f} / {d['true_travel_cm']:.0f} | {d['f0_add_cm']:.2f} | "
                  + ' | '.join(f"{sp[p]['loss']:.4f} ({sp[p]['n']})" for p in ('rest_pre', 'moving', 'held_still', 'post'))
                  + f" | {d['occluded_frames']} | {d['reanchor']['body']['star']:.4f} | {d['trk']:.4f} |")
    print('\n## A5 frame-0 re-anchor [M] (oracle: the track is moved so frame 0 sits at the mocap pose)\n')
    print('| set | T\\* | body re-anchor gain (eps + / −) | world re-anchor gain (eps +) | bias T_trk − T\\* | body gain / bias |')
    print('|---|---|---|---|---|---|')
    for tag in ('all', 'no_ep23'):
        s = S[tag]; sel = [r for e, r in E.items() if tag == 'all' or e != '23']
        print(f"| {tag} | {np.mean([r['star']['AUC'] for r in sel]):.4f} | {s['reanchor_body_gain']:+.4f} ({s['reanchor_body_pos']} / {s['reanchor_body_neg']}) "
              f"| {s['reanchor_world_gain']:+.4f} ({s['reanchor_world_pos']}) | {s['bias_trk']:+.4f} | {s['reanchor_body_over_bias']} |")
    h = S['H3_objects_over_30deg']
    print(f"\nH3 (objects whose true rotation span > 30°, ep23 excluded): {h['n']} objects; body re-anchor gain {h['reanchor_gain_sum']:+.4f} "
          f"vs constant-offset bound {h['bias_sum']:+.4f} (ratio {h['ratio']}). H3 is falsified if the ratio < 0.5.")
    print('\n| ep | T\\* | body re-anchor | world re-anchor | T_trk |')
    print('|---|---|---|---|---|')
    for e in sorted(E, key=int):
        r = E[e]
        print(f"| {e} | {r['star']['AUC']:.4f} | {r['reanchor']['body']['star']['AUC']:.4f} | {r['reanchor']['world']['star']['AUC']:.4f} | {r['trk']['AUC']:.4f} |")

if 'a3' in J:
    E = J['a3']['episodes']; S = J['a3']['summary']
    print('\n## A3 reference construction stages (L4) on \\*, O and P [M]\n')
    print('| arm | raw | a: table + snap | IK + contacts | rest settle | with S2 (raw / a / settle) | lib column: raw / settle / S2 settle |')
    print('|---|---|---|---|---|---|---|')
    for arm in ('O', 'P'):
        m = S[arm]['R_star_mean']; l = S[arm]['R_lib_mean']
        print(f"| {arm} | {m['base:raw']:.4f} | {m['base:a']:.4f} | {m['base:ik']:.4f} | {m['base:settle']:.4f} | {m['S2:raw']:.4f} / {m['S2:a']:.4f} / {m['S2:settle']:.4f} "
              f"| {l['base:raw']:.4f} / {l['base:settle']:.4f} / {l['S2:settle']:.4f} |")
    print(f"\nO stages costing ≥ 0.02 per object (PLAN §4 action rule: ≥ 3 episodes): " +
          '; '.join(f"{k}: {v or 'none'}" for k, v in S['O_stage_costs_ge_0p02'].items()))
    print('\n| ep | O raw | O a | O settle | O S2 | P raw | P a | P settle | P S2 | O snap cm | P snap cm |')
    print('|---|---|---|---|---|---|---|---|---|---|---|')
    for e in sorted(E, key=int):
        r = E[e]; g = lambda k, s: r['arms'][k][s]['star']['AUC']   # noqa: E731
        print(f"| {e} | {g('O_base', 'raw'):.4f} | {g('O_base', 'a'):.4f} | {g('O_base', 'settle'):.4f} | {g('O_S2', 'settle'):.4f} "
              f"| {g('P_base', 'raw'):.4f} | {g('P_base', 'a'):.4f} | {g('P_base', 'settle'):.4f} | {g('P_S2', 'settle'):.4f} "
              f"| {r['prep']['O_base']['snap_cm']} | {r['prep']['P_base']['snap_cm']} |")
    if J['a3'].get('stored'):
        print('\nStored real references (older perception and code; P only) on \\* (lib in brackets):\n')
        print('| ep | run | loaded (a + b) | E2S + contacts | processed (contact retarget) | grasp-lock trained | loaded vs E2S max cm | loaded vs processed max cm |')
        print('|---|---|---|---|---|---|---|---|')
        for r in J['a3']['stored']:
            f = lambda k: (f"{r[k]['star']['AUC']:.4f} ({r[k]['lib']['AUC']:.4f})" if k in r else '–')   # noqa: E731
            print(f"| {r['ep']} | {r['run']} | {f('loaded')} | {f('e2s')} | {f('processed')} | {f('glock')} | {r.get('loaded_vs_e2s_max_cm', '–')} | {r.get('loaded_vs_processed_max_cm', '–')} |")

if 'a4' in J:
    S = J['a4']['summary']; E = J['a4']['episodes']
    q = lambda d: (f"{d['median']:+.0f} [{d['p25']:+.0f}, {d['p75']:+.0f}] (n {d['n']})" if d['n'] else '–')   # noqa: E731
    print('\n## A4 hands vs the mocap object motion [M] (frames at 20 fps; median [IQR]; ep23 excluded)\n')
    print('| quantity | first handling segment | last segment | all segments |')
    print('|---|---|---|---|')
    print(f"| hand arrival (fingertip ≤ 2 cm of the true surface) − true onset | {q(S['arrival_lag_first'])} | | {q(S['arrival_lag_all'])} |")
    print(f"| hand leave − true end | | {q(S['leave_lag_last'])} | {q(S['leave_lag_all'])} |")
    print(f"| our track's onset − true onset | {q(S['perc_onset_lag_first'])} | | {q(S['perc_onset_lag_all'])} |")
    print(f"| our track's end − true end | | {q(S['perc_end_lag_last'])} | {q(S['perc_end_lag_all'])} |")
    g1, g2 = S['gap_true_cm_median_over_objects'], S['gap_perc_cm_median_over_objects']
    print(f"\nFingertip-to-surface gap during true motion (median over objects of the per-object median): true surface {g1['median']:.2f} cm "
          f"[{g1['p25']:.2f}, {g1['p75']:.2f}], our track's surface {g2['median']:.2f} cm. Segments without a hand within 2 cm: "
          f"{S['segments_without_hand']} of {S['segments']}; leave capped at the 40-frame window: {S['leave_capped']}.")
    print('\n| ep | object | segments (true onset–end: arrival, leave, our onset, our end lags) | gap true / ours cm | gap > 3 cm frac | hand measured in motion |')
    print('|---|---|---|---|---|---|')
    for e in sorted(E, key=int):
        for n, d in E[e]['objects_detail'].items():
            sg = '; '.join(f"{x['segment'][0]}–{x['segment'][1]}: {x['arrival_lag']}, {x['leave_lag']}, {x['perc_onset_lag']}, {x['perc_end_lag']}" for x in d['segments'])
            print(f"| {e} | {SHORT[n]} | {sg or '–'} | {d['gap_true_cm_median']} / {d['gap_perc_cm_median']} | {d['gap_true_frac_over_3cm']} "
                  f"| {d['moving_frames_hand_measured']}/{d['moving_frames']} |")

if 'a6' in J:
    s = J['a6']['summary']
    print('\n## A6 scorer sanity and frame invariance [M] (from frames_check.json)\n')
    print(f"All pass flags: {s['all_pass']} ({', '.join(f'{k} {v}' for k, v in s['pass_flags'].items())}). Mocap through the kit path: "
          f"{s['a1_mocap_scan_min']:.4f} (scan) / {s['a2_mocap_Xkit_min']:.4f} (lib at X_kit); T\\* two ways max |Δ| {s['b1_two_ways_max_abs']:.4f}; "
          f"cup spin max |Δ| {s['b2_cup_spin_max_abs']:.4f} (rule ≤ 0.002); budgeted-scan registration noise max {s['b1b_budget_scan_max_abs']:.4f}.")

if 'a7' in J:
    A = J['a7']['a7']; S = J['a7']['summary']
    print('\n## A7 2 s hands-free settle of the mocap rest configurations [M] (gate: every object ≤ 1 cm and ≤ 5° at 2 s)\n')
    print('| ep | rest frames (dropped: held) | lib | lib + carve | scan |')
    print('|---|---|---|---|---|')
    for e in sorted(A, key=int):
        v = A[e]; cell = []
        for g in ('lib', 'lib_carve', 'scan'):
            x = v['geoms'].get(g)
            if not x:
                cell.append('–'); continue
            if 'missing' in x:
                cell.append('not run'); continue
            worst = max(((c['at_2s'][n][0], c['at_2s'][n][1], F, n) for F, c in x['configs'].items() for n in c['at_2s']), default=None)
            cell.append(f"{'PASS' if x['gate_pass'] else 'FAIL'} {x['n_pass']}/{x['n']}" + (f"; worst {worst[0]:.2f} cm / {worst[1]:.1f}° ({SHORT[worst[3]]} f{worst[2]})" if worst else ''))
        print(f"| {e} | {v['frames']} ({v['dropped_held'] or '–'}) | " + ' | '.join(cell) + ' |')
    print('\n' + '; '.join(f"{g}: pass {len(s['gate_pass'])} / {s['eps']} eps" for g, s in S.items()))
