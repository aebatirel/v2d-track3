"""DIAGNOSTIC (2026-10-23): how far are the fingertips from an object, in the reference and in recorded rollouts
(tools/trace_rollout.py)? Per frame and hand: the smallest fingertip-to-surface distance and the number of tips within
1.5 cm, for the reference (its robot frames and object poses) and for each trace. Points = the five distal phalanx origins
(DP), the same physical points in both (sim and reference coincide to 0.0 mm at reset; the reference's DP orientation is
not rigid to its tip sites for the four fingers, so tips are not reconstructed); "touching" = DP origin within 3 cm of
the surface (a DP origin sits 2-3 cm behind the fingertip). Also the mean DP distance sim-reference (finger tracking), the simulated wrist (C_MC) distance to the
reference wrist and the simulated object displacement. No ground truth is read.
Usage: hand_object_gap.py PARQUET MESH_DIR OBJECT TRACE.npz[:label] ... [--every 20]
"""
import argparse

import numpy as np
import pyarrow.parquet as pq
import trimesh
from scipy.spatial.transform import Rotation as R

FINGERS = ('thumb', 'index', 'middle', 'ring', 'pinky')
p = argparse.ArgumentParser(); p.add_argument('parquet'); p.add_argument('mesh_dir'); p.add_argument('obj')
p.add_argument('traces', nargs='+'); p.add_argument('--every', type=int, default=20)
a = p.parse_args()
t = pq.read_table(a.parquet); names = t.column('object_body_names')[0].as_py(); j = names.index(a.obj)
T = len(np.array(t.column('robot_left_wrist_position')[0].as_py(), float).reshape(-1, 3))
OP = np.array(t.column('object_body_position')[0].as_py(), float).reshape(T, len(names), 3)[:, j]
OQ = np.array(t.column('object_body_wxyz')[0].as_py(), float).reshape(T, len(names), 4)[:, j][:, [1, 2, 3, 0]]
mesh = trimesh.load(f'{a.mesh_dir}/{a.obj}/{a.obj}.glb', force='mesh'); pq_ = trimesh.proximity.ProximityQuery(mesh)


def gap(pts, pos, quat):  # unsigned distance of world points to the object surface at (pos, quat xyzw)
    loc = R.from_quat(quat).inv().apply(pts - pos); d = np.abs(pq_.signed_distance(loc)); return d


TOUCH = 0.03
ref = {}
for s in ('left', 'right'):
    fn = t.column(f'{s}_robot_frame_names')[0].as_py(); F = np.array(t.column(f'robot_{s}_frames')[0].as_py(), float).reshape(T, -1, 7)
    ref[s] = dict(dp=F[:, [fn.index(f'{s}_{f}_DP') for f in FINGERS], :3], wrist=F[:, fn.index(f'{s}_hand_C_MC'), :3])
traces = []
for spec in a.traces:
    path, _, lab = spec.partition(':'); d = np.load(path); L = [str(x) for x in d['labels']]; q = d['q'].astype(float)
    bid = {n: next(i for i, l in enumerate(L) if l.split('/')[-1] == n) for s in ('left', 'right') for n in [f'{s}_hand_C_MC'] + [f'{s}_{f}_DP' for f in FINGERS]}
    oid = next(i for i, l in enumerate(L) if l.startswith(f'track3_{a.obj}/'))
    traces.append((lab or path, q, d['frame'], bid, oid))
hdr = 'frame | ref: R DP<3cm, R gap cm, L gap cm'
for lab, *_ in traces:
    hdr += f' || {lab}: R DP<3cm, R gap, L gap, R fingers-ref cm, R wrist-ref cm, obj moved cm'
print(hdr)
for f in range(0, T, a.every):
    row = f'{f:5d} |'
    gr = {s: gap(ref[s]['dp'][f], OP[f], OQ[f]) for s in ('left', 'right')}
    row += f' {int((gr["right"] < TOUCH).sum())}  {100 * gr["right"].min():5.1f}  {100 * gr["left"].min():5.1f}'
    for lab, q, fr, bid, oid in traces:
        k = min(f, len(q) - 1); out = {}; dps = {}
        for s in ('left', 'right'):
            dps[s] = np.stack([q[k, bid[f'{s}_{fi}_DP'], :3] for fi in FINGERS])
            out[s] = gap(dps[s], q[k, oid, :3], q[k, oid, 3:7])
        fe = 100 * np.linalg.norm(dps['right'] - ref['right']['dp'][min(f, T - 1)], axis=1).mean()
        wr = 100 * np.linalg.norm(q[k, bid['right_hand_C_MC'], :3] - ref['right']['wrist'][min(f, T - 1)])
        mv = 100 * np.linalg.norm(q[k, oid, :3] - q[0, oid, :3])
        row += f' || {int((out["right"] < TOUCH).sum())}  {100 * out["right"].min():5.1f}  {100 * out["left"].min():5.1f}  {fe:5.1f}  {wr:5.1f}  {mv:5.1f}'
    print(row)
