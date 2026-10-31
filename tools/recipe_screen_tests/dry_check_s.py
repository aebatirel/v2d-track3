"""Checks of the arm-S phase of the recipe-screen CPU dry run (dry_run.sh phase 2; physics-solver.md section 9): S trains
on the solved file alone in its own task tree, with C's arguments and environment; C / K / D are unchanged (same train
commands as the dry run of the code before arm S, and the same args / env as the committed module); the job refuses an
unregistered solved file; the merge gives section 9's verdict on the FAKE numbers (signal / no signal / INCOMPLETE /
INVALID), and the K_vs_C / D_vs_C verdicts do not change when S summaries are merged in.
Usage: dry_check_s.py DRY_DIR REF.parquet [OLD_DRY_DIR]"""
import copy, glob, hashlib, json, os, subprocess, sys

D, REF = sys.argv[1], sys.argv[2]; OLD = sys.argv[3] if len(sys.argv) > 3 and sys.argv[3] else None
HERE = os.path.dirname(os.path.abspath(__file__)); TOOL = os.path.join(HERE, '..', 'recipe_screen.py'); REPO = os.path.join(HERE, '..', '..')
sys.path.insert(0, os.path.join(HERE, '..'))
import recipe_screen as RS  # noqa: E402

fails = []


def check(name, ok, info=None):
    print(f"{'PASS' if ok else 'FAIL'}  {name}" + (f"  {info}" if info is not None else ''))
    if not ok:
        fails.append(name)


md5 = lambda p: hashlib.md5(open(p, 'rb').read()).hexdigest()  # noqa: E731
hv = lambda e: f'processed/sequence_id=t3_ep{e:03d}/robot_name=sharpa_wave'  # noqa: E731
EPS, SEEDS = RS.EPS, RS.SEEDS
stub = {k: {int(e): m for e, m in v.items()} for k, v in json.load(open(f'{D}/stub_ref_md5.json')).items()}
PSR = f'{D}/fakestore/runs/20261030-psolverl-04301a2/refs'
decoys = {md5(f'{PSR}/glockt/ep{e}/{hv(e)}/ref_gl_ilc.parquet') for e in EPS} | {md5(f'{PSR}/psolve/ep{e}/{hv(e)}/ref_ps.parquet') for e in (2, 12)}
base = md5(REF)
check('stand-ins: solved files differ from the base reference on ep2/12/24, equal it on ep18 (as the store), none is a decoy',
      all((stub['solved'][e] == base) == (e == 18) for e in EPS) and not decoys & set(stub['solved'].values()),
      {e: stub['solved'][e][:8] for e in EPS})
ex = open(f'{D}/exits_s.txt').read()
check('the 4 S boxes finished (job exit 0)', ex.count('exit 0') == 4, ex.split())


def trainings(box):
    out = {}
    for f in glob.glob(f'{D}/{box}/runs/screen/*/ep*-s*/stub_train.json'):
        a, c = f.split('/')[-3], f.split('/')[-2]; out[f'{a}/{c}'] = json.load(open(f))
    return out


kv = lambda t: dict(x.split('=', 1) for x in t['argv'] if '=' in x)  # noqa: E731
root = lambda box: f'{D}/{box}'  # noqa: E731
# ---- S trainings: the solved file, alone, in refs/screenS; the support stage two levels above sequence_id=
ts = {(b, k): t for b in ('sboxS42', 'sboxS43') for k, t in trainings(b).items()}
check('8 S trainings on the two S boxes (4 each), no other arm', len(ts) == 8 and all(k.startswith('S/') for _, k in ts), sorted(k for _, k in ts))
bad = []
for (b, k), t in ts.items():
    e = int(k.split('/ep')[1].split('-')[0]); tp = kv(t)['task.parquet'].strip("'")
    if tp != f'{root(b)}/refs/screenS/ep{e}/{hv(e)}' or t['task_files'] != {'ref_gl_ilc.parquet': stub['solved'][e]} or t['support_stage'] != ['stage.usda']:
        bad.append((b, k, tp, t['task_files'], t['support_stage']))
check('every S training read exactly one parquet, the solved file of its episode (psolve2 ep2/12, psolve ep18/24), in refs/screenS with its support stage',
      not bad, bad[:2])
