"""B1 tests of gmg/score.py, gmg/geom.py and the packer, and the PREREG B.14 V2 synthetic tests (P21).

  GMG_MODE=dev python docs/research/mesh-2026-10-26/gmg/tests/test_score.py          (venv python)
  GMG_MODE=dev python .../test_score.py B14                                          (only the B.14 tests)

PREREG B.14 (build step B1, dev, test fixtures), as written:
  T-V2a ep11: the blue cup's route-A shell united with the beige cup's route-A shell placed at the beige cup's median
        contact-frame relative pose (a fused double cup) -> must be vetoed.
  T-V2b ep11: the convex hull of the blue cup's owned points (cavity filled) -> must be vetoed.
  T-V2c ep2: the lid's route-A shell united with the pot's route-A shell placed at the pot's median contact-frame
        relative pose (a lid with a phantom pot body) -> must be vetoed.
  T-V2d ep2: the hand-kit lid potlid/fit/ep2 (label sha prefix e1be3218a8608793; role fixture) -> must not be vetoed
        against pot samples.
  Pass: all four as stated. These are dev data (library_v3 --others removed), so the tests check the logic, not
  ownership.
Choices made here (DEVIATIONS, B1): 'united' = the two closed meshes concatenated (V2 (a) then uses the exact winding
number wherever the parity check disagrees); 'route-A shell' = producers/shell (autokit thin_shell) at t0_dev;
'median contact-frame relative pose' = the medoid contact frame of T_{o<-p} under the A.2 jitter metric (mean
displacement of the partner samples); the label sha of T-V2d is mesh_metric's sha1[:16] of the raw fixture file.
Results go to <scratchpad>/gmg/b1/test_score_b14.json (env B14_OUT overrides). No scan, label value or eval file is
read.
"""
import hashlib
import importlib.util
import itertools
import json
import os
import sys
import time
import unittest

os.environ.setdefault('GMG_MODE', 'dev')
HERE = os.path.dirname(os.path.abspath(__file__))
GMG = os.path.dirname(HERE)
MR = os.path.dirname(GMG)
if MR not in sys.path:
    sys.path.insert(0, MR)
from gmg import guard  # noqa: E402
import numpy as np  # noqa: E402
import trimesh  # noqa: E402

from gmg import bundle as B, contact as CT, geom, score as SC  # noqa: E402
from gmg.producers import shell as P_SHELL  # noqa: E402

B14_OUT = os.environ.get('B14_OUT', os.path.join(guard.CFG['data'], 'gmg', 'b1', 'test_score_b14.json'))
FIXTURE = os.path.join(guard.CFG['data'], 'prim', 'potlid', 'cand', 'white_pot_lid_ep2_fit.glb')
_CACHE = {}


def _bundle(ep):
    if ep not in _CACHE:
        _CACHE[ep] = B.from_obs_all(ep)
    return _CACHE[ep]


def _t0():
    d = guard.load_json(os.path.join(guard.CFG['gmg'], 'dev_constants.json'), 'dev_frozen')
    return guard.constant('t0_m', float(d['t0_dev_m']), d['t0_dev_origin'])


def _shell(b, obj):
    key = ('shell', b.meta['ep'], obj)
    if key not in _CACHE:
        _CACHE[key] = P_SHELL.produce(dict(bundle=b, obj=obj, t0=_t0()))[0].mesh
    return _CACHE[key]


def median_contact_pose(b, o, p, n=600):
    """Medoid contact frame of T_{o<-p}: the frame minimising the summed mean displacement of P_p (A.2 metric)."""
    frames = sorted(set(b.contact(o, p)['contact']))
    Xp = b.samples(p)[0]
    rng = np.random.default_rng(0)
    if len(Xp) > n:
        Xp = Xp[rng.choice(len(Xp), n, replace=False)]
    Y = np.stack([CT.moved(Xp, CT.rel(b.poses, o, p, f)) for f in frames])
    D = np.linalg.norm(Y[:, None] - Y[None], axis=-1).mean(-1)
    k = int(D.sum(1).argmin())
    return CT.rel(b.poses, o, p, frames[k]), frames[k], len(frames)


def _summ(r):
    return {p: {k: v for k, v in d.items() if k in ('veto', 'n_median', 'a_median', 'b_median', 'threshold',
                                                     'contact_frames', 'band_mm', 'n_max', 'frames_violating',
                                                     'inside_method')} for p, d in r['partners'].items()}


def _record(name, res):
    try:
        d = json.load(open(B14_OUT)) if os.path.exists(B14_OUT) else {}
    except ValueError:
        d = {}
    d[name] = res
    os.makedirs(os.path.dirname(B14_OUT), exist_ok=True)
    with open(B14_OUT, 'w') as f:
        json.dump(d, f, indent=1)


