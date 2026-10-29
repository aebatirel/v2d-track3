import sys
from huggingface_hub import hf_hub_download, HfApi
dst = sys.argv[1]
fs = HfApi().list_repo_files('aebatirel/v2d-store', repo_type='dataset')
want = []
for pat in sys.argv[2:]:
    want += [f for f in fs if all(p in f for p in pat.split('&'))]
for f in sorted(set(want)):
    p = hf_hub_download('aebatirel/v2d-store', f, repo_type='dataset', local_dir=dst)
    print(p)
