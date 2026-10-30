"""B0 tests of gmg/guard.py, the autokit/io_gt.py fix and the strace audit (SPEC section 24, step B0).

  python docs/research/mesh-2026-10-26/gmg/tests/test_guard.py        (venv python: numpy is needed)

Pass condition (SPEC section 24, B0): every deny path, glob, sha256, refused folder, refused det key and hard-link copy
raises; the allowed roles pass; the strace of a dummy clean-mode run shows 0 forbidden opens.

The guard reads its configuration once at import, so every scenario runs in a fresh interpreter (guard_probe.py) with
GMG_DATA_ROOT pointing at a synthetic tree built here (in the session scratchpad). The synthetic files hold made-up
bytes; no scan, library mesh, parquet or mocap content is created or read. Checks on real repository and scratchpad
paths use guard.check (path rules only), so a refused real file is never opened. The test runner itself does not
import gmg.guard (its open hook would refuse the creation of the synthetic "scan" files).
"""
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
GMG = os.path.dirname(HERE)
MR = os.path.dirname(GMG)
REPO = os.path.abspath(os.path.join(MR, '..', '..', '..'))
SCRATCH = '/tmp/claude-0/-home-user-v2d-track3/90d4009c-b597-536b-9d55-58f81afca135/scratchpad'
PROBE = os.path.join(HERE, 'guard_probe.py')
AUDIT = os.path.join(GMG, 'tools', 'strace_audit.py')
DUMMY = os.path.join(GMG, 'tools', 'dummy_clean_run.py')
RUN_NAME = '20261030-test-0000000'
T = {}                                                   # the synthetic tree


def _w(path, data=b'x'):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'wb') as f:
        f.write(data if isinstance(data, bytes) else data.encode())
    return path


def _npz(path, **arrs):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    np.savez(path, **arrs)
    return path