cmds = {(b, k): open(f'{D}/{b}/results/recipe_screen/{k}/train_cmd.txt').read() for b, k in ts}
check("train_cmd.txt of every S cell names refs/screenS/ep<N>/<hive> and never refs/glockt",
      all(f"task.parquet='{root(b)}/refs/screenS/ep{k.split('/ep')[1].split('-')[0]}/" in c and 'refs/glockt' not in c for (b, k), c in cmds.items()),
      next(iter(cmds.values())).split('task.parquet=')[1].split()[0] if cmds else None)
# S = C apart from the reference: same argv (bar task.parquet / output_dir) and the same training env, same ep and seed
tc = {k: (b, t) for b in ('boxA', 'boxB') for k, t in trainings(b).items()}
diff = []
for (b, k), t in ts.items():
    bc, c = tc[k.replace('S/', 'C/')]
    norm = lambda t_, r_: sorted(x.replace(r_, '<ROOT>') for x in t_['argv'] if not x.startswith(('task.parquet=', 'output_dir=')))  # noqa: E731
    if norm(t, root(b)) != norm(c, root(bc)) or t['env'] != c['env']:
        diff.append((k, set(norm(t, root(b))) ^ set(norm(c, root(bc))), t['env'], c['env']))
check('S argv == C argv (same ep, seed; apart from task.parquet and output_dir) and S training env == C training env (no DR, FDR + VOC)',
      not diff and len(ts) == 8, diff[:2])
# ---- C / K / D unchanged
ok_args = True; info = []
old_src = subprocess.run(['git', '-C', REPO, 'show', 'HEAD:tools/recipe_screen.py'], capture_output=True, text=True, check=True).stdout
open(f'{D}/recipe_screen_HEAD.py', 'w').write(old_src)
for arm in 'CKD':
    for seed in SEEDS:
        for sub, extra in (('args', ['70004736']), ('env', [str(seed), '1.5,0.015,0.01'])):
            o = subprocess.run([sys.executable, f'{D}/recipe_screen_HEAD.py', sub, arm, *extra], capture_output=True, text=True).stdout
            n = subprocess.run([sys.executable, TOOL, sub, arm, *extra], capture_output=True, text=True).stdout
            ok_args &= (o == n); info.append(f'{arm}/{sub}/{seed}:{"=" if o == n else "DIFF"}')
check('args / env of C, K, D (seeds 42, 43): the new module prints exactly what the committed one (HEAD) prints', ok_args, ' '.join(info[:6]))
s_ae = [subprocess.run([sys.executable, TOOL, sub, 'S', *extra], capture_output=True, text=True).stdout for sub, extra in
        (('args', ['70004736']), ('env', ['42', '1.5,0.015,0.01']), ('env', ['43', '1.5,0.015,0.01']))]
c_ae = [subprocess.run([sys.executable, TOOL, sub, 'C', *extra], capture_output=True, text=True).stdout for sub, extra in
        (('args', ['70004736']), ('env', ['42', '1.5,0.015,0.01']), ('env', ['43', '1.5,0.015,0.01']))]
check('S args / env == C args / env (empty) in the module', s_ae == c_ae == ['\n', '\n', '\n'], s_ae)
epn = lambda k: int(k.split('/ep')[1].split('-')[0])  # noqa: E731
bad = [(b, k) for k, (b, t) in tc.items() if kv(t)['task.parquet'].strip("'") != f'{root(b)}/refs/glockt/ep{epn(k)}/{hv(epn(k))}'
       or t['task_files'] != {'ref_gl_ilc.parquet': base}]
check('C / K / D trainings (boxes A, B) still read the physS1 file alone in refs/glockt', not bad and len(tc) == 24, bad[:3])
if OLD:
    dif, n = [], 0
    for b in ('boxA', 'boxB'):
        for f in sorted(glob.glob(f'{OLD}/{b}/results/recipe_screen/*/ep*-s*/train_cmd.txt')):
            rel = f.split(f'{OLD}/{b}/')[1]; g = f'{D}/{b}/{rel}'; n += 1
            if not os.path.exists(g) or open(f).read().replace(f'{OLD}/{b}', '<ROOT>') != open(g).read().replace(f'{D}/{b}', '<ROOT>'):
                dif.append(rel)
    check(f'C / K / D train_cmd.txt identical to the dry run of the pre-S code ({os.path.basename(OLD)}), root path aside', not dif and n == 24, (n, dif[:3]))
    dif, n = [], 0
    for b in ('boxA', 'boxB'):
        for f in sorted(glob.glob(f'{OLD}/{b}/runs/screen/*/ep*-s*/stub_train.json')):
            rel = f.split(f'{OLD}/{b}/')[1]; g = f'{D}/{b}/{rel}'; n += 1
            o, w = json.load(open(f)), json.load(open(g)) if os.path.exists(g) else {}
            if [x.replace(f'{OLD}/{b}', '<ROOT>') for x in o['argv']] != [x.replace(f'{D}/{b}', '<ROOT>') for x in w.get('argv', [])] or o['env'] != w.get('env'):
                dif.append(rel)
    check(f'C / K / D training argv and env as received by the training process: identical to {os.path.basename(OLD)}', not dif and n == 24, (n, dif[:3]))
