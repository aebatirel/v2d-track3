"""Summary and pre-registered verdict of the masses transfer check (2026-10-31; ops/jobs/mass_check.sh; rule fixed in
docs/research/work/masses-transfer-20261031/PREREG.md before any result).

Cells: episode x arm x seed; each cell = the NREP official evaluations of the checkpoint glock_public.sh chose by
sim_vs_ref (no ground truth), each scored vs mocap (registered ADD-AUC, score_registered.py --meshes library_v3).
  cell mean   = mean registered AUC of the cell's rollouts (unrounded)
  seed mean   = mean of an arm's cell means over the seeds (each seed weighs the same)
  delta(ep)   = seed mean(treatment) - seed mean(control)
  delta(ep,s) = cell mean(treatment, s) - cell mean(control, s)  (same reference, same seed, same box)
Verdict (PREREG section 3):
  INVALID       mass_verify.py failed (the arms did not load what the design says);
  INCOMPLETE    a cell is missing or has fewer than MIN_N scored rollouts (no reading; re-run the missing cells); a cell
                verify.json lists as missing (no chosen checkpoint) counts as missing even if its summary.json exists;
  ADOPT         delta(ep) >= +0.03 on EVERY episode and no delta(ep,s) < -0.05;
  NOT ADOPTED   otherwise.
Also reported, not part of the rule: sim_vs_ref per cell and delta, the noise (SE of delta from the rollout spread), the
references' own AUC vs mocap per cell (ref_auc: the same reference must give the same value in both arms) and the floor;
evaluations cut by EVAL_TIMEOUT per cell and per arm (verify.json eval_timeouts), printed right after the label (a cut
can correlate with the arm: read it before the verdict).
Usage: mass_verdict.py --eps "2 12" --seeds "42 43" --control mass0 --treatment mass1 --verify V.json --out S.json
       [--content /content] [--manifests "M2.json M12.json"] [--min_n 8]
"""
import argparse, json, math, os, sys

GAIN, DROP = 0.03, 0.05


def stats(v):
    if not v:
        return None
    m = sum(v) / len(v)
    sd = math.sqrt(sum((x - m) ** 2 for x in v) / (len(v) - 1)) if len(v) > 1 else 0.0
    return dict(n=len(v), mean=m, sd=sd, min=min(v), max=max(v))


def r4(d):
    return {k: (round(v, 4) if isinstance(v, float) else v) for k, v in d.items()} if d else d


