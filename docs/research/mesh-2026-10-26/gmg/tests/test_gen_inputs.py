"""B2 tests of gmg/gen_inputs.py (M9 CPU part): view choice (filters, farthest-point spacing, one-view fallback,
contact mode, no qualifying view), exclusive masks (partner and hand pixels removed, a hand behind the target kept),
refinement cut-back, the PREREG B.11 partner-pixel test, and the dev_hands guard role.

  GMG_MODE=dev python docs/research/mesh-2026-10-26/gmg/tests/test_gen_inputs.py      (venv python)

Synthetic data only (no file but calib.json is read; the guard-role test opens nothing). PREREG B.11 itself runs on the
dev bundles of ep2, ep11, ep26 through tools/b11_views.py.
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
from gmg import guard  # noqa: E402
import numpy as np  # noqa: E402

from gmg import gen_inputs as GI  # noqa: E402


def _dir(az_deg, el_deg=30.0):
    a, e = np.radians(az_deg), np.radians(el_deg)
    return [float(np.cos(e) * np.cos(a)), float(np.cos(e) * np.sin(a)), float(np.sin(e))]


def _row(k, az, area=1000, hand=0.0, depth=0.9, partner=0.0, el=30.0):
    return dict(k=k, j=k + 1, area=area, area_fp=area, partner_share=partner, hand_share=hand, in_image=1.0,
                depth_share=depth, dir=_dir(az, el))


class _FakeBundle:
    """Minimal bundle: objects, partners, census in meta['contact'], obs (pts, own), poses, good frames."""

    def __init__(self, objs, sep=None, pts=None, poses=None, T=10):
        self.objects = list(objs)
        self.meta = dict(contact={})
        for o in objs:
            for p in objs:
                if o != p:
                    s = list(sep if sep is not None else range(T))
                    self.meta['contact'][f'{o}|{p}'] = dict(separated=s)
        self._pts = pts or {}
        self.poses = poses or {}
        self.T = T

    def partners(self, o):
        return [p for p in self.objects if p != o]

    def obs(self, o):
        return dict(pts=self._pts[o], own=np.zeros(len(self._pts[o]), np.uint8))

    def good_frames(self, o):
        return list(range(self.T))


class ChooseViewsTests(unittest.TestCase):
    def test_fps_spacing_and_first_view(self):
        rows = [_row(k, az=3.0 * k, area=1000 + (50 if k == 7 else 0)) for k in range(40)]   # 0..117 deg
        b = _FakeBundle(['a', 'b'], sep=range(40), T=40)
        views, rep = GI.choose_views(b, 'a', b.meta['contact'], table=rows)
        self.assertEqual(rep['mode'], 'separated')
        self.assertEqual(views[0].k, 7)                       # the largest visible area first
        self.assertEqual(len(views), 6)                       # capped at 6
        D = np.array([v.dir for v in views])
        ang = np.degrees(np.arccos(np.clip(D @ D.T, -1, 1)))
        self.assertGreaterEqual(ang[~np.eye(6, dtype=bool)].min(), 8.0 - 1e-9)
        self.assertNotIn('one_view', rep['flags'])
        self.assertNotIn('mv_skipped', rep['flags'])

    def test_hand_free_first(self):
        rows = [_row(0, 0, area=1000, hand=0.10), _row(1, 1, area=900, hand=0.0), _row(2, 2, area=950, hand=0.0)]
        b = _FakeBundle(['a', 'b'], T=3)
        views, rep = GI.choose_views(b, 'a', b.meta['contact'], table=rows)
        self.assertEqual(views[0].k, 2)                       # the largest hand-free view beats a larger handled one
        rows = [_row(0, 0, area=1000, hand=0.10), _row(1, 1, area=900, hand=0.05)]
        views, rep = GI.choose_views(b, 'a', b.meta['contact'], table=rows)
        self.assertEqual(views[0].k, 0)                       # no hand-free view: the largest visible area

    def test_one_view_fallback(self):
        rows = [_row(k, az=0.1 * k) for k in range(30)]       # span 2.9 deg < 8 deg
        b = _FakeBundle(['a', 'b'], T=30)
        views, rep = GI.choose_views(b, 'a', b.meta['contact'], table=rows)
        self.assertEqual(len(views), 1)
        self.assertIn('one_view', rep['flags'])
        self.assertIn('mv_skipped', rep['flags'])
        self.assertLess(rep['pool_span_deg'], 8.0)

    def test_two_views_skip_mv(self):
        rows = [_row(k, az=(0.0 if k < 10 else 12.0)) for k in range(20)]
        b = _FakeBundle(['a', 'b'], T=20)
        views, rep = GI.choose_views(b, 'a', b.meta['contact'], table=rows)
        self.assertEqual(len(views), 2)
        self.assertIn('mv_skipped', rep['flags'])
        self.assertNotIn('one_view', rep['flags'])

    def test_filters(self):
        rows = [_row(0, 0, area=1000), _row(1, 20, area=1000, hand=0.26), _row(2, 40, area=599),
                _row(3, 60, area=1000, depth=0.59), _row(4, 80, area=1000), _row(5, 100, area=1000),
                _row(6, 120, area=600, hand=0.25, depth=0.6)]
        b = _FakeBundle(['a', 'b'], sep=[0, 1, 2, 3, 4, 6], T=7)          # frame 5 is not separated
        views, rep = GI.choose_views(b, 'a', b.meta['contact'], table=rows)
        self.assertEqual(sorted(v.k for v in views), [0, 4, 6])           # boundaries are inclusive (<= 25 %, >= 0.6)
        self.assertTrue(all(v.mode == 'separated' for v in views))
        self.assertEqual(rep['qualifying'], 3)

    def test_no_partner_all_frames_separated(self):
        rows = [_row(k, az=10.0 * k) for k in range(5)]
        b = _FakeBundle(['a'], T=5)
        views, rep = GI.choose_views(b, 'a', b.meta['contact'], table=rows)
        self.assertEqual(rep['mode'], 'separated')
        self.assertIsNone(rep['separated'])
        self.assertEqual(len(views), 5)

    def test_contact_mode_least_overlap(self):
        rows = [_row(0, 0, partner=0.30), _row(1, 1, partner=0.10), _row(2, 30, partner=0.20),
                _row(3, 31, partner=0.05, hand=0.5), _row(4, 60, partner=0.25)]
        b = _FakeBundle(['a', 'b'], sep=[], T=5)
        views, rep = GI.choose_views(b, 'a', b.meta['contact'], table=rows)
        self.assertEqual(rep['mode'], 'contact')
        self.assertIn('contact_mode', rep['flags'])
        self.assertEqual([v.k for v in views], [1, 2, 4])                 # least overlap first, 8 deg apart, hands
        self.assertTrue(all(v.mode == 'contact' for v in views))

    def test_no_qualifying_view(self):
        rows = [_row(k, az=10.0 * k, hand=0.5) for k in range(5)]
        b = _FakeBundle(['a', 'b'], sep=[0, 1], T=5)
        views, rep = GI.choose_views(b, 'a', b.meta['contact'], table=rows)
        self.assertEqual(views, [])
        self.assertIn('no_qualifying_view', rep['flags'])
        self.assertEqual(rep['mode'], 'separated')                        # separated frames exist: no contact mode


def _geo():
    K = np.array([[600.0, 0, 320], [0, 600.0, 240], [0, 0, 1]])
    return GI.Geo(Ka=K.copy(), Da=np.zeros(5), T_a_rect=np.eye(4), W=640, H=480, K_rect=K.copy(), a_offset=1)


def _disc(cx, cy, r, z, n=4000, seed=0):
    rng = np.random.default_rng(seed)
    a = rng.uniform(0, 2 * np.pi, n)
    s = r * np.sqrt(rng.uniform(0, 1, n))
    return np.stack([cx + s * np.cos(a), cy + s * np.sin(a), np.full(n, z)], 1)


class MaskTests(unittest.TestCase):
    """Two discs seen face-on by an ideal camera (no distortion): target at 0.5 m, partner overlapping in the image
    at 0.45 m (in front). Points are given in the object frame = camera frame (identity tracks)."""

    def setUp(self):
        self.geo = _geo()
        pts = dict(t=_disc(0.0, 0.0, 0.05, 0.50), p=_disc(0.06, 0.0, 0.03, 0.45, seed=1))
        poses = {'world_T_cam': np.repeat(np.eye(4)[None], 3, 0), 'cam_T_t': np.repeat(np.eye(4)[None], 3, 0),
                 'cam_T_p': np.repeat(np.eye(4)[None], 3, 0)}
        self.b = _FakeBundle(['t', 'p'], sep=[], pts=pts, poses=poses, T=3)

    def test_exclusive_removes_partner_and_front_hand(self):
        L = GI.frame_layers(self.b, 0, self.geo)
        S = L.fp['t']
        self.assertTrue((S & L.fp['p']).any())                            # the footprints overlap
        # a hand in front of the target (z 0.40 m) on the left, a hand behind it (z 0.70 m) on the right
        L.hand = np.zeros_like(S); L.hand_z = np.full(S.shape, np.inf, np.float32)
        L.hand[200:280, 230:260] = True; L.hand_z[200:280, 230:260] = 0.40
        L.hand[200:280, 300:320] = True; L.hand_z[200:280, 300:320] = 0.70
        M, q = GI.exclusive(L, 't')
        self.assertFalse((M & q['Pd']).any())
        self.assertFalse((M & L.fp['p']).any())
        self.assertFalse(M[200:280, 230:260].any())                       # front hand removed
        self.assertTrue(M[200:280, 300:320].all())                        # hand behind the target kept
        t = GI.partner_pixel_test(M, self.b, 't', 0, self.geo, layers=L)
        self.assertTrue(t['pass'])
        self.assertGreater(t['points_projected'], 0)
        self.assertGreaterEqual(t['min_dist_px'], L.partner_px - 1.5)
        bad = GI.partner_pixel_test(S, self.b, 't', 0, self.geo, layers=L)   # the raw footprint is not exclusive
        self.assertFalse(bad['pass'])
        self.assertGreater(bad['points_inside'], 0)

    def test_depth_occluders_removed(self):
        L = GI.frame_layers(self.b, 0, self.geo)
        S = L.fp['t']
        L.valid = np.ones_like(S)
        L.depth_z = np.where(S, L.zf['t'], np.inf).astype(np.float32)        # depth agrees with the target ...
        L.depth_z[215:235, 280:305] = 0.47                                  # ... except a 30 mm-near occluder
        L.depth_z[250:270, 280:305] = 0.49                                  # 10 mm near: still the target
        self.assertTrue(S[215:235, 280:305].all() and S[250:270, 280:305].all())
        M, q = GI.exclusive(L, 't')
        self.assertFalse(M[215:235, 280:305].any())
        self.assertTrue(q['Oc'][215:235, 280:305].all())
        self.assertTrue(M[250:270, 280:305].all())
        self.assertTrue(M[240:247, 280:305].all())
        self.assertFalse((q['Oc'] & ~S).any())
        self.assertFalse((M & q['Pd']).any())

    def test_partner_dilation_scaled_to_cam_a_focal(self):
        g = self.geo
        self.assertEqual(GI.partner_dilate_px(g), 10)
        g2 = GI.Geo(Ka=np.diag([1150.0, 1150.0, 1.0]), Da=np.zeros(5), T_a_rect=np.eye(4), W=10, H=10,
                    K_rect=np.diag([600.0, 600.0, 1.0]))
        self.assertEqual(GI.partner_dilate_px(g2), 19)

    def test_refine_cut_back_and_hands(self):
        v = GI.View(obj='t', k=0, j=1, mode='contact', dir=[0, 0, -1], area=1, hand_share=0, depth_share=1,
                    partner_share=0)
        leak = lambda img, pos, neg, M: np.ones_like(M)                   # noqa: E731  gains partner pixels
        F, res = GI.masks(v, self.b, np.zeros((480, 640, 3), np.uint8), geo=self.geo, refine=leak)
        self.assertIn('refine_cut_back', res['info']['flags'])
        self.assertTrue(np.array_equal(F, res['projected']))
        inner = lambda img, pos, neg, M: M & (np.arange(M.shape[1])[None, :] < 335)   # noqa: E731  shrinks only
        F2, res2 = GI.masks(v, self.b, np.zeros((480, 640, 3), np.uint8), geo=self.geo, refine=inner)
        self.assertNotIn('refine_cut_back', res2['info']['flags'])
        self.assertTrue((F2 <= res2['projected']).all())
        self.assertLess(F2.sum(), res2['projected'].sum())
        self.assertTrue(GI.partner_pixel_test(F2, self.b, 't', 0, self.geo, layers=res2['layers'])['pass'])
        tiny = lambda img, pos, neg, M: M & (np.arange(M.shape[1])[None, :] < 280)   # noqa: E731  keeps < 0.6
        F3, res3 = GI.masks(v, self.b, np.zeros((480, 640, 3), np.uint8), geo=self.geo, refine=tiny)
        self.assertIn('refine_rejected', res3['info']['flags'])
        self.assertTrue(np.array_equal(F3, res3['projected']))
        from scipy.ndimage import binary_erosion
        holes = lambda img, pos, neg, M: M & ~((np.arange(M.shape[0])[:, None] % 9 == 0) &    # noqa: E731
                                                (np.arange(M.shape[1])[None, :] % 9 == 0) &
                                                binary_erosion(M, np.ones((5, 5), bool)))
        F4, res4 = GI.masks(v, self.b, np.zeros((480, 640, 3), np.uint8), geo=self.geo, refine=holes)
        self.assertTrue(np.array_equal(F4, res4['projected']))              # pinholes of the refinement are filled
        pos, neg = GI.prompts(res2['layers'], 't', res2['projected'])
        self.assertEqual(len(pos), 5)
        self.assertEqual(len(neg), 5)
        self.assertTrue(all(res2['projected'][y, x] for x, y in pos))
        self.assertTrue(all(res2['layers'].fp['p'][y, x] for x, y in neg))

    def test_hand_capsules_render_in_front(self):
        hands = dict(valid_left=np.array([True]), valid_right=np.array([False]),
                     joints_left=np.zeros((1, 21, 3), np.float32), joints_right=np.zeros((1, 21, 3), np.float32))
        J = np.zeros((21, 3)); J[:, 2] = 0.40; J[:, 0] = np.linspace(-0.04, 0.04, 21)
        hands['joints_left'][0] = J
        poses = {'world_T_cam': np.eye(4)[None]}
        caps = GI.hand_capsules(hands, poses, 0)
        self.assertEqual(len(caps[0]), len(GI.BONES) + 1)
        m, zn = GI.hand_layer(caps, self.geo)
        self.assertTrue(m[240, 320])
        self.assertAlmostEqual(float(zn[240, 320]), 0.40 - 0.045, places=3)   # the forearm disc (45 mm) covers it
        self.assertAlmostEqual(float(zn[240, 410]), 0.40 - 0.03, places=3)    # finger side: hand radius only
        self.assertFalse(m[20, 20])


class GuardRoleTests(unittest.TestCase):
    def test_dev_hands_role(self):
        self.assertIn('dev_hands', guard.DEV_ROLES)
        self.assertNotIn('dev_hands', guard.CLEAN_ROLES)
        self.assertEqual(set(guard.NPZ_KEYS['dev_hands']),
                         {'joints_left', 'joints_right', 'valid_left', 'valid_right', 'a_offset'})


if __name__ == '__main__':
    unittest.main(verbosity=2)
