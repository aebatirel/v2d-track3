#!/usr/bin/env python3
"""Score test G-B (Gemini track audit) — GROUND-TRUTH SIDE. Run only after every G-B request has an answer.

Reads the G-B cache (run_gemini.py), the G-B specs (ids = ep:obj:frame) and the depth audit's label table
docs/research/work/depth-audit-20261030/calib_gt/v2/per_frame.csv: `adds_cm` = the kit's symmetric registered ADD of
the same perception track against mocap, kit frame-0 alignment (pipeline/score_registered.py --per_frame; the audit's
primary label). The statistic functions are imported unchanged from that study's calibrate.py.

Statistic (PREREG.md, copied from the work log 2026-11-13 ~00:50 UTC):
  score = 1 - P(aligned) (the noul answer); positive = adds_cm > 2 cm.
  Pooled AUROC (Mann-Whitney, average ranks) over all answered rows of the 19 primary episodes.
  95 % CI: episode-cluster bootstrap, 2,000 draws, seed 0, percentile (calibrate.boot_ci, same withholding rules).
  INFORMATIVE iff AUROC >= 0.75 and >= 8 episodes contribute positives; FALSIFIED iff AUROC < 0.65; otherwise
  INCONCLUSIVE. The verdict uses the point estimate. Missing answers: rows without an ok answer are left out and
  listed; if more than 2 % of the 7,835 rows (> 156) are missing the verdict is INCONCLUSIVE (missing data).
Checks: the spec rows must equal the table's valid primary rows (7,835); the depth audit's own `behind` AUROC on the
answered rows is recomputed (0.600 on all rows).
Diagnostics (never used for the verdict): per-episode and per-class AUROC, leave-one-episode-out range, mean
within-track AUROC, thresholds 1 / 3 / 5 cm, the two alternative scene alignments (adds_glob_cm, adds_f0all_cm),
P(aligned) < 0.5 rates on positives and negatives, Spearman with `behind`.
Usage: score_GB.py --cache cache_GB.jsonl --specs specs_GB.jsonl --labels .../calib_gt/v2/per_frame.csv
                   --calibrate .../depth-audit-20261030/calibrate.py --out DIR [--allow_fake]
"""
import argparse, csv, hashlib, importlib.util, json, os
from collections import defaultdict

import numpy as np
from scipy.stats import spearmanr

