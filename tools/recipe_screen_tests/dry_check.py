"""Checks of the recipe-screen CPU dry run (dry_run.sh): the arms reached the right processes, the faults became the
right cell states, the merge gives the pre-registered verdicts on the FAKE numbers, and the merge's guards work
(missing -> INCOMPLETE, reference or config mismatch -> INVALID, duplicates). Usage: dry_check.py DRY_DIR"""
import copy, glob, json, os, subprocess, sys

D = sys.argv[1]; HERE = os.path.dirname(os.path.abspath(__file__)); TOOL = os.path.join(HERE, '..', 'recipe_screen.py')
sys.path.insert(0, os.path.join(HERE, '..'))
import recipe_screen as RS  # noqa: E402

fails = []


def check(name, ok, info=None):
    print(f"{'PASS' if ok else 'FAIL'}  {name}" + (f"  {info}" if info is not None else ''))
    if not ok:
        fails.append(name)


m = json.load(open(f'{D}/merged.json')); cells = m['cells']; v = m['verdicts']
check('both boxes finished (job exit 0) and the merge read 2 summaries', open(f'{D}/exits.txt').read().count('exit 0') == 2 and len(m['inputs']) == 2,
      open(f'{D}/exits.txt').read().split())
check('24 cells in the merge (12 per box)', len(cells) == 24, len(cells))
left = glob.glob(f'{D}/box*/results/recipe_screen/.summary.*')
fl = [l for b in 'AB' for l in open(f'{D}/box{b}/job.log') if 'summary FAILED' in l]
check('incremental box summaries: no failure, no temp file left', not left and not fl, (len(left), len(fl)))
# the arms reached the right processes
tr = {}
for f in glob.glob(f'{D}/box*/runs/screen/*/ep*-s*/stub_train.json'):
    a, cell = f.split('/')[-3], f.split('/')[-2]; tr[f'{a}/{cell}'] = json.load(open(f))
check('every cell launched a training (24 stub_train.json)', len(tr) == 24, len(tr))
kv = lambda t: dict(x.split('=', 1) for x in t['argv'] if '=' in x)  # noqa: E731
ok_k = all(kv(t).get('training.optimization.learning_rate_peak') == '0.0006' and kv(t).get('training.optimization.learning_rate_initial') == '0.0006'
           and kv(t).get('training.optimization.learning_rate_end') == '3e-05' and kv(t).get('training.optimization.learning_rate_schedule_updates') == '136728'
           and json.loads(kv(t)['curriculum.thresholds']) == RS.k_thresholds() for k, t in tr.items() if k.startswith('K/'))
check('K trainings: LR 6e-4 / 6e-4 / 3e-5, schedule_updates 136728, thresholds x2', ok_k)
ok_cd = all(not any(x.startswith(('training.optimization.', 'curriculum.thresholds')) for x in t['argv']) for k, t in tr.items() if k[0] in 'CD')
check('C and D trainings: no LR / threshold override (CURR_SCALE=0.4 in the job env was ignored)', ok_cd)
ok_env = all((t['env']['FC_DR_RESET'] == '1.5,0.015,0.01' and t['env']['FC_DR_SEED'] == k.split('-s')[1]) if k.startswith('D/')
             else (t['env']['FC_DR_RESET'] is None and t['env']['FC_DR_SEED'] is None) for k, t in tr.items())
check('FC_DR_RESET / FC_DR_SEED: D trainings only (seed = training seed; FC_DR_RESET=9,9,9 in the job env was dropped)', ok_env)
same = all(kv(t)['training.total_environment_steps'] == '70004736' and kv(t)['reset.seed'] == k.split('-s')[1]
           and kv(t).get('objective.force_closure.weight') == '6' and kv(t).get('curriculum') == 'tracking_250m_mixed_reset_v2d'
           and t['env']['FC_FDR_OBJ'] == '1' and t['env']['FC_VOC_INERTIA'] == '1' for k, t in tr.items())
