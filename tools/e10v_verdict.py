"""Verdict of the eval-10 V4p retrain under the agreed pack-10 swap rule (2026-10-31; rule fixed in
docs/research/work/perception-sprint-20261031/ev10retrain/PREREG.md section 5 before any result). GT-free throughout.

Inputs: one or more tools/e10v_score.py outputs (sets by name: conf = the new policy's confirmation draws, own V;
packed = the packed policy's H5p7 eval-10 draws, own P; old = the old packed draw, own P; later files win a set name),
tools/e10v_verify.py's verify.json and choice.json.
Per reference X in (V, P), N = conf's scored draws, K = packed's scored draws:
  (a_X) mean sim_vs_ref_X(N) >= mean sim_vs_ref_X(K)
  (b_X) fraction of N with RPE_X > 5 cm <= that fraction of K
  (c_X) median RPE_X(N) <= median RPE_X(K)
  (s_X) sim_vs_ref_X(N's draw 1 by position) >= sim_vs_ref_X(old packed draw) - 0.05  (both references: this PREREG's
        stricter reading; the literal own-reference reading, draw 1 vs V against the old draw vs P, is reported)
  comparisons with a 1e-9 tolerance in favour of "holds".
Labels:
  INVALID        verify.json missing or not ok; any clause value NaN / inf;
  INCOMPLETE     verify ok but a seed is missing / thin (choice.json), n(N) < 10, n(K) < 10, or the old packed draw is not
                 scored on both references, or draw 1 is not scored;
  SWAP-ELIGIBLE  every clause on both references holds;
  NO-SWAP        otherwise (a both-reference disagreement is NO-SWAP and is named as such).
Reported, not gating: per set and reference n / mean / sd / min / max of sim_vs_ref, RPE, MPPE, AUC, failure counts,
audit.py's own flag, per-object AUC means; each clause's sides and margin; the gate PREREG section 5 cross-check
(mean sim_vs_ref_V(N) >= 0.456); the training-box seed summaries and the chosen seed; evaluation return codes.
Usage: e10v_verdict.py --score S1.json [--score S2.json ...] --verify V.json --choice C.json --out SUMMARY.json [--min_n 10]
"""
import argparse, json, math, os, statistics, sys

TOL, SEC_DROP, OLD_PACKED_P = 1e-9, 0.05, 0.4563
REFS = ('V', 'P')


def fin(x):
    return isinstance(x, (int, float)) and not isinstance(x, bool) and math.isfinite(x)


def stats(v):
    if not v:
        return None
    m = sum(v) / len(v); sd = math.sqrt(sum((x - m) ** 2 for x in v) / (len(v) - 1)) if len(v) > 1 else 0.0
    return dict(n=len(v), mean=round(m, 4), sd=round(sd, 4), min=round(min(v), 4), max=round(max(v), 4), median=round(statistics.median(v), 4))


def scored(rows):
    """rollouts with every score finite on both references (e10v_score's 'scored')"""
    return [r for r in rows if r.get('scored') and all(X in r.get('vs', {}) for X in REFS)]


def side(rows, X):
    s = [r['vs'][X] for r in rows]
    return dict(n=len(s), sim_vs_ref=stats([x['sim_vs_ref'] for x in s]), RPE=stats([x['RPE'] for x in s]),
                MPPE=stats([x['MPPE'] for x in s]), AUC=stats([x['AUC'] for x in s]),
                fail_rate=round(sum(1 for x in s if x['RPE'] > 5.0) / len(s), 4) if s else None,
                fails=sum(1 for x in s if x['RPE'] > 5.0), audit_fails=sum(1 for x in s if x.get('audit_fail')),
                objects={o: round(sum(x['objects'][o]['AUC'] for x in s) / len(s), 4) for o in (s[0]['objects'] if s else {})},
                mean_raw=sum(x['sim_vs_ref'] for x in s) / len(s) if s else None,
                fail_raw=sum(1 for x in s if x['RPE'] > 5.0) / len(s) if s else None,
                median_rpe_raw=statistics.median([x['RPE'] for x in s]) if s else None)


