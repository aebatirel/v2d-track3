"""B3 tests of gmg/remesh.py (M10): the six-direction ray vote against the exact winding number, and watertight
output (after the gmg's own copy of the kit decode) on synthetic closed, open, inverted, self-overlapping, floater and
thin inputs.

  GMG_MODE=dev python docs/research/mesh-2026-10-26/gmg/tests/test_remesh.py      (venv python)

Synthetic data only; no file is read. PREREG B.10 itself runs on the 104 gen-probe meshes through tools/b10_remesh.py.
"""
import os
import sys
import unittest

os.environ.setdefault('GMG_MODE', 'dev')
HERE = os.path.dirname(os.path.abspath(__file__))
GMG = os.path.dirname(HERE)
MR = os.path.dirname(GMG)
if MR not in sys.path:
    sys.path.insert(0, MR)
from gmg import guard  # noqa: E402,F401
import numpy as np  # noqa: E402
import trimesh  # noqa: E402

from gmg import geom, remesh as RM, score  # noqa: E402


def _decoded_watertight(m):
    v, f = score.kit_decode(m)
    tri = v[f]
    ar = 0.5 * np.linalg.norm(np.cross(tri[:, 1] - tri[:, 0], tri[:, 2] - tri[:, 0]), axis=1)
    return trimesh.Trimesh(v, f[ar > 1e-14], process=True).is_watertight


def _cup(r=0.04, h=0.08, t=0.003, sections=48):
    """An open-topped cup: outer cylinder minus inner cylinder, as a closed solid (annulus extrusion + base)."""
    outer = trimesh.creation.cylinder(radius=r, height=h, sections=sections)
    inner = trimesh.creation.cylinder(radius=r - t, height=h, sections=sections)
    inner.apply_translation([0, 0, t])
    return outer.difference(inner, engine='manifold')


class VoteTests(unittest.TestCase):
    def test_votes_match_exact_winding_closed(self):
        ext = np.array([0.0503, 0.0311, 0.0417])
        m = trimesh.creation.box(extents=ext)
        pitch = 0.004
        lo, shape = RM._grid(m, pitch)
        w, votes = RM.axis_votes(geom._tris(m), lo, shape, pitch)
        X = lo + np.indices(shape).reshape(3, -1).T * pitch
        ins = np.all(np.abs(X) < ext / 2, axis=1)
        self.assertTrue(np.array_equal(np.abs(w.ravel()) >= 0.5, ins))
        # every one of the six rays gives the exact winding number for a closed mesh
        self.assertTrue(np.all(votes.reshape(6, -1)[:, ins] == 1))
        self.assertTrue(np.all(votes.reshape(6, -1)[:, ~ins] == 0))

    def test_open_mesh_vote_close_to_gwn(self):
        m = trimesh.creation.icosphere(subdivisions=3, radius=0.03)
        keep = m.triangles_center[:, 2] < 0.024                    # a hole at the top (open mesh)
        m.update_faces(keep)
        pitch = 0.004
        lo, shape = RM._grid(m, pitch)
        w, _ = RM.axis_votes(geom._tris(m), lo, shape, pitch)
        X = lo + np.indices(shape).reshape(3, -1).T * pitch
        g = geom.winding_number(m, X)
        far = np.abs(np.linalg.norm(X, axis=1) - 0.03) > 0.004     # away from the surface
        agree = ((np.abs(w.ravel()) >= 0.5) == (g >= 0.5))[far].mean()
        self.assertGreater(agree, 0.99)


class WatertightTests(unittest.TestCase):
    def check(self, m, **kw):
        out, info = RM.watertight(m, **kw)
        self.assertTrue(info['watertight'], info)
        self.assertTrue(info['decode_watertight'], info)
        self.assertTrue(info['accepted'], info)
        self.assertLessEqual(len(out.faces), RM.BUDGET)
        self.assertTrue(_decoded_watertight(out), info)
        return out, info

    def test_sphere_volume(self):
        m = trimesh.creation.icosphere(subdivisions=4, radius=0.05)
        out, info = self.check(m)
        self.assertAlmostEqual(out.volume / m.volume, 1.0, delta=0.02)
        self.assertGreaterEqual(info['coverage'], 0.99)
        self.assertNotIn('thin_union', info['flags'])

    def test_open_sphere_closed(self):
        m = trimesh.creation.icosphere(subdivisions=4, radius=0.05)
        m.update_faces(m.triangles_center[:, 2] < 0.04)            # a 6 cm hole
        self.assertFalse(m.is_watertight)
        out, info = self.check(m)
        self.assertGreater(out.volume, 0.8 * (4 / 3) * np.pi * 0.05 ** 3)

    def test_inverted_sphere(self):
        m = trimesh.creation.icosphere(subdivisions=4, radius=0.05)
        m.invert()
        out, _ = self.check(m)
        self.assertAlmostEqual(out.volume / (4 / 3 * np.pi * 0.05 ** 3), 1.0, delta=0.03)

    def test_overlapping_bodies_union(self):
        a = trimesh.creation.box(extents=(0.06, 0.04, 0.04))
        b = trimesh.creation.box(extents=(0.04, 0.06, 0.04))
        b.apply_translation([0.02, 0.02, 0.0])
        m = trimesh.util.concatenate([a, b])                        # self-overlapping, not a valid solid
        out, info = self.check(m)
        u = a.union(b, engine='manifold')
        self.assertAlmostEqual(out.volume / u.volume, 1.0, delta=0.05)
        self.assertEqual(info['components'], 1)

    def test_floater_removed(self):
        a = trimesh.creation.icosphere(subdivisions=3, radius=0.04)
        f = trimesh.creation.icosphere(subdivisions=2, radius=0.006)
        f.apply_translation([0.08, 0, 0])
        out, info = self.check(trimesh.util.concatenate([a, f]))
        self.assertEqual(info['inside_components'], 2)                # the floater's voxels are dropped
        self.assertEqual(info['components'], 1)
        self.assertLess(out.bounds[1, 0], 0.05)                     # the floater is gone

    def test_cup_keeps_cavity(self):
        c = _cup()
        out, info = self.check(c)
        self.assertAlmostEqual(out.volume / c.volume, 1.0, delta=0.15)  # 3 mm wall on a 1.5 mm grid
        # the cavity stays open: a point in the middle of the cup is outside
        self.assertFalse(geom.inside(out, np.array([[0.0, 0.0, 0.02]]))[0][0])

    def test_thin_sheet(self):
        d = trimesh.creation.annulus(r_min=0.0, r_max=0.04, height=0.0004, sections=48)   # a 0.4 mm plate
        out, info = self.check(d)
        self.assertIn('thin_union', info['flags'])
        self.assertGreater(info.get('coverage_final', info['coverage']), 0.9)


if __name__ == '__main__':
    unittest.main(verbosity=2)
