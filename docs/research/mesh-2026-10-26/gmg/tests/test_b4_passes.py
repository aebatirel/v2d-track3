"""Unit tests of the B4 decision code that verification round 1 found untested (round 2): extract_joint passes 2-3
(det_candidates, det_seed_select, proposal_points, seeded_component, crop_guard, resolve_ties, pair_flags), track_sanity.check,
split_test and the failing path of cross_test (also reg_chamfers), tools/b4_b2a.direction, contact.frame_gaps.
Synthetic data only; no data file is read.

  GMG_MODE=clean python -m unittest gmg.tests.test_b4_passes   (from docs/research/mesh-2026-10-26)
"""
import os
import sys
import unittest
from unittest import mock

import numpy as np
from scipy.spatial import cKDTree

HERE = os.path.dirname(os.path.abspath(__file__))
MR = os.path.dirname(os.path.dirname(HERE))
if MR not in sys.path:
    sys.path.insert(0, MR)

from gmg import extract_joint as EJ, track_sanity as TS, contact as CT  # noqa: E402

C = dict(vox=0.004, cube=0.30, zmin=0.05, zmax=1.5, hit=0.004, free=0.010, min_hits=3, min_ratio=0.5, tie_se=2.0,
         guard_k=1.5, guard_min=0.02, guard_frac=0.25, grid_margin=0.02, near_seed=0.5, comoving=0.5)
W = EJ.IMG_W


def _pix(v, u):
    return np.asarray(v, np.int64) * W + np.asarray(u, np.int64)


