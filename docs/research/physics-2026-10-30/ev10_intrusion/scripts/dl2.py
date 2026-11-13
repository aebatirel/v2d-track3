import sys
from huggingface_hub import hf_hub_download
out = sys.argv[1]; R = 'runs/20261026-gl10A2-5e0e100/'
for f in ('COMMIT', 'glock_ep10.log', 'job.log', 'run_job.log'):
    print(hf_hub_download('aebatirel/v2d-store', R + f, repo_type='dataset', local_dir=out))
