"""B7 tests of gmg/markers.py (module M6; SPEC section 10; PREREG A.6 "ball radius window" and "ball detector").

  GMG_MODE=dev python docs/research/mesh-2026-10-26/gmg/tests/test_markers.py            (venv python)
  GMG_MODE=dev python .../test_markers.py Frozen Units                                (fast tests only)

Frozen: the detector settings in markers.FROZEN are the PREREG A.6 values and hash to the committed
  gmg/marker_settings.json (frozen at B7 before the first dev run); a change needs a PREREG F amendment.
Units: the batched free sphere fit equals autokit parts.sphere_fit_free; attach() returns a watertight union.
Synthetic (no radius prior): a box carrying four balls on posts, ray-cast with 1 mm range noise (tests/synth.py, 600 px
  focal length so a ball spans several pixels), at two ball radii (4.0 and 9.0 mm, inside the generic window, neither
  near the ~7 mm the scan catalogue suggests); the detector must find >= 3 of the 4 balls of each with centre and
  radius within 1 sigma. False balls (centre farther than r from every true ball) are counted and recorded.
Known limitation (expected failures, B7 notes): the frozen detector also accepts the box's sharp corners and edges as
  balls, so 'no false ball on a plain box' and 'no false ball next to the true balls' fail as frozen. The diagnostic
  statistics (normal_dev_deg, outside_ratio) are recorded for every ball.
Results go to <scratchpad>/gmg/b7/test_markers.json (env B7_MK_OUT overrides). Nothing is read from disk but code and
the committed settings file.
"""
import hashlib
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

from gmg import markers as MK  # noqa: E402
from gmg.tests import synth  # noqa: E402

SIGMA = synth.SIGMA
OUT = os.environ.get('B7_MK_OUT', os.path.join(guard.CFG['data'], 'gmg', 'b7', 'test_markers.json'))
SETTINGS = os.path.join(GMG, 'marker_settings.json')
_RESULTS = {}

# (point on the box surface, outward post direction)
POSTS = [((0.03, 0.0, 0.015), (0, 0, 1)), ((-0.035, 0.015, 0.015), (0, 0, 1)), ((0.05, -0.01, 0.0), (1, 0, 0)),
         ((-0.01, 0.03, -0.005), (0, 1, 0))]


def ball_box(r_ball, balls=True):
    """100 x 60 x 30 mm box; with balls: four spheres of radius r_ball on 1.5 mm posts 15 mm long. Returns (mesh,
    true centres)."""
    parts = [trimesh.creation.box([0.10, 0.06, 0.03])]
    truth = []
    if balls:
        for p, d in POSTS:
            p = np.array(p, float); d = np.array(d, float); L = 0.015
            parts.append(trimesh.creation.cylinder(radius=0.0015, segment=[p - 0.002 * d, p + L * d], sections=16))
            c = p + (L + 0.8 * r_ball) * d
            parts.append(trimesh.creation.icosphere(subdivisions=3, radius=r_ball).apply_translation(c))
            truth.append(c)
    return trimesh.util.concatenate(parts), np.array(truth)


def cams():
    c = synth.ring(35, 12) + synth.ring(70, 4, 45) + synth.ring(0, 8, 22)
    rng = np.random.default_rng(5)
    return [c[i] for i in rng.permutation(len(c))]       # shuffled: each ball is seen in both halves of the episode


def run_case(r_ball, balls=True):
    f0, w0, h0 = synth.F_PX, synth.W, synth.H
    synth.F_PX, synth.W, synth.H = 600.0, 480, 360
    try:
        m, truth = ball_box(r_ball, balls)
        t = time.time()
        b = synth.episode(m, cams(), name='o', seed=0)
        tr = time.time() - t
        t = time.time()
        res = MK.detect_episode(b, sigma=SIGMA)
        td = time.time() - t
    finally:
        synth.F_PX, synth.W, synth.H = f0, w0, h0
    found = []
    for bb in res['balls']['o']:
        c = np.array(bb['c'])
        dist = np.linalg.norm(truth - c, axis=1) if len(truth) else np.array([np.inf])
        k = int(np.argmin(dist))
        found.append(dict(truth=k, centre_err_mm=round(float(dist[k]) * 1e3, 4),
                          r_err_mm=round((bb['r'] - r_ball) * 1e3, 4), r_mm=bb['r_mm'], frames=bb['frames'],
                          resid_mm=round(bb['resid'] * 1e3, 4), cap_deg=bb['cap_deg'], halves=bb['halves'],
                          votes=bb['votes'], fit=bb['fit'], pass_=bb['pass_'], normal_dev_deg=bb['normal_dev_deg'],
                          outside_ratio=bb['outside_ratio']))
    rec = dict(r_true_mm=r_ball * 1e3, balls=balls, n_points=int(len(b.obs('o')['pts'])), render_s=round(tr, 1),
               detect_s=round(td, 1), r_consensus_mm=res['r_consensus_mm'], unimodal=res['unimodal'], found=found,
               rejections={k: [ci.get('rejected') for ci in res['per_object']['o'][k]['candidates_info']]
                           for k in ('pass1', 'pass2') if k in res['per_object']['o']})
    return rec


def _save():
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, 'w') as f:
        json.dump(_RESULTS, f, indent=1, default=float)


