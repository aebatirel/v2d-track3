"""B0 tests of gmg/guard.py, the autokit/io_gt.py fix and the strace audit (SPEC section 24, step B0; round 2).

  python docs/research/mesh-2026-10-26/gmg/tests/test_guard.py        (venv python: numpy is needed)

Pass condition (SPEC section 24, B0): every deny path, glob, sha256, refused folder, refused det key and hard-link copy
raises; the allowed roles pass; the strace of a dummy clean-mode run shows 0 forbidden opens. Round 2 adds the
verification-round-1 cases: the det key filter by file identity (bypasses a-d), dev outputs never entering a clean run
(run markers), the auditor's former blind spots (system prefixes, O_RDWR, writes outside the run) and the dir_fd
open. Round 3 adds the verification-round-2 cases: dev outputs moved into a clean run by os.replace / os.rename /
shutil.move / os.link / os.symlink and a self-written marker (both probes), the run provenance ledger, removals and
other runs, a+b opens, the HF dataset scans, hard-link reads, kit scorer imports, the private door flags, process
arguments and URLs, the frozen eval tracks, and the auditor's pid attribution (a pid that ends by exec'ing git), git's
own reads, renames, links, symlinks, network connections and manifest outputs.

The guard reads its configuration once at import, so every scenario runs in a fresh interpreter (guard_probe.py) with
GMG_DATA_ROOT pointing at a synthetic tree built here (in the session scratchpad). The synthetic files hold made-up
bytes; no scan, library mesh, parquet or mocap content is created or read. The one real det dump used (det copy via
the committed registry) is copied byte for byte by this runner and read by the guarded probe through its mask keys
only. Checks on real repository and scratchpad paths use guard.check (path rules only), so a refused real file is never
opened. The test runner itself does not import gmg.guard (its open hook would refuse the creation of the synthetic
"scan" files).
"""
import hashlib
import json
import os
import re
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
REAL_DET = os.path.join(SCRATCH, 'data', 'store', 'ep2', 'det_f0.npz')
REAL_EVAL1 = os.path.join(SCRATCH, 'data', 'eval', 'ep1', 'poses.npz')
T = {}                                                   # the synthetic tree
REFUSAL_REASONS = ('deny-list glob', 'path contains', 'refused folder')


def _w(path, data=b'x'):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'wb') as f:
        f.write(data if isinstance(data, bytes) else data.encode())
    return path


def _npz(path, **arrs):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    np.savez(path, **arrs)
    return path


def _json(path):
    with open(path) as f:
        return json.load(f)


def _bytes(path):
    with open(path, 'rb') as f:
        return f.read()


def _marker(run, mode='clean', tier='P1', **kw):
    """A run marker as set_run writes it (run name and root bound to the folder); KW overrides fields."""
    body = dict(mode=mode, tier=tier, run=os.path.basename(run), root=os.path.basename(os.path.dirname(run)), **kw)
    return _w(os.path.join(run, 'run_tier.json'), json.dumps({k: v for k, v in body.items() if v is not None}))


def _sha(path):
    return hashlib.sha256(_bytes(path)).hexdigest()


def _ledger(run, paths, mode='clean', name=None, sha=None):
    """Append ledger lines (RUN/outputs.jsonl) for PATHS, as write_manifest of a clean guarded process of this run
    would. Test setup only: this runner is not guarded, so it stands in for the process that wrote the fixtures."""
    with open(os.path.join(run, 'outputs.jsonl'), 'a') as f:
        for p in paths:
            rel = os.path.relpath(os.path.realpath(p), os.path.realpath(run))
            f.write(json.dumps(dict(path=rel, sha256=sha or _sha(p), bytes=os.path.getsize(p), how='test-fixture',
                                    run=name or os.path.basename(run), mode=mode, pid=0, manifest=None)) + '\n')


def setUpModule():
    base = os.path.join(SCRATCH, 'gmgtest')
    os.makedirs(base, exist_ok=True)
    D = tempfile.mkdtemp(prefix='tree-', dir=base)
    T['D'] = D
    T['RUN'] = os.path.join(D, 'gmg', 'runs', RUN_NAME)
    T['RUN_DEV'] = os.path.join(D, 'gmg', 'runs-dev', RUN_NAME)
    _marker(T['RUN'])                                     # an existing clean run folder (marker first)
    _marker(T['RUN_DEV'], 'dev', 'DEV')
    K = os.path.join(D, 'kit', 'v2d_submission_kit')
    T['K'] = K
    I4 = np.tile(np.eye(4), (3, 1, 1))
    T['calib'] = _w(f'{D}/data/calib.json', json.dumps(dict(stereo_pairs=[dict(camera='ego')])))
    T['tracks_pub'] = _npz(f'{D}/data/sweep/ep2/poses.npz', world_T_cam=I4, cam_T_white_pot=I4, template_score=np.ones(3))
    T['tracks_eval'] = f'{D}/data/eval/ep1/poses.npz'      # a byte copy of the frozen eval ep1 track (SPEC 17)
    if os.path.isfile(REAL_EVAL1):
        os.makedirs(os.path.dirname(T['tracks_eval']), exist_ok=True)
        shutil.copyfile(REAL_EVAL1, T['tracks_eval'])
    else:
        _npz(T['tracks_eval'], world_T_cam=I4, cam_T_white_pot=I4)
    T['tracks_eval_bad'] = _npz(f'{D}/data/eval/ep3/poses.npz', world_T_cam=I4, cam_T_white_pot=I4)
    T['tracks_eval_unknown'] = _npz(f'{D}/data/eval/ep99/poses.npz', world_T_cam=I4, cam_T_white_pot=I4)
    T['tracks_run'] = _npz(f'{T["RUN"]}/tracks/ep2/poses.npz', world_T_cam=I4, cam_T_white_pot=I4)
    T['det_keys_ok'] = ['K', 'depth', 'frame', 'image', 'mask_shape', 'masks', 'names']
    T['det_keys_bad'] = ['sim', 'score', 'score_rules', 'gdino', 'template_extent', 'template_intensity', 'chosen',
                         'verify', 'verify_matched', 'rules', 'params', 'reprop', 'centroid', 'area', 'intensity',
                         'extent', 'extent_eroded']
    det = {k: np.zeros(2) for k in T['det_keys_ok'] + T['det_keys_bad']}
    det['gdino'] = np.array('[]')
    T['det'] = _npz(f'{D}/data/store/ep2/det_f0.npz', **det)
    # det copies made outside the guard (this runner is not guarded): a byte copy with an innocent name, a re-saved
    # copy (other bytes, same keys), and an own bundle that shares one key name with a det dump (not a det file)
    T['det_copy'] = f'{T["RUN"]}/bundle/det_copy.npz'
    os.makedirs(os.path.dirname(T['det_copy']), exist_ok=True)
    shutil.copyfile(T['det'], T['det_copy'])
    T['det_resaved'] = _npz(f'{T["RUN"]}/bundle/resaved.npz', **{k: np.ones(3) for k in det})
    T['bundle_ok'] = _npz(f'{T["RUN"]}/bundle/bundle_ok.npz', pts=np.zeros((2, 3)), verify=np.ones(2), area=np.ones(2))
    if os.path.isfile(REAL_DET):                           # byte copy of a real dump: caught by det_registry.json
        T['real_det_copy'] = f'{T["RUN"]}/bundle/innocent_real.bin'
        shutil.copyfile(REAL_DET, T['real_det_copy'])
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
    sha = hashlib.sha256(_bytes(T['deny_copy'])).hexdigest()
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
    # the RUN fixtures a clean guarded process of this run would have written (det copies included, so the det key
    # filter is tested on files that pass the run provenance check)
    _ledger(T['RUN'], [T[k] for k in ('tracks_run', 'det_copy', 'det_resaved', 'bundle_ok', 'own', 'real_det_copy')
                       if k in T])
    # HF dataset layout (synthetic bytes): public scans and URDFs under hfds/track_3/public/{mesh,urdf}
    T['hf_mesh'] = _w(f'{D}/hfds/track_3/public/mesh/white_pot/white_pot.glb')
    T['hf_urdf'] = _w(f'{D}/hfds/track_3/public/urdf/white_pot.urdf')
    T['hf_meta'] = _w(f'{D}/hfds/track_3/public/meta/info.json', '{}')


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
            e['GMG_RUN'] = T['RUN_DEV'] if mode == 'dev' else T['RUN']
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


def probe_raw(ops, **kw):
    """(returncode, stdout, stderr) of a probe whose import may fail (root checks)."""
    r = subprocess.run([sys.executable, PROBE], input=json.dumps(ops), capture_output=True, text=True, env=env(**kw),
                       cwd=SCRATCH, timeout=300)
    return r.returncode, r.stdout, r.stderr


