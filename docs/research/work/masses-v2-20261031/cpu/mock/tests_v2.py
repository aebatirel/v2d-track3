"""Fixture tests of the Masses v2 rule (tools/mass_verdict.py --rule v2) and of the unchanged v1 default (2026-10-31).
usage: python3 -I tests_v2.py OUT.json [FIRST_CHECK_DL_ROOT]
  R*  verdict_v2() on synthetic cells: ADOPT; NOT ADOPTED on each clause alone (mean, 3 of 4, drop); boundaries exactly at
      mean +0.03 (passes), delta -0.05 (fails: '<= -0.05'), -0.0499 (passes), delta 0.0 (not > 0) and +0.00004 (> 0: owner's literal rule, 31 Oct amendment); a NaN delta (INVALID), exactly 3 of 4 positive (passes); INCOMPLETE (7 rollouts; a missing cell); INVALID (with missing listed);
      PARTIAL (box reading);
  M*  main_v2() on file trees (two boxes merged; a pair split over two boxes; a re-run box filling a missing pair; a pair
      present twice -> exit 2, no verdict; a cell verify lists as missing; a cell not in verify's cells; a failed verify;
      3 episodes without --partial -> refused);
  V1* the v1 rule unchanged: the first check's own fixture cases (masses-transfer-20261031/cpu/mock/tests.py T4) and, when
      FIRST_CHECK_DL_ROOT (store runs/20261031-mass-2ed46ea downloaded file by file) is given, the stored summary.json and
      RESULT line reproduced byte for byte by the default (v1) path.
"""
import json, os, subprocess, sys, tempfile
R = '/home/user/v2d-track3'; T = f'{R}/tools'
sys.path.insert(0, T)
import mass_verdict as mv                                                 # noqa: E402
OUT = sys.argv[1]; DL = sys.argv[2] if len(sys.argv) > 2 else None
res = {}
EPS, SEEDS = [24, 11, 13, 31], ['42', '43']


def cells(d, n=10, base=0.5):
    """d[ep] = per-seed (delta42, delta43) or a single delta for both seeds; control cells at `base`."""
    rows = {}
    for e in EPS:
        v = d[e] if isinstance(d[e], tuple) else (d[e], d[e])
        for s, dv in zip(SEEDS, v):
            rows[(e, 'mass0', s)] = dict(auc=dict(n=n, mean=base, sd=0.02, min=base - 0.03, max=base + 0.03))
            rows[(e, 'mass1', s)] = dict(auc=dict(n=n, mean=base + dv, sd=0.02, min=base + dv - 0.03, max=base + dv + 0.03))
    return rows


def V(rows, ok=True, partial=False):
    lab, rs, per, cl = mv.verdict_v2(rows, EPS, SEEDS, 'mass0', 'mass1', ok, 8, partial)
    return lab, rs, cl


def case(name, rows, want, ok=True, partial=False, check=None):
    lab, rs, cl = V(rows, ok, partial)
    good = lab == want and (check is None or check(rs, cl))
    res[name] = dict(ok=good, got=lab, want=want, reasons=rs, clauses={k: v for k, v in cl.items() if k != 'mean_delta'})


case('R1_adopt', cells({24: 0.10, 11: 0.05, 13: 0.02, 31: -0.01}), 'ADOPT')
case('R2_not_mean_only', cells({24: 0.05, 11: 0.02, 13: 0.02, 31: 0.02}), 'NOT ADOPTED',
     check=lambda r, c: len(r) == 1 and r[0].startswith('mean delta +0.0275'))
case('R3_not_3of4_only', cells({24: 0.20, 11: 0.01, 13: 0.0, 31: -0.02}), 'NOT ADOPTED',
     check=lambda r, c: len(r) == 1 and r[0].startswith('only 2 of 4'))
case('R4_not_drop_only', cells({24: 0.20, 11: 0.05, 13: 0.03, 31: -0.06}), 'NOT ADOPTED',
     check=lambda r, c: len(r) == 1 and 'ep31 -0.0600' in r[0])
case('R5_boundary_mean_exactly_0.03', cells({24: 0.03, 11: 0.03, 13: 0.03, 31: 0.03}), 'ADOPT',
     check=lambda r, c: c['mean_delta_4dp'] == 0.03)
