"""Fixture tests of tools/e10v_verdict.py (the PREREG section 5 swap rule), 2026-10-31. Synthetic score sets only (no
real rollout, no eval result). Each case builds conf / packed / old sets in tools/e10v_score.py's layout and checks the
label and, where it matters, which clauses fail. Usage: python -I verdict_tests.py REPO OUT.json"""
import copy, json, math, sys
REPO, OUT = sys.argv[1], sys.argv[2]
sys.path.insert(0, f'{REPO}/tools')
import e10v_verdict as V   # noqa: E402

OBJ = lambda auc: {'blue_cup': dict(AUC=auc), 'beige_cup': dict(AUC=auc)}


def roll(draw, sv, rp, sp, rpp, scored=True):
    """one rollout: sim_vs_ref / RPE vs V (sv, rp) and vs P (sp, rpp)"""
    return dict(draw=draw, scored=scored, own_ref_check=dict(ok=True),
                vs=dict(V=dict(sim_vs_ref=sv, RPE=rp, MPPE=rp / 2, AUC=sv, audit_fail=rp > 5, fail=rp > 5, objects=OBJ(sv)),
                        P=dict(sim_vs_ref=sp, RPE=rpp, MPPE=rpp / 2, AUC=sp, audit_fail=rpp > 5, fail=rpp > 5, objects=OBJ(sp))))


def base():
    conf = [roll(i, 0.85 + 0.002 * i, 2.0 + 0.1 * i, 0.75 + 0.002 * i, 3.0 + 0.1 * i) for i in range(1, 11)]
    packed = [roll(i, 0.45 + 0.001 * i, 15.0 + 0.1 * i, 0.45 + 0.001 * i, 15.5 + 0.1 * i) for i in range(1, 11)]
    old = [roll(1, 0.452, 15.2, 0.4563, 15.76)]
    sets = dict(conf=dict(own='V', rollouts=conf), packed=dict(own='P', rollouts=packed), old=dict(own='P', rollouts=old))
    return sets, dict(ok=True, failures=[]), dict(chosen='42', checkpoint='x', sha256='y')


cases = []


def case(name, expect, mutate, fails=None):
    s, v, c = base(); s, v, c = mutate(copy.deepcopy(s), v, c)
    label, why, clauses, sides = V.verdict(s, v, c)
    bad = sorted(k for k, x in clauses.items() if not x['holds'])
    ok = label == expect and (fails is None or bad == sorted(fails))
    cases.append(dict(case=name, expect=expect, got=label, failing_clauses=bad, expected_failing=fails, why=why, ok=ok))


def m(f):
    def g(s, v, c):
        f(s, v, c); return s, v, c
    return g


case('pass', 'SWAP-ELIGIBLE', m(lambda s, v, c: None), [])
# (a) fails on V only: the new mean vs V just below the packed mean vs V (P still holds) -> disagreement
def a_fail(X, rest, d1):
    def f(s, v, c):
        for r in s['conf']['rollouts'][1:]:
            r['vs'][X].update(sim_vs_ref=rest)
        s['conf']['rollouts'][0]['vs'][X].update(sim_vs_ref=d1)
    return f
# new mean vs V 0.4546 < packed 0.4555 (draw 1 0.46 keeps the secondary)
case('fail_a_V_disagree', 'NO-SWAP', m(a_fail('V', 0.454, 0.46)), ['a_V'])
case('fail_a_P', 'NO-SWAP', m(a_fail('P', 0.44, 0.50)), ['a_P'])
# (b) fails on P: 3 new failures (RPE > 5) vs P, packed 10/10 fail vs P -> holds; make packed only 2/10 fail on P
def b_fail(s, v, c):
    for r in s['packed']['rollouts'][2:]:
        r['vs']['P'].update(RPE=4.0)
    for r in s['conf']['rollouts'][:3]:
        r['vs']['P'].update(RPE=6.0)
case('fail_b_P', 'NO-SWAP', m(b_fail), ['b_P'])   # medians 3.75 vs 4.0: (c) still holds
# (c) fails on V only: same failure counts, new median RPE above packed's (all below 5 cm on both sides)
def c_fail(s, v, c):
    for r in s['packed']['rollouts']:
        r['vs']['V'].update(RPE=2.0)
    for r in s['conf']['rollouts']:
        r['vs']['V'].update(RPE=2.5)