# ---- the S boxes' records and logs
sm = json.load(open(f'{D}/sboxS42/results/recipe_screen/summary.json'))
r = sm['refs']
check('S box summary records S_ep<N> md5 / hive / src / in_md5 for the 4 episodes (and the physS1 ep<N> records)',
      all(r.get(f'S_ep{e}', {}).get('md5') == stub['solved'][e] and r[f'S_ep{e}'].get('hive') == hv(e) for e in EPS)
      and all(r.get(f'ep{e}', {}).get('md5') == base for e in EPS)
      and all(r[f'S_ep{e}']['src'] == f"20261030-psolverl-04301a2 {RS.SOLVED_SUB[e]}/{hv(e)}/ref_ps.parquet" for e in EPS),
      {k: (v.get('md5', '')[:8], v.get('src', '').split('/')[1:3]) for k, v in r.items()})
check("the solver input (ref_in.parquet) recorded = the box's physS1 reference, for every episode",
      all(r[f'S_ep{e}']['in_md5'] == base for e in EPS))
log = open(f'{D}/sboxS42/job.log').read()
check("job log: S reference line per episode with 'solver input ... = this box's ... reference: yes'",
      sum(1 for l in log.splitlines() if 'recipe_screen S ep' in l and "reference: yes" in l) == 4)
gl = {e: md5(f'{D}/sboxS42/refs/glockt/ep{e}/{hv(e)}/ref_gl_ilc.parquet') for e in EPS}
check("S box: refs/glockt holds the physS1 files untouched (G3's psolverl copies were not pulled)", all(v == base for v in gl.values()))
check('S box: only the registered sub-folders were pulled (no G1 ep2/ep12 output, no psolverl refs/glockt)',
      not os.path.exists(f'{D}/sboxS42/refs/psolve/ep2') and not os.path.exists(f'{D}/sboxS42/refs/psolve/ep12')
      and sorted(os.listdir(f'{D}/sboxS42/refs/psolve2')) == ['ep12', 'ep2'] and sorted(os.listdir(f'{D}/sboxS42/refs/psolve')) == ['ep18', 'ep24'])
ev = [json.loads(x) for f in glob.glob(f'{D}/sbox*/eval_env.log') for x in open(f)]
check('S boxes: no training or evaluation saw FC_DR_RESET (FC_DR_RESET=9,9,9 in the job env dropped)',
      ev and all(x['FC_DR_RESET'] is None for x in ev) and all(t['env']['FC_DR_RESET'] is None for t in ts.values()), len(ev))
ms = json.load(open(f'{D}/merged_S.json')); cells = ms['cells']; vs = ms['verdicts']
sc = {k: c for k, c in cells.items() if k.startswith('S/')}
check('8 S cells present, scored, ref_set solved, ref_md5 = the stand-in solved file, config as C, no DR line, trained on refs/screenS',
      len(sc) == 8 and all(c['present'] and c['ref_set'] == 'solved' and c['ref_md5'] == stub['solved'][c['ep']] and not RS.config_problems(c, 70004736)
                           and c['dr_active'] == '' and '/refs/screenS/ep' in c['config_check']['task_parquet'] for c in sc.values()),
      {k: (c['status'], c['ref_md5'][:8]) for k, c in list(sc.items())[:2]})
# the strict box: an unregistered solved file is refused, its cells are not run
sx = json.load(open(f'{D}/sboxSX/results/recipe_screen/summary.json'))
logx = open(f'{D}/sboxSX/job.log').read()
check('REF_MD5_CHECK=1 (default): the 4 stand-in solved files are refused (not the registered md5) and the S cells are not run',
      all(c['status'] == 'not_run' for c in sx['cells'].values()) and len(sx['cells']) == 4 and logx.count('is not the registered') == 4
      and not glob.glob(f'{D}/sboxSX/runs/screen/S/*/stub_train.json') and not any(k.startswith('S_') for k in sx['refs']),
      [c['status'] for c in sx['cells'].values()])
