"""b4_b2a: PREREG B.2a (ownership leakage, prediction P2) on the clean B4 bundles. GMG_MODE=clean, same run (role own).

Pairs (PREREG B.2): pot/lid ep2; cups ep11; boards ep24; pot/rack ep26, ep27; cup/rack ep12, ep13; sweeper/rack ep31;
sweeper/dust pan ep18; boards ep23 only if both boards pass the identity tests. For target o and partner p (both
directions): o's route-A sheet (autokit.shell.shell_sheet) from o's owned points of its 3-D-separated frames (final
census, gap > 20 mm; frames holding o's owned points). Testable if there are >= 10 such frames (A.6). Leakage = the
share of o's owned samples from contact frames (final census) that lie more than 3 sigma_o from that sheet and within
4 mm of p's owned samples of the same frame (moved into o's frame by T_{o<-p}[f]).
Pass: leakage <= 1 % on every testable direction (and B.2b at B13). Fail: > 1 % on 2 or more testable pairs (a pair
fails if either direction fails). Inconclusive: fewer than 4 pairs have a testable direction.
Usage: GMG_MODE=clean python gmg/tools/b4_b2a.py --run <DATA>/gmg/runs/<clean run>
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

PAIRS = [(2, 'white_pot', 'white_pot_lid'), (11, 'blue_cup', 'beige_cup'), (24, 'wooden_piece_1', 'wooden_piece_2'),
         (26, 'plastic_dish_rack', 'white_pot'), (27, 'plastic_dish_rack', 'white_pot'),
         (12, 'blue_cup', 'plastic_dish_rack'), (13, 'blue_cup', 'plastic_dish_rack'),
         (31, 'mini_sweeper', 'plastic_dish_rack'), (18, 'mini_sweeper', 'mini_dust_pan'),
         (23, 'wooden_piece_1', 'wooden_piece_2')]
SHEET_CAP = 600000   # owned points fed to the reference sheet (random, seed 0; numerical)


def direction(b, o, p, c):
    import numpy as np
    from autokit import shell as SH
    from gmg import geom, contact as CT
    obs = b.obs(o)
    fr = np.asarray(obs['frame'])
    own = np.asarray(obs['own'])
    P = np.asarray(obs['pts'], np.float64)
    rec = b.contact(o, p)
    have = set(np.unique(fr[own == 0]).tolist())
    sep = [f for f in rec['sep3d'] if f in have]
    out = dict(target=o, partner=p, sep3d_frames=len(sep), contact_frames=len(rec['contact']))
    if len(sep) < c['min_frames']:
        out.update(testable=False)
        return out
    idx = np.nonzero(np.isin(fr, sep) & (own == 0))[0]
    rng = np.random.default_rng(0)
    if len(idx) > SHEET_CAP:
        idx = np.sort(rng.choice(idx, SHEET_CAP, replace=False))
    sh = SH.shell_sheet({k: np.asarray(obs[k])[idx] for k in ('pts', 'cam', 'frame')})
    sheet = sh['sheet']
    out.update(testable=True, sheet_points=int(len(idx)), sheet_faces=int(len(sheet.faces)))
    if len(sheet.faces) == 0:
        out.update(leakage=None, note='empty sheet')
        return out
    cl = geom.Closest(sheet)
    sig = b.sigma(o)
    po = b.obs(p)
    pfr, pown, PP = np.asarray(po['frame']), np.asarray(po['own']), np.asarray(po['pts'], np.float64)
    n_tot = n_leak = n_far = 0
    per = []
    for f in rec['contact']:
        mo = (fr == f) & (own == 0)
        if not mo.any():
            continue
        X = P[mo]
        d = cl.query(X)[0]
        far = d > c['k_sigma'] * sig
        mp = (pfr == f) & (pown == 0)
        leak = np.zeros(len(X), bool)
        if far.any() and mp.any():
            Q = CT.moved(PP[mp], CT.rel(b.poses, o, p, f))
            from scipy.spatial import cKDTree
            dn = cKDTree(Q).query(X[far], k=1)[0]
            leak[np.nonzero(far)[0][dn <= c['near']]] = True
        n_tot += len(X)
        n_far += int(far.sum())
        n_leak += int(leak.sum())
        per.append((int(f), int(len(X)), int(leak.sum())))
    out.update(owned_in_contact=n_tot, far_from_sheet=n_far, leaked=n_leak,
               leakage=round(n_leak / n_tot, 5) if n_tot else None, sigma_mm=round(sig * 1e3, 3),
               worst_frames=sorted(per, key=lambda x: -x[2])[:5])
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--run', required=True)
    a = ap.parse_args()
    if guard.mode() != 'clean':
        raise SystemExit('b4_b2a runs in GMG_MODE=clean only')
    from gmg import bundle as BU
    run = guard.set_run(a.run)
    c = dict(min_frames=guard.constant('b2_reference_min_frames', 10, 'generic:PREREG A.6 B.2 reference minimum'),
             k_sigma=guard.constant('b2_far_sigma_k', 3.0, 'generic:PREREG B.2a more than 3 sigma from the sheet'),
             near=guard.constant('b2_near_partner_m', 0.004, 'generic:PREREG B.2a within 4 mm of the partner'),
             thr=guard.constant('b2_leak_max', 0.01, 'generic:PREREG B.2a leakage <= 1 %'))
    t0 = time.time()
    ident = guard.load_json(os.path.join(run, 'identity', 'cross.json'), 'own')
    res = []
    for ep, o, p in PAIRS:
        b = BU.load_bundle(os.path.join(run, 'bundle', 'public', f'ep{ep}'))
        if ep == 23:
            fl = [f for q in (o, p) for f in b.meta['sanity'][q]['flags']]
            if 'IDENTITY_SWAP' in fl or not all(ident['results'][f'ep23:{q}'].get('testable') for q in (o, p)):
                res.append(dict(ep=ep, pair=f'{o}|{p}', included=False,
                                reason='ep23 only if both boards pass the identity tests', flags=fl))
                print(res[-1], flush=True)
                continue
        dirs = [direction(b, o, p, c), direction(b, p, o, c)]
        testable = [d for d in dirs if d.get('testable') and d.get('leakage') is not None]
        fail = any(d['leakage'] > c['thr'] for d in testable)
        res.append(dict(ep=ep, pair=f'{o}|{p}', included=True, directions=dirs, testable=len(testable) > 0,
                        pair_fail=bool(fail)))
        print(json.dumps({k: v for k, v in res[-1].items() if k != 'directions'}),
              [(d['target'], d.get('sep3d_frames'), d.get('leakage')) for d in dirs], flush=True)
    inc = [r for r in res if r['included']]
    n_test = sum(r['testable'] for r in inc)
    n_fail = sum(r['pair_fail'] for r in inc)
    all_ok = all(d['leakage'] <= c['thr'] for r in inc for d in r['directions']
                 if d.get('testable') and d.get('leakage') is not None)
    verdict = ('INCONCLUSIVE (fewer than 4 testable pairs)' if n_test < 4 else
               'FAIL' if n_fail >= 2 else 'PASS (B.2a part; B.2b at B13)' if all_ok else
               'INCONCLUSIVE (1 testable pair over 1 %)')
    summ = dict(prereg='B.2a', pairs=res, testable_pairs=n_test, failing_pairs=n_fail, verdict=verdict,
                sec=round(time.time() - t0, 1))
    os.makedirs(os.path.join(run, 'validate'), exist_ok=True)
    with open(os.path.join(run, 'validate', 'b2a.json'), 'w') as f:
        json.dump(summ, f, indent=1)
    print('B.2a', verdict, 'testable pairs', n_test, 'failing', n_fail, flush=True)
    guard.write_manifest(os.path.join(run, 'manifests', 'b2a.json'), extra=dict(step='B4', prereg='B.2a'))


if __name__ == '__main__':
    main()