def verdict(rows, eps, seeds, control, treatment, verify_ok, min_n):
    """rows[(ep, arm, seed)] = cell dict with 'auc' stats (or None). Returns (label, reasons, per-episode readings)."""
    reasons, per = [], {}
    missing = [f'ep{e}/{a}/s{s}' for e in eps for a in (control, treatment) for s in seeds
               if not (rows.get((e, a, s)) or {}).get('auc') or rows[(e, a, s)]['auc']['n'] < min_n]
    for e in eps:
        c = [rows[(e, control, s)]['auc']['mean'] for s in seeds if (rows.get((e, control, s)) or {}).get('auc')]
        t = [rows[(e, treatment, s)]['auc']['mean'] for s in seeds if (rows.get((e, treatment, s)) or {}).get('auc')]
        ps = {s: rows[(e, treatment, s)]['auc']['mean'] - rows[(e, control, s)]['auc']['mean'] for s in seeds
              if (rows.get((e, control, s)) or {}).get('auc') and (rows.get((e, treatment, s)) or {}).get('auc')}
        se = [rows[(e, a, s)]['auc']['sd'] ** 2 / rows[(e, a, s)]['auc']['n'] for s in seeds for a in (control, treatment)
              if (rows.get((e, a, s)) or {}).get('auc')]
        per[f'ep{e}'] = dict(control_seed_mean=sum(c) / len(c) if c else None, treatment_seed_mean=sum(t) / len(t) if t else None,
                             delta=(sum(t) / len(t) - sum(c) / len(c)) if c and t else None, per_seed_delta=ps,
                             se_delta=math.sqrt(sum(se)) / len(seeds) if se else None)
    if not verify_ok:
        return 'INVALID', (['mass_verify.py failed: the arms did not load what the design says (see verify.json)']
                           + ([f'also missing or < {min_n} scored rollouts: {missing}'] if missing else [])), per
    if missing:
        return 'INCOMPLETE', [f'missing or < {min_n} scored rollouts: {missing}'], per
    ok = True
    for e in eps:
        p = per[f'ep{e}']
        if p['delta'] < GAIN:
            ok = False; reasons.append(f'ep{e}: delta {p["delta"]:+.4f} < +{GAIN}')
        for s, d in p['per_seed_delta'].items():
            if d < -DROP:
                ok = False; reasons.append(f'ep{e} seed {s}: drop {d:+.4f} < -{DROP}')
    if ok:
        reasons.append(f'every episode delta >= +{GAIN} and no seed drop > {DROP}')
    harm = [f'ep{e}' for e in eps if per[f'ep{e}']['delta'] <= -GAIN]
    if harm:
        reasons.append(f'harm reading (delta <= -{GAIN}): {harm}')
    return ('ADOPT' if ok else 'NOT ADOPTED'), reasons, per


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    for x in ('--eps', '--seeds', '--control', '--treatment', '--verify', '--out'):
        ap.add_argument(x, required=True)
    ap.add_argument('--content', default='/content'); ap.add_argument('--manifests', default=''); ap.add_argument('--min_n', type=int, default=8)
    a = ap.parse_args()
    C = a.content.rstrip('/'); eps = [int(x) for x in a.eps.split()]; seeds = a.seeds.split()
    V = json.load(open(a.verify)) if os.path.exists(a.verify) else dict(ok=False, failures=['verify.json missing'])
    vmiss = set(V.get('missing', []))                          # no chosen checkpoint: not verified -> missing
    man = {}
    for f in a.manifests.split():
        if os.path.exists(f):
            d = json.load(open(f)); man[f"ep{d['episode']}"] = dict(source_parquet=d['source_parquet'], source_md5=d['source_md5'],
                                                                     traj_fingerprint=d['traj_fingerprint'],
                                                                     masses={arm: {n: o['mass'] for n, o in v['objects'].items()} for arm, v in d['arms'].items()})
    rows, cells = {}, {}
    for e in eps:
        for arm in (a.control, a.treatment):
            for s in seeds:
                f = f'{C}/results/{arm}s{s}_glock_public/ep{e}/best/summary.json'; row = None
                if os.path.exists(f) and f'ep{e}/{arm}/s{s}' not in vmiss:
                    d = json.load(open(f)); rr = d.get('rollouts', [])
                    row = dict(checkpoint=d.get('checkpoint'), n_rollouts=len(rr), errors=sum(1 for x in rr if 'error' in x),
                               auc=stats([x['auc'] for x in rr if 'auc' in x]), sim_vs_ref=stats([x['sim_vs_ref'] for x in rr if 'sim_vs_ref' in x]),
                               ref_auc=stats([x['ref_auc'] for x in rr if 'ref_auc' in x]), floor_auc=stats([x['floor_auc'] for x in rr if 'floor_auc' in x]),
                               auc_rollouts=[round(x['auc'], 4) for x in rr if 'auc' in x])
                rows[(e, arm, s)] = row
                cells[f'ep{e}/{arm}/s{s}'] = None if row is None else {k: (r4(v) if isinstance(v, dict) else v) for k, v in row.items()}
    label, reasons, per = verdict(rows, eps, seeds, a.control, a.treatment, bool(V.get('ok')), a.min_n)
    # evaluations cut by EVAL_TIMEOUT (not part of the rule; never silent): per cell and per arm, printed after the label
    tmo = {k: (V.get('cells', {}).get(k) or {}).get('eval_timeouts') for k in cells}
    cut = {k: v for k, v in tmo.items() if v and (v['best'] or v['curve'])}
    unrec = sorted(k for k, v in tmo.items() if v and v['best_without_rc'])
    per_arm = {arm: dict(best=sum(v['best'] for k, v in tmo.items() if v and k.split('/')[1] == arm),
                         curve=sum(v['curve'] for k, v in tmo.items() if v and k.split('/')[1] == arm)) for arm in (a.control, a.treatment)}
    flag = (f' [EVAL TIMEOUTS in {len(cut)} cell(s): ' + ', '.join(f'{k} best {v["best"]}/{v["best_runs"]} curve {v["curve"]}/{v["curve_runs"]}'
                                                                  for k, v in cut.items())
            + '; per arm best/curve ' + ', '.join(f'{arm} {v["best"]}/{v["curve"]}' for arm, v in per_arm.items()) + ']' if cut else '') \
        + (f' [eval exit codes NOT RECORDED for {unrec}]' if unrec else '')
    for e in eps:                                              # secondary readings (not part of the rule)
        p = per[f'ep{e}']
        sv = {arm: [rows[(e, arm, s)]['sim_vs_ref']['mean'] for s in seeds if (rows.get((e, arm, s)) or {}).get('sim_vs_ref')]
              for arm in (a.control, a.treatment)}
        if all(sv.values()):
            p['sim_vs_ref_delta'] = sum(sv[a.treatment]) / len(sv[a.treatment]) - sum(sv[a.control]) / len(sv[a.control])
        ra = [rows[(e, arm, s)]['ref_auc']['mean'] for arm in (a.control, a.treatment) for s in seeds if (rows.get((e, arm, s)) or {}).get('ref_auc')]
        p['ref_auc_spread_across_cells'] = (max(ra) - min(ra)) if ra else None
        per[f'ep{e}'] = {k: (round(v, 4) if isinstance(v, float) else ({kk: round(vv, 4) for kk, vv in v.items()} if isinstance(v, dict) else v))
                         for k, v in p.items()}
    out = dict(rule='docs/research/work/masses-transfer-20261031/PREREG.md', control=a.control, treatment=a.treatment,
               bars=dict(gain_each_episode=GAIN, max_seed_drop=DROP, min_scored_rollouts=a.min_n),
               verdict=label, reasons=reasons, verification_ok=bool(V.get('ok')), verification_failures=V.get('failures', [])[:20],
               verification_missing=sorted(vmiss), eval_timeouts=dict(cells_cut=cut, per_arm=per_arm, not_recorded=unrec, per_cell=tmo),
               episodes=per, references=man, cells=cells)
    json.dump(out, open(a.out, 'w'), indent=1)
    print(f'{label}{flag}: ' + '; '.join(reasons) + ' | ' + '; '.join(
        f"ep{e} {a.control} {per[f'ep{e}']['control_seed_mean']} {a.treatment} {per[f'ep{e}']['treatment_seed_mean']} delta "
        f"{per[f'ep{e}']['delta']} per seed {per[f'ep{e}']['per_seed_delta']}" for e in eps))


if __name__ == '__main__':
    main()
