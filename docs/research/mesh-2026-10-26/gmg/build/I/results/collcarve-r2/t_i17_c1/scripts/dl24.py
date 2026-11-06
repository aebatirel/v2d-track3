import sys, hashlib
from huggingface_hub import hf_hub_download
out = sys.argv[1]
base = 'runs/20261030-physS1-6a814df/refs/glockt/ep24/'
for f in ['processed/sequence_id=t3_ep024/robot_name=sharpa_wave/ref_gl_ilc.parquet',
          'reconstructed_stage/t3_ep024_support.usda']:
    p = hf_hub_download('aebatirel/v2d-store', base + f, repo_type='dataset', local_dir=out)
    print(p, hashlib.md5(open(p, 'rb').read()).hexdigest())