# ------------------------------------------------------------------------------------------------ unit tests
class GeomTests(unittest.TestCase):
    def test_inside_matches_gwn(self):
        m = trimesh.creation.icosphere(subdivisions=3, radius=0.05)
        X = np.random.default_rng(0).normal(size=(3000, 3)) * 0.04
        ins, info = geom.inside(m, X)
        self.assertEqual(info['disagree'], 0)
        self.assertTrue(np.array_equal(ins, geom.winding_number(m, X) >= 0.5))
        two = trimesh.util.concatenate([m, m.copy().apply_translation([0.03, 0, 0])])   # overlapping union
        ins2, info2 = geom.inside(two, X)
        self.assertTrue(np.array_equal(ins2, geom.winding_number(two, X) >= 0.5))

    def test_rays_match_bruteforce(self):
        m = trimesh.creation.annulus(r_min=0.02, r_max=0.05, height=0.04).apply_translation([0, 0, 0.5])
        P = np.random.default_rng(1).normal(size=(1500, 3)) * 0.03 + [0, 0, 0.5]
        fast = geom.ray_ranges(np.asarray(m.vertices)[m.faces], P)
        D = P / np.linalg.norm(P, axis=1, keepdims=True)
        ref = geom.first_hit(m, np.zeros_like(P), D)
        self.assertTrue(np.array_equal(np.isfinite(fast), np.isfinite(ref)))
        f = np.isfinite(ref)
        self.assertLess(np.abs(fast[f] - ref[f]).max(), 1e-9)

    def test_volume_samples(self):
        m = trimesh.creation.box((0.10, 0.06, 0.02))
        X, _ = geom.volume_samples(m, 20000, seed=0, axis=2)
        self.assertEqual(len(X), 20000)
        self.assertTrue(np.all(np.abs(X) <= np.array([0.05, 0.03, 0.01]) + 1e-9))
        self.assertLess(abs(np.mean(X[:, 0] > 0) - 0.5), 0.02)

    def test_closest(self):
        m = trimesh.creation.box((0.1, 0.1, 0.1))
        d, f, n = geom.closest(m, np.array([[0.0, 0.0, 0.08], [0.0, 0.0, 0.0], [0.07, 0.07, 0.0]]))
        self.assertTrue(np.allclose(d, [0.03, 0.05, np.hypot(0.02, 0.02)], atol=1e-9))
        self.assertTrue(np.allclose(n[0], [0, 0, 1]))


class KitDecodeTests(unittest.TestCase):
    def test_copy_matches_kit(self):
        kit = os.path.join(guard.CFG['kit'], 'v2dlb', 'mesh_budget.py')
        guard.open_input(kit, 'kit')
        spec = importlib.util.spec_from_file_location('kit_mesh_budget', kit)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        run = os.path.join(guard.CFG['data'], 'gmg', 'b1', 'kitdecode')
        os.makedirs(run, exist_ok=True)
        for name, m in (('sphere', trimesh.creation.icosphere(subdivisions=5, radius=0.05)),
                        ('box', trimesh.creation.box((0.1, 0.05, 0.02)))):
            p = os.path.join(run, f'{name}.glb')
            m.export(p)
            v1, f1 = mod.budget_mesh(p, 4096, 4096)
            v2, f2 = SC.kit_decode(p)
            self.assertTrue(np.array_equal(v1, v2) and np.array_equal(f1, f2), name)
            self.assertEqual(SC.v1(p)['watertight'], True)


class V2LogicTests(unittest.TestCase):
    """Synthetic two-object bundle: the logic of clauses (a) and (b) on known geometry."""

    def _bundle(self):
        vox = 0.004
        part = trimesh.creation.box((0.04, 0.04, 0.04))                        # partner: a 4 cm cube at the origin
        P, fi = trimesh.sample.sample_surface(part, 20000, seed=0)
        P = np.asarray(P)
        cam = P + np.asarray(part.face_normals)[fi] * 0.5                       # each point seen from outside
        lo = np.array([-0.062, -0.062, -0.062]); shape = (31, 31, 31)       # faces off the voxel boundaries
        hits = np.zeros(shape, np.uint16)
        vi = np.floor((P - lo) / vox).astype(int)
        np.add.at(hits, tuple(vi.T), 1)
        hits = ((hits > 0) * 10).astype(np.uint16)
        free = np.zeros(shape, np.uint16)
        obsp = dict(pts=P.astype(np.float32), cam=cam.astype(np.float32), frame=np.zeros(len(P), np.int32),
                    own=np.zeros(len(P), np.uint8), lo=lo, vox=vox, hits=hits.astype(np.uint16), free=free)
        obsp['state'] = B.state_grid(obsp['hits'], free)
        tgt = trimesh.creation.box((0.04, 0.04, 0.04)).apply_translation([0.08, 0, 0])   # target, far away
        Q, _ = trimesh.sample.sample_surface(tgt, 5000, seed=1)
        obst = dict(pts=np.asarray(Q, np.float32), cam=np.asarray(Q, np.float32) + 0.5, frame=np.zeros(5000, np.int32),
                    own=np.zeros(5000, np.uint8), lo=lo, vox=vox, hits=np.zeros(shape, np.uint16), free=free)
        obst['state'] = B.state_grid(obst['hits'], free)
        I = np.tile(np.eye(4), (1, 1, 1))
        poses = {'world_T_cam': I, 'cam_T_t': I, 'cam_T_p': I}
        meta = dict(objects=['t', 'p'], T=1, stride=1, sigma_mm=dict(t=1.0, p=1.0),
                    contact={'t|p': dict(contact=[0], j_mm=0.0), 'p|t': dict(contact=[0], j_mm=0.0)})
        return B.Bundle(meta, dict(t=obst, p=obsp), poses), part

    def test_clauses(self):
        b, part = self._bundle()
        far = trimesh.creation.box((0.04, 0.04, 0.04)).apply_translation([0.08, 0, 0])
        self.assertFalse(SC.v2(far, b, 't')['veto'])                                    # nowhere near
        filled = trimesh.creation.box((0.06, 0.06, 0.06))                              # swallows the partner
        r = SC.v2(filled, b, 't')['partners']['p']
        self.assertTrue(r['veto']); self.assertGreater(r['a_median'], 0)
        copy = trimesh.util.concatenate([far, part.copy()])                             # copies its surface
        r = SC.v2(copy, b, 't')['partners']['p']
        self.assertTrue(r['veto']); self.assertGreater(r['b_median'], 0); self.assertEqual(r['a_median'], 0)
        touch = trimesh.creation.box((0.04, 0.04, 0.04)).apply_translation([0.0405, 0, 0])   # touches one face
        self.assertFalse(SC.v2(touch, b, 't')['veto'])                                  # wall faces the other way


