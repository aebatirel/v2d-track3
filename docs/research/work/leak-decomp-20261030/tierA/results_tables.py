"""Markdown tables for RESULTS.md from the Tier A outputs of tools/leak_tierA.py (a1.json ... a7.json in this folder).
ORACLE SIDE: the inputs hold mocap-derived scores; public episodes only. Leaderboard conversion = PLAN.md §2 (fixed
before any result): per eval e with H5 sim_vs_ref S_e >= 0.8, dT_e = a S_e dR(twin(e)), a = 1.025; L_LB = (c/20) sum_e
dT_e with c in [0.74, 1.0]. Labelled [E]. Evals 10, 14, 30 (S_e < 0.8) and the 10 spoon evals carry no [M] row.
Sign convention (PLAN §2/§4): every dR is "what the true version of the stage gains", so dR > 0 is a leak. For a
construction stage (A3) that is R(before the stage) - R(after it); for registration T* - T_lib; for tracking loss 1 - R*.
Optional inputs: a1seed.json (seed-only registration test), a4_w120.json (A4 with a 120-frame window), a3_depen_check.json,
a1_v2.json (A1 with welded host perturbations; replaces a1.json, whose perturbations decimated unwelded scan soups).
Usage: python -I results_tables.py [DIR]
(2026-10-30; v2 31 Oct: A3 sign fixed (stage loss = before - after), plan phases, init / drift, seed test, per-twin gates)
"""
import json, os, sys
import numpy as np

D = sys.argv[1] if len(sys.argv) > 1 else os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '..', '..', '..'))
J = {k: json.load(open(f'{D}/{k}.json')) for k in ('a1', 'a1seed', 'a2', 'a3', 'a3_depen_check', 'a4', 'a4_w120', 'a6', 'a7')
     if os.path.exists(f'{D}/{k}.json')}
A1_SRC = 'a1.json'
if os.path.exists(f'{D}/a1_v2.json'):         # a1.json's host perturbations decimated unwelded scan soups (invalid); v2 welds
    J['a1'] = json.load(open(f'{D}/a1_v2.json')); A1_SRC = 'a1_v2.json'
H5 = json.load(open(f'{REPO}/docs/analysis/h5-20261029/h5_summary.json'))
TWIN = {1: [2], 8: [27, 39], 10: [11], 14: [12, 13], 19: [18], 20: [21], 25: [24], 28: [27], 30: [31], 38: [39]}
TWINS = (2, 11, 12, 13, 18, 21, 24, 27, 31, 39)               # Phase-2 rollout twins (PLAN §3)
A_MAP, C_LO, C_HI = 1.025, 0.74, 1.0
PH = ('f0', 'rest_pre', 'moving', 'held_still', 'post')
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
    lo, hi, _, _ = lb(dR)
    return f'{min(lo, hi):+.4f} to {max(lo, hi):+.4f}'


def verdict(d):
    """PLAN §4 reference-level rule: mean dR >= 0.01 and >= 60 % of episodes (12/20) positive -> leaks; the same
    negative -> truth worse; |mean| < 0.005 -> no leak; else inconclusive."""
    d = np.asarray(d, float); n = len(d); need = int(np.ceil(0.6 * n)); m = float(d.mean())
    pos, neg = int((d > 1e-9).sum()), int((d < -1e-9).sum())
    v = ('**leaks**' if m >= 0.01 and pos >= need else '**truth worse**' if m <= -0.01 and neg >= need
         else 'no leak' if abs(m) < 0.005 else 'inconclusive')
    return m, pos, neg, v


def vrow(name, dR, note=''):
    """Pre-registered verdict on all 20 episodes (PLAN keeps ep23 in Tier A); the verdict without ep23 (identity swap:
    one tracker failure that dominates several means) is shown beside it as a sensitivity, not as the reading."""
    m20, pos, neg, v = verdict(list(dR.values()))
    ex = {e: x for e, x in dR.items() if e != 23}
    m19, p19, n19, v19 = verdict(list(ex.values()))
    print(f'| {name} | {m20:+.4f} | {pos} / {neg} | {v} | {m19:+.4f} | {v19} | {lbs(ex)} | {note} |')


