import sys, json
from huggingface_hub import HfApi
api = HfApi()
files = api.list_repo_files('aebatirel/v2d-store', repo_type='dataset')
out = {}
for run in sys.argv[1:]:
    out[run] = [f for f in files if f.startswith(f'runs/{run}/')]
json.dump(out, open('data/store_files.json', 'w'), indent=0)
for r, fs in out.items():
    print(r, len(fs))
