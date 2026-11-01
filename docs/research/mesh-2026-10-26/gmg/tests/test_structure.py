"""B7 tests of gmg/structure.py (module M5; SPEC sections 7, 8, 10 and 24; PREREG A.6 symmetry acceptance).

  GMG_MODE=dev python docs/research/mesh-2026-10-26/gmg/tests/test_structure.py            (venv python)
  GMG_MODE=dev python .../test_structure.py Lathe                                       (one class)

Pass condition of build step B7 (SPEC section 24): synthetic lathe, mirror and plate recovered within 1 sigma.
Each synthetic object is a known closed mesh, tilted 35 deg and moved off the origin, ray-cast from 16-22 cameras with
1 mm Gaussian range noise and voted into the 4 mm grids (tests/synth.py; sigma = 1 mm, the noise the renderer adds).
"Recovered within 1 sigma" is measured as a POSITION error over the object, so an angle error counts with the lever
arm it has on the object (DEVIATIONS, B7):
  lathe   the estimated axis is accepted (rotc <= 3 sigma) and its distance from the true axis, taken at the two ends
          of the object's span along the true axis, is <= 1 sigma at both ends;
  mirror  the one true mirror plane is found and accepted: the signed distance to the estimated plane differs from the
          signed distance to the true plane by <= 1 sigma at every vertex of the true mesh; the two planes the
          handle breaks are not accepted, and the object is not accepted as a lathe (negative controls);
  plate   a plane pair (the plate's two faces) is found: |thickness - true| <= 1 sigma and the mid plane is within
          1 sigma of the true mid plane at every vertex (same measure as a mirror).
Results go to <scratchpad>/gmg/b7/test_structure.json (env B7_OUT overrides). Nothing is read from disk but code.
"""
import json
import math
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

from gmg import structure as ST  # noqa: E402
from gmg.tests import synth  # noqa: E402

SIGMA = synth.SIGMA
B7_OUT = os.environ.get('B7_OUT', os.path.join(guard.CFG['data'], 'gmg', 'b7', 'test_structure.json'))
_CACHE, _RESULTS = {}, {}


def rot(axis, deg):
    return trimesh.transformations.rotation_matrix(np.radians(deg), axis)


def pose():
    """The common test pose: 35 deg about a skew axis, then a few mm off the origin."""
    T = rot([1, 0.3, 0.2], 35)
    T[:3, 3] = [0.01, -0.005, 0.008]
    return T


def cup():
    """Tapered hollow cup (body of revolution about z): outer radius 35-42 mm, wall 3.5-7 mm, 90 mm tall."""
    prof = [(0, -0.045), (0.035, -0.045), (0.042, 0.045), (0.038, 0.045), (0.0315, -0.040), (0, -0.040)]
    return synth_revolve(prof)


def synth_revolve(prof, nseg=96):
    from autokit import parts as PT
    return PT.L.revolve(prof, nseg=nseg)


def handled_box():
    """90 x 60 x 40 mm box with a 7 mm-radius handle along +x at z = +10 mm: one true mirror plane (y = 0 in the
    object's own frame); the handle breaks the x and z planes of the box."""
    box = trimesh.creation.box([0.09, 0.06, 0.04])
    h = trimesh.creation.cylinder(radius=0.007, height=0.05, sections=48)
    h.apply_transform(rot([0, 1, 0], 90))
    h.apply_translation([0.045 + 0.025, 0, 0.01])
    m = trimesh.util.concatenate([box, h])
    m.apply_translation([-0.0125, 0, 0])
    return m


def plate():
    return trimesh.creation.box([0.12, 0.06, 0.01])


CASES = {
    'lathe': (cup, lambda: synth.ring(35, 14, 0)[:11] + synth.ring(65, 6, 20)[:5] + synth.ring(5, 8, 10)[:6]),
    'mirror': (handled_box, lambda: synth.ring(35, 12) + synth.ring(70, 4, 45) + synth.ring(0, 8, 22)),
    'plate': (plate, lambda: synth.ring(40, 8) + synth.ring(-40, 8, 22)),
}