def setUpModule():
    base = os.path.join(SCRATCH, 'gmgtest')
    os.makedirs(base, exist_ok=True)
    D = tempfile.mkdtemp(prefix='tree-', dir=base)
    T['D'] = D
    T['RUN'] = os.path.join(D, 'gmg', 'runs', RUN_NAME)
    K = os.path.join(D, 'kit', 'v2d_submission_kit')
    T['K'] = K
    I4 = np.tile(np.eye(4), (3, 1, 1))
    T['calib'] = _w(f'{D}/data/calib.json', json.dumps(dict(stereo_pairs=[dict(camera='ego')])))
    T['tracks_pub'] = _npz(f'{D}/data/sweep/ep2/poses.npz', world_T_cam=I4, cam_T_white_pot=I4, template_score=np.ones(3))
    T['tracks_eval'] = _npz(f'{D}/data/eval/ep1/poses.npz', world_T_cam=I4, cam_T_white_pot=I4)
    T['tracks_run'] = _npz(f'{T["RUN"]}/tracks/ep2/poses.npz', world_T_cam=I4, cam_T_white_pot=I4)
    T['det_keys_ok'] = ['K', 'depth', 'frame', 'image', 'mask_shape', 'masks', 'names']
    T['det_keys_bad'] = ['sim', 'score', 'score_rules', 'gdino', 'template_extent', 'template_intensity', 'chosen',
                         'verify', 'verify_matched', 'rules', 'params', 'reprop', 'centroid', 'area', 'intensity',
                         'extent', 'extent_eroded']
    det = {k: np.zeros(2) for k in T['det_keys_ok'] + T['det_keys_bad']}
    det['gdino'] = np.array('[]')
    T['det'] = _npz(f'{D}/data/store/ep2/det_f0.npz', **det)
    T['video_pub'] = _w(f'{D}/data/store/ep2_a.mp4', b'\x00' * 64)
    T['video_eval'] = _w(f'{D}/data/eval/ep1_a.mp4', b'\x00' * 64)
    T['video_hf'] = _w(f'{D}/hfds/track_3/public/videos/chunk-000/observation.images.ego_cam_a/episode_000002.mp4')
    T['depth_legacy'] = _w(f'{D}/data/depth/ep2/depths_fs0.5.npy')
    T['depth_pub'] = _w(f'{D}/cache/depth/public/ep2/depths_fs0.5.npy')
    T['depth_eval'] = _w(f'{D}/cache/depth/eval/ep1/depths_fs0.5.npy')
    T['roster_kit'] = _w(f'{K}/data/track_3_evaluation_objects.json', json.dumps(dict(episodes={'1': ['a']})))
    T['kit_cfg'] = _w(f'{K}/config/tracks.json', '{}')
    T['kit_budget'] = _w(f'{K}/v2dlb/mesh_budget.py', '# kit decode\n')
    T['kit_scorer'] = [_w(f'{K}/metric_code/track_3/CD-O.py'), _w(f'{K}/v2dlb/object_mesh.py'),
                       _w(f'{K}/v2dlb/track3_pose.py'), _w(f'{K}/v2dlb/trajectory.py'), _w(f'{K}/v2dlb/dataset.py')]
    T['weights'] = _w(f'{D}/weights/sam3d/checkpoints/ss_generator.ckpt')
    T['own'] = _w(f'{T["RUN"]}/bundle/train/ep2/note.json', '{"x": 1}')
    T['refused'] = {
        'library_v3x': _w(f'{D}/meshes/library_v3x/a.glb'),
        'library_v3': _w(f'{D}/meshes/library_v3/a.glb'),
        'library_v1': _w(f'{D}/meshes/library_v1/a.glb'),
        'library_v4': _w(f'{D}/meshes/library_v4/a.glb'),
        'results/prim': _w(f'{D}/results/prim/meshes/a.glb'),
        'prim': _w(f'{D}/prim/potlid/cand/white_pot_lid_ep2_fit.glb', b'not the hand-kit lid'),
        'lathe': _w(f'{D}/lathe/a.glb'),
        'auto': _w(f'{D}/auto/stage1/refined/ep2_white_pot.npz'),
        'gen/mesh-20261029': _w(f'{D}/gen/mesh-20261029-gen-f3fbeb0/results/a.glb'),
        'gen/mesh-other': _w(f'{D}/gen/mesh-20261101-gen-abcdef0/a.glb'),
        'crops': _w(f'{D}/crops/ep11/a.json'),
        'evalcrops': _w(f'{D}/evalcrops/ep16/a.json'),
        'diag': _w(f'{D}/diag/sam-placement/common.py', 'def load_scan(): pass\n'),
        'gmg/design': _w(f'{D}/gmg/design/gen-first/contact_census.jsonl'),
        'obs_all': _npz(f'{D}/obs_all/ep2_white_pot.npz', pts=np.zeros((2, 3))),
        'obs': _npz(f'{D}/obs/ep2_white_pot.npz', pts=np.zeros((2, 3))),
    }
    T['gt'] = {
        '/scan': _w(f'{D}/data/scan/white_pot.glb'),
        '/loc/': _w(f'{D}/loc/perc/ep2/poses.npz'),
        '_align': _w(f'{D}/page/align/ep11_beige_cup_align.npz'),
        '.parquet': _w(f'{D}/t3/ep2.parquet'),
        'mocap': _w(f'{D}/data/mocap_ep2.npz'),
    }
    T['code_scan'] = _w(f'{D}/tools/json/scanner.py', '# code\n')
    T['other'] = _w(f'{D}/misc/notes.bin')
    # a renamed copy of a "denied" file: its sha256 goes on an extra deny-list (GMG_EXTRA_DENYLIST, additive)
    T['deny_copy'] = _npz(f'{D}/data/sweep/ep3/poses.npz', world_T_cam=I4 * 7)
    sha = hashlib.sha256(open(T['deny_copy'], 'rb').read()).hexdigest()
    T['deny_copy_sha'] = sha
    T['extra_deny'] = _w(f'{base}/extra_deny_{os.path.basename(D)}.json',
                         json.dumps(dict(globs=['*/forbidden_glob_dir/*'], sha256={sha: 'test: synthetic denied file'})))
    T['glob_hit'] = _w(f'{D}/data/sweep/forbidden_glob_dir/poses.npz')
    # hard link (two names, one inode) inside allowed folders
    T['hl_a'] = _npz(f'{D}/data/sweep/ep4/poses.npz', world_T_cam=I4)
    T['hl_b'] = f'{D}/data/sweep/ep5/poses.npz'
    os.makedirs(os.path.dirname(T['hl_b']), exist_ok=True)
    os.link(T['hl_a'], T['hl_b'])
    # symlinks inside the run folder that point at refused files
    T['sym_scan'] = f'{T["RUN"]}/bundle/innocent.glb'
    os.symlink(T['gt']['/scan'], T['sym_scan'])
    T['sym_auto'] = f'{T["RUN"]}/bundle/sneaky.npz'
    os.symlink(T['refused']['auto'], T['sym_auto'])
    T['sym_lib'] = f'{T["RUN"]}/bundle/lib.glb'
    os.symlink(f'{REPO}/meshes/library_v3/white_pot.glb', T['sym_lib'])
    T['fixture_tmp'] = _w(f'{base}/fixtures-{os.path.basename(D)}/synthetic_lid.glb')
    T['x0_gen'] = T['refused']['gen/mesh-other']