class Base(unittest.TestCase):
    def assertStatus(self, res, status):
        bad = [x for x in res if x['status'] != status]
        self.assertFalse(bad, f'expected {status}: ' + json.dumps(bad, default=str)[:3000])

    def assertReason(self, res, reasons=REFUSAL_REASONS):
        """Every result is refused by one of REASONS (not merely by the role allow-list)."""
        for x in res:
            self.assertEqual(x['status'], 'refused', json.dumps(x, default=str)[:1000])
            self.assertTrue(any(r in x['msg'] for r in reasons), (reasons, x['msg']))


class TestRefusals(Base):
    def test_gt_substrings_refused(self):
        for mode in ('clean', 'dev'):
            res = probe([['open', p, role] for p in T['gt'].values() for role in ('own', 'tracks', 'kit')], mode=mode)
            self.assertReason(res, ('path contains',))

    def test_real_denylist_globs_refused(self):
        globs = _json(os.path.join(REPO, 'ops', 'provenance', 'denylist.json'))['globs']
        self.assertGreaterEqual(len(globs), 16)
        ops = []
        for g in globs:
            ex = g.replace('*', 'zz')
            ex = os.path.join(REPO, ex) if not ex.startswith('zz') else '/' + ex
            ops.append(['open', ex, 'own'])
            ops.append(['check', ex, 'kit'])
        res = probe(ops)
        self.assertReason(res, ('deny-list glob', 'path contains'))      # never the allow-list alone

    def test_real_library_and_scan_paths_refused_without_opening(self):
        lib = [f'{REPO}/meshes/library_v{v}/white_pot.glb' for v in (1, 2, 3, 4)] + \
              [f'{REPO}/meshes/library_v3x/beige_cup.glb', f'{MR}/results/prim/meshes/white_pot_lid_ep2_fit_v1.glb']
        gt = [f'{SCRATCH}/data/scan/white_pot.glb', f'{SCRATCH}/loc/perc/ep2/poses.npz']
        res = probe([['check', p, r] for p in lib for r in ('own', 'kit', 'tracks')], synthetic=False)
        self.assertReason(res, ('deny-list glob', 'refused folder'))
        res = probe([['check', p, r] for p in gt for r in ('own', 'kit', 'tracks')], synthetic=False)
        self.assertReason(res, ('path contains',))

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
            self.assertReason(res[1:], ('deny-list glob', 'refused folder'))
        finally:
            os.remove(empty)

    def test_refused_folders_clean(self):
        ops = [['open', p, role] for p in T['refused'].values()
               for role in ('own', 'kit', 'tracks', 'weights', 'video')]
        res = probe(ops)
        self.assertReason(res, ('refused folder', 'deny-list glob'))

    def test_refused_folders_real_scratchpad(self):
        real = [f'{SCRATCH}/auto/roster/ep0.npz', f'{SCRATCH}/gen/mesh-20261029-gen-f3fbeb0/scores.log',
                f'{SCRATCH}/crops/ep11/beige_cup_crops.json', f'{SCRATCH}/evalcrops/log_ep16_wooden_spoon.txt',
                f'{SCRATCH}/diag/sam-placement/common.py', f'{SCRATCH}/gmg/design/evidence.md',
                f'{SCRATCH}/obs_all/ep26_white_pot.npz', f'{SCRATCH}/obs/ep41_white_pot.npz',
                f'{SCRATCH}/prim/potlid/cand/white_pot_lid_ep2_fit.glb', f'{SCRATCH}/lathe/ep41_white_pot_hyb.glb']
        for synthetic in (False, True):       # True: a non-default GMG_DATA_ROOT; the **/scratchpad/... rules hold
            res = probe([['check', p, r] for p in real for r in ('own', 'kit', 'tracks', 'det')], synthetic=synthetic)
            self.assertReason(res, ('refused folder', 'deny-list glob'))

    def test_refusal_survives_a_future_allowlist_change(self):
        ops = [['patch_allow', 'own', '{DATA}/**'], ['patch_allow', 'kit', '{DATA}/**']]
        ops += [['open', p, 'own'] for p in T['refused'].values()]
        ops += [['open', p, 'kit'] for p in T['refused'].values()]
        ops += [['open', T['other'], 'own']]                     # the patch itself works on an ordinary file
        res = probe(ops)
        self.assertStatus(res[:2], 'ok')
        self.assertReason(res[2:-1], ('refused folder', 'deny-list glob'))
        self.assertEqual(res[-1]['status'], 'ok')

    def test_hard_link_copy_refused(self):
        res = probe([['open', T['hl_a'], 'tracks'], ['open', T['hl_b'], 'tracks'], ['npz', T['hl_b'], 'tracks']])
        self.assertReason(res, ('hard links',))

    def test_symlinks_resolved(self):
        res = probe([['open', T['sym_scan'], 'own'], ['open', T['sym_auto'], 'own'], ['check', T['sym_lib'], 'own']])
        self.assertReason(res)

    def test_track_key_filter(self):
        res = probe([['npz', T['tracks_pub'], 'tracks'], ['npz', T['tracks_pub'], 'tracks', ['template_score']]])
        self.assertEqual(res[0]['value'], ['cam_T_white_pot', 'world_T_cam'])
        self.assertEqual(res[1]['status'], 'refused')

    def test_kit_scorer_refused(self):
        res = probe([['open', p, 'kit'] for p in T['kit_scorer']])
        self.assertReason(res, ('kit scorer is excluded',))

    def test_dev_roles_refused_in_clean(self):
        res = probe([['open', T['refused']['obs_all'], 'obs_all'], ['open', T['x0_gen'], 'x0_pool'],
                     ['open', T['refused']['prim'], 'fixture'], ['register_fixture_root', os.path.dirname(T['fixture_tmp'])]])
        self.assertStatus(res, 'refused')

    def test_unlisted_and_unknown(self):
        res = probe([['open', T['other'], 'own'], ['open', T['other'], 'kit'], ['open', T['calib'], 'scan'],
                     ['open', T['calib'], 'tracks'], ['open', f'{T["D"]}/data/sweep/ep2/hands.npz', 'tracks']])
        self.assertStatus(res, 'refused')

    @unittest.skipUnless(os.path.isfile(REAL_EVAL1), 'no local eval track')
    def test_frozen_eval_tracks(self):
        """SPEC section 17: eval tracks must equal the frozen store run (gmg/frozen_eval_tracks.json); with the
        registry absent a clean run refuses them (fail closed), a dev run notes it."""
        res = probe([['npz', T['tracks_eval'], 'tracks'], ['npz', T['tracks_eval_bad'], 'tracks'],
                     ['open', T['tracks_eval_unknown'], 'tracks'], ['manifest']])
        self.assertEqual([x['status'] for x in res], ['ok', 'refused', 'refused', 'ok'], json.dumps(res)[:2000])
        self.assertIn('!= frozen', res[1]['msg'])
        self.assertIn('is not in', res[2]['msg'])
        res = probe([['patch_frozen', '/nonexistent/frozen_eval_tracks.json'], ['open', T['tracks_eval'], 'tracks']])
        self.assertReason(res[1:], ('registry',))
        res = probe([['patch_frozen', '/nonexistent/frozen_eval_tracks.json'], ['open', T['tracks_eval'], 'tracks'],
                     ['manifest']], mode='dev')
        self.assertStatus(res, 'ok')
        reg = _json(os.path.join(GMG, 'frozen_eval_tracks.json'))
        self.assertEqual(len(reg['files']), 20)
        self.assertEqual(set(reg['local_check'].values()), {'match'})

    def test_expect_sha256(self):
        sha = hashlib.sha256(_bytes(T['calib'])).hexdigest()
        res = probe([['open', T['calib'], 'calib', {'expect_sha256': sha}],
                     ['open', T['tracks_eval'], 'tracks', {'expect_sha256': '0' * 64}], ['manifest']])
        self.assertEqual(res[0]['status'], 'ok')
        self.assertEqual(res[1]['status'], 'refused')


