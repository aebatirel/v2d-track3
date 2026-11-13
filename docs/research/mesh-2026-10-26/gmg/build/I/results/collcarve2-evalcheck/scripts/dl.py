"""Download the packed references (packed_refs.json, focused-pascal c6fe323) and their sim assets from the HF store."""
import sys, json, hashlib, os
from huggingface_hub import hf_hub_download, HfApi
refs = json.load(open(sys.argv[1])); out = sys.argv[2]; eps = sys.argv[3].split(',')
api = HfApi()
rep = {}
for ep in eps:
    e = refs['episodes'][ep]
    want = [p for p in e['pull_files'] if p.endswith(('.parquet', '.usda', 'contact_retarget.json', 'ref_summary.json',
                                                     'qa_ref.json', 'table_frame.npz', 'hands_refined.json', 'support_fill.json'))
            and ('/loaded/' not in p) and ('/e2s_raw/' not in p)]
    ref_path = f"runs/{e['source_run']}/{e['reference']}"
    if ref_path not in want:
        want.append(ref_path)
    if not e['shared_assets']:
        root = f"runs/{e['source_run']}/" + e['asset_root'].replace('/content/', '')
        try:
            want += [x.path for x in api.list_repo_tree("aebatirel/v2d-store", path_in_repo=root, repo_type="dataset",
                                                        recursive=True) if '.' in os.path.basename(x.path)]
        except Exception as ex:
            print('LIST FAIL', root, ex)
    r = {}
    for f in want:
        try:
            p = hf_hub_download("aebatirel/v2d-store", f, repo_type="dataset", local_dir=out)
            r[f] = hashlib.md5(open(p, 'rb').read()).hexdigest()
        except Exception as ex:
            r[f] = 'FAIL ' + type(ex).__name__ + ' ' + str(ex)[:150]
    md5_ref = r.get(ref_path)
    rep[ep] = dict(reference=ref_path, md5=md5_ref, md5_listed=e['md5'], md5_match=md5_ref == e['md5'], files=r)
    print(ep, 'ref md5 match', md5_ref == e['md5'], len(r), 'files', flush=True)
json.dump(rep, open(os.path.join(out, 'dl_report.json'), 'w'), indent=1)