# ------------------------------------------------------------------------------------------------ PREREG B.14
class HullCoarsenTests(unittest.TestCase):
    """producers/hull._coarsen (DEVIATIONS 52): majority of kept fine voxels, no block with a non-OBSERVED partner
    voxel, then the component with the most OBSERVED voxels; the coarse march is watertight."""

    def test_rules(self):
        from gmg.producers import hull as P_HULL
        occ = np.zeros((12, 12, 12), bool)
        occ[2:10, 2:10, 2:10] = True                 # 8^3 cube -> 4^3 blocks at k = 2
        obsd = np.zeros_like(occ)
        obsd[2, 2:10, 2:10] = True                   # one observed face
        part = np.zeros_like(occ)
        part[9, 9, 9] = True                         # a non-OBSERVED partner voxel in the far corner block
        co = P_HULL._coarsen(occ, part, obsd, 2)
        self.assertEqual(co.shape, (6, 6, 6))
        self.assertEqual(int(co.sum()), 4 ** 3 - 1)  # the partner block is dropped
        self.assertFalse(co[4, 4, 4])
        part2 = np.zeros_like(occ)
        part2[2, 2, 2] = True                        # partner voxel that is OBSERVED: never clips
        self.assertEqual(int(P_HULL._coarsen(occ, part2, obsd, 2).sum()), 4 ** 3)
        z = np.zeros_like(occ)
        slab = z.copy()
        slab[2:10, 2:10, 4] = True                   # one-voxel slab: 4 of 8 fine voxels per block = half, kept
        self.assertEqual(int(P_HULL._coarsen(slab, z, z, 2).sum()), 16)
        line = z.copy()
        line[2:10, 4, 4] = True                      # one-voxel line: 2 of 8 per block, below half, dropped
        self.assertFalse(P_HULL._coarsen(line, z, z, 2).any())
        far = occ.copy()
        far[0, 0, 0] = far[0, 0, 1] = far[0, 1, 0] = far[1, 0, 0] = True   # separate component without OBSERVED
        far[1, 1, 1] = False
        co = P_HULL._coarsen(far, np.zeros_like(occ), obsd, 2)
        self.assertFalse(co[0, 0, 0])                # the seeded (observed) component is kept
        m = P_HULL._march(P_HULL._coarsen(occ, part, obsd, 2), np.zeros(3), 0.008)
        self.assertTrue(m.is_watertight)


class B14(unittest.TestCase):
    def test_a_fused_double_cup(self):
        b = _bundle(11)
        blue, beige = _shell(b, 'blue_cup'), _shell(b, 'beige_cup')
        T, f, n = median_contact_pose(b, 'blue_cup', 'beige_cup')
        fused = trimesh.util.concatenate([blue, beige.copy().apply_transform(T)])
        r = SC.v2(fused, b, 'blue_cup')
        base = SC.v2(blue, b, 'blue_cup')
        _record('T-V2a', dict(expect='veto', veto=r['veto'], detail=_summ(r), medoid_frame=f, contact_frames=n,
                              control_blue_shell_alone=dict(veto=base['veto'], detail=_summ(base))))
        self.assertTrue(r['veto'])

    def test_b_filled_cup(self):
        b = _bundle(11)
        P = np.asarray(b.obs('blue_cup')['pts'], np.float64)
        hull = trimesh.convex.convex_hull(P)
        r = SC.v2(hull, b, 'blue_cup')
        _record('T-V2b', dict(expect='veto', veto=r['veto'], detail=_summ(r), hull_faces=int(len(hull.faces))))
        self.assertTrue(r['veto'])

    def test_c_lid_with_phantom_pot(self):
        b = _bundle(2)
        lid, pot = _shell(b, 'white_pot_lid'), _shell(b, 'white_pot')
        T, f, n = median_contact_pose(b, 'white_pot_lid', 'white_pot')
        fused = trimesh.util.concatenate([lid, pot.copy().apply_transform(T)])
        r = SC.v2(fused, b, 'white_pot_lid')
        base = SC.v2(lid, b, 'white_pot_lid')
        _record('T-V2c', dict(expect='veto', veto=r['veto'], detail=_summ(r), medoid_frame=f, contact_frames=n,
                              control_lid_shell_alone=dict(veto=base['veto'], detail=_summ(base))))
        self.assertTrue(r['veto'])

    def test_d_kit_lid_passes(self):
        b = _bundle(2)
        rp = guard.open_input(FIXTURE, 'fixture')
        with open(rp, 'rb') as fh:
            sha1 = hashlib.sha1(fh.read()).hexdigest()
        label = guard.FIXTURE_LABEL_SHA['{DATA}/prim/potlid/cand/white_pot_lid_ep2_fit.glb']
        self.assertTrue(sha1.startswith(label), f'fixture sha1 {sha1[:16]} != label sha {label}')
        m = trimesh.load(rp, force='mesh')
        r = SC.v2(m, b, 'white_pot_lid')
        _record('T-V2d', dict(expect='no veto', veto=r['veto'], detail=_summ(r), fixture_sha1_16=sha1[:16],
                              fixture_sha256=guard.inputs()[[x['realpath'] for x in guard.inputs()].index(rp)]['sha256'],
                              faces=int(len(m.faces)), watertight=bool(m.is_watertight)))
        self.assertFalse(r['veto'])


