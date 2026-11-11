import json, sys, hashlib, os
from huggingface_hub import hf_hub_download
from concurrent.futures import ThreadPoolExecutor
cand = json.load(open(sys.argv[1])); target = json.load(open(sys.argv[2]))['results_md5']; out = sys.argv[3]; dl = sys.argv[4]
want = {v: k for k, v in target.items() if k.endswith('.json')}
def one(x):
    try:
        p = hf_hub_download('aebatirel/v2d-store', x['path'], repo_type='dataset', local_dir=dl)
        return x['path'], hashlib.md5(open(p, 'rb').read()).hexdigest()
    except Exception as e:
        return x['path'], 'ERR ' + str(e)[:80]
with ThreadPoolExecutor(16) as ex:
    res = list(ex.map(one, cand))
hits = {}
for path, m in res:
    if m in want:
        hits.setdefault(want[m], []).append(path)
json.dump(dict(hits=hits, all=res), open(out, 'w'), indent=1)
print('json targets', len(want), 'matched', len(hits)); print(sorted(set(want.values()) - set(hits)))
