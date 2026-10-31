"""Summary and pre-registered verdict of the ep11 rollout gate (2026-10-31; ops/jobs/ep11_gate.sh; rule fixed in
docs/research/work/perception-sprint-20261031/ep11gate/PREREG.md section 3 before any result).

Cells: arm (e11c = C control, e11t = T treatment, S12 V4p) x seed; each cell = the NREP official evaluations of the
checkpoint glock_public.sh chose by sim_vs_ref (no ground truth), each scored vs mocap (registered ADD-AUC,
score_registered.py --meshes library_v3).
  cell mean = mean registered AUC of the cell's scored rollouts (unrounded)
  seed mean = mean of an arm's cell means over the seeds (each seed weighs the same)
  delta     = seed mean(T) - seed mean(C);  delta(s) = cell mean(T, s) - cell mean(C, s)
Verdict:
  INVALID     e11g_verify.py failed (B0 band, build inputs, arm identity, the evaluator's chain or the config diff);
  INCOMPLETE  a cell is missing or has fewer than MIN_N (8) scored rollouts; re-run only the missing cells;
  PASS        delta >= +0.05 and no delta(s) < -0.05;
  FAIL        otherwise.
Reported, not part of the rule: per-seed cells (mean, sd, min, n, AUCs, checkpoint), delta(s), SE of delta from the rollout
spread sqrt(sum sd^2/n)/2 and the two-seed spread |delta(42) - delta(43)|/2, sim_vs_ref per cell and its delta,
per-object AUC (blue_cup, beige_cup) per cell (from best/r*/score_registered_ep11.json when present), each cell's
reference vs mocap (ref_auc) and the static floor, each arm's zero-action sim_vs_ref and rest check (arms.json), the B0
bands and the arm-identity numbers (verify.json), evaluation timeouts per cell printed right after the label.
Usage: e11g_verdict.py --content /content --arms "e11c e11t" --seeds "42 43" --gate G --out S.json [--min_n 8]
       (G = results/ep11_gate: verify.json, arms.json, b0.json)
"""
import argparse, glob, json, math, os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from mass_verdict import stats, r4                     # noqa: E402  (mean / sd ddof 1 / min / max; rounding)

GAIN, DROP, EP = 0.05, 0.05, 11
EPS = 1e-9                                            # an exact +0.05 / -0.05 counts as met (float sums of 4-decimal AUCs)
OBJS = ('blue_cup', 'beige_cup')


def verdict(rows, seeds, control, treatment, verify_ok, min_n):
    """rows[(arm, seed)] = cell dict with 'auc' stats (or None). Returns (label, reasons, readings)."""
    missing = [f'{a}/s{s}' for a in (control, treatment) for s in seeds
               if not (rows.get((a, s)) or {}).get('auc') or rows[(a, s)]['auc']['n'] < min_n]
    ok_ = lambda a, s: bool((rows.get((a, s)) or {}).get('auc'))
    c = [rows[(control, s)]['auc']['mean'] for s in seeds if ok_(control, s)]
    t = [rows[(treatment, s)]['auc']['mean'] for s in seeds if ok_(treatment, s)]
    ps = {s: rows[(treatment, s)]['auc']['mean'] - rows[(control, s)]['auc']['mean'] for s in seeds if ok_(control, s) and ok_(treatment, s)}
    se = [rows[(a, s)]['auc']['sd'] ** 2 / rows[(a, s)]['auc']['n'] for s in seeds for a in (control, treatment) if ok_(a, s)]
    per = dict(control_seed_mean=sum(c) / len(c) if c else None, treatment_seed_mean=sum(t) / len(t) if t else None,
               delta=(sum(t) / len(t) - sum(c) / len(c)) if c and t else None, per_seed_delta=ps,
               se_delta_rollouts=math.sqrt(sum(se)) / len(seeds) if se else None,
               two_seed_spread=abs(ps[seeds[0]] - ps[seeds[1]]) / 2 if len(seeds) == 2 and len(ps) == 2 else None)
    if not verify_ok:
        return 'INVALID', (['e11g_verify.py failed: the arms are not what the design says (see verify.json)']
                           + ([f'also missing or < {min_n} scored rollouts: {missing}'] if missing else [])), per
    if missing:
        return 'INCOMPLETE', [f'missing or < {min_n} scored rollouts: {missing} (re-run only these cells on the stored references)'], per
    reasons, ok = [], True
    if per['delta'] < GAIN - EPS:
        ok = False; reasons.append(f'delta {per["delta"]:+.4f} < +{GAIN}')
    for s, d in ps.items():
        if d < -DROP - EPS:
            ok = False; reasons.append(f'seed {s}: T below C by {d:+.4f} (< -{DROP})')
    if ok:
        reasons.append(f'delta {per["delta"]:+.4f} >= +{GAIN} and no seed of T more than {DROP} below its C seed')
    return ('PASS' if ok else 'FAIL'), reasons, per