# ------------------------------------------------------------------------------------------------ B5 (score full)
# Synthetic single-object episodes (tests/synth.py): known meshes, ray-cast depth with 1 mm noise, obs_points-style
# grids. GT-free by construction; no file is read except the ambiguity reference fixture (role fixture).
from gmg import select as SEL  # noqa: E402
from gmg.producers import Candidate  # noqa: E402
from gmg.tests import amb_meshes as AM, synth as SY  # noqa: E402

B5_OUT = os.environ.get('B5_OUT', os.path.join(guard.CFG['data'], 'gmg', 'b5', 'test_score_b5.json'))
AMB_REF = os.path.join(GMG, 'tests', 'fixtures', 'amb_reference.json')
_SYN = {}


def _record_b5(name, res):
    try:
        d = json.load(open(B5_OUT)) if os.path.exists(B5_OUT) else {}
    except ValueError:
        d = {}
    d[name] = res
    os.makedirs(os.path.dirname(B5_OUT), exist_ok=True)
    with open(B5_OUT, 'w') as f:
        json.dump(d, f, indent=1, default=lambda o: o.tolist() if hasattr(o, 'tolist') else str(o))


def cyl_episode():
    """Cylinder r 4 cm, h 8 cm (base at z = -4 cm). Blocks 1-2 (frames 0-30): two rings at +35 deg elevation; block 3
    (frames 32-46): a ring at -45 deg, the only views of the base."""
    if 'cyl' not in _SYN:
        _SYN['cyl'] = SY.episode(SY.cylinder(), SY.ring(35, 8) + SY.ring(35, 8, 22.5) + SY.ring(-45, 8), name='cyl')
    return _SYN['cyl']


def disc_episode():
    """Disc r 6 cm, 1 cm thick (z 0-1 cm), seen from +40, +10 and -20 deg: the space below it is carved FREE."""
    if 'disc' not in _SYN:
        _SYN['disc'] = SY.episode(SY.disc(), SY.ring(40, 8) + SY.ring(10, 8, 22.5) + SY.ring(-20, 8), name='disc')
    return _SYN['disc']


def slab_episode():
    """The slab with four balls on posts (tests/amb_meshes.py) seen from +50, +20 and -30 deg."""
    if 'slab' not in _SYN:
        _SYN['slab'] = SY.episode(AM.slab_with_balls(), SY.ring(50, 8) + SY.ring(20, 8, 22.5) + SY.ring(-30, 8),
                                  name='slab')
    return _SYN['slab']


def static_episode():
    """24 views within about 1 deg of one direction (a static episode)."""
    if 'static' not in _SYN:
        cams = [SY.cam_centre(30 + 0.5 * np.sin(i), 10 + 0.8 * np.cos(i)) for i in range(24)]
        _SYN['static'] = SY.episode(SY.cylinder(), cams, name='cyl')
    return _SYN['static']


class _Toy:
    """Test producer on the cylinder episode. rule 'always': the full cylinder whatever the frames (a structured
    completion closes the base). rule 'seen': the base only if the build frames hold more than 50 owned points on
    the base disc (z < -39 mm, radius < 35 mm), i.e. a shell covers only what it saw. rule 'raise': no fold build.
    rule 'skip2': the candidate exists except when building fold 2 (the frames without block 2)."""

    def __init__(self, cid, cls, rule, n_params=0):
        self.__name__, self.cid, self.cls, self.rule, self.n_params = f'toy_{cid}', cid, cls, rule, n_params

    def produce(self, ctx, frames=None):
        b, obj = ctx['bundle'], ctx['obj']
        full = SY.cylinder()
        obs = b.obs(obj)
        fr = np.asarray(obs['frame'])
        m = np.ones(len(fr), bool) if frames is None else np.isin(fr, list(frames))
        if self.rule == 'raise' and frames is not None:
            raise NotImplementedError('toy: no fold build')
        if self.rule == 'skip2' and frames is not None and not np.isin(ctx['block2'], list(frames)).any():
            return []
        mesh = full
        if self.rule == 'seen':
            P = np.asarray(obs['pts'], np.float64)[m]
            on_base = (P[:, 2] < -0.039) & (np.hypot(P[:, 0], P[:, 1]) < 0.035)
            mesh = full if int(on_base.sum()) > 50 else SY.without_base(full)
        return [Candidate(cid=self.cid, producer=self.__name__, cls=self.cls, mesh=mesh, params=dict(rule=self.rule),
                          n_params=self.n_params, built_on_frames='all' if frames is None else 'subset')]


