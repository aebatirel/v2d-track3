"""Fixture tests of tools/mass_eval_rule.py (PLAN section 5 rules 4-9; review F4) and of the F1 merge mechanics
(tools/mass_eval_merge.py: a missing or thin seed -> INCOMPLETE). Synthetic inputs only (no box, no ground truth): each
case is a small h5_summary.json + c1_merge.json (or training-box summary.json files for the merge) with an expected
verdict. usage: python3 -I test_rule.py OUT_DIR   -> OUT_DIR/rule_tests.txt, OUT_DIR/rule_tests.json; exit 1 on a failure.
"""
import json, os, subprocess, sys

REPO = '/home/user/v2d-track3'
sys.path.insert(0, f'{REPO}/tools')
import mass_eval_rule as R          # noqa: E402

OUT = sys.argv[1]; os.makedirs(OUT, exist_ok=True)
P7 = json.loads(open(f'{REPO}/results/submissions/20261030-track3g-candidate/summary.txt').readline())
P8 = json.loads(open(f'{REPO}/results/submissions/20261030-track3h-candidate/summary.txt').readline())
res = []


def check(name, cond, detail=''):
    res.append(dict(name=name, ok=bool(cond), detail=str(detail)[:400]))


def merge(**eps):
    """eps: ep -> 'C' (CANDIDATE, seed 42) | 'O' (OUT) | 'I' (INCOMPLETE training)."""
    d = {}
    for e, k in eps.items():
        e = e.lstrip('e')
        if k == 'C':
            d[e] = dict(decision='CANDIDATE', seed='42', run=f'20261101-mevX-{e}', mode='glock',
                        stats={'42': dict(n=10, mean=0.9, sd=0.01, min=0.88), '43': dict(n=10, mean=0.89, sd=0.01, min=0.87)})
        elif k == 'O':
            d[e] = dict(decision='OUT (a box INVALID: packed policy stays)')
        else:
            d[e] = dict(decision='INCOMPLETE (seeds [\'43\'] missing or n < 8: retrain only those seeds on a new box, same '
                                 'reference and commit; PLAN section 5 rule 2 as amended 31 Oct)', todo={'43': 'retrain'})
    return dict(episodes=d)


def h5(board, **eps):
    """eps: ep -> (n, mean, sd); packed = the board pack's draw."""
    P = P7 if board == 'pack7' else P8
    return {e.lstrip('e'): dict(n=n, mean=m, sd=s, min=round(m - 2 * s, 4), p20=m, packed=P[e.lstrip('e')]) for e, (n, m, s) in eps.items()}


V = lambda r, e: r['episodes'][e]['verdict']

# ---- the fixed levels and bars reproduce PLAN sections 1 and 5 ----
lv, bars = R.levels_and_bars('pack7')
need = {'1': (0.8519, 0.2387), '3': (0.9339, 0.0717), '14': (0.6452, 0.1989), '16': (0.8429, 0.0767), '25': (0.8801, 0.0988),
        '30': (0.8284, 0.2552)}
check('L1_rule6_thresholds_as_written', all((R.r4(lv[e]['mean'] + 0.03), lv[e]['sd']) == v for e, v in need.items()),
      {e: (R.r4(lv[e]['mean'] + 0.03), lv[e]['sd']) for e in need})
check('L2_spoon_thresholds', (R.r4(lv['33']['mean'] - 0.02), R.r4(lv['15']['mean'] - 0.02)) == (0.9144, 0.9397),
      (R.r4(lv['33']['mean'] - 0.02), R.r4(lv['15']['mean'] - 0.02)))
check('L3_bars_pack7', bars == {e: float(v) for e, v in P7.items()} and bars['1'] == 0.9196 and bars['33'] == 0.9401, bars)
lv8, bars8 = R.levels_and_bars('pack8')
check('L4_pack8_eval1_level_and_bar', lv8['1']['mean'] == 0.9241 and lv8['1']['sd'] == 0.017 and bars8['1'] == 0.9232
      and lv['1']['mean'] == 0.8219, (lv8['1'], bars8['1'], lv['1']))