class TestDetIdentity(Base):
    """The det_f0.npz key filter follows the file, not the role (verification round 1, bypasses a-d)."""

    def test_det_key_filter(self):
        ops = [['npz', T['det'], 'det'], ['npz', T['det'], 'det', ['masks']]]
        ops += [['npz', T['det'], 'det', ['masks', k]] for k in T['det_keys_bad']]
        ops += [['manifest']]
        res = probe(ops)
        self.assertEqual(res[0]['status'], 'ok')
        self.assertEqual(res[0]['value'], sorted(T['det_keys_ok']))
        self.assertEqual(res[1]['value'], ['masks'])
        self.assertReason(res[2:-1], ('refused det keys',))
        rec = [i for i in res[-1]['value']['inputs'] if i['role'] == 'det'][0]
        self.assertEqual(sorted(rec['keys']), sorted(T['det_keys_ok']))
        self.assertEqual(sorted(rec['keys_not_read']), sorted(T['det_keys_bad']))
        self.assertGreaterEqual(len([r for r in res[-1]['value']['refusals'] if r['via'] == 'load_npz']),
                                len(T['det_keys_bad']))

    def test_a_det_only_through_load_npz(self):
        d = T['det']
        res = probe([['open', d, 'det'], ['np_load', d], ['builtin_open', d], ['os_open', d],
                     ['dirfd_open', os.path.dirname(d), 'det_f0.npz'], ['npz', d, 'det'], ['manifest']])
        self.assertReason(res[:1], ('read through guard.load_npz only',))
        self.assertReason(res[1:5], ('opened only inside guard.load_npz',))
        self.assertEqual(res[5]['value'], sorted(T['det_keys_ok']))
        m = res[-1]['value']
        self.assertGreaterEqual(m['guarded_opens'].get(os.path.realpath(d), 0), 2)       # hash + np.load
        self.assertEqual(len([r for r in m['refusals'] if r['via'] == 'hook']), 4)

    def test_b_copies(self):
        c, rs, ok = T['det_copy'], T['det_resaved'], T['bundle_ok']
        res = probe([['copyfile', T['det'], f'{T["RUN"]}/bundle/c2.npz'],      # in-process copy: hook
                     ['open', c, 'own'], ['np_load', c], ['builtin_open', c],
                     ['npz', c, 'own'], ['npz', c, 'own', ['masks', 'sim']],
                     ['npz', rs, 'own'], ['npz', rs, 'own', ['chosen']], ['np_load', rs], ['open', rs, 'own'],
                     ['npz', ok, 'own'], ['manifest']])
        self.assertReason(res[:1], ('opened only inside guard.load_npz',))
        self.assertFalse(os.path.exists(f'{T["RUN"]}/bundle/c2.npz'))
        self.assertReason(res[1:4], ('copy of a det file',))
        self.assertEqual(res[4]['value'], sorted(T['det_keys_ok']))
        self.assertReason(res[5:6], ('refused own keys',))
        self.assertEqual(res[6]['value'], sorted(T['det_keys_ok']))
        self.assertReason(res[7:8], ('refused own keys',))
        self.assertReason(res[8:10], ('det signature keys',))
        self.assertEqual(res[10]['value'], ['area', 'pts', 'verify'])             # one shared name: not a det file
        recs = {i['realpath']: i for i in res[-1]['value']['inputs']}
        self.assertEqual(recs[os.path.realpath(c)]['key_filter'], 'det')
        self.assertEqual(recs[os.path.realpath(rs)]['key_filter'], 'det')
        self.assertNotIn('key_filter', recs[os.path.realpath(ok)])
        # a fresh process whose first act is to load the copy (the original's sha256 is hashed lazily)
        res = probe([['npz', c, 'own', ['sim']], ['npz', c, 'own']])
        self.assertReason(res[:1], ('copy of a det file',))
        self.assertEqual(res[1]['value'], sorted(T['det_keys_ok']))

    @unittest.skipUnless(os.path.isfile(REAL_DET), 'no local det dump')
    def test_b_real_det_copy_via_registry(self):
        c = T['real_det_copy']
        res = probe([['npz', c, 'own', ['masks', 'sim']], ['np_load', c], ['open', c, 'own'], ['npz', c, 'own']])
        self.assertReason(res[:3], ('det registry',))
        self.assertEqual(res[3]['value'], sorted(T['det_keys_ok']))

    def test_c_future_allowlist_change(self):
        d = T['det']
        res = probe([['patch_allow', 'weights', '{DATA}/**'], ['patch_allow', 'own', '{DATA}/**'],
                     ['npz', d, 'weights', ['masks', 'sim', 'chosen']], ['npz', d, 'weights'],
                     ['npz', d, 'own', ['template_extent']], ['npz', d, 'own'], ['open', d, 'weights']])
        self.assertStatus(res[:2], 'ok')
        self.assertReason(res[2:3], ('refused weights keys',))
        self.assertEqual(res[3]['value'], sorted(T['det_keys_ok']))
        self.assertReason(res[4:5], ('refused own keys',))
        self.assertEqual(res[5]['value'], sorted(T['det_keys_ok']))
        self.assertReason(res[6:7], ('read through guard.load_npz only',))

    def test_d_kit_and_weights_roots(self):
        D = T['D']
        bad = dict(GMG_KIT_ROOT=[f'{D}/data', D, f'{D}/data/store', REPO, f'{D}/gmg/runs', f'{D}/gmg', f'{D}/auto',
                                 f'{D}/auto/x', '/', f'{D}/cache/depth', f'{D}/gmg/runs-dev', os.path.dirname(D)],
                   GMG_WEIGHTS_ROOT=[f'{D}/data', f'{REPO}/meshes', f'{D}/obs_all', f'{D}/gmg/runs-dev', f'{D}/diag',
                                     f'{D}/cache'])
        for var, roots in bad.items():
            for r in roots:
                rc, out, err = probe_raw([['npz', T['det'], 'kit']], **{var: r})
                self.assertNotEqual(rc, 0, (var, r, out[-500:]))
                self.assertIn(f'refused {var}', err, (var, r))
        rc, out, err = probe_raw([['mode']], GMG_KIT_ROOT=f'{D}/kit/v2d_submission_kit', GMG_WEIGHTS_ROOT=f'{D}/w2')
        self.assertEqual(rc, 0, err[-1000:])


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
        self.assertEqual(m['tier'], 'P1')                       # Phase-1 tracks and the clean run marker
        self.assertEqual(len(m['inputs']), len(ops) - 1)
        for i in m['inputs']:
            self.assertEqual(i['sha256'], hashlib.sha256(_bytes(i['realpath'])).hexdigest())
        tiers = {i['role']: i['tier'] for i in m['inputs']}
        self.assertEqual(tiers['calib'], 'P0')
        self.assertEqual(tiers['det'], 'P0')
        self.assertEqual(tiers['tracks'], 'P1')
        self.assertEqual(tiers['own'], 'P1')
        self.assertTrue(m['hook']['installed'])
        self.assertRegex(m['commit'] or '', r'^[0-9a-f]{40}$')
        self.assertEqual(m['refusals'], [])
        self.assertEqual(m['run_marker']['mode'], 'clean')
        ev = [i for i in m['inputs'] if i['realpath'] == os.path.realpath(T['tracks_eval'])][0]
        self.assertIn('checked against', ev['frozen_sha'])     # the synthetic ep1 track equals the frozen sha256
        self.assertIn('docs/research/mesh-2026-10-26/scripts', m['code_dirs'])

    def test_roster_public_json_allowed(self):
        p = os.path.join(GMG, 'roster_public.json')
        res = probe([['check', p, 'roster']])
        self.assertStatus(res, 'ok')

    def test_run_markers(self):
        mk = os.path.join(T['RUN'], 'run_tier.json')
        try:
            _marker(T['RUN'], 'clean', 'P0')                    # e.g. a Phase-2 run: own files P0
            res = probe([['json', T['own'], 'own'], ['open', T['calib'], 'calib'], ['tier']])
            self.assertStatus(res, 'ok')
            self.assertEqual(res[-1]['value'], 'P0')
            nm = os.path.basename(T['RUN'])
            cases = [(json.dumps(dict(mode='clean', tier='DEV', run=nm, root='runs')), 'tier DEV'),
                     (json.dumps(dict(mode='dev', tier='DEV', run=nm, root='runs-dev')), 'outside the dev run root'),
                     (json.dumps(dict(mode='dev', tier='P1', run=nm, root='runs-dev')), 'dev marker with tier'),
                     (json.dumps(dict(mode='clean', tier='P1')), 'copied or moved marker'),          # round-2 form
                     (json.dumps(dict(mode='clean', tier='P1', run='20261030-other-0000000', root='runs')),
                      'copied or moved marker'),
                     (json.dumps(dict(mode='clean', tier='P1', run=nm, root='runs-dev')), 'copied or moved marker'),
                     ('{not json', 'unreadable marker'), (None, 'without run_tier.json')]
            for body, why in cases:
                if body is None:
                    os.remove(mk)
                else:
                    _w(mk, body)
                res = probe([['set_run', T['RUN']], ['check', T['own'], 'own']], run=False)
                self.assertReason(res[:1], (why,))
                self.assertStatus(res[1:], 'refused')            # no run folder set: own admits nothing
        finally:
            _marker(T['RUN'])

    def test_dev_outputs_never_enter_a_clean_run(self):
        """Verification round 1: a dev process writes a bundle from obs_all; a clean process must never take it as
        P1. Dev runs live under gmg/runs-dev with a DEV marker; clean set_run refuses that root, a folder without a
        marker and a DEV marker."""
        D = T['D']
        name = '20261030-devx-0000000'
        dev_run, clean_twin = f'{D}/gmg/runs-dev/{name}', f'{D}/gmg/runs/{name}'
        out = f'{dev_run}/bundle/ep2_white_pot.npz'
        res = probe([['set_run', clean_twin]], mode='dev', run=False)
        self.assertReason(res, ('must be',))                                # dev may not use the clean root
        res = probe([['write', f'{clean_twin}/bundle/x.json']], mode='dev', run=False)
        self.assertReason(res, ('write under the clean run root',))         # nor write into it without set_run
        res = probe([['set_run', dev_run], ['npz', T['refused']['obs_all'], 'obs_all'], ['write', out],
                     ['own_tier'], ['tier'], ['manifest']], mode='dev', run=False)
        self.assertStatus(res, 'ok')
        self.assertEqual(res[3]['value'], 'DEV')
        self.assertEqual(res[4]['value'], 'DEV')
        self.assertEqual(_json(f'{dev_run}/run_tier.json')['tier'], 'DEV')
        res = probe([['set_run', dev_run], ['check', out, 'own']], run=False)
        self.assertReason(res[:1], ('must be',))
        self.assertStatus(res[1:], 'refused')
        # the dev outputs copied into the clean root by an unguarded process: no marker, then a copied DEV marker
        os.makedirs(f'{clean_twin}/bundle', exist_ok=True)
        shutil.copyfile(out, f'{clean_twin}/bundle/ep2_white_pot.npz')
        res = probe([['set_run', clean_twin]], run=False)
        self.assertReason(res, ('without run_tier.json',))
        shutil.copyfile(f'{dev_run}/run_tier.json', f'{clean_twin}/run_tier.json')
        res = probe([['set_run', clean_twin]], run=False)
        self.assertReason(res, ('outside the dev run root',))
        # a clean run whose marker disappears after set_run: own files are DEV (never P1) and refused
        fresh = f'{D}/gmg/runs/20261030-fresh-0000000'
        res = probe([['set_run', fresh], ['write', f'{fresh}/bundle/n.json', '{}'], ['json', f'{fresh}/bundle/n.json', 'own'],
                     ['remove', f'{fresh}/run_tier.json'], ['own_tier'], ['json', f'{fresh}/bundle/n.json', 'own']],
                    run=False)
        self.assertEqual([x['status'] for x in res], ['ok'] * 5 + ['refused'], json.dumps(res)[:2000])
        self.assertEqual(res[4]['value'], 'DEV')
        self.assertIn('marker is missing', res[5]['msg'])

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

    @unittest.skipUnless(os.path.isfile(f'{SCRATCH}/prim/potlid/cand/white_pot_lid_ep2_fit.glb'), 'no fixture')
    def test_named_fixture_prefix(self):
        """PREREG B.14 T-V2d: the raw hand-kit lid (prefix 4bd1751e84052f05) passes as a dev fixture; clean refuses."""
        p = f'{SCRATCH}/prim/potlid/cand/white_pot_lid_ep2_fit.glb'
        res = probe([['open', p, 'fixture'], ['manifest']], mode='dev', synthetic=False)
        self.assertStatus(res, 'ok')
        rec = res[-1]['value']['inputs'][0]
        self.assertTrue(rec['sha256'].startswith('4bd1751e84052f05'))
        self.assertEqual(rec['tier'], 'DEV')
        res = probe([['open', p, 'fixture']], synthetic=False)
        self.assertStatus(res, 'refused')

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
        res = probe([['set_run', T['RUN']], ['set_run', T['RUN_DEV']]], mode='dev', run=False)
        self.assertEqual([x['status'] for x in res], ['refused', 'ok'])


