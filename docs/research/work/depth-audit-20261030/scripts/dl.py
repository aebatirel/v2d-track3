"""Download explicit store paths into an own new dir. Usage: python -I dl.py OUTDIR path1 [path2 ...]"""
import sys, os
from huggingface_hub import hf_hub_download
out = sys.argv[1]; os.makedirs(out, exist_ok=True)
for p in sys.argv[2:]:
    f = hf_hub_download('aebatirel/v2d-store', p, repo_type='dataset', local_dir=out)
    print(f, os.path.getsize(f))