def case(name):
    """(mesh in the test pose, hypotheses, seconds); rendered and analysed once per process."""
    if name not in _CACHE:
        make, cams = CASES[name]
        m = make()
        m.apply_transform(pose())
        t = time.time()
        b = synth.episode(m, cams(), name='o', seed=0)
        obs = b.obs('o')
        t1 = time.time()
        h = ST.hypotheses(obs, sigma=SIGMA)
        _CACHE[name] = (m, h, dict(render_s=round(t1 - t, 1), hypotheses_s=round(time.time() - t1, 1),
                                   n_points=int(len(obs['pts']))))
    return _CACHE[name]


def axis_end_error(c_e, a_e, c_t, a_t, V):
    """Distance from the true axis to the estimated axis at the two ends of the object's span along the true axis."""
    a_t = a_t / np.linalg.norm(a_t); a_e = np.asarray(a_e, np.float64) / np.linalg.norm(a_e)
    h = (V - c_t) @ a_t
    ends = c_t + np.outer([h.min(), h.max()], a_t)
    D = ends - c_e
    D = D - np.outer(D @ a_e, a_e)
    return np.linalg.norm(D, axis=1)


def plane_error(n_e, d_e, n_t, d_t, V):
    """max over V of |signed distance to the estimated plane - signed distance to the true plane| (signs aligned)."""
    n_e = np.asarray(n_e, np.float64); n_t = np.asarray(n_t, np.float64)
    s = 1.0 if n_e @ n_t >= 0 else -1.0
    return float(np.max(np.abs((V @ n_e - d_e) * s - (V @ n_t - d_t))))


def angle_deg(u, v):
    u = np.asarray(u, np.float64); v = np.asarray(v, np.float64)
    return math.degrees(math.acos(min(1.0, abs(float(u @ v)) / np.linalg.norm(u) / np.linalg.norm(v))))


def _save():
    os.makedirs(os.path.dirname(B7_OUT), exist_ok=True)
    with open(B7_OUT, 'w') as f:
        json.dump(_RESULTS, f, indent=1, default=float)


class Lathe(unittest.TestCase):
    def test_lathe_recovered_within_1_sigma(self):
        m, h, tm = case('lathe')
        T = pose()
        c_t, a_t = T[:3, 3], T[:3, :3] @ [0, 0, 1]
        ax = h['axis']
        err = axis_end_error(np.array(ax['c']), np.array(ax['a']), c_t, a_t, np.asarray(m.vertices))
        _RESULTS['lathe'] = dict(timing=tm, accepted=ax['accepted'], rotc_sigma=ax['rotc_sigma'],
                                 lathe_mad_sigma=ax['lathe_mad_sigma'], source=ax['source'],
                                 angle_deg=round(angle_deg(ax['a'], a_t), 4),
                                 end_err_mm=[round(float(e) * 1e3, 4) for e in err], sigma_mm=SIGMA * 1e3,
                                 accepted_repeats=h['accepted']['repeats'])
        _save()
        self.assertTrue(ax['accepted'], f'lathe not accepted: rotc {ax["rotc_sigma"]} sigma')
        self.assertLessEqual(float(err.max()), SIGMA, f'axis end errors {err * 1e3} mm > 1 sigma')


class Mirror(unittest.TestCase):
    def test_mirror_recovered_within_1_sigma(self):
        m, h, tm = case('mirror')
        T = pose()
        R, t = T[:3, :3], T[:3, 3]
        V = np.asarray(m.vertices)
        # the true plane: y = 0 of the object's own frame, moved by the pose
        n_t = R @ [0, 1, 0]; d_t = float(n_t @ t)
        broken = [R @ [1, 0, 0], R @ [0, 0, 1]]
        rows = []
        for mi in h['mirrors']:
            rows.append(dict(accepted=mi['accepted'], resid_sigma=mi['resid_sigma'], observed=mi['observed'],
                             free_viol=mi['free_viol'], moved=mi['moved'], refined_by=mi['refined_by'],
                             angle_to_true_deg=round(angle_deg(mi['n'], n_t), 4),
                             plane_err_mm=round(plane_error(mi['n'], mi['d'], n_t, d_t, V) * 1e3, 4),
                             angle_to_broken_deg=[round(angle_deg(mi['n'], b), 3) for b in broken]))
        true = [r for r in rows if r['angle_to_true_deg'] < 10]
        acc_broken = [r for r in rows if r['accepted'] and min(r['angle_to_broken_deg']) < 10]
        _RESULTS['mirror'] = dict(timing=tm, mirrors=rows, lathe_accepted=h['axis']['accepted'],
                                  lathe_rotc_sigma=h['axis']['rotc_sigma'], sigma_mm=SIGMA * 1e3)
        _save()
        self.assertEqual(len(true), 1, f'true plane found {len(true)} times: {rows}')
        self.assertTrue(true[0]['accepted'], f'true plane not accepted: {true[0]}')
        self.assertLessEqual(true[0]['plane_err_mm'], SIGMA * 1e3, f'true plane error > 1 sigma: {true[0]}')
        self.assertEqual(acc_broken, [], 'a plane broken by the handle was accepted')
        self.assertFalse(h['axis']['accepted'], 'the handled box was accepted as a lathe')


