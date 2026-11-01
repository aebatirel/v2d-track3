"""After the Masses v2 boxes (CPU): download exactly the files the v2 merge reads, ONE hf_hub_download per file (no store
listing; HF 429), into OUT/runs/<run>/... (the store layout, so mass_verdict.py --content takes OUT/runs/<run>).
Per run and episode of that box (refs_v2.json 'boxes', or --eps for a re-run box): the 4 cells' best/summary.json (or only
--seeds), plus the run's results/mass_check/{verify.json, summary.json, verdict.txt, stored_refs_v2.txt, arms_ep<N>.json}
and job.log. A missing cell file is reported, not fatal (the merge counts the cell as missing -> INCOMPLETE).
usage: python3 -I pull_results.py OUT RUN:EPS [RUN:EPS ...] [--seeds "42 43"] [--dry]
  e.g. pull_results.py dl 20261101-mv2a-abc1234:24,13 20261101-mv2b-abc1234:11,31"""
import json, os, sys, time
args = [a for a in sys.argv[1:] if not a.startswith('--')]; dry = '--dry' in sys.argv
seeds = sys.argv[sys.argv.index('--seeds') + 1].split() if '--seeds' in sys.argv else ['42', '43']
if '--seeds' in sys.argv:
    args.remove(sys.argv[sys.argv.index('--seeds') + 1])
out, specs = args[0], args[1:]
want = []
for sp in specs:
    run, eps = sp.split(':'); eps = eps.split(',')
    want += [f'runs/{run}/job.log'] + [f'runs/{run}/results/mass_check/{f}' for f in ('verify.json', 'summary.json', 'verdict.txt', 'stored_refs_v2.txt')]
    want += [f'runs/{run}/results/mass_check/arms_ep{e}.json' for e in eps]
    want += [f'runs/{run}/results/{a}s{s}_glock_public/ep{e}/best/summary.json' for e in eps for a in ('mass0', 'mass1') for s in seeds]
if dry:
    print('\n'.join(want)); print(f'{len(want)} single-file downloads, 0 listings'); sys.exit(0)
from huggingface_hub import hf_hub_download   # noqa: E402
log = []
for f in want:
    for i in range(5):
        try:
            hf_hub_download('aebatirel/v2d-store', f, repo_type='dataset', local_dir=out); log.append(dict(f=f, ok=True, tries=i + 1)); break
        except Exception as ex:
            if 'EntryNotFound' in type(ex).__name__ or '404' in str(ex)[:300]:
                log.append(dict(f=f, ok=False, error='not in the store')); break
            time.sleep(20 * (i + 1))
    else:
        log.append(dict(f=f, ok=False, error='failed after 5 tries'))
    print(('ok  ' if log[-1]['ok'] else 'MISS') + ' ' + f, flush=True); time.sleep(2)
json.dump(log, open(f'{out}/pull_results_log.json', 'w'), indent=1)
print(f"{sum(1 for x in log if x['ok'])} of {len(log)} downloaded")
