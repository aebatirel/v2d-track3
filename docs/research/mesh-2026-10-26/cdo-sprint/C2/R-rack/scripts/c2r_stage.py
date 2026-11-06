#!/usr/bin/env python
"""C2/R inputs (PREREG section 4): fetch C0b's rack inputs from the HF store run and record their sha256.

Fetched (runs/<RUN>/results/c0b/...): pts/B/ep<e>_plastic_dish_rack.npz, markers/ep<e>.json for e in 12,13,26,27,31,
params.json, t0_c0b.json, the C0b rack run log/outputs that exist (cand/rack/*.jsonl, selection.json,
plastic_dish_rack/joint.json) for reporting only. Never a scan, mocap, parquet pose, *_align file or library_v3 mesh.
Usage: python -I c2r_stage.py --run RUN_ID --out DIR
"""
import argparse, hashlib, json, os, shutil, sys

from huggingface_hub import hf_hub_download

STORE = 'aebatirel/v2d-store'
EPS = [12, 13, 26, 27, 31]
BAN = ('scan', 'mocap', '_align', 'parquet', 'library_v3')


def sha(p):
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for b in iter(lambda: f.read(1 << 22), b''):
            h.update(b)
    return h.hexdigest()


def main():
    ap = argparse.ArgumentParser(); ap.add_argument('--run', required=True); ap.add_argument('--out', required=True)
    a = ap.parse_args()
    base = f'runs/{a.run}/results/c0b'
    need = [f'pts/B/ep{e}_plastic_dish_rack.npz' for e in EPS] + [f'markers/ep{e}.json' for e in EPS] + \
           ['params.json', 't0_c0b.json']
    opt = ['cand/rack/candidates.jsonl', 'cand/rack/selection.json', 'cand/rack/plastic_dish_rack/joint.json',
           'logs/build/rack_run.log', 'selection.json']
    os.makedirs(a.out, exist_ok=True)
    rows = {}
    for rel in need + opt:
        assert not any(b in rel for b in BAN), rel
        try:
            p = hf_hub_download(STORE, f'{base}/{rel}', repo_type='dataset', cache_dir=os.path.join(a.out, '.cache'))
        except Exception as ex:  # noqa: BLE001
            if rel in need:
                print(json.dumps(dict(missing=rel, error=f'{type(ex).__name__}: {str(ex)[:200]}')))
                sys.exit(1)
            rows[rel] = None
            continue
        dst = os.path.join(a.out, rel)
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        shutil.copyfile(p, dst)
        rows[rel] = sha(dst)
    shutil.rmtree(os.path.join(a.out, '.cache'), ignore_errors=True)
    P = json.load(open(os.path.join(a.out, 'params.json')))
    rack = P['targets'].get('rack/run')
    out = dict(run=a.run, files=rows, rack_params=rack, t0_c0b_m=P.get('t0_c0b_m'))
    json.dump(out, open(os.path.join(a.out, 'STAGED.json'), 'w'), indent=1)
    print(json.dumps(dict(rack_params=rack, n_files=sum(v is not None for v in rows.values()))))


if __name__ == '__main__':
    main()
