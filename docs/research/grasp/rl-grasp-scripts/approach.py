"""Approach of a hand to a plate in a trace: per frame, palm centre in the plate PCA frame (cm), palm-centre height over
the table, palm normal (world z and . plate normal), the lowest fingertip height over the table, the palm velocity
direction in the plate frame, and the hand's offset from a second source (e.g. the FK reference) = what the residual
changed: palm position (cm) and orientation (deg) and per-joint differences (deg).
Usage: approach.py TRACE.npz FKREF.npz OBJ HULLS GLB SIDE F0 F1 STEP"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
from scipy.spatial.transform import Rotation as R
from rlgrasp_lib import ObjGeom, load_trace, hand_points, revolute_joints, joint_angles, link_world, TABLE_Z
tr, fk = load_trace(sys.argv[1]), load_trace(sys.argv[2]); obj = sys.argv[3]; G = ObjGeom(sys.argv[4], sys.argv[5]); S = sys.argv[6]
f0, f1, st = int(sys.argv[7]), int(sys.argv[8]), int(sys.argv[9]); hp = hand_points(S, 60); js = revolute_joints(S)
pc = hp[f'{S}_hand_C_MC'].mean(0)
for f in range(f0, f1, st):
    op = tr['obj'][obj][f]; Ro = R.from_quat(op[3:7]); pal = tr['links'][f'{S}_hand_C_MC'][f]; Rp = R.from_quat(pal[3:7])
    c = pal[:3] + Rp.apply(pc); cp = G.pca(Ro.inv().apply(c - op[:3]))[0]; nrm = Rp.apply([1.0, 0, 0])
    tips = min(link_world(tr['links'][f'{S}_{fi}_DP'][f], hp[f'{S}_{fi}_DP'])[:, 2].min() for fi in ('index', 'middle', 'ring', 'pinky')) - TABLE_Z
    thumb = link_world(tr['links'][f'{S}_thumb_DP'][f], hp[f'{S}_thumb_DP'])[:, 2].min() - TABLE_Z
    pal_n = tr['links'][f'{S}_hand_C_MC'][min(f + st, tr['T'] - 1)]; v = (pal_n[:3] + R.from_quat(pal_n[3:7]).apply(pc)) - c
    vp = G.W @ Ro.inv().apply(v) / max(1e-6, np.linalg.norm(v))
    q = fk['links'][f'{S}_hand_C_MC'][f]; dpos = 100 * np.linalg.norm(pal[:3] - q[:3]); drot = np.degrees((R.from_quat(q[3:7]).inv() * Rp).magnitude())
    ja = joint_angles({k: v_[f] for k, v_ in tr['links'].items()}, js); jr = joint_angles({k: v_[f] for k, v_ in fk['links'].items()}, js)
    dj = {k.split('_', 1)[1]: round(float(np.degrees(ja[k][0] - jr[k][0]))) for k in ja if k in jr and abs(np.degrees(ja[k][0] - jr[k][0])) >= 15}
    print(f'f{f:3d} palm@plate ({cp[0]*100:5.1f},{cp[1]*100:5.1f},{cp[2]*100:5.1f}) h {100*(c[2]-TABLE_Z):5.1f} n.z {nrm[2]:+.2f} n.pn {nrm @ Ro.apply(G.W[2]):+.2f} '
          f'tips {1000*tips:+5.0f} thumb {1000*thumb:+5.0f}mm v ({vp[0]:+.1f},{vp[1]:+.1f},{vp[2]:+.1f}) {100*np.linalg.norm(v):4.1f}cm | vs ref palm {dpos:4.1f}cm {drot:4.0f}deg {dj}')
