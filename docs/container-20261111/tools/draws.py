import json, re, sys, collections
from concurrent.futures import ThreadPoolExecutor
from huggingface_hub import hf_hub_download
S = sys.argv[1]
d = json.load(open(f'{S}/container/dl/runs_listing.json'))
pat = re.compile(r'episode_0000(\d\d)\.json$')
c = [x['path'] for x in d if pat.search(x['path']) and ('/results/h5/' in x['path'] or '/ev10_nj/' in x['path'] or '/pf_arms/' in x['path'])]
w = json.load(open(f'{S}/container/stage/weights_record.json'))
want = {v['expected']: int(k) for k, v in w.items()}
def one(p):
    try:
        j = json.load(open(hf_hub_download('aebatirel/v2d-store', p, repo_type='dataset', local_dir=f'{S}/container/dl/draws')))
        return p, j.get('checkpoint_sha256'), j.get('metrics', {})
    except Exception as e:
        return p, None, {}
with ThreadPoolExecutor(16) as ex:
    res = list(ex.map(one, c))
by = collections.defaultdict(list)
for p, sha, m in res:
    if sha in want and m:
        by[want[sha]].append(dict(path=p, add_auc=m.get('add_auc'), mppe_cm=m.get('mppe_cm'), maniptrans_sr=m.get('maniptrans_sr'),
                                  rpe=m.get('relative_position_error_cm'), chord_sr=m.get('chord_sr')))
json.dump(by, open(f'{S}/container/verify/stored_draws_13h_checkpoints.json', 'w'), indent=1)
print({k: len(v) for k, v in sorted(by.items())})
