"""Download explicit store paths (single files, no listing) into OUTDIR, with backoff on HTTP 429.
Usage: python -I dl_retry.py OUTDIR LISTFILE"""
import os, sys, time
from huggingface_hub import hf_hub_download
out, lst = sys.argv[1], sys.argv[2]
paths = [l.strip() for l in open(lst) if l.strip()]
ok = bad = 0
for p in paths:
    if os.path.exists(os.path.join(out, p)):
        ok += 1; continue
    for att in range(5):
        try:
            f = hf_hub_download('aebatirel/v2d-store', p, repo_type='dataset', local_dir=out)
            print('ok', p, os.path.getsize(f), flush=True); ok += 1; break
        except Exception as e:
            msg = repr(e)[:200]
            if '429' in msg:
                w = 30 * (att + 1); print('429, wait', w, p, flush=True); time.sleep(w); continue
            print('FAIL', p, msg, flush=True); bad += 1; break
    time.sleep(0.5)
print('done ok', ok, 'fail', bad)
