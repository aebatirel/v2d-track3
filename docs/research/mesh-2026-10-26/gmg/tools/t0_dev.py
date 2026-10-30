"""t0_dev: the PREREG A.1 thickness statistic on the dev observations (obs_all), for dev runs only (build step B1).

PREREG A.1: "Dev runs use t0_dev, the same statistic on obs_all; it is never used in a clean run." This tool runs in
GMG_MODE=dev, reads every obs_all file of the public roster (role obs_all; keys pts, cam, frame), measures the
two-sided thicknesses (gmg/thickness.py), aggregates them by A.1 and writes
  RUN/t0_dev.json + RUN/manifest.json     (the dev run folder, tier DEV)
  gmg/dev_constants.json                  (the committed copy that dev runs read under the dev-only role
                                           dev_frozen; never readable in clean mode)
Usage: GMG_MODE=dev python gmg/tools/t0_dev.py --run <DATA>/gmg/runs-dev/<yyyymmdd>-t0dev-<commit7>
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
from gmg import guard, thickness as TH  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--run', required=True)
    ap.add_argument('--publish', default=os.path.join(guard.CFG['gmg'], 'dev_constants.json'))
    a = ap.parse_args()
    if guard.mode() != 'dev':
        raise SystemExit('t0_dev runs in GMG_MODE=dev only')
    run = guard.set_run(a.run)
    D = guard.CFG['data']
    roster = guard.load_json(os.path.join(guard.CFG['gmg'], 'roster_public.json'), 'roster')
    rows = []
    for ep, objs in sorted(roster['episodes'].items(), key=lambda kv: int(kv[0])):
        for o in objs:
            p = os.path.join(D, 'obs_all', f'ep{ep}_{o}.npz')
            if not os.path.exists(p):
                continue
            t = time.time()
            z = guard.load_npz(p, 'obs_all', keys=['pts', 'cam', 'frame'])
            T, info = TH.two_sided_measurements(z)
            import numpy as np
            r = dict(obj=o, ep=int(ep), n=int(len(T)), median_m=float(np.median(T)) if len(T) else None,
                     info=info, sec=round(time.time() - t, 1))
            rows.append(r)
            print(json.dumps(r), flush=True)
    res = TH.aggregate(rows)
    res.update(per_episode=rows, statistic='t0_dev (PREREG A.1 on obs_all; dev only)', run=os.path.basename(run))
    guard.constant('t0_dev_m', res['t0_m'], 'fitted:own t0_dev, PREREG A.1 statistic on the dev observations'
                   if res['fittable'] else 'fallback:scan-coincident (brief leak), PREREG A.1 not fittable')
    with open(os.path.join(run, 't0_dev.json'), 'w') as f:
        json.dump(res, f, indent=1)
    man = guard.write_manifest(os.path.join(run, 'manifest.json'))
    pub = dict(schema='gmg-dev-constants/1', note='DEV ONLY (tier DEV): read by dev runs under the dev-only guard '
               'role dev_frozen; never readable in clean mode (PREREG A.1: t0_dev is never used in a clean run)',
               t0_dev_m=res['t0_m'], t0_dev_origin=('fitted:own t0_dev (PREREG A.1 statistic on obs_all)'
                                                    if res['fittable'] else res['origin']),
               fittable=res['fittable'], t0_raw_m=res['t0_raw_m'], objects=res['objects'],
               source_run=os.path.basename(run), commit=man['commit'], code_dirty=man['code_dirty'],
               inputs=[dict(path=r['realpath'], sha256=r['sha256']) for r in man['inputs']])
    with open(a.publish, 'w') as f:
        json.dump(pub, f, indent=1)
    print(json.dumps(dict(t0_m=res['t0_m'], fittable=res['fittable'], raw=res['t0_raw_m'],
                          objects={k: (v['n'], round(v['median_m'] * 1e3, 3)) for k, v in res['objects'].items()})))


if __name__ == '__main__':
    main()
