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


if __name__ == '__main__':
    if guard.mode() != 'dev':
        raise SystemExit('test_score runs in GMG_MODE=dev (dev bundles, fixtures)')
    argv = [sys.argv[0]] + sys.argv[1:]
    t = time.time()
    res = unittest.main(argv=argv, verbosity=2, exit=False)
    print(f'{time.time() - t:.0f} s')
    sys.exit(0 if res.result.wasSuccessful() else 1)