print('## Verdicts (PLAN §4 reference-level rule on the 20 public episodes: mean ΔR ≥ 0.01 and ≥ 12/20 episodes '
      'positive → leaks; the same negative → truth worse; |mean ΔR| < 0.005 → no leak; else inconclusive)\n')
print('ΔR = what the true version gains (positive = a leak). L_LB = (c/20)·Σ_e a·S_e·ΔR(twin(e)) over the 7 evals with '
      'S_e ≥ 0.8 (1, 8, 19, 20, 25, 28, 38), a = 1.025, c 0.74–1.0 [E].\n')
print('| quantity (ΔR per episode) | mean 20 eps | eps > 0 / < 0 | verdict (rule) | mean without ep23 | verdict without ep23 | L_LB [E] | note |')
print('|---|---|---|---|---|---|---|---|')
if 'a1' in J:
    E = J['a1']['episodes']
    vrow('A1 L1 registration, public scan, own seed: T\\* − T_lib', {int(e): r['star']['AUC'] - r['lib']['AUC'] for e, r in E.items()}, '[M]')
    vrow('A1 constant body bias T_trk − T\\* (upper bound)', {int(e): r['bias'] for e, r in E.items()}, '[M], oracle fit, not a fix')
if 'a1seed' in J:
    E = J['a1seed']['episodes']
    vrow('A1 seed only (public scan as host): T_lib own seed − mean over 50 seeds', {int(e): r['summary']['scene_drop_mean'] for e, r in E.items()},
         '[M] given host scan = public scan')
if 'a1' in J:
    E = J['a1']['episodes']
    vrow(f"A1 host-scan perturbation ({'welded' if A1_SRC == 'a1_v2.json' else 'UNWELDED soups: invalid'}, 30 % decimation, 1 mm, 10 % holes; {A1_SRC}): T\\* − T_lib, mean of 50", {int(e): -r['perturb']['scene']['L1_mean'] for e, r in E.items()},
         '[M] under a perturbation model [H]')
if 'a2' in J:
    E = J['a2']['episodes']
    ph = lambda r, ps: float(np.mean([sum(d['split'][p]['loss'] for p in ps) for d in r['objects_detail'].values()]))   # noqa: E731
    vrow('A2 tracking loss of P_o on \\*: 1 − R\\* (L2 + L3)', {int(e): 1 - r['star']['AUC'] for e, r in E.items()}, '[M]; P_s splits L2 / L3 (Phase 1)')
    vrow('A2 phase f0 (frame 0)', {int(e): ph(r, ('f0',)) for e, r in E.items()}, '[M]')
    vrow('A2 phase untouched rest (before the first true motion)', {int(e): ph(r, ('rest_pre',)) for e, r in E.items()}, '[M]')
    vrow('A2 phase held-moving (true motion ± 2 frames, and still between motions)', {int(e): ph(r, ('moving', 'held_still')) for e, r in E.items()}, '[M]')
    vrow('A2 phase post-release (after the last true motion)', {int(e): ph(r, ('post',)) for e, r in E.items()}, '[M]')
    vrow('A2 loss in hand-occluded frames (all phases)', {int(e): float(np.mean([sum(d['split'][p]['occ']['loss'] for p in PH) for d in r['objects_detail'].values()]))
                                                          for e, r in E.items()}, '[M]; occlusion proxy [H]')
    vrow('A5 init: frame-0 re-anchor gain, body form', {int(e): r['reanchor']['body']['star']['AUC'] - r['star']['AUC'] for e, r in E.items()}, '[M], oracle')
    vrow('A5 drift: loss left after the body re-anchor, 1 − R\\*_re', {int(e): 1 - r['reanchor']['body']['star']['AUC'] for e, r in E.items()}, '[M], oracle')
    vrow('A5 frame-0 re-anchor gain, world form', {int(e): r['reanchor']['world']['star']['AUC'] - r['star']['AUC'] for e, r in E.items()}, '[M], oracle')
