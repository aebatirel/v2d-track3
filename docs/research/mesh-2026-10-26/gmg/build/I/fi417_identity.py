"""PREREG F-I4.17.6 step 2 (i): at fi4_rev 16 the REV 17 code reproduces REV 16 on w1 t = 10 mm byte for byte (pieces
and records except timing). Two processes: the gmg package at commit 3b7e6d0 (REV 16 build; extracted with git
archive) and the working tree, both with platebody.REV = 16.

  python fi417_identity.py worker MR OUT.npz            one side (MR = the directory that holds gmg/)
  python fi417_identity.py compare A.npz B.npz OUT.json
"""
import json
import os
import sys


def worker(mr, out):
    os.environ.setdefault('GMG_MODE', 'dev')
    sys.path.insert(0, os.path.join(mr, 'gmg', 'tests'))
    sys.path.insert(0, mr)
    import numpy as np
    from gmg import platebody as PB, interlock as IL
    import test_interlock as TI
    PB.REV = 16
    b, cand, recs, sides = TI._waiver_case(10)
    arrs, rec = {}, {}
    for r in recs:
        x = r['target']
        if r.get('_waiver'):
            for kk in ('slotted', 'default'):
                for i, V in enumerate(r['_waiver'][kk]):
                    arrs[f'{x}_{kk}_{i:03d}'] = np.asarray(V)
        w = r.get('waiver_fi4')
        if w is not None:
            rec[f'{x}_{r["decision"]}_{r["voxels"]}'] = dict(decision=r['decision'], tier=r['tier'],
                                                             flags=sorted(r['flags']), waiver=w)
    js = json.dumps(rec, sort_keys=True, default=IL._jdefault)
    np.savez(out, records=np.frombuffer(js.encode(), np.uint8), **arrs)
    print('pieces', len(arrs), 'records', len(rec), 'file', PB.__file__, 'REV', PB.REV)


def _strip(o):
    if isinstance(o, dict):
        return {k: _strip(v) for k, v in o.items() if k not in ('sec', 'seconds', 'time_s', 'elapsed_s')}
    if isinstance(o, list):
        return [_strip(v) for v in o]
    return o


def compare(a, b, out):
    import numpy as np
    A, B = np.load(a), np.load(b)
    ka = sorted(k for k in A.files if k != 'records')
    kb = sorted(k for k in B.files if k != 'records')
    same_keys = ka == kb
    same_arr = same_keys and all(A[k].tobytes() == B[k].tobytes() and A[k].shape == B[k].shape for k in ka)
    ra = _strip(json.loads(A['records'].tobytes().decode()))
    rb = _strip(json.loads(B['records'].tobytes().decode()))
    diff = []

    def walk(x, y, path):
        if type(x) != type(y):
            diff.append((path, 'type'))
        elif isinstance(x, dict):
            for k in sorted(set(x) | set(y)):
                if k not in x or k not in y:
                    diff.append((path + '/' + k, 'missing'))
                else:
                    walk(x[k], y[k], path + '/' + k)
        elif isinstance(x, list):
            if len(x) != len(y):
                diff.append((path, 'len'))
            else:
                for i, (p, q) in enumerate(zip(x, y)):
                    walk(p, q, f'{path}[{i}]')
        elif x != y:
            diff.append((path, f'{x!r} != {y!r}'[:200]))
    walk(ra, rb, '')
    res = dict(pieces=len(ka), same_piece_keys=same_keys, pieces_byte_identical=bool(same_arr),
               records_identical_except_timing=not diff, record_diffs=diff[:50], n_record_diffs=len(diff),
               a=a, b=b)
    with open(out, 'w') as f:
        json.dump(res, f, indent=1)
    print(json.dumps({k: v for k, v in res.items() if k != 'record_diffs'}), diff[:10])


if __name__ == '__main__':
    if sys.argv[1] == 'worker':
        worker(sys.argv[2], sys.argv[3])
    else:
        compare(sys.argv[2], sys.argv[3], sys.argv[4])