class TestHook(Base):
    def test_hook_refuses_forbidden_opens(self):
        ops = [['builtin_open', p] for p in T['gt'].values()]
        ops += [['builtin_open', T['refused'][k]] for k in ('auto', 'diag', 'gmg/design', 'crops', 'obs_all',
                                                           'library_v3', 'library_v3x', 'gen/mesh-20261029')]
        ops += [['np_load', T['refused']['obs_all']], ['os_open', T['refused']['obs']],
                ['os_open', T['gt']['/scan']], ['np_load', T['deny_copy'].replace('ep3', 'forbidden_glob_dir')],
                ['dirfd_open', f'{T["D"]}/auto', 'stage1/refined/ep2_white_pot.npz'],
                ['dirfd_open', f'{T["D"]}/data', 'scan/white_pot.glb']]
        res = probe(ops)
        self.assertReason(res)

    def test_hook_allows_ordinary_and_code_opens(self):
        res = probe([['builtin_open', T['calib']], ['builtin_open', T['other']], ['builtin_open', T['code_scan']],
                     ['np_load', T['tracks_pub']], ['dirfd_open', f'{T["D"]}/data', 'calib.json']])
        self.assertStatus(res, 'ok')
        res = probe([['open', T['code_scan'], 'kit']])             # open_input applies the substrings to code too
        self.assertStatus(res, 'refused')

    def test_hook_code_exemption_by_suffix_only(self):
        """A non-code file under the interpreter prefix gets the substrings (round 1: prefixes were exempt)."""
        d = tempfile.mkdtemp(prefix='gmgtest-', dir=sys.prefix)
        try:
            data = _w(os.path.join(d, 'scan', 'a.json'), '{}')
            code = _w(os.path.join(d, 'scan', 'a.py'), '# code\n')
            res = probe([['builtin_open', data], ['builtin_open', code]])
            self.assertReason(res[:1], ('path contains',))
            self.assertStatus(res[1:], 'ok')
        finally:
            shutil.rmtree(d, ignore_errors=True)

    def test_hook_dev_admitted_only(self):
        p = T['refused']['obs_all']
        res = probe([['builtin_open', p], ['open', p, 'obs_all'], ['builtin_open', p], ['np_load', p]], mode='dev')
        self.assertEqual([x['status'] for x in res], ['refused', 'ok', 'ok', 'ok'])

    def test_hook_write_rules(self):
        D = T['D']
        res = probe([['write', f'{T["RUN"]}/bundle/w.txt'], ['write', f'{D}/gmg/runs/20200101-x-0000000/a.txt'],
                     ['write', f'{D}/gmg/runs-dev/20200101-x-0000000/a.txt'], ['write', f'{T["RUN_DEV"]}/b.txt']])
        self.assertStatus(res[:1], 'ok')
        self.assertReason(res[1:], ('run root outside the current run folder', 'dev run root is never touched'))
        res = probe([['write', f'{T["RUN_DEV"]}/bundle/w.txt'], ['write', f'{T["RUN"]}/bundle/w2.txt']], mode='dev')
        self.assertStatus(res[:1], 'ok')
        self.assertReason(res[1:], ('run root outside the current run folder',))


