"""Joins the masses eval-retrain training boxes into ONE confirmation job (2026-10-31; PLAN.md section 5 rules 2-4,
docs/research/work/masses-eval-20261031/JOBS.txt "C1"). CPU only; reads each box's results/mass_eval/summary.json
(tools/mass_eval_verify.py; one single-file download per box), no ground truth.
Per episode over all boxes that trained it (e.g. eval 1: S1a seed 42 and S1b seed 43 on two boxes):
  - any box INVALID -> the episode is out (rule 3: its packed policy stays). A seed counts from a VERIFIED box, or from an
    INCOMPLETE box whose only gaps are OTHER seeds (missing or thin, nothing unchecked): e.g. seed 42 of a grasp-lock box
    whose seed 43 must be retrained counts once seed 43 arrives from its new box;
  - both pre-registered seeds (--seeds, 42 and 43) must come from VERIFIED boxes with n >= 8 scored training-box rollouts
    each (PLAN section 5 rule 2 as amended 31 Oct, review F1). Otherwise the episode is INCOMPLETE: no candidate, no
    single-seed fallback; the output names, per missing seed, what to do (retrain only those seeds on a new box, same
    reference and commit; or re-run tools/mass_eval_verify.py on CPU when the box only lacked a packed file). A seed
    outside --seeds is ignored and reported;
  - rule 2 across the VERIFIED boxes' seeds (tools/mass_eval_verify.rule2): the higher 10-rollout mean, within 0.005 the
    lower sd, still tied the first of --seeds (42);
  - the confirmation strings for that seed: grasp lock RUN@refs/mass1_sf/ep<N>,refs/mass1s<seed>_glockt/ep<N> and
    <N>:RUN:ck=results/mass1s<seed>_glock_public/ep<N>/best/policy.safetensors; standard learner RUN@refs/perc2mcks/ep<N>
    and <N>:RUN:ck=<the chosen checkpoint>, MA_ARGS --physics and the pieces h5_reeval.sh does not already add.
Prints the ops/jobs/h5_reeval.sh job string (KEEP_RESULTS / base PICK_EXTRA / PACKED_TXT of the pack on the board) and
writes the choices to --out. Refused: two standard-learner candidates whose pieces differ (one shared /content/assets).
Usage: mass_eval_merge.py --table packed_refs.json --out C.json [--n 10] [--seeds "42 43"]
       [--keep "20261026-pack6-5203d42 20261030-c33B-0202139"] [--base-pick "33:20261029-rcB-34bf6ae"]
       [--packed-txt /content/v2d-track3/results/submissions/20261030-track3g-candidate/summary.txt] S1.json S2.json ...
"""
import argparse, json, os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from mass_eval_verify import rule2, H5_PIECES, MIN_N   # noqa: E402

PROPS = '/content/v2d-track3/docs/research/physics-2026-10-30/props_masses_only.json'


