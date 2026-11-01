"""GT-free scoring of one eval episode's rollouts against our packed reference (2026-10-31, pack 9b D arm;
docs/research/work/pack9b-20261031/PREREG.md section 4). tools/e10v_score.py's code, unchanged, for any roster episode:
its module-level roster (NAMES) is set to the episode's kit roster (data/track_3_evaluation_objects.json: object names
and slot order, allowed for eval episodes) before anything is scored, in this process and in every worker. No ground
truth exists or is read: inputs are the official evaluator's rollout parquets, our reference parquet P (the packed
reference the policy was trained on; the D arm trains on a byte copy), the kit's metric code and our library meshes.
Per rollout (e10v_score.Scorer.score): sim_vs_ref exactly as pipeline/qa.py policy; RPE / MPPE / AUC and per-object
numbers as the score-status session's GT-free audit (docs/analysis/evalaudit-20261031/audit.py, rdlib chain); fail =
RPE > 5 cm; own-reference check (OWN = P): P's poses at each reference_frame equal the rollout's stored reference
columns (|dpos| <= 1e-6 m, |dq| <= 1e-6 up to sign); scored = every score finite.
Usage: dr_score.py --kit KIT --lib meshes/library_v3 --ep N --ref P=REF.parquet --out OUT.json --set NAME:OWN:GLOB [...]
                   [--roster KIT/data/track_3_evaluation_objects.json] [--jobs N]
       (sets used by tools/dr_verdict.py: conf = the D candidate's confirmation draws, packed = the packed policy's H5p7
        draws, old = the old packed draw; GLOB e.g. <dl>/runs/<C>/results/h5/r*/ep14/episode_000014.parquet; draws are
        ordered by the r<i> number in the path, a path without r<i> is draw 0)
"""
import argparse, glob, hashlib, json, os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import e10v_score as E   # noqa: E402


def _init(kit, lib, refs, names, ep):
    E.NAMES = list(names); E.EP = int(ep)
    E._init(kit, lib, refs)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--kit', required=True); ap.add_argument('--lib', required=True); ap.add_argument('--out', required=True)
    ap.add_argument('--ep', type=int, required=True); ap.add_argument('--roster', default='')
    ap.add_argument('--ref', action='append', required=True, help='X=path (one reference: P)')
    ap.add_argument('--set', action='append', required=True, help='NAME:OWN:GLOB')
    ap.add_argument('--jobs', type=int, default=0)
    a = ap.parse_args()
    roster = json.load(open(a.roster or f'{a.kit}/data/track_3_evaluation_objects.json'))['episodes']
    names = roster[str(a.ep)]
    E.NAMES = list(names); E.EP = a.ep
    md5 = lambda f: hashlib.md5(open(f, 'rb').read()).hexdigest()
    refs, ref_info = {}, {}
    for x in a.ref:
        k, p = x.split('=', 1); refs[k] = E.ref_poses(p); ref_info[k] = dict(path=p, md5=md5(p), frames=int(len(refs[k])))
    out = dict(ep=a.ep, names=names, refs=ref_info, rule='docs/research/work/pack9b-20261031/PREREG.md section 4',
               rpe_fail_cm=E.RPE_FAIL_CM, scorer='tools/e10v_score.py via tools/dr_score.py', sets={})
    jobs = a.jobs or int(os.environ.get('E10V_SCORE_JOBS') or min(8, os.cpu_count() or 1))
    specs = [(spec.split(':', 2)) for spec in a.set]
    work = [(f, own) for name, own, g in specs for f in sorted(glob.glob(g), key=lambda p: (E.draw_no(p), p))]
    if jobs > 1 and len(work) > 1:
        from concurrent.futures import ProcessPoolExecutor
        with ProcessPoolExecutor(jobs, initializer=_init, initargs=(a.kit, a.lib, refs, names, a.ep)) as ex:
            done = dict(zip(work, ex.map(E._one, work)))
    else:
        _init(a.kit, a.lib, refs, names, a.ep); done = {w: E._one(w) for w in work}
    for name, own, g in specs:
        files = sorted(glob.glob(g), key=lambda p: (E.draw_no(p), p)); rows = [done[(f, own)] for f in files]
        out['sets'][name] = dict(own=own, glob=g, n_files=len(files), n_scored=sum(1 for r in rows if r.get('scored')), rollouts=rows)
        print(f'ep{a.ep} {name} (own {own}): {len(files)} rollouts, {out["sets"][name]["n_scored"]} scored; ' + '; '.join(
            f"r{r['draw']} " + ' '.join(f"{X} s_v_r {r['vs'][X]['sim_vs_ref']:.4f} RPE {r['vs'][X]['RPE']:.2f}" for X in r.get('vs', {}))
            + ('' if r.get('own_ref_check', {}).get('ok', own == '-') else ' OWN-REF-CHECK FAILED') + (f" ERROR {r['error']}" if 'error' in r else '')
            for r in rows), flush=True)
    json.dump(out, open(a.out, 'w'), indent=1)


if __name__ == '__main__':
    main()
