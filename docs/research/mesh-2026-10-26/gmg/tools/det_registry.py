"""Det-file registry for the gmg guard (B0 round 2): sha256, size and member names of every det dump.

  python det_registry.py [--out gmg/det_registry.json]

The guard applies the det key filter (mask keys only) to a file by its identity, not by the role it is opened under.
One identity test is the sha256: a renamed or copied det_f0.npz keeps the original's bytes. This tool hashes every
DATA/data/store/ep*/det_f<N>.npz (bytes only; nothing is decompressed), lists each file's zip member names (the
central directory; no array is read) and writes gmg/det_registry.json, which the guard loads at import. A box that
never downloads the originals still recognises a copy. Run it again whenever new det dumps are added.
"""
import argparse
import datetime
import glob
import json
import os
import sys

MR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if MR not in sys.path:
    sys.path.insert(0, MR)
from gmg import guard  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', default=guard.DET_REGISTRY)
    a = ap.parse_args()
    D = guard.CFG['data']
    files = []
    for p in sorted(glob.glob(os.path.join(D, 'data', 'store', 'ep*', 'det_f*.npz'))):
        rp = os.path.realpath(p)
        with guard._internal():
            sha = guard._sha256(rp)
            names = sorted(guard._npz_names(rp) or ())
        hits = sorted(set(names) & set(guard.DET_SIGNATURE))
        if len(hits) < guard.DET_SIGNATURE_MIN:
            sys.exit(f'det_registry: {rp} carries only {hits} of the signature keys; update DET_SIGNATURE')
        files.append(dict(path=os.path.relpath(rp, D), bytes=os.path.getsize(rp), sha256=sha, keys=names,
                          signature_hits=hits))
    out = dict(schema='gmg-det-registry/1',
               created_utc=datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'),
               commit=guard._git('rev-parse', 'HEAD'), data_root=D,
               note='sha256 and zip member names only (no array read); the guard filters any file with one of these '
                    'sha256 values to NPZ_KEYS["det"]',
               allowed_keys=list(guard.NPZ_KEYS['det']), signature_keys=sorted(guard.DET_SIGNATURE), files=files)
    with open(a.out, 'w') as f:
        json.dump(out, f, indent=1)
    print(json.dumps(dict(out=a.out, files=len(files), sizes=sorted({x['bytes'] for x in files})[:3])))


if __name__ == '__main__':
    main()
