"""Verification round 2, blocking item 2: the verifier's git cases under the strace auditor (one JSON line per case).

  GMG_MODE=clean python git_cases.py > build/b0/git_cases_r3.jsonl

Builds the synthetic tree of test_guard.py, runs each case under tools/strace_audit.py and prints forbidden_opens.
"""
import json, os, shutil, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import test_guard as tg
tg.setUpModule()
T = tg.T
try:
    t = tg.TestStrace()
    tag = os.path.basename(T['D'])
    script = tg._w(os.path.join(os.path.dirname(T['D']), f'num_{tag}.py'), tg.UNGUARDED)
    log = os.path.join(os.path.dirname(T['D']), f'num_{tag}.strace')
    copy = f'{T["D"]}/misc/innocent.bin'; shutil.copyfile(T['det'], copy)
    ops = [['read', T['det']], ['read', copy], ['read', T['other']], ['write', f'{T["D"]}/misc/w.txt']]
    git = shutil.which('git')
    cases = {'control': [sys.executable, '-I', script, json.dumps(ops)],
             'control + execv git --version': [sys.executable, '-I', script, json.dumps(ops + [['execv', git, ['git', '--version']]])],
             'git hash-object <det copy> <unlisted>': [git, 'hash-object', copy, T['other']],
             "sh -c 'exec git hash-object --stdin < <det copy>'": ['sh', '-c', f'exec git hash-object --stdin < {copy}']}
    for k, cmd in cases.items():
        r, rep = t._audit(cmd, log)
        print(json.dumps(dict(case=k, forbidden_opens=rep['forbidden_opens'], git=rep['git'],
                              reasons=sorted({f['reason'][:60] for x in ('forbidden', 'unlisted', 'writes_outside_run') for f in rep[x]}))))
finally:
    tg.tearDownModule()
