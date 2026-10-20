# Unit test of y_ud.Obj.maxdepth: union of two overlapping boxes (L/plus shape) and a tilted box; known depths.
import sys, numpy as np, importlib.util
sys.argv = ['x', 'none=none']
spec = importlib.util.spec_from_file_location('y', '/Users/aebatirel/Documents/Code/v2d-research/work/19-verify/r2/y_ud.py')
src = open(spec.origin).read().split('_o = {}')[0]; g = {}; exec(src, g)
from scipy.spatial.transform import Rotation as R
def box(lo, hi, Rm=np.eye(3)):
    v = np.array([[x, y, z] for x in (lo[0], hi[0]) for y in (lo[1], hi[1]) for z in (lo[2], hi[2])]); return v @ Rm.T
Rm = R.from_euler('xyz', [17, 31, 8], degrees=True).as_matrix()
hv = [box((0, 0, 0), (0.04, 0.01, 0.01)), box((0.015, -0.02, 0), (0.025, 0.03, 0.01))]   # plus shape, thickness 10 mm
np.savez('/tmp/y_ud_test.npz', n=2, v0=hv[0], v1=hv[1]) if False else None
import os; d = '/Users/aebatirel/Documents/Code/v2d-research/work/19-verify/r2/'
np.savez(d + 'ut_plus.npz', n=2, v0=hv[0], v1=hv[1]); np.savez(d + 'ut_tilt.npz', n=1, v0=box((0, 0, 0), (0.03, 0.02, 0.012), Rm))
O = g['Obj'](d + 'ut_plus.npz')
for p, true in (([0.02, 0.005, 0.005], 5.0), ([0.02, 0.005, 0.003], 3.0), ([0.005, 0.005, 0.005], 5.0), ([0.02, 0.025, 0.002], 2.0), ([0.0205, 0.0052, 0.0049], 4.9)):
    print('plus  true', true, 'est', round(O.maxdepth(np.array([p]))[0], 3), 'per-hull', round(O.perhull(np.array([p]))[0] * 1e3, 3))
O2 = g['Obj'](d + 'ut_tilt.npz')
for p, true in (([0.015, 0.01, 0.006], 6.0), ([0.004, 0.01, 0.006], 4.0), ([0.015, 0.0025, 0.006], 2.5)):
    print('tilt  true', true, 'est', round(O2.maxdepth((np.array([p])) @ Rm.T)[0], 3))
hv = [box((0, 0, 0), (0.02, 0.02, 0.02), Rm), box((0.015, 0, 0), (0.04, 0.02, 0.02), Rm)]
np.savez(d + 'ut_bar.npz', n=2, v0=hv[0], v1=hv[1]); O3 = g['Obj'](d + 'ut_bar.npz')
for p, true in (([0.02, 0.01, 0.01], 10.0), ([0.0175, 0.004, 0.012], 4.0), ([0.019, 0.0137, 0.0071], 6.3)):
    q = np.array([p]) @ Rm.T
    print('bar   true', true, 'est', round(O3.maxdepth(q)[0], 3), 'per-hull', round(O3.perhull(q)[0] * 1e3, 3), 'ub-sample', round(O3.ub_tree().query(q)[0][0] * 1e3, 3))
hv = [box((0, 0, 0), (0.02, 0.02, 0.02), Rm), box((0.02, 0, 0), (0.04, 0.02, 0.02), Rm)]
np.savez(d + 'ut_shared.npz', n=2, v0=hv[0], v1=hv[1]); O4 = g['Obj'](d + 'ut_shared.npz')
for p, true in (([0.02, 0.01, 0.01], 10.0), ([0.019, 0.004, 0.012], 4.0), ([0.021, 0.0137, 0.0071], 6.3)):
    q = np.array([p]) @ Rm.T
    print('shared true', true, 'est', round(O4.maxdepth(q)[0], 3), 'per-hull', round(O4.perhull(q)[0] * 1e3, 3), 'ub-sample', round(O4.ub_tree().query(q)[0][0] * 1e3, 3))