if 'a3' in J:
    E = J['a3']['episodes']
    for arm, lab in (('O', 'O (mocap)'), ('P', 'P (P_o)')):
        for k, nm in (('a', 'stage a: table + snap'), ('settle', 'contact retarget: rest settle'), ('S2', 'S2 0.545-frame advance'),
                      ('chain', 'whole chain raw → S2 + a + settle')):
            vrow(f'A3 {lab}, {nm}: R before − R after', {int(e): -r['delta_star'][arm][k] for e, r in E.items()},
                 '[M]' + (', IK + contacts: 0 by construction (checked)' if k == 'a' else '') + (', LB upper bound only: O is not available on eval' if arm == 'O' else ''))

if 'a1' in J:
    E = J['a1']['episodes']
    print(f'\n## A1 registration (L1) per episode and object [M] (source: {A1_SRC})\n')
    print('| ep | object | T_lib | T\\* | T_trk | L1 = T_lib − T\\* | bias T_trk − T\\* | E = X\\*_geom X_kit⁻¹ ADD cm | perturbation: flips /50 | T_lib drops ≥ 0.03 /50 | perturbed L1 mean ± sd |'
          + (' seed only: flips /50 | seed only: T_lib drops ≥ 0.03 /50 |' if 'a1seed' in J else ''))
    print('|---|---|---|---|---|---|---|---|---|---|---|' + ('---|---|' if 'a1seed' in J else ''))
    for e in sorted(E, key=int):
        r = E[e]
        for n in r['objects']:
            p = r['perturb']['summary'][n]; sx = ''
            if 'a1seed' in J:
                q = J['a1seed']['episodes'][e]; lib0 = q['lib_own_seed']['per_obj_AUC'][n]
                sx = f" {q['summary']['flips'][n]} | {sum(x['lib']['per_obj_AUC'][n] <= lib0 - 0.03 for x in q['rows'])} |"
            print(f"| {e} | {SHORT[n]} | {r['lib']['per_obj_AUC'][n]:.4f} | {r['star']['per_obj_AUC'][n]:.4f} | {r['trk']['per_obj_AUC'][n]:.4f} "
                  f"| {r['L1_obj'][n]:+.4f} | {r['bias_obj'][n]:+.4f} | {r['E_kit'][n]['sym_add_cm']:.2f} | {p['flips']} | {p['lib_drop_ge_0p03']} "
                  f"| {p['L1_mean']:+.4f} ± {p['L1_sd']:.4f} |" + sx)
    print('\nPer object over episodes (L1 = T_lib − T\\*; the PLAN §4 action needs a LOSS T\\* − T_lib ≥ 0.03 on one object in ≥ 2 episodes):\n')
    print('| object | eps | L1 mean | eps with loss ≥ 0.03 (L1 ≤ −0.03) | eps with L1 ≥ +0.03 | perturbation flips / draws | bias mean |'
          + (' seed-only flips / draws (slot) |' if 'a1seed' in J else ''))
    print('|---|---|---|---|---|---|---|' + ('---|' if 'a1seed' in J else ''))
    for n, o in J['a1']['summary']['per_object'].items():
        sx = ''
        if 'a1seed' in J:
            sx = ' ' + ', '.join(f"{v['flips']} / {v['draws']} (slot {k.split('@')[1]})" for k, v in J['a1seed']['summary']['per_object_slot'].items()
                                 if k.split('@')[0] == n) + ' |'
        print(f"| {SHORT[n]} | {len(o['eps'])} | {o['L1_mean']:+.4f} | {o['eps_L1_le_m0p03'] or '–'} | {o['eps_L1_ge_0p03'] or '–'} | {o['flips']} / {o['draws']} "
              f"| {o['bias_mean']:+.4f} |" + sx)
    print('\nScene level (the kit aligns the whole scene on the first non-symmetric object at frame 0, so a flip of that '
          'object moves every other object too):\n')
    print('| ep | objects (anchor first) | T_lib own seed | perturbation: scene T_lib mean (min), drops ≥ 0.03 /50 |' + (' seed only: scene T_lib mean (min), drops ≥ 0.03 /50 |' if 'a1seed' in J else ''))
    print('|---|---|---|---|' + ('---|' if 'a1seed' in J else ''))
    for e in sorted(E, key=int):
        r = E[e]; rows = r['perturb']['rows']; sc = np.array([x['lib']['AUC'] for x in rows]); sx = ''
        if 'a1seed' in J:
            s = J['a1seed']['episodes'][e]['summary']
            sx = f" {s['scene_lib_mean']:.4f} ({s['scene_lib_min']:.4f}), {s['scene_drops_ge_0p03']} |"
        print(f"| {e} | {', '.join(SHORT[n] for n in r['objects'])} | {r['lib']['AUC']:.4f} | {sc.mean():.4f} ({sc.min():.4f}), {int((sc <= r['lib']['AUC'] - 0.03).sum())} |" + sx)