check('every training: 70,004,736 steps, its seed, the FDR recipe (curriculum v2d, force closure 6, FC_FDR_OBJ, FC_VOC_INERTIA)', same)
par = {}
for f in glob.glob(f'{D}/box*/runs/screen/*/ep*-s*/stub_train.json'):   # paths relative to each box root (/content on a box)
    root = f.split('/runs/screen/')[0]; t = json.load(open(f))
    par.setdefault(f.split('/')[-2].split('-')[0], set()).add(kv(t)['task.parquet'].replace(root, '<CROOT>'))
check('one reference directory per episode across arms, seeds and boxes', all(len(x) == 1 for x in par.values()), {e: len(x) for e, x in par.items()})
ev = [json.loads(x) for f in glob.glob(f'{D}/box*/eval_env.log') for x in open(f)]
check('no evaluation process (ES, curve, NREP draws) saw FC_DR_RESET', len(ev) > 0 and all(x['FC_DR_RESET'] is None for x in ev),
      f"{len(ev)} evaluations: " + str({k: sum(1 for x in ev if x['kind'] == k) for k in ('es_eval', 'curve', 'evaluate')}))
# faults -> cell states
c = cells['D/ep24-s43']
check('D/ep24-s43 crashed after 2 checkpoints -> train_failed, not present (checkpoints on disk are not scored)',
      c['status'] == 'train_failed' and not c['present'] and c['trained_checkpoints'] == 2, (c['status'], c['trained_checkpoints'], c['notes'][:1]))
c = cells['K/ep2-s42']
check('K/ep2-s42 hung draw r7 killed by EVAL_TIMEOUT -> 9 of 10 draws, still present (>= 8)',
      c['auc']['n'] == 9 and c['present'] and c['draws_failed'] == ['r7'], (c['auc'], c['draws_failed']))
c = cells['C/ep18-s42']
check('C/ep18-s42 hung ES watcher killed ES_TAIL s after its training; trained to the cap, scored by the curve',
      any('ES watcher killed' in n for n in c['notes']) and c['trained_checkpoints'] == 7 and c['present'], (c['notes'], c['trained_checkpoints']))
killed = sorted(k for k, r in cells.items() if any('ES watcher killed' in n for n in r['notes']))
check('only the hung ES watcher was killed (the others finished within ES_TAIL)', killed == ['C/ep18-s42'], killed)
es = {k: r['early_stop'] for k, r in cells.items() if r.get('early_stop')}
check('early stopping ran: some trainings stopped before the cap (ES kill path)', any(cells[k]['trained_checkpoints'] < 7 for k in es),
      {k: (x, cells[k]['trained_checkpoints']) for k, x in list(es.items())[:6]})
check('checkpoints chosen by sim_vs_ref (ep2 peak at 20M in the fake curve)', all(cells[f'{a}/ep2-s{s}']['checkpoint_steps'] == 20000768
                                                                                  for a in 'CKD' for s in (42, 43)))
check('every present cell has a config check as registered (D == C config hash)',
      all(not RS.config_problems(r, 70004736) for r in cells.values() if r['present']) and not v['K_vs_C']['invalid'] and not v['D_vs_C']['invalid'])
check('DR hook line in D trainings only', all(bool(r['dr_active']) == (r['arm'] == 'D') for r in cells.values() if r['status'] != 'not_run'))
# verdicts on the fake numbers
k = v['K_vs_C']; d = v['D_vs_C']
check("K vs C = 'signal' (fake: mean +0.04, no episode <= -0.05)", k['verdict'] == 'signal' and abs(k['mean_delta'] - 0.04) < 0.003,
      (k['verdict'], k['mean_delta']))
check("D vs C = 'INCOMPLETE' with the missing cell listed (not INVALID, not silently dropped)",
      d['verdict'] == 'INCOMPLETE' and d['missing'] == ['D/ep24-s43'] and d['mean_delta'] is None,
      (d['verdict'], d['missing'], 'provisional', d['provisional_mean_delta_on_complete_episodes']))
check('missing cells listed', [x['cell'] for x in v['missing_cells']] == ['D/ep24-s43'], v['missing_cells'])
sel = v['report_seed_selection_by_sim_vs_ref']; ag = v['report_sim_vs_ref_ranks_seeds_like_auc']
check('reports present: seed selection per arm, sim_vs_ref vs AUC seed order', set(sel) == {'C', 'K', 'D'} and ag['of'] == 11,
      ({a: s['mean_gain'] for a, s in sel.items()}, f"{ag['agree']}/{ag['of']}"))
