"""B5 dev check (GT-free, tier DEV, nothing scored): score.py full and select.py on the B1 pools of one dev episode.

  GMG_MODE=dev python gmg/build/b5/dev_pool.py --ep N --out <scratchpad>/gmg/runs-dev/<yyyymmdd>-b5pool<N>-<commit7>
  (cwd docs/research/mesh-2026-10-26; run under gmg/tools/strace_audit.py run)

Per object: the B1 producers (SHELL at t0_dev, HULL), packed as run_episode packs them; the SHELL rebuilt on the K = 3
fold training frames (score.build_folds, then packed), the HULL scored 'fixed' (no fold build yet, DEVIATIONS 56);
score.score_pool with the folds (kit symmetry, untrusted balls: no markers before B7, tau None before B13,
obs_flip_margin on) and, for comparison, the all-frames form; select.pick (V0). Writes RUN/b5pool/ep<N>/<obj>.json
and RUN/manifest.json. Reads only what run_episode reads in dev mode (obs_all, tracks, calib, det keys depth/K,
roster, dev_constants, the kit config for the symmetry).
"""
import argparse
import json
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
GMG = os.path.dirname(os.path.dirname(HERE))
MR = os.path.dirname(GMG)
if MR not in sys.path:
    sys.path.insert(0, MR)
from gmg import guard  # noqa: E402
import numpy as np  # noqa: E402

from gmg import bundle as B, pack as PK, score as SC, select as SEL  # noqa: E402
from gmg.producers import hull as P_HULL, shell as P_SHELL  # noqa: E402
from gmg.run_episode import _jsonable, _t0  # noqa: E402


