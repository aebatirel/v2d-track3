"""Manipulation-type segmentation from our own perception (no ground truth), prototype 2026-10-21.

Per frame and object, from the tracked object poses (perc2 poses.npz), the hand joints (hands_mp / hand_refine npz) and
the table plane (mkref table_frame.npz), all in the world frame (rectified camera 0):
  speed (cm/s, smoothed), height of the object's lowest point above the table, nearest hand-joint distance to the
  object's surface, nearest distance to any other object.
Labels: rest (speed < 3 cm/s), carry (moving, lifted > 1.5 cm, a hand within 2.5 cm), slide (moving, on the table,
hand within 2.5 cm), lift (moving up, a hand in contact), tool (moving, no hand within 4 cm, another object within
2 cm), free (moving without any of these: perception noise or a fall). Prints run-length segments.
Usage: python tools/manip_segments.py POSES.npz HANDS.npz TABLE_FRAME.npz MESH_DIR [fps]
"""
import sys, numpy as np, trimesh
from scipy.ndimage import uniform_filter1d

poses, hands, table, mesh_dir = sys.argv[1:5]; fps = float(sys.argv[5]) if len(sys.argv) > 5 else 20.0
P = np.load(poses); W = P['world_T_cam']; names = [k[6:] for k in P.files if k.startswith('cam_T_')]
H = np.load(hands); tf = np.load(table); n, d = tf['plane_n'].astype(float), float(tf['plane_d'])
T = min(len(W), len(H['joints_left']))
J = {s: H[f'joints_{s}'][:T].astype(float) for s in ('left', 'right')}
V = {s: H[f'valid_{s}'][:T].astype(bool) for s in ('left', 'right')}
pts = {o: trimesh.sample.sample_surface(trimesh.load(f'{mesh_dir}/{o}.glb', force='mesh'), 600, seed=0)[0] for o in names}
Tw = {o: np.stack([W[t] @ P[f'cam_T_{o}'][t] for t in range(T)]) for o in names}
for o in names:
    c = Tw[o][:, :3, 3]; sp = np.linalg.norm(np.gradient(uniform_filter1d(c, 5, axis=0), axis=0), axis=1) * fps * 100
    lab = []
    for t in range(T):
        X = pts[o] @ Tw[o][t][:3, :3].T + Tw[o][t][:3, 3]
        hgt = (X @ n + d).min() * 100
        hd = min([np.linalg.norm(J[s][t][:, None] - X[None], axis=2).min() * 100 for s in J if V[s][t]] or [99])
        od = min([np.linalg.norm((pts[q] @ Tw[q][t][:3, :3].T + Tw[q][t][:3, 3])[::6, None] - X[None, ::6], axis=2).min() * 100
                  for q in names if q != o] or [99])
        up = (c[min(t + 3, T - 1)] - c[max(t - 3, 0)]) @ n * 100
        if sp[t] < 3: l = 'rest' if hd > 2.5 else 'rest+hand'
        elif hd <= 2.5 and hgt > 1.5: l = 'carry'
        elif hd <= 2.5 and up > 1.0: l = 'lift'
        elif hd <= 2.5: l = 'slide'
        elif od <= 2.0 and hd > 4: l = 'tool'
        else: l = 'free'
        lab.append(l)
    segs, s0 = [], 0
    for t in range(1, T + 1):
        if t == T or lab[t] != lab[s0]:
            if t - s0 >= 3 or not segs: segs.append((s0, t - 1, lab[s0]))
            elif segs: segs[-1] = (segs[-1][0], t - 1, segs[-1][2])
            s0 = t
    print(f'{o}: ' + ', '.join(f'{a}-{b} {l}' for a, b, l in segs))