def verdict(sets, verify, choice, min_n=10):
    reasons, clauses = [], {}
    N = scored((sets.get('conf') or {}).get('rollouts', [])); K = scored((sets.get('packed') or {}).get('rollouts', []))
    O = scored((sets.get('old') or {}).get('rollouts', []))
    draw1 = next((r for r in (sets.get('conf') or {}).get('rollouts', []) if r.get('draw') == 1), None)
    sides = {X: dict(new=side(N, X), packed=side(K, X)) for X in REFS}
    if not verify or not verify.get('ok'):
        return 'INVALID', [f'verify failed: {(verify or {}).get("failures", ["verify.json missing"])[:6]}'], clauses, sides
    inc = []
    if not choice or not choice.get('chosen'):
        inc.append(f'no chosen seed (seeds without 8 scored training-box rollouts: {(choice or {}).get("incomplete_seeds")})')
    if len(N) < min_n:
        inc.append(f'{len(N)} scored confirmation draws (< {min_n})')
    if len(K) < min_n:
        inc.append(f'{len(K)} scored packed-policy draws (< {min_n})')
    if len(O) != 1:
        inc.append(f'old packed draw scored {len(O)} times (1 needed)')
    if not (draw1 and draw1.get('scored') and all(X in draw1.get('vs', {}) for X in REFS)):
        inc.append('confirmation draw 1 not scored')
    if inc:
        return 'INCOMPLETE', inc, clauses, sides
    for X in REFS:
        n, k = sides[X]['new'], sides[X]['packed']
        old = O[0]['vs'][X]['sim_vs_ref']; d1 = draw1['vs'][X]['sim_vs_ref']
        vals = dict(a=(n['mean_raw'], k['mean_raw']), b=(n['fail_raw'], k['fail_raw']), c=(n['median_rpe_raw'], k['median_rpe_raw']),
                    s=(d1, old - SEC_DROP))
        for c, (x, y) in vals.items():
            if not (fin(x) and fin(y)):
                return 'INVALID', [f'clause {c}_{X} is not finite ({x}, {y})'], clauses, sides
        clauses[f'a_{X}'] = dict(new_mean=round(vals['a'][0], 4), packed_mean=round(vals['a'][1], 4), holds=vals['a'][0] >= vals['a'][1] - TOL,
                                 margin=round(vals['a'][0] - vals['a'][1], 4))
        clauses[f'b_{X}'] = dict(new_fail_rate=round(vals['b'][0], 4), packed_fail_rate=round(vals['b'][1], 4), holds=vals['b'][0] <= vals['b'][1] + TOL,
                                 margin=round(vals['b'][1] - vals['b'][0], 4))
        clauses[f'c_{X}'] = dict(new_median_rpe=round(vals['c'][0], 4), packed_median_rpe=round(vals['c'][1], 4), holds=vals['c'][0] <= vals['c'][1] + TOL,
                                 margin=round(vals['c'][1] - vals['c'][0], 4))
        clauses[f's_{X}'] = dict(new_draw1=round(d1, 4), old_packed_draw=round(old, 4), bar=round(old - SEC_DROP, 4), holds=d1 >= old - SEC_DROP - TOL,
                                 margin=round(d1 - (old - SEC_DROP), 4))
    bad = [k for k, v in clauses.items() if not v['holds']]
    if not bad:
        return 'SWAP-ELIGIBLE', ['every clause holds on both references'], clauses, sides
    split = [c for c in 'abcs' if clauses[f'{c}_V']['holds'] != clauses[f'{c}_P']['holds']]
    why = [f'fails: {bad}']
    if split:
        why.append(f'both-reference disagreement on clause(s) {split} (holds on {[X for X in REFS if all(clauses[f"{c}_{X}"]["holds"] for c in split)]})')
    return 'NO-SWAP', why, clauses, sides


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--score', action='append', required=True); ap.add_argument('--verify', required=True)
    ap.add_argument('--choice', required=True); ap.add_argument('--out', required=True); ap.add_argument('--min_n', type=int, default=10)
    a = ap.parse_args()
    js = lambda f: json.load(open(f)) if f and os.path.isfile(f) else None
    sets = {}
    for f in a.score:
        for k, v in (js(f) or {}).get('sets', {}).items():
            sets[k] = v
    verify, choice = js(a.verify), js(a.choice)
    label, why, clauses, sides = verdict(sets, verify, choice, a.min_n)
    conf = sets.get('conf') or {}
    d1 = next((r for r in conf.get('rollouts', []) if r.get('draw') == 1 and r.get('scored')), None)
    lit = dict(new_draw1_vs_V=d1['vs']['V']['sim_vs_ref'] if d1 else None, old_packed_draw_vs_P=OLD_PACKED_P,
               holds=bool(d1 and d1['vs']['V']['sim_vs_ref'] >= OLD_PACKED_P - SEC_DROP - TOL))
    n_v = (sides.get('V') or {}).get('new', {}).get('sim_vs_ref') or {}
    out = dict(label=label, why=why, clauses=clauses, sides={X: {k: {kk: vv for kk, vv in v.items() if not kk.endswith('_raw')} for k, v in s.items()}
                                                             for X, s in sides.items()},
               secondary_literal_own_reference=lit,
               gate_prereg_s5_crosscheck=dict(new_mean_vs_V=n_v.get('mean'), bar=0.456, holds=(n_v.get('mean') or -1) >= 0.456 - TOL),
               choice={k: (choice or {}).get(k) for k in ('chosen', 'checkpoint', 'sha256', 'seeds', 'incomplete_seeds')},
               verify=dict(ok=(verify or {}).get('ok'), failures=(verify or {}).get('failures'), confirmation=(verify or {}).get('confirmation'),
                           b0_band=(verify or {}).get('b0_band')),
               counts={k: dict(own=v.get('own'), n_files=v.get('n_files'), n_scored=v.get('n_scored')) for k, v in sets.items()},
               rule='docs/research/work/perception-sprint-20261031/ev10retrain/PREREG.md section 5')
    json.dump(out, open(a.out, 'w'), indent=1, default=str)
    rc = ((verify or {}).get('confirmation') or {}).get('eval_rc')
    print(f'{label} (eval rc of the confirmation draws: {rc}) :: ' + '; '.join(why) + ' :: ' + ' | '.join(
        f"{k} {'ok' if v['holds'] else 'FAIL'} " + ' '.join(f'{kk} {vv}' for kk, vv in v.items() if kk not in ('holds',)) for k, v in clauses.items())
          + ' :: ' + ' | '.join(f"{X}: new {(s['new'].get('sim_vs_ref') or {}).get('mean')} (n {s['new']['n']}, RPE med {(s['new'].get('RPE') or {}).get('median')}, "
                                f"fails {s['new'].get('fails')}) vs packed {(s['packed'].get('sim_vs_ref') or {}).get('mean')} (n {s['packed']['n']}, RPE med "
                                f"{(s['packed'].get('RPE') or {}).get('median')}, fails {s['packed'].get('fails')})" for X, s in sides.items())
          + f" :: chosen seed {out['choice'].get('chosen')}")


if __name__ == '__main__':
    main()