# merge guards on edited copies of the box summaries
sa, sb = (json.load(open(f'{D}/box{b}/results/recipe_screen/summary.json')) for b in 'AB')


def merged(sums, name):
    paths = []
    for i, s in enumerate(sums):
        p = f'{D}/guard_{name}_{i}.json'; json.dump(s, open(p, 'w')); paths.append(p)
    subprocess.run([sys.executable, TOOL, 'verdict', *paths, '--out', f'{D}/guard_{name}.json'], check=True, capture_output=True)
    return json.load(open(f'{D}/guard_{name}.json'))['verdicts']


full = copy.deepcopy(sb); r = copy.deepcopy(full['cells']['D/ep18-s43']); r.update(ep=24, status='scored', present=True)
r['ref_md5'] = full['cells']['C/ep24-s43']['ref_md5']; r['auc'] = dict(full['cells']['C/ep24-s43']['auc']); r['auc']['mean'] -= 0.01
r['sim_vs_ref'] = dict(full['cells']['C/ep24-s43']['sim_vs_ref']); r['config_check'] = full['cells']['C/ep24-s43']['config_check']
full['cells']['D/ep24-s43'] = r
g = merged([sa, full], 'complete')
check("with the missing cell filled (fake): D vs C = 'signal' (sd -50 % on ep2 and ep12, mean -0.01 >= -0.02)",
      g['D_vs_C']['verdict'] == 'signal' and g['D_vs_C']['episodes_sd_falls_40pct'] == 2, (g['D_vs_C']['verdict'], g['D_vs_C']['mean_delta']))
bad = copy.deepcopy(sb); bad['cells']['C/ep12-s43']['ref_md5'] = '0' * 32
g = merged([sa, bad], 'refmd5')
check('a cell on another reference -> INVALID for both verdicts', g['K_vs_C']['verdict'] == 'INVALID' and g['D_vs_C']['verdict'] == 'INVALID',
      g['K_vs_C']['invalid'])
bad = copy.deepcopy(sa); bad['cells']['K/ep18-s42']['config_check']['learning_rate_peak'] = 3e-4
g = merged([bad, sb], 'kcfg')
check('a K checkpoint without the K settings -> K vs C INVALID; D vs C unaffected', g['K_vs_C']['verdict'] == 'INVALID'
      and g['D_vs_C']['verdict'] == 'INCOMPLETE', g['K_vs_C']['invalid'])
bad = copy.deepcopy(sa); bad['cells']['D/ep2-s42']['config_check']['cfg_sha256'] = 'x'
g = merged([bad, sb], 'dcfg')
check('a D checkpoint whose config differs from C -> D vs C INVALID', g['D_vs_C']['verdict'] == 'INVALID', g['D_vs_C']['invalid'])
g = merged([sa, sb, sa], 'dup')
check('a summary given twice: verdicts unchanged', g['K_vs_C']['verdict'] == 'signal' and g['D_vs_C']['verdict'] == 'INCOMPLETE')
dup = json.load(open(f'{D}/guard_dup.json'))['duplicates']
check('... and its cells listed as duplicates (first kept)', len(dup) == 12, len(dup))
subprocess.run([sys.executable, TOOL, 'verdict', f'{D}/boxA/results/recipe_screen', f'{D}/boxB/results/recipe_screen/summary.json',
                '--out', f'{D}/guard_dir.json'], check=True, capture_output=True)
g = json.load(open(f'{D}/guard_dir.json'))['verdicts']
check("a box's results directory (no summary.json needed, e.g. a box that died) merges to the same verdicts",
      g['K_vs_C']['verdict'] == v['K_vs_C']['verdict'] and g['K_vs_C']['mean_delta'] == v['K_vs_C']['mean_delta']
      and g['D_vs_C']['verdict'] == v['D_vs_C']['verdict'] and g['missing_cells'] == v['missing_cells'])
print(f"{len(fails)} FAIL" + (f": {fails}" if fails else ''))
sys.exit(1 if fails else 0)
