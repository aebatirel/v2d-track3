"""Checks of the arm V / RESCORE dry run (dry_run_v.sh; physics-solver.md section 10). FAKE numbers; exit 1 on any FAIL.
Usage: dry_check_v.py DRY_DIR STORED_CKPT"""
import copy, glob, json, os, re, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
import recipe_screen as RS  # noqa: E402

D, CK = sys.argv[1], sys.argv[2]
fails = []
def check(name, ok, info=''):
    print(('PASS ' if ok else 'FAIL ') + name + (f'  [{info}]' if info else '')); ok or fails.append(name)

ex = open(f'{D}/exits.txt').read().split('\n')
check('all 4 jobs exit 0', sum(1 for x in ex if x.endswith('exit 0')) == 4, ' | '.join(x for x in ex if x))
R = lambda b: f'{D}/vbox{b}/results/recipe_screen'  # noqa: E731
for b in ('V42', 'V43'):
    s = int(b[1:])
    for e in (2, 12, 18, 24):
        cmd = open(f'{R(b)}/V/ep{e}-s{s}/train_cmd.txt').read()
        st = json.load(open(f'{D}/vbox{b}/runs/screen/V/ep{e}-s{s}/stub_train.json'))
        cc = json.load(open(f'{R(b)}/V/ep{e}-s{s}/config_check.json'))
        check(f'V/ep{e}-s{s}: train command has the override once; no DR env; config records actor velocity True',
              cmd.count(RS.V_OVERRIDE) == 1 and not st['env'].get('FC_DR_RESET') and cc.get('actor_object_velocity') is True,
              f"override x{cmd.count(RS.V_OVERRIDE)}, DR {st['env'].get('FC_DR_RESET')}, cfg {cc.get('actor_object_velocity')}")
for b, cells in (('C42', [(e, 42) for e in (2, 12, 18, 24)]), ('C43', [(2, 43), (12, 43), (18, 43)])):
    for e, s in cells:
        cmd = open(f'{R(b)}/C/ep{e}-s{s}/train_cmd.txt').read(); cc = json.load(open(f'{R(b)}/C/ep{e}-s{s}/config_check.json'))
        check(f'C/ep{e}-s{s}: no override; config actor velocity False', 'object_body_velocity' not in cmd and cc.get('actor_object_velocity') is False)
check('vC43 never trained C/ep24-s43', not os.path.exists(f'{D}/vboxC43/results/recipe_screen/C/ep24-s43'))

# RESCORE on vV43
oc = f'{R("V43")}/C/ep24-s43'; c = json.load(open(f'{oc}/cell.json')); cc = json.load(open(f'{oc}/config_check.json'))
check('rescore cell scored, 10 draws, present', c['status'] == 'scored' and c['auc']['n'] == 10 and c['present'], f"{c['status']} n={c['auc'] and c['auc']['n']}")
check('rescore cell: checkpoint policy_20000768 from the real stored file; steps 20000768',
      c['checkpoint'] == 'policy_20000768.safetensors' and c['checkpoint_steps'] == 20000768 and cc.get('environment_steps') == 20000768,
      f"{c['checkpoint']} {c['checkpoint_steps']} {cc.get('environment_steps')}")
check('rescore cell: real config is C seed 43, actor velocity False, no config problem',
      cc.get('seed') == 43 and cc.get('actor_object_velocity') is False and RS.config_problems(c, 70004736) == [],
      f"seed {cc.get('seed')} vel {cc.get('actor_object_velocity')} problems {RS.config_problems(c, 70004736)}")
