"""Fixture tests of tools/dr_verdict.py (swap rule, PREREG sections 4 and 6) and tools/dr_eval_verify.py's D-line check
(PREREG 1.2). Synthetic numbers only (no rollout, no ground truth). Usage: python -I test_verdict.py [OUT.json]"""
import copy, json, math, os, subprocess, sys, tempfile

R = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '../../../../../..'))
sys.path.insert(0, f'{R}/tools')
import dr_verdict as V        # noqa: E402
import dr_eval_verify as DV   # noqa: E402

E = '14'
SHA_D, SHA_P = 'd' * 64, '05b13510629eb5333fc7756b1d927275db0926005af35d09ad96e4648d9cd27e'
T = dict(md5='10d5f3ba6b7368ed30dad9d0c9c30df1', packed_sha256=SHA_P)
MERGE = dict(decision='CANDIDATE', run='20261101-drG-abc1234', seed='42', sha256=SHA_D, store_checkpoint='x', stats={})


def ro(draw, svr, rpe, sha, ok=True, scored=True, mppe=1.0, auc=None):
    return dict(path=f'/dl/r{draw}/ep14/episode_000014.parquet', draw=draw, scored=scored, checkpoint_sha256=sha,
                own_ref_check=dict(ok=ok), vs=dict(P=dict(sim_vs_ref=svr, RPE=rpe, MPPE=mppe, AUC=svr if auc is None else auc,
                                                         audit_fail=False, objects={'blue_cup': dict(AUC=svr)})))


def base(n_conf=10, n_pack=10):
    conf = [ro(i, 0.93, 2.0, SHA_D) for i in range(1, n_conf + 1)]
    pack = [ro(i, 0.90, 2.5, SHA_P) for i in range(1, n_pack + 1)]
    pack[3]['vs']['P'].update(sim_vs_ref=0.55, RPE=8.0)           # one packed failure
    return dict(conf=dict(own='P', rollouts=conf), packed=dict(own='P', rollouts=pack),
                old=dict(own='P', rollouts=[ro(0, 0.9094, 3.39, SHA_P)]))


CHECKS = [('final_eval', dict(ok=True, dr_eps=[14], episodes={E: dict(checkpoint_sha256=SHA_D)})),
          ('h5', dict(ok=True, dr_eps=[14], episodes={E: dict(checkpoint_sha256=SHA_D)}))]
REFS = {'P': {T['md5']}}


def run(sets=None, merge=MERGE, checks=CHECKS, refs=REFS, n=10):
    return V.episode(E, merge, T, base() if sets is None else sets, refs, checks, n)


cases = []


def case(name, want, got, extra_ok=True, note=''):
    lab = got[0]
    ok = (lab == want) and extra_ok
    cases.append(dict(case=name, want=want, got=lab, ok=ok, why=got[1][:3], note=note))


