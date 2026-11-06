"""Fixture tests of tools/e11g_verdict.py (the PREREG section 3 rule) on synthetic cells. Each case writes a minimal
/content tree (results/perc2<arm>s<seed>_glock_public/ep11/best/summary.json with 10 rollouts, optional
best/r*/score_registered_ep11.json; results/ep11_gate/{verify.json, arms.json}) and checks the label.
Usage: python verdict_tests.py REPO WORKDIR OUT.json"""
import json, os, shutil, subprocess, sys
REPO, WD, OUT = sys.argv[1:4]
SEEDS = ('42', '43')


def tree(name, cells, verify_ok=True, vmissing=(), per_obj=True, no_verify=False):
    C = f'{WD}/{name}'; shutil.rmtree(C, ignore_errors=True); G = f'{C}/results/ep11_gate'; os.makedirs(G)
    for (arm, s), aucs in cells.items():
        if aucs is None:
            continue
        O = f'{C}/results/perc2{arm}s{s}_glock_public/ep11'; os.makedirs(f'{O}/best')
        rows = []
        for i, x in enumerate(aucs):
            if x is None:
                rows.append(dict(rollout=f'r{i + 1}', error='mock: crashed rollout')); continue
            rows.append(dict(rollout=f'r{i + 1}', sim_vs_ref=0.5 + x / 2, auc=x, ref_auc=0.9, floor_auc=0.595))
            if per_obj:
                os.makedirs(f'{O}/best/r{i + 1}')
                json.dump(dict(sim=dict(AUC=x, per_obj_AUC=dict(blue_cup=x, beige_cup=x))), open(f'{O}/best/r{i + 1}/score_registered_ep11.json', 'w'))
        json.dump(dict(checkpoint=f'/content/runs/perc2{arm}s{s}_glock/ep11-s{s}/policy_1.safetensors', n=len(rows), rollouts=rows),
                  open(f'{O}/best/summary.json', 'w'))
    if not no_verify:
        json.dump(dict(ok=verify_ok, failures=[] if verify_ok else ['mock: configs differ in training.lr'], missing=list(vmissing),
                       b0_bands=dict(e11c='IDENTICAL', e11t='IDENTICAL'), cells={}), open(f'{G}/verify.json', 'w'))
    json.dump(dict(ok=True, arms={a: dict(source_md5='x', zero_score='zero_action: 0.579', rest_check=dict(all_ok=False)) for a in ('e11c', 'e11t')}),
              open(f'{G}/arms.json', 'w'))
    return C


def run(C):
    r = subprocess.run([sys.executable, '-I', f'{REPO}/tools/e11g_verdict.py', '--content', C, '--gate', f'{C}/results/ep11_gate',
                        '--out', f'{C}/summary.json'], capture_output=True, text=True)
    return json.load(open(f'{C}/summary.json')), r.stdout.strip(), r.returncode


def cell(v, n=10):
    return [v] * n


