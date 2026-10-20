# Stage C: same geometry, different CoACD input orientation. newton/FlashCHORD decompose the mesh in its own file
# frame and keep the <collision><origin> transform for every hull (A3), so shipping vertices rotated by R with
# <origin rpy = R^-1> gives identical world geometry while CoACD's axis-aligned cuts see a rotated mesh.
# Runs the exact FlashCHORD call on W2 rotated by R, rotates the hulls back to the object frame.
# usage: c_rotdecomp.py name (aligned|x<deg>|y<deg>|z<deg>) outdir
import sys, os, time, numpy as np
from scipy.spatial.transform import Rotation as Rot
sys.path.insert(0, '/Users/aebatirel/Documents/Code/v2d-research/work/15-verify/pylib11'); import coacd
sys.path.insert(0, '/Users/aebatirel/Documents/Code/v2d-research/work/19/b'); from common import *
n, spec, od = sys.argv[1], sys.argv[2], sys.argv[3]; os.makedirs(od, exist_ok=True)
R = np.load(f'/Users/aebatirel/Documents/Code/v2d-research/work/19/c/align_{n}.npy') if spec == 'aligned' else \
    Rot.from_euler(spec[0], float(spec[1:]), degrees=True).as_matrix()
d = np.load(f'{W}/W2/{n}.npz'); v = d['v'] @ R.T; f = d['f']
coacd.set_log_level('info'); t = time.time()
parts = coacd.run_coacd(coacd.Mesh(np.ascontiguousarray(v, dtype=np.float64), np.ascontiguousarray(f, dtype=np.int64)),
                        threshold=0.05, max_convex_hull=-1, preprocess_mode='auto')
save_hulls(f'{od}/{n}.npz', [(np.asarray(p[0]) @ R, np.asarray(p[1])) for p in parts])
print('RESULT', n, spec, 'hulls', len(parts), 'sec %.0f' % (time.time() - t),
      'rotation deg %.2f' % np.degrees(Rot.from_matrix(R).magnitude()), flush=True)