def summary(r):
    keys = ('cid', 'cls', 'E', 'E_blocks', 'E_se', 'fold', 'fsv_far', 'fsv_far_shell', 'ray', 'ray_blocks', 'v3',
            'trusted_markers', 'flags')
    out = {k: r.get(k) for k in keys}
    out['v1'] = {k: r['v1'].get(k) for k in ('veto', 'watertight', 'faces')}
    out['v2'] = dict(veto=r['v2']['veto'], partners={p: {k: d.get(k) for k in ('veto', 'n_median', 'threshold')}
                                                     for p, d in r['v2']['partners'].items()})
    out['v4'] = {k: r['v4'].get(k) for k in ('applies', 'veto', 'share')}
    for a in ('amb', 'amb_noball'):
        if r.get(a):
            out[a] = {k: r[a].get(k) for k in ('amb_mm', 'amb_floor_mm', 'flip_risk', 'flip_units', 'kind')}
    if r.get('obs_flip_margin'):
        out['obs_flip_margin'] = r['obs_flip_margin']
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--ep', type=int, required=True)
    ap.add_argument('--out', required=True)
    a = ap.parse_args()
    if guard.mode() != 'dev':
        raise SystemExit('dev only')
    t_start = time.time()

    def log(msg):
        print(f'[{time.time() - t_start:7.1f}s] {msg}', flush=True)
    run = guard.set_run(a.out)
    t0, t0_src = _t0()
    b = B.from_obs_all(a.ep)
    b = B.load_bundle(B.save_bundle(b, B.bundle_dir(run, 'public', a.ep)))
    log(f'bundle ep{a.ep}: {b.objects}, sigma {b.meta["sigma_mm"]}, t0 {t0 * 1e3:.3f} mm')
    res = {}
    for obj in b.objects:
        ctx = dict(bundle=b, obj=obj, t0=t0)
        cdir = os.path.join(run, 'cand', 'public', f'ep{a.ep}', obj)
        t = time.time()
        cands = P_SHELL.produce(ctx) + P_HULL.produce(ctx)
        packed = []
        for c in cands:
            m, pinfo = PK.pack(c.mesh, os.path.join(cdir, f'{c.cid}.glb'))
            packed.append(dict(cid=c.cid, cls=c.cls, producer=c.producer, n_params=c.n_params, mesh=m, v1=pinfo['v1'],
                               flags=list(c.flags)))
        log(f'{obj}: {len(cands)} candidates built and packed ({time.time() - t:.0f} s)')
        pl = SC.plan(b, obj, 3)
        folds, fstat = {}, {}
        for prod in (P_SHELL, P_HULL):
            t = time.time()
            raw, st = SC.build_folds(prod, ctx, pl)
            for cid, ms in raw.items():
                folds[cid] = []
                for k, mk in enumerate(ms):
                    if mk is None:
                        folds[cid].append(None); continue
                    pm, _ = PK.pack(mk, os.path.join(cdir, 'folds', f'{cid}_k{k + 1}.glb'))
                    folds[cid].append(pm)
            st['sec'] = round(time.time() - t, 1)
            fstat[prod.__name__] = st
            log(f'{obj}: folds of {prod.__name__}: {st["state"]} ({st["sec"]} s)')
        t = time.time()
        pool = SC.score_pool(packed, b, obj, K=3, folds=folds, tau=None, kind='kit', trusted=False, flip_margin=True)
        flat = SC.score_pool(packed, b, obj, K=3, folds=None, tau=None, kind='kit', trusted=False, amb=False)
        log(f'{obj}: scored ({time.time() - t:.0f} s)')
        obs = b.obs(obj)
        far = SC.far_free_grid(obs)
        fold_fsv = {cid: [SC.fsv_far(m, obs, far)['fsv_far'] if m is not None else None for m in ms]
                    for cid, ms in folds.items()}
        n_own = int((np.asarray(obs['own']) == 0).sum())
        status = dict(low_coverage=len(b.good_frames(obj)) < 20 or n_own < 20000)
        p = SEL.pick(pool['rows'], kit_symmetric=pool['kit_symmetric'], gen_view_overlap=pool['gen_view_overlap'],
                     status=status)
        pf = SEL.pick(flat['rows'], kit_symmetric=flat['kit_symmetric'], gen_view_overlap=flat['gen_view_overlap'],
                      status=status)
        res[obj] = dict(kind=pool['kind'], blocks=pool['blocks'], fold_status=fstat, fold_fsv_far=fold_fsv,
                        rows=[summary(r) for r in pool['rows']], rows_all_frames=[summary(r) for r in flat['rows']],
                        pick={k: p[k] for k in ('cid', 'best', 'tie_set', 'order', 'flags', 'fallback', 'trace')},
                        pick_all_frames={k: pf[k] for k in ('cid', 'best', 'tie_set', 'order', 'flags', 'fallback')})
        for r in pool['rows']:
            log(f'  {obj}/{r["cid"]}: E {r["E"]:.4f} blocks {r["E_blocks"]} fold {r["fold"]} fsv {r["fsv_far"]:.4f} '
                f'amb {r["amb"]["amb_mm"]} floor {r["amb"]["amb_floor_mm"]:.3f} risk {r["amb"]["flip_risk"]} '
                f'margin {r["obs_flip_margin"].get("margin_mm")}')
        log(f'{obj}: pick {p["cid"]} (tie set {p["tie_set"]}, flags {p["flags"]}); all-frames pick {pf["cid"]}')
        odir = os.path.join(run, 'b5pool', f'ep{a.ep}')
        os.makedirs(odir, exist_ok=True)
        with open(os.path.join(odir, f'{obj}.json'), 'w') as f:
            json.dump(_jsonable(res[obj]), f, indent=1)
    man = guard.write_manifest(os.path.join(run, 'manifest.json'), extra=dict(
        step='B5 dev check (score full + select)', ep=a.ep, t0=t0_src, sec=round(time.time() - t_start, 1),
        picks={o: r['pick']['cid'] for o, r in res.items()}))
    log(f'manifest: tier {man["tier"]}, {len(man["inputs"])} inputs, commit {man["commit"][:7]} dirty '
        f'{man["code_dirty"]}')


if __name__ == '__main__':
    main()