case('R5b_boundary_mean_0.0299', cells({24: 0.0299, 11: 0.0299, 13: 0.0299, 31: 0.0299}), 'NOT ADOPTED')
case('R6_boundary_delta_exactly_-0.05_fails', cells({24: 0.20, 11: 0.05, 13: 0.05, 31: -0.05}), 'NOT ADOPTED',
     check=lambda r, c: c['drops'] == ['ep31'] and len(r) == 1)
case('R6b_float_artifact_-0.05', cells({24: 0.20, 11: 0.05, 13: 0.05, 31: (0.45 - 0.5, 0.45 - 0.5)}), 'NOT ADOPTED',
     check=lambda r, c: c['drops'] == ['ep31'])
case('R7_delta_-0.0499_passes', cells({24: 0.20, 11: 0.05, 13: 0.05, 31: -0.0499}), 'ADOPT')
case('R8_exactly_3of4_positive_one_zero', cells({24: 0.10, 11: 0.05, 13: 0.05, 31: 0.0}), 'ADOPT',
     check=lambda r, c: c['n_positive'] == 3)
case('R9_zero_is_not_positive', cells({24: 0.10, 11: 0.10, 13: 0.0, 31: 0.0}), 'NOT ADOPTED',
     check=lambda r, c: c['n_positive'] == 2)
# review F3 (31 Oct amendment): the clauses read the owner's literal rule (9-decimal rounding removes float noise only),
# so +0.00004 IS positive (it was 'not positive' under the earlier 4-decimal comparison)
case('R10_+0.00004_is_positive_owner_literal', cells({24: 0.10, 11: 0.10, 13: 0.00004, 31: 0.0}), 'ADOPT',
     check=lambda r, c: c['n_positive'] == 3)
# review F2: a non-finite delta (NaN cell mean) is INVALID, never ADOPT
case('R10b_nan_delta_invalid', cells({24: float('nan'), 11: 0.10, 13: 0.10, 31: 0.10}), 'INVALID')
case('R11_per_seed_drop_alone_does_not_fail', cells({24: (0.20, -0.10), 11: 0.05, 13: 0.05, 31: 0.05}), 'ADOPT')
r = cells({24: 0.10, 11: 0.05, 13: 0.05, 31: 0.05}); r[(13, 'mass1', '43')]['auc']['n'] = 7
case('R12_incomplete_7_rollouts', r, 'INCOMPLETE', check=lambda rs, c: 'ep13/mass1/s43' in rs[0])
r = cells({24: 0.10, 11: 0.05, 13: 0.05, 31: 0.05}); r[(31, 'mass0', '42')] = None
case('R13_incomplete_missing_cell', r, 'INCOMPLETE', check=lambda rs, c: 'ep31/mass0/s42' in rs[0] and c['episodes_scored'] == 3)
case('R14_invalid_with_missing_listed', r, 'INVALID', ok=False, check=lambda rs, c: 'also missing' in rs[-1])
case('R15_partial', cells({24: 0.10, 11: 0.05, 13: 0.05, 31: 0.05}), 'PARTIAL', partial=True)


# ---- M: main_v2 on file trees
def summ(ep, arm, s, aucs):
    return dict(checkpoint=f'/content/runs/{arm}s{s}_glock/ep{ep}-s{s}/policy_70004736.safetensors', n=len(aucs),
                rollouts=[dict(rollout=f'r{i + 1}', sim_vs_ref=a, auc=a, ref_auc=0.9, floor_auc=0.5) for i, a in enumerate(aucs)])


def tree(root, eps, seeds, delta, skip=(), n=10, vmiss=(), vdrop=(), vok=True):
    cl = {}
    for e in eps:
        for s in seeds:
            for arm in ('mass0', 'mass1'):
                k = f'ep{e}/{arm}/s{s}'
                if k in skip:
                    continue
                d = f'{root}/results/{arm}s{s}_glock_public/ep{e}/best'; os.makedirs(d, exist_ok=True)
                base = 0.5 + (delta.get(e, 0) if arm == 'mass1' else 0)
                json.dump(summ(e, arm, s, [round(base + 0.001 * (i - 4.5), 4) for i in range(n)]), open(f'{d}/summary.json', 'w'))
                if k not in vmiss and k not in vdrop:
                    cl[k] = dict(eval_timeouts=dict(best=0, best_runs=10, best_rc={'0': 10}, best_without_rc=0, curve=0, curve_runs=21, curve_rc={'0': 21}, curve_without_rc=0))
    os.makedirs(f'{root}/results/mass_check', exist_ok=True)
    json.dump(dict(ok=vok, failures=[] if vok else ['mock failure'], missing=sorted(vmiss), cells=cl), open(f'{root}/results/mass_check/verify.json', 'w'))
    return root