# ---- wave 1 under pack 7: swap, keep, insurance, eval 1's extra bar; spoon pilots pass ----
r = R.apply(h5('pack7', e20=(10, 0.91, 0.03), e8=(10, 0.975, 0.01), e33=(10, 0.95, 0.008), e15=(10, 0.955, 0.006),
               e1=(10, 0.921, 0.02)), merge(e20='C', e8='C', e33='C', e15='C', e1='C'), 'pack7', 'C1RUN')
check('W1_board_swap_20', V(r, '20') == 'BOARD SWAP' and r['episodes']['20']['expected_board_effect'] == round((0.91 - 0.8948) / 20 * 0.76, 5),
      r['episodes']['20'])
check('W1_keep_8', V(r, '8') == 'KEEP' and r['episodes']['8']['rule'] == '7', r['episodes']['8']['why'])
check('W1_board_swap_33_15', V(r, '33') == 'BOARD SWAP' and V(r, '15') == 'BOARD SWAP')
check('W1_eval1_between_0.9196_and_0.9241_is_insurance', V(r, '1').startswith('INSURANCE') and r['episodes']['1']['bar'] == 0.9241,
      r['episodes']['1']['why'])
check('W1_spoon_propose_wave2', r['spoon_stratum'].startswith('PROPOSE wave 2'), r['spoon_stratum'])
check('W1_pack9_inputs', sorted(r['pack9']['swap'], key=int) == ['15', '20', '33'] and list(r['pack9']['insurance_if_owner_accepts']) == ['1']
      and 'runs/C1RUN/results/submission/results/episode_000020' in r['pack9']['swap']['20'], r['pack9'])
check('W1_strata', r['strata']['spoon']['episodes'] == 2 and r['strata']['masses']['episodes'] == 3, r['strata'])

# ---- boundaries: mean == bar is a swap; mean == level + 0.03 with sd == level sd is insurance; sd above is keep ----
r = R.apply(h5('pack7', e20=(10, 0.8948, 0.05), e3=(10, 0.9339, 0.0717), e14=(10, 0.70, 0.20), e16=(10, 0.85, 0.07)),
            merge(e20='C', e3='C', e14='C', e16='C'), 'pack7')
check('B1_mean_equal_bar_swaps', V(r, '20') == 'BOARD SWAP', r['episodes']['20']['why'])
check('B2_insurance_at_threshold', V(r, '3').startswith('INSURANCE'), r['episodes']['3']['why'])
check('B3_sd_above_level_sd_keeps', V(r, '14') == 'KEEP', r['episodes']['14']['why'])
check('B4_insurance_16', V(r, '16').startswith('INSURANCE') and r['episodes']['16']['expected_board_effect'] < 0, r['episodes']['16'])
check('B5_spoon_no_reading_without_pilots', r['spoon_stratum'].startswith('NO READING'), r['spoon_stratum'])

# ---- rule 4: n < 8 or no confirmation -> INCOMPLETE (only C1 repeated); training INCOMPLETE / OUT passed through ----
r = R.apply(h5('pack7', e20=(7, 0.95, 0.01)), merge(e20='C', e8='C', e33='I', e15='O'), 'pack7')
check('R4_n7_incomplete', V(r, '20') == 'INCOMPLETE' and r['episodes']['20']['rule'] == '4', r['episodes']['20']['why'])
check('R4_no_confirmation_incomplete', V(r, '8') == 'INCOMPLETE' and 'repeat only the confirmation' in r['episodes']['8']['why'])
check('R2_training_incomplete_passed_through', V(r, '33') == 'INCOMPLETE (training)' and r['episodes']['33']['todo'], r['episodes']['33'])
check('R3_out_keeps', V(r, '15') == 'KEEP' and r['episodes']['15']['rule'] == '3')
check('R9_pilot_without_reading', r['spoon_stratum'].startswith('NO READING') and 'pilot 33' in r['spoon_stratum']
      and 'pilot 15' in r['spoon_stratum'], r['spoon_stratum'])