def tearDownModule():
    if T.get('D') and os.path.isdir(T['D']):
        shutil.rmtree(T['D'], ignore_errors=True)
    for k in ('extra_deny',):
        if T.get(k) and os.path.exists(T[k]):
            os.remove(T[k])
    fx = os.path.dirname(T.get('fixture_tmp', ''))
    if fx and os.path.isdir(fx):
        shutil.rmtree(fx, ignore_errors=True)


def env(mode='clean', synthetic=True, run=True, extra=True, **kw):
    e = {k: v for k, v in os.environ.items() if not k.startswith(('GMG_', 'V2D_'))}
    e['GMG_MODE'] = mode
    if synthetic:
        e['GMG_DATA_ROOT'] = T['D']
        if run:
            e['GMG_RUN'] = T['RUN']
        if extra:
            e['GMG_EXTRA_DENYLIST'] = T['extra_deny']
    e.update(kw)
    return e


def probe(ops, **kw):
    r = subprocess.run([sys.executable, PROBE], input=json.dumps(ops), capture_output=True, text=True, env=env(**kw),
                       cwd=SCRATCH, timeout=300)
    if r.returncode != 0:
        raise AssertionError(f'probe failed ({r.returncode}): {r.stderr[-3000:]}')
    return json.loads(r.stdout.strip().splitlines()[-1])


class Base(unittest.TestCase):
    def assertStatus(self, res, status):
        bad = [x for x in res if x['status'] != status]
        self.assertFalse(bad, f'expected {status}: ' + json.dumps(bad, default=str)[:3000])


