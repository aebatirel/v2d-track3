"""One episode through the gmg (module M16 of SPEC section 7; SKELETON for build step B1).

  python -m gmg.run_episode --split public --ep N --mode dev --producers cpu --variant deploy --out RUN
                            [--objects a,b]
(run with docs/research/mesh-2026-10-26 on sys.path or as the cwd; GMG_MODE must equal --mode: the guard reads it at
import.)

Stages (SPEC section 5), B1 form:
  1. guard.set_run(RUN); t0 (dev: gmg/dev_constants.json, role dev_frozen; clean: gmg/frozen_constants.json,
     role frozen, written at B13).
  2. bundle: dev = bundle.from_obs_all (tier DEV); clean = extract_joint (B4, not yet built). Saved to
     RUN/bundle/<split>/ep<N>/ and read back through load_bundle.
  3. per target object: CPU producers SHELL and HULL (B1 minimal) -> RUN/cand/<split>/ep<N>/<obj>/<cid>.glb + .json,
     packed (fit_budget 4000, own kit decode, V1).
  4. features (score.py, all-frames form): E with the moving-block bootstrap, fsv_far, V2, V3 (not applied: tau is
     fitted at B13), V4 -> RUN/feat/<split>/ep<N>/<obj>.jsonl.
  5. SKELETON pick (select.py is B5): vetoes V1, V2, V4; tie set E(c) - E(best) <= b_tie x SE_diff(c); class order
     STRUCT > FUSE > GEN > SHELL > HULL, then lower E (V5, markers and the parameter prior are not in B1) ->
     RUN/pick/<split>/ep<N>/<obj>.json. No feasible candidate: ABSTAIN_HULL (SPEC section 13) if coverage is not low.
  6. output RUN/out/<split>/ep<N>/<obj>.glb (packed pick), <obj>.report.json (GT-free), manifest.json (guard).
     No simulator copy in B1 (B9). Nothing is scored against scans.
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
MR = os.path.dirname(HERE)
if MR not in sys.path:
    sys.path.insert(0, MR)

from gmg import guard  # noqa: E402  (installs the audit hook first)
import numpy as np  # noqa: E402

from gmg import bundle as B, pack as PK, score as SC  # noqa: E402
from gmg.producers import CLASSES, shell as P_SHELL, hull as P_HULL  # noqa: E402

PRODUCERS = dict(cpu=(P_SHELL, P_HULL))
VARIANT_V0 = dict(K=3, b_tie=1, prior=True)


def _t0():
    if guard.mode() == 'dev':
        d = guard.load_json(os.path.join(guard.CFG['gmg'], 'dev_constants.json'), 'dev_frozen')
        return guard.constant('t0_m', float(d['t0_dev_m']), d['t0_dev_origin']), dict(source='dev_constants.json',
                                                                                       run=d.get('source_run'))
    d = guard.load_json(os.path.join(guard.CFG['gmg'], 'frozen_constants.json'), 'frozen')
    return guard.constant('t0_m', float(d['t0_mm']) * 1e-3, 'fitted:own t0 (PREREG A.1, public clean batch)'), \
        dict(source='frozen_constants.json')


def _variant(name):
    if name != 'deploy':
        raise SystemExit(f'variant {name!r}: B1 knows only deploy')
    p = os.path.join(guard.CFG['gmg'], 'deploy_variant.json')
    if guard.mode() == 'clean' and os.path.exists(p):
        return guard.load_json(p, 'frozen'), ['deploy_variant.json']
    return dict(VARIANT_V0), ['deploy_variant_absent_V0']


def _jsonable(o):
    if isinstance(o, dict):
        return {str(k): _jsonable(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [_jsonable(v) for v in o]
    if isinstance(o, (np.floating,)):
        return float(o)
    if isinstance(o, (np.integer,)):
        return int(o)
    if isinstance(o, np.bool_):
        return bool(o)
    if isinstance(o, np.ndarray):
        return o.tolist()
    return o


def _pick(rows, variant):
    """B1 skeleton of S1 (PREREG A.5) without V3 (tau unfitted), V5, markers and the parameter prior."""
    trace = []
    feas = [r for r in rows if not r['vetoes']]
    trace.append(dict(step='vetoes', removed={r['cid']: r['vetoes'] for r in rows if r['vetoes']},
                      not_applied=['V3 (tau fitted at B13)', 'V5 (B5/B7)']))
    if not feas:
        return None, trace
    best = min(feas, key=lambda r: r['E'])
    tie = [r for r in feas if r['E'] - best['E'] <= variant['b_tie'] * r['se_diff']]
    trace.append(dict(step='tie band', best=best['cid'], b_tie=variant['b_tie'],
                      tie_set=[(r['cid'], round(r['E'] - best['E'], 5), round(r['se_diff'], 5)) for r in tie]))
    order = sorted(tie, key=lambda r: (CLASSES.index(r['cls']), r['E']))
    trace.append(dict(step='priors', order=[r['cid'] for r in order],
                      keys='class (STRUCT > FUSE > GEN > SHELL > HULL), then lower E; flip safety, markers and the '
                           'parameter prior are not in B1'))
    return order[0], trace


def run_object(b, obj, run, t0, variant, producers, log):
    split, ep = b.meta['split'], b.meta['ep']
    cdir = os.path.join(run, 'cand', split, f'ep{ep}', obj)
    t = time.time()
    ctx = dict(bundle=b, obj=obj, t0=t0)
    cands = []
    for mod in producers:
        try:
            cands += mod.produce(ctx)
        except Exception as e:                                                   # noqa: BLE001
            log(f'  {obj}: producer {mod.__name__} failed: {type(e).__name__}: {e}')
            if isinstance(e, guard.GuardError):
                raise
    log(f'  {obj}: {len(cands)} candidates in {time.time() - t:.0f} s')
    shell = next((c for c in cands if c.cls == 'SHELL'), None)
    obs = b.obs(obj)
    far = SC.far_free_grid(obs)
    blocks = SC.heldout(b, obj)
    reps = SC.bootstrap_reps(blocks)
    s = b.sigma(obj)
    rows, packed = [], {}
    fsv_s = None
    for c in cands:
        t = time.time()
        glb = os.path.join(cdir, f'{c.cid}.glb')
        m, pinfo = PK.pack(c.mesh, glb)
        packed[c.cid] = (m, glb)
        fs = SC.fsv_far(m, obs, far)
        if c is shell:
            fsv_s = fs['fsv_far']
        ev = SC.evidence(m, b, obj, blocks, fs['fsv_far'] or 0.0)
        er = SC.e_reps(ev, fs['fsv_far'] or 0.0, s, reps)
        v2 = SC.v2(m, b, obj)
        v4 = SC.below_table(m, b, obj)
        row = dict(cid=c.cid, cls=c.cls, producer=c.producer, n_params=c.n_params, E=ev['E'],
                   E_blocks=ev['R_blocks'], ray=ev['ray'], fsv_far=fs['fsv_far'], fsv_outside_grid=fs['outside_grid'],
                   v1=pinfo['v1'], v2=v2, v4=v4, pack=dict((k, pinfo.get(k)) for k in (
                       'faces', 'vertices', 'watertight_packed', 'sha256', 'solid_faces_in', 'solid_area_change')),
                   _reps=er, flags=list(c.flags))
        rows.append(row)
        with open(os.path.join(cdir, f'{c.cid}.json'), 'w') as f:
            json.dump(_jsonable(dict(c.meta(), sha256=pinfo['sha256'], faces=pinfo['faces'],
                                     watertight_after_decode=pinfo['v1']['watertight'])), f, indent=1)
        log(f'  {obj}/{c.cid}: faces {pinfo["faces"]} wt-decode {pinfo["v1"]["watertight"]} E {ev["E"]:.4f} '
            f'fsv {fs["fsv_far"]:.4f} V2 {v2["veto"]} V4 {v4["veto"]} ({time.time() - t:.0f} s)')
    for r in rows:
        r['v3'] = SC.v3(r['fsv_far'], fsv_s, None)
        r['vetoes'] = [v for v, hit in (('V1', r['v1']['veto']), ('V2', r['v2']['veto']), ('V3', r['v3']['veto']),
                                        ('V4', r['v4']['veto'])) if hit]
    feas = [r for r in rows if not r['vetoes']]
    best = min(feas, key=lambda r: r['E']) if feas else None
    for r in rows:
        r['E_se'] = float(np.std(r['_reps']))
        r['se_diff'] = float(np.std(r['_reps'] - best['_reps'])) if best is not None else None
    pick, trace = _pick(rows, variant)
    flags = ['dev_tier', 'skeleton_select_B1'] + ([] if feas else ['no_feasible'])
    fallback = None
    n_own = int((np.asarray(obs['own']) == 0).sum())
    good = b.good_frames(obj)
    low_cov = len(good) < 20 or n_own < 20000
    if low_cov:
        flags.append('low_coverage')
    if pick is None:
        hull = next((r for r in rows if r['cls'] == 'HULL'), None)
        if hull is not None and not low_cov and hull['v1']['watertight']:
            pick, fallback = hull, 'ABSTAIN_HULL'
            flags.append('fallback')
        trace.append(dict(step='fallback', ladder='ABSTAIN_HULL / PRIOR_GEN / PRIOR_PUBLIC (SPEC 13); B1 has '
                          'ABSTAIN_HULL only', result=fallback))
    fdir = os.path.join(run, 'feat', split, f'ep{ep}')
    os.makedirs(fdir, exist_ok=True)
    with open(os.path.join(fdir, f'{obj}.jsonl'), 'w') as f:
        for r in rows:
            f.write(json.dumps(_jsonable({k: v for k, v in r.items() if not k.startswith('_')})) + '\n')
    pdir = os.path.join(run, 'pick', split, f'ep{ep}')
    os.makedirs(pdir, exist_ok=True)
    pk = dict(cid=pick['cid'] if pick else None, variant=variant, tie_set=next(
        (t['tie_set'] for t in trace if t['step'] == 'tie band'), []), trace=trace, fallback=fallback, flags=flags)
    with open(os.path.join(pdir, f'{obj}.json'), 'w') as f:
        json.dump(_jsonable(pk), f, indent=1)
    odir = os.path.join(run, 'out', split, f'ep{ep}')
    os.makedirs(odir, exist_ok=True)
    out_glb = None
    if pick is not None:
        out_glb = os.path.join(odir, f'{obj}.glb')
        shutil.copyfile(packed[pick['cid']][1], out_glb)
    report = dict(schema='gmg-report/1-skeleton', split=split, ep=ep, obj=obj, tier=b.meta['tier'],
                  gt_free=True, scored_against_scans=False, pick=pk, out=out_glb,
                  out_sha256=guard._sha256(os.path.realpath(out_glb)) if out_glb else None,
                  out_v1=SC.v1(out_glb) if out_glb else None,
                  candidates=[{k: v for k, v in r.items() if not k.startswith('_')} for r in rows],
                  bundle=dict(path=b.path, sigma_mm=b.meta['sigma_mm'][obj], good_frames=len(good), owned_points=n_own,
                              contact={p: {k: b.contact(obj, p).get(k) for k in ('j_mm', 'band_mm')} | dict(
                                  contact=len(b.contact(obj, p)['contact']),
                                  separated=len(b.contact(obj, p)['separated']),
                                  sep3d=len(b.contact(obj, p)['sep3d'])) for p in b.partners(obj)},
                              rest=b.meta.get('rest', {}).get(obj), table=b.meta.get('table'),
                              flags=b.meta.get('flags')),
                  t0_mm=round(t0 * 1e3, 4), flags=flags,
                  not_in_b1=['simulator copy (B9)', 'STRUCT producers (B8, B11)', 'markers (B7)', 'V3 tau (B13)',
                             'V5 and select.py (B5)', 'fold rebuilds (B5)', 'track sanity and identity (B4)'])
    with open(os.path.join(odir, f'{obj}.report.json'), 'w') as f:
        json.dump(_jsonable(report), f, indent=1)
    log(f'  {obj}: pick {pk["cid"]} fallback {fallback} -> {out_glb}')
    return report


def main(argv=None):
    ap = argparse.ArgumentParser(prog='gmg.run_episode')
    ap.add_argument('--split', required=True, choices=B.SPLITS)
    ap.add_argument('--ep', required=True, type=int)
    ap.add_argument('--mode', required=True, choices=guard.MODES)
    ap.add_argument('--producers', default='cpu', choices=('cpu', 'all'))
    ap.add_argument('--variant', default='deploy')
    ap.add_argument('--out', required=True, help='run folder RUN (DATA/gmg/runs[-dev]/<yyyymmdd>-<tag>-<commit7>)')
    ap.add_argument('--objects', default=None, help='comma-separated target objects (default: every tracked one)')
    a = ap.parse_args(argv)
    if a.mode != guard.mode():
        raise SystemExit(f'--mode {a.mode} but GMG_MODE={guard.mode()} (the guard reads GMG_MODE at import)')
    if a.producers == 'all':
        raise SystemExit('--producers all: GPU producers come with B15; B1 runs cpu only')
    t_start = time.time()
    run = guard.set_run(a.out)

    def log(msg):
        print(f'[{time.time() - t_start:7.1f}s] {msg}', flush=True)

    t0, t0_src = _t0()
    variant, vflags = _variant(a.variant)
    log(f'run {run} mode {guard.mode()} split {a.split} ep {a.ep} t0 {t0 * 1e3:.3f} mm ({t0_src})')
    if guard.mode() == 'dev':
        b = B.from_obs_all(a.ep, split=a.split)
    else:
        raise SystemExit('clean bundles need gmg/extract_joint.py (build step B4)')
    bdir = B.save_bundle(b, B.bundle_dir(run, a.split, a.ep))
    b = B.load_bundle(bdir)
    log(f'bundle {bdir}: objects {b.objects}, sigma {b.meta["sigma_mm"]}')
    targets = a.objects.split(',') if a.objects else b.objects
    bad = [o for o in targets if o not in b.objects]
    if bad:
        raise SystemExit(f'objects {bad} are not tracked in ep{a.ep} ({b.objects})')
    reports = {o: run_object(b, o, run, t0, variant, PRODUCERS[a.producers], log) for o in targets}
    odir = os.path.join(run, 'out', a.split, f'ep{a.ep}')
    summary = {o: dict(pick=r['pick']['cid'], fallback=r['pick']['fallback'], out=r['out'],
                       watertight_after_decode=(r['out_v1'] or {}).get('watertight'),
                       faces=(r['out_v1'] or {}).get('faces')) for o, r in reports.items()}
    man = guard.write_manifest(os.path.join(odir, 'manifest.json'),
                               extra=dict(step='B1 skeleton', split=a.split, ep=a.ep, targets=targets,
                                          variant=variant, variant_flags=vflags, t0=t0_src, summary=summary,
                                          sec=round(time.time() - t_start, 1)))
    log(f'manifest {os.path.join(odir, "manifest.json")}: tier {man["tier"]}, {len(man["inputs"])} inputs, '
        f'{len(man["outputs"])} outputs, commit {man["commit"][:7]} dirty {man["code_dirty"]}')
    print(json.dumps(summary))
    return summary


if __name__ == '__main__':
    main()
