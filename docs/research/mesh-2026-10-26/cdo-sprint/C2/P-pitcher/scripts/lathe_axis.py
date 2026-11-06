"""C2/P PREREG amendment A1: lathe_obs.py with the axis DIRECTION fixed to our observed resting up (rest_axis.py),
everything else exactly lathe_obs.py. The shared script is not edited: this wrapper replaces lathe_obs.fit_axis by a
function that evaluates only the given direction, with fit_axis's own steps for it (normals / planarity on the same
points, line-complex placement lathe_obs._place with the direction fixed, centre shifted to the points' mean height,
rotational consistency on the same 20,000-point subsample, seed 1), then calls lathe_obs.main() with the remaining
arguments. lathe_obs then flips the direction so the open end is +h, as for any axis.
Usage: lathe_axis.py --axis_json REST_AXIS.json OBS.npz OUT.glb [lathe_obs.py options]
"""
import json, os, sys
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.abspath(os.path.join(HERE, '..', '..', '..', '..', 'scripts')))
import lathe_obs as L  # noqa: E402

i = sys.argv.index('--axis_json')
AX = np.array(json.load(open(sys.argv[i + 1]))['axis_dir'], float)
AX /= np.linalg.norm(AX)
del sys.argv[i:i + 2]


def fixed_axis(P, C, iters=8, nclust=6, knn=24):
    c0 = P.mean(0); X = P - c0
    n, planar = L.normals(X, C - c0, k=knn)
    nb = np.cross(X, n)
    a = AX.copy()
    abar = L._place(n, nb, planar, a)
    c = c0 + np.cross(a, abar)
    c = c + a * ((P - c) @ a).mean()
    sub = np.random.default_rng(1).choice(len(P), min(20000, len(P)), replace=False)
    return L.rot_consistency(P[sub], c, a) * 1e3, c, a, 1


L.fit_axis = fixed_axis
if __name__ == '__main__':
    L.main()
