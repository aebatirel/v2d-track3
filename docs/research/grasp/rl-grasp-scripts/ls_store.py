import sys
from huggingface_hub import HfApi
fs = HfApi().list_repo_files('aebatirel/v2d-store', repo_type='dataset')
for pat in sys.argv[1:]:
    for f in fs:
        if all(p in f for p in pat.split('&')):
            print(f)
