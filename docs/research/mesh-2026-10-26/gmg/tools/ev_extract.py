"""ev_extract: the clean Phase-1 bundle of one EVAL episode with a per-board identity mapping of the frozen eval track
(board slot round 3, Prep25). Same steps as b4_extract (M1 hands, M2 joint extraction, M3 per-episode track sanity,
rest planes, route-A shells, split identity test), with three differences:
  1. split eval: depth DATA/cache/depth/eval/ep<N>/depths_fs0.5.npy, video DATA/data/eval/ep<N>_a.mp4, roster = the
     kit's track_3_evaluation_objects.json (object names and slot order; the kit provides them for eval episodes);
  2. tracks: the frozen eval track DATA/data/eval/ep<N>/poses.npz (sha256 checked by the guard against
     gmg/frozen_eval_tracks.json, SPEC section 17) with the board names mapped to the packed reference's boards by
     --map TARGET=SOURCE:ROT,... (ROT one of I, Rx180, Ry180, Rz180: cam_T_TARGET = cam_T_SOURCE @ ROT; world_T_cam
     unchanged). The mapped track is written to RUN/tracks/eval/ep<N>/poses.npz (+ mapping.json) and is the bundle's
     tracks input. The mapping itself is measured outside this process (rigid comparison of our track with the packed
     reference's perception track; build/I/results/slot3-ev25/PREP.md) and given on the command line;
  3. no frame-0 det seeds (none exist for eval in DATA/data/store; ep24's public bundle had none either) and no aux
     owner file (the B.3 ROI-swap validation is public only).
No scan, mesh, mocap, parquet pose or alignment file is opened (guard; strace audit).
--rehome CLEAN_BUNDLE (GMG_MODE=dev): the guard admits a tracks file only from data/sweep, data/eval (frozen sha256)
or the CURRENT run's tracks/, so a clean bundle whose tracks are the mapped track in the clean run cannot be loaded by
a dev consumer (interlock_cands, interlock_dev). This mode regenerates the mapped track in the dev run (same frozen
source, same map: identical arrays), copies the clean bundle's object npz and shell files byte for byte (read through
role clean_run, sha256 recorded) into RUN/bundle/eval/ep<N>/ and rewrites only episode.json's tracks entry (path,
sha256), tier DEV and a rehomed_from record. Consumers then use that bundle with --run = this dev run.
Usage: GMG_MODE=clean python gmg/tools/ev_extract.py --run <DATA>/gmg/runs/<yyyymmdd>-<tag>-<commit7> --ep 25 \
         --map wooden_piece_1=wooden_piece_2:Rx180,wooden_piece_2=wooden_piece_1:I
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

ROTS = dict(I=(1, 1, 1), Rx180=(1, -1, -1), Ry180=(-1, 1, -1), Rz180=(-1, -1, 1))


def parse_map(s, objs):
    m = {}
    for kv in s.split(','):
        tgt, rest = kv.split('=')
        src, rot = rest.split(':')
        if rot not in ROTS:
            raise SystemExit(f'--map: rotation {rot!r} not in {list(ROTS)}')
        m[tgt.strip()] = (src.strip(), rot)
    if sorted(m) != sorted(objs) or sorted(v[0] for v in m.values()) != sorted(objs):
        raise SystemExit(f'--map {s!r} is not a permutation of the roster objects {objs}')
    return m


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--run', required=True)
    ap.add_argument('--ep', type=int, required=True)
    ap.add_argument('--map', required=True, help='TARGET=SOURCE:ROT,... (board names of the packed reference)')
    ap.add_argument('--rehome', default='', help='dev mode only: CLEAN_RUN/bundle/eval/ep<N> to copy into --run')
    a = ap.parse_args()
    if a.rehome and guard.mode() != 'dev':
        raise SystemExit('ev_extract --rehome runs in GMG_MODE=dev only')
    if not a.rehome and guard.mode() != 'clean':
        raise SystemExit('ev_extract runs in GMG_MODE=clean only')
    import numpy as np
    from gmg import hands_cpu, extract_joint as EJ, track_sanity as TS, bundle as BU
    run = guard.set_run(a.run)
    start = dict(commit=guard._git('rev-parse', 'HEAD'),
                 dirty=guard._git('status', '--porcelain', '--', *[os.path.relpath(d, guard.CFG['repo'])
                                                                    for d in guard.CODE_DIRS]))
    D = guard.CFG['data']
    ep, split = a.ep, 'eval'
    t0 = time.time()
    roster_p = os.path.join(guard.CFG['kit'], 'data', 'track_3_evaluation_objects.json')
    roster = guard.load_json(roster_p, 'roster')
    objs = list(roster['episodes'][str(ep)])
    mp = parse_map(a.map, objs)
    src_tracks = os.path.join(D, 'data', 'eval', f'ep{ep}', 'poses.npz')
    depth = os.path.join(D, 'cache', 'depth', split, f'ep{ep}', 'depths_fs0.5.npy')
    calib = os.path.join(D, 'data', 'calib.json')
    video = os.path.join(D, 'data', 'eval', f'ep{ep}_a.mp4')
    logp = os.path.join(run, 'logs', f'{split}-ep{ep}.log')
    os.makedirs(os.path.dirname(logp), exist_ok=True)

    def log(*x):
        s = ' '.join(str(v) for v in x)
        print(s, flush=True)
        with open(logp, 'a') as f:
            f.write(f'[{time.strftime("%H:%M:%S")}] {s}\n')

    log(f'ev_extract ep{ep} objects {objs} map {mp} start {start}')
    # mapped tracks (names and object frames of the packed reference's boards)
    P = guard.load_npz(src_tracks, 'tracks')
    src_rec = guard._INPUTS[os.path.realpath(src_tracks)]
    out_t = {'world_T_cam': np.asarray(P['world_T_cam'])}
    for tgt, (src, rot) in mp.items():
        R4 = np.diag(list(ROTS[rot]) + [1]).astype(np.float64)
        out_t[f'cam_T_{tgt}'] = (np.asarray(P[f'cam_T_{src}'], np.float64) @ R4).astype(np.asarray(P[f'cam_T_{src}']).dtype)
    tdir = os.path.join(run, 'tracks', split, f'ep{ep}')
    os.makedirs(tdir, exist_ok=True)
    tracks = os.path.join(tdir, 'poses.npz')
    with open(tracks, 'wb') as f:
        np.savez(f, **out_t)
    mrec = dict(source=dict(path=src_tracks, sha256=src_rec['sha256'], frozen=src_rec.get('frozen_sha')),
                map={t: dict(source=s, rot=r, rot_diag=list(ROTS[r])) for t, (s, r) in mp.items()},
                rule='cam_T_TARGET = cam_T_SOURCE @ diag(ROT, 1); world_T_cam unchanged',
                evidence='build/I/results/slot3-ev25/PREP.md (rigid comparison with the packed reference track)')
    with open(os.path.join(tdir, 'mapping.json'), 'w') as f:
        json.dump(mrec, f, indent=1)
    log('mapped tracks', tracks, json.dumps(mrec['map']))
    if a.rehome:
        rehome(a, run, ep, split, objs, mrec, tracks, start, log)
        return
    # M1 hands (world_T_cam only)
    hdir = os.path.join(run, 'hands', split, f'ep{ep}')
    th = time.time()
    hpath = hands_cpu.run_hands(split, ep, video, depth, calib, tracks, hdir, log=os.path.join(hdir, 'hands_mp.log'))
    guard.register_output(os.path.join(hdir, 'hands_mp.log'))
    hands_s = round(time.time() - th, 1)
    hl = json.load(open(os.path.join(hdir, 'hands_log.json')))
    log(f'hands {hands_s} s: frames with hand {hl.get("frames_with_hand")} / {hl.get("T")}')
    # M2 + M4
    b = EJ.extract_episode(split, ep, depth, tracks, calib, hpath, objs, None, seed_masks=None, aux_dir=None, log=log,
                           roster=roster_p)
    b.meta['hands'] = dict(path=os.path.relpath(hpath, run), sec=hands_s, frames_with_hand=hl.get('frames_with_hand'),
                           frames_two_hands=hl.get('frames_two_hands'), T=hl.get('T'))
    b.meta['track_map'] = mrec
    log('extract timing', json.dumps(b.meta['timing']))
    # M3 per episode (as b4_extract)
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
    shells, b.meta['shells'] = {}, {}
    out = BU.bundle_dir(run, split, ep)
    os.makedirs(out, exist_ok=True)
    for o in objs:
        shells[o], sinfo = TS.route_a_shell(b.obs(o), b.good_frames(o))
        np.save(os.path.join(out, f'shell_{o}.npy'), shells[o].astype(np.float32))
        b.meta['shells'][o] = dict(file=f'shell_{o}.npy', **sinfo)
    if len(objs) > 1:
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
    BU.save_bundle(b, out)
    b.meta['timing']['episode_s'] = round(time.time() - t0, 1)
    log(f'bundle {out} total {b.meta["timing"]["episode_s"]} s')
    os.makedirs(os.path.join(run, 'manifests'), exist_ok=True)
    guard.write_manifest(os.path.join(run, 'manifests', f'{split}-ep{ep}.json'),
                         extra=dict(step='Prep25 (ev_extract)', ep=ep, split=split, start=start, track_map=mrec,
                                    timing=b.meta['timing']))


def rehome(a, run, ep, split, objs, mrec, tracks, start, log):
    """Dev mode: copy a clean eval bundle into this run with the tracks entry pointing at this run's mapped track."""
    import hashlib
    src = os.path.realpath(a.rehome)
    meta = guard.load_json(os.path.join(src, 'episode.json'), 'clean_run')
    if meta.get('split') != split or int(meta.get('ep', -1)) != ep or list(meta['objects']) != objs:
        raise SystemExit(f'--rehome {src}: split / ep / objects differ from eval ep{ep} {objs}')
    tm = meta.get('track_map') or {}
    if tm.get('map') != mrec['map'] or (tm.get('source') or {}).get('sha256') != mrec['source']['sha256']:
        raise SystemExit(f'--rehome {src}: the clean bundle was built with another map or source track: {tm}')
    out = os.path.join(run, 'bundle', split, f'ep{ep}')
    os.makedirs(out, exist_ok=True)
    files = {}
    for f in [f'{o}.npz' for o in objs] + [f'shell_{o}.npy' for o in objs]:
        sp = os.path.join(src, f)
        rp = guard.open_input(sp, 'clean_run')
        with open(rp, 'rb') as fh:
            data = fh.read()
        sha = hashlib.sha256(data).hexdigest()
        if sha != guard._INPUTS[os.path.realpath(sp)]['sha256']:
            raise SystemExit(f'--rehome: {sp} changed while it was read')
        with open(os.path.join(out, f), 'wb') as fh:
            fh.write(data)
        files[f] = dict(sha256=sha, bytes=len(data))
    new = dict(meta)
    t_sha = guard._sha256(os.path.realpath(tracks))
    new['tracks'] = dict(path=tracks, sha256=t_sha)
    new['tier'] = 'DEV'
    new['rehomed_from'] = dict(bundle=src, episode_json_sha256=guard._INPUTS[os.path.realpath(
        os.path.join(src, 'episode.json'))]['sha256'], clean_tracks=meta['tracks'], files=files,
        rule='object npz and shell files copied byte for byte; tracks = the same map of the same frozen source, '
             'regenerated in this run (the tracks role admits only the current run\'s tracks/)')
    with open(os.path.join(out, 'episode.json'), 'w') as fh:
        json.dump(new, fh)
    log(f'rehomed {src} -> {out}: files {json.dumps(files)}; tracks {tracks} sha256 {t_sha}')
    os.makedirs(os.path.join(run, 'manifests'), exist_ok=True)
    guard.write_manifest(os.path.join(run, 'manifests', f'{split}-ep{ep}-rehome.json'),
                         extra=dict(step='Prep25 (ev_extract --rehome)', ep=ep, split=split, start=start,
                                    track_map=mrec, rehomed_from=new['rehomed_from']))


if __name__ == '__main__':
    main()
