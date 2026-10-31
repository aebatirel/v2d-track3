"""Assertions on one eval-10 V4p retrain mock run (2026-10-31). Usage: check.py MR EXPECT [RUN_ID] [--rerun SEEDS]
EXPECT: SWAP-ELIGIBLE | NO-SWAP | INCOMPLETE | INVALID (a verdict run, rc 0) or STOP:<substring of the STOPPED reason> (rc 1).
Prints one line per check and a JSON summary; exit 1 if any check fails."""
import glob, json, os, sys
MR, EXPECT = sys.argv[1], sys.argv[2]
RID = sys.argv[3] if len(sys.argv) > 3 and not sys.argv[3].startswith('--') else '20261031-e10v-mocksha'
RERUN = sys.argv[sys.argv.index('--rerun') + 1].split() if '--rerun' in sys.argv else None
C = f'{MR}/content'; G = f'{C}/results/ev10_v4p'; ST = f'{MR}/store/runs/{RID}'
GL = '--single_hand 1 --mcp_first 1 --close 10 --palm_clear -0.001 --wrap_where_held 1 --snap 1 --approach_cm 15'.split()
res, bad = [], []


def ok(name, cond, info=''):
    res.append(dict(check=name, ok=bool(cond), info=str(info)[:300])); print(('ok   ' if cond else 'FAIL ') + name + (f'  [{info}]' if info else ''))
    if not cond:
        bad.append(name)


def jl(f):
    return [json.loads(x) for x in open(f)] if os.path.exists(f) else []


rc = open(f'{MR}/rc.txt').read().strip()
hf = jl(f'{MR}/hf.log'); dl = [x for x in hf if x['kind'] == 'file']; up = [x for x in hf if x['kind'] == 'upload']
ok('no store listing (single-file downloads only)', not [x for x in hf if x['kind'] == 'LISTING'], len(dl))
bad_dl = [x['path'] for x in dl if x.get('result') != 'ok' and 'MOCK_HIDE' not in x.get('result', '')]
ok('every download succeeded (files hidden by MOCK_HIDE excepted)', not bad_dl, bad_dl[:4])
ok('exactly one store upload (the final push)', len(up) == 1, up)
ok('hands_mp / hand_refine / perc2 / score_registered never ran', not os.path.exists(f'{MR}/UNEXPECTED.log'), jl(f'{MR}/UNEXPECTED.log')[:2])
ok('nothing written under the packed names refs/glockt/ep10, refs/perc2mck/ep10, results/glock_public/ep10',
   not [p for p in ('refs/glockt/ep10', 'refs/perc2mck/ep10', 'results/glock_public/ep10', 'refs/glock/ep10') if os.path.exists(f'{C}/{p}')])
if EXPECT.startswith('STOP'):
    why = EXPECT.split(':', 1)[1] if ':' in EXPECT else ''
    ok('rc 1 (stopped)', rc == 'rc=1', rc)
    st = open(f'{G}/STOPPED').read() if os.path.exists(f'{G}/STOPPED') else ''
    ok(f'stopped for: {why}', why in st, st.strip())
    ok('no reference built', not glob.glob(f'{C}/refs/perc2e10v*'), glob.glob(f'{C}/refs/perc2e10v*')[:3])
    ok('no training', not os.path.exists(f'{MR}/train_audit.log'))
    ok('push holds the stop reason', os.path.exists(f'{ST}/results/ev10_v4p/STOPPED'))