def _row_summary(r):
    keys = ('cid', 'cls', 'E', 'E_blocks', 'E_se', 'fold', 'fsv_far', 'fsv_far_shell', 'trusted_markers')
    out = {k: r.get(k) for k in keys}
    out['v3'] = r.get('v3')
    out['ray_blocks'] = r.get('ray_blocks')
    for a in ('amb', 'amb_noball'):
        if r.get(a):
            out[a] = {k: r[a].get(k) for k in ('amb_mm', 'amb_floor_mm', 'flip_risk', 'flip_units')}
    return out


class AmbiguityCopyTests(unittest.TestCase):
    """score.ambiguity (own copy) == scripts/mesh_metric.ambiguity (original, kit AUC helpers) on the synthetic
    meshes; reference values written once by build/b5/amb_reference.py outside the gmg."""

    def test_copy_matches_mesh_metric(self):
        ref = guard.load_json(AMB_REF, 'fixture')['values']
        self.assertEqual(sorted(ref), sorted(AM.RECIPES))
        for name, (fn, kind) in AM.RECIPES.items():
            m = fn()
            v, f = np.asarray(m.vertices, np.float64), np.asarray(m.faces, np.int64)
            r = SC.ambiguity(v, f, kind)
            self.assertEqual((len(f), len(v)), (ref[name]['faces'], ref[name]['vertices']), name)
            for k in ('amb_mm', 'amb45_mm', 'amb_floor_mm', 'amb_rel', 'radius_mm'):
                self.assertAlmostEqual(r[k], ref[name][k], delta=1e-9 * max(1.0, abs(ref[name][k])), msg=(name, k))
            self.assertEqual((r['amb_rot'], r['n_starts']), (ref[name]['amb_rot'], ref[name]['n_starts']), name)

    def test_kit_symmetry_from_kit_config(self):
        self.assertEqual(SC.kit_symmetry('blue_cup'), 'axial')
        self.assertEqual(SC.kit_symmetry('beige_cup'), 'axial')
        self.assertEqual(SC.kit_symmetry('white_pot_lid'), 'half')
        self.assertIsNone(SC.kit_symmetry('wooden_piece_1'))

    def test_flip_units(self):
        self.assertEqual(SC.flip_units(3.0, 1.0), 2)
        self.assertEqual(SC.flip_units(1.5, 1.0), 0)
        self.assertEqual(SC.flip_units(0.9, 1.0), -1)
        self.assertEqual(SC.flip_units(float('inf'), 1.0), SC.FLIP_UNITS_INF)
        self.assertTrue(SC.is_flip_risk(1.9, 1.0)); self.assertFalse(SC.is_flip_risk(2.0, 1.0))


class PlanTests(unittest.TestCase):
    def test_blocks_and_heldout_sets(self):
        b = cyl_episode()
        obs = b.obs('cyl')
        good = b.good_frames('cyl')
        self.assertEqual(len(good), 24)
        for K in (3, 5):
            pl = SC.plan(b, 'cyl', K)
            bl = pl['blocks']
            self.assertEqual(sum((x['frames'] for x in bl), []), good)             # contiguous, time order
            sizes = [len(x['frames']) for x in bl]
            self.assertLessEqual(max(sizes) - min(sizes), 1)
            for k, x in enumerate(bl):
                fr = np.asarray(obs['frame'])[x['idx']]
                self.assertTrue(np.isin(fr, x['frames']).all())
                vi = np.floor((np.asarray(obs['pts'], np.float64)[x['idx']] - obs['lo']) / obs['vox']).astype(int)
                key = np.concatenate([fr[:, None], vi], 1)
                self.assertEqual(len(np.unique(key, axis=0)), len(key))           # one point per voxel per frame
                self.assertLessEqual(len(x['idx']), 20000)
                tr = SC.train_frames(pl, k)
                self.assertEqual(sorted(tr + x['frames']), good)
        self.assertEqual(SC.heldout(b, 'cyl')[0]['idx'].tolist(), SC.plan(b, 'cyl', 3)['blocks'][0]['idx'].tolist())


