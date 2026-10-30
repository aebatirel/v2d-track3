"""Frozen eval-track registry for the gmg guard (SPEC section 17; written in B0 round 3, DEVIATIONS 31).

  python frozen_eval_tracks.py [--out gmg/frozen_eval_tracks.json] [--data <scratchpad>]

SPEC section 17: the eval tracks are frozen to the store run `20261025-evperc-4f596df`; a run checks each local
`data/eval/ep<N>/poses.npz` against the store copy's sha256 and stops on a mismatch. This tool lists that store run
through the Hugging Face API (file names, sizes and the LFS sha256 the hub keeps for every LFS file; nothing is
downloaded) and writes the sha256 of `results/evalperc/ep<N>/poses.npz` for the 20 eval episodes to
gmg/frozen_eval_tracks.json, which the guard loads for every tracks input under data/eval/. It also hashes the local
copies (bytes only, nothing is decoded) and records whether each matches. It does not import the guard and reads no
other file. The eval tracks are inputs (P1), not outputs: no eval result is read or used.
"""
import argparse
import datetime
import hashlib
import json
import os
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
GMG = os.path.dirname(HERE)
SCRATCH = '/tmp/claude-0/-home-user-v2d-track3/90d4009c-b597-536b-9d55-58f81afca135/scratchpad'
STORE = 'aebatirel/v2d-store'
RUN = 'runs/20261025-evperc-4f596df'
EVAL_EPS = (1, 3, 5, 6, 8, 10, 14, 15, 16, 19, 20, 25, 28, 30, 32, 33, 35, 36, 37, 38)    # SPEC section 17


def listing():
    url = f'https://huggingface.co/api/datasets/{STORE}/tree/main/{RUN}/results/evalperc?recursive=true'
    with urllib.request.urlopen(url, timeout=60) as r:
        return json.load(r)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', default=os.path.join(GMG, 'frozen_eval_tracks.json'))
    ap.add_argument('--data', default=os.environ.get('GMG_DATA_ROOT', SCRATCH))
    a = ap.parse_args()
    files, sizes = {}, {}
    for x in listing():
        p = x.get('path', '')
        parts = p.split('/')
        if x.get('type') == 'file' and parts[-1] == 'poses.npz' and parts[-2].startswith('ep'):
            oid = (x.get('lfs') or {}).get('oid')
            if not oid:
                raise SystemExit(f'no LFS sha256 for {p}')
            files[parts[-2]] = oid
            sizes[parts[-2]] = int(x.get('size') or 0)
    want = {f'ep{n}' for n in EVAL_EPS}
    if set(files) != want:
        raise SystemExit(f'store run episodes {sorted(files)} != eval episodes {sorted(want)}')
    local = {}
    for ep in sorted(files, key=lambda e: int(e[2:])):
        lp = os.path.join(a.data, 'data', 'eval', ep, 'poses.npz')
        if not os.path.isfile(lp):
            local[ep] = 'absent'
            continue
        h = hashlib.sha256(open(lp, 'rb').read()).hexdigest()
        local[ep] = 'match' if h == files[ep] else f'MISMATCH {h}'
    out = dict(schema='gmg-frozen-eval-tracks/1', spec='SPEC v1 rev 1 section 17', store=STORE, run=RUN,
               path='results/evalperc/ep<N>/poses.npz',
               source='Hugging Face API tree listing: LFS sha256 per file (no download)',
               created_utc=datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'),
               files=dict(sorted(files.items(), key=lambda kv: int(kv[0][2:]))),
               bytes=dict(sorted(sizes.items(), key=lambda kv: int(kv[0][2:]))), local_check=local)
    with open(a.out, 'w') as f:
        json.dump(out, f, indent=1)
    print(json.dumps(dict(out=a.out, episodes=len(files), local=sorted(set(v.split()[0] for v in local.values())))))


if __name__ == '__main__':
    main()