if 'a2' in J:
    E = J['a2']['episodes']
    print('\n## A2 phase split of the tracking loss on \\* (P_o = refine/in tracks) [M]; occlusion proxy [H]\n')
    print('Loss = contribution to 1 − R\\* (mean over the scene\'s objects, then over episodes); the phases add up to 1 − R\\* exactly. '
          'Plan phases: frame-0 = f0; untouched rest = rest_pre; held-moving = moving + held_still; post-release = post.\n')
    print('| set | 1 − R\\* | f0 | untouched rest | held-moving | post-release | in occluded frames | occluded share of object-frames |')
    print('|---|---|---|---|---|---|---|---|')
    for tag in ('all', 'no_ep23'):
        sel = [r for e, r in E.items() if tag == 'all' or e != '23']
        for form in ('track', 'body re-anchor'):
            sp = (lambda d: d['split']) if form == 'track' else (lambda d: d['reanchor']['body']['split'])     # noqa: E731
            ph = {p: float(np.mean([np.mean([sp(d)[p]['loss'] for d in r['objects_detail'].values()]) for r in sel])) for p in PH}
            occ = float(np.mean([np.mean([sum(sp(d)[p]['occ']['loss'] for p in PH) for d in r['objects_detail'].values()]) for r in sel]))
            nocc = sum(sp(d)[p]['occ']['n'] for r in sel for d in r['objects_detail'].values() for p in PH)
            nall = sum(sp(d)[p]['n'] for r in sel for d in r['objects_detail'].values() for p in PH)
            tot = sum(ph.values())
            print(f"| {tag} ({len(sel)} eps), {form} | {tot:.4f} | {ph['f0']:.4f} | {ph['rest_pre']:.4f} ({ph['rest_pre'] / tot:.0%}) "
                  f"| {ph['moving'] + ph['held_still']:.4f} ({(ph['moving'] + ph['held_still']) / tot:.0%}) | {ph['post']:.4f} ({ph['post'] / tot:.0%}) "
                  f"| {occ:.4f} ({occ / tot:.0%}) | {nocc / nall:.0%} |")
    print('\nPer episode (scene means; init = body re-anchor gain, drift = 1 − R\\* after it):\n')
    print('| ep | 1 − R\\* | f0 | untouched rest | held-moving | post-release | init (A5) | drift (A5) | T_trk − T\\* |')
    print('|---|---|---|---|---|---|---|---|---|')
    for e in sorted(E, key=int):
        r = E[e]; d = r['objects_detail'].values()
        ph = {p: float(np.mean([x['split'][p]['loss'] for x in d])) for p in PH}; re = r['reanchor']['body']['star']['AUC']
        print(f"| {e} | {1 - r['star']['AUC']:.4f} | {ph['f0']:.4f} | {ph['rest_pre']:.4f} | {ph['moving'] + ph['held_still']:.4f} | {ph['post']:.4f} "
              f"| {re - r['star']['AUC']:+.4f} | {1 - re:.4f} | {r['trk']['AUC'] - r['star']['AUC']:+.4f} |")
    print('\nPer object (loss = contribution to the object\'s 1 − AUC; frames in brackets):\n')
    print('| ep | object | R\\* | true rot span ° / travel cm | f0 ADD cm | untouched rest | held-moving | post | occluded frames | body re-anchor R\\* | T_trk |')
    print('|---|---|---|---|---|---|---|---|---|---|---|')
    for e in sorted(E, key=int):
        for n, d in E[e]['objects_detail'].items():
            sp = d['split']; hm = sp['moving']['loss'] + sp['held_still']['loss']
            print(f"| {e} | {SHORT[n]} | {d['star']:.4f} | {d['true_rot_span_deg']:.0f} / {d['true_travel_cm']:.0f} | {d['f0_add_cm']:.2f} | "
                  f"{sp['rest_pre']['loss']:.4f} ({sp['rest_pre']['n']}) | {hm:.4f} ({sp['moving']['n'] + sp['held_still']['n']}) | {sp['post']['loss']:.4f} ({sp['post']['n']}) "
                  f"| {d['occluded_frames']} | {d['reanchor']['body']['star']:.4f} | {d['trk']:.4f} |")
    S = J['a2']['summary']; h = S['H3_objects_over_30deg']
    print(f"\nFRAMES H3 falsifier (objects whose true rotation span > 30°, ep23 excluded): {h['n']} objects; body re-anchor gain "
          f"{h['reanchor_gain_sum']:+.4f} vs constant-offset bound {h['bias_sum']:+.4f} (ratio {h['ratio']}); falsified if < 0.5.")