PRIMARY = [0, 2, 11, 12, 13, 18, 21, 22, 24, 26, 27, 31, 39, 40, 41, 42, 43, 44, 45]
THR, MAX_MISSING_SHARE = 2.0, 0.02


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--cache', required=True); ap.add_argument('--specs', required=True)
    ap.add_argument('--labels', required=True); ap.add_argument('--calibrate', required=True)
    ap.add_argument('--out', required=True); ap.add_argument('--allow_fake', action='store_true')
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    spec = importlib.util.spec_from_file_location('calibrate', a.calibrate)
    cal = importlib.util.module_from_spec(spec); spec.loader.exec_module(cal)
    auroc, boot_ci = cal.auroc, cal.boot_ci
    specs = [json.loads(l) for l in open(a.specs)]
    L = {}
    with open(a.labels) as fh:
        for r in csv.DictReader(fh):
            if int(r['ep']) in PRIMARY and r['valid'] == '1':
                L[f"ep{r['ep']}:{r['obj']}:{r['frame']}"] = r
    ids = [s['id'] for s in specs]
    if set(ids) != set(L) or len(ids) != len(L):
        raise SystemExit(f'spec rows ({len(ids)}) differ from the audit table valid primary rows ({len(L)})')
    ans = {}
    for l in open(a.cache):
        r = json.loads(l)
        if r.get('ok'):
            if r.get('fake') and not a.allow_fake:
                raise SystemExit('cache holds fake answers; pass --allow_fake only for tests')
            ans.setdefault(r['id'], r)
    missing = [i for i in ids if i not in ans]
    rows = []
    for s in specs:
        if s['id'] not in ans:
            continue
        x = ans[s['id']]['response']['answers']['aligned']
        lab = L[s['id']]
        rows.append(dict(id=s['id'], ep=s['episode'], obj=s['obj'], frame=s['frame'], p=float(x['noul']),
                         conf=float(x['confidence']), score=1.0 - float(x['noul']), behind=float(lab['behind']),
                         adds=float(lab['adds_cm']), glob=float(lab['adds_glob_cm']), f0all=float(lab['adds_f0all_cm'])))
    ep = np.array([r['ep'] for r in rows]); ob = np.array([r['obj'] for r in rows])
    S = {k: np.array([r[k] for r in rows]) for k in ('score', 'behind', 'p', 'adds', 'glob', 'f0all', 'conf')}

    def pooled(score, lab, thr, mask=None, boot=False):
        m = np.ones(len(rows), bool) if mask is None else mask
        per = [(score[m & (ep == e)], lab[m & (ep == e)] > thr) for e in PRIMARY]
        s = np.concatenate([x[0] for x in per]); y = np.concatenate([x[1] for x in per])
        v, n1, n0 = auroc(s, y)
        res = dict(auroc=None if not np.isfinite(v) else round(v, 4), n_pos=n1, n_neg=n0,
                   episodes_with_pos=int(sum(x[1].sum() > 0 for x in per)))
        if boot and np.isfinite(v):
            res['ci95'] = boot_ci([x for x in per if len(x[0])], 2000)
        return res

    prim = pooled(S['score'], S['adds'], THR, boot=True)
    v = prim['auroc']
    if len(missing) > MAX_MISSING_SHARE * len(ids):
        verdict = f'INCONCLUSIVE (missing data: {len(missing)} of {len(ids)} rows unanswered > 2 %)'
    elif v is None:
        verdict = 'INCONCLUSIVE (no positives or no negatives)'
    elif v < 0.65:
        verdict = 'FALSIFIED (pooled AUROC < 0.65)'
    elif v >= 0.75 and prim['episodes_with_pos'] >= 8:
        verdict = 'INFORMATIVE (pooled AUROC >= 0.75, >= 8 episodes with positives)'
    else:
        verdict = 'INCONCLUSIVE (0.65 <= AUROC < 0.75, or < 8 episodes with positives)'
    behind_check = pooled(S['behind'], S['adds'], THR)
    per_ep = {e: pooled(S['score'], S['adds'], THR, mask=(ep == e)) for e in PRIMARY}
    per_cls = {o: pooled(S['score'], S['adds'], THR, mask=(ob == o)) for o in sorted(set(ob))}
    loo = {e: pooled(S['score'], S['adds'], THR, mask=(ep != e))['auroc'] for e in PRIMARY}
    tracks = defaultdict(list)
    for i, r in enumerate(rows):
        tracks[(r['ep'], r['obj'])].append(i)
    wt = []
    for k, ix in tracks.items():
        y = S['adds'][ix] > THR
        if y.sum() >= 10 and (~y).sum() >= 10:
            wt.append(auroc(S['score'][ix], y)[0])
    pos = S['adds'] > THR
    out = dict(test='G-B', rule='INFORMATIVE iff AUROC >= 0.75 and >= 8 episodes with positives; FALSIFIED iff '
                                'AUROC < 0.65; else INCONCLUSIVE; > 2 % rows missing -> INCONCLUSIVE',
               calibrate_sha256=hashlib.sha256(open(a.calibrate, 'rb').read()).hexdigest(),
               n_rows=len(ids), n_answered=len(rows), n_missing=len(missing), missing=missing[:200],
               primary=dict(prim, score='1 - P(aligned)', label='symmetric registered ADD > 2 cm (kit frame-0)',
                            verdict=verdict),
               depth_audit_behind_same_rows=behind_check,
               thresholds={f'{t:g}cm': pooled(S['score'], S['adds'], t) for t in (1.0, 3.0, 5.0)},
               alt_alignment={'global_fit': pooled(S['score'], S['glob'], THR),
                              'frame0_all_objects': pooled(S['score'], S['f0all'], THR)},
               per_episode=per_ep, per_class=per_cls,
               loo=dict(values=loo, min=min(x for x in loo.values() if x is not None),
                        max=max(x for x in loo.values() if x is not None)),
               within_track=dict(n_tracks=len(wt), mean=round(float(np.mean(wt)), 4) if wt else None),
               flag_rates=dict(pos_p_lt_0p5=round(float((S['p'][pos] < 0.5).mean()), 4) if pos.any() else None,
                               neg_p_lt_0p5=round(float((S['p'][~pos] < 0.5).mean()), 4) if (~pos).any() else None),
               spearman_with_behind=round(float(spearmanr(S['score'], S['behind']).correlation), 4),
               mean_confidence=round(float(S['conf'].mean()), 4), fake=any(ans[k].get('fake') for k in ans))
    json.dump(out, open(os.path.join(a.out, 'GB_result.json'), 'w'), indent=1, default=float)
    ci = (prim.get('ci95') or {}).get('ci')
    M = [f'# Test G-B result{" (FAKE ANSWERS - pipeline test only)" if out["fake"] else ""}', '',
         f'- Verdict: **{verdict}**',
         f'- Pooled AUROC of 1 - P(aligned) for ADD > 2 cm: **{v}** (95 % episode-bootstrap CI '
         f'{"withheld" if ci is None else f"{ci[0]:.2f}-{ci[1]:.2f}"}); {prim["n_pos"]} positives / {prim["n_neg"]} '
         f'negatives; {prim["episodes_with_pos"]} episodes with positives',
         f'- Check: depth-audit `behind` AUROC on the same rows: {behind_check["auroc"]} (0.600 on all 7,835)',
         f'- Answered {len(rows)} of {len(ids)} rows; missing {len(missing)}',
         f'- Alternative alignments (diagnostic): global fit {out["alt_alignment"]["global_fit"]["auroc"]}, '
         f'frame-0 all objects {out["alt_alignment"]["frame0_all_objects"]["auroc"]}', '',
         '| ep | n | pos | AUROC |', '|---|---|---|---|']
    for e in PRIMARY:
        r = per_ep[e]
        M.append(f"| {e} | {r['n_pos'] + r['n_neg']} | {r['n_pos']} | {r['auroc']} |")
    open(os.path.join(a.out, 'GB_result.md'), 'w').write('\n'.join(M) + '\n')
    print('\n'.join(M[:8]))


if __name__ == '__main__':
    main()
