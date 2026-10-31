"""b4_identity: SPEC section 7 cross-object identity test over all public bundles of a clean B4 run (PREREG B.15).

GMG_MODE=clean, same run folder as tools/b4_extract.py (role own). For every object-episode: its route-A shell (saved by
b4_extract from the object's good frames, shell_<obj>.npy) is registered (rigid best-of-24 PCA-start ICP, no scale) onto
every other good object-episode's shell (no TRACK_FAIL); the test passes if the nearest is one of o's own other
episodes; not testable if o has no other good public episode. A failure of the cross test or of any split test (saved
by b4_extract) marks o IDENTITY_SWAP. Writes RUN/identity/cross.json and updates each episode.json (sanity
identity_cross, flags), then the run ledger (manifest).
Usage: GMG_MODE=clean python gmg/tools/b4_identity.py --run <DATA>/gmg/runs/<clean run> [--eps 0,2,...]
"""
import argparse
import json
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
MR = os.path.dirname(os.path.dirname(HERE))
if MR not in sys.path:
    sys.path.insert(0, MR)
from gmg import guard  # noqa: E402

PUBLIC = [0, 2, 11, 12, 13, 18, 21, 22, 23, 24, 26, 27, 31, 39, 40, 41, 42, 43, 44, 45]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--run', required=True)
    ap.add_argument('--eps', default=','.join(str(e) for e in PUBLIC))
    a = ap.parse_args()
    if guard.mode() != 'clean':
        raise SystemExit('b4_identity runs in GMG_MODE=clean only')
    import numpy as np
    from gmg import track_sanity as TS
    run = guard.set_run(a.run)
    t0 = time.time()
    eps = [int(x) for x in a.eps.split(',')]
    metas, shells, good = {}, {}, []
    for ep in eps:
        bdir = os.path.join(run, 'bundle', 'public', f'ep{ep}')
        m = guard.load_json(os.path.join(bdir, 'episode.json'), 'own')
        metas[ep] = m
        for o in m['objects']:
            p = guard.open_input(os.path.join(bdir, f'shell_{o}.npy'), 'own')
            shells[(ep, o)] = np.load(p).astype(np.float64)
            if 'TRACK_FAIL' not in m['sanity'][o]['flags']:
                good.append((ep, o))
    res = {}
    for key in sorted(shells):
        r = TS.cross_test(shells, key, good)
        res[f'ep{key[0]}:{key[1]}'] = r
        print(key, {k: r.get(k) for k in ('testable', 'pass_', 'nearest', 'd_own_mm', 'd_other_mm', 'reason')},
              flush=True)
    os.makedirs(os.path.join(run, 'identity'), exist_ok=True)
    with open(os.path.join(run, 'identity', 'cross.json'), 'w') as f:
        json.dump(dict(good=[f'ep{e}:{o}' for e, o in good], results=res, sec=round(time.time() - t0, 1)), f, indent=1)
    for ep, m in metas.items():
        for o in m['objects']:
            r = res[f'ep{ep}:{o}']
            san = m['sanity'][o]
            san['identity_cross'] = {k: v for k, v in r.items() if k != 'chamfers_mm'}
            split_fail = any(v.get('testable') and not v.get('pass_') for v in (san.get('identity_split') or {}).values())
            cross_fail = bool(r.get('testable') and not r.get('pass_'))
            if (split_fail or cross_fail) and 'IDENTITY_SWAP' not in san['flags']:
                san['flags'].append('IDENTITY_SWAP')
            san['identity_fail'] = dict(split=split_fail, cross=cross_fail)
        with open(os.path.join(run, 'bundle', 'public', f'ep{ep}', 'episode.json'), 'w') as f:
            json.dump(m, f)
    guard.write_manifest(os.path.join(run, 'manifests', 'identity.json'), extra=dict(step='B4', prereg='B.15'))


if __name__ == '__main__':
    main()
