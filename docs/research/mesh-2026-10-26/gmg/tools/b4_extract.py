"""b4_extract: the clean Phase-1 bundle of one episode (build step B4: M1 hands, M2 joint extraction, M4 census and
jitter, M3 per-episode track sanity and split identity test).

GMG_MODE=clean. Inputs (guarded): depth DATA/cache/depth/<split>/ep<N>/depths_fs0.5.npy, tracks
DATA/data/sweep/ep<N>/poses.npz (P1), calib DATA/data/calib.json, the cam_a video (public dataset copy under
DATA/hfds/track_3/public/videos/), the frame-0 det dump DATA/data/store/ep<N>/det_f0.npz (mask keys only) when it
exists, the roster gmg/roster_public.json. Outputs in RUN: hands/<split>/ep<N>/ (M1), bundle/<split>/ep<N>/
(episode.json + <obj>.npz), aux/<split>/ep<N>/owners.npz (final owner per sample, for the B.3 validation; deleted after
it), manifests/<split>-ep<N>.json (with the run ledger). No scan, mesh, mocap, parquet pose or alignment file is
opened (guard; strace audit).
Usage: GMG_MODE=clean python gmg/tools/b4_extract.py --run <DATA>/gmg/runs/<yyyymmdd>-b4ext-<commit7> --ep 2
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


def video_path(D, split, ep):
    sub = 'public' if split == 'public' else 'evaluation'
    return os.path.join(D, 'hfds', 'track_3', sub, 'videos', 'chunk-000', 'observation.images.ego_cam_a',
                        f'episode_{int(ep):06d}.mp4')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--run', required=True)
    ap.add_argument('--split', default='public', choices=['public'])
    ap.add_argument('--ep', type=int, required=True)
    ap.add_argument('--no-aux', action='store_true')
    a = ap.parse_args()
    if guard.mode() != 'clean':
        raise SystemExit('b4_extract runs in GMG_MODE=clean only')
    import numpy as np
    from gmg import hands_cpu, extract_joint as EJ, track_sanity as TS, bundle as BU
    run = guard.set_run(a.run)
    start = dict(commit=guard._git('rev-parse', 'HEAD'),
                 dirty=guard._git('status', '--porcelain', '--', *[os.path.relpath(d, guard.CFG['repo'])
                                                                    for d in guard.CODE_DIRS]))
    D = guard.CFG['data']
    ep, split = a.ep, a.split
    t0 = time.time()
    roster_p = os.path.join(guard.CFG['gmg'], 'roster_public.json')
    roster = guard.load_json(roster_p, 'roster')
    objs = list(roster['episodes'][str(ep)])
    tracks = os.path.join(D, 'data', 'sweep', f'ep{ep}', 'poses.npz')
    depth = os.path.join(D, 'cache', 'depth', split, f'ep{ep}', 'depths_fs0.5.npy')
    calib = os.path.join(D, 'data', 'calib.json')
    video = video_path(D, split, ep)
    det = os.path.join(D, 'data', 'store', f'ep{ep}', 'det_f0.npz')
    det = det if os.path.exists(det) else None
    logp = os.path.join(run, 'logs', f'{split}-ep{ep}.log')
    os.makedirs(os.path.dirname(logp), exist_ok=True)

    def log(*x):
        s = ' '.join(str(v) for v in x)
        print(s, flush=True)
        with open(logp, 'a') as f:
            f.write(f'[{time.strftime("%H:%M:%S")}] {s}\n')

    log(f'b4_extract ep{ep} objects {objs} det {bool(det)} start {start}')
    # M1 hands
    hdir = os.path.join(run, 'hands', split, f'ep{ep}')
    hpath = os.path.join(hdir, 'hands.npz')
    th = time.time()
    hpath = hands_cpu.run_hands(split, ep, video, depth, calib, tracks, hdir, log=os.path.join(hdir, 'hands_mp.log'))
    guard.register_output(os.path.join(hdir, 'hands_mp.log'))
    hands_s = round(time.time() - th, 1)
    hl = json.load(open(os.path.join(hdir, 'hands_log.json')))
    log(f'hands {hands_s} s: frames with hand {hl.get("frames_with_hand")} / {hl.get("T")}')
    # M2 + M4
    aux = None if a.no_aux else os.path.join(run, 'aux', split, f'ep{ep}')
    b = EJ.extract_episode(split, ep, depth, tracks, calib, hpath, objs, None, seed_masks=det, aux_dir=aux, log=log,
                           roster=roster_p)
    if aux:
        guard.register_output(os.path.join(aux, 'owners.npz'))
    b.meta['hands'] = dict(path=os.path.relpath(hpath, run), sec=hands_s, frames_with_hand=hl.get('frames_with_hand'),
                           frames_two_hands=hl.get('frames_two_hands'), T=hl.get('T'))
    log('extract timing', json.dumps(b.meta['timing']))
    # M3 per episode: good frames, sanity; then rest planes (V4) on the good frames; split identity test
    ts = time.time()
    b.meta['good'], b.meta['sanity'] = {}, {}
    for o in objs:
        r = TS.check(b, o)
        b.meta['good'][o] = r.pop('good')
        r.update(identity_split=None, identity_cross=None)
        b.meta['sanity'][o] = r
        log(f'sanity {o}: {r["n_good"]}/{r["n_frames"]} good, flags {r["flags"]}, below {r["below_table_frac"]}, '
            f'resid {r["block_resid_mm"]}')
    b.meta['rest'] = {o: BU._rest(b, o, b.meta['table_band_m']) for o in objs}
    shells = {}
    if len(objs) > 1:
        for o in objs:
            shells[o], _ = TS.route_a_shell(b.obs(o), b.good_frames(o))
        for o in objs:
            res = {}
            for p in objs:
                if p != o:
                    res[p] = TS.split_test(b, o, p, shells=shells)
            b.meta['sanity'][o]['identity_split'] = res
            log(f'split test {o}: ' + json.dumps({p: (r.get('pass_'), r.get('chamfer_h1_h2_mm'),
                                                      r.get('chamfer_h1_p_mm'), r.get('chamfer_h2_p_mm'))
                                                  for p, r in res.items()}))
    b.meta['timing']['sanity_s'] = round(time.time() - ts, 1)
    out = BU.bundle_dir(run, split, ep)
    BU.save_bundle(b, out)
    b.meta['timing']['episode_s'] = round(time.time() - t0, 1)
    log(f'bundle {out} total {b.meta["timing"]["episode_s"]} s')
    os.makedirs(os.path.join(run, 'manifests'), exist_ok=True)
    guard.write_manifest(os.path.join(run, 'manifests', f'{split}-ep{ep}.json'),
                         extra=dict(step='B4', ep=ep, split=split, start=start, timing=b.meta['timing']))


if __name__ == '__main__':
    main()