class TestRefusals(Base):
    def test_gt_substrings_refused(self):
        for mode in ('clean', 'dev'):
            res = probe([['open', p, role] for p in T['gt'].values() for role in ('own', 'tracks', 'kit')], mode=mode)
            self.assertStatus(res, 'refused')
            for x in res:
                self.assertIn('path contains', x['msg'])

    def test_real_denylist_globs_refused(self):
        globs = json.load(open(os.path.join(REPO, 'ops', 'provenance', 'denylist.json')))['globs']
        self.assertGreaterEqual(len(globs), 16)
        ops = []
        for g in globs:
            ex = g.replace('*', 'zz')
            ex = os.path.join(REPO, ex) if not ex.startswith('zz') else '/' + ex
            ops.append(['open', ex, 'own'])
            ops.append(['check', ex, 'kit'])
        res = probe(ops)
        self.assertStatus(res, 'refused')

    def test_real_library_and_scan_paths_refused_without_opening(self):
        paths = [f'{REPO}/meshes/library_v{v}/white_pot.glb' for v in (1, 2, 3, 4)] + \
                [f'{REPO}/meshes/library_v3x/beige_cup.glb', f'{SCRATCH}/data/scan/white_pot.glb',
                 f'{SCRATCH}/loc/perc/ep2/poses.npz', f'{MR}/results/prim/meshes/white_pot_lid_ep2_fit_v1.glb']
        res = probe([['check', p, r] for p in paths for r in ('own', 'kit', 'tracks')], synthetic=False)
        self.assertStatus(res, 'refused')

    def test_extra_denylist_sha_and_glob(self):
        res = probe([['open', T['deny_copy'], 'tracks'], ['npz', T['deny_copy'], 'tracks'],
                     ['open', T['glob_hit'], 'tracks']])
        self.assertStatus(res, 'refused')
        self.assertIn('sha256 is on the deny-list', res[0]['msg'])
        self.assertIn('deny-list glob', res[2]['msg'])
        # without the extra list the same file passes: the refusal above came from the sha256 entry only
        res = probe([['open', T['deny_copy'], 'tracks']], extra=False)
        self.assertStatus(res, 'ok')

    def test_env_can_only_add_deny_entries(self):
        empty = T['extra_deny'] + '.empty.json'
        _w(empty, json.dumps(dict(globs=[], sha256={})))
        try:
            res = probe([['deny_sizes'], ['check', f'{REPO}/meshes/library_v2/white_pot.glb', 'own']],
                        V2D_DENYLIST=empty, GMG_EXTRA_DENYLIST=empty)
            self.assertEqual(res[0]['status'], 'ok')
            self.assertGreaterEqual(res[0]['value']['sha256'], 67)
            self.assertGreaterEqual(res[0]['value']['globs'], 16)
            self.assertEqual(res[1]['status'], 'refused')
        finally:
            os.remove(empty)

    def test_refused_folders_clean(self):
        ops = [['open', p, role] for p in T['refused'].values()
               for role in ('own', 'kit', 'tracks', 'weights', 'video')]
        res = probe(ops)
        self.assertStatus(res, 'refused')
        for x in res:
            self.assertTrue('refused folder' in x['msg'] or 'deny-list glob' in x['msg'], x['msg'])

    def test_refused_folders_real_scratchpad(self):
        real = [f'{SCRATCH}/auto/roster/ep0.npz', f'{SCRATCH}/gen/mesh-20261029-gen-f3fbeb0/scores.log',
                f'{SCRATCH}/crops/ep11/beige_cup_crops.json', f'{SCRATCH}/evalcrops/log_ep16_wooden_spoon.txt',
                f'{SCRATCH}/diag/sam-placement/common.py', f'{SCRATCH}/gmg/design/evidence.md',
                f'{SCRATCH}/obs_all/ep26_white_pot.npz', f'{SCRATCH}/obs/ep41_white_pot.npz',
                f'{SCRATCH}/prim/potlid/cand/white_pot_lid_ep2_fit.glb', f'{SCRATCH}/lathe/ep41_white_pot_hyb.glb']
        res = probe([['check', p, r] for p in real for r in ('own', 'kit', 'tracks', 'det')], synthetic=False)
        self.assertStatus(res, 'refused')

    def test_refusal_survives_a_future_allowlist_change(self):
        ops = [['patch_allow', 'own', '{DATA}/**'], ['patch_allow', 'kit', '{DATA}/**']]
        ops += [['open', p, 'own'] for p in T['refused'].values()]
        ops += [['open', p, 'kit'] for p in T['refused'].values()]
        ops += [['open', T['other'], 'own']]                     # the patch itself works on an ordinary file
        res = probe(ops)
        self.assertStatus(res[:2], 'ok')
        self.assertStatus(res[2:-1], 'refused')
        self.assertEqual(res[-1]['status'], 'ok')

    def test_hard_link_copy_refused(self):
        res = probe([['open', T['hl_a'], 'tracks'], ['open', T['hl_b'], 'tracks'], ['npz', T['hl_b'], 'tracks']])
        self.assertStatus(res, 'refused')
        self.assertIn('hard links', res[0]['msg'])

    def test_symlinks_resolved(self):
        res = probe([['open', T['sym_scan'], 'own'], ['open', T['sym_auto'], 'own'], ['check', T['sym_lib'], 'own']])
        self.assertStatus(res, 'refused')

    def test_det_key_filter(self):
        ops = [['npz', T['det'], 'det'], ['npz', T['det'], 'det', ['masks']]]
        ops += [['npz', T['det'], 'det', ['masks', k]] for k in T['det_keys_bad']]
        ops += [['manifest']]
        res = probe(ops)
        self.assertEqual(res[0]['status'], 'ok')
        self.assertEqual(res[0]['value'], sorted(T['det_keys_ok']))
        self.assertEqual(res[1]['value'], ['masks'])
        self.assertStatus(res[2:-1], 'refused')
        rec = [i for i in res[-1]['value']['inputs'] if i['role'] == 'det'][0]
        self.assertEqual(sorted(rec['keys']), sorted(T['det_keys_ok']))
        self.assertEqual(sorted(rec['keys_not_read']), sorted(T['det_keys_bad']))
        self.assertGreaterEqual(len([r for r in res[-1]['value']['refusals'] if r['via'] == 'load_npz']),
                                len(T['det_keys_bad']))

    def test_track_key_filter(self):
        res = probe([['npz', T['tracks_pub'], 'tracks'], ['npz', T['tracks_pub'], 'tracks', ['template_score']]])
        self.assertEqual(res[0]['value'], ['cam_T_white_pot', 'world_T_cam'])
        self.assertEqual(res[1]['status'], 'refused')

    def test_kit_scorer_refused(self):
        res = probe([['open', p, 'kit'] for p in T['kit_scorer']])
        self.assertStatus(res, 'refused')

    def test_dev_roles_refused_in_clean(self):
        res = probe([['open', T['refused']['obs_all'], 'obs_all'], ['open', T['x0_gen'], 'x0_pool'],
                     ['open', T['refused']['prim'], 'fixture'], ['register_fixture_root', os.path.dirname(T['fixture_tmp'])]])
        self.assertStatus(res, 'refused')

    def test_unlisted_and_unknown(self):
        res = probe([['open', T['other'], 'own'], ['open', T['other'], 'kit'], ['open', T['calib'], 'scan'],
                     ['open', T['calib'], 'tracks'], ['open', f'{T["D"]}/data/sweep/ep2/hands.npz', 'tracks']])
        self.assertStatus(res, 'refused')

    def test_expect_sha256(self):
        sha = hashlib.sha256(open(T['calib'], 'rb').read()).hexdigest()
        res = probe([['open', T['calib'], 'calib', {'expect_sha256': sha}],
                     ['open', T['tracks_eval'], 'tracks', {'expect_sha256': '0' * 64}]])
        self.assertEqual(res[0]['status'], 'ok')
        self.assertEqual(res[1]['status'], 'refused')


