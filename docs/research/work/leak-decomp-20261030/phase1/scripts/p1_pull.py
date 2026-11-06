"""Phase-1 pull (30 Oct 2026): one run's Phase-1 poses files from the HF store, one hf_hub_download per file (no store listing;
BUILD.md §1, JOBS.txt "After the boxes"). Reads OUT/runs/<rid>/results/leak_p1/summary.json (downloaded first, the same way) and
pulls per episode perc2/poses_world_vo.npz, perc2/poses.npz, perc2scan/poses_world_vo.npz and, on REPEAT episodes,
perc2rep/poses_world_vo.npz. ORACLE outputs (P_s = scan templates). Usage: python3 -I p1_pull.py OUT RUN_ID
(2026-10-30)
"""
import json, sys, time
from huggingface_hub import hf_hub_download
out, rid = sys.argv[1], sys.argv[2]
base = f'runs/{rid}/results/leak_p1'
summ = json.load(open(f'{out}/{base}/summary.json'))
want = []
for ep, e in summ['episodes'].items():
    want += [f'{base}/{ep}/perc2/poses_world_vo.npz', f'{base}/{ep}/perc2/poses.npz', f'{base}/{ep}/perc2scan/poses_world_vo.npz']
    if 'o2' in e['arms']:
        want.append(f'{base}/{ep}/perc2rep/poses_world_vo.npz')
for f in want:
    for i in range(6):
        try:
            hf_hub_download('aebatirel/v2d-store', f, repo_type='dataset', local_dir=out); print('ok', f, flush=True); break
        except Exception as ex:
            print('retry', i, f, type(ex).__name__, str(ex)[:120], flush=True); time.sleep(30 * (i + 1))
    else:
        print('FAILED', f, flush=True)