class Frozen(unittest.TestCase):
    def test_prereg_a6_values(self):
        F = MK.FROZEN
        self.assertEqual(F['radius_window_m'], [0.0015, 0.0125])
        self.assertEqual(F['seeds'], 15000)
        self.assertEqual(F['min_frames'], 3)
        self.assertEqual(F['resid_max_sigma'], 1.5)
        self.assertEqual(F['cap_min_deg'], 90.0)
        self.assertTrue(F['both_halves'])
        self.assertEqual(F['second_pass_rel'], 0.10)
        self.assertEqual(F['vote_vox_m'], 0.0015)

    def test_settings_file_matches(self):
        with open(SETTINGS) as f:
            S = json.load(f)
        self.assertEqual(S['settings'], json.loads(json.dumps(MK.FROZEN)))
        self.assertEqual(S['settings_sha256'], MK.SETTINGS_SHA256)
        self.assertEqual(hashlib.sha256(json.dumps(S['settings'], sort_keys=True).encode()).hexdigest(),
                         MK.SETTINGS_SHA256)


class Units(unittest.TestCase):
    def test_batched_fit_equals_parts(self):
        from autokit import parts as PT
        rng = np.random.default_rng(3)
        S, nmax = 40, 300
        Qs, Ms = [], []
        for _ in range(S):
            n = int(rng.integers(30, nmax)); r = rng.uniform(0.003, 0.012); c = rng.normal(0, 0.01, 3)
            u = rng.normal(size=(n, 3)); u /= np.linalg.norm(u, axis=1, keepdims=True)
            ax = rng.normal(size=3); ax /= np.linalg.norm(ax)
            u = u[u @ ax > np.cos(rng.uniform(0.6, 1.5))]
            if len(u) < 20:
                u = rng.normal(size=(40, 3)); u /= np.linalg.norm(u, axis=1, keepdims=True)
            X = np.vstack([c + r * u + rng.normal(0, 0.0008, (len(u), 3)),
                           c + rng.normal(0, 0.02, (int(rng.integers(0, 10)), 3))])
            q = np.zeros((nmax + 20, 3)); m = np.zeros(nmax + 20, bool); q[:len(X)] = X; m[:len(X)] = True
            Qs.append(q); Ms.append(m)
        Q, M = np.stack(Qs), np.stack(Ms)
        c, r, res, keep, ok = MK.batch_free_fit(Q, M)
        n_cmp = 0
        for s in range(S):
            f = PT.sphere_fit_free(Q[s][M[s]])
            if f is None or f[1] > 0.1:           # no fit, or a near-planar fit far outside any radius window: both
                continue                          # fits are numerically ill-posed there and are rejected either way
            self.assertTrue(ok[s])
            np.testing.assert_allclose(c[s], f[0], atol=1e-7)
            self.assertAlmostEqual(r[s], f[1], delta=1e-7)
            self.assertAlmostEqual(res[s], f[2], delta=1e-7)
            n_cmp += 1
        self.assertGreater(n_cmp, 30)

    def test_attach_watertight(self):
        m = trimesh.creation.box([0.1, 0.06, 0.03])
        balls = [MK.Ball(c=[0.0, 0.0, 0.027], r=0.006, frames=5, resid=0.0005, cap_deg=120.0),
                 MK.Ball(c=[0.06, 0.0, 0.0], r=0.005, frames=5, resid=0.0005, cap_deg=120.0)]
        out = MK.attach(m, balls)
        self.assertTrue(out.is_watertight)
        self.assertGreater(out.volume, m.volume)
        self.assertEqual(len(out.metadata['balls']), 2)
        same = MK.attach(m, [])
        self.assertAlmostEqual(same.volume, m.volume, places=9)

    def test_json_round_trip(self):
        b = MK.Ball(c=[0.0, 0.01, 0.02], r=0.007, frames=5, resid=0.0004, cap_deg=130.0, votes=9, halves=[2, 3])
        b2 = MK.balls_from_json([MK.ball_dict(b)])[0]
        self.assertEqual(b2, b)


_CASES = {}


def _case(r_ball, balls=True):
    k = (r_ball, balls)
    if k not in _CASES:
        rec = run_case(r_ball, balls)
        rec['false'] = [f for f in rec['found'] if f['centre_err_mm'] > r_ball * 1e3] if balls else rec['found']
        rec['n_false'] = len(rec['false'])
        _CASES[k] = rec
        _RESULTS[f'balls_r{r_ball * 1e3:.1f}mm' if balls else 'plain_box'] = rec
        _save()
    return _CASES[k]


class Synthetic(unittest.TestCase):
    def _recall(self, r_ball):
        rec = _case(r_ball)
        good = {f['truth'] for f in rec['found'] if f['centre_err_mm'] <= SIGMA * 1e3 and abs(f['r_err_mm']) <= SIGMA * 1e3}
        rec['recalled_within_1_sigma'] = sorted(good)
        _save()
        self.assertGreaterEqual(len(good), 3, f'r {r_ball}: {rec}')

    def test_balls_r4mm_recall(self):
        self._recall(0.004)

    def test_balls_r9mm_recall(self):
        self._recall(0.009)

    @unittest.expectedFailure
    def test_known_limitation_no_false_ball_r4mm(self):
        self.assertEqual(_case(0.004)['n_false'], 0)

    @unittest.expectedFailure
    def test_known_limitation_no_ball_on_plain_box(self):
        self.assertEqual(_case(0.006, balls=False)['n_false'], 0)


if __name__ == '__main__':
    unittest.main(verbosity=2)
