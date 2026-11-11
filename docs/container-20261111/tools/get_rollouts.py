import json, sys, hashlib, os, shutil
from huggingface_hub import hf_hub_download
hits = json.load(open(sys.argv[1]))['hits']; target = json.load(open(sys.argv[2]))['results_md5']; dl = sys.argv[3]; out = sys.argv[4]
os.makedirs(out, exist_ok=True); rec = {}
for name, paths in sorted(hits.items()):
    src = paths[0]
    pq = src[:-5] + '.parquet'
    rec[name[:-5]] = {}
    for f, t in ((src, name), (pq, name[:-5] + '.parquet')):
        p = hf_hub_download('aebatirel/v2d-store', f, repo_type='dataset', local_dir=dl)
        m = hashlib.md5(open(p, 'rb').read()).hexdigest()
        ok = m == target[t]
        print(f'{t}: {"MATCH" if ok else "MISMATCH"} md5 {m} expected {target[t]} from {f}')
        if ok:
            shutil.copyfile(p, os.path.join(out, t))
        rec[name[:-5]][t] = dict(source=f, md5=m, expected=target[t], ok=ok, sha256=hashlib.sha256(open(p,'rb').read()).hexdigest())
json.dump(rec, open(os.path.join(os.path.dirname(out.rstrip('/')), 'rollout_sources.json'), 'w'), indent=1)
