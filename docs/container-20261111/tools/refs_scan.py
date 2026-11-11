import json, sys, os, glob, hashlib
import pyarrow.parquet as pq
from huggingface_hub import hf_hub_download
S = sys.argv[1]
src = json.load(open(f'{S}/container/stage/rollout_sources.json'))
listing = {x['path']: x for x in json.load(open(f'{S}/container/dl/runs_listing.json'))}
out = {}
for ep, rec in sorted(src.items()):
    run = rec[ep + '.json']['source'].split('/')[1]
    j = json.load(open(f'{S}/container/stage/rollouts/{ep}.json'))
    ref = j['parquet']; assert ref.startswith('/workspace/')
    store = f'runs/{run}/' + ref[len('/workspace/'):]
    p = hf_hub_download('aebatirel/v2d-store', store, repo_type='dataset', local_dir=f'{S}/container/dl/refs')
    row = pq.read_table(p, columns=['object_urdf_paths', 'object_body_names', 'sequence_id', 'robot_name']).to_pylist()[0]
    seqdir = os.path.dirname(os.path.dirname(ref))
    stage = os.path.dirname(os.path.dirname(seqdir)) + '/reconstructed_stage'
    st = [k for k in listing if k.startswith(f'runs/{run}/' + stage[len('/workspace/'):] + '/')]
    urdfs = []
    for u in row['object_urdf_paths']:
        k = f'runs/{run}/' + u[len('/content/'):]
        urdfs.append((u, k in listing))
    out[ep] = dict(run=run, ref=ref, ref_md5=hashlib.md5(open(p, 'rb').read()).hexdigest(), objects=row['object_body_names'],
                   urdfs=urdfs, stage=st)
    print(ep, run, row['object_body_names'], [(u, ok) for u, ok in urdfs], 'stage', [s.split('/')[-1] for s in st])
json.dump(out, open(f'{S}/container/stage/refs_scan.json', 'w'), indent=1)