def run(roots, eps='24 11 13 31', extra=()):
    out = tempfile.mktemp(suffix='.json')
    p = subprocess.run([sys.executable, '-I', f'{T}/mass_verdict.py', '--rule', 'v2', '--eps', eps, '--seeds', '42 43', '--control', 'mass0',
                        '--treatment', 'mass1', '--content', ' '.join(roots), '--verify', ' '.join(f'{r}/results/mass_check/verify.json' for r in roots),
                        '--out', out] + list(extra), capture_output=True, text=True)
    return p.returncode, p.stdout.strip() + p.stderr.strip()[-300:], (json.load(open(out)) if os.path.exists(out) else None)


tmp = tempfile.mkdtemp(); D = {24: 0.06, 11: 0.04, 13: 0.03, 31: -0.01}
A = tree(f'{tmp}/A', [24, 13], ['42', '43'], D); B = tree(f'{tmp}/B', [11, 31], ['42', '43'], D)
rc, out, S = run([A, B]); res['M1_merge_two_boxes'] = dict(ok=rc == 0 and S['verdict'] == 'ADOPT' and S['clauses']['mean_delta_4dp'] == 0.03
                                                             and S['cell_source']['ep13/mass1/s43'] == A and S['cell_source']['ep31/mass0/s42'] == B, got=out[:300])
Af = tree(f'{tmp}/Af', [24, 13], ['42', '43'], D, skip={'ep13/mass1/s43'}, vmiss={'ep13/mass1/s43'})
rc, out, S = run([Af, B]); res['M2_missing_cell_incomplete'] = dict(ok=rc == 0 and S['verdict'] == 'INCOMPLETE' and 'ep13/mass1/s43' in S['reasons'][0], got=out[:300])
Rr = tree(f'{tmp}/R', [13], ['43'], D)
rc, out, S = run([Af, B, Rr]); res['M3_rerun_fills_the_pair'] = dict(ok=rc == 0 and S['verdict'] == 'ADOPT' and S['cell_source']['ep13/mass1/s43'] == Rr
                                                                    and S['cell_source']['ep13/mass0/s43'] == Rr and S['cell_source']['ep13/mass0/s42'] == Af, got=out[:300])
rc, out, S = run([A, B, Rr]); res['M4_pair_twice_refused_exit2'] = dict(ok=rc == 2 and 'REFUSED' in out and S is None, got=out[:300])
Bs = tree(f'{tmp}/Bs', [11, 31], ['42', '43'], D, skip={'ep31/mass1/s42'}, vmiss={'ep31/mass1/s42'})
Rs = tree(f'{tmp}/Rs', [31], ['42'], D, skip={'ep31/mass0/s42'}, vmiss={'ep31/mass0/s42'})
rc, out, S = run([A, Bs, Rs]); res['M5_pair_split_over_boxes_incomplete'] = dict(ok=rc == 0 and S['verdict'] == 'INCOMPLETE', got=out[:300])
Bv = tree(f'{tmp}/Bv', [11, 31], ['42', '43'], D, vmiss={'ep11/mass0/s42'})
rc, out, S = run([A, Bv]); res['M6_verify_missing_wins_over_summary'] = dict(ok=S['verdict'] == 'INCOMPLETE' and 'ep11/mass0/s42' in S['reasons'][0], got=out[:300])
Bu = tree(f'{tmp}/Bu', [11, 31], ['42', '43'], D, vdrop={'ep11/mass1/s43'})
rc, out, S = run([A, Bu]); res['M7_unverified_cell_incomplete'] = dict(ok=S['verdict'] == 'INCOMPLETE' and 'ep11/mass1/s43' in S['reasons'][0], got=out[:300])
Bx = tree(f'{tmp}/Bx', [11, 31], ['42', '43'], D, vok=False)
rc, out, S = run([A, Bx]); res['M8_failed_verify_invalid'] = dict(ok=S['verdict'] == 'INVALID', got=out[:300])
rc, out, S = run([A, B], eps='24 11 13'); res['M9_three_episodes_refused'] = dict(ok=rc != 0 and 'exactly 4 episodes' in out, got=out[-200:])
rc, out, S = run([A], eps='24 13', extra=['--partial']); res['M10_box_partial'] = dict(ok=rc == 0 and S['verdict'] == 'PARTIAL', got=out[:200])
D2 = {24: 0.10, 11: 0.05, 13: 0.0, 31: (0.45 - 0.5)}                    # ep31 exactly -0.05 from float arithmetic
A2 = tree(f'{tmp}/A2', [24, 13], ['42', '43'], D2); B2 = tree(f'{tmp}/B2', [11, 31], ['42', '43'], D2)
rc, out, S = run([A2, B2]); res['M11_files_boundary_drop'] = dict(ok=S['verdict'] == 'NOT ADOPTED' and S['clauses']['drops'] == ['ep31'], got=out[:300])

