"""b4_identity: SPEC section 7 cross-object identity test over all public bundles of a clean B4 run (PREREG B.15).

GMG_MODE=clean, same run folder as tools/b4_extract.py (role own). For every object-episode: its route-A shell (saved by
b4_extract from the object's good frames, shell_<obj>.npy) is registered (rigid best-of-24 PCA-start ICP, no scale) onto
every other good object-episode's shell (no TRACK_FAIL); the test passes if the nearest is one of o's own other
episodes; not testable if o has no other good public episode. A failure of the cross test or of any split test (saved
by b4_extract) marks o IDENTITY_SWAP. Round 2: the distance is TS.reg_chamfers (best of 4 subsample seeds, chamfer on the full shells; DEVIATIONS B4-R2.2);
the round-1 seed-0 verdict is stored beside and sets no flag. Writes RUN/identity/cross.json and updates each
episode.json (sanity
identity_cross, flags; TRACK_FAIL over all extraction frames, DEVIATIONS 99), then the run ledger (manifest).
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


_SHELLS = {}


def _one(kk):
    from gmg import track_sanity as TS
    return TS.reg_chamfers(_SHELLS[kk[0]], _SHELLS[kk[1]])


def _pool_map(shells, pairs, workers):
    """TS.reg_chamfers over PAIRS in WORKERS forked children (os.fork + os.pipe, pickle over the pipe). Not
    multiprocessing: its locks are POSIX semaphores, which open files under /dev/shm, a write outside the run for the
    strace audit. The children only compute and leave with os._exit (no file access, no atexit handler)."""
    import pickle
    _SHELLS.clear()
    _SHELLS.update(shells)
    if workers <= 1 or len(pairs) < 2:
        return [_one(kk) for kk in pairs]
    chunks = [pairs[i::workers] for i in range(workers)]
    procs = []
    for ch in chunks:
        if not ch:
            continue
        r, w = os.pipe()
        pid = os.fork()
        if pid == 0:                                  # child
            os.close(r)
            try:
                data = pickle.dumps([_one(kk) for kk in ch])
            except BaseException as e:                # noqa: BLE001 (re-raised in the parent)
                data = pickle.dumps(RuntimeError(f'worker failed: {e!r}'))
            view = memoryview(data)
            while len(view):
                view = view[os.write(w, view):]
            os.close(w)
            os._exit(0)
        os.close(w)
        procs.append((pid, r, ch))
    out = {}
    for pid, r, ch in procs:
        buf = []
        while True:
            b = os.read(r, 1 << 20)
            if not b:
                break
            buf.append(b)
        os.close(r)
        os.waitpid(pid, 0)
        res = pickle.loads(b''.join(buf))
        if isinstance(res, BaseException):
            raise res
        out.update(zip(ch, res))
    return [out[kk] for kk in pairs]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--run', required=True)
    ap.add_argument('--eps', default=','.join(str(e) for e in PUBLIC))
    ap.add_argument('--workers', type=int, default=3)
    a = ap.parse_args()
    if guard.mode() != 'clean':
        raise SystemExit('b4_identity runs in GMG_MODE=clean only')
    import numpy as np
    from gmg import track_sanity as TS
    run = guard.set_run(a.run)
    t0 = time.time()
    eps = [int(x) for x in a.eps.split(',')]
    metas, shells, good = {}, {}, []
    frac = guard.constant('sanity_fail_frac', 0.30, 'informed:PREREG A.6 track sanity (TRACK_FAIL < 30 % good)')
    fmin = guard.constant('sanity_fail_min_frames', 20, 'informed:PREREG A.6 track sanity (TRACK_FAIL < 20 good frames)')
    for ep in eps:
        bdir = os.path.join(run, 'bundle', 'public', f'ep{ep}')
        m = guard.load_json(os.path.join(bdir, 'episode.json'), 'own')
        metas[ep] = m
        n_all = len(range(0, int(m['T']), int(m['stride'])))
        for o in m['objects']:
            # DEVIATIONS 99: TRACK_FAIL over all extraction frames of the track ("its frames"); the frames-with-points
            # reading of b4_extract (DEVIATIONS 90) is kept alongside
            san = m['sanity'][o]
            old = 'TRACK_FAIL' in san['flags']
            new = san['n_good'] < frac * n_all or san['n_good'] < fmin
            san['track_fail_readings'] = dict(frames_with_points=bool(old), all_frames=bool(new),
                                              n_good=san['n_good'], n_frames_with_points=san['n_frames'],
                                              n_extraction_frames=n_all,
                                              good_frac_all_frames=round(san['n_good'] / max(n_all, 1), 4))
            san['flags'] = [f for f in san['flags'] if f != 'TRACK_FAIL'] + (['TRACK_FAIL'] if new else [])
        for o in m['objects']:
            p = guard.open_input(os.path.join(bdir, f'shell_{o}.npy'), 'own')
            shells[(ep, o)] = np.load(p).astype(np.float64)
            if 'TRACK_FAIL' not in m['sanity'][o]['flags']:
                good.append((ep, o))
    # every registration the cross tests need (round 2: TS.reg_chamfers, best of REG_SEEDS, full-shell chamfer, and
    # the round-1 seed-0 value), in forked worker processes (the ICP loop holds the GIL, so threads gave no speed-up;
    # each registration is independent and seeded, so the values are those of the serial loop; speed only)
    pairs = TS.cross_pairs(shells, good)
    vals = _pool_map(shells, pairs, a.workers)
    chamfers = dict(zip(pairs, vals))
    print(f'{len(pairs)} registrations, {round(time.time() - t0, 1)} s', flush=True)
    res = {}
    for key in sorted(shells):
        r = TS.cross_test(shells, key, good, chamfers=chamfers)
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
            sp = (san.get('identity_split') or {}).values()
            split_fail = any(v.get('testable') and not v.get('pass_') for v in sp)
            cross_fail = bool(r.get('testable') and not r.get('pass_'))
            if (split_fail or cross_fail) and 'IDENTITY_SWAP' not in san['flags']:
                san['flags'].append('IDENTITY_SWAP')
            # the round-1 (seed-0 registration) verdicts, reported beside; they set no flag
            s0_split = any(v.get('testable') and v.get('seed0') is not None and not v['seed0']['pass_'] for v in sp)
            s0_cross = bool(r.get('testable') and r.get('seed0') is not None and not r['seed0']['pass_'])
            san['identity_fail'] = dict(split=split_fail, cross=cross_fail, seed0_split=s0_split,
                                        seed0_cross=s0_cross)
        with open(os.path.join(run, 'bundle', 'public', f'ep{ep}', 'episode.json'), 'w') as f:
            json.dump(m, f)
    guard.write_manifest(os.path.join(run, 'manifests', 'identity.json'), extra=dict(step='B4', prereg='B.15'))


if __name__ == '__main__':
    main()
