"""Dummy clean-mode gmg run for the B0 strace audit (SPEC section 24, step B0).

  GMG_MODE=clean python dummy_clean_run.py [--tag b0dummy]

It sets a run folder DATA/gmg/runs/<yyyymmdd>-<tag>-<commit7>, reads one input of every clean role that exists here
through the guard (and the public track and calibration through autokit.io_gt, as autokit code would), then tries
every refused class of input: scans, deny-listed library meshes and scan-templated tracks, every revision-1 refused
folder (real files where they exist), refused det keys, the kit scorer, dev-only roles, a hard-link copy, a symlink
to a scan, a parquet, *_align and mocap paths, plain open() and np.load() of refused paths, io_gt.load_obs of
obs_all and io_gt.load_mesh of library_v3. Every attempt must raise GuardError before the file is opened. It writes
RUN/manifest.json and RUN/dummy_result.json and prints the result; exit code 0 if every attempt was refused and every
allowed read passed. Run it under tools/strace_audit.py to show 0 forbidden opens.
"""
import argparse
import datetime
import json
import os
import shutil
import sys

MR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if MR not in sys.path:
    sys.path.insert(0, MR)
from gmg import guard  # noqa: E402

import numpy as np  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--tag', default='b0dummy')
    a = ap.parse_args()
    if guard.mode() != 'clean':
        sys.exit('dummy_clean_run: GMG_MODE must be clean')
    commit = (guard._git('rev-parse', '--short=7', 'HEAD') or '0000000')[:7]
    day = datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%d')
    D, R, K = guard.CFG['data'], guard.CFG['repo'], guard.CFG['kit']
    run = guard.set_run(os.path.join(D, 'gmg', 'runs', f'{day}-{a.tag}-{commit}'))
    res = dict(run=run, allowed=[], refused=[], unexpected=[], absent=[])

    def ok(label, fn):
        try:
            v = fn()
            res['allowed'].append(dict(label=label, result=str(v)[:120]))
        except FileNotFoundError as e:
            res['absent'].append(dict(label=label, error=str(e)[:200]))
        except Exception as e:
            res['unexpected'].append(dict(label=label, expected='allowed', error=f'{type(e).__name__}: {e}'[:400]))

    def no(label, fn, path=None):
        exists = os.path.isfile(path) if path else None          # stat only
        try:
            fn()
            res['unexpected'].append(dict(label=label, expected='refused', path=path))
        except guard.GuardError as e:
            res['refused'].append(dict(label=label, path=path, exists=exists, by='gmg.guard', reason=str(e)[-160:]))
        except ValueError as e:                                   # autokit.io_gt's own refusal (before the guard)
            if not str(e).startswith('integrity: refused'):
                raise
            res['refused'].append(dict(label=label, path=path, exists=exists, by='autokit.io_gt',
                                       reason=str(e)[-160:]))
        except Exception as e:
            res['unexpected'].append(dict(label=label, expected='GuardError', path=path,
                                          error=f'{type(e).__name__}: {e}'[:300]))

    # ---------------------------------------------------------------- allowed inputs (one per clean role present)
    ok('calib', lambda: guard.load_json(f'{D}/data/calib.json', 'calib')['stereo_pairs'][0]['camera'])
    ok('tracks public ep2', lambda: sorted(guard.load_npz(f'{D}/data/sweep/ep2/poses.npz', 'tracks')))
    ok('tracks eval ep1', lambda: sorted(guard.load_npz(f'{D}/data/eval/ep1/poses.npz', 'tracks')))
    ok('det ep2 mask keys', lambda: sorted(guard.load_npz(f'{D}/data/store/ep2/det_f0.npz', 'det')))
    ok('det ep2 masks only', lambda: guard.load_npz(f'{D}/data/store/ep2/det_f0.npz', 'det', ['masks'])['masks'].shape)

    def video():
        rp = guard.open_input(f'{D}/data/store/ep2_a.mp4', 'video')
        with open(rp, 'rb') as f:
            return len(f.read(1 << 16))
    ok('video public ep2_a', video)
    ok('video eval ep1_a', lambda: guard.open_input(f'{D}/data/eval/ep1_a.mp4', 'video'))
    ok('roster kit', lambda: len(guard.load_json(f'{K}/data/track_3_evaluation_objects.json', 'roster')['episodes']))
    ok('roster public', lambda: len(guard.load_json(f'{guard.GMG_DIR}/roster_public.json', 'roster')['episodes']))
    ok('kit config', lambda: sorted(guard.load_json(f'{K}/config/tracks.json', 'kit'))[:3])
    ok('depth public ep2', lambda: guard.open_input(f'{D}/data/depth/ep2/depths_fs0.5.npy', 'depth'))

    def own():
        p = os.path.join(run, 'bundle', 'note.json')
        os.makedirs(os.path.dirname(p), exist_ok=True)
        json.dump(dict(x=1), open(p, 'w'))
        return guard.load_json(p, 'own')
    ok('own write+read', own)

    def via_io_gt():
        from autokit import io_gt
        P = io_gt.load_poses(2)
        return sorted(P), io_gt.load_calib()['size']
    ok('io_gt poses+calib', via_io_gt)
    ok('constant generic', lambda: guard.constant('vote_voxel_m', 0.004, 'generic'))

    # ---------------------------------------------------------------- refused attempts
    S = D
    probes = [
        ('scan (data/scan)', f'{S}/data/scan/white_pot.glb', 'own'),
        ('library_v3 mesh', f'{R}/meshes/library_v3/white_pot.glb', 'kit'),
        ('library_v2 mesh', f'{R}/meshes/library_v2/white_pot.glb', 'kit'),
        ('library_v1 mesh', f'{R}/meshes/library_v1/white_pot.glb', 'kit'),
        ('library_v4 mesh', f'{R}/meshes/library_v4/white_pot.glb', 'kit'),
        ('library_v3x mesh', f'{R}/meshes/library_v3x/beige_cup.glb', 'own'),
        ('results/prim mesh', f'{MR}/results/prim/meshes/white_pot_lid_ep2_fit_v1.glb', 'own'),
        ('scratchpad/prim', f'{S}/prim/potlid/cand/white_pot_lid_ep2_fit.glb', 'own'),
        ('scratchpad/lathe', f'{S}/lathe/ep41_white_pot_hyb.glb', 'own'),
        ('scratchpad/auto', f'{S}/auto/roster/ep0.npz', 'own'),
        ('scratchpad/gen/mesh-*', f'{S}/gen/mesh-20261029-gen-f3fbeb0/scores.log', 'own'),
        ('scratchpad/crops', f'{S}/crops/ep11/beige_cup_crops.json', 'own'),
        ('scratchpad/evalcrops', f'{S}/evalcrops/log_ep16_wooden_spoon.txt', 'own'),
        ('scratchpad/diag', f'{S}/diag/sam-placement/common.py', 'kit'),
        ('scratchpad/gmg/design', f'{S}/gmg/design/evidence.md', 'own'),
        ('scratchpad/obs_all as own', f'{S}/obs_all/ep26_white_pot.npz', 'own'),
        ('scratchpad/obs_all as obs_all (dev-only role)', f'{S}/obs_all/ep26_white_pot.npz', 'obs_all'),
        ('scratchpad/obs', f'{S}/obs/ep41_white_pot.npz', 'own'),
        ('x0_pool (dev-only role)', f'{MR}/results/gen-probe/scores.jsonl', 'x0_pool'),
        ('fixture (dev-only role)', f'{S}/prim/potlid/cand/white_pot_lid_ep2_fit.glb', 'fixture'),
        ('scan-templated track (loc/perc)', f'{S}/loc/perc/ep2/poses.npz', 'tracks'),
        ('align file', f'{S}/page/align/ep11_beige_cup_align.npz', 'own'),
        ('parquet', f'{D}/t3/ep2.parquet', 'roster'),
        ('mocap path', f'{D}/data/mocap/ep2.npz', 'tracks'),
        ('kit scorer', f'{K}/metric_code/track_3/CD-O.py', 'kit'),
        ('kit scorer v2dlb', f'{K}/v2dlb/object_mesh.py', 'kit'),
        ('det store poses as tracks', f'{D}/data/store/ep2/poses.npz', 'tracks'),
        ('hands not a clean role', f'{D}/data/sweep/ep2/hands.npz', 'tracks'),
        ('unknown role', f'{D}/data/calib.json', 'scan'),
    ]
    for label, p, role in probes:
        no(label, lambda p=p, role=role: guard.open_input(p, role), p)
    for k in ('sim', 'gdino', 'chosen', 'template_extent', 'score', 'verify'):
        no(f'det key {k}', lambda k=k: guard.load_npz(f'{D}/data/store/ep2/det_f0.npz', 'det', ['masks', k]),
           f'{D}/data/store/ep2/det_f0.npz')

    def hardlink():
        src = os.path.join(run, 'bundle', 'hl_src.json')
        json.dump(dict(y=2), open(src, 'w'))
        dst = os.path.join(run, 'bundle', 'hl_dst.json')
        if os.path.exists(dst):
            os.remove(dst)
        os.link(src, dst)
        return guard.open_input(dst, 'own')
    no('hard-link copy', hardlink)

    def symlink():
        dst = os.path.join(run, 'bundle', 'innocent.glb')
        if os.path.lexists(dst):
            os.remove(dst)
        os.symlink(f'{S}/data/scan/white_pot.glb', dst)
        return guard.open_input(dst, 'own')
    no('symlink to a scan', symlink)
    no('open() of a scan (hook)', lambda: open(f'{S}/data/scan/white_pot.glb', 'rb'), f'{S}/data/scan/white_pot.glb')
    no('np.load of obs_all (hook)', lambda: np.load(f'{S}/obs_all/ep26_white_pot.npz'), f'{S}/obs_all/ep26_white_pot.npz')
    no('os.open of library_v3 (hook)', lambda: os.open(f'{R}/meshes/library_v3/white_pot.glb', os.O_RDONLY),
       f'{R}/meshes/library_v3/white_pot.glb')
    no('open() of diag code (hook)', lambda: open(f'{S}/diag/sam-placement/common.py'),
       f'{S}/diag/sam-placement/common.py')

    # det key filter by file identity (verification round 1, bypasses a-c; d is an import-time root check, see tests)
    det = f'{D}/data/store/ep2/det_f0.npz'
    no('(a) open_input of det_f0.npz outside load_npz', lambda: guard.open_input(det, 'det'), det)
    no('(a) np.load of det_f0.npz (hook)', lambda: np.load(det), det)
    no('(a) open() of det_f0.npz (hook)', lambda: open(det, 'rb'), det)
    no('(b) shutil.copyfile det_f0.npz -> RUN (hook)',
       lambda: shutil.copyfile(det, os.path.join(run, 'bundle', 'det_copy.npz')), det)
    no('(c) load_npz det_f0.npz as weights with sim, chosen',
       lambda: guard.load_npz(det, 'weights', ['masks', 'sim', 'chosen']), det)
    no('(c) load_npz det_f0.npz as own, all keys', lambda: guard.load_npz(det, 'own'), det)

    def dirfd_auto():
        fd = os.open(f'{S}/auto', os.O_RDONLY | os.O_DIRECTORY)
        try:
            return os.open('roster/ep0.npz', os.O_RDONLY, dir_fd=fd)
        finally:
            os.close(fd)
    no('os.open with dir_fd into auto/ (hook)', dirfd_auto, f'{S}/auto/roster/ep0.npz')
    no('write into another run folder (hook)',
       lambda: open(os.path.join(guard.runs_root(), '20200101-other-0000000', 'x.json'), 'w'))
    no('write into the dev run root (hook)',
       lambda: open(os.path.join(guard.runs_root('dev'), '20200101-other-0000000', 'x.json'), 'w'))

    def io_gt_obs():
        from autokit import io_gt
        return io_gt.load_obs(f'{S}/obs_all/ep26_white_pot.npz')
    no('io_gt.load_obs of obs_all', io_gt_obs, f'{S}/obs_all/ep26_white_pot.npz')

    def io_gt_mesh():
        from autokit import io_gt
        return io_gt.load_mesh(f'{R}/meshes/library_v3/white_pot.glb')
    no('io_gt.load_mesh of library_v3', io_gt_mesh, f'{R}/meshes/library_v3/white_pot.glb')

    def io_gt_auto_mesh():
        from autokit import io_gt
        return io_gt.mesh_input(f'{S}/lathe/ep41_white_pot_hyb.glb')
    no('io_gt.mesh_input of a dropped root (lathe)', io_gt_auto_mesh, f'{S}/lathe/ep41_white_pot_hyb.glb')
    no('constant 7 mm ball radius', lambda: guard.constant('ball_r_mm', 7.0, 'generic'))
    no('constant tau_v3 0.20', lambda: guard.constant('tau_v3', 0.2, 'informed'))
    no('constant fitted to scans', lambda: guard.constant('t0_mm', 2.1, 'fitted:scan wall median'))

    res['io_gt_roots'] = guard.io_gt_roots_report()
    m = guard.write_manifest(os.path.join(run, 'manifest.json'))
    res['manifest'] = dict(path=os.path.join(run, 'manifest.json'), tier=m['tier'], inputs=len(m['inputs']),
                           refusals=len(m['refusals']), hook=m['hook'], commit=m['commit'])
    res['pass'] = not res['unexpected']
    json.dump(res, open(os.path.join(run, 'dummy_result.json'), 'w'), indent=1)
    print(json.dumps(dict(run=run, allowed=len(res['allowed']), refused=len(res['refused']),
                          absent=[x['label'] for x in res['absent']], unexpected=res['unexpected'],
                          manifest=res['manifest'], **{'pass': res['pass']})))
    sys.exit(0 if res['pass'] else 1)


if __name__ == '__main__':
    main()
