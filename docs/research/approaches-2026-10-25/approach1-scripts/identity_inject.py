"""T-1 injection test for identity_rule.py (pre-registered in approach1-motion-constrained-meshes.md §6).
Take a good two-board track (ep24, 21 Oct own track), inject {no swap, swap} x {I, Rx, Ry, Rz on the first board},
run the rule, apply its choice, and check the original poses come back (both boards within 1 deg and 1 mm).
Pass: all 8 restored. Inputs: our track, video, calibration, our meshes (no GT).
Usage: python identity_inject.py VIDEO_C.mp4 CALIB.json POSES.npz MESH_1 MESH_2 OUTDIR"""
import itertools, os, subprocess, sys

import numpy as np
from scipy.spatial.transform import Rotation as R

vid, calib, poses, m1, m2, outd = sys.argv[1:7]
os.makedirs(outd, exist_ok=True)
here = os.path.dirname(os.path.abspath(__file__))
FL = {'I': np.eye(4), 'Rx': np.diag([1., -1, -1, 1]), 'Ry': np.diag([-1., 1, -1, 1]), 'Rz': np.diag([-1., -1, 1, 1])}
P = dict(np.load(poses)); n1, n2 = 'cam_T_wooden_piece_1', 'cam_T_wooden_piece_2'
ok_all = True
for swap, fk in itertools.product((False, True), FL):
    A, B = (P[n2], P[n1]) if swap else (P[n1], P[n2])
    inj = dict(P); inj[n1] = A @ FL[fk]; inj[n2] = B
    f = f'{outd}/inj_{int(swap)}_{fk}.npz'; np.savez(f, **inj)
    out = subprocess.run([sys.executable, '-I', f'{here}/identity_rule.py', vid, calib, f, m1, m2, '0,2,4,6'],
                         capture_output=True, text=True).stdout
    best = eval(out.split('best 5 (score, assignment, F board1, F board2): ')[1].split('\n')[0])[0]
    _, assign, f1, f2 = best
    src = {n1: n1, n2: n2} if assign == 'as tracked' else {n1: n2, n2: n1}
    rec = {n1: inj[src[n1]] @ FL[f1], n2: inj[src[n2]] @ FL[f2]}
    err = [(R.from_matrix(rec[n][:, :3, :3] @ np.transpose(P[n][:, :3, :3], (0, 2, 1))).magnitude().max() * 180 / np.pi,
            np.abs(rec[n][:, :3, 3] - P[n][:, :3, 3]).max() * 1e3) for n in (n1, n2)]
    ok = all(e[0] < 1 and e[1] < 1 for e in err); ok_all &= ok
    print(f'inject swap={swap} flip(board1)={fk}: rule -> {assign}, {f1}, {f2}; restored={ok}', flush=True)
print('T-1 injection:', 'PASS' if ok_all else 'FAIL')