class DetSeedTests(unittest.TestCase):
    def setUp(self):
        # half-resolution proposals (scale 2) on a 20 x 30 grid
        self.props = np.zeros((4, 20, 30), bool)
        self.props[0, 2:10, 2:12] = True        # object A's whole mask
        self.props[1, 4:6, 4:6] = True          # a small part of A (holds A's origin too)
        self.props[2, 0:20, 0:30] = True        # the whole image: holds both origins -> never used
        self.props[3, 12:18, 15:25] = True      # object B's mask
        self.org0 = {'A': (2 * 5 + 0.5, 2 * 5 + 0.5), 'B': (2 * 20, 2 * 15)}   # full-res (u, v)

    def test_candidates_exclusive(self):
        self.assertEqual(EJ.det_candidates(self.props, 2.0, self.org0, ['A', 'B'], 'A'), [0, 1])
        self.assertEqual(EJ.det_candidates(self.props, 2.0, self.org0, ['A', 'B'], 'B'), [3])
        self.assertEqual(EJ.det_candidates(None, 2.0, self.org0, ['A', 'B'], 'A'), [])
        self.assertEqual(EJ.det_candidates(self.props, 2.0, dict(self.org0, A=None), ['A', 'B'], 'A'), [])

    def _samples(self):
        # frame-0 samples inside A's mask (half-res rows 2-9, cols 2-11): A-owned only at the part (rows 4-5,
        # cols 4-5), the rest unowned, one B-owned, one shared A|B, one shared B|C (not A); one outside A's cube
        rows, cols = np.mgrid[2:10, 2:12]
        hv, hu = rows.ravel(), cols.ravel()
        n = len(hv)
        own = np.full(n, EJ.NONE, np.int8)
        tied = np.zeros(n, np.uint8)
        part = (hv >= 4) & (hv < 6) & (hu >= 4) & (hu < 6)
        own[part] = 0
        own[0] = 1                                   # B-owned
        own[1], tied[1] = EJ.SHARED, 0b011           # shared A|B -> A-tied
        own[2], tied[2] = EJ.SHARED, 0b110           # shared B|C -> not A
        lin = np.arange(n, dtype=np.int32)
        lin[3] = -1                                  # outside A's cube
        pix = _pix(2 * hv, 2 * hu)
        return own, tied, pix, lin, part

    def test_seed_select_round2(self):
        own, tied, pix, lin, part = self._samples()
        cand = EJ.det_candidates(self.props, 2.0, self.org0, ['A', 'B'], 'A')
        sel, info = EJ.det_seed_select(self.props, 2.0, cand, 0, own, tied, pix, lin)
        # the footprint (A-owned or A-tied samples) is the part + sample 1: proposal 1 (the part) has the larger IoU
        self.assertEqual(info['det_index'], 1)
        # inside proposal 1: the 4 part samples (A-owned), all kept
        self.assertEqual(int(sel.sum()), 4)
        self.assertTrue(np.all(sel[part]))

    def test_seed_select_whole_mask(self):
        # A owns half of its mask: proposal 0 wins on IoU; the seed is every sample of the mask that no other object
        # owns (unowned included), not only A's provisional points (the round-1 restriction, DEVIATIONS 86)
        own, tied, pix, lin, part = self._samples()
        hv = (pix // W) // 2
        own[(hv >= 6) & (own == EJ.NONE)] = 0
        cand = [0, 1]
        sel, info = EJ.det_seed_select(self.props, 2.0, cand, 0, own, tied, pix, lin)
        self.assertEqual(info['det_index'], 0)
        exp = np.ones(len(own), bool)
        exp[[0, 2, 3]] = False                       # B-owned, shared without A, outside A's cube
        np.testing.assert_array_equal(sel, exp)
        self.assertEqual(info['seed_other_excluded'], 2)
        self.assertEqual(info['seed_in_proposal'], len(own) - 1)
        self.assertGreater(info['seed_unowned'], 0)
        mine = EJ._tied_with(own, tied, 0)
        self.assertLess(int((mine & sel).sum()), int(sel.sum()))     # round 1 would have kept only these

    def test_no_candidate_or_footprint(self):
        own, tied, pix, lin, _ = self._samples()
        sel, info = EJ.det_seed_select(self.props, 2.0, [], 0, own, tied, pix, lin)
        self.assertIsNone(sel)
        own2 = np.full(len(own), EJ.NONE, np.int8)          # no A footprint: IoU 0 everywhere, no proposal chosen
        sel, info = EJ.det_seed_select(self.props, 2.0, [0, 1], 0, own2, np.zeros(len(own), np.uint8), pix, lin)
        self.assertIsNone(sel)
        self.assertIsNone(info['det_index'])


class ComponentGuardTests(unittest.TestCase):
    n = 150

    def _lin(self, ijk):
        ijk = np.asarray(ijk)
        return (ijk[:, 0] * self.n + ijk[:, 1]) * self.n + ijk[:, 2]

    def _ctr(self, ijk):
        return -C['cube'] + (np.asarray(ijk, float) + 0.5) * C['vox']

    def test_seeded_component(self):
        a = [(50, 50, z) for z in range(50, 60)]          # a rod
        b = [(90, 90, z) for z in range(50, 60)]          # a second rod far away
        vset = np.sort(self._lin(a + b))
        lab = EJ._components(vset, self.n)
        cm, labs = EJ.seeded_component(vset, lab, self._ctr([(50, 50, 52)]), C, self.n)
        self.assertEqual(len(labs), 1)
        self.assertEqual(int(cm.sum()), 10)
        self.assertTrue(cm[self._lin([(50, 50, 55)])[0]])
        self.assertFalse(cm[self._lin([(90, 90, 55)])[0]])
        cm0, _ = EJ.seeded_component(vset, lab, np.zeros((0, 3)), C, self.n)
        self.assertEqual(int(cm0.sum()), 0)

    def test_guard_fires_and_clips(self):
        # a 40-voxel (160 mm) slab component; the seed covers 10 voxels (40 mm) of it: 160 > 1.5 x 40 -> clipped to
        # the seed box + max(20 mm, 25 %) = +-20 mm, i.e. 80 mm of the slab
        ijk = [(60 + i, 60 + j, 60) for i in range(40) for j in range(5)]
        cm = np.zeros(self.n ** 3, bool)
        cm[self._lin(ijk)] = True
        seed = self._ctr([(70 + i, 60 + j, 60) for i in range(10) for j in range(5)])
        seed = np.vstack([seed - [0, 0, 0.0015], seed + [0, 0, 0.0015]])     # points spread within their voxels
        cm2, box, info = EJ.crop_guard(cm, seed, C, self.n)
        self.assertTrue(info['guard'])
        kept = np.stack(np.unravel_index(np.nonzero(cm2)[0], (self.n,) * 3), 1)
        self.assertIn(int(kept[:, 0].min()), (65, 66))     # seed centres 70-79 -/+ 20 mm (5 voxels), boundary
        self.assertIn(int(kept[:, 0].max()), (83, 84))
        self.assertEqual(info['component_voxels_after_guard'], int(cm2.sum()))
        self.assertAlmostEqual(box[0][0], seed[:, 0].min() - 0.02)

    def test_guard_quiet_and_no_seed(self):
        ijk = [(60 + i, 60 + j, 60) for i in range(12) for j in range(5)]
        cm = np.zeros(self.n ** 3, bool)
        cm[self._lin(ijk)] = True
        seed = self._ctr([(61 + i, 60 + j, 60) for i in range(10) for j in range(5)])  # 36 vs 48 mm: < 1.5x
        seed = np.vstack([seed - [0, 0, 0.0015], seed + [0, 0, 0.0015]])
        cm2, box, info = EJ.crop_guard(cm, seed, C, self.n)
        self.assertFalse(info['guard'])
        self.assertEqual(int(cm2.sum()), int(cm.sum()))
        ctr = self._ctr(ijk)
        np.testing.assert_allclose(box[0], ctr.min(0) - C['vox'] / 2 - C['grid_margin'])
        cm3, box3, info3 = EJ.crop_guard(cm, np.zeros((0, 3)), C, self.n)       # no seed: no guard
        self.assertFalse(info3['guard'])
        self.assertEqual(int(cm3.sum()), int(cm.sum()))
        self.assertIsNone(EJ.crop_guard(np.zeros(self.n ** 3, bool), seed, C, self.n)[1])


class ProposalExtentTests(unittest.TestCase):
    def test_proposal_points_keep_table_band(self):
        # a flat 10 x 6 cm slab whose top lies 4 mm above the table plane (inside the 8 mm band): every proposal pixel
        # with depth becomes a box point, except hand-capsule pixels, pixels another object owns and pixels out of
        # the cube
        K = np.array([[600.0, 0, 800], [0, 600.0, 500], [0, 0, 1]])
        D = np.full((1000, 1600), np.nan, np.float32)
        D[400:600, 700:900] = 0.5
        c = dict(C, edge=0.02)
        mask = np.zeros((500, 800), bool)
        mask[200:300, 350:450] = True                   # half-res: covers full-res rows 400-599, cols 700-899
        T = np.eye(4)
        T[2, 3] = 0.5
        P = EJ.proposal_points(mask, 2.0, D, K, T, c)
        self.assertGreater(len(P), 30000)
        self.assertLess(np.abs(P[:, 2]).max(), 1e-6)
        ext = P.max(0) - P.min(0)
        self.assertAlmostEqual(ext[0], 199 * 0.5 / 600, delta=0.002)
        # a hand capsule over the left half, and pixels owned by another object, are left out
        seg = (np.array([[-0.2, 0.0, 0.5]]), np.array([[-0.05, 0.0, 0.5]]), np.array([0.05]))
        other = np.arange(500, 600, dtype=np.int64) * 1600 + 850
        P2 = EJ.proposal_points(mask, 2.0, D, K, T, c, seg=seg, other_pix=other)
        self.assertLess(len(P2), len(P))
        Pc2 = P2 + [0, 0, 0.5]                          # camera frame
        h = np.clip((Pc2[:, 0] + 0.2) / 0.15, 0, 1)
        dseg = np.linalg.norm(Pc2 - (np.array([-0.2, 0, 0.5]) + h[:, None] * [0.15, 0, 0]), axis=1)
        self.assertGreater(dseg.min(), 0.05 - 1e-9)      # nothing inside the capsule
        self.assertLess(P[:, 0].min(), -0.08)            # (those pixels were there before)
        Pc = P2 @ np.eye(3).T + [0, 0, 0.5]
        u = np.rint(600 * Pc[:, 0] / Pc[:, 2] + 800).astype(int)
        v = np.rint(600 * Pc[:, 1] / Pc[:, 2] + 500).astype(int)
        self.assertFalse(np.any((u == 850) & (v >= 500)))

    def test_box_points_widen_seed_box(self):
        # the round-1 failure mode: a seed of a few points on a large flat component fires the guard and clips it;
        # with the proposal's extent as box points the guard keeps the component
        n = 150
        ijk = [(60 + i, 60 + j, 60) for i in range(40) for j in range(25)]
        cm = np.zeros(n ** 3, bool)
        cm[(np.array(ijk)[:, 0] * n + np.array(ijk)[:, 1]) * n + 60] = True
        ctr = -C['cube'] + (np.array(ijk, float) + 0.5) * C['vox']
        seed = ctr[(np.array(ijk)[:, 0] < 63) & (np.array(ijk)[:, 1] < 63)]
        seed = np.vstack([seed - [0, 0, 0.002], seed + [0, 0, 0.002]])
        cm1, _, i1 = EJ.crop_guard(cm, seed, C, n)
        self.assertTrue(i1['guard'])
        self.assertLess(int(cm1.sum()), int(cm.sum()))
        bp = np.vstack([ctr - [0, 0, 0.002], ctr + [0, 0, 0.002]])
        cm2, _, i2 = EJ.crop_guard(cm, seed, C, n, box_pts=bp)
        self.assertFalse(i2['guard'])
        self.assertEqual(int(cm2.sum()), int(cm.sum()))
        self.assertIn('seed_box_points_mm', i2)


class TieBreakTests(unittest.TestCase):
    def setUp(self):
        # two objects at the camera origin frame (identity poses); seeds: A around x = 0, B around x = 0.1 m
        self.T = [np.eye(4), np.eye(4)]
        self.trees = [cKDTree(np.array([[0.0, 0, 0.5]])), cKDTree(np.array([[0.1, 0, 0.5]]))]

    def test_rules_a_b_c(self):
        P = np.array([[0.01, 0, 0.5],     # tied, inside A's mask only -> (a) A
                      [0.09, 0, 0.5],     # tied, inside both masks -> (b): B's seed 10 mm, A's 90 mm -> B
                      [0.05, 0, 0.5],     # tied, inside no mask, equidistant -> (c) shared
                      [0.02, 0, 0.5],     # owned by A already -> untouched
                      [0.04, 0, 0.5]])    # tied A|B, (b): 40 vs 60 mm -> not below half -> shared
        own = np.array([EJ.SHARED, EJ.SHARED, EJ.SHARED, 0, EJ.SHARED], np.int8)
        tied = np.array([3, 3, 3, 0, 3], np.uint8)
        mh = np.array([[True, False], [True, True], [False, False], [True, False], [False, False]])
        o2, how = EJ.resolve_ties(own, tied, P, self.T, self.trees, C, mask_hits=mh)
        self.assertEqual(o2.tolist(), [0, 1, EJ.SHARED, 0, EJ.SHARED])
        self.assertEqual(how.tolist(), [1, 2, 3, 0, 3])
        self.assertEqual(own[0], EJ.SHARED)            # input untouched

    def test_without_masks_and_missing_seed(self):
        P = np.array([[0.01, 0, 0.5], [0.095, 0, 0.5]])
        own = np.array([EJ.SHARED, EJ.SHARED], np.int8)
        tied = np.array([3, 3], np.uint8)
        o2, how = EJ.resolve_ties(own, tied, P, self.T, self.trees, C)
        self.assertEqual(o2.tolist(), [0, 1])
        self.assertEqual(how.tolist(), [2, 2])
        # B has no seed (DEVIATIONS 101): no distance for B, the samples stay shared
        o3, how3 = EJ.resolve_ties(own, tied, P, self.T, [self.trees[0], None], C)
        self.assertEqual(o3.tolist(), [EJ.SHARED, EJ.SHARED])
        self.assertEqual(how3.tolist(), [3, 3])

    def test_pose_used(self):
        # B's frame is shifted: a sample at camera x = 0.2 is at B-frame x = 0.1 (its seed) -> B
        T = [np.eye(4), np.eye(4)]
        T[1][:3, 3] = [0.1, 0, 0]
        o2, how = EJ.resolve_ties(np.array([EJ.SHARED], np.int8), np.array([3], np.uint8),
                                  np.array([[0.2, 0, 0.5]]), T, self.trees, C)
        self.assertEqual(int(o2[0]), 1)


class PairFlagTests(unittest.TestCase):
    def test_flags(self):
        pt = dict(n=100, tied1=80, tied1_frac=0.8, pass3=dict(decided_by_ratio_or_component=0, mask=5, seed=20,
                                                              shared=55))
        self.assertEqual(EJ.pair_flags(pt, C), (True, True, 'seed', 80))
        pt = dict(n=100, tied1=80, tied1_frac=0.8, pass3=dict(decided_by_ratio_or_component=0, mask=50, seed=20,
                                                              shared=10))
        self.assertEqual(EJ.pair_flags(pt, C), (True, False, 'mask', 80))
        pt = dict(n=100, tied1=10, tied1_frac=0.1, pass3=dict(decided_by_ratio_or_component=0, mask=0, seed=0,
                                                              shared=10))
        self.assertEqual(EJ.pair_flags(pt, C), (False, False, 'none', 10))


class _FakeBundle:
    """The parts of gmg.bundle.Bundle that track_sanity and b4_b2a read."""

    def __init__(self, obs, poses, T, sigma_m, table_frames=None, contact=None, good=None, stride=1):
        self.meta = dict(T=T, stride=stride, table_frames=table_frames or {}, good=good or {})
        self._obs, self.poses, self._sig, self._contact = obs, poses, sigma_m, contact or {}

    @property
    def objects(self):
        return list(self._obs)

    def obs(self, o):
        return self._obs[o]

    def sigma(self, o):
        return self._sig

    def frames(self):
        return list(range(0, int(self.meta['T']), int(self.meta['stride'])))

    def good_frames(self, o):
        return [f for f in self.frames() if self.meta['good'][o][f]]

    def contact(self, o, p):
        return self._contact[f'{o}|{p}']


def _plate(rng, n, half=(0.05, 0.03), z=0.0):
    P = np.column_stack([rng.uniform(-half[0], half[0], n), rng.uniform(-half[1], half[1], n), np.full(n, z)])
    return P + rng.normal(0, 0.0005, P.shape)


class TrackSanityTests(unittest.TestCase):
    def _bundle(self, T=30, bad_below=(), bad_jump=()):
        # a 10 x 6 cm plate seen from above in every frame, its frame = camera frame shifted to z = 0.5 m; the table
        # plane (camera frame) lies 2 cm below the plate: height = z_table - z, i.e. n = (0, 0, -1), d = 0.52
        rng = np.random.default_rng(0)
        pts, fr = [], []
        for f in range(T):
            X = _plate(rng, 400)
            if f in bad_jump:
                X = X + np.array([0.0, 0.0, 0.03])      # this frame's points 3 cm off the others (track jump)
            pts.append(X)
            fr.append(np.full(len(X), f))
        P = np.concatenate(pts)
        obs = dict(pts=P.astype(np.float32), frame=np.concatenate(fr).astype(np.int32), own=np.zeros(len(P), np.uint8),
                   cam=np.tile([0.0, 0.0, -0.5], (len(P), 1)).astype(np.float32))
        Tco = np.tile(np.eye(4), (T, 1, 1))
        Tco[:, 2, 3] = 0.5
        for f in bad_below:
            Tco[f, 2, 3] = 0.55                          # placed 3 cm below the table by this frame's track
        tf = {str(f): [[0.0, 0.0, -1.0], 0.52] for f in range(T)}
        return _FakeBundle(dict(a=obs), {'cam_T_a': Tco}, T, 0.001, table_frames=tf)

    def test_all_good(self):
        r = TS.check(self._bundle(), 'a')
        self.assertEqual(r['n_good'], 30)
        self.assertEqual(r['flags'], [])

    def test_below_table_and_jump(self):
        r = TS.check(self._bundle(bad_below=(3, 4), bad_jump=(20,)), 'a')
        self.assertEqual(sorted(r['bad_below']), [3, 4])
        self.assertIn(20, r['bad_resid'])
        self.assertFalse(r['good'][3])
        self.assertFalse(r['good'][20])
        self.assertTrue(r['good'][10])
        self.assertEqual(r['flags'], [])

    def test_track_fail(self):
        r = TS.check(self._bundle(T=30, bad_below=tuple(range(0, 30, 1))[:25]), 'a')
        self.assertLess(r['n_good'], 20)
        self.assertEqual(r['flags'], ['TRACK_FAIL'])


def _box_surface(rng, n, ext):
    ext = np.asarray(ext, float)
    P = rng.uniform(-1, 1, (n, 3)) * ext
    k = rng.integers(0, 3, n)
    P[np.arange(n), k] = np.sign(P[np.arange(n), k]) * ext[k]
    return P


class IdentityTests(unittest.TestCase):
    def test_reg_chamfers(self):
        rng = np.random.default_rng(4)
        A = _box_surface(rng, 1200, (0.04, 0.025, 0.01))
        B = A @ np.array([[0, -1, 0], [1, 0, 0], [0, 0, 1.0]]).T + 0.1
        r = TS.reg_chamfers(A, B)
        self.assertLess(r['mm'], 1.0)            # same points: the full-shell chamfer of the best transform ~ 0
        self.assertLessEqual(r['mm'], r['seed0_mm'] + 1e-9)
        self.assertEqual(TS.reg_chamfer(A, B), r['mm'])

    def test_cross_fails_on_swap(self):
        # ep1's "cup" shell is really a plate-like box (the other object): its nearest shell is the plate of ep3
        rng = np.random.default_rng(5)
        cup = lambda: _box_surface(rng, 700, (0.04, 0.04, 0.05))
        plate = lambda: _box_surface(rng, 700, (0.09, 0.06, 0.008))
        sh = {(1, 'cup'): plate(), (2, 'cup'): cup(), (3, 'plate'): plate(), (4, 'plate'): plate()}
        good = sorted(sh)
        r = TS.cross_test(sh, (1, 'cup'), good)
        self.assertTrue(r['testable'])
        self.assertFalse(r['pass_'])
        self.assertTrue(r['nearest'].endswith(':plate'))
        self.assertGreater(r['d_own_mm'], r['d_other_mm'])
        self.assertIn('seed0', r)
        self.assertFalse(r['seed0']['pass_'])
        r2 = TS.cross_test(sh, (2, 'cup'), good)            # the true cup's own reference is the swapped shell
        self.assertTrue(r2['testable'])
        nt = TS.cross_test(sh, (1, 'cup'), [k for k in good if k != (2, 'cup')])
        self.assertFalse(nt['testable'])                     # no other good episode of the cup
        # precomputed floats give the same verdict (b4_identity passes reg_chamfers dicts)
        ch = {(k1, k2): TS.reg_chamfer(sh[k1], sh[k2]) for k1, k2 in TS.cross_pairs(sh, good)}
        self.assertEqual(TS.cross_test(sh, (1, 'cup'), good, chamfers=ch)['pass_'], False)

    def test_split_test(self):
        rng = np.random.default_rng(6)
        cup = _box_surface(rng, 700, (0.04, 0.04, 0.05))
        plate = _box_surface(rng, 700, (0.09, 0.06, 0.008))
        good = [True] * 20
        b = _FakeBundle({'o': {}, 'p': {}}, {}, 20, 0.001, good={'o': good, 'p': good})
        halves = {}

        def fake_shell(obs, frames=None, **kw):
            if obs is b.obs('p'):
                return plate, {}
            return halves[(id(obs), frames[0] >= 10)], {}
        po, pp = b.obs('o'), b.obs('p')
        with mock.patch.object(TS, 'route_a_shell', fake_shell):
            # no swap: both halves are the cup, the partner is the plate
            halves.update({(id(po), False): cup, (id(po), True): cup + 0.001})
            r = TS.split_test(b, 'o', 'p')
            self.assertTrue(r['pass_'])
            self.assertTrue(r['seed0']['pass_'])
            # mid-episode swap: the second half of o's track holds the plate
            halves.update({(id(po), True): plate + 0.001})
            r = TS.split_test(b, 'o', 'p')
            self.assertFalse(r['pass_'])


class LeakageDirectionTests(unittest.TestCase):
    def test_direction_counts_partner_surface(self):
        # target o: a plate at z = 0 (object frame = camera frame). Frames 0-11 separated (reference), 12-19 contact.
        # In contact frames the partner p (a plate at z = 6 mm) touches, and o's owned points also hold 50 points of
        # p's surface (leakage) per frame among 400 of its own.
        sys.path.insert(0, os.path.join(MR, 'gmg', 'tools'))
        import b4_b2a
        rng = np.random.default_rng(7)
        po, fo, pp, fp = [], [], [], []
        for f in range(20):
            X = _plate(rng, 400)
            if f >= 12:
                X = np.vstack([X, _plate(rng, 50, half=(0.03, 0.02), z=0.006)])
                Y = _plate(rng, 300, half=(0.03, 0.02), z=0.006)
                pp.append(Y)
                fp.append(np.full(len(Y), f))
            po.append(X)
            fo.append(np.full(len(X), f))
        mk = lambda P, F: dict(pts=np.concatenate(P).astype(np.float32), frame=np.concatenate(F).astype(np.int32),
                               own=np.zeros(sum(len(x) for x in P), np.uint8),
                               cam=np.tile([0.0, 0.0, 0.5], (sum(len(x) for x in P), 1)).astype(np.float32))
        poses = {'cam_T_o': np.tile(np.eye(4), (20, 1, 1)), 'cam_T_p': np.tile(np.eye(4), (20, 1, 1))}
        rec = dict(sep3d=list(range(12)), contact=list(range(12, 20)))
        b = _FakeBundle(dict(o=mk(po, fo), p=mk(pp, fp)), poses, 20, 0.0007, contact={'o|p': rec})
        c = dict(min_frames=10, k_sigma=3.0, near=0.004, thr=0.01)
        r = b4_b2a.direction(b, 'o', 'p', c)
        self.assertTrue(r['testable'])
        self.assertEqual(r['owned_in_contact'], 8 * 450)
        self.assertAlmostEqual(r['leakage'], 50 / 450, delta=0.02)
        # fewer than 10 reference frames: not testable; the diagnostic override of the frame lists is honoured
        r2 = b4_b2a.direction(b, 'o', 'p', c, sep_frames=list(range(9)))
        self.assertFalse(r2['testable'])
        r3 = b4_b2a.direction(b, 'o', 'p', c, contact_frames=[12])
        self.assertEqual(r3['owned_in_contact'], 450)


class FrameGapTests(unittest.TestCase):
    def test_frame_gaps(self):
        a = {0: np.array([[0.0, 0, 0.5]]), 1: np.array([[0.0, 0, 0.5]])}
        b = {0: np.array([[0.005, 0, 0.5]]), 1: np.array([[0.05, 0, 0.5]])}
        g = CT.frame_gaps({'a': a, 'b': b}, [0, 1, 2], ['a', 'b'])
        self.assertEqual(g['a|b']['sep3d_frame'], [1])
        self.assertIsNone(g['a|b']['d3_frame_mm'][2])
        self.assertAlmostEqual(g['b|a']['d3_frame_mm'][0], 5.0, delta=2.1)   # 2 mm centroids


if __name__ == '__main__':
    unittest.main()