class TestAllowed(Base):
    def test_every_clean_role_passes(self):
        ops = [['open', T['calib'], 'calib'], ['npz', T['tracks_pub'], 'tracks'], ['npz', T['tracks_eval'], 'tracks'],
               ['npz', T['tracks_run'], 'tracks'], ['open', T['depth_legacy'], 'depth'],
               ['open', T['depth_pub'], 'depth'], ['open', T['depth_eval'], 'depth'],
               ['open', T['video_pub'], 'video'], ['open', T['video_eval'], 'video'], ['open', T['video_hf'], 'video'],
               ['npz', T['det'], 'det'], ['json', T['roster_kit'], 'roster'], ['open', T['kit_cfg'], 'kit'],
               ['open', T['kit_budget'], 'kit'], ['open', T['weights'], 'weights'], ['json', T['own'], 'own'],
               ['manifest']]
        res = probe(ops)
        self.assertStatus(res, 'ok')
        m = res[-1]['value']
        self.assertEqual(m['mode'], 'clean')
        self.assertEqual(m['tier'], 'P1')                       # Phase-1 tracks and default own tier
        self.assertEqual(len(m['inputs']), len(ops) - 1)
        for i in m['inputs']:
            self.assertEqual(i['sha256'], hashlib.sha256(open(i['realpath'], 'rb').read()).hexdigest())
        tiers = {i['role']: i['tier'] for i in m['inputs']}
        self.assertEqual(tiers['calib'], 'P0')
        self.assertEqual(tiers['det'], 'P0')
        self.assertEqual(tiers['tracks'], 'P1')
        self.assertTrue(m['hook']['installed'])
        self.assertRegex(m['commit'] or '', r'^[0-9a-f]{40}$')
        self.assertEqual(m['refusals'], [])

    def test_roster_public_json_allowed(self):
        p = os.path.join(GMG, 'roster_public.json')
        res = probe([['check', p, 'roster']])
        self.assertStatus(res, 'ok')

    def test_own_tier_from_run_tier_json(self):
        rt = _w(os.path.join(T['RUN'], 'run_tier.json'), json.dumps(dict(tier='P0')))
        try:
            res = probe([['json', T['own'], 'own'], ['open', T['calib'], 'calib'], ['tier']])
            self.assertStatus(res, 'ok')
            self.assertEqual(res[-1]['value'], 'P0')
            _w(rt, json.dumps(dict(tier='DEV')))
            res = probe([['json', T['own'], 'own']])
            self.assertStatus(res, 'refused')                     # a clean run never consumes DEV outputs
        finally:
            os.remove(rt)

    def test_dev_mode(self):
        fx = os.path.dirname(T['fixture_tmp'])
        res = probe([['mode'], ['npz', T['refused']['obs_all'], 'obs_all'], ['open', T['x0_gen'], 'x0_pool'],
                     ['register_fixture_root', fx], ['open', T['fixture_tmp'], 'fixture'],
                     ['open', T['refused']['prim'], 'fixture'],             # named fixture, wrong sha prefix
                     ['open', T['refused']['obs_all'], 'own'],               # dev exemption is per role
                     ['open', T['refused']['auto'], 'x0_pool'],              # auto/ is refused in dev mode too
                     ['open', T['refused']['library_v3'], 'x0_pool'],        # deny-list never exempt
                     ['open', T['gt']['/scan'], 'fixture'],
                     ['tier']], mode='dev')
        st = [x['status'] for x in res]
        self.assertEqual(st, ['ok', 'ok', 'ok', 'ok', 'ok', 'refused', 'refused', 'refused', 'refused', 'refused',
                              'ok'], json.dumps(res, default=str)[:3000])
        self.assertEqual(res[0]['value'], 'dev')
        self.assertIn('sha256', res[5]['msg'])
        self.assertEqual(res[-1]['value'], 'DEV')

    def test_mode_default_and_invalid(self):
        e = env()
        e.pop('GMG_MODE')
        r = subprocess.run([sys.executable, PROBE], input='[["mode"]]', capture_output=True, text=True, env=e)
        self.assertEqual(json.loads(r.stdout)[0]['value'], 'clean')
        r = subprocess.run([sys.executable, PROBE], input='[["mode"]]', capture_output=True, text=True,
                           env=env(mode='bogus'))
        self.assertNotEqual(r.returncode, 0)
        self.assertIn('GMG_MODE', r.stderr)

    def test_set_run_rules(self):
        res = probe([['set_run', os.path.join(T['D'], 'gmg', 'runs', 'not-a-run-name')],
                     ['set_run', os.path.join(T['D'], 'elsewhere', RUN_NAME)],
                     ['set_run', T['RUN']]], run=False)
        self.assertEqual([x['status'] for x in res], ['refused', 'refused', 'ok'])
        res = probe([['set_run', os.path.join(T['D'], 'gmg', 'runs', '20261030-other-1234567')]])
        self.assertEqual(res[0]['status'], 'refused')            # the run folder is set once