if 'a3' in J:
    E = J['a3']['episodes']; S = J['a3']['summary']
    print('\n## A3 reference construction stages (L4) on \\*, O and P [M]\n')
    print('| arm | raw | a: table + snap | IK + contacts | rest settle | with S2 (raw / a / settle) | lib column: raw / settle / S2 settle |')
    print('|---|---|---|---|---|---|---|')
    for arm in ('O', 'P'):
        m = S[arm]['R_star_mean']; l = S[arm]['R_lib_mean']
        print(f"| {arm} | {m['base:raw']:.4f} | {m['base:a']:.4f} | {m['base:ik']:.4f} | {m['base:settle']:.4f} | {m['S2:raw']:.4f} / {m['S2:a']:.4f} / {m['S2:settle']:.4f} "
              f"| {l['base:raw']:.4f} / {l['base:settle']:.4f} / {l['S2:settle']:.4f} |")
    print('\nPLAN §4 L4 action rule (a stage costs ≥ 0.02 per object on O in ≥ 3 episodes): ' +
          '; '.join(f"{k}: {len(v)} ({', '.join(f'ep{e} {SHORT[n]}' for e, n in v) or 'none'})" for k, v in S['O_stage_costs_ge_0p02'].items()))
    Pc = {k: [(r['episode'], n) for r in E.values() for n, d in r['delta_star_obj']['P'].items() if d[k] <= -0.02] for k in ('a', 'settle', 'S2')}
    Pg = {k: [(r['episode'], n) for r in E.values() for n, d in r['delta_star_obj']['P'].items() if d[k] >= 0.02] for k in ('a', 'settle', 'S2')}
    print('\nOn P, objects where a stage costs ≥ 0.02: ' + '; '.join(f"{k}: {len(v)} ({', '.join(f'ep{e} {SHORT[n]}' for e, n in sorted(v)) or 'none'})" for k, v in Pc.items()))
    print('\nOn P, objects where a stage gains ≥ 0.02: ' + '; '.join(f"{k}: {len(v)} ({', '.join(f'ep{e} {SHORT[n]}' for e, n in sorted(v)) or 'none'})" for k, v in Pg.items()))
    print('\n| ep | O raw | O a | O settle | O S2 settle | P raw | P a | P settle | P S2 settle | O snap cm | P snap cm | P support fallback |')
    print('|---|---|---|---|---|---|---|---|---|---|---|---|')
    for e in sorted(E, key=int):
        r = E[e]; g = lambda k, s: r['arms'][k][s]['star']['AUC']   # noqa: E731
        print(f"| {e} | {g('O_base', 'raw'):.4f} | {g('O_base', 'a'):.4f} | {g('O_base', 'settle'):.4f} | {g('O_S2', 'settle'):.4f} "
              f"| {g('P_base', 'raw'):.4f} | {g('P_base', 'a'):.4f} | {g('P_base', 'settle'):.4f} | {g('P_S2', 'settle'):.4f} "
              f"| {r['prep']['O_base']['snap_cm']} | {r['prep']['P_base']['snap_cm']} | {r['prep']['P_base']['support_fallback']} |")
    if J['a3'].get('stored'):
        print('\nStored real references (older perception and code; P only) on \\* (lib in brackets):\n')
        print('| ep | run | loaded (a + b) | E2S + contacts | processed (contact retarget) | grasp-lock trained (ref_gl_ilc) | loaded vs E2S max cm | loaded vs processed max cm |')
        print('|---|---|---|---|---|---|---|---|')
        for r in J['a3']['stored']:
            f = lambda k: (f"{r[k]['star']['AUC']:.4f} ({r[k]['lib']['AUC']:.4f})" if k in r else '–')   # noqa: E731
            print(f"| {r['ep']} | {r['run']} | {f('loaded')} | {f('e2s')} | {f('processed')} | {f('glock')} | {r.get('loaded_vs_e2s_max_cm', '–')} | {r.get('loaded_vs_processed_max_cm', '–')} |")
    if 'a3_depen_check' in J:
        c = J['a3_depen_check']
        print('\nJoint depenetration check (mkref\'s 6 mm joint depenetration, skipped in the 20-episode run): rest-settled R\\* without / with it: '
              + '; '.join(f"ep{e} {arm[0]} {v[arm]['star']:.4f} / {v[arm + '_depen']['star']:.4f} (max position difference {v[arm + '_maxdiff_cm']} cm)"
                          for e, v in c.items() for arm in ('P_base', 'O_base')))


