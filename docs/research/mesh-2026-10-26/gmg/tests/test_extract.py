"""Unit tests of the B4 modules on synthetic data (no data file is read): extract_joint (ownership ties, the voxel
vote, 8 mm components), track_sanity (registration and chamfer, rotations), hands_cpu (capsule segments).

  GMG_MODE=clean python -m unittest gmg.tests.test_extract   (from docs/research/mesh-2026-10-26)
"""
import os
import sys
import unittest

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
MR = os.path.dirname(os.path.dirname(HERE))
if MR not in sys.path:
    sys.path.insert(0, MR)

from gmg import extract_joint as EJ, track_sanity as TS  # noqa: E402

C = dict(vox=0.004, cube=0.30, zmin=0.05, zmax=1.5, hit=0.004, free=0.010, min_hits=3, min_ratio=0.5, tie_se=2.0)


def _grid(h, f):
    return dict(hits=np.array(h, np.int32).reshape(1, 1, -1), free=np.array(f, np.int32).reshape(1, 1, -1))


class OwnershipTests(unittest.TestCase):
    def test_clear_winner(self):
        # voxel 0: object A 40/40 persistent, object B 20 hits 20 free (ratio 0.5, keep passes) -> A
        g = [_grid([40], [0]), _grid([20], [20])]
        own, tied, _ = EJ.owners([np.array([0]), np.array([0])], g, C)
        self.assertEqual(int(own[0]), 0)
        self.assertEqual(int(tied[0]), 0)

    def test_tie_is_shared(self):
        # both fully persistent (co-moving): tie -> shared, bitmask 0b11
        g = [_grid([30], [0]), _grid([28], [0])]
        own, tied, _ = EJ.owners([np.array([0]), np.array([0])], g, C)
        self.assertEqual(int(own[0]), EJ.SHARED)
        self.assertEqual(int(tied[0]), 3)

    def test_keep_rule_and_outside(self):
        # A fails the keep rule (2 hits), B outside its cube (-1): nobody
        g = [_grid([2], [0]), _grid([30], [0])]
        own, _, _ = EJ.owners([np.array([0]), np.array([-1])], g, C)
        self.assertEqual(int(own[0]), EJ.NONE)

    def test_allow_mask(self):
        g = [_grid([40], [0]), _grid([40], [0])]
        allow = [np.array([[[False]]]), np.array([[[True]]])]
        own, _, _ = EJ.owners([np.array([0]), np.array([0])], g, C, allow=allow)
        self.assertEqual(int(own[0]), 1)

    def test_few_frames_not_certain(self):
        # A: 3/3 (ratio 1, n 3), B: 45/50 (0.9): Agresti-Caffo SE keeps them tied (plain SE 0 would not)
        g = [_grid([3], [0]), _grid([45], [5])]
        own, tied, _ = EJ.owners([np.array([0]), np.array([0])], g, C)
        self.assertEqual(int(own[0]), EJ.SHARED)


class VoteTests(unittest.TestCase):
    def test_plane(self):
        # a fronto-parallel wall at z = 0.5 m seen by a camera at the origin; lattice along z through the wall
        K = np.array([[600.0, 0, 800], [0, 600.0, 500], [0, 0, 1]])
        D = np.full((1000, 1600), 0.5, np.float32)
        lab = np.ones(D.shape, np.int8)
        axes = (np.array([0.0]), np.array([0.0]), 0.40 + (np.arange(50) + 0.5) * 0.004)
        fl, (hl,) = EJ.vote(D, lab, np.eye(4), axes, K, C)
        z = axes[2]
        self.assertTrue(np.all(z[fl] < 0.5 - 0.010))
        self.assertTrue(np.all(np.abs(z[hl] - 0.5) < 0.004))
        self.assertEqual(len(hl), 2)
        lab[:] = 0
        _, (hl0,) = EJ.vote(D, lab, np.eye(4), axes, K, C)
        self.assertEqual(len(hl0), 0)


class ComponentTests(unittest.TestCase):
    def test_8mm(self):
        n = 150
        def lin(i, j, k):
            return (i * n + j) * n + k
        # two voxels 2 apart (8 mm) connect; a third 3 apart from the second (12 mm) does not
        s = np.array(sorted([lin(10, 10, 10), lin(10, 10, 12), lin(10, 10, 15)]))
        lab = EJ._components(s, n)
        self.assertEqual(lab[0], lab[1])
        self.assertNotEqual(lab[1], lab[2])
        # diagonal (1,1,1) = 6.9 mm connects; (2,1,0) = 8.9 mm does not
        s2 = np.array(sorted([lin(20, 20, 20), lin(21, 21, 21)]))
        self.assertEqual(len(set(EJ._components(s2, n))), 1)
        s3 = np.array(sorted([lin(30, 30, 30), lin(32, 31, 30)]))
        self.assertEqual(len(set(EJ._components(s3, n))), 2)


class RegistrationTests(unittest.TestCase):
    def test_rotations24(self):
        self.assertEqual(len(TS.ROT24), 24)
        for R in TS.ROT24:
            self.assertAlmostEqual(np.linalg.det(R), 1.0)

    def test_recover(self):
        rng = np.random.default_rng(1)
        # an asymmetric box surface (8 x 5 x 2 cm) with a bump: rotated and shifted copy registers back
        P = rng.uniform(-1, 1, (4000, 3)) * np.array([0.04, 0.025, 0.01])
        k = rng.integers(0, 3, 4000)
        P[np.arange(4000), k] = np.sign(P[np.arange(4000), k]) * np.array([0.04, 0.025, 0.01])[k]
        P = np.vstack([P, rng.normal([0.03, 0.015, 0.012], 0.003, (300, 3))])
        from scipy.spatial.transform import Rotation as Rot
        R = Rot.from_euler('xyz', [40, -70, 120], degrees=True).as_matrix()
        Q = P @ R.T + np.array([0.2, -0.1, 0.05])
        T, ch = TS.register(P, Q)
        # floor: two random 1500-point subsets of one surface lie about 1 mm apart (sampling, not misfit)
        self.assertLess(ch, 2.0)            # mm
        self.assertGreater(TS.chamfer_mm(P, Q), 20.0)

    def test_size_counts(self):
        rng = np.random.default_rng(2)
        P = rng.normal(0, 1, (3000, 3))
        P /= np.linalg.norm(P, axis=1, keepdims=True)
        A, B = 0.05 * P, 0.07 * P          # spheres of radius 5 and 7 cm: no scale normalisation
        self.assertGreater(TS.register(A, B)[1], 15.0)


class HandSegmentTests(unittest.TestCase):
    def test_bones(self):
        from gmg import hands_cpu
        self.assertEqual(len(hands_cpu.BONES), 21)
        sys.path.insert(0, os.path.join(os.path.dirname(MR), '..', '..', 'pipeline'))
        import recon_mesh
        self.assertEqual([tuple(b) for b in recon_mesh.BONES], hands_cpu.BONES)


if __name__ == '__main__':
    unittest.main()
