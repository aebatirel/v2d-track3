import sys
from huggingface_hub import hf_hub_download, HfApi
out = sys.argv[1]
R = 'runs/20261026-gl10A2-5e0e100/'
files = [R + 'refs/glockt/ep10/processed/sequence_id=t3_ep010/robot_name=sharpa_wave/ref_gl_ilc.parquet'] + \
        [R + 'refs/perc2mck/ep10/' + f for f in ('ref_summary.json', 'mkref_log.txt', 'qa_ref.json', 'contact_retarget.json')]
for f in files:
    print(hf_hub_download('aebatirel/v2d-store', f, repo_type='dataset', local_dir=out))
api = HfApi()
for e in api.list_repo_tree('aebatirel/v2d-store', repo_type='dataset', path_in_repo=R.rstrip('/')):
    print('TOP', e.path, getattr(e, 'size', None))
