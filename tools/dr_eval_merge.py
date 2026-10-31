"""Joins the D-arm training boxes into ONE confirmation job (2026-10-31, pack 9b; docs/research/work/pack9b-20261031/
PREREG.md sections 2-3, JOBS.txt "C"). CPU only; reads each box's results/dr_eval/summary.json (tools/dr_eval_verify.py;
one single-file download per box), no ground truth. tools/mass_eval_merge.py's logic with the D folders:
  - any box INVALID for an episode -> the episode is OUT (its packed policy stays). A seed counts from a VERIFIED box, or
    from an INCOMPLETE box whose only gaps are OTHER seeds (missing or thin, nothing unchecked);
  - both pre-registered seeds (--seeds, 42 43) must be there with n >= 8 scored training-box rollouts each, else the
    episode is INCOMPLETE (no single-seed fallback) and the output names what to do per missing seed;
  - PREREG section 2 (tools/mass_eval_verify.rule2): the higher training-box mean, within 0.005 the lower sd, still tied 42;
  - confirmation strings for that seed: grasp lock RUN@refs/drs<seed>_glockt/ep<N> and
    <N>:RUN:ck=results/drs<seed>_glock_public/ep<N>/best/policy.safetensors; standard learner RUN@refs/perc2mckdr/ep<N> and
    <N>:RUN:ck=<the chosen checkpoint>; the pieces h5_reeval.sh does not already add (none for 25 / 30).
Prints the ops/jobs/h5_reeval.sh job string (N 10, KEEP_RESULTS = pack 7's rollout sources, base PICK 33:rcB, DR_EPS =
EVAL_ONLY = EPS_ONLY = the candidates, PACKED_TXT = pack 7's summary) and writes --out with, per candidate, the run, seed,
store path and sha256 of its checkpoint and the table's packed sha256: tools/dr_verdict.py checks every confirmation
rollout against them.
Usage: dr_eval_merge.py --table packed_refs.json --out C.json [--n 10] [--seeds "42 43"] [--keep ...] [--base-pick ...]
       [--packed-txt ...] S1.json S2.json ...
"""
import argparse, json, os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from mass_eval_verify import rule2, H5_PIECES, MIN_N   # noqa: E402


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
        if S.get('arm') != 'dr':
            sys.exit(f'{f}: not a D-arm summary (arm {S.get("arm")!r}); tools/mass_eval_merge.py joins masses boxes')
        for e, x in S['episodes'].items():
            per.setdefault(e, []).append(dict(run=S['run'], mode=S['mode'], status=x['status'], seeds=x['seeds'],
                                              retrain=x.get('retrain_seeds', []), unchecked=x.get('unchecked', [])))
    out, runs, picks, eps, pieces = {}, [], [], [], set()
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
        if gone:
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
                               + ' only for unchecked files: re-run tools/dr_eval_verify.py on CPU once they are there (no retrain)')
            out[e] = dict(decision=f'INCOMPLETE (seeds {gone} missing or n < {MIN_N}: PREREG section 6)', todo=todo,
                          boxes=[(b['run'], b['status']) for b in B], ignored_seeds=extra,
                          stats={s: {k: v.get(k) for k in ('n', 'mean', 'sd', 'min')} for s, v in st.items()})
            continue
        c = rule2(st, order)
        r = src[c]['run']
        if T['mode'] == 'glock':
            ckp = f'results/drs{c}_glock_public/ep{e}/best/policy.safetensors'
            runs.append(f'{r}@refs/drs{c}_glockt/ep{e}'); picks.append(f'{e}:{r}:ck={ckp}')
        else:
            ckp = rel(st[c]['checkpoint'])
            runs.append(f'{r}@refs/perc2mckdr/ep{e}'); picks.append(f'{e}:{r}:ck={ckp}')
            pieces.add(T.get('pieces') or '')
        eps.append(e)
        out[e] = dict(decision='CANDIDATE', seed=c, run=r, mode=T['mode'], ignored_seeds=extra,
                      checkpoint=st[c].get('checkpoint'), store_checkpoint=f'runs/{r}/{ckp}', sha256=st[c].get('checkpoint_sha256'),
                      packed_sha256=T['packed_sha256'], boxes=[(b['run'], b['status']) for b in B],
                      stats={s: {k: v.get(k) for k in ('n', 'mean', 'sd', 'min')} for s, v in st.items()})
    # one /content/assets on the confirmation box (pack 6's ASSET_PIECES ev25 + ev10): std candidates with pieces that
    # h5_reeval.sh does not already add would reach every std episode evaluated beside them
    extra = sorted(f'/content/v2d-track3/{p}' for p in pieces if p and p not in H5_PIECES)
    if extra:
        sys.exit(f'standard-learner candidates need pieces {extra} beyond h5_reeval.sh\'s ASSET_PIECES: confirm them on separate boxes')
    E = ' '.join(eps)
    job = (f'N={a.n} KEEP_RESULTS="{a.keep}" RUNS_EXTRA="{" ".join(runs)}" PICK_EXTRA="{" ".join([a.base_pick] + picks).strip()}" '
           f'DR_EPS="{E}" EVAL_ONLY="{E}" EPS_ONLY="{E}" PACKED_TXT={a.packed_txt} bash ops/jobs/h5_reeval.sh')
    json.dump(dict(episodes=out, seeds=order, min_n=MIN_N, n=a.n, job=job if eps else None,
                   rule='docs/research/work/pack9b-20261031/PREREG.md sections 2-3'), open(a.out, 'w'), indent=1)
    for e, x in out.items():
        print(f'ep{e}: {x["decision"]}' + (f' seed {x["seed"]} ({x["run"]}) sha {str(x["sha256"])[:12]} ' + json.dumps(x['stats'])
                                           if x['decision'] == 'CANDIDATE' else '')
              + (' :: ' + '; '.join(f's{s}: {t}' for s, t in x['todo'].items()) if x.get('todo') else '')
              + (f' :: ignored seeds {x["ignored_seeds"]}' if x.get('ignored_seeds') else ''))
    print('JOB: ' + (job if eps else 'none (no candidate)'))


if __name__ == '__main__':
    main()
