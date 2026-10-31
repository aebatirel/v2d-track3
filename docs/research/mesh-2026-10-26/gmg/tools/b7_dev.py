"""b7_dev: structure hypotheses (M5) and marker balls (M6) on the PREREG C.2 anchor episodes, dev mode (build step B7).

GMG_MODE=dev only. For each episode: the dev bundle (bundle.from_obs_all: obs_all, tracks, calib, roster, det keys
depth/K), then
  structure.hypotheses(obs, sigma=bundle sigma) for the episode's anchor object(s) (PREREG C.2: the first episode of
      each object's list; track sanity is B4 and not built, so no anchor is skipped) and, with --partners, for the
      other tracked objects of the episode too;
  markers.detect_episode(bundle) for every tracked object of the episode (the radius consensus is pooled over the
      episode's objects, SPEC section 10).
Writes RUN/b7/ep<N>.json per episode, RUN/b7_summary.json and RUN/manifest.json (tier DEV). GT-free: no scan, mesh,
mocap, parquet pose or alignment file is opened (the guard refuses them; the strace audit checks it). Dev outputs are
never scored (PREREG C.1).
Usage: GMG_MODE=dev python gmg/tools/b7_dev.py --run <DATA>/gmg/runs-dev/<yyyymmdd>-b7dev<k>-<commit7> --eps 27,2
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

# PREREG C.2: the first episode of each object's list (fixed before any run)
ANCHORS = [(27, 'white_pot'), (2, 'white_pot_lid'), (31, 'plastic_dish_rack'), (12, 'blue_cup'), (11, 'beige_cup'),
           (21, 'water_pitcher'), (40, 'mini_dust_pan'), (18, 'mini_sweeper'), (24, 'wooden_piece_1'),
           (23, 'wooden_piece_2')]


def _short_struct(h):
    ax = h.get('axis') or {}
    return dict(n_points=h['n_points'], sigma_mm=h['sigma_mm'], lathe=ax.get('accepted'), rotc_sigma=h['rotc_sigma'],
                lathe_mad_sigma=h['lathe_mad_sigma'], rot_free_viol=ax.get('rot_free_viol'),
                axis_source=ax.get('source'),
                mirrors=[dict(accepted=m['accepted'], resid_sigma=m['resid_sigma'], observed=m['observed'],
                              free_viol=m['free_viol'], moved=m['moved']) for m in h['mirrors']],
                planes=len(h['planes']), plate_pairs=[dict(thickness_mm=p['thickness_mm'], overlap=p['overlap'])
                                                       for p in h['plane_pairs']],
                repeats_accepted=h['accepted']['repeats'],
                repeats=[dict(order=r['order'], resid_sigma=r['resid_sigma'], observed=r['observed'],
                              free_viol=r['free_viol'], accepted=r['accepted']) for r in h['repeats']],
                timing_s=h['timing_s'], flags=h.get('flags', []))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--run', required=True)
    ap.add_argument('--eps', default=','.join(str(e) for e, _ in ANCHORS))
    ap.add_argument('--partners', action='store_true', help='structure for every tracked object, not only anchors')
    ap.add_argument('--no-markers', action='store_true')
    ap.add_argument('--no-structure', action='store_true')
    ap.add_argument('--marker-objects', choices=('all', 'anchors'), default='all',
                    help='anchors: detect on the anchor object(s) only, consensus pooled over them (compute; B7 notes)')
    a = ap.parse_args()
    if guard.mode() != 'dev':
        raise SystemExit('b7_dev runs in GMG_MODE=dev only')
    run = guard.set_run(a.run)
    # the code state at the START of the run (the manifest records HEAD and the dirty files at the end)
    code_dirs = [os.path.relpath(d, guard.CFG['repo']) for d in guard.CODE_DIRS]
    start = dict(commit=guard._git('rev-parse', 'HEAD'),
                 dirty_files=(guard._git('status', '--porcelain', '--', *code_dirs) or '').splitlines())
    from gmg import bundle as B, markers as MK, structure as ST
    eps = [int(x) for x in a.eps.split(',') if x]
    anchors = {}
    for e, o in ANCHORS:
        anchors.setdefault(e, []).append(o)
    out_dir = os.path.join(run, 'b7')
    os.makedirs(out_dir, exist_ok=True)
    summary = dict(schema='gmg-b7-dev/1', run=os.path.basename(run), tier='DEV', anchors=ANCHORS,
                   marker_settings_sha256=MK.SETTINGS_SHA256, code_at_start=start, episodes={})
    for ep in eps:
        t0 = time.time()
        b = B.from_obs_all(ep)
        tb = round(time.time() - t0, 1)
        objs = b.objects if a.partners else [o for o in b.objects if o in anchors.get(ep, [])]
        if a.no_structure:
            objs = []
        res = dict(ep=ep, objects=b.objects, anchors=anchors.get(ep, []), bundle_s=tb,
                   sigma_mm={o: b.meta['sigma_mm'][o] for o in b.objects}, structure={}, markers=None)
        for o in objs:
            t = time.time()
            h = ST.hypotheses(b.obs(o), sigma=b.sigma(o))
            res['structure'][o] = h
            print(json.dumps(dict(ep=ep, obj=o, structure=_short_struct(h), sec=round(time.time() - t, 1)),
                             default=float), flush=True)
        if not a.no_markers:
            t = time.time()
            mk = MK.detect_episode(b, objects=None if a.marker_objects == 'all' else
                                   [o for o in b.objects if o in anchors.get(ep, [])])
            mk['sec'] = round(time.time() - t, 1)
            res['markers'] = mk
            print(json.dumps(dict(ep=ep, r_consensus_mm=mk['r_consensus_mm'], n_balls=mk['n_balls'],
                                  unimodal=mk['unimodal'], sec=mk['sec']), default=float), flush=True)
        res['sec'] = round(time.time() - t0, 1)
        with open(os.path.join(out_dir, f'ep{ep}.json'), 'w') as f:
            json.dump(res, f, indent=1, default=float)
        summary['episodes'][str(ep)] = dict(
            sigma_mm=res['sigma_mm'], sec=res['sec'],
            structure={o: _short_struct(h) for o, h in res['structure'].items()},
            markers=None if res['markers'] is None else dict(
                r_consensus_mm=res['markers']['r_consensus_mm'], n_balls=res['markers']['n_balls'],
                unimodal=res['markers']['unimodal'],
                objects=res['markers']['objects'],
                radii_mm={o: [x['r_mm'] for x in v] for o, v in res['markers']['balls'].items()},
                passes={o: [x['pass_'] for x in v] for o, v in res['markers']['balls'].items()},
                normal_dev_deg={o: [x['normal_dev_deg'] for x in v] for o, v in res['markers']['balls'].items()},
                outside_ratio={o: [x['outside_ratio'] for x in v] for o, v in res['markers']['balls'].items()}))
        with open(os.path.join(run, 'b7_summary.json'), 'w') as f:
            json.dump(summary, f, indent=1, default=float)
        del b
    man = guard.write_manifest(os.path.join(run, 'manifest.json'))
    print(json.dumps(dict(done=True, commit=man['commit'], code_dirty=man['code_dirty'],
                          inputs=len(man['inputs']), refusals=len(man.get('refusals', [])))), flush=True)


if __name__ == '__main__':
    main()
