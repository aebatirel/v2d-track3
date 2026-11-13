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

--rule v2 (2026-10-31, opt-in; the default --rule v1 above is unchanged): the owner's "Masses v2" rule, fixed in
docs/research/work/masses-v2-20261031/PREREG.md before any v2 result. Four public episodes, the same cells, seeds,
NREP and verify step; two boxes (2 + 2 episodes), merged here:
  --content "ROOT_A ROOT_B [ROOT_R ...]" and --verify "VA.json VB.json [VR.json ...]" in the same order (one root per box:
  its /content, or its store run folder runs/<run_id> downloaded file by file); --manifests lists every arms_ep<N>.json.
  A pair (episode, seed) is taken whole (both arms) from the ONE root where both arms are present, verified (in that
  root's verify.json cells, not in its missing list) and have >= --min_n scored rollouts. A pair qualifying in two roots
  is refused (exit 2, no verdict): an INCOMPLETE re-run box may only re-run pairs that are missing everywhere else.
  delta(ep) as v1 (unrounded cell means); the clauses compare the owner's literal rule on values rounded to 9 decimals
  (float noise only; review F3, 31 Oct amendment): d(ep) = round(delta(ep), 9), m = round(mean of the 4 delta(ep), 9);
  reports show 4 decimals.
  INVALID       any verify.json present and not ok, or a non-finite delta (review F2); a box with NO verify.json leaves
                its pairs unverified, i.e. missing -> INCOMPLETE (review F1);
  INCOMPLETE    a pair qualifies in no root (missing cell, no chosen checkpoint, or < min_n scored rollouts);
  ADOPT         m >= +0.03 AND at least 3 of the 4 d(ep) > 0 AND no d(ep) <= -0.05;
  NOT ADOPTED   otherwise (every failed clause is named).
  --partial (one box, fewer than 4 episodes): the same readings, label PARTIAL, never a verdict (mass_check.sh's box line).
"""
import argparse, json, math, os, sys

GAIN, DROP = 0.03, 0.05
V2_MEAN, V2_POS, V2_DROP, V2_NEP = 0.03, 3, -0.05, 4          # Masses v2 (owner, 31 Oct 2026 14:55 UTC)


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


def verdict_v2(rows, eps, seeds, control, treatment, verify_ok, min_n, partial=False):
    """Masses v2 (owner's rule; PREREG section 4). rows as verdict(). Returns (label, reasons, per-episode, clauses)."""
    _, _, per = verdict(rows, eps, seeds, control, treatment, True, min_n)          # the v1 per-episode readings, unchanged
    missing = [f'ep{e}/{a}/s{s}' for e in eps for a in (control, treatment) for s in seeds
               if not (rows.get((e, a, s)) or {}).get('auc') or rows[(e, a, s)]['auc']['n'] < min_n]
    full = [e for e in eps if per[f'ep{e}']['delta'] is not None and not any(m.startswith(f'ep{e}/') for m in missing)]
    d4 = {e: round(per[f'ep{e}']['delta'], 4) for e in full}                      # display
    d9 = {e: round(per[f'ep{e}']['delta'], 9) for e in full}                      # the clauses (review F3)
    mean = sum(per[f'ep{e}']['delta'] for e in full) / len(full) if full else None
    cl = dict(mean_delta=mean, mean_delta_4dp=None if mean is None else round(mean, 4), delta_4dp={f'ep{e}': d for e, d in d4.items()},
              mean_delta_9dp=None if mean is None else round(mean, 9),
              n_positive=sum(1 for d in d9.values() if d > 0), drops=[f'ep{e}' for e, d in d9.items() if d <= V2_DROP],
              episodes_scored=len(full))
    if not verify_ok:
        return 'INVALID', (['mass_verify.py failed in at least one box: the arms did not load what the design says (see verify)']
                           + ([f'also missing or < {min_n} scored rollouts: {missing}'] if missing else [])), per, cl
    if missing:
        return 'INCOMPLETE', [f'missing or < {min_n} scored rollouts: {missing}'], per, cl
    if not all(math.isfinite(x) for x in [mean, *d9.values()]):
        return 'INVALID', ['non-finite delta (a NaN/inf AUC reached a cell mean)'], per, cl
    if partial:
        return 'PARTIAL', [f'box reading over {len(eps)} of {V2_NEP} episodes; the v2 verdict needs both boxes merged'], per, cl
    reasons, ok = [], True
    if cl['mean_delta_9dp'] < V2_MEAN:
        ok = False; reasons.append(f'mean delta {cl["mean_delta_4dp"]:+.4f} < +{V2_MEAN}')
    if cl['n_positive'] < V2_POS:
        ok = False; reasons.append(f'only {cl["n_positive"]} of {len(eps)} episodes with delta > 0 (needs >= {V2_POS})')
    if cl['drops']:
        ok = False; reasons.append('delta <= ' + f'{V2_DROP}: ' + ', '.join(f'{e} {cl["delta_4dp"][e]:+.4f}' for e in cl['drops']))
    if ok:
        reasons.append(f'mean delta {cl["mean_delta_4dp"]:+.4f} >= +{V2_MEAN}, {cl["n_positive"]} of {len(eps)} delta > 0, '
                       f'no delta <= {V2_DROP}')
    return ('ADOPT' if ok else 'NOT ADOPTED'), reasons, per, cl


def cell_row(f):
    """One cell's row from its best/summary.json, exactly as v1 main() builds it."""
    d = json.load(open(f)); rr = d.get('rollouts', [])
    return dict(checkpoint=d.get('checkpoint'), n_rollouts=len(rr), errors=sum(1 for x in rr if 'error' in x),
                auc=stats([x['auc'] for x in rr if isinstance(x.get('auc'), (int, float)) and math.isfinite(x['auc'])]),
                auc_nonfinite=sum(1 for x in rr if 'auc' in x and not (isinstance(x['auc'], (int, float)) and math.isfinite(x['auc']))), sim_vs_ref=stats([x['sim_vs_ref'] for x in rr if 'sim_vs_ref' in x]),
                ref_auc=stats([x['ref_auc'] for x in rr if 'ref_auc' in x]), floor_auc=stats([x['floor_auc'] for x in rr if 'floor_auc' in x]),
                auc_rollouts=[round(x['auc'], 4) for x in rr if 'auc' in x])


def main_v2(a):
    """--rule v2: merge one or more boxes (roots) and apply the Masses v2 rule. Exit 2 (no verdict) on an ambiguous pair."""
    roots = [r.rstrip('/') for r in a.content.split()]; vfs = a.verify.split()
    eps = [int(x) for x in a.eps.split()]; seeds = a.seeds.split(); arms = (a.control, a.treatment)
    if len(roots) != len(vfs):
        sys.exit(f'mass_verdict v2: {len(roots)} --content roots but {len(vfs)} --verify files (one per box, same order)')
    if not a.partial and len(eps) != V2_NEP:
        sys.exit(f'mass_verdict v2: the rule needs exactly {V2_NEP} episodes (got {eps}); use --partial for one box')
    # a box that never wrote / pushed verify.json (died, watchdog, push failed): its cells are unverified, so missing
    # (INCOMPLETE, PREREG 5.2), not a verify failure (INVALID needs a verify.json with ok false)
    Vs = [json.load(open(f)) if os.path.exists(f) else dict(ok=True, cells={}, missing=[], failures=[], absent=f) for f in vfs]
    man = {}
    for f in a.manifests.split():
        if os.path.exists(f):
            d = json.load(open(f)); man[f"ep{d['episode']}"] = dict(source_parquet=d['source_parquet'], source_md5=d['source_md5'],
                                                                     traj_fingerprint=d['traj_fingerprint'],
                                                                     masses={arm: {n: o['mass'] for n, o in v['objects'].items()} for arm, v in d['arms'].items()})
    rows, cells, source, tmo, ambiguous = {}, {}, {}, {}, []
    for e in eps:
        for s in seeds:
            q, seen = [], {}
            for i, (C, V) in enumerate(zip(roots, Vs)):
                vm, vc = set(V.get('missing', [])), V.get('cells', {})
                got = {}
                for arm in arms:
                    k, f = f'ep{e}/{arm}/s{s}', f'{C}/results/{arm}s{s}_glock_public/ep{e}/best/summary.json'
                    if os.path.exists(f) and k not in vm and k in vc:
                        got[arm] = cell_row(f)
                if got:
                    seen[i] = got
                if len(got) == 2 and all(r['auc'] and r['auc']['n'] >= a.min_n for r in got.values()):
                    q.append(i)
            if len(q) > 1:
                ambiguous.append(f'ep{e}/s{s} in {[roots[i] for i in q]}'); continue
            # a pair that qualifies nowhere is shown from the root holding most of it; its absent arm or its short cell
            # (< min_n) makes it missing (INCOMPLETE). Arms of one pair from two boxes are never combined.
            i = q[0] if q else (max(seen, key=lambda j: len(seen[j])) if seen else None)
            for arm in arms:
                k = f'ep{e}/{arm}/s{s}'
                row = (seen.get(i) or {}).get(arm) if i is not None else None
                rows[(e, arm, s)] = row
                cells[k] = None if row is None else {kk: (r4(v) if isinstance(v, dict) else v) for kk, v in row.items()}
                source[k] = None if i is None else roots[i]
                tmo[k] = None if i is None else (Vs[i].get('cells', {}).get(k) or {}).get('eval_timeouts')
    if ambiguous:
        print(f'REFUSED (no verdict): pair(s) qualify in more than one box: {ambiguous}'); sys.exit(2)
    vok = all(bool(V.get('ok')) for V in Vs)
    label, reasons, per, cl = verdict_v2(rows, eps, seeds, a.control, a.treatment, vok, a.min_n, a.partial)
    cut = {k: v for k, v in tmo.items() if v and (v['best'] or v['curve'])}
    unrec = sorted(k for k, v in tmo.items() if v and v['best_without_rc'])
    per_arm = {arm: dict(best=sum(v['best'] for k, v in tmo.items() if v and k.split('/')[1] == arm),
                         curve=sum(v['curve'] for k, v in tmo.items() if v and k.split('/')[1] == arm)) for arm in arms}
    flag = (f' [EVAL TIMEOUTS in {len(cut)} cell(s): ' + ', '.join(f'{k} best {v["best"]}/{v["best_runs"]} curve {v["curve"]}/{v["curve_runs"]}'
                                                                  for k, v in cut.items())
            + '; per arm best/curve ' + ', '.join(f'{arm} {v["best"]}/{v["curve"]}' for arm, v in per_arm.items()) + ']' if cut else '') \
        + (f' [eval exit codes NOT RECORDED for {unrec}]' if unrec else '')
    for e in eps:                                              # secondary readings (not part of the rule), as v1
        p = per[f'ep{e}']
        sv = {arm: [rows[(e, arm, s)]['sim_vs_ref']['mean'] for s in seeds if (rows.get((e, arm, s)) or {}).get('sim_vs_ref')] for arm in arms}
        if all(sv.values()):
            p['sim_vs_ref_delta'] = sum(sv[a.treatment]) / len(sv[a.treatment]) - sum(sv[a.control]) / len(sv[a.control])
        ra = [rows[(e, arm, s)]['ref_auc']['mean'] for arm in arms for s in seeds if (rows.get((e, arm, s)) or {}).get('ref_auc')]
        p['ref_auc_spread_across_cells'] = (max(ra) - min(ra)) if ra else None
        p['harm_reading'] = p['delta'] is not None and round(p['delta'], 4) <= -GAIN
        per[f'ep{e}'] = {k: (round(v, 4) if isinstance(v, float) else ({kk: round(vv, 4) for kk, vv in v.items()} if isinstance(v, dict) else v))
                         for k, v in p.items()}
    out = dict(rule='docs/research/work/masses-v2-20261031/PREREG.md', rule_version='v2', control=a.control, treatment=a.treatment,
               bars=dict(mean_delta_min=V2_MEAN, positive_episodes_min=V2_POS, episode_delta_fail_at_or_below=V2_DROP,
                         min_scored_rollouts=a.min_n, compared_at='4 decimals'),
               verdict=label, reasons=reasons, clauses={k: (round(v, 6) if isinstance(v, float) else v) for k, v in cl.items()},
               verification_ok=vok, verification_failures=[f for V in Vs for f in V.get('failures', [])][:40],
               verification_missing=sorted({m for V in Vs for m in V.get('missing', [])}), roots=roots, verify_files=vfs,
               verify_absent=[V['absent'] for V in Vs if V.get('absent')],
               cell_source=source, eval_timeouts=dict(cells_cut=cut, per_arm=per_arm, not_recorded=unrec, per_cell=tmo),
               episodes=per, references=man, cells=cells)
    json.dump(out, open(a.out, 'w'), indent=1)
    m4 = cl['mean_delta_4dp']
    print(f'{label}{flag}: ' + '; '.join(reasons) + f' | mean delta {m4 if m4 is None else f"{m4:+.4f}"}; ' + '; '.join(
        f"ep{e} {a.control} {per[f'ep{e}']['control_seed_mean']} {a.treatment} {per[f'ep{e}']['treatment_seed_mean']} delta "
        f"{per[f'ep{e}']['delta']} per seed {per[f'ep{e}']['per_seed_delta']}" for e in eps))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    for x in ('--eps', '--seeds', '--control', '--treatment', '--verify', '--out'):
        ap.add_argument(x, required=True)
    ap.add_argument('--content', default='/content'); ap.add_argument('--manifests', default=''); ap.add_argument('--min_n', type=int, default=8)
    ap.add_argument('--rule', default='v1', choices=('v1', 'v2')); ap.add_argument('--partial', action='store_true')
    a = ap.parse_args()
    if a.rule == 'v2':                                         # opt-in; everything below is the v1 rule, unchanged
        return main_v2(a)
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