class TestHook(Base):
    def test_hook_refuses_forbidden_opens(self):
        ops = [['builtin_open', p] for p in T['gt'].values()]
        ops += [['builtin_open', T['refused'][k]] for k in ('auto', 'diag', 'gmg/design', 'crops', 'obs_all',
                                                           'library_v3', 'library_v3x', 'gen/mesh-20261029')]
        ops += [['np_load', T['refused']['obs_all']], ['os_open', T['refused']['obs']],
                ['os_open', T['gt']['/scan']], ['np_load', T['deny_copy'].replace('ep3', 'forbidden_glob_dir')]]
        res = probe(ops)
        self.assertStatus(res, 'refused')

    def test_hook_allows_ordinary_and_code_opens(self):
        res = probe([['builtin_open', T['calib']], ['builtin_open', T['other']], ['builtin_open', T['code_scan']],
                     ['np_load', T['tracks_pub']]])
        self.assertStatus(res, 'ok')
        res = probe([['open', T['code_scan'], 'kit']])             # open_input applies the substrings to code too
        self.assertStatus(res, 'refused')

    def test_hook_dev_admitted_only(self):
        p = T['refused']['obs_all']
        res = probe([['builtin_open', p], ['open', p, 'obs_all'], ['builtin_open', p], ['np_load', p]], mode='dev')
        self.assertEqual([x['status'] for x in res], ['refused', 'ok', 'ok', 'ok'])