# ---- rule 9 variants ----
r = R.apply(h5('pack7', e33=(10, 0.91, 0.01), e15=(10, 0.93, 0.01)), merge(e33='C', e15='C'), 'pack7')
check('R9_both_below_closed', r['spoon_stratum'].startswith('CLOSED'), (r['spoon_pilots'], r['spoon_stratum']))
check('R9_both_below_also_keep', V(r, '33') == 'KEEP' and V(r, '15') == 'KEEP')
r = R.apply(h5('pack7', e33=(10, 0.95, 0.01), e15=(10, 0.93, 0.01)), merge(e33='C', e15='C'), 'pack7')
check('R9_one_below_owner', r['spoon_stratum'].startswith('OWNER DECIDES'), r['spoon_stratum'])
r = R.apply(h5('pack7', e33=(10, 0.9142, 0.01), e15=(10, 0.95, 0.01)), merge(e33='C', e15='C'), 'pack7')
check('R9_rounding_window_ambiguous', r['spoon_stratum'].startswith('AMBIGUOUS') and r['spoon_pilots']['33']['reading'] == 'AMBIGUOUS',
      r['spoon_pilots'])
r = R.apply(h5('pack7', e33=(10, 0.9397, 0.01), e15=(10, 0.9397, 0.01)), merge(e33='C', e15='C'), 'pack7')
check('R9_at_threshold_not_below', r['spoon_stratum'].startswith('PROPOSE'), r['spoon_pilots'])

# ---- pack 8 on the board: eval 1's bar 0.9232 and the 0.9241 carve bar; no insurance possible ----
r = R.apply(h5('pack8', e1=(10, 0.9235, 0.01)), merge(e1='C'), 'pack8')
check('P8_eval1_0.9235_keep', V(r, '1') == 'KEEP' and r['episodes']['1']['insurance_needs']['mean'] == 0.9541, r['episodes']['1'])
r = R.apply(h5('pack8', e1=(10, 0.9241, 0.01)), merge(e1='C'), 'pack8')
check('P8_eval1_0.9241_swap', V(r, '1') == 'BOARD SWAP', r['episodes']['1']['why'])

# ---- refused inputs ----
bad = h5('pack7', e33=(10, 0.95, 0.01)); bad['33']['packed'] = 0.9319               # pack 6's draw: PACKED_TXT not pack 7's
r = R.apply(bad, merge(e33='C'), 'pack7')
check('X1_packed_column_mismatch_refused', 'refused' in r and 'PACKED_TXT' in r['refused'][0], r.get('refused'))
r = R.apply(h5('pack7', e33=(10, 0.95, 0.01), e19=(10, 0.95, 0.01)), merge(e33='C'), 'pack7')
check('X2_non_candidate_in_h5_refused', 'refused' in r and 'ep19' in r['refused'][0], r.get('refused'))
r = R.apply(h5('pack8', e1=(10, 0.95, 0.01)), merge(e1='C'), 'pack7')                # packs 7 and 8 differ only in eval 1
check('X3_board_flag_mismatch_refused', 'refused' in r, r.get('refused'))

# ---- the CLI: exit codes and output files ----
for name, H, Mg, board, rc_want in (('cli_ok', h5('pack7', e20=(10, 0.91, 0.03)), merge(e20='C'), 'pack7', 0),
                                    ('cli_refused', bad, merge(e33='C'), 'pack7', 2)):
    hf, mf, of = (f'{OUT}/{name}_{k}.json' for k in ('h5', 'merge', 'rule'))
    json.dump(H, open(hf, 'w')); json.dump(Mg, open(mf, 'w'))
    p = subprocess.run([sys.executable, '-I', f'{REPO}/tools/mass_eval_rule.py', '--h5', hf, '--merge', mf, '--board', board,
                        '--out', of], capture_output=True, text=True)
    check(f'C_{name}_exit_{rc_want}', p.returncode == rc_want and os.path.exists(of), (p.returncode, p.stdout[-300:], p.stderr[-300:]))

# ---- F1 in tools/mass_eval_merge.py: training-box summaries -> INCOMPLETE / CANDIDATE ----
TAB = f'{REPO}/docs/research/work/masses-eval-20261031/packed_refs.json'


def box(run, status, seeds, retrain=(), unchecked=()):
    eps = {'20': dict(status=status, seeds={s: (dict(n=n, mean=m, sd=0.01, min=m - 0.02, checkpoint=f'/content/x/{s}') if n else dict(n=0))
                                            for s, (n, m) in seeds.items()},
                      retrain_seeds=list(retrain), unchecked=list(unchecked))}
    f = f'{OUT}/sum_{run}.json'; json.dump(dict(run=run, mode='glock', episodes=eps), open(f, 'w')); return f


