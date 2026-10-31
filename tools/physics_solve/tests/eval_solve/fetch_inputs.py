"""Download the solver-relevant pull_files (refs/glockt/ep<N>/..., refs/sf/ep<N>/assets/...) of the 15 grasp-lock eval
episodes into a local mirror of the store (single-file downloads), then check md5 of each reference."""
import hashlib, json, sys, time
from huggingface_hub import hf_hub_download
tab, out = sys.argv[1], sys.argv[2]
d = json.load(open(tab))['episodes']
for e in sorted(d, key=int):
    r = d[e]
    if r['mode'] != 'glock':
        continue
    pre = f"runs/{r['source_run']}/"
    sel = [f for f in r['pull_files'] if f.startswith(pre + f'refs/glockt/ep{e}/') or f.startswith(pre + f'refs/sf/ep{e}/assets/')]
    t0 = time.time(); bad = []
    for f in sel:
        for i in range(4):
            try:
                hf_hub_download('aebatirel/v2d-store', f, repo_type='dataset', local_dir=out); break
            except Exception as ex:
                if i == 3: bad.append((f, str(ex)[:100]))
                time.sleep(5 * (i + 1))
    ref = f"{out}/{pre}{r['reference']}"
    try:
        md5 = hashlib.md5(open(ref, 'rb').read()).hexdigest()
    except Exception as ex:
        md5 = f'missing {ex}'
    print(f"ep{e} {r['source_run']} files {len(sel)} failed {len(bad)} md5 {md5} want {r['md5']} {'OK' if md5 == r['md5'] else 'MISMATCH'} {time.time()-t0:.0f}s {bad}", flush=True)