class TestConstants(Base):
    def test_constants(self):
        ops = [['constant', 'vote_voxel_m', 0.004, 'generic'],
               ['constant', 'remesh_pitch_m', 0.0015, 'sensor'],
               ['constant', 'face_budget', 4000, 'kit'],
               ['constant', 'class_order', ['STRUCT', 'FUSE', 'GEN', 'SHELL', 'HULL'], 'informed:[D] hand kits'],
               ['constant', 't0_mm', 2.5, 'fallback:scan-coincident (brief leak), PREREG A.6'],
               ['constant', 'tau_v3', 0.2, 'fitted:own CPU fold-rebuild null q99'],
               ['constant', 'ball_r_mm', 7.0, 'fitted:own B.4 consensus'],
               ['constant', 'vote_voxel_m', 0.004, 'generic'],                   # same value again: fine
               ['constants']]
        res = probe(ops)
        self.assertStatus(res, 'ok')
        cs = {c['name']: c for c in res[-1]['value']}
        self.assertEqual(len(cs), 7)
        self.assertTrue(all(c['where'] for c in cs.values()))
        bad = [['constant', 'x', 1, 'made-up'], ['constant', 'x', 1, 'fitted'], ['constant', 'x', 1, 'fitted: '],
               ['constant', 'x', 1, 'fitted:scan wall median'], ['constant', 'y', 1, 'fitted:library_v3 extents'],
               ['constant', 'ball_r_mm', 7.0, 'generic'], ['constant', 'ball_radius_m', 0.007, 'informed'],
               ['constant', 'thickness_default_mm', 2.5, 'generic'], ['constant', 'tau_v3', 0.2, 'informed'],
               ['constant', 'vote_voxel_m', 0.004, 'generic'], ['constant', 'vote_voxel_m', 0.005, 'generic'],
               ['constant', 'bad name', 1, 'generic'], ['constant_set', 'z', [1, 2], 'generic']]
        res = probe(bad)
        self.assertNotIn('ok', [x['status'] for i, x in enumerate(res) if i != 9], json.dumps(res)[:3000])
        self.assertEqual(res[9]['status'], 'ok')
        self.assertIn('already', res[10]['msg'])


class TestIoGt(Base):
    def test_mesh_roots_dropped(self):
        sys.path.insert(0, MR)
        try:
            from autokit import io_gt
        finally:
            sys.path.remove(MR)
        dropped = [f'{io_gt.SCRATCH}/auto', f'{REPO}/meshes/library_v3', f'{MR}/results/prim/meshes',
                   f'{io_gt.SCRATCH}/prim', f'{io_gt.SCRATCH}/lathe']
        for r in dropped:
            self.assertNotIn(r, io_gt.ROOTS['mesh'])
            for k, v in io_gt.ROOTS.items():
                self.assertNotIn(r, v, k)
        self.assertNotIn('library_v3', json.dumps(io_gt.ROOTS))

    def test_io_gt_denylist(self):
        lib = f'{REPO}/meshes/library_v3/white_pot.glb'
        res = probe([['io_gt', 'check_path', [lib]], ['io_gt', 'load_mesh', [lib]],
                     ['io_gt', 'check_path', [f'{REPO}/meshes/library_v2/white_pot.glb']],
                     ['io_gt', 'mesh_input', [f'{SCRATCH}/lathe/ep41_white_pot_hyb.glb']],
                     ['io_gt', 'mesh_input', [f'{SCRATCH}/auto/roster/ep0.npz']]], synthetic=False)
        self.assertStatus(res, 'refused')
        self.assertIn('deny-list glob', res[0]['msg'])

    def test_io_gt_deny_sha(self):
        # io_gt reads the deny-list through pipeline/provenance.py; V2D_DENYLIST adds the synthetic sha256
        dl = json.load(open(os.path.join(REPO, 'ops', 'provenance', 'denylist.json')))
        dl['sha256'][T['deny_copy_sha']] = 'test: synthetic denied file'
        p = T['extra_deny'] + '.v2d.json'
        _w(p, json.dumps(dl))
        try:
            res = probe([['io_gt', 'check_path', [T['deny_copy']]]], synthetic=False, V2D_DENYLIST=p)
            self.assertStatus(res, 'refused')
            self.assertIn('sha256 on the deny-list', res[0]['msg'])
            res = probe([['io_gt', 'check_path', [T['deny_copy']]]], synthetic=False)
            self.assertStatus(res, 'ok')
        finally:
            os.remove(p)

    def test_gmg_refuses_io_gt_roots_not_on_allowlist(self):
        obs = f'{SCRATCH}/obs_all/ep26_white_pot.npz'
        res = probe([['io_gt', 'check_input', [obs, 'obs']], ['io_gt', 'load_obs', [obs]], ['roots_report'],
                     ['io_gt', 'load_poses', [2]], ['manifest']], synthetic=False)
        self.assertEqual([x['status'] for x in res], ['refused', 'refused', 'ok', 'ok', 'ok'],
                         json.dumps(res, default=str)[:3000])
        self.assertIn('io_gt root not on the gmg allow-list', res[0]['msg'])
        rep = res[2]['value']
        for root, v in rep['obs'].items():
            if root.endswith(('/obs_all', '/obs', '/auto/stage1/refined')):
                self.assertTrue(v.startswith('refused'), (root, v))
        self.assertTrue(all(v.startswith('refused') for v in rep['corr'].values()))
        self.assertTrue(all(v.startswith('allowed') for v in rep['poses'].values()), rep['poses'])
        roles = {i['role'] for i in res[-1]['value']['inputs']}
        self.assertEqual(roles, {'tracks'})                      # io_gt's read went into the gmg manifest

    def test_dev_mode_io_gt_obs_all(self):
        obs = f'{SCRATCH}/obs_all/ep26_white_pot.npz'
        res = probe([['io_gt', 'load_obs', [obs]], ['manifest']], synthetic=False, mode='dev')
        self.assertStatus(res, 'ok')
        self.assertEqual({i['role'] for i in res[-1]['value']['inputs']}, {'obs_all'})
        self.assertEqual(res[-1]['value']['tier'], 'DEV')