class Plate(unittest.TestCase):
    def test_plate_recovered_within_1_sigma(self):
        m, h, tm = case('plate')
        T = pose()
        R, t = T[:3, :3], T[:3, 3]
        V = np.asarray(m.vertices)
        n_t = R @ [0, 0, 1]; d_t = float(n_t @ t)
        rows = []
        for p in h['plane_pairs']:
            rows.append(dict(thickness_mm=p['thickness_mm'], overlap=p['overlap'], parallel_deg=p['parallel_deg'],
                             angle_to_true_deg=round(angle_deg(p['mid_n'], n_t), 4),
                             mid_err_mm=round(plane_error(p['mid_n'], p['mid_d'], n_t, d_t, V) * 1e3, 4)))
        mid = [r for r in rows if r['angle_to_true_deg'] < 10]
        mir = [dict(accepted=mi['accepted'], angle_to_mid_deg=round(angle_deg(mi['n'], n_t), 3),
                    plane_err_mm=round(plane_error(mi['n'], mi['d'], n_t, d_t, V) * 1e3, 4)) for mi in h['mirrors']]
        _RESULTS['plate'] = dict(timing=tm, pairs=rows, planes=len(h['planes']), mirrors=mir,
                                 lathe_accepted=h['axis']['accepted'], lathe_rotc_sigma=h['axis']['rotc_sigma'],
                                 rot_free_viol=h['axis']['rot_free_viol'], sigma_mm=SIGMA * 1e3, true_thickness_mm=10.0)
        _save()
        self.assertEqual(len(mid), 1, f'plate pair found {len(mid)} times: {rows}')
        self.assertLessEqual(abs(mid[0]['thickness_mm'] - 10.0), SIGMA * 1e3, f'thickness off: {mid[0]}')
        self.assertLessEqual(mid[0]['mid_err_mm'], SIGMA * 1e3, f'mid plane off: {mid[0]}')


class Units(unittest.TestCase):
    def test_sigma_required(self):
        with self.assertRaises(ValueError):
            ST.hypotheses(dict(pts=np.zeros((10, 3))), sigma=None)

    def test_sym_eval_exact_mirror(self):
        """A point set symmetric about z = 0 scores residual ~ 0, observed 1, free 0 at the true plane."""
        rng = np.random.default_rng(0)
        P = rng.normal(0, 0.02, (4000, 3)); P = np.vstack([P, P * [1, 1, -1]])
        obs = dict(lo=np.full(3, -0.15), vox=0.004, hits=np.ones((75, 75, 75), np.uint16),
                   free=np.zeros((75, 75, 75), np.uint16))
        g = ST.Grid(obs, np.zeros((75, 75, 75), np.uint8))
        from scipy.spatial import cKDTree
        ev = ST.sym_eval(P, ST._reflect(P, np.array([0, 0, 1.0]), 0.0), cKDTree(P), g, 0.003, 0.8)
        self.assertLess(ev['resid'], 1e-9)
        self.assertEqual(ev['observed'], 1.0)
        self.assertEqual(ev['free'], 0.0)

    def test_constants_registered(self):
        K = ST.consts()
        self.assertEqual(K['acc_rotc'], 3.0)
        self.assertEqual(K['acc_res'], 3.0)
        self.assertEqual(K['acc_obs'], 0.7)
        self.assertEqual(K['acc_free'], 0.05)
        self.assertEqual(K['slab'], [0.003, 0.025])


if __name__ == '__main__':
    unittest.main(verbosity=2)