class TestRunProvenance(Base):
    """Verification round 2, blocking item 1: dev outputs must not enter a clean run by rename, replace, link, symlink
    or a self-written marker; and whatever ends up in a clean run folder is read only if a clean guarded process of
    that run wrote it (ledger RUN/outputs.jsonl)."""

    def _clean_run(self, tag):
        run = f'{T["D"]}/gmg/runs/20261030-{tag}-0000000'
        res = probe([['set_run', run], ['write_manifest', f'{run}/manifest.json']], run=False)
        self.assertStatus(res, 'ok')
        return run

    def test_probe1_dev_replace_and_rename_into_a_clean_run(self):
        D = T['D']
        clean = self._clean_run('probe1')
        dev = f'{D}/gmg/runs-dev/20261030-probe1-0000000'
        tmp = f'{D}/misc/probe1_tmp.npz'
        res = probe([['set_run', dev], ['npz', T['refused']['obs_all'], 'obs_all'],
                     ['savez', tmp, ['pts']], ['savez', f'{dev}/bundle/ep2_white_pot.npz', ['pts']],
                     ['replace', tmp, f'{clean}/bundle/ep2_white_pot.npz'],          # write-to-temp-then-replace
                     ['rename', f'{dev}/bundle/ep2_white_pot.npz', f'{clean}/bundle/moved.npz'],
                     ['shutil_move', tmp, f'{clean}/bundle/moved2.npz'],
                     ['link', tmp, f'{clean}/bundle/linked.npz'],
                     ['symlink', tmp, f'{clean}/bundle/sym.npz'],
                     ['write', f'{clean}/bundle/direct.json'],
                     ['makedirs', f'{clean}/bundle2'],
                     ['remove', f'{clean}/manifest.json']], mode='dev', run=False)
        self.assertStatus(res[:4], 'ok')
        self.assertReason(res[4:], ('run root outside the current run folder', 'hard link is never made inside a run'))
        self.assertFalse(os.path.exists(f'{clean}/bundle'))
        # the same moves made by an unguarded process (this runner): the clean process accepts the folder (its marker
        # is its own) but reads none of the moved files
        os.makedirs(f'{clean}/bundle', exist_ok=True)
        os.replace(tmp, f'{clean}/bundle/ep2_white_pot.npz')
        os.rename(f'{dev}/bundle/ep2_white_pot.npz', f'{clean}/bundle/moved.npz')
        res = probe([['set_run', clean], ['npz', f'{clean}/bundle/ep2_white_pot.npz', 'own'],
                     ['npz', f'{clean}/bundle/moved.npz', 'own'], ['np_load', f'{clean}/bundle/moved.npz'],
                     ['builtin_open', f'{clean}/bundle/ep2_white_pot.npz'], ['tier'],
                     ['json', f'{clean}/manifest.json', 'own']], run=False)
        self.assertStatus(res[:1], 'ok')
        self.assertReason(res[1:5], ('run provenance',))
        self.assertEqual(res[5]['value'], 'P0')                  # nothing was admitted from the moved files
        self.assertEqual(res[6]['status'], 'ok')                 # its own manifest is in the ledger

    def test_probe2_self_written_marker_and_moved_dev_run(self):
        D = T['D']
        name = '20261030-probe2-0000000'
        dev, moved = f'{D}/gmg/runs-dev/{name}', f'{D}/gmg/runs/{name}'
        forged = json.dumps(dict(mode='clean', tier='P1', run=name, root='runs'))
        res = probe([['set_run', dev], ['savez', f'{dev}/bundle/ep2_white_pot.npz', ['pts']],
                     ['write_manifest', f'{dev}/manifest.json'],
                     ['write', f'{dev}/run_tier.json', forged],                       # self-written marker
                     ['open_mode', f'{dev}/run_tier.json', 'a'], ['truncate', f'{dev}/run_tier.json', 0],
                     ['tls_protected_write', f'{dev}/run_tier.json', forged],        # private flag set by hand
                     ['write', f'{dev}/outputs.jsonl', '{}'],
                     ['rename', dev, moved], ['shutil_move', dev, moved], ['symlink', dev, moved],
                     ['rename', f'{dev}/run_tier.json', f'{dev}/x.json']], mode='dev', run=False)
        self.assertStatus(res[:3], 'ok')
        self.assertReason(res[3:8], ('written by the guard only',))
        self.assertReason(res[8:11], ('run root outside the current run folder',))
        self.assertReason(res[11:], ('is moved by nobody',))
        self.assertEqual(_json(f'{dev}/run_tier.json')['mode'], 'dev')
        # the same steps by an unguarded process: forge the marker, move the folder into the clean root
        try:
            _w(f'{dev}/run_tier.json', forged)
            os.rename(dev, moved)
            res = probe([['set_run', moved], ['npz', f'{moved}/bundle/ep2_white_pot.npz', 'own'],
                         ['np_load', f'{moved}/bundle/ep2_white_pot.npz'], ['json', f'{moved}/manifest.json', 'own']],
                        run=False)
            self.assertStatus(res[:1], 'ok')                       # a fully forged marker passes set_run ...
            self.assertReason(res[1:], ('run provenance',))        # ... but the dev ledger admits nothing
            # a forged marker without the run binding (round-2 form) is refused outright
            _w(f'{moved}/run_tier.json', json.dumps(dict(mode='clean', tier='P1')))
            res = probe([['set_run', moved]], run=False)
            self.assertReason(res, ('copied or moved marker',))
        finally:
            shutil.rmtree(moved, ignore_errors=True)

    def test_ledger_rules(self):
        run = self._clean_run('ledger')
        a, b = f'{run}/bundle/a.npz', f'{run}/bundle/b.npz'
        res = probe([['set_run', run], ['savez', a, ['pts']], ['npz', a, 'own'],          # own write: readable
                     ['replace', a, b], ['npz', b, 'own'],                               # rename inside the run
                     ['makedirs', f'{run}/tmp'], ['savez', f'{run}/tmp/c.npz'], ['rename', f'{run}/tmp', f'{run}/t2'],
                     ['npz', f'{run}/t2/c.npz', 'own'],
                     ['savez', f'{T["D"]}/misc/outside.npz'], ['rename', f'{T["D"]}/misc/outside.npz', f'{run}/o.npz'],
                     ['symlink', T['calib'], f'{run}/calib.json'], ['link', b, f'{run}/b2.npz'],
                     ['savez', f'{T["D"]}/misc/outside2.npz'], ['shutil_move', f'{T["D"]}/misc/outside2.npz', f'{run}/m.npz'],
                     ['write_manifest', f'{run}/manifest.json'], ['outputs']], run=False)
        st = [x['status'] for x in res]
        self.assertEqual(st, ['ok'] * 10 + ['refused'] * 3 + ['ok', 'refused'] + ['ok'] * 2, json.dumps(res)[:3000])
        self.assertFalse(os.path.exists(f'{run}/m.npz'))         # shutil.move's copy fallback did not run (round 3)
        self.assertIn('from outside it', res[10]['msg'])
        self.assertIn('must point inside it', res[11]['msg'])
        self.assertEqual(sorted(o['path'] for o in res[-1]['value'] if o['path'] != 'manifest.json'),
                         ['bundle/b.npz', 't2/c.npz'])
        # a fresh process: the ledger admits what the manifest recorded; changed or unlisted files are refused
        _w(f'{run}/bundle/foreign.npz', _bytes(b))                                      # same bytes, not listed
        with open(f'{run}/t2/c.npz', 'ab') as f:                                          # changed after the ledger
            f.write(b'x')
        res = probe([['set_run', run], ['npz', b, 'own'], ['npz', f'{run}/bundle/foreign.npz', 'own'],
                     ['npz', f'{run}/t2/c.npz', 'own'], ['open_mode', f'{run}/bundle/foreign.npz', 'ab'],
                     ['open_mode', f'{run}/bundle/foreign.npz', 'r+b'], ['a_plus_npz', f'{run}/bundle/foreign.npz'],
                     ['np_load', f'{run}/bundle/foreign.npz'],
                     ['open_mode', f'{run}/bundle/foreign.npz', 'wb'],                   # truncation: own content
                     ['json', f'{run}/manifest.json', 'own']], run=False)
        self.assertEqual(res[1]['status'], 'ok')
        self.assertReason(res[2:3], ('has no entry in outputs.jsonl',))
        self.assertReason(res[3:4], ('differs from its outputs.jsonl entries',))
        self.assertReason(res[4:8], ('run provenance',))
        self.assertStatus(res[8:], 'ok')
        # ledger lines that do not belong to this clean run admit nothing
        _w(f'{run}/bundle/d.npz', _bytes(b))
        _ledger(run, [f'{run}/bundle/d.npz'], mode='dev')
        _ledger(run, [f'{run}/bundle/d.npz'], name='20261030-other-0000000')
        _ledger(run, [f'{run}/bundle/d.npz'], sha='0' * 64)
        res = probe([['set_run', run], ['npz', f'{run}/bundle/d.npz', 'own']], run=False)
        self.assertReason(res[1:], ('run provenance',))

    def test_register_output(self):
        run = self._clean_run('regout')
        p = f'{run}/bundle/c_written.bin'
        res = probe([['set_run', run], ['subprocess', ['sh', '-c', f'mkdir -p {run}/bundle && printf abc > {p}']],
                     ['open', p, 'own'], ['register_output', p], ['open', p, 'own'],
                     ['register_output', f'{T["D"]}/misc/notes.bin'], ['register_output', f'{run}/run_tier.json'],
                     ['write_manifest', f'{run}/manifest.json'], ['outputs']], run=False)
        self.assertEqual([x['status'] for x in res], ['ok', 'ok', 'refused', 'ok', 'ok', 'refused', 'refused', 'ok',
                                                      'ok'], json.dumps(res)[:3000])
        self.assertEqual(res[-1]['value'][0]['how'], 'registered')
        old = f'{run}/bundle/old.bin'
        _w(old)
        os.utime(old, (1e9, 1e9))
        res = probe([['set_run', run], ['register_output', old]], run=False)
        self.assertReason(res[1:], ('not modified since this process started',))

    def test_removals_and_other_runs(self):
        D = T['D']
        other = self._clean_run('other')
        res = probe([['remove', f'{other}/manifest.json'], ['rmtree', other], ['rmtree', f'{D}/gmg/runs'],
                     ['rmtree', f'{D}/gmg'], ['rename', f'{D}/gmg', f'{D}/gmg_old'], ['mkdir', f'{other}/x'],
                     ['mkdir', f'{D}/gmg/runs/20261030-new-0000000'], ['truncate', f'{other}/manifest.json', 0],
                     ['makedirs', T['RUN']], ['makedirs', f'{T["RUN"]}/sub']])
        self.assertReason(res[:8], ('run root outside the current run folder', 'is or contains the'))
        self.assertStatus(res[8:], 'ok')
        self.assertTrue(os.path.isfile(f'{other}/manifest.json'))