class BootstrapTests(unittest.TestCase):
    def test_moving_blocks(self):
        self.assertEqual([SC.block_length(n) for n in (1, 2, 7, 8, 26, 27, 64, 172)], [1, 1, 2, 2, 3, 3, 4, 6])
        blocks = [dict(frames=list(range(0, 54, 2)), kept=list(range(0, 54, 2))),       # 27 frames: L = 3
                  dict(frames=[60, 62, 64, 66, 70], kept=[60, 62, 64, 66, 70])]          # 5 frames: L = 2
        reps = SC.bootstrap_reps(blocks)
        self.assertEqual(len(reps), 200)
        for r in reps:
            for x, bk in zip(r, blocks):
                kept = bk['kept']
                L = SC.block_length(len(kept))
                self.assertEqual(len(x), len(kept))
                pos = [kept.index(int(f)) for f in x]
                for s in range(0, len(pos), L):                                # contiguous runs of L frames
                    run = pos[s:s + L]
                    self.assertEqual(run, list(range(run[0], run[0] + len(run))))
        again = SC.bootstrap_reps(blocks)                                       # seed 0: reproducible
        self.assertTrue(all(np.array_equal(a, c) for r1, r2 in zip(reps, again) for a, c in zip(r1, r2)))

    def test_paired_replicates(self):
        b = cyl_episode()
        pl = SC.plan(b, 'cyl', 3)
        reps = SC.bootstrap_reps(pl['blocks'])
        m = SY.cylinder()
        ev = SC.evidence(m, b, 'cyl', pl['blocks'], 0.0)
        e1 = SC.e_reps(ev, 0.0, b.sigma('cyl'), reps)
        e2 = SC.e_reps(SC.evidence(m, b, 'cyl', pl['blocks'], 0.0), 0.0, b.sigma('cyl'), reps)
        self.assertEqual(SC.se_diff(e1, e2), 0.0)
        self.assertGreater(float(np.std(e1)), 0.0)


class GenHoldoutTests(unittest.TestCase):
    def test_removes_views_within_8_deg(self):
        b = cyl_episode()
        D = SC.view_dirs(b, 'cyl', b.good_frames('cyl'))
        ang = np.degrees(np.arccos(np.clip(D @ D[0], -1, 1)))
        pl = SC.plan(b, 'cyl', 3, gen_views=[0])
        self.assertEqual(pl['removed'], [f for f, a in zip(b.good_frames('cyl'), ang) if a <= 8.0])
        self.assertEqual(pl['removed'], [0])                     # rings 22.5 / 45 deg apart: only frame 0 itself
        self.assertFalse(pl['gen_view_overlap'])
        self.assertNotIn(0, pl['blocks'][0]['kept'])
        self.assertFalse(np.isin(np.asarray(b.obs('cyl')['frame'])[pl['blocks'][0]['idx']], [0]).any())
        self.assertIn(0, SC.train_frames(pl, 1))                  # removed from held-out sets only
        pl2 = SC.plan(b, 'cyl', 3, gen_views=SC.view_dirs(b, 'cyl', [0]))   # directions instead of frames
        self.assertEqual(pl2['removed'], [0])

    def test_static_episode_skips_and_flags(self):
        b = static_episode()
        pl = SC.plan(b, 'cyl', 3, gen_views=[0])
        self.assertTrue(pl['gen_view_overlap'])
        self.assertEqual(pl['removed'], [])
        self.assertFalse(pl['holdout']['applied'])
        self.assertGreater(pl['holdout']['near_frac'], 0.8)
        full = SY.cylinder()
        cands = [dict(cid='gen', cls='GEN', mesh=full, n_params=0, gen_input_frames=[0]),
                 dict(cid='shell', cls='SHELL', mesh=full, n_params=0)]
        pool = SC.score_pool(cands, b, 'cyl', kind=None, amb=False)
        self.assertTrue(pool['gen_view_overlap'])
        p = SEL.pick(pool['rows'], gen_view_overlap=pool['gen_view_overlap'])
        self.assertEqual(p['order'], ['shell', 'gen'])            # generated E is optimistic: SHELL before GEN
        self.assertEqual(SEL.pick(pool['rows'])['order'], ['gen', 'shell'])


class FoldTests(unittest.TestCase):
    def test_fixed_partial_rebuilt(self):
        b = cyl_episode()
        pl = SC.plan(b, 'cyl', 3)
        ctx = dict(bundle=b, obj='cyl', block2=pl['blocks'][1]['frames'])
        folds, st = SC.build_folds(_Toy('h', 'HULL', 'raise'), ctx, pl)
        self.assertEqual((folds, st['state']), ({}, 'fixed'))
        from gmg.producers import hull as P_HULL
        folds, st = SC.build_folds(P_HULL, ctx, pl)                # the B1 HULL has no fold build yet (B4/B8)
        self.assertEqual(st['state'], 'fixed')
        folds, st = SC.build_folds(_Toy('s', 'SHELL', 'skip2'), ctx, pl)
        self.assertEqual(st['missing'], {'s': [1]})
        ms, state = SC.fold_meshes(SY.cylinder(), folds['s'], 3)
        self.assertEqual(state, 'partial')
        ev = SC.evidence(ms, b, 'cyl', pl['blocks'], 0.0)
        self.assertAlmostEqual(ev['R_blocks'][1], 10.0, places=4)  # no candidate on fold 2: every ray missing
        self.assertLess(ev['R_blocks'][0], 1.0)
        folds, st = SC.build_folds(_Toy('t', 'STRUCT', 'always'), ctx, pl)
        self.assertEqual((st['state'], st['missing']), ('rebuilt', {}))
        self.assertEqual(SC.fold_meshes(SY.cylinder(), folds['t'], 3)[1], 'rebuilt')