def per_object(O):
    """Mean per-object registered AUC over a cell's scored rollouts (best/r*/score_registered_ep11.json), or None."""
    v = {n: [] for n in OBJS}
    for f in sorted(glob.glob(f'{O}/best/r*/score_registered_ep{EP}.json')):
        try:
            po = json.load(open(f))['sim'].get('per_obj_AUC', {})
        except Exception:
            continue
        for n in OBJS:
            if n in po:
                v[n].append(float(po[n]))
    return {n: (round(sum(x) / len(x), 4) if x else None) for n, x in v.items()} | {'n_files': max(len(x) for x in v.values())}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--content', default='/content'); ap.add_argument('--arms', default='e11c e11t'); ap.add_argument('--seeds', default='42 43')
    ap.add_argument('--gate', required=True); ap.add_argument('--out', required=True); ap.add_argument('--min_n', type=int, default=8)
    a = ap.parse_args()
    C = a.content.rstrip('/'); G = a.gate.rstrip('/'); control, treatment = a.arms.split(); seeds = a.seeds.split()
    js = lambda f: json.load(open(f)) if os.path.isfile(f) else None
    V = js(f'{G}/verify.json') or dict(ok=False, failures=['verify.json missing']); man = js(f'{G}/arms.json') or {}
    vmiss = set(V.get('missing', []))
    rows, cells = {}, {}
    for arm in (control, treatment):
        for s in seeds:
            O = f'{C}/results/perc2{arm}s{s}_glock_public/ep{EP}'; f = f'{O}/best/summary.json'; row = None
            if os.path.exists(f) and f'{arm}/s{s}' not in vmiss:
                d = json.load(open(f)); rr = d.get('rollouts', [])
                row = dict(checkpoint=d.get('checkpoint'), n_rollouts=len(rr), errors=sum(1 for x in rr if 'error' in x),
                           auc=stats([x['auc'] for x in rr if 'auc' in x]), sim_vs_ref=stats([x['sim_vs_ref'] for x in rr if 'sim_vs_ref' in x]),
                           ref_auc=stats([x['ref_auc'] for x in rr if 'ref_auc' in x]), floor_auc=stats([x['floor_auc'] for x in rr if 'floor_auc' in x]),
                           auc_rollouts=[round(x['auc'], 4) for x in rr if 'auc' in x], per_object_auc=per_object(O))
            rows[(arm, s)] = row
            cells[f'{arm}/s{s}'] = None if row is None else {k: (r4(v) if isinstance(v, dict) else v) for k, v in row.items()}
    label, reasons, per = verdict(rows, seeds, control, treatment, bool(V.get('ok')), a.min_n)
    sv = {arm: [rows[(arm, s)]['sim_vs_ref']['mean'] for s in seeds if (rows.get((arm, s)) or {}).get('sim_vs_ref')] for arm in (control, treatment)}
    if all(sv.values()):
        per['sim_vs_ref_delta'] = sum(sv[treatment]) / len(sv[treatment]) - sum(sv[control]) / len(sv[control])
    for n in OBJS:
        po = {arm: [rows[(arm, s)]['per_object_auc'][n] for s in seeds if (rows.get((arm, s)) or {}).get('per_object_auc', {}).get(n) is not None]
              for arm in (control, treatment)}
        if all(po.values()):
            per[f'{n}_auc_delta'] = sum(po[treatment]) / len(po[treatment]) - sum(po[control]) / len(po[control])
    per = {k: (round(v, 4) if isinstance(v, float) else ({kk: round(vv, 4) for kk, vv in v.items()} if isinstance(v, dict) else v)) for k, v in per.items()}
    tmo = {k: (V.get('cells', {}).get(k) or {}).get('eval_timeouts') for k in cells}
    cut = {k: v for k, v in tmo.items() if v and (v.get('best') or v.get('curve'))}
    unrec = sorted(k for k, v in tmo.items() if v and v.get('best_without_rc'))
    per_arm = {arm: dict(best=sum((v or {}).get('best', 0) for k, v in tmo.items() if k.split('/')[0] == arm),
                         curve=sum((v or {}).get('curve', 0) for k, v in tmo.items() if k.split('/')[0] == arm)) for arm in (control, treatment)}
    flag = (f' [EVAL TIMEOUTS in {len(cut)} cell(s): ' + ', '.join(f'{k} best {v["best"]}/{v["best_runs"]} curve {v["curve"]}/{v["curve_runs"]}'
                                                                  for k, v in cut.items())
            + '; per arm best/curve ' + ', '.join(f'{arm} {v["best"]}/{v["curve"]}' for arm, v in per_arm.items()) + ']' if cut else '') \
        + (f' [eval exit codes NOT RECORDED for {unrec}]' if unrec else '')
    arm_info = {arm: dict(zero_action=(man.get('arms', {}).get(arm) or {}).get('zero_score'),
                          rest_check_all_ok=((man.get('arms', {}).get(arm) or {}).get('rest_check') or {}).get('all_ok'),
                          reference_md5=(man.get('arms', {}).get(arm) or {}).get('source_md5')) for arm in (control, treatment)}
    out = dict(rule='docs/research/work/perception-sprint-20261031/ep11gate/PREREG.md', control=control, treatment=treatment,
               bars=dict(gain=GAIN, max_seed_drop=DROP, min_scored_rollouts=a.min_n), verdict=label, reasons=reasons,
               verification_ok=bool(V.get('ok')), verification_failures=V.get('failures', [])[:20], verification_missing=sorted(vmiss),
               b0_bands=V.get('b0_bands'), identity=V.get('identity'), eval_timeouts=dict(cells_cut=cut, per_arm=per_arm, not_recorded=unrec, per_cell=tmo),
               readings=per, arms=arm_info, cells=cells)
    json.dump(out, open(a.out, 'w'), indent=1)
    f4 = lambda x: 'n/a' if x is None else f'{x:.4f}'
    nr = ' | partial numbers, NOT a reading:' if label in ('INCOMPLETE', 'INVALID') else ' |'
    print(f'{label}{flag}: ' + '; '.join(reasons) + nr + f" C {f4(per.get('control_seed_mean'))} T {f4(per.get('treatment_seed_mean'))} "
          f"delta {per.get('delta')} per seed {per.get('per_seed_delta')} SE {per.get('se_delta_rollouts')} spread {per.get('two_seed_spread')} "
          f"| sim_vs_ref delta {per.get('sim_vs_ref_delta')} | blue delta {per.get('blue_cup_auc_delta')} beige delta {per.get('beige_cup_auc_delta')} "
          f"| B0 {V.get('b0_bands')}")


if __name__ == '__main__':
    main()