class TestHookEvents(Base):
    """Round 3 non-blocking items: a+b opens, HF dataset scans, hard links, kit scorer imports, the private door
    flags, process arguments and URLs."""

    def test_a_plus_b_det_copy(self):
        c = T['det_copy']
        res = probe([['a_plus_npz', c], ['open_mode', c, 'r+b'], ['open_mode', c, 'a+b']])
        self.assertReason(res, ('copy of a det file',))

    def test_hf_dataset_scans(self):
        res = probe([['builtin_open', T['hf_mesh']], ['builtin_open', T['hf_urdf']], ['open', T['hf_mesh'], 'video'],
                     ['open', T['hf_urdf'], 'kit'], ['check', T['hf_mesh'], 'own']])
        self.assertReason(res, ('refused folder: HF dataset track_3 mesh/ and urdf/',))
        res = probe([['builtin_open', T['hf_meta']], ['open', T['video_hf'], 'video']])
        self.assertStatus(res, 'ok')
        for r in (f'{T["D"]}/hfds', f'{T["D"]}/hfds/track_3/public'):
            rc, out, err = probe_raw([['mode']], GMG_WEIGHTS_ROOT=r)
            self.assertNotEqual(rc, 0, (r, out))
            self.assertIn('refused GMG_WEIGHTS_ROOT', err)

    def test_hard_link_read_by_the_hook(self):
        res = probe([['np_load', T['hl_b']], ['builtin_open', T['hl_a']]])
        self.assertReason(res, ('hard links',))

    def test_kit_scorer_import_refused(self):
        pyc = f'{T["K"]}/v2dlb/__pycache__/object_mesh.cpython-313.pyc'
        _w(pyc, b'\x00' * 16)
        try:
            res = probe([['import_kit', 'v2dlb.object_mesh'], ['import_kit', 'v2dlb.track3_pose'],
                         ['builtin_open', pyc], ['builtin_open', T['kit_scorer'][0]]])
            self.assertReason(res, ('kit scorer',))
            res = probe([['import_kit', 'v2dlb.mesh_budget']])
            self.assertStatus(res, 'ok')
        finally:
            os.remove(pyc)

    def test_private_doors_need_a_guard_frame(self):
        d = T['det']
        res = probe([['tls_det_np_load', d], ['internal_np_load', d], ['tls_det_np_load', T['det_copy']],
                     ['manifest']])
        self.assertReason(res[:3], ('opened only inside guard.load_npz',))
        # at most the guard's own hash of the original dump (to recognise the copy); no np.load went through
        self.assertLessEqual(res[-1]['value']['guarded_opens'].get(os.path.realpath(d), 0), 1)

    def test_process_arguments_and_urls(self):
        hf = 'https://huggingface.co/datasets/nvidia/video_to_data_challenge/resolve/main/track_3'
        res = probe([['subprocess', ['cat', T['refused']['obs_all']]], ['subprocess', ['cat', T['gt']['/scan']]],
                     ['subprocess', ['curl', '-sS', f'{hf}/public/mesh/white_pot/white_pot.glb']],
                     ['subprocess', ['curl', f'{hf}/public/data/chunk-000/episode_000002.parquet']],
                     ['os_system', f'cat {T["refused"]["auto"]} > /dev/null'],
                     ['urllib_open', 'http://127.0.0.1:9/datasets/x/resolve/main/track_3/public/urdf/white_pot.urdf'],
                     ['http_send', '/datasets/nvidia/video_to_data_challenge/resolve/main/track_3/public/mesh/a.glb'],
                     ['subprocess', ['cat', f'{T["K"]}/v2dlb/object_mesh.py']]])
        self.assertReason(res, ('refused folder', 'path contains', 'URL', 'kit scorer'))
        res = probe([['subprocess', ['true', T['calib']]],
                     ['urllib_open', 'http://127.0.0.1:9/datasets/x/resolve/main/track_3/public/videos/x.mp4'],
                     ['http_send', '/api/datasets/aebatirel/v2d-store']])
        self.assertEqual([x['status'] for x in res], ['ok', 'ok', 'ok'], json.dumps(res)[:2000])
        self.assertTrue(str(res[1]['value']).startswith('oserror'))         # reached the (closed) port: not refused


class TestConstants(Base):
    def test_constants(self):
        ops = [['constant', 'vote_voxel_m', 0.004, 'generic'],
               ['constant', 'remesh_pitch_m', 0.0015, 'sensor'],
               ['constant', 'face_budget', 4000, 'kit'],
               ['constant', 'class_order', ['STRUCT', 'FUSE', 'GEN', 'SHELL', 'HULL'],
                'informed:class order ([D] hand kits)'],
               ['constant', 't0_mm', 2.5, 'fallback:scan-coincident (brief leak), PREREG A.6'],
               ['constant', 'tau_v3', 0.2, 'fitted:own CPU fold-rebuild null q99'],
               ['constant', 'ball_r_mm', 7.0, 'fitted:own B.4 consensus'],
               ['constant', 'free_ratio_max', 0.2, 'generic'],                     # A.6 FREE ratio: not banned
               ['constant', 'free_thresh', 0.2, 'generic'],                        # round 3: 'thresh' alone is fine
               ['constant', 'vote_voxel_m', 0.004, 'generic'],                   # same value again: fine
               ['constants']]
        res = probe(ops)
        self.assertStatus(res, 'ok')
        cs = {c['name']: c for c in res[-1]['value']}
        self.assertEqual(len(cs), 9)
        self.assertTrue(all(c['where'] for c in cs.values()))
        bad = [['constant', 'x', 1, 'made-up'], ['constant', 'x', 1, 'fitted'], ['constant', 'x', 1, 'fitted: '],
               ['constant', 'x', 1, 'fitted:scan wall median'], ['constant', 'y', 1, 'fitted:library_v3 extents'],
               ['constant', 'ball_r_mm', 7.0, 'generic'], ['constant', 'ball_radius_m', 0.007, 'informed:V5'],
               ['constant', 'thickness_default_mm', 2.5, 'generic'], ['constant', 'tau_v3', 0.2, 'informed:V5'],
               ['constant', 'vote_voxel_m', 0.004, 'generic'], ['constant', 'vote_voxel_m', 0.005, 'generic'],
               ['constant', 'bad name', 1, 'generic'], ['constant_set', 'z', [1, 2], 'generic'],
               # verification round 1: names the round-1 regexes missed, and informed origins not on A.6
               ['constant', 'sphere_radius_mm', 7.0, 'generic'], ['constant', 'v3_threshold', 0.2, 'informed:V5'],
               ['constant', 'shell_t_mm', 2.5, 'generic'], ['constant', 'marker_diam_mm', 14.0, 'sensor'],
               ['constant', 'wall_m', 0.0025, 'kit'], ['constant', 'q', 3, 'informed'],
               ['constant', 'q', 3, 'informed:looked nice'],
               # verification round 2: constants are fitted on public observations only
               ['constant', 'e', 3, 'fitted:eval episodes median'], ['constant', 'e', 3, 'fitted:Evaluation split q90'],
               ['constant', 'fold_tau', 0.2, 'generic']]
        res = probe(bad)
        self.assertNotIn('ok', [x['status'] for i, x in enumerate(res) if i != 9], json.dumps(res)[:3000])
        self.assertEqual(res[9]['status'], 'ok')
        self.assertIn('already', res[10]['msg'])
        for x in res[13:18]:
            self.assertIn('scan-informed value', x['msg'])
        for x in res[18:20]:
            self.assertIn('PREREG A.6 row', x['msg'])
        for x in res[20:22]:
            self.assertIn('public observations only', x['msg'])
        self.assertIn('scan-informed value', res[22]['msg'])
        res = probe([['constant', 'k', 3, 'fitted:retrieval of own public points']])
        self.assertStatus(res, 'ok')

    def test_informed_rows_match_prereg(self):
        """INFORMED_A6 equals the PREREG A.6 rows whose origin says 'informed' (names only)."""
        with open(os.path.join(GMG, 'PREREG.md')) as f:
            txt = f.read()
        sec = txt.split('### A.6 Constants', 1)[1].split('### A.6b', 1)[0]
        rows = [[c.strip() for c in ln.strip().strip('|').split('|')] for ln in sec.splitlines()
                if ln.startswith('| ') and not ln.startswith('| Constant') and not ln.startswith('|---')]
        informed = [r[0] for r in rows if len(r) >= 3 and 'informed' in r[2]]
        names = probe([['attr', 'INFORMED_A6']])[0]['value']
        self.assertEqual(len(informed), len(names), (informed, names))
        for n in names:
            self.assertTrue(any(i.startswith(n) for i in informed), (n, informed))


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
        dl = _json(os.path.join(REPO, 'ops', 'provenance', 'denylist.json'))
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
            if root.endswith(('/obs_all', '/obs', '/auto/stage1/refined', '/runs-dev')):
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