def rel(p):
    """a box path /content/<rel> (or a mock root .../content/<rel>) -> <rel>"""
    return p[p.index('/content/') + len('/content/'):] if '/content/' in p else p


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('summaries', nargs='+'); ap.add_argument('--table', required=True); ap.add_argument('--out', required=True)
    ap.add_argument('--n', type=int, default=10); ap.add_argument('--seeds', default='42 43')
    ap.add_argument('--keep', default='20261026-pack6-5203d42 20261030-c33B-0202139')
    ap.add_argument('--base-pick', default='33:20261029-rcB-34bf6ae')
    ap.add_argument('--packed-txt', default='/content/v2d-track3/results/submissions/20261030-track3g-candidate/summary.txt')
    a = ap.parse_args()
    tab = json.load(open(a.table))['episodes']; order = a.seeds.split()
    per = {}
    for f in a.summaries:
        S = json.load(open(f))
        for e, x in S['episodes'].items():
            per.setdefault(e, []).append(dict(run=S['run'], mode=S['mode'], status=x['status'], seeds=x['seeds'],
                                              retrain=x.get('retrain_seeds', []), unchecked=x.get('unchecked', [])))
    out, runs, picks, eps, pieces, ma = {}, [], [], [], set(), False
    for e in sorted(per, key=int):
        B = per[e]; T = tab[e]
        if any(b['status'] == 'INVALID' for b in B):
            out[e] = dict(decision='OUT (a box INVALID: packed policy stays)', boxes=[(b['run'], b['status']) for b in B]); continue
        ok = [b for b in B if b['status'] == 'VERIFIED' or (b['status'] == 'INCOMPLETE' and not b['unchecked'])]
        st, src, extra = {}, {}, []
        for b in ok:
            for s, v in b['seeds'].items():
                if s not in order:
                    extra.append(f'{s} ({b["run"]})'); continue
                if v.get('n', 0) >= MIN_N and s not in b['retrain']:
                    if s in st:
                        sys.exit(f'ep{e}: seed {s} trained on two boxes ({src[s]["run"]}, {b["run"]})')
                    st[s] = v; src[s] = b
        gone = [s for s in order if s not in st]
        if gone:                                                   # review F1: a missing or thin seed -> INCOMPLETE
            todo = {}
            for s in gone:
                had = [b for b in B if s in b['seeds']]
                if not had:
                    todo[s] = 'not trained on any box: train it on a new box (same reference and commit)'
                elif any(s in b['retrain'] or b['seeds'][s].get('n', 0) < MIN_N for b in had):
                    todo[s] = (f'missing or n < {MIN_N} on ' + ', '.join(f'{b["run"]} (n {b["seeds"][s].get("n", 0)})' for b in had)
                               + ': retrain only this seed on a new box, same reference and commit')
                else:
                    todo[s] = ('trained, but ' + ', '.join(f'{b["run"]} is {b["status"]}' for b in had)
                               + ' only for unchecked files: re-run tools/mass_eval_verify.py on CPU once they are there (no retrain)')
            out[e] = dict(decision=f'INCOMPLETE (seeds {gone} missing or n < {MIN_N}: retrain only those seeds on a new box, '
                                   f'same reference and commit; PLAN section 5 rule 2 as amended 31 Oct)',
                          todo=todo, boxes=[(b['run'], b['status']) for b in B], ignored_seeds=extra,
                          stats={s: {k: v.get(k) for k in ('n', 'mean', 'sd', 'min')} for s, v in st.items()})
            continue
        c = rule2(st, order)
        r = src[c]['run']
        if T['mode'] == 'glock':
            runs.append(f'{r}@refs/mass1_sf/ep{e},refs/mass1s{c}_glockt/ep{e}')
            picks.append(f'{e}:{r}:ck=results/mass1s{c}_glock_public/ep{e}/best/policy.safetensors')
        else:
            runs.append(f'{r}@refs/perc2mcks/ep{e}'); picks.append(f'{e}:{r}:ck={rel(st[c]["checkpoint"])}'); ma = True
            pieces.add(T.get('pieces') or '')
        eps.append(e)
        out[e] = dict(decision='CANDIDATE', seed=c, run=r, mode=T['mode'], ignored_seeds=extra,
                      checkpoint=st[c].get('checkpoint'), boxes=[(b['run'], b['status']) for b in B],
                      stats={s: {k: v.get(k) for k in ('n', 'mean', 'sd', 'min')} for s, v in st.items()})
    if len(pieces) > 1:
        sys.exit(f'standard-learner candidates need different pieces {sorted(pieces)} in the one /content/assets: confirm them on separate boxes')
    extra = sorted(f'/content/v2d-track3/{p}' for p in pieces if p and p not in H5_PIECES)
    E = ' '.join(eps)
    job = (f'N={a.n} KEEP_RESULTS="{a.keep}" RUNS_EXTRA="{" ".join(runs)}" PICK_EXTRA="{" ".join([a.base_pick] + picks).strip()}" '
           f'MASS_EPS="{E}" EVAL_ONLY="{E}" EPS_ONLY="{E}" '
           + (f'MA_ARGS="--physics {PROPS}" ' if ma else '') + (f'ASSET_PIECES_EXTRA="{" ".join(extra)}" ' if extra else '')
           + f'PACKED_TXT={a.packed_txt} bash ops/jobs/h5_reeval.sh')
    json.dump(dict(episodes=out, seeds=order, min_n=MIN_N, job=job if eps else None), open(a.out, 'w'), indent=1)
    for e, x in out.items():
        print(f'ep{e}: {x["decision"]}' + (f' seed {x["seed"]} ({x["run"]}) ' + json.dumps(x['stats']) if x['decision'] == 'CANDIDATE' else '')
              + (' :: ' + '; '.join(f's{s}: {t}' for s, t in x['todo'].items()) if x.get('todo') else '')
              + (f' :: ignored seeds {x["ignored_seeds"]}' if x.get('ignored_seeds') else ''))
    print('JOB: ' + (job if eps else 'none (no candidate)'))


if __name__ == '__main__':
    main()
