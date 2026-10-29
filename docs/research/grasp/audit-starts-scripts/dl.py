import json, sys
from huggingface_hub import hf_hub_download
d = json.load(open('data/store_files.json'))
want = {'20261024-e2-e49e83d': 'ep21', '20261024-e3-e49e83d': 'ep2', '20261024-w1-37cc551': 'ep26'}
n = 0
for run, ep in want.items():
    for f in d[run]:
        g = f[len('runs/' + run) + 1:]
        if '.safetensors' in g or 'hydra' in g or 'e2s_raw' in g or 'cloudflared' in g or 'tunnel' in g:
            continue
        parts = g.split('/')
        if any(p.startswith('ep') and p.rstrip('.r1') not in (ep,) and p not in (ep, ep + '.r1', ep + '-s42') and not p.startswith('episode') for p in parts[:-1]):
            continue
        if parts[-1].startswith('glock_ep') and parts[-1] != f'glock_{ep}.log':
            continue
        if parts[-1].startswith('ref_ep') and parts[-1] != f'ref_{ep}.log':
            continue
        hf_hub_download('aebatirel/v2d-store', f, repo_type='dataset', local_dir='data/store')
        n += 1
print('downloaded', n)