F = 0.5950
cases = [
    ('pass', dict(cells={('e11c', s): cell(F) for s in SEEDS} | {('e11t', s): cell(0.7) for s in SEEDS}), 'PASS'),
    ('pass_boundary_delta_0.05', dict(cells={('e11c', s): cell(0.25) for s in SEEDS} | {('e11t', s): cell(0.30) for s in SEEDS}), 'PASS'),
    ('fail_delta_0.03', dict(cells={('e11c', s): cell(F) for s in SEEDS} | {('e11t', s): cell(F + 0.03) for s in SEEDS}), 'FAIL'),
    ('fail_just_below_0.05', dict(cells={('e11c', s): cell(F) for s in SEEDS} | {('e11t', s): cell(F + 0.0499) for s in SEEDS}), 'FAIL'),
    ('fail_seed_drop', dict(cells={('e11c', '42'): cell(F), ('e11c', '43'): cell(0.80), ('e11t', '42'): cell(F + 0.20), ('e11t', '43'): cell(0.73)}), 'FAIL'),
    ('pass_seed_drop_exactly_0.05', dict(cells={('e11c', '42'): cell(0.25), ('e11c', '43'): cell(0.80), ('e11t', '42'): cell(0.40), ('e11t', '43'): cell(0.75)}), 'PASS'),
    ('incomplete_7_scored', dict(cells={('e11c', s): cell(F) for s in SEEDS} | {('e11t', '42'): cell(0.7), ('e11t', '43'): [0.7] * 7 + [None] * 3}), 'INCOMPLETE'),
    ('pass_8_scored', dict(cells={('e11c', s): cell(F) for s in SEEDS} | {('e11t', '42'): cell(0.7), ('e11t', '43'): [0.7] * 8 + [None] * 2}), 'PASS'),
    ('incomplete_summary_missing', dict(cells={('e11c', s): cell(F) for s in SEEDS} | {('e11t', '42'): cell(0.7), ('e11t', '43'): None}), 'INCOMPLETE'),
    ('incomplete_verify_lists_missing', dict(cells={('e11c', s): cell(F) for s in SEEDS} | {('e11t', s): cell(0.7) for s in SEEDS},
                                             vmissing=['e11t/s43']), 'INCOMPLETE'),
    ('invalid_verify_failed', dict(cells={('e11c', s): cell(F) for s in SEEDS} | {('e11t', s): cell(0.9) for s in SEEDS}, verify_ok=False), 'INVALID'),
    ('invalid_verify_failed_and_missing', dict(cells={('e11c', s): cell(F) for s in SEEDS} | {('e11t', '42'): cell(0.9), ('e11t', '43'): None},
                                               verify_ok=False, vmissing=['e11t/s43']), 'INVALID'),
    ('invalid_no_verify_json', dict(cells={('e11c', s): cell(F) for s in SEEDS} | {('e11t', s): cell(0.9) for s in SEEDS}, no_verify=True), 'INVALID'),
    # review F1 (31 Oct): a NaN AUC is not a scored rollout (before the fix, a NaN in T read as PASS with delta nan)
    ('nan_one_rollout_not_scored', dict(cells={('e11c', s): cell(F) for s in SEEDS} | {('e11t', '42'): cell(0.7), ('e11t', '43'): [0.7] * 9 + [float('nan')]}), 'PASS'),
    ('nan_three_rollouts_incomplete', dict(cells={('e11c', s): cell(F) for s in SEEDS} | {('e11t', '42'): cell(0.7), ('e11t', '43'): [float('nan')] * 3 + [0.7] * 7}), 'INCOMPLETE'),
    ('nan_whole_T_cell_incomplete', dict(cells={('e11c', s): cell(F) for s in SEEDS} | {('e11t', '42'): cell(0.7), ('e11t', '43'): cell(float('nan'))}), 'INCOMPLETE'),
    ('pass_no_per_object_files', dict(cells={('e11c', s): cell(F) for s in SEEDS} | {('e11t', s): cell(0.7) for s in SEEDS}, per_obj=False), 'PASS'),
]
res, bad = [], 0
for name, kw, want in cases:
    S, line, rc = run(tree(name, **kw))
    ok = S['verdict'] == want and rc == 0
    extra = {}
    if name == 'pass':
        r = S['readings']; extra = dict(delta=r['delta'], se=r['se_delta_rollouts'], blue=r.get('blue_cup_auc_delta'), sim=r.get('sim_vs_ref_delta'))
        ok = ok and abs(r['delta'] - 0.105) < 1e-9 and r['se_delta_rollouts'] == 0 and abs(r['blue_cup_auc_delta'] - 0.105) < 1e-4
    if name == 'pass_no_per_object_files':
        ok = ok and 'blue_cup_auc_delta' not in S['readings']
    bad += not ok
    res.append(dict(case=name, want=want, got=S['verdict'], ok=ok, reasons=S['reasons'], **extra))
    print(('ok   ' if ok else 'FAIL ') + f'{name}: want {want}, got {S["verdict"]} :: {line[:220]}')
json.dump(dict(passed=len(cases) - bad, total=len(cases), cases=res), open(OUT, 'w'), indent=1)
print(f'{len(cases) - bad}/{len(cases)} pass')
sys.exit(1 if bad else 0)
