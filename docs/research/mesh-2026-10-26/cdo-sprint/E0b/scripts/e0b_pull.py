"""Pull the E0b box results (non-bulk: everything but pts/) from the HF store run folder and check them against the
box SHA256SUMS. Usage: python -I e0b_pull.py RUN_ID OUTDIR   (writes OUTDIR/runs/<RUN_ID>/results/e0b/...)"""
import hashlib, os, sys

from huggingface_hub import snapshot_download

run, out = sys.argv[1:3]
snapshot_download('aebatirel/v2d-store', repo_type='dataset', local_dir=out, max_workers=8,
                  allow_patterns=[f'runs/{run}/results/e0b/**', f'runs/{run}/run_job.log', f'runs/{run}/*.log'],
                  ignore_patterns=[f'runs/{run}/results/e0b/pts/**'])
R = f'{out}/runs/{run}/results/e0b'
rows = [l.rstrip('\n').split('  ', 1) for l in open(f'{R}/SHA256SUMS') if l.strip()]
present = bad = 0
for h, p in rows:
    f = os.path.join(R, p)
    if not os.path.exists(f):
        continue
    present += 1
    if hashlib.sha256(open(f, 'rb').read()).hexdigest() != h:
        bad += 1
        print('BAD', p)
skipped = sum(1 for _, p in rows if p.startswith('./pts/'))
print(f'{present} files present, {bad} bad, {len(rows) - present} not pulled ({skipped} bulk pts)')
sys.exit(1 if bad or len(rows) - present != skipped else 0)
