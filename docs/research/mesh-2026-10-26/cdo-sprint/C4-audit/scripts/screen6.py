"""G2 stage-1 screen (PREREG s7, addendum 2). Diagnostic [D]: public scans stand in for the hidden scans.

One mesh_metric.evaluate() per generated mesh (its GT-free Sim(3) copy), with the eval roster EMPTIED and the 6 seeds
3001..3006 (the audit_multiseed.py pattern with 6 seeds instead of 50). Run only after the generated files' SHA256SUMS
is committed. Each mesh is scored once: a label already in OUT is never re-run; a crash is retried once and logged.
The record keeps every seed row plus the audit summary (cdo_med, w30, anc_med, ...).

Usage: MESH_SCR=<scratch> screen6.py MANIFEST.tsv OUT.jsonl [--workers N]
Manifest lines: label<TAB>object<TAB>path
"""
import argparse, json, os, sys, time, traceback
from multiprocessing import Pool

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, '..', '..', '..', '..', '..', '..'))
sys.path.insert(0, os.path.join(REPO, 'docs/research/mesh-2026-10-26/scripts'))
sys.path.insert(0, HERE)
from audit_multiseed import summarise          # noqa: E402  (same summary as the 50-seed audit)
SEEDS = tuple(range(3001, 3007))


def work(item):
    import mesh_metric as MM
    MM.ROSTER = {}                                   # no eval seeds (PREREG s2, s7)
    label, obj, path = item
    t0 = time.time()
    errs = []
    for attempt in (1, 2):
        try:
            rec = MM.evaluate(label, obj, path, group='g2_screen', seeds_extra=SEEDS, min_seeds=0, min_extra=len(SEEDS))
            rec['screen'] = dict(attempt=attempt, errors=errs, summary=summarise(rec), secs=round(time.time() - t0, 1))
            return rec
        except Exception:
            errs.append(traceback.format_exc()[-2000:])
    return dict(label=label, object=obj, path=path, error=errs)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('manifest'); ap.add_argument('out')
    ap.add_argument('--workers', type=int, default=2)
    a = ap.parse_args()
    items = [tuple(l.rstrip('\n').split('\t')[:3]) for l in open(a.manifest) if l.strip() and not l.startswith('#')]
    done = set()
    if os.path.exists(a.out):
        done = {json.loads(l)['label'] for l in open(a.out) if l.strip()}
    todo = [it for it in items if it[0] not in done]
    print(time.strftime('%FT%TZ', time.gmtime()), f'{len(items)} meshes, {len(done)} done, {len(todo)} to score, '
          f'{a.workers} workers', flush=True)
    with Pool(a.workers) as pool, open(a.out, 'a') as f:
        for rec in pool.imap_unordered(work, todo):
            f.write(json.dumps(rec) + '\n'); f.flush()
            s = rec.get('screen', {}).get('summary', {})
            print(time.strftime('%FT%TZ', time.gmtime()), rec['label'], 'ERROR' if 'error' in rec else
                  f"cdo_med {s.get('cdo_med')} w30 {s.get('w30')} anc {s.get('anc_med')}", flush=True)


if __name__ == '__main__':
    main()