UNGUARDED = '''import json, os, shutil, sys
for op in json.loads(sys.argv[1]):
    k = op[0]
    if k == 'read':
        open(op[1], 'rb').read(1)
    elif k == 'rplus':
        with open(op[1], 'r+b') as f:
            f.read()
    elif k == 'write':
        with open(op[1], 'w') as f:
            f.write('x')
    elif k == 'dirfd':
        d = os.open(op[1], os.O_RDONLY | os.O_DIRECTORY)
        g = os.open(op[2], os.O_RDONLY, dir_fd=d)
        os.read(g, 1)
        os.close(g)
        os.close(d)
    elif k == 'copy':
        shutil.copyfile(op[1], op[2])
    elif k == 'rename':
        os.rename(op[1], op[2])
    elif k == 'link':
        os.link(op[1], op[2])
    elif k == 'symlink':
        os.symlink(op[1], op[2])
    elif k == 'chdir':
        os.chdir(op[1])
    elif k == 'connect':
        import socket
        s = socket.socket()
        s.settimeout(0.5)
        try:
            s.connect(('127.0.0.1', 9))
        except OSError:
            pass
        s.close()
    elif k == 'execv':
        os.execv(op[1], op[2])
'''


def _is_git_exe(exe):
    return bool(exe) and os.path.basename(exe).startswith('git')