# ---- V1: the default rule unchanged
cv1 = lambda vals, n=10: {k: dict(auc=dict(n=n, mean=v, sd=0.02, min=v - 0.03, max=v + 0.03)) for k, v in vals.items()}
V1 = lambda d, n=10, ok=True: mv.verdict(cv1(d, n), [2, 12], ['42', '43'], 'mass0', 'mass1', ok, 8)[0]
base = {(2, 'mass0', '42'): 0.70, (2, 'mass0', '43'): 0.72, (12, 'mass0', '42'): 0.88, (12, 'mass0', '43'): 0.86}
adopt = {**base, **{(2, 'mass1', '42'): 0.75, (2, 'mass1', '43'): 0.76, (12, 'mass1', '42'): 0.92, (12, 'mass1', '43'): 0.90}}
short = {**adopt, **{(12, 'mass1', '42'): 0.90, (12, 'mass1', '43'): 0.88}}
drop = {**adopt, **{(2, 'mass1', '42'): 0.64, (2, 'mass1', '43'): 0.88}}
edge = {(2, 'mass0', '42'): 0.5, (2, 'mass0', '43'): 0.5, (2, 'mass1', '42'): 0.53, (2, 'mass1', '43'): 0.53,
        (12, 'mass0', '42'): 0.5, (12, 'mass0', '43'): 0.5, (12, 'mass1', '42'): 0.45, (12, 'mass1', '43'): 0.67}
got = dict(adopt=V1(adopt), short=V1(short), drop=V1(drop), edge=V1(edge), incomplete=V1(adopt, n=7), invalid=V1(adopt, ok=False))
want = dict(adopt='ADOPT', short='NOT ADOPTED', drop='NOT ADOPTED', edge='ADOPT', incomplete='INCOMPLETE', invalid='INVALID')
res['V1_first_check_fixture_cases'] = dict(ok=got == want, got=got, want=want)
if DL:
    first = f'{R}/docs/research/work/masses-transfer-20261031/results'
    out = tempfile.mktemp(suffix='.json')
    p = subprocess.run([sys.executable, '-I', f'{T}/mass_verdict.py', '--eps', '2 12', '--seeds', '42 43', '--control', 'mass0', '--treatment', 'mass1',
                        '--verify', f'{first}/verify.json', '--manifests', f'{DL}/results/mass_check/arms_ep2.json {DL}/results/mass_check/arms_ep12.json',
                        '--content', DL, '--out', out], capture_output=True, text=True)
    line = [x for x in open(f'{first}/job.log') if 'mass_check RESULT:' in x][0].split('mass_check RESULT: ', 1)[1].rstrip('\n')
    res['V1_stored_results_reproduced'] = dict(ok=open(out, 'rb').read() == open(f'{first}/summary.json', 'rb').read() and p.stdout[:1500].rstrip('\n') == line,
                                              got=p.stdout.strip()[:200])
n_ok = sum(1 for v in res.values() if v['ok'])
json.dump(dict(passed=n_ok, total=len(res), tests=res), open(OUT, 'w'), indent=1)
print(f'{n_ok}/{len(res)} pass' + ('' if n_ok == len(res) else ': FAILED ' + ', '.join(k for k, v in res.items() if not v['ok'])))
