import json, sys, hashlib, os, shutil
import pandas as pd
from huggingface_hub import hf_hub_download
S, B = sys.argv[1], sys.argv[2]
found = json.load(open(f'{S}/ckpt_found.json'))['found']
f = pd.read_parquet(f'{B}/submitted/track3_submission.parquet')
f['ep'] = f.row_id.str.extract(r'^track_3/e0*(\d+)/')[0].astype(int)
out = f'{B}/weights/track3_13h'; os.makedirs(out, exist_ok=True); rec = {}
roll = json.load(open(f'{S}/container/stage/rollout_sources.json'))
for ep, shas in f.groupby('ep').checkpoint_sha256.unique().items():
    assert len(shas) == 1; want = shas[0]
    paths = found[want]
    pref = sorted(paths, key=lambda p: (not p.split('/', 2)[2].startswith('results/'), p))
    src = pref[0]
    p = hf_hub_download('aebatirel/v2d-store', src, repo_type='dataset', local_dir=f'{S}/container/dl/ckpt')
    got = hashlib.sha256(open(p, 'rb').read()).hexdigest()
    dst = f'{out}/episode_{ep:06d}.safetensors'
    if got == want:
        shutil.copyfile(p, dst)
    rj = json.load(open(f'{S}/container/stage/rollouts/episode_{ep:06d}.json'))
    rec[ep] = dict(store_path=src, sha256=got, expected=want, ok=got == want, rollout_checkpoint_sha256=rj['checkpoint_sha256'],
                   evaluated_path=rj['checkpoint'], size=os.path.getsize(p))
    print(ep, 'MATCH' if got == want else 'MISMATCH', got[:16], want[:16], 'rollout', rj['checkpoint_sha256'] == want, src)
json.dump(rec, open(f'{S}/container/stage/weights_record.json', 'w'), indent=1)