check('rescore cell notes say rescore + selection not redone', any('selection not redone' in n for n in c['notes']))
check('rescore cell ref md5 = this box ep24 record', c['ref_md5'] == open(f'{R("V43")}/refs/ep24.md5').read().strip())
check('no C training on vV43', not glob.glob(f'{D}/vboxV43/runs/screen/C/*'))
log = open(f'{D}/vboxV43/job.log').read() if os.path.exists(f'{D}/vboxV43/job.log') else open(f'{D}/vboxV43/stdout.txt').read()
i_r, i_t = log.find('RESCORE RESULT'), log.find('training on slot')
check('rescore finished before the first training started', 0 <= i_r < i_t, f'rescore at {i_r}, first training at {i_t}')
ev = [json.loads(x) for x in open(f'{D}/vboxV43/eval_env.log')]
rs = [x for x in ev if x['kind'] == 'evaluate' and '/rescore/C/ep24-s43/policy_20000768.safetensors' in x['checkpoint']]
check('10 official evaluations of the re-scored checkpoint, none with FC_DR_RESET', len(rs) == 10 and not any(x['FC_DR_RESET'] for x in ev), f'{len(rs)}')
sm = json.load(open(f'{R("V43")}/summary.json'))
check('vV43 summary lists the rescore cell', 'C/ep24-s43' in sm['cells'] and sm['meta'].get('rescore') == 'C:24:43:20261031-rscr43-865dfbb')

# merge
m = json.load(open(f'{D}/merged_V.json')); v = m['verdicts']['V_vs_C']
check('merge: C/ep24-s43 taken from the rescore box (old 4-draw record first, not present)',
      m['cell_source']['C/ep24-s43'].endswith('vboxV43/results/recipe_screen/summary.json') and m['cells']['C/ep24-s43']['present'] and not m['duplicates'],
      m['cell_source']['C/ep24-s43'])
check('V_vs_C on the fake design = signal (mean +0.03 at the bound, lowest -0.02)', v['verdict'] == 'signal' and abs(v['mean_delta'] - 0.03) < 1e-6
      and abs(v['min_delta'] + 0.02) < 1e-6 and not v['invalid'], f"{v['verdict']} {v['mean_delta']} {v['min_delta']} {v['invalid']}")
cells = copy.deepcopy(m['cells']); cells['V/ep12-s42']['config_check']['actor_object_velocity'] = False
x = RS.verdicts(cells, 70004736, ref_md5=RS.load_md5(f'{D}/stub_ref_md5.json'))['V_vs_C']
check('negative: a V checkpoint without the override -> INVALID', x['verdict'] == 'INVALID' and 'V/ep12-s42' in x['invalid'], x['verdict'])
cells = copy.deepcopy(m['cells']); cells['C/ep2-s42']['config_check']['actor_object_velocity'] = True
x = RS.verdicts(cells, 70004736, ref_md5=RS.load_md5(f'{D}/stub_ref_md5.json'))['V_vs_C']
check('negative: a C checkpoint with actor velocity -> INVALID', x['verdict'] == 'INVALID' and 'C/ep2-s42' in x['invalid'], x['verdict'])
cells = copy.deepcopy(m['cells']); cells['V/ep18-s43']['ref_md5'] = '0' * 32
x = RS.verdicts(cells, 70004736, ref_md5=RS.load_md5(f'{D}/stub_ref_md5.json'))['V_vs_C']
check('negative: a V cell on another reference -> INVALID', x['verdict'] == 'INVALID', x['verdict'])
cells = copy.deepcopy(m['cells']); del cells['V/ep24-s43']
x = RS.verdicts(cells, 70004736, ref_md5=RS.load_md5(f'{D}/stub_ref_md5.json'))['V_vs_C']
check('negative: a missing V cell -> INCOMPLETE', x['verdict'] == 'INCOMPLETE' and 'V/ep24-s43' in x['missing'], x['verdict'])
cells = copy.deepcopy(m['cells'])
for s in (42, 43):
    cells[f'V/ep2-s{s}']['auc']['mean'] = cells[f'C/ep2-s{s}']['auc']['mean'] - 0.10
x = RS.verdicts(cells, 70004736, ref_md5=RS.load_md5(f'{D}/stub_ref_md5.json'))['V_vs_C']
check('negative: ep2 -0.10 -> harm', x['verdict'] == 'harm', f"{x['verdict']} {x['min_delta']}")
print(f'{len(fails)} FAIL' if fails else 'ALL PASS')
sys.exit(1 if fails else 0)