case('fail_c_V', 'NO-SWAP', m(c_fail), ['c_V'])
# secondary fails on P: draw 1 vs P below 0.4563 - 0.05
case('fail_s_P', 'NO-SWAP', m(lambda s, v, c: s['conf']['rollouts'][0]['vs']['P'].update(sim_vs_ref=0.40)), ['s_P'])
case('fail_s_V', 'NO-SWAP', m(lambda s, v, c: s['conf']['rollouts'][0]['vs']['V'].update(sim_vs_ref=0.39)), ['s_V'])
# ties count as holding (>= / <= inclusive)
def ties(s, v, c):
    for r, q in zip(s['conf']['rollouts'], s['packed']['rollouts']):
        r['vs']['V'] = copy.deepcopy(q['vs']['V'])
    s['conf']['rollouts'][0]['vs']['P'].update(sim_vs_ref=0.4563 - 0.05)
case('ties_hold', 'SWAP-ELIGIBLE', m(ties), [])
case('incomplete_conf_9', 'INCOMPLETE', m(lambda s, v, c: s['conf']['rollouts'].pop()))
case('incomplete_packed_9', 'INCOMPLETE', m(lambda s, v, c: s['packed']['rollouts'].pop()))
case('incomplete_no_old', 'INCOMPLETE', m(lambda s, v, c: s.pop('old')))
case('incomplete_no_seed', 'INCOMPLETE', m(lambda s, v, c: c.update(chosen=None, incomplete_seeds=['43'])))
case('incomplete_draw1_unscored', 'INCOMPLETE', m(lambda s, v, c: s['conf']['rollouts'][0].update(scored=False)))
case('incomplete_packed_missing', 'INCOMPLETE', m(lambda s, v, c: s.pop('packed')))
case('invalid_verify', 'INVALID', m(lambda s, v, c: v.update(ok=False, failures=['config diff'])))
case('invalid_verify_missing', 'INVALID', lambda s, v, c: (s, None, c))
# a NaN score: e10v_score marks the rollout scored=False -> it counts toward no n -> 9 draws -> INCOMPLETE
case('nan_unscored_incomplete', 'INCOMPLETE', m(lambda s, v, c: s['conf']['rollouts'][4].update(scored=False) or s['conf']['rollouts'][4]['vs']['V'].update(RPE=float('nan'))))
# defence in depth: a NaN that slipped through as 'scored' makes a clause non-finite -> INVALID
case('nan_slipped_invalid', 'INVALID', m(lambda s, v, c: s['conf']['rollouts'][4]['vs']['P'].update(sim_vs_ref=float('nan'))))
# 11 draws on each side still read (>= 10)
case('eleven_draws', 'SWAP-ELIGIBLE', m(lambda s, v, c: s['conf']['rollouts'].append(roll(11, 0.86, 2.1, 0.76, 3.1)) or
                                         s['packed']['rollouts'].append(roll(11, 0.45, 15.0, 0.45, 15.0))), [])
# the new policy also fails like the packed one (left behind at the floor): typical NO-SWAP
def floor(s, v, c):
    for i, r in enumerate(s['conf']['rollouts']):
        r['vs']['V'].update(sim_vs_ref=0.448 + 0.0001 * i, RPE=15.8); r['vs']['P'].update(sim_vs_ref=0.449, RPE=16.0)
case('new_at_floor', 'NO-SWAP', m(floor))
ok = all(x['ok'] for x in cases)
json.dump(dict(ok=ok, n=len(cases), passed=sum(x['ok'] for x in cases), cases=cases), open(OUT, 'w'), indent=1)
for x in cases:
    print(('ok  ' if x['ok'] else 'FAIL') + f" {x['case']}: expect {x['expect']} got {x['got']} failing {x['failing_clauses']} | {'; '.join(x['why'])[:160]}")
print(f"{sum(x['ok'] for x in cases)}/{len(cases)} verdict fixtures pass")
sys.exit(0 if ok else 1)
