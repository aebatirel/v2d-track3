#!/usr/bin/env python3
"""Test G-B rows: the depth audit's valid object-frames on its 19 primary public episodes (30 Oct; 7,835 rows).
INFERENCE SIDE: the row set is defined by the audit's own `valid` flag (vis_frac >= 0.20 and >= 50 selected pixels),
which uses only our tracks, our hands, our meshes and stereo depth. It is read from:
  - audit/public/ep<N>/audit.json (in the repository): per object, `frames` and `valid`. Where valid == frames, every
    frame of that track is a row;
  - otherwise a re-audit of that episode with the unchanged pipeline/depth_audit.py (audit.npz, `valid` per frame),
    given with --reaudit EP=PATH. Only ep11's blue cup needs it (130 of 137 valid). The re-audit's inputs must have
    the sha256s recorded in the original audit.json; this is checked.
Optional --check_keys per_frame.csv: compares the row keys with the (ep, frame, obj, valid) columns of the depth
audit's calibration table. That file also holds labels; ONLY those four columns are read, and nothing else is
returned or printed from it.
Usage: gb_rows.py --audit_root .../depth-audit-20261030/audit/public --reaudit 11=PATH/audit.npz --out gb_rows.csv
                  [--check_keys .../calib_gt/v2/per_frame.csv]
"""
import argparse, csv, hashlib, json, os

import numpy as np

PRIMARY = [0, 2, 11, 12, 13, 18, 21, 22, 24, 26, 27, 31, 39, 40, 41, 42, 43, 44, 45]     # depth-audit PREREG.md


def sha(p):
    return hashlib.sha256(open(p, 'rb').read()).hexdigest()


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--audit_root', required=True); ap.add_argument('--out', required=True)
    ap.add_argument('--reaudit', action='append', default=[])
    ap.add_argument('--check_keys', default=None)
    a = ap.parse_args()
    re = {int(x.split('=', 1)[0]): x.split('=', 1)[1] for x in a.reaudit}
    rows, notes = [], []
    for e in PRIMARY:
        A = json.load(open(os.path.join(a.audit_root, f'ep{e}', 'audit.json')))
        for slot, o in enumerate(A['objects']):
            s = A['summary'][o]
            if s['valid'] == s['frames'] == A['T']:
                valid = np.ones(A['T'], bool)
            else:
                if e not in re:
                    raise SystemExit(f'ep{e} {o}: {s["valid"]}/{s["frames"]} valid; needs --reaudit {e}=audit.npz')
                RJ = json.load(open(os.path.join(os.path.dirname(re[e]), 'audit.json')))
                for k in ('poses', 'depth', 'hands'):
                    if RJ['inputs'][k]['sha256'] != A['inputs'][k]['sha256']:
                        raise SystemExit(f'ep{e}: re-audit input {k} differs from the original audit')
                Z = np.load(re[e])
                names = [str(x) for x in Z['names']]
                valid = Z['valid'][:, names.index(o)].astype(bool)
                if int(valid.sum()) != s['valid'] or RJ['summary'][o] != s:
                    raise SystemExit(f'ep{e} {o}: re-audit summary differs from the original audit')
                notes.append(f'ep{e} {o}: {int(valid.sum())}/{len(valid)} valid from the re-audit (summary identical '
                             f'to the original; invalid frames {np.nonzero(~valid)[0].tolist()})')
            for t in np.nonzero(valid)[0]:
                rows.append((e, o, slot, int(t)))
    with open(a.out, 'w', newline='') as fh:
        w = csv.writer(fh); w.writerow(['ep', 'obj', 'slot', 'frame'])
        w.writerows(rows)
    print(f'{len(rows)} rows from {len(PRIMARY)} episodes -> {a.out}')
    for n in notes:
        print(n)
    if a.check_keys:
        mine = {(e, o, t) for e, o, _, t in rows}
        theirs = set()
        with open(a.check_keys) as fh:
            for r in csv.DictReader(fh):
                if int(r['ep']) in PRIMARY and r['valid'] == '1':
                    theirs.add((int(r['ep']), r['obj'], int(r['frame'])))
        print(f'key check against the audit table: {len(mine)} rows here, {len(theirs)} there, '
              f'{len(mine & theirs)} shared -> {"IDENTICAL" if mine == theirs else "DIFFERENT"}')


if __name__ == '__main__':
    main()
