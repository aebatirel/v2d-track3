#!/usr/bin/env python3
"""Score test G-A (Gemini mesh selector) — GROUND-TRUTH SIDE. Run only after every G-A request has an answer.

Reads the G-A cache (run_gemini.py), the G-A specs (ids, objects) and the probe's per-mesh CD-O against the public
scans (docs/research/mesh-2026-10-26/results/gen-probe/rows.json, key `cdo` = cdo_eval as in gen_analysis.py; the
GT-free metric `gtf` from the same file is only used to reproduce the pre-registered bar).

Statistic (PREREG.md, copied from the work log 2026-11-13 ~00:50 UTC):
  rho  = Spearman(Gemini expected score, -CD-O) over all 104 meshes (average ranks for ties);
  hits = number of the 10 objects on which Gemini's top mesh (highest expected score) is the CD-O best of that
         object's scored meshes. A tie for the top expected score (|diff| <= 1e-9) gives credit 1/n_tied when the
         CD-O best is among the tied meshes.
  PASS iff rho > 0.46 and hits > 2; FAIL iff rho <= 0.46 and hits <= 2; otherwise INCONCLUSIVE.
  Missing answers: meshes without an ok answer after the runner's retries are left out and listed; if more than 5 of
  the 104 are missing the verdict is INCONCLUSIVE (missing data).
Diagnostics (reported, never used for the verdict): per-object rho, regret and CD-O rank of Gemini's pick; the
GT-free metric's rho and hits recomputed from rows.json (must give 0.4650 and 2); rho with an object-cluster
bootstrap 95 % CI (2,000 draws, seed 0); mean within-object rho; agreement between Gemini and the GT-free metric.
Usage: score_GA.py --cache cache_GA.jsonl --specs specs_GA.jsonl --rows .../gen-probe/rows.json --out DIR
                   [--allow_fake]
"""
import argparse, json, os
from collections import defaultdict

import numpy as np
from scipy.stats import spearmanr

RHO_BAR, HITS_BAR, MAX_MISSING = 0.46, 2, 5


def load_answers(cache, allow_fake):
    ans = {}
    for l in open(cache):
        r = json.loads(l)
        if not r.get('ok'):
            continue
        if r.get('fake') and not allow_fake:
            raise SystemExit('cache holds fake answers; pass --allow_fake only for tests')
        ans.setdefault(r['id'], r)
    return ans


def top_credit(labels, E, cdo):
    """Fractional hit credit and the pick (first of the tied tops) for one object."""
    E = np.asarray(E, float); cdo = np.asarray(cdo, float)
    tops = np.nonzero(E >= E.max() - 1e-9)[0]
    best = int(np.argmin(cdo))
    return (1.0 / len(tops) if best in tops else 0.0), int(tops[0]), tops.tolist(), best


