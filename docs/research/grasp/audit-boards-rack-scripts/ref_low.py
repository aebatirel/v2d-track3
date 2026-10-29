import sys, numpy as np, trimesh
from scipy.spatial.transform import Rotation as R
sys.path.insert(0, __file__.rsplit('/', 1)[0]); from refload import load_ref
d = load_ref(sys.argv[1]); lib = sys.argv[2]; fr = [int(x) for x in sys.argv[3].split(',')]; ztab = float(sys.argv[4])
for j, o in enumerate(d['names']):
    v = trimesh.load(f'{lib}/{o}.glb', force='mesh').vertices
    lows = [(R.from_quat(d['OQ'][t, j]).apply(v) + d['OP'][t, j])[:, 2].min() - ztab for t in fr]
    tilt = [np.degrees(np.arccos(abs(R.from_quat(d['OQ'][t, j]).apply([1, 0, 0])[2]))) for t in fr]
    print(o, ' '.join(f'f{t}:{l*100:+.1f}cm/{a:.0f}d' for t, l, a in zip(fr, lows, tilt)))
