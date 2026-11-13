"""INTERLOCK contract test, gmg side (round-1 fix B1/B2): validate the Embodiment tool's real exports (made by
contract_ext.py on our delivered round 0) and run carve_from_intrusions on them; compare the decisions with our
tracks path (the dev driver's decisions.json of the same round).

  GMG_MODE=dev GMG_RUN=<run> python contract_gmg.py --bundle BUNDLE --sim R0 --exports e0.npz [e0fit.npz]
      --tracks-decisions <run>/interlock/public/ep24-<tag>/decisions.json --out OUT.json --identity eval
"""
import argparse
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
MR = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
if MR not in sys.path:
    sys.path.insert(0, MR)
from gmg import guard  # noqa: E402
from gmg import interlock as IL  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--bundle', required=True); ap.add_argument('--sim', required=True)
    ap.add_argument('--exports', nargs='+', required=True); ap.add_argument('--tracks-decisions', required=True)
    ap.add_argument('--out', required=True); ap.add_argument('--identity', default='eval')
    ap.add_argument('--run', required=True)
    ap.add_argument('--allow-do-not-use', action='store_true',
                    help='DIAGNOSTIC: validate / carve on a round marked do-not-use (flagged in every output)')
    a = ap.parse_args()
    guard.set_run(a.run)
    b = IL.load_bundle_any(a.bundle)
    tracks = dict(path=b.meta['tracks']['path'], sha256=b.meta['tracks']['sha256'], poses=b.poses)
    out = dict(bundle=a.bundle, sim=a.sim, identity=a.identity, exports={},
               do_not_use_overridden=bool(a.allow_do_not_use))
    pair = tuple(b.objects)
    for e in a.exports:
        ok, rep = IL.validate(e, a.sim, tracks=tracks, allow_do_not_use=a.allow_do_not_use)
        hdr = json.load(open(e[:-4] + '.json'))
        rec = dict(valid=ok, refused=rep.get('refused'), flags=rep.get('flags'), reference_pose=rep.get('reference_pose'),
                   containment=rep.get('containment'), pushed_residual=rep.get('pushed_residual'),
                   fit_refused=rep.get('fit_refused'), their_flags=hdr.get('flags'), their_checks=hdr.get('checks'),
                   counts=hdr.get('counts'), seconds=hdr.get('seconds'), tool_commit=hdr.get('commit'))
        if ok:
            tag = os.path.basename(e)[:-4]
            res = IL.carve_from_intrusions(pair, e, b, a.sim, os.path.join(os.path.dirname(a.sim), f'r1-{tag}'), 1,
                                           physics_fn=None, identity=a.identity, ref_poses=None,
                                           allow_do_not_use=a.allow_do_not_use)
            rec['decisions'] = [dict(target=d['target'], decision=d['decision'], tier=d['tier'], voxels=d['voxels'],
                                     region_voxels=d.get('region_voxels'), mix=d.get('class_mix'),
                                     iw=d.get('image_width_px'), push_mm=d.get('push_mm'),
                                     pushed_residual_used=d.get('pushed_residual_used'), flags=d['flags'],
                                     sources={k: (v or {}).get('agree') if isinstance(v, dict) else v
                                              for k, v in (d.get('sources') or {}).items()},
                                     w_sim=(d.get('widths') or {}).get('w_sim_mm'),
                                     run=(d.get('run') or {}).get('frames'))
                                for d in res['decisions'] if d['voxels'] >= 3]
            rec['r1'] = res['pieces_dir']
        out['exports'][os.path.basename(e)] = rec
        print(os.path.basename(e), json.dumps({k: v for k, v in rec.items() if k in ('valid', 'refused', 'flags',
                                                                                      'reference_pose',
                                                                                      'pushed_residual')},
                                              default=IL._jdefault), flush=True)
        for d in rec.get('decisions', []):
            print('  export', d['target'], d['decision'], d['tier'], d['mix'], d['flags'], flush=True)
    td = json.load(open(a.tracks_decisions))
    out['tracks_path'] = [dict(target=d['target'], decision=d['decision'], tier=d['tier'], voxels=d['voxels'],
                               region_voxels=d.get('region_voxels'), mix=d.get('class_mix'), flags=d['flags'])
                          for d in td if d['voxels'] >= 3]
    for d in out['tracks_path']:
        print('  tracks', d['target'], d['decision'], d['tier'], d['mix'], d['flags'], flush=True)
    json.dump(out, open(a.out, 'w'), indent=1, default=IL._jdefault)
    guard.write_manifest(a.out[:-5] + '.manifest.json')


if __name__ == '__main__':
    main()