tm = trainings('sboxM')
check('a mixed job (CELLS="C:12:42 S:12:42"): C on refs/glockt + physS1 file, S on refs/screenS + solved file',
      tm.get('C/ep12-s42', {}).get('task_files') == {'ref_gl_ilc.parquet': base} and '/refs/glockt/ep12/' in kv(tm['C/ep12-s42'])['task.parquet']
      and tm.get('S/ep12-s42', {}).get('task_files') == {'ref_gl_ilc.parquet': stub['solved'][12]} and '/refs/screenS/ep12/' in kv(tm['S/ep12-s42'])['task.parquet'],
      sorted(tm))
# ---- verdicts on the FAKE numbers
x = vs['S_vs_C']
check("S vs C = 'signal' (fake deltas +0.10 / +0.03 / -0.01 / +0.02: mean +0.035, none <= -0.05) and the action starts eval solving",
      x['verdict'] == 'signal' and abs(x['mean_delta'] - 0.035) < 0.001 and abs(x['min_delta'] + 0.01) < 0.001 and x['action'].startswith('eval solving'),
      (x['verdict'], x['mean_delta'], x['min_delta']))
check('per-episode draw sd reported for S and C (fake: C ep2 0.20, S ep2 0.12)',
      abs(x['episodes']['ep2']['draw_sd_C'] - 0.20) < 0.001 and abs(x['episodes']['ep2']['draw_sd_S'] - 0.12) < 0.001
      and all(x['episodes'][f'ep{e}']['draw_sd_S'] is not None for e in EPS), {e: (d['draw_sd_C'], d['draw_sd_S']) for e, d in x['episodes'].items()})
check('per-seed S / C AUC and chosen checkpoints reported (ep2 per seed)', all(x['episodes']['ep2']['seeds'][f's{s}'][a]['checkpoint_steps'] for s in SEEDS for a in 'CS'))
check("box records in the verdict: the solver input equals the registered base reference (stub md5s)",
      all(all(q['solver_input_is_registered_base'] for q in x['box_reference_records'][f'ep{e}']) for e in EPS))
m0 = json.load(open(f'{D}/merged.json'))['verdicts']
same = all(vs[n][f] == m0[n][f] for n in ('K_vs_C', 'D_vs_C') for f in ('verdict', 'mean_delta', 'episodes', 'missing', 'invalid')) \
    and vs['missing_cells'] == m0['missing_cells'] and vs['report_seed_selection_by_sim_vs_ref'] == m0['report_seed_selection_by_sim_vs_ref']
check('K_vs_C and D_vs_C (verdict, deltas, episodes, missing, invalid) and the C/K/D reports unchanged when the S boxes are merged in', same,
      (vs['K_vs_C']['verdict'], vs['D_vs_C']['verdict']))
txt = open(f'{D}/merged_S.txt').read()
check("verdict printout: S rows in the table and an 'S_vs_C: signal' line", 'S/ep2-s42' in txt and 'S_vs_C: signal' in txt)
xr = json.load(open(f'{D}/merged_S_registered.json'))['verdicts']['S_vs_C']
check('with the registered md5s (no --ref-md5), the stub files are caught: S vs C INVALID on every S and C cell',
      xr['verdict'] == 'INVALID' and sum(1 for k in xr['invalid'] if k.startswith(('S/', 'C/'))) == 16, sorted(xr['invalid'])[:3])
# ---- merge guards on edited copies of the summaries
sa, sb, s2, s3 = (json.load(open(f'{D}/{b}/results/recipe_screen/summary.json')) for b in ('boxA', 'boxB', 'sboxS42', 'sboxS43'))


def merged(sums, name, md5file=f'{D}/stub_ref_md5.json'):
    paths = []
    for i, s in enumerate(sums):
        p = f'{D}/sguard_{name}_{i}.json'; json.dump(s, open(p, 'w')); paths.append(p)
    subprocess.run([sys.executable, TOOL, 'verdict', *paths, '--out', f'{D}/sguard_{name}.json'] + (['--ref-md5', md5file] if md5file else []),
                   check=True, capture_output=True)
    return json.load(open(f'{D}/sguard_{name}.json'))['verdicts']