def a4_table(A, label):
    S = A['summary']
    q = lambda d: (f"{d['median']:+.0f} [{d['p25']:+.0f}, {d['p75']:+.0f}] (n {d['n']})" if d['n'] else '–')   # noqa: E731
    print(f'\n{label}\n')
    print('| quantity (frames at 20 fps; median [IQR]) | first handling segment | last segment | all segments |')
    print('|---|---|---|---|')
    print(f"| hand arrival (fingertip ≤ 2 cm of the true surface) − true onset | {q(S['arrival_lag_first'])} | | {q(S['arrival_lag_all'])} |")
    print(f"| hand leave − true end | | {q(S['leave_lag_last'])} | {q(S['leave_lag_all'])} |")
    print(f"| our track's onset − true onset | {q(S['perc_onset_lag_first'])} | | {q(S['perc_onset_lag_all'])} |")
    print(f"| our track's end − true end | | {q(S['perc_end_lag_last'])} | {q(S['perc_end_lag_all'])} |")
    g1, g2 = S['gap_true_cm_median_over_objects'], S['gap_perc_cm_median_over_objects']
    print(f"\nFingertip-to-surface gap during true motion (median over objects of the per-object median, nearest measured fingertip of "
          f"either hand): true surface {g1['median']:.2f} cm [{g1['p25']:.2f}, {g1['p75']:.2f}], our track's surface {g2['median']:.2f} cm. "
          f"Segments without a hand within 2 cm: {S['segments_without_hand']} of {S['segments']}; leave still near at the window edge "
          f"(a lower bound): {S['leave_capped']} of {S['segments']}.")