def rho(x, y):
    return float(spearmanr(x, y).correlation)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--cache', required=True); ap.add_argument('--specs', required=True)
    ap.add_argument('--rows', required=True); ap.add_argument('--out', required=True)
    ap.add_argument('--allow_fake', action='store_true')
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    specs = [json.loads(l) for l in open(a.specs)]
    R = {r['label']: r for r in json.load(open(a.rows))}
    assert len(specs) == 104 and {s['id'] for s in specs} == set(R), 'specs must cover the 104 scored meshes'
    A = load_answers(a.cache, a.allow_fake)
    missing = [s['id'] for s in specs if s['id'] not in A]
    recs = []
    for s in specs:
        if s['id'] not in A:
            continue
        x = A[s['id']]['response']['answers']['shape_match']
        recs.append(dict(label=s['id'], object=s['object'], group=s['group'], E=float(x['score']),
                         conf=float(x['confidence']), probs={k: float(v) for k, v in x['probabilities'].items()},
                         cdo=float(R[s['id']]['cdo']), gtf=float(R[s['id']]['gtf'])))
    E = np.array([r['E'] for r in recs]); cdo = np.array([r['cdo'] for r in recs]); gtf = np.array([r['gtf'] for r in recs])
    r_all = rho(E, -cdo)
    by = defaultdict(list)
    for i, r in enumerate(recs):
        by[r['object']].append(i)
    per, hits, gt_hits = [], 0.0, 0.0
    for o, ix in by.items():
        c, pick, tops, best = top_credit([recs[i]['label'] for i in ix], E[ix], cdo[ix])
        hits += c
        gc, gpick, _, _ = top_credit(None, -gtf[ix], cdo[ix])
        gt_hits += gc
        order = np.argsort(cdo[ix], kind='stable')
        per.append(dict(object=o, n=len(ix), rho=rho(E[ix], -cdo[ix]) if len(ix) > 2 else None,
                        pick=recs[ix[pick]]['label'], pick_E=float(E[ix][pick]), pick_cdo=float(cdo[ix][pick]),
                        n_tied_top=len(tops), credit=c, best=recs[ix[best]]['label'], best_cdo=float(cdo[ix][best]),
                        regret=float(cdo[ix][pick] - cdo[ix][best]),
                        pick_cdo_rank=int(1 + list(order).index(pick)),
                        gtfree_rho=rho(-gtf[ix], -cdo[ix]), gtfree_pick=recs[ix[gpick]]['label'], gtfree_credit=gc))
    # reference: the GT-free metric's pooled rho and hits over the same meshes (pre-registered bar 0.46 / 2)
    gt_rho = rho(-gtf, -cdo)
    # object-cluster bootstrap of rho (diagnostic)
    rng = np.random.default_rng(0)
    objs = list(by)
    bs = []
    for _ in range(2000):
        pick = rng.integers(0, len(objs), len(objs))
        ix = np.concatenate([by[objs[p]] for p in pick])
        bs.append(rho(E[ix], -cdo[ix]))
    bs = np.asarray([b for b in bs if np.isfinite(b)])
    if len(missing) > MAX_MISSING:
        verdict = f'INCONCLUSIVE (missing data: {len(missing)} of 104 meshes unanswered > {MAX_MISSING})'
    elif r_all > RHO_BAR and hits > HITS_BAR:
        verdict = 'PASS (rho > 0.46 and top mesh = CD-O best on more than 2 of 10 objects)'
    elif r_all <= RHO_BAR and hits <= HITS_BAR:
        verdict = 'FAIL (rho <= 0.46 and top mesh = CD-O best on 2 or fewer objects)'
    else:
        verdict = 'INCONCLUSIVE (the two criteria disagree)'
    out = dict(test='G-A', rule='PASS iff rho > 0.46 and hits > 2; FAIL iff rho <= 0.46 and hits <= 2; else '
                                'INCONCLUSIVE; > 5 missing -> INCONCLUSIVE',
               n_answered=len(recs), missing=missing, rho=round(r_all, 4), hits=round(hits, 3), verdict=verdict,
               rho_boot95=[round(float(np.percentile(bs, 2.5)), 4), round(float(np.percentile(bs, 97.5)), 4)],
               mean_within_object_rho=round(float(np.nanmean([p['rho'] for p in per if p['rho'] is not None])), 4),
               gtfree_reference=dict(rho=round(gt_rho, 4), hits=gt_hits,
                                     note='must reproduce 0.4650 and 2 (selection.json) when all 104 are answered'),
               agreement_gemini_vs_gtfree=round(rho(E, -gtf), 4),
               mean_confidence=round(float(np.mean([r['conf'] for r in recs])), 4) if recs else None,
               per_object=per, per_mesh=recs, fake=any(A[k].get('fake') for k in A))
    json.dump(out, open(os.path.join(a.out, 'GA_result.json'), 'w'), indent=1)
    L = [f'# Test G-A result{" (FAKE ANSWERS - pipeline test only)" if out["fake"] else ""}', '',
         f'- Verdict: **{verdict}**',
         f'- rho = Spearman(Gemini expected score, -CD-O) over {len(recs)} meshes: **{r_all:.4f}** (bar > {RHO_BAR}; '
         f'object-bootstrap 95 % CI {out["rho_boot95"][0]:.2f} to {out["rho_boot95"][1]:.2f})',
         f'- Gemini top mesh = CD-O best on **{hits:g}** of {len(by)} objects (bar > {HITS_BAR})',
         f'- Reference, GT-free metric on the same meshes: rho {gt_rho:.4f}, hits {gt_hits:g}',
         f'- Missing answers: {len(missing)} {missing if missing else ""}', '',
         '| object | n | rho | Gemini pick (E) | its CD-O | CD-O rank | best (CD-O) | regret | GT-free rho |',
         '|---|---|---|---|---|---|---|---|---|']
    for p in per:
        f2 = lambda v: '-' if v is None or not np.isfinite(v) else f'{v:.2f}'  # noqa: E731
        L.append(f"| {p['object']} | {p['n']} | {f2(p['rho'])} | {p['pick'].split('/', 1)[1]} ({p['pick_E']:.2f}"
                 f"{', tie x' + str(p['n_tied_top']) if p['n_tied_top'] > 1 else ''}) | {p['pick_cdo']:.3f} | "
                 f"{p['pick_cdo_rank']} | {p['best'].split('/', 1)[1]} ({p['best_cdo']:.3f}) | {p['regret']:.3f} | "
                 f"{f2(p['gtfree_rho'])} |")
    open(os.path.join(a.out, 'GA_result.md'), 'w').write('\n'.join(L) + '\n')
    print('\n'.join(L[:7]))


if __name__ == '__main__':
    main()
