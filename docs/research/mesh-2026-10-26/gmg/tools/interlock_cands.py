"""INTERLOCK BI2 helper (dev): CPU candidates (P-SHELL, P-HULL) of a bundle that has none yet, packed as run_episode
does (pack.pack: fit_budget 4000, own kit decode, V1). Uses build 1's producers unchanged.

  GMG_MODE=dev python -m gmg.tools.interlock_cands --run RUN --bundle BUNDLE_DIR --ep N [--objects a,b]
Writes RUN/cand/public/ep<N>/<obj>/<cid>.glb and <cid>.json (producer report + pack info)."""
from __future__ import annotations

import argparse
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
MR = os.path.dirname(os.path.dirname(HERE))
if MR not in sys.path:
    sys.path.insert(0, MR)
from gmg import guard  # noqa: E402
from gmg import interlock as IL, pack as PK  # noqa: E402
from gmg.producers import shell as P_SHELL, hull as P_HULL  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--run', required=True); ap.add_argument('--bundle', required=True); ap.add_argument('--ep', type=int)
    ap.add_argument('--objects', default='')
    a = ap.parse_args()
    guard.set_run(a.run)
    d = guard.load_json(os.path.join(guard.CFG['gmg'], 'dev_constants.json'), 'dev_frozen')
    t0 = guard.constant('t0_m', float(d['t0_dev_m']), d['t0_dev_origin'])
    b = IL.load_bundle_any(a.bundle)
    objs = a.objects.split(',') if a.objects else b.objects
    for o in objs:
        out = os.path.join(a.run, 'cand', 'public', f'ep{a.ep}', o)
        os.makedirs(out, exist_ok=True)
        for mod in (P_SHELL, P_HULL):
            for c in mod.produce(dict(bundle=b, obj=o, t0=t0)):
                m, info = PK.pack(c.mesh, os.path.join(out, f'{c.cid}.glb'))
                json.dump(dict(meta=c.meta(), pack={k: v for k, v in info.items() if k != 'v1'} | dict(v1=info['v1'])),
                          open(os.path.join(out, f'{c.cid}.json'), 'w'), default=str)
                print(o, c.cid, info['faces'], info['watertight_packed'], flush=True)
    guard.write_manifest(os.path.join(a.run, f'manifest_cands_ep{a.ep}.json'))


if __name__ == '__main__':
    main()
