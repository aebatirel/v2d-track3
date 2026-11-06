"""Assertions on the injected-stall mock (run_timeout_mock.sh). usage: timeout_check.py MR OUT.json
  E1 the stub hung exactly the 3 chosen evaluations (hang_audit.log), one of them ignoring SIGTERM;
  E2 their eval_rc.txt: 124, 124 and 137 (timeout -k 60 killed the one that ignored SIGTERM); every other evaluation 0;
  E3 timing: the 124 ones end ~EVAL_TIMEOUT (4 s) after they start, the 137 one ~4 + 60 s after (the -k grace);
  E4 verify.json: VERIFIED (a cut is not a load/config failure) and eval_timeouts names exactly those 3 cells;
  E5 the verdict line (verdict.txt and the RESULT line in job.log) carries the timeouts right after the label, per cell
     and per arm, and summary.json eval_timeouts holds them;
  E6 the cut rollouts are not scored (those cells have 9 scored rollouts, not 10) and the rule still runs on n >= 8;
  E7 the job ends rc 0 and pushes once.
"""
import glob, json, os, re, sys
MR, OUT = sys.argv[1], sys.argv[2]
C = f'{MR}/content'; R = f'{C}/results'; res, fails = {}, []


def ok(name, cond, detail=''):
    res[name] = dict(ok=bool(cond), detail=detail)
    if not cond:
        fails.append(name)


want = {f'{R}/mass1s42_glock_public/ep2/best/r3': ('124', False), f'{R}/mass1s43_glock_public/ep2/curve/policy_9998336/r2': ('124', False),
        f'{R}/mass0s43_glock_public/ep12/best/r7': ('137', True)}
hang = [json.loads(x) for x in open(f'{MR}/hang_audit.log')] if os.path.exists(f'{MR}/hang_audit.log') else []
got = {os.path.dirname(h['out']): h for h in hang}
ok('E1_three_hangs', sorted(got) == sorted(want) and all(got[k]['ignores_sigterm'] == v[1] for k, v in want.items()),
   [(k.replace(MR, 'MR'), h['ignores_sigterm']) for k, h in got.items()])
rcs = {os.path.dirname(f): open(f).read().strip() for f in glob.glob(f'{R}/mass*_glock_public/ep*/best/r*/eval_rc.txt')
       + glob.glob(f'{R}/mass*_glock_public/ep*/curve/policy_*/r*/eval_rc.txt')}
ok('E2_exit_codes', all(rcs.get(k) == v[0] for k, v in want.items()) and all(v == '0' for k, v in rcs.items() if k not in want)
   and len(rcs) == 8 * (10 + 21), dict(n=len(rcs), injected={k.replace(MR, 'MR'): rcs.get(k) for k in want},
                                         others=sorted({v for k, v in rcs.items() if k not in want})))
dt = {k: round(os.path.getmtime(f'{k}/eval_rc.txt') - got[k]['t'], 1) for k in want if k in got and k in rcs}
ok('E3_timing', len(dt) == 3 and all((60 <= v <= 90) if want[k][1] else (2 <= v <= 20) for k, v in dt.items()),
   dict(seconds_from_hang_start_to_exit={k.replace(MR, 'MR'): v for k, v in dt.items()}))
V = json.load(open(f'{R}/mass_check/verify.json'))
exp = {'ep2/mass1/s42': (1, 0), 'ep2/mass1/s43': (0, 1), 'ep12/mass0/s43': (1, 0)}
ok('E4_verify_counts', V['ok'] and sorted(V['eval_timeouts']) == sorted(exp)
   and all((V['eval_timeouts'][k]['best'], V['eval_timeouts'][k]['curve']) == v for k, v in exp.items()),
   dict(ok=V['ok'], eval_timeouts={k: {x: v[x] for x in ('best', 'best_rc', 'curve', 'curve_rc')} for k, v in V['eval_timeouts'].items()}))
S = json.load(open(f'{R}/mass_check/summary.json')); line = open(f'{R}/mass_check/verdict.txt').read().strip()
job = open(f'{C}/job.log').read(); res_line = [x for x in job.splitlines() if 'mass_check RESULT:' in x]
flag = re.match(r'^(ADOPT|NOT ADOPTED|INCOMPLETE|INVALID) \[EVAL TIMEOUTS in 3 cell\(s\): ([^\]]*)\]', line)
ok('E5_reported_after_label', flag is not None and S['verdict'] == flag.group(1)
   and 'per arm best/curve mass0 1/0, mass1 1/1' in flag.group(2)
   and all(f'{k} best {b}/10 curve {c}/21' in flag.group(2) for k, (b, c) in exp.items())
   and sorted(S['eval_timeouts']['cells_cut']) == sorted(exp) and len(res_line) == 1 and '[EVAL TIMEOUTS in 3 cell(s)' in res_line[0],
   dict(verdict_line=line[:420], per_arm=S['eval_timeouts']['per_arm']))
n = {k: (c['auc']['n'], c['n_rollouts']) for k, c in S['cells'].items()}
ok('E6_cut_rollouts_unscored', all(n[k] == ((9, 10) if exp.get(k, (0, 0))[0] else (10, 10)) for k in n) and S['verdict'] in ('ADOPT', 'NOT ADOPTED'),
   dict(scored_of_rollouts=n, verdict=S['verdict']))
hf = open(f'{MR}/hf.log').read().splitlines()
ok('E7_rc0_one_push', open(f'{MR}/rc.txt').read().strip() == 'rc=0' and sum(1 for x in hf if x.startswith('hf upload')) == 1,
   open(f'{MR}/rc.txt').read().strip())
json.dump(dict(ok=not fails, failures=fails, checks=res, note='mock scores are synthetic; this tests the timeout plumbing only'),
          open(OUT, 'w'), indent=1)
print(('ALL CHECKS PASS' if not fails else f'FAILED: {fails}') + f' ({len(res)} checks)')
sys.exit(0 if not fails else 1)
