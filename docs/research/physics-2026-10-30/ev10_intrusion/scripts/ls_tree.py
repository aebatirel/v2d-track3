import sys, os
from huggingface_hub import HfApi
api = HfApi()
for p in sys.argv[1:]:
    try:
        for e in api.list_repo_tree('aebatirel/v2d-store', repo_type='dataset', path_in_repo=p, recursive=True):
            print(p, '|', e.path, getattr(e, 'size', None))
    except Exception as ex:
        print('ERR', p, repr(ex)[:300])
