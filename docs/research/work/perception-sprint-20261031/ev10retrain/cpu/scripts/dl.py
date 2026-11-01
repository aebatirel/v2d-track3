"""Single-file store downloads (hf_hub_download, one per file, no listing). Usage: dl.py OUT path ..."""
import sys, time
from huggingface_hub import hf_hub_download
out = sys.argv[1]
for f in sys.argv[2:]:
    for i in range(4):
        try:
            print('ok', hf_hub_download('aebatirel/v2d-store', f, repo_type='dataset', local_dir=out), flush=True); break
        except Exception as e:
            print('retry', i, f, type(e).__name__, str(e)[:160], flush=True); time.sleep(20 * (i + 1))
    else:
        print('FAILED', f, flush=True)
