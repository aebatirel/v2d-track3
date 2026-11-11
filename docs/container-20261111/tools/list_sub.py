import json, sys
from huggingface_hub import HfApi
from concurrent.futures import ThreadPoolExecutor
api = HfApi(); R = 'aebatirel/v2d-store'
runs = [e.path for e in api.list_repo_tree(R, repo_type='dataset', path_in_repo='runs', recursive=False)]
def one(r):
    out = []
    try:
        for e in api.list_repo_tree(R, repo_type='dataset', path_in_repo=f'{r}/results/submission/results', recursive=False):
            if hasattr(e, 'size'):
                out.append(dict(path=e.path, size=e.size, oid=getattr(e, 'blob_id', None),
                                lfs=(e.lfs.sha256 if getattr(e, 'lfs', None) else None)))
    except Exception as ex:
        pass
    return out
with ThreadPoolExecutor(16) as ex:
    res = [x for l in ex.map(one, runs) for x in l]
json.dump(res, open(sys.argv[1], 'w'), indent=0)
print(len(res), 'files in', len({x['path'].split('/results/')[0] for x in res}), 'runs')
