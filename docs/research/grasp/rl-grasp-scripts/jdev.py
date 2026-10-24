"""Mean joint angles (deg) of SIDE's hand in a trace vs a second source (FK reference) per window, and the palm offset.
Usage: jdev.py TRACE.npz FK.npz SIDE WINDOWS"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
from scipy.spatial.transform import Rotation as R
from rlgrasp_lib import load_trace, revolute_joints, joint_angles
tr, fk = load_trace(sys.argv[1]), load_trace(sys.argv[2]); S = sys.argv[3]; js = revolute_joints(S)
order = ['thumb_CMC_FE', 'thumb_CMC_AA', 'thumb_MCP_FE', 'thumb_MCP_AA', 'thumb_IP'] + [f'{f}_{j}' for f in ('index', 'middle', 'ring', 'pinky') for j in ('MCP_FE', 'MCP_AA', 'PIP', 'DIP')]
for w in sys.argv[4].split(','):
    f0, f1 = map(int, w.split('-')); A, B, dp, dr = [], [], [], []
    for f in range(f0, min(f1, tr['T'], fk['T'])):
        ja = joint_angles({k: v[f] for k, v in tr['links'].items()}, js); jb = joint_angles({k: v[f] for k, v in fk['links'].items()}, js)
        A.append([np.degrees(ja[f'{S}_{j}'][0]) for j in order]); B.append([np.degrees(jb[f'{S}_{j}'][0]) for j in order])
        p, q = tr['links'][f'{S}_hand_C_MC'][f], fk['links'][f'{S}_hand_C_MC'][f]
        dp.append(100 * np.linalg.norm(p[:3] - q[:3])); dr.append(np.degrees((R.from_quat(q[3:7]).inv() * R.from_quat(p[3:7])).magnitude()))
    A, B = np.mean(A, 0), np.mean(B, 0)
    print(f'{w}: palm offset {np.mean(dp):.1f} cm / {np.mean(dr):.0f} deg')
    print('   ' + '  '.join(f'{j.replace("_FE", "").replace("thumb_", "T").replace("index_", "I").replace("middle_", "M").replace("ring_", "R").replace("pinky_", "P")} {a:.0f}/{b:.0f}' for j, a, b in zip(order, A, B)))