g = copy.deepcopy(s3); del g['cells']['S/ep24-s43']
v = merged([sa, sb, s2, g], 'smiss')
check("a missing S cell -> S vs C 'INCOMPLETE', the cell listed, no mean; action stop", v['S_vs_C']['verdict'] == 'INCOMPLETE'
      and v['S_vs_C']['missing'] == ['S/ep24-s43'] and v['S_vs_C']['mean_delta'] is None and v['S_vs_C']['action'].startswith('stop'), v['S_vs_C']['missing'])
g = copy.deepcopy(sb); g['cells']['C/ep2-s43'].update(status='train_failed', present=False)
v = merged([sa, g, s2, s3], 'cmiss')
check("a missing C cell -> S vs C 'INCOMPLETE' listing it", v['S_vs_C']['verdict'] == 'INCOMPLETE' and v['S_vs_C']['missing'] == ['C/ep2-s43'], v['S_vs_C']['missing'])
v = merged([sa, sb, s2], 'sbox')
check("one S box only (seed 43 missing) -> INCOMPLETE with the 4 seed-43 S cells", v['S_vs_C']['verdict'] == 'INCOMPLETE'
      and v['S_vs_C']['missing'] == [f'S/ep{e}-s43' for e in EPS], v['S_vs_C']['missing'])
g = copy.deepcopy(s3); g['cells']['S/ep18-s43']['auc']['mean'] -= 0.08   # ep18: -0.01 -> -0.05 exactly
g2 = copy.deepcopy(s2); g2['cells']['S/ep2-s42']['auc']['mean'] += 0.05; g['cells']['S/ep2-s43']['auc']['mean'] += 0.05   # mean stays >= +0.03
v = merged([sa, sb, g2, g], 'slo')
check("ep18 delta exactly -0.05 with a mean >= +0.03 -> 'no signal' (no delta <= -0.05)", v['S_vs_C']['verdict'] == 'no signal'
      and abs(v['S_vs_C']['min_delta'] + 0.05) < 1e-4 and v['S_vs_C']['mean_delta'] >= 0.03, (v['S_vs_C']['min_delta'], v['S_vs_C']['mean_delta']))
g = copy.deepcopy(s3)
for e in EPS:
    g['cells'][f'S/ep{e}-s43']['auc']['mean'] -= 0.04                # mean delta 0.035 - 0.02 = 0.015
v = merged([sa, sb, s2, g], 'smean')
check("mean delta +0.015 (< +0.03) -> 'no signal'", v['S_vs_C']['verdict'] == 'no signal' and abs(v['S_vs_C']['mean_delta'] - 0.015) < 0.001,
      v['S_vs_C']['mean_delta'])
g = copy.deepcopy(s3); g['cells']['S/ep12-s43']['ref_md5'] = 'f' * 32
v = merged([sa, sb, s2, g], 'smd5')
check('S seeds of one episode on different files -> S vs C INVALID (S_ep12 listed); K / D unaffected',
      v['S_vs_C']['verdict'] == 'INVALID' and 'S_ep12' in v['S_vs_C']['invalid'] and 'S/ep12-s43' in v['S_vs_C']['invalid']
      and v['K_vs_C']['verdict'] == m0['K_vs_C']['verdict'] and v['D_vs_C']['verdict'] == m0['D_vs_C']['verdict'], sorted(v['S_vs_C']['invalid']))
g = copy.deepcopy(s2); g3 = copy.deepcopy(s3)
for e in EPS:                                                         # both seeds on one wrong file: consistent, but not registered
    g['cells'][f'S/ep{e}-s42']['ref_md5'] = g3['cells'][f'S/ep{e}-s43']['ref_md5'] = 'e' * 32
v = merged([sa, sb, g, g3], 'smd5b')
check('S cells all on an unregistered file (consistent across seeds) -> INVALID', v['S_vs_C']['verdict'] == 'INVALID'
      and sum(1 for k in v['S_vs_C']['invalid'] if k.startswith('S/')) == 8)
g = copy.deepcopy(sb); g['cells']['C/ep12-s43']['ref_md5'] = '0' * 32
v = merged([sa, g, s2, s3], 'cmd5')
check('a C cell on another file than the physS1 reference -> S vs C INVALID (and K / D INVALID as before)',
      v['S_vs_C']['verdict'] == 'INVALID' and 'C/ep12-s43' in v['S_vs_C']['invalid'] and v['K_vs_C']['verdict'] == 'INVALID' and v['D_vs_C']['verdict'] == 'INVALID')