# --- PASS and each clause failing
case('pass', 'PASS', run())
s = base(); [r['vs']['P'].update(sim_vs_ref=0.80) for r in s['conf']['rollouts']]
g = run(s); case('a_fails (mean 0.80 < 0.865; s fails too)', 'NO-SWAP', g, g[2]['a']['holds'] is False)
s = base(); [s['conf']['rollouts'][i]['vs']['P'].update(RPE=6.0) for i in (0, 1)]
g = run(s); case('b_fails (2/10 > 1/10)', 'NO-SWAP', g, g[2]['b']['holds'] is False and g[2]['a']['holds'] and g[2]['c']['holds'])
s = base(); [r['vs']['P'].update(RPE=2.6) for r in s['conf']['rollouts']]
g = run(s); case('c_fails (median 2.6 > 2.5)', 'NO-SWAP', g, g[2]['c']['holds'] is False and g[2]['b']['holds'])
s = base(); s['conf']['rollouts'][0]['vs']['P'].update(sim_vs_ref=0.85)
g = run(s); case('s_fails (draw 1 0.85 < 0.9094-0.05)', 'NO-SWAP', g, g[2]['s']['holds'] is False and g[2]['a']['holds'])
s = base(); s['conf']['rollouts'][0]['vs']['P'].update(sim_vs_ref=0.8594)
g = run(s); case('s_boundary (draw 1 = bar, holds)', 'PASS', g, g[2]['s']['holds'])
s = base(); [r['vs']['P'].update(sim_vs_ref=0.865) for r in s['conf']['rollouts']]
g = run(s); case('a_tie (equal means, holds)', 'PASS', g, abs(g[2]['a']['margin']) < 1e-9)
# a fails alone
s = base(); [r['vs']['P'].update(sim_vs_ref=0.86) for r in s['conf']['rollouts']]
g = run(s); case('a_fails_alone (0.86 < 0.865)', 'NO-SWAP', g, g[2]['a']['holds'] is False and all(g[2][c]['holds'] for c in 'bcs'))
# --- INCOMPLETE
case('incomplete_conf_9', 'INCOMPLETE', run(base(n_conf=9)))
case('incomplete_packed_9', 'INCOMPLETE', run(base(n_pack=9)))
s = base(); s['old']['rollouts'] = []
case('incomplete_no_old', 'INCOMPLETE', run(s))
case('incomplete_merge', 'INCOMPLETE', run(merge=dict(decision='INCOMPLETE (seeds [43] missing)', todo={'43': 'retrain'})))
case('incomplete_no_merge_entry', 'INCOMPLETE', run(merge=None))
# --- INVALID
case('invalid_training_out', 'INVALID', run(merge=dict(decision='OUT (a box INVALID: packed policy stays)')))
case('invalid_one_pack_check', 'INVALID', run(checks=CHECKS[:1]))
case('invalid_pack_check_refused', 'INVALID', run(checks=[CHECKS[0], ('h5', dict(ok=False, failures=['x']))]))
case('invalid_pack_check_other_sha', 'INVALID', run(checks=[CHECKS[0], ('h5', dict(ok=True, dr_eps=[14], episodes={E: dict(checkpoint_sha256='e' * 64)}))]))
case('invalid_pack_check_not_dr', 'INVALID', run(checks=[CHECKS[0], ('h5', dict(ok=True, dr_eps=[16], episodes={}))]))
s = base(); s['conf']['rollouts'][4]['checkpoint_sha256'] = SHA_P
case('invalid_conf_sha (packed checkpoint in conf)', 'INVALID', run(s))
s = base(); s['packed']['rollouts'][2]['checkpoint_sha256'] = SHA_D
case('invalid_packed_sha', 'INVALID', run(s))
s = base(); s['old']['rollouts'][0]['checkpoint_sha256'] = 'f' * 64
case('invalid_old_sha', 'INVALID', run(s))
s = base(); s['conf']['rollouts'][6]['own_ref_check'] = dict(ok=False)
case('invalid_own_ref', 'INVALID', run(s))
case('invalid_ref_md5', 'INVALID', run(refs={'P': {'0' * 32}}))
case('invalid_ref_md5_two_files', 'INVALID', run(refs={'P': {T['md5'], '0' * 32}}))
# --- NaN
s = base(); s['conf']['rollouts'][5]['vs']['P']['RPE'] = float('nan')
g = run(s); case('nan_in_a_draw_10 (not scored -> 9 -> INCOMPLETE)', 'INCOMPLETE', g)
s = base(n_conf=11); s['conf']['rollouts'][5]['vs']['P']['RPE'] = float('nan')
g = run(s); case('nan_in_a_draw_11 (10 scored -> decided)', 'PASS', g, g[3]['new']['n'] == 10)
s = base(); s['old']['rollouts'][0]['vs']['P']['sim_vs_ref'] = float('inf')
case('inf_old_draw (not scored -> INCOMPLETE)', 'INCOMPLETE', run(s))
n_ = dict(mean_raw=0.9, fail_raw=0.0, median_rpe_raw=float('nan')); k_ = dict(mean_raw=0.9, fail_raw=0.0, median_rpe_raw=2.0)
cl, err = V.clauses_of(n_, k_, 0.9, 0.9)
cases.append(dict(case='nan_clause_value (clauses_of -> None -> INVALID)', want='None', got=str(cl), ok=cl is None and 'not finite' in err, why=[err]))
# --- draw 1 failed call
s = base(n_conf=11); s['conf']['rollouts'][0].update(scored=False, error='evaluation failed'); s['conf']['rollouts'][0]['vs'] = {}
s['conf']['rollouts'][1]['vs']['P']['sim_vs_ref'] = 0.95
g = run(s); case('draw1_failed_call (r1 unscored -> draw 1 = r2)', 'PASS', g, g[2]['s']['new_draw1_r'] == 2 and g[2]['s']['new_draw1'] == 0.95)
s = base(n_conf=11); s['conf']['rollouts'][0].update(scored=False); s['conf']['rollouts'][0]['vs'] = {}
s['conf']['rollouts'][1]['vs']['P']['sim_vs_ref'] = 0.80
g = run(s); case('draw1_failed_call_then_low (r2 0.80 < bar -> NO-SWAP)', 'NO-SWAP', g, g[2]['s']['holds'] is False and g[2]['s']['new_draw1_r'] == 2)
s = base(n_conf=10); del s['conf']['rollouts'][0]
case('draw1_missing_file_9_left (INCOMPLETE)', 'INCOMPLETE', run(s))
# --- equal floor (both fail everything) reads PASS on equal numbers; the CLI adds the note
s = base(); [r['vs']['P'].update(sim_vs_ref=0.45, RPE=15.0) for r in s['conf']['rollouts'] + s['packed']['rollouts']]
s['old']['rollouts'][0]['vs']['P']['sim_vs_ref'] = 0.46
g = run(s); case('equal_floor (PASS on two floors, note in CLI)', 'PASS', g)