class B5Synthetic(unittest.TestCase):
    """SPEC 24 B5 pass condition, synthetic tests (the fourth, the deterministic tie order, is also in
    test_select.OrderTests)."""

    def test_a_cylinder_missing_base_charged_on_heldout_base_rays(self):
        b = cyl_episode()
        s = b.sigma('cyl')
        pl = SC.plan(b, 'cyl', 3)
        obs = b.obs('cyl')
        idx3 = pl['blocks'][2]['idx']
        P3 = np.asarray(obs['pts'], np.float64)[idx3]
        base = (P3[:, 2] < -0.039) & (np.hypot(P3[:, 0], P3[:, 1]) < 0.035)
        self.assertGreater(int(base.sum()), 500)                    # block 3 sees the base
        for blk in (0, 1):
            Pk = np.asarray(obs['pts'], np.float64)[pl['blocks'][blk]['idx']]
            self.assertEqual(int(((Pk[:, 2] < -0.039) & (np.hypot(Pk[:, 0], Pk[:, 1]) < 0.035)).sum()), 0)
        full, nobase = SY.cylinder(), SY.without_base(SY.cylinder())
        res = {}
        for nm, m in (('full', full), ('nobase', nobase)):
            delta, cost, _ = SC.ray_costs(m, b, 'cyl', idx3[base])
            res[nm] = dict(base_rays=int(base.sum()), miss_frac=float((delta > 3 * s).mean()),
                           mean_cost_sigma=float(cost.mean() / s))
        self.assertGreaterEqual(res['nobase']['miss_frac'], 0.95)  # charged on the held-out base rays
        self.assertGreaterEqual(res['nobase']['mean_cost_sigma'], 9.0)
        self.assertLessEqual(res['full']['miss_frac'], 0.05)
        self.assertLess(res['full']['mean_cost_sigma'], 1.0)
        # through the producers: a shell rebuilt without block 3 has no base and is charged on block 3; a structured
        # completion keeps it. The all-frames form (no rebuild) cannot see the difference.
        ctx = dict(bundle=b, obj='cyl')
        shell_p, struct_p = _Toy('shell_toy', 'SHELL', 'seen'), _Toy('lathe_toy', 'STRUCT', 'always', n_params=4)
        cands = shell_p.produce(ctx) + struct_p.produce(ctx)
        self.assertEqual(len(cands[0].mesh.faces), len(full.faces))   # the all-frames shell saw the base
        folds = {}
        for prod in (shell_p, struct_p):
            f, st = SC.build_folds(prod, ctx, pl)
            self.assertEqual(st['state'], 'rebuilt')
            folds.update(f)
        self.assertLess(len(folds['shell_toy'][2].faces), len(full.faces))   # fold 3 (without block 3): no base
        pool = SC.score_pool(cands, b, 'cyl', folds=folds, kind=None, amb=False)
        flat = SC.score_pool(cands, b, 'cyl', folds=None, kind=None, amb=False)
        r = {x['cid']: x for x in pool['rows']}; rf = {x['cid']: x for x in flat['rows']}
        self.assertEqual((r['shell_toy']['fold'], rf['shell_toy']['fold']), ('rebuilt', 'fixed'))
        self.assertGreater(r['shell_toy']['E_blocks'][2], 3.0)
        self.assertLess(r['lathe_toy']['E_blocks'][2], 1.0)
        self.assertLess(abs(rf['shell_toy']['E'] - rf['lathe_toy']['E']), 1e-9)   # identical meshes all-frames
        p = SEL.pick(pool['rows'])
        dE = r['shell_toy']['E'] - r['lathe_toy']['E']
        sd = SC.se_diff(r['shell_toy']['E_reps'], r['lathe_toy']['E_reps'])
        self.assertGreater(dE, 3 * sd)
        self.assertEqual((p['best'], p['cid'], [c for c, _, _ in p['tie_set']]), ('lathe_toy', 'lathe_toy',
                                                                                  ['lathe_toy']))
        _record_b5('B5-a cylinder missing base', dict(
            fixed_meshes=res, folds={k: _row_summary(v) for k, v in r.items()},
            all_frames={k: _row_summary(v) for k, v in rf.items()}, dE=dE, se_diff=sd,
            pick={k: p[k] for k in ('cid', 'best', 'tie_set', 'order', 'flags')}))

    def test_b_phantom_under_disc_high_fsv_far(self):
        b = disc_episode()
        obs = b.obs('disc')
        d, ph = SY.disc(), SY.phantom_under(SY.disc())
        fd, fp = SC.fsv_far(d, obs)['fsv_far'], SC.fsv_far(ph, obs)['fsv_far']
        self.assertLessEqual(fd, 0.01)
        self.assertGreaterEqual(fp, 0.3)
        # V3 with a tau from a fold null of honest candidates (here: the disc and a slightly thicker disc rebuilt per
        # fold are identical meshes, so the null is zero and tau = 0); the phantom is vetoed, the disc is not
        null = SC.fold_fsv_diffs([SY.disc(t=0.012)] * 3, [d] * 3, obs)          # D(c, k), all-frames grid
        self.assertEqual(SC.fold_fsv_diffs([ph, None], [d, d], obs)[1], None)
        self.assertAlmostEqual(SC.fold_fsv_diffs([ph], [d], obs)[0], fp - fd, places=12)
        tau = SC.tau_q99(null)
        self.assertEqual(tau, 0.0)
        self.assertAlmostEqual(SC.tau_q99(list(np.arange(101) / 100.0) + [None, float('nan')]), 0.99, places=12)
        cands = [dict(cid='disc_shell', cls='SHELL', mesh=d, n_params=0),
                 dict(cid='disc_phantom', cls='GEN', mesh=ph, n_params=0, gen_input_frames=[0])]
        pool = SC.score_pool(cands, b, 'disc', kind=None, tau=tau, amb=False)
        self.assertEqual(pool['flags'], [])
        r = {x['cid']: x for x in pool['rows']}
        self.assertTrue(r['disc_phantom']['v3']['veto']); self.assertFalse(r['disc_shell']['v3']['veto'])
        self.assertAlmostEqual(r['disc_phantom']['v3']['diff'], fp - fd, places=9)
        p = SEL.pick(pool['rows'], gen_view_overlap=pool['gen_view_overlap'])
        self.assertEqual(p['cid'], 'disc_shell')
        self.assertEqual(p['trace'][0]['removed'], {'disc_phantom': ['V3']})
        nogv = [dict(c) for c in cands]
        nogv[1].pop('gen_input_frames')
        self.assertEqual(SC.score_pool(nogv, b, 'disc', kind=None, amb=False)['flags'], ['gen_input_frames_missing'])
        pool0 = SC.score_pool(cands, b, 'disc', kind=None, tau=None, amb=False)    # before B13: reported only
        r0 = {x['cid']: x for x in pool0['rows']}
        self.assertFalse(r0['disc_phantom']['v3']['applied'])
        self.assertGreater(r0['disc_phantom']['E'], r0['disc_shell']['E'] + 10 * 0.3 - 1e-9)   # 10 x fsv_far in E
        _record_b5('B5-b phantom under disc', dict(fsv_disc=fd, fsv_phantom=fp, tau=tau, holdout=pool['holdout'],
                                                    rows={k: _row_summary(v) for k, v in r.items()},
                                                    pick={k: p[k] for k in ('cid', 'trace', 'flags')}))

    def test_c_slab_flip_risk_without_balls_not_with_trusted_balls(self):
        slab, balls = AM.slab(), AM.slab_with_balls()
        a0, a1 = SC.self_ambiguity(slab), SC.self_ambiguity(balls)
        self.assertTrue(a0['flip_risk']); self.assertFalse(a1['flip_risk'])
        b = slab_episode()
        cands = [dict(cid='slab_balls', cls='STRUCT', mesh=balls, base_mesh=slab, balls=len(AM.BALLS), n_params=6),
                 dict(cid='slab_plain', cls='STRUCT', mesh=slab, n_params=6)]
        out = {}
        for trusted in (True, False):
            pool = SC.score_pool(cands, b, 'slab', kind=None, trusted=trusted, flip_margin=True)
            r = {x['cid']: x for x in pool['rows']}
            p = SEL.pick(pool['rows'])
            v5 = [t for t in p['trace'] if t['step'] == 'V5'][0]
            out[f'trusted={trusted}'] = dict(rows={k: _row_summary(v) | dict(obs_flip_margin=v['obs_flip_margin'])
                                                   for k, v in r.items()},
                                             pick={k: p[k] for k in ('cid', 'tie_set', 'order', 'flags')}, v5=v5)
            self.assertTrue(r['slab_plain']['amb']['flip_risk'])
            self.assertTrue(r['slab_balls']['amb_noball']['flip_risk'])
            self.assertEqual(r['slab_balls']['trusted_markers'], len(AM.BALLS) if trusted else 0)
            if trusted:
                self.assertFalse(r['slab_balls']['amb']['flip_risk'])            # trusted balls break the flip
                self.assertTrue(v5['applied']); self.assertEqual(v5['removed'], ['slab_plain'])
                self.assertEqual(p['cid'], 'slab_balls'); self.assertNotIn('flip_risk', p['flags'])
            else:
                self.assertTrue(r['slab_balls']['amb']['flip_risk'])             # untrusted balls: ball-free
                self.assertFalse(v5['applied'])
                self.assertIn('flip_risk', p['flags'])
        _record_b5('B5-c slab flip risk', out)

    def test_d_tie_order_deterministic_on_scored_pool(self):
        b = cyl_episode()
        full = SY.cylinder()
        cands = [dict(cid=c, cls=k, mesh=full, n_params=n) for c, k, n in
                 (('s2', 'STRUCT', 4), ('s1', 'STRUCT', 4), ('sh', 'SHELL', 0), ('hu', 'HULL', 0), ('s0', 'STRUCT', 2))]
        pool = SC.score_pool(cands, b, 'cyl', kind=None, amb=False)
        ref = SEL.pick(pool['rows'])
        self.assertEqual(ref['order'], ['s0', 's1', 's2', 'sh', 'hu'])         # identical E: class, params, cid
        for perm in itertools.permutations(pool['rows']):
            p = SEL.pick(list(perm))
            self.assertEqual((p['cid'], p['order'], p['tie_set']), (ref['cid'], ref['order'], ref['tie_set']))
        _record_b5('B5-d tie order', dict(order=ref['order'], tie_set=ref['tie_set'], permutations=120))


if __name__ == '__main__':
    if guard.mode() != 'dev':
        raise SystemExit('test_score runs in GMG_MODE=dev (dev bundles, fixtures)')
    argv = [sys.argv[0]] + sys.argv[1:]
    t = time.time()
    res = unittest.main(argv=argv, verbosity=2, exit=False)
    print(f'{time.time() - t:.0f} s')
    sys.exit(0 if res.result.wasSuccessful() else 1)