g = copy.deepcopy(s2); g['cells']['S/ep2-s42']['config_check']['learning_rate_peak'] = 6e-4
v = merged([sa, sb, g, s3], 'scfg')
check("an S checkpoint not on C's config (K's LR) -> S vs C INVALID; K / D unaffected", v['S_vs_C']['verdict'] == 'INVALID'
      and 'S/ep2-s42' in v['S_vs_C']['invalid'] and v['K_vs_C']['verdict'] == m0['K_vs_C']['verdict'])
g = copy.deepcopy(s2); g['cells']['S/ep12-s42']['dr_active'] = 'v2d FC_DR_RESET: ...'
v = merged([sa, sb, g, s3], 'sdr')
check('the DR hook active in an S training -> INVALID', v['S_vs_C']['verdict'] == 'INVALID' and 'S/ep12-s42' in v['S_vs_C']['invalid'])
g = copy.deepcopy(s2); g['cells']['S/ep24-s42']['config_check']['task_parquet'] = g['cells']['S/ep24-s42']['config_check']['task_parquet'].replace('/refs/screenS/', '/refs/glockt/')
v = merged([sa, sb, g, s3], 'stree')
check("an S checkpoint trained on the physS1 tree (refs/glockt) -> INVALID", v['S_vs_C']['verdict'] == 'INVALID' and 'S/ep24-s42' in v['S_vs_C']['invalid'],
      v['S_vs_C']['invalid'].get('S/ep24-s42'))
v = merged([sa, sb, s2, s3, s2], 'sdup')
check('an S summary given twice: S vs C unchanged', v['S_vs_C']['verdict'] == 'signal' and v['S_vs_C']['mean_delta'] == x['mean_delta'])
subprocess.run([sys.executable, TOOL, 'verdict', f'{D}/boxA/results/recipe_screen', f'{D}/boxB/results/recipe_screen', f'{D}/sboxS42/results/recipe_screen',
                f'{D}/sboxS43/results/recipe_screen', '--ref-md5', f'{D}/stub_ref_md5.json', '--out', f'{D}/sguard_dirs.json'], check=True, capture_output=True)
v = json.load(open(f'{D}/sguard_dirs.json'))['verdicts']
check("results directories (boxes that died) merge to the same S vs C", v['S_vs_C']['verdict'] == x['verdict'] and v['S_vs_C']['mean_delta'] == x['mean_delta'])
# ---- boundary unit test of section 9's rule (synthetic cells on the registered md5s)
cfg = lambda s: dict(RS.expected('C', 70004736, s), fdr=dict(force_closure_enabled=True, force_closure_weight=6, wrench_weight=3, unintended_weight=-2),  # noqa: E731
                     dr_strings=[], cfg_sha256='x')


def synth(deltas, drop=None):
    cs = {}
    for e, dl in zip(EPS, deltas):
        for s in SEEDS:
            for a, v_ in (('C', 0.5), ('S', 0.5 + dl)):
                k = RS.key(a, e, s)
                if k == drop:
                    continue
                cs[k] = dict(arm=a, ep=e, seed=s, status='scored', present=True, ref_md5=RS.REF_MD5[RS.REF_SET[a]][e], dr_active='',
                             auc=dict(mean=v_, sd=0.01, min=v_ - 0.02, n=10), sim_vs_ref=dict(mean=0.6, sd=0.01), checkpoint_steps=20000768,
                             config_check=cfg(s))
    return RS.verdicts(cs, 70004736)['S_vs_C']['verdict']


cases = [((0.03, 0.03, 0.03, 0.03), None, 'signal'), ((0.0299, 0.0299, 0.0299, 0.0299), None, 'no signal'),
         ((0.17, 0.0, 0.0, -0.05), None, 'no signal'), ((0.17, 0.0, 0.0, -0.0499), None, 'signal'), ((-0.03, -0.03, -0.03, -0.03), None, 'no signal'),
         ((0.1, 0.1, 0.1, 0.1), 'S/ep18-s43', 'INCOMPLETE'), ((0.1, 0.1, 0.1, 0.1), 'C/ep2-s42', 'INCOMPLETE')]
got = [synth(d, dr) for d, dr, _ in cases]
check('rule boundaries: mean exactly +0.03 signal, +0.0299 no signal; a delta of exactly -0.05 no signal, -0.0499 signal; harm-size '
      'no signal; a missing S or C cell INCOMPLETE (registered md5s pass)', got == [w for _, _, w in cases], list(zip([w for _, _, w in cases], got)))
print(f"{len(fails)} FAIL" + (f": {fails}" if fails else ''))
sys.exit(1 if fails else 0)