@unittest.skipUnless(shutil.which('strace'), 'strace not installed')
class TestStrace(Base):
    def test_dummy_clean_run_zero_forbidden_opens(self):
        import datetime
        day = datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%d')
        commit = subprocess.run(['git', '-C', REPO, 'rev-parse', '--short=7', 'HEAD'], capture_output=True,
                                text=True).stdout.strip()
        run = os.path.join(SCRATCH, 'gmg', 'runs', f'{day}-b0test-{commit}')
        shutil.rmtree(run, ignore_errors=True)
        log = os.path.join(SCRATCH, 'gmg', 'audit', f'b0test-{commit}.strace')
        e = env(synthetic=False)
        r = subprocess.run([sys.executable, AUDIT, 'run', '--log', log, '--manifest', os.path.join(run, 'manifest.json'),
                            '--', sys.executable, DUMMY, '--tag', 'b0test'], capture_output=True, text=True, env=e,
                           cwd='/tmp', timeout=900)
        rep = json.load(open(log + '.audit.json'))
        dummy = json.load(open(os.path.join(run, 'dummy_result.json')))
        self.assertTrue(dummy['pass'], json.dumps(dummy['unexpected'])[:3000])
        self.assertGreaterEqual(len(dummy['refused']), 40)
        self.assertEqual(rep['forbidden_opens'], 0, json.dumps(rep['forbidden'] + rep['unlisted'])[:3000])
        self.assertEqual(rep['returncode'], 0, r.stdout[-2000:] + r.stderr[-2000:])
        self.assertGreater(rep['events'], 500)
        self.assertGreaterEqual(len(rep['data_reads']), 5)
        T['strace_report'] = dict(log=log, run=run, events=rep['events'], data_reads=len(rep['data_reads']),
                                  refused=len(dummy['refused']), allowed=len(dummy['allowed']))

    def test_audit_detects_unguarded_opens(self):
        """Negative control: an unguarded process that reads GT-pattern, refused, deny-sha and unlisted files is
        caught by the auditor (so 0 above means 0, not a blind auditor)."""
        script = _w(os.path.join(os.path.dirname(T['D']), f'unguarded_{os.path.basename(T["D"])}.py'),
                    'import sys\nfor p in sys.argv[1:]:\n    open(p, "rb").read(1)\n')
        files = [T['gt']['/scan'], T['refused']['auto'], T['refused']['obs_all'], T['deny_copy'], T['other']]
        log = os.path.join(os.path.dirname(T['D']), f'neg_{os.path.basename(T["D"])}.strace')
        try:
            r = subprocess.run([sys.executable, AUDIT, 'run', '--log', log, '--', sys.executable, '-I', script, *files],
                               capture_output=True, text=True, env=env(), cwd='/tmp', timeout=300)
            rep = json.load(open(log + '.audit.json'))
            self.assertNotEqual(r.returncode, 0)
            hit = {f['rpath'] or f['path'] for f in rep['forbidden']} | {f['rpath'] or f['path'] for f in rep['unlisted']}
            for f in files:
                self.assertIn(f, hit, json.dumps(rep, default=str)[:3000])
            self.assertEqual(rep['forbidden_opens'], len(files))
        finally:
            for p in (script, log, log + '.audit.json'):
                if os.path.exists(p):
                    os.remove(p)


if __name__ == '__main__':
    unittest.main(verbosity=2)