if 'a4' in J:
    print('\n## A4 hands vs the mocap object motion [M] (ep23 excluded)')
    a4_table(J['a4'], 'Window ±40 frames (as pre-built):')
    if 'a4_w120' in J:
        a4_table(J['a4_w120'], 'Window ±120 frames (sensitivity; neighbouring segments still bound each window):')
    E = J['a4']['episodes']
    print('\n| ep | object | segments (true onset–end: arrival, leave, our onset, our end lags; ±40) | gap true / ours cm | gap > 3 cm frac | hand measured in motion |')
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


def handfree(F, c):
    g = list((c.get('hand_gap_cm') or {}).values())
    return bool(g) and (all(h is not None and h > 3 for h in g) or (F == '0' and all(h is None or h > 3 for h in g)))


if 'a7' in J:
    A = J['a7']['a7']; S = J['a7']['summary']
    print('\n## A7 2 s hands-free settle of the mocap rest configurations [M] (gate: every object ≤ 1 cm and ≤ 5° at 2 s)\n')
    print('| ep | rest frames (dropped: held in the air) | lib | lib + carve | scan |')
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
            free = {F: c for F, c in x['configs'].items() if handfree(F, c)}
            hg = (x['configs'][worst[2]].get('hand_gap_cm') or {}).get(worst[3]) if worst else None
            cell.append(f"{'PASS' if x['gate_pass'] else 'FAIL'} {x['n_pass']}/{x['n']} (hand-free {sum(c['pass_'] for c in free.values())}/{len(free)})"
                        + (f"; worst {worst[0]:.2f} cm / {worst[1]:.1f}° ({SHORT[worst[3]]} f{worst[2]}, hand {hg} cm)" if worst else ''))
        print(f"| {e} | {v['frames']} ({v['dropped_held'] or '–'}) | " + ' | '.join(cell) + ' |')
    print('\nAll configurations: ' + '; '.join(f"{g}: pass {len(s['gate_pass'])} / {s['eps']} eps" for g, s in S.items()))
    print('\n"Hand-free" = every measured fingertip > 3 cm from every object\'s true surface at that frame. A frame with no '
          'measured hand counts as unknown (not hand-free), except frame 0. Gate on hand-free configurations only:\n')
    res = {}
    for g in ('lib', 'lib_carve', 'scan'):
        res[g] = {}
        for e, v in A.items():
            x = v['geoms'].get(g)
            if not x or 'missing' in x:
                continue
            fr = {F: c for F, c in x['configs'].items() if handfree(F, c)}
            res[g][int(e)] = (all(c['pass_'] for c in fr.values()), len(fr), fr) if fr else (None, 0, {})
        r = res[g]
        print(f"- {g}: pass {sorted(e for e, x in r.items() if x[0])}; fail {sorted(e for e, x in r.items() if x[0] is False)}; "
              f"no hand-free configuration {sorted(e for e, x in r.items() if x[0] is None)}")
    print('\nPer Phase-2 twin (PLAN §3 gate for c4–c6 = scan geometry; lib shown for c1–c3, which the plan does not gate):\n')
    print('| twin | eval | scan: hand-free gate | scan: worst hand-free drift | lib: hand-free gate | lib: worst hand-free drift | lib + carve: hand-free gate |')
    print('|---|---|---|---|---|---|---|')
    ev = {t: [e for e, tw in TWIN.items() if t in tw] for t in TWINS}
    for t in TWINS:
        def cellv(g):
            x = res.get(g, {}).get(t)
            if x is None:
                return '–', '–'
            ok, n, fr = x
            w = max(((c['at_2s'][o][0], c['at_2s'][o][1], F, o) for F, c in fr.items() for o in c['at_2s']), default=None)
            return (('PASS' if ok else 'FAIL' if ok is False else 'no hand-free config') + f' ({n})',
                    f'{w[0]:.2f} cm / {w[1]:.1f}° ({SHORT[w[3]]} f{w[2]})' if w else '–')
        s1, s2 = cellv('scan'); l1, l2 = cellv('lib'); c1, _ = cellv('lib_carve')
        print(f"| ep{t} | {', '.join(map(str, ev[t]))} | {s1} | {s2} | {l1} | {l2} | {c1} |")
