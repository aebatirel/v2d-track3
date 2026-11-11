import json, sys, re
from huggingface_hub import HfApi
from concurrent.futures import ThreadPoolExecutor
api = HfApi(); R = 'aebatirel/v2d-store'
ck = json.load(open(sys.argv[1]))['found']
runs = sorted({p.split('/')[1] for v in ck.values() for p in v})
subs = json.load(open(sys.argv[2]))
runs = sorted(set(runs) | {x['path'].split('/')[1] for x in subs})
print(len(runs), 'runs', file=sys.stderr)
def one(r):
    out = []
    for e in api.list_repo_tree(R, repo_type='dataset', path_in_repo=f'runs/{r}', recursive=True):
        if hasattr(e, 'size'):
            out.append(dict(path=e.path, size=e.size, oid=getattr(e, 'blob_id', None),
                            lfs=(e.lfs.sha256 if getattr(e, 'lfs', None) else None)))
    return out
with ThreadPoolExecutor(12) as ex:
    res = [x for l in ex.map(one, runs) for x in l]
json.dump(res, open(sys.argv[3], 'w'))
print(len(res), 'files', file=sys.stderr)