@unittest.skipUnless(shutil.which('strace'), 'strace not installed')
class TestStrace(Base):
    def _audit(self, cmd, log, manifest=None, **kw):
        args = [sys.executable, AUDIT, 'run', '--log', log] + (['--manifest', manifest] if manifest else []) + \
            ['--', *cmd]
        r = subprocess.run(args, capture_output=True, text=True, errors='replace', env=env(**kw), cwd='/tmp',
                           timeout=900)
        return r, _json(log + '.audit.json')

    def test_dummy_clean_run_zero_forbidden_opens(self):
        import datetime
        day = datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%d')
        commit = subprocess.run(['git', '-C', REPO, 'rev-parse', '--short=7', 'HEAD'], capture_output=True,
                                text=True).stdout.strip()
        run = os.path.join(SCRATCH, 'gmg', 'runs', f'{day}-b0test-{commit}')
        shutil.rmtree(run, ignore_errors=True)
        log = os.path.join(SCRATCH, 'gmg', 'audit', f'b0test-{commit}.strace')
        r, rep = self._audit([sys.executable, DUMMY, '--tag', 'b0test'], log, os.path.join(run, 'manifest.json'),
                             synthetic=False)
        dummy = _json(os.path.join(run, 'dummy_result.json'))
        self.assertTrue(dummy['pass'], json.dumps(dummy['unexpected'])[:3000])
        self.assertGreaterEqual(len(dummy['refused']), 50)
        self.assertEqual(rep['forbidden_opens'], 0,
                         json.dumps(rep['forbidden'] + rep['unlisted'] + rep['writes_outside_run'])[:3000])
        self.assertEqual(rep['returncode'], 0, r.stdout[-2000:] + r.stderr[-2000:])
        self.assertEqual(rep['writes_outside_run'], [])
        self.assertGreater(rep['events'], 500)
        self.assertGreaterEqual(len(rep['data_reads']), 5)
        det = os.path.realpath(REAL_DET)
        if os.path.isfile(det):
            man = _json(os.path.join(run, 'manifest.json'))
            self.assertEqual(rep['det_reads'].get(det), man['guarded_opens'].get(det))
        T['strace_report'] = dict(log=log, run=run, events=rep['events'], data_reads=len(rep['data_reads']),
                                  refused=len(dummy['refused']), allowed=len(dummy['allowed']))

    def test_audit_detects_unguarded_opens(self):
        """Negative control: an unguarded process that reads GT-pattern, refused, deny-sha and unlisted files, also
        under /root/.cache and /opt, reads a deny-sha file with r+b, writes outside the run, opens through dir_fd and
        copies a det dump. Every one is caught (so 0 above means 0, not a blind auditor)."""
        tag = os.path.basename(T['D'])
        cache = os.path.join(os.path.expanduser('~'), '.cache', f'gmgtest-{tag}')
        opt = f'/opt/gmgtest-{tag}'
        script = _w(os.path.join(os.path.dirname(T['D']), f'unguarded_{tag}.py'), UNGUARDED)
        log = os.path.join(os.path.dirname(T['D']), f'neg_{tag}.strace')
        blob = _bytes(T['deny_copy'])
        try:
            sysf = dict(parquet=_w(f'{cache}/hub/datasets/x/episode_000002.parquet'),
                        scan=_w(f'{cache}/hub/track_3/public/scan/white_pot.glb'),
                        loc=_w(f'{opt}/loc/perc/ep2/poses.npz'),
                        blob_cache=_w(f'{cache}/blob.bin', blob), blob_opt=_w(f'{opt}/blob.bin', blob),
                        plain_opt=_w(f'{opt}/plain.txt'), mocap=_w(f'{cache}/mocap_ep2.npz'))
            reads = [T['gt']['/scan'], T['refused']['auto'], T['refused']['obs_all'], T['deny_copy'], T['other']]
            reads += list(sysf.values())
            outside = f'{T["D"]}/misc/written.txt'
            copy = f'{T["RUN"]}/bundle/neg_copy.npz'
            ops = [['read', p] for p in reads] + [['rplus', T['deny_copy']], ['write', outside],
                                                  ['dirfd', f'{T["D"]}/auto', 'stage1/refined/ep2_white_pot.npz'],
                                                  ['copy', T['det'], copy]]
            r, rep = self._audit([sys.executable, '-I', script, json.dumps(ops)], log)
            self.assertNotEqual(r.returncode, 0)
            hit = {f.get('rpath') or f['path'] for k in ('forbidden', 'unlisted', 'writes_outside_run') for f in rep[k]}
            for p in reads + [outside, copy, T['det']]:
                self.assertIn(os.path.realpath(p), hit, (p, json.dumps(rep, default=str)[:3000]))
            rplus = [f for f in rep['forbidden'] if f.get('rpath') == os.path.realpath(T['deny_copy']) and
                     f.get('write')]
            self.assertTrue(rplus, 'r+b read of a deny-sha file not caught')
            self.assertTrue([f for f in rep['forbidden'] if 'written file is a det file' in f['reason']])
            self.assertTrue([f for f in rep['forbidden'] if 'opened 1 times, 0 by guard.load_npz' in f['reason']])
            self.assertEqual({f['rpath'] for f in rep['writes_outside_run']},
                             {os.path.realpath(outside), os.path.realpath(T['deny_copy'])})      # r+b is a write too
            # the same system-prefix files read by cat (the verifier's control)
            r, rep = self._audit(['cat'] + list(sysf.values()), log)
            self.assertNotEqual(r.returncode, 0)
            hit = {f.get('rpath') or f['path'] for k in ('forbidden', 'unlisted') for f in rep[k]}
            for p in sysf.values():
                self.assertIn(os.path.realpath(p), hit, p)
        finally:
            for p in (script, log, log + '.audit.json'):
                if os.path.exists(p):
                    os.remove(p)
            shutil.rmtree(cache, ignore_errors=True)
            shutil.rmtree(opt, ignore_errors=True)
            if os.path.exists(f'{T["RUN"]}/bundle/neg_copy.npz'):
                os.remove(f'{T["RUN"]}/bundle/neg_copy.npz')

    def _hits(self, rep):
        return {f.get('rpath') or f['path'] for k in ('forbidden', 'unlisted', 'writes_outside_run') for f in rep[k]}

    @unittest.skipUnless(shutil.which('git'), 'git not installed')
    def test_audit_git_attribution(self):
        """Verification round 2, blocking item 2: opens a pid made before it execs git are checked like any other
        (the image current at each call decides), and git's own exemption covers its .git/ reads only."""
        tag = os.path.basename(T['D'])
        git = shutil.which('git')
        script = _w(os.path.join(os.path.dirname(T['D']), f'gitattr_{tag}.py'), UNGUARDED)
        log = os.path.join(os.path.dirname(T['D']), f'gitattr_{tag}.strace')
        copy = f'{T["D"]}/misc/innocent.bin'
        shutil.copyfile(T['det'], copy)
        outside = f'{T["D"]}/misc/written_by_git_case.txt'
        reads = [T['det'], copy, T['other']]
        ops = [['read', p] for p in reads] + [['write', outside]]
        try:
            r, rep = self._audit([sys.executable, '-I', script, json.dumps(ops)], log)            # control
            control = rep['forbidden_opens']
            self.assertGreaterEqual(control, 4, json.dumps(rep, default=str)[:2000])
            for p in reads + [outside]:
                self.assertIn(os.path.realpath(p), self._hits(rep))
            r, rep = self._audit([sys.executable, '-I', script,
                                  json.dumps(ops + [['execv', git, ['git', '--version']]])], log)
            self.assertEqual(rep['forbidden_opens'], control, json.dumps(rep['forbidden'], default=str)[:2000])
            for p in reads + [outside]:
                self.assertIn(os.path.realpath(p), self._hits(rep))
            r, rep = self._audit([git, 'hash-object', copy, T['other']], log)
            self.assertNotEqual(r.returncode, 0)
            self.assertIn(os.path.realpath(copy), self._hits(rep))
            self.assertIn(os.path.realpath(T['other']), self._hits(rep))
            self.assertTrue([f for f in rep['forbidden'] if 'by guard.load_npz' in f['reason']])
            r, rep = self._audit(['sh', '-c', f'exec git hash-object --stdin < {copy}'], log)
            self.assertNotEqual(r.returncode, 0)
            self.assertTrue([f for f in rep['forbidden'] if 'by guard.load_npz' in f['reason']],
                            json.dumps(rep, default=str)[:2000])
            self.assertTrue([f for f in rep['forbidden'] + rep['unlisted']
                             if f.get('rpath') == os.path.realpath(copy) and not _is_git_exe(f.get('exe'))])
        finally:
            for p in (script, log, log + '.audit.json', copy, outside):
                if os.path.exists(p):
                    os.remove(p)

    def test_audit_moves_links_symlinks_network(self):
        """rename*, link*, symlink* and connect are traced: a file moved into the run from outside, a hard link into
        the run, a symlink to a refused folder, a read of a run file nobody wrote, a relative rename after chdir and a
        network connection are caught; a rename inside the run is not."""
        tag = os.path.basename(T['D'])
        script = _w(os.path.join(os.path.dirname(T['D']), f'moves_{tag}.py'), UNGUARDED)
        log = os.path.join(os.path.dirname(T['D']), f'moves_{tag}.strace')
        R, M = T['RUN'], f'{T["D"]}/misc'
        _w(f'{M}/mv_src.bin', b'moved in')
        _w(f'{M}/ln_src.bin', b'linked in')
        _w(f'{M}/rel_src.bin', b'relative')
        _w(f'{R}/bundle/nobody.bin', b'placed here by nobody')
        made = [f'{R}/bundle/mv_dst.bin', f'{R}/bundle/ln_dst.bin', f'{R}/bundle/sym_auto.npz', f'{R}/bundle/rel.bin',
                f'{R}/bundle/in_run_b.bin']
        ops = [['rename', f'{M}/mv_src.bin', made[0]], ['link', f'{M}/ln_src.bin', made[1]],
               ['symlink', T['refused']['auto'], made[2]], ['read', f'{R}/bundle/nobody.bin'],
               ['chdir', M], ['rename', 'rel_src.bin', made[3]],
               ['write', f'{R}/bundle/in_run_a.bin'], ['rename', f'{R}/bundle/in_run_a.bin', made[4]],
               ['read', made[4]], ['connect']]
        try:
            r, rep = self._audit([sys.executable, '-I', script, json.dumps(ops)], log)
            self.assertNotEqual(r.returncode, 0)
            wo = {f['path']: f['reason'] for f in rep['writes_outside_run']}
            self.assertIn('rename source outside', wo.get(f'{M}/mv_src.bin', ''))
            self.assertIn('rename source outside', wo.get(f'{M}/rel_src.bin', ''))       # relative path via cwd
            reasons = [f['reason'] for f in rep['forbidden']]
            self.assertTrue([x for x in reasons if 'hard link created in the run folder' in x])
            self.assertTrue([f for f in rep['forbidden'] if f['path'] == T['refused']['auto']
                             and f['kind'] == 'symlink_target'])
            self.assertTrue([f for f in rep['forbidden'] if f['path'] == f'{R}/bundle/nobody.bin'
                             and 'run provenance' in f['reason']])
            self.assertTrue([x for x in reasons if 'network connection' in x])
            self.assertIn(f'{M}/ln_src.bin', self._hits(rep))           # link source: read checks (2 links now)
            clean = [f for k in ('forbidden', 'unlisted', 'writes_outside_run') for f in rep[k]
                     if f['path'] in (f'{R}/bundle/in_run_a.bin', made[4])]
            self.assertEqual(clean, [], json.dumps(clean)[:2000])
            self.assertGreaterEqual(rep['moves'], 3)
            r, rep = self._audit(['sh', '-c', f'{sys.executable} -I {script} \'{json.dumps([["connect"]])}\''], log)
            self.assertEqual(len(rep['network']), 1)
            args = [sys.executable, AUDIT, 'analyze', log, '--allow-net']
            rr = subprocess.run(args, capture_output=True, text=True, env=env(), cwd='/tmp')
            self.assertEqual(rr.returncode, 0, rr.stdout[-2000:])
        finally:
            for p in [script, log, log + '.audit.json', f'{R}/bundle/nobody.bin'] + made:
                if os.path.lexists(p):
                    os.remove(p)
            for p in (f'{M}/mv_src.bin', f'{M}/ln_src.bin', f'{M}/rel_src.bin', f'{R}/bundle/in_run_a.bin'):
                if os.path.lexists(p):
                    os.remove(p)

    def test_audit_manifest_outputs_written_by_the_command(self):
        """register_output of a file the audited command did not write is caught by the audit."""
        run = f'{T["D"]}/gmg/runs/20261030-regaudit-0000000'
        _marker(run)
        pre = _w(f'{run}/bundle/pre.bin', b'placed before the audited command started')
        man = f'{run}/manifest.json'
        log = os.path.join(os.path.dirname(T['D']), f'regaudit_{os.path.basename(T["D"])}.strace')
        ops = json.dumps([['register_output', pre], ['savez', f'{run}/bundle/own.npz'], ['write_manifest', man]])
        sh = f'{sys.executable} {PROBE} <<\'EOF\'\n{ops}\nEOF\n'
        try:
            r, rep = self._audit(['sh', '-c', sh], log, man, GMG_RUN=run)
            reasons = {f['path']: f['reason'] for f in rep['forbidden']}
            self.assertIn('not written by the audited command', reasons.get(pre, ''), json.dumps(rep['forbidden'])[:2000])
            self.assertNotIn(f'{run}/bundle/own.npz', reasons)
        finally:
            shutil.rmtree(run, ignore_errors=True)
            for p in (log, log + '.audit.json'):
                if os.path.exists(p):
                    os.remove(p)

    def test_audit_roster_policy(self):
        """Policy roster (M0r): the --src parquets may be read (the auditor does not hash them: its own hook refuses
        .parquet opens, round 3); any other data read, and any parquet outside --src, is caught."""
        tag = os.path.basename(T['D'])
        src = os.path.join(os.path.dirname(T['D']), f'roster_src_{tag}')
        pq = _w(f'{src}/episode_000002.parquet', b'PAR1 synthetic PAR1')
        log = os.path.join(os.path.dirname(T['D']), f'roster_{tag}.strace')
        out = os.path.join(os.path.dirname(T['D']), f'roster_out_{tag}.json')
        try:
            args = [sys.executable, AUDIT, 'run', '--policy', 'roster', '--src', src, '--out', out, '--log', log, '--',
                    'cat', pq]
            r = subprocess.run(args, capture_output=True, text=True, env=env(run=False), cwd='/tmp', timeout=300)
            rep = _json(log + '.audit.json')
            self.assertEqual(rep['forbidden_opens'], 0, r.stdout[-2000:] + r.stderr[-2000:])
            self.assertEqual(rep['data_reads'], [pq])
            args[-1:] = [pq, T['other'], T['gt']['.parquet']]
            r = subprocess.run(args, capture_output=True, text=True, env=env(run=False), cwd='/tmp', timeout=300)
            rep = _json(log + '.audit.json')
            self.assertEqual(rep['forbidden_opens'], 2, json.dumps(rep, default=str)[:2000])
            self.assertIn(T['other'], {f['path'] for f in rep['unlisted']})
            self.assertIn(T['gt']['.parquet'], {f['path'] for f in rep['forbidden']})
        finally:
            shutil.rmtree(src, ignore_errors=True)
            for p in (log, log + '.audit.json', out):
                if os.path.exists(p):
                    os.remove(p)

    def test_audit_reconciles_det_opens(self):
        """A guarded process loads the det dump through load_npz and writes its manifest; a child `cat` of the same
        file in the same audited command is an unguarded open and is caught."""
        man = os.path.join(T['RUN'], 'recon_manifest.json')
        log = os.path.join(os.path.dirname(T['D']), f'recon_{os.path.basename(T["D"])}.strace')
        ops = json.dumps([['npz', T['det'], 'det'], ['write_manifest', man]])
        sh = f'{sys.executable} {PROBE} <<\'EOF\'\n{ops}\nEOF\n'
        try:
            r, rep = self._audit(['sh', '-c', sh], log, man)
            self.assertEqual(rep['forbidden_opens'], 0, json.dumps(rep['forbidden'] + rep['unlisted'])[:3000])
            r, rep = self._audit(['sh', '-c', sh + f'cat {T["det"]} > /dev/null\n'], log, man)
            self.assertTrue([f for f in rep['forbidden'] if 'by guard.load_npz' in f['reason']],
                            json.dumps(rep['forbidden'])[:3000])
        finally:
            for p in (log, log + '.audit.json', man):
                if os.path.exists(p):
                    os.remove(p)


if __name__ == '__main__':
    unittest.main(verbosity=2)