def run_merge(name, files):
    o = f'{OUT}/merge_{name}.json'
    p = subprocess.run([sys.executable, '-I', f'{REPO}/tools/mass_eval_merge.py', '--table', TAB, '--out', o] + files,
                       capture_output=True, text=True)
    return (json.load(open(o))['episodes']['20'] if p.returncode == 0 else None), p


x, p = run_merge('thin43', [box('mevA', 'INCOMPLETE', {'42': (10, 0.91), '43': (6, 0.95)}, retrain=['43'])])
check('F1_thin_seed_incomplete', x and x['decision'].startswith('INCOMPLETE') and '43' in x['todo'] and 'retrain' in x['todo']['43']
      and 'retrain only' in x['decision'], (x, p.stderr[-200:]))
x, p = run_merge('missing43', [box('mevA', 'INCOMPLETE', {'42': (10, 0.91), '43': (0, 0)}, retrain=['43'])])
check('F1_missing_seed_incomplete', x and x['decision'].startswith('INCOMPLETE') and list(x['todo']) == ['43'], x)
x, p = run_merge('retrained43', [box('mevA', 'INCOMPLETE', {'42': (10, 0.91), '43': (6, 0.95)}, retrain=['43']),
                                 box('mevB', 'VERIFIED', {'43': (10, 0.93)})])
check('F1_after_retrain_candidate', x and x['decision'] == 'CANDIDATE' and x['seed'] == '43' and x['run'] == 'mevB', x)
x, p = run_merge('one_box_one_seed', [box('mevS1a', 'VERIFIED', {'42': (10, 0.91)})])
check('F1_single_seed_no_fallback', x and x['decision'].startswith('INCOMPLETE') and 'not trained' in x['todo']['43'], x)
x, p = run_merge('unchecked', [box('mevA', 'INCOMPLETE', {'42': (10, 0.91), '43': (10, 0.92)}, unchecked=['packed header'])])
check('F1_unchecked_rerun_verify_not_retrain', x and x['decision'].startswith('INCOMPLETE')
      and all('re-run tools/mass_eval_verify.py' in t for t in x['todo'].values()), x)
x, p = run_merge('both_ok', [box('mevA', 'VERIFIED', {'42': (10, 0.91), '43': (10, 0.913)})])
check('F1_rule2_within_0.005_lower_sd_then_first', x and x['decision'] == 'CANDIDATE' and x['seed'] == '42', x)
x, p = run_merge('invalid', [box('mevA', 'INVALID', {'42': (10, 0.91), '43': (10, 0.92)})])
check('F1_invalid_out', x and x['decision'].startswith('OUT'), x)
sys.path.insert(0, f'{REPO}/tools'); from mass_eval_verify import rule2   # noqa: E402
check('F1_rule2_ignores_n_below_8', rule2({'42': dict(n=7, mean=0.99, sd=0.0), '43': dict(n=8, mean=0.5, sd=0.1)}, ['42', '43']) == '43'
      and rule2({'42': dict(n=7, mean=0.99, sd=0.0)}, ['42', '43']) is None)
check('R1_rule2_exact_0.005_gap_is_within', rule2({'42': dict(n=10, mean=0.905, sd=0.02), '43': dict(n=10, mean=0.9, sd=0.01)},
      ['42', '43']) == '43' and all(rule2({'42': dict(n=10, mean=round(a / 1e4 + .005, 4), sd=0.02), '43': dict(n=10, mean=a / 1e4, sd=0.01)},
      ['42', '43']) == '43' for a in range(5000, 9950)) and rule2({'42': dict(n=10, mean=0.9051, sd=0.02),
      '43': dict(n=10, mean=0.9, sd=0.01)}, ['42', '43']) == '42')

L = [f'{"PASS" if x["ok"] else "FAIL"} {x["name"]}' + ('' if x['ok'] else f': {x["detail"]}') for x in res]
open(f'{OUT}/rule_tests.txt', 'w').write('\n'.join(L) + '\n')
json.dump(dict(ok=all(x['ok'] for x in res), n=len(res), results=res), open(f'{OUT}/rule_tests.json', 'w'), indent=1)
print('\n'.join(L)); print(f'{sum(x["ok"] for x in res)} / {len(res)} pass')
sys.exit(0 if all(x['ok'] for x in res) else 1)
