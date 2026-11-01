"""Unit checks of pipeline/twist_canon.py (2026-11-01; numpy/scipy only). Run: python -I test_twist_canon.py"""
import os, sys
import numpy as np
from scipy.spatial.transform import Rotation as R
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import twist_canon as TC  # noqa: E402

T = 60; ax = np.array([0, 0, 1.0]); OP = np.zeros((T, 3)); far = np.full((T, 2, 3), 5.0)
hands = {'left': (far, np.tile([1.0, 0, 0, 0], (T, 1))), 'right': (far, np.tile([1.0, 0, 0, 0], (T, 1)))}
# 1) a resting cup whose track twists 140 deg about its axis -> twist removed, axis kept
tw = np.radians(np.linspace(0, 140, T)); Rin = R.from_rotvec([0.3, 0, 0]) * R.from_rotvec(np.outer(tw, ax))   # body-frame twist
q, inf = TC.canonicalise(Rin.as_quat()[:, [3, 0, 1, 2]], OP, ax, 0.05, hands)
Rc = TC.quat_wxyz_to_R(q)
assert np.allclose(Rc.apply(ax), Rin.apply(ax), atol=1e-9), 'axis changed'
assert np.allclose((Rc * Rc[0].inv()).magnitude(), 0, atol=1e-9), 'resting cup still rotates'
print('PASS resting twist removed (removed max', inf['removed_deg_max'], 'deg), tilt kept')
# 2) a pure tilt (axis moves) is reproduced exactly
Rt = R.from_rotvec(np.outer(np.radians(np.linspace(0, 60, T)), [1.0, 0, 0]))
q, _ = TC.canonicalise(Rt.as_quat()[:, [3, 0, 1, 2]], OP, ax, 0.05, hands)
assert np.allclose((TC.quat_wxyz_to_R(q) * Rt.inv()).magnitude(), 0, atol=1e-9); print('PASS pure tilt unchanged')
# 3) held and moving: the twist follows the holding wrist's rotation about the axis
OPm = np.outer(np.arange(T), [0.002, 0, 0]); near = OPm[:, None, :] + np.array([0.06, 0, 0])
Wr = R.from_rotvec(np.outer(np.radians(np.linspace(0, 90, T)), ax))
hands_h = {'left': (near.repeat(2, 1), Wr.as_quat()[:, [3, 0, 1, 2]]), 'right': (far, np.tile([1.0, 0, 0, 0], (T, 1)))}
q, inf = TC.canonicalise(np.tile([1.0, 0, 0, 0], (T, 1)), OPm, ax, 0.05, hands_h)
got = np.degrees((TC.quat_wxyz_to_R(q)[-1]).magnitude())
assert abs(got - 90) < 1e-6 and inf['held_by']['left'] == T - 1, (got, inf); print('PASS held twist follows the wrist (90 deg)')
