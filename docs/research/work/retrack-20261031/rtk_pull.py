"""Pull the P_o' outputs of the re-track boxes (2026-10-31), ONE hf_hub_download per file: never a store listing,
never --include (HF 429; JOBS.txt "After the boxes"). Per run id: runs/<rid>/results/leak_p1/summary.json first, then
per episode in it bundle.json, perc2/poses_world_vo.npz, perc2/poses.npz, perc2/run.json (43 files for a 10-episode
box, with run_job.log and job.log). P_o needs no pull: Phase 1's bundles are in po_bundles/ (this folder) and its tracks on this VM
(scratchpad leak/p1/runs/20261030-orcP1{a,b,c}-87fc869/...).
usage: python3 -I rtk_pull.py OUT RUN_ID [RUN_ID ...] [--dry-run]     (--dry-run prints the paths after the summaries)
"""
import json, os, sys, time

args = [a for a in sys.argv[1:] if a != '--dry-run']; dry = '--dry-run' in sys.argv
out, rids = args[0], args[1:]
STORE = os.environ.get('HF_STORE', 'aebatirel/v2d-store')


def get(f):
    if os.path.isfile(f'{out}/{f}'):
        return True
    from huggingface_hub import hf_hub_download
    for i in range(6):
        try:
            hf_hub_download(STORE, f, repo_type='dataset', local_dir=out); print('ok', f, flush=True); return True
        except Exception as x:
            print('retry', i, f, type(x).__name__, str(x)[:120], flush=True); time.sleep(30 * (i + 1))
    print('FAILED', f, flush=True); return False


n = bad = 0
for rid in rids:
    base = f'runs/{rid}/results/leak_p1'
    if not get(f'{base}/summary.json'):
        bad += 1; continue
    s = json.load(open(f'{out}/{base}/summary.json'))
    for f in ('run_job.log', 'job.log'):                                 # env-snapshot restore + gpu line (PREREG §5 e)
        n += 1; bad += not get(f'runs/{rid}/{f}')
    for ep in s['episodes']:
        for f in ('bundle.json', 'perc2/poses_world_vo.npz', 'perc2/poses.npz', 'perc2/run.json'):
            n += 1
            if dry:
                print(f'{base}/{ep}/{f}'); continue
            bad += not get(f'{base}/{ep}/{f}')
            time.sleep(0.5)
print(f'{n} episode files for {len(rids)} run(s){" (dry run)" if dry else ""}; failed {bad}')
sys.exit(1 if bad else 0)