# --- CLI end to end (files)
d = tempfile.mkdtemp(prefix='drv_')
mg = dict(episodes={'14': MERGE, '16': dict(decision='OUT (a box INVALID: packed policy stays)')})
json.dump(mg, open(f'{d}/merge.json', 'w'))
sc = dict(ep=14, refs={'P': dict(md5=T['md5'])}, sets=base()); json.dump(sc, open(f'{d}/s14.json', 'w'))
for n, c in CHECKS:
    json.dump(c, open(f'{d}/{n}.json', 'w'))
p = subprocess.run([sys.executable, '-I', f'{R}/tools/dr_verdict.py', '--merge', f'{d}/merge.json', '--table',
                    f'{R}/docs/research/work/masses-eval-20261031/packed_refs.json', '--score', f'{d}/s14.json',
                    '--pack-check', f'{d}/final_eval.json', '--pack-check', f'{d}/h5.json', '--out', f'{d}/v.json'], capture_output=True, text=True)
vo = json.load(open(f'{d}/v.json')) if os.path.exists(f'{d}/v.json') else {}
lab = {e: x['label'] for e, x in vo.get('episodes', {}).items()}
cases.append(dict(case='cli (14 PASS, 16 INVALID, 25/30/33 INCOMPLETE; pack9b = [14])', want="{'14': 'PASS', '16': 'INVALID', '25': 'INCOMPLETE', '30': 'INCOMPLETE', '33': 'INCOMPLETE'}",
                  got=str(lab), ok=p.returncode == 0 and lab == {'14': 'PASS', '16': 'INVALID', '25': 'INCOMPLETE', '30': 'INCOMPLETE', '33': 'INCOMPLETE'}
                  and list(vo.get('pack9b', {})) == ['14'] and vo['episodes']['14']['old_vs_pack7_summary']['matches'], why=p.stdout.splitlines()[:2]))

# --- dr_eval_verify D-line check
L0 = ('v2d FC_DR_RESET: sampled resets perturbed by +-1.5 mm, +-0.015 rad (rotation vector per axis), fingers +-0.01 rad; '
      '2 objects, 44 finger joints, 4096 worlds, seed {s}')
TAIL = '; skip immediate starts (FC_DR_SKIP_IMMEDIATE: deployment-exact starts not perturbed)'


def dl(lines, seed, skip, n_obj=2):
    f = f'{d}/train_{len(cases)}.log'; open(f, 'w').write(''.join(x + '\n' for x in ['[train] start'] + lines + ['[train] step 1']))
    return DV.dr_lines(f, seed, n_obj, skip)


for name, lines, seed, skip, want in [
        ('dline_glock_ok', [L0.format(s=42)], 42, False, True),
        ('dline_std_ok', [L0.format(s=43) + TAIL], 43, True, True),
        ('dline_two_builds_ok', [L0.format(s=42), L0.format(s=42)], 42, False, True),
        ('dline_missing', [], 42, False, False),
        ('dline_wrong_seed', [L0.format(s=43)], 42, False, False),
        ('dline_std_without_tail', [L0.format(s=42)], 42, True, False),
        ('dline_glock_with_tail', [L0.format(s=42) + TAIL], 42, False, False),
        ('dline_wrong_bounds', [L0.format(s=42).replace('+-1.5 mm', '+-3.0 mm')], 42, False, False),
        ('dline_wrong_objects', [L0.format(s=42).replace('2 objects', '3 objects')], 42, False, False),
        ('dline_old_patch_format_std (609582a: no tail)', [L0.format(s=42)], 42, True, False)]:
    ok_, bad_, _ = dl(lines, seed, skip)
    cases.append(dict(case=name, want=str(want), got=str(ok_), ok=ok_ == want, why=bad_[:2]))
ok_, bad_, _ = DV.dr_lines(f'{d}/no_such.log', 42, 2, False)
cases.append(dict(case='dline_no_log', want='False', got=str(ok_), ok=ok_ is False, why=bad_[:1]))
h, log = DV.expected_hook()
cases.append(dict(case='expected_hook (repo patch writes v2d_dr.py with the skip flag)', want='md5', got=str(h), ok=bool(h), why=[log[-100:]]))

npass = sum(c['ok'] for c in cases)
for c in cases:
    print(('PASS ' if c['ok'] else 'FAIL ') + f"{c['case']}: want {c['want']} got {c['got']} :: {' | '.join(map(str, c['why']))[:220]}")
print(f'{npass} / {len(cases)} pass')
if len(sys.argv) > 1:
    json.dump(dict(n=len(cases), passed=npass, cases=cases), open(sys.argv[1], 'w'), indent=1, default=str)
sys.exit(0 if npass == len(cases) else 1)