else:
    ok('rc 0', rc == 'rc=0', rc)
    S = json.load(open(f'{G}/summary.json')); V = json.load(open(f'{G}/verify.json'))
    ok(f'verdict {EXPECT}', S['label'] == EXPECT, f"{S['label']}: {S['why']}")
    ok('verdict pushed to the store', os.path.exists(f'{ST}/results/ev10_v4p/summary.json'))
    ok('no depth cache in the push', not glob.glob(f'{ST}/**/depths_*', recursive=True))
    tr = jl(f'{MR}/train_audit.log'); starts = [x for x in tr if 'task' in x]
    ev = jl(f'{MR}/eval_audit.log'); mk = jl(f'{MR}/mkref_audit.log'); ra = jl(f'{MR}/ref_audit.log')
    want = RERUN if RERUN else ['42', '43']
    for s in want:
        x = [y for y in starts if f'perc2e10vs{s}_glock/' in y['run']]
        inj = [y for y in tr if y.get('injected_failure') and f'perc2e10vs{s}_glock/' in y['run']]
        if inj:
            ok(f's{s}: injected training failure (missing seed)', not x, len(inj)); continue
        ok(f's{s}: trained once', len(x) == 1, len(x))
        if not x:
            continue
        x = x[0]
        ok(f's{s}: trained on its own copy of V', f'/refs/perc2e10vs{s}_glockt/ep10' in x['task'], x['task'])
        ok(f's{s}: seed, steps', x['seed'] == s and x['steps'] == 70004736, (x['seed'], x['steps']))
        ok(f's{s}: 0.3 kg URDFs under /content/assets', all(v['mass'] == 0.3 and '/content/assets/urdf/' in v['urdf'] for v in x['loaded'].values()))
        ok(f's{s}: every CLI training key equals the packed gl10A2 config', not x['cli_vs_packed_mismatch'],
           f"{x['cli_vs_packed_mismatch']} compared {x['cli_keys_compared']}")
    if not RERUN:
        ok('V4p track rebuilt here: B0 IDENTICAL (same CPU / venvs as the expectation)', V['b0_band'] == 'IDENTICAL', V['b0_band'])
        ok('mkref ran once on the V4p track (md5 fa449903...) with the eval-10 cache and the stored hands, SPLIT=eval',
           len(mk) == 1 and mk[0]['poses_md5'] == 'fa449903630d6bb42dd79131331f4b6b' and mk[0]['depth'].endswith('cache/depth/eval/ep10/depths_fs0.5.npy')
           and mk[0]['hands_md5'] == '419c230800b727240663597916cba59e' and mk[0]['split'] == 'eval', mk)
        gls = [y for y in ra if y['stage'] == 'grasp_lock.py']
        ok('grasp-lock reference stages ran once (+ re-plan check) with the gl10A2 GL_ARGS and kp 400',
           1 <= len(gls) <= 2 and all(y['args'][:len(GL)] == GL and y['env']['GL_WRIST_KP'] == '400' for y in gls), [y['args'] for y in gls])
        ok('contact retargeting with --rest_settle 1', [y['args'] for y in ra if y['stage'] == 'contact_retarget.py'] == [['--rest_settle', '1']])
    if S['label'] in ('SWAP-ELIGIBLE', 'NO-SWAP'):
        ch = json.load(open(f'{G}/choice.json'))
        off = [y for y in ev if y['kind'] == 'official' and not y.get('injected_failure')]
        ok('confirmation: >= 10 official draws of the chosen checkpoint on the pristine evaluator',
           len(off) >= 10 and all(y['ck'] == ch['checkpoint'] for y in off) and all('v2d_clean' in (y.get('runtime_root') or '') for y in off), len(off))
        ok('10 scored confirmation draws, own-reference check ok on every scored rollout',
           S['counts']['conf']['n_scored'] >= 10 and all(V['own_ref_checks'].values()), S['counts'])
        ok('packed H5p7 draws (10) and the old packed draw scored on both references', S['counts']['packed']['n_scored'] == 10 and S['counts']['old']['n_scored'] == 1, S['counts'])
        ok('verify VERIFIED', V['ok'], V['failures'][:3])
    ok('verify / summary / score pushed', all(os.path.exists(f'{ST}/results/ev10_v4p/{f}') for f in ('verify.json', 'summary.json', 'score.json')))
json.dump(dict(mr=MR, expect=EXPECT, ok=not bad, failed=bad, checks=res), open(f'{MR}/check.json', 'w'), indent=1)
print(f'{len(res) - len(bad)}/{len(res)} checks pass' + (f'; FAILED: {bad}' if bad else ''))
sys.exit(1 if bad else 0)
