"""Render-only: translate an object mesh along its mean rest-up axis so its lowest point sits on the tabletop at rest
in every listed replay (2026-11-27: the clean library_c0 rack sat 2.6-4.1 mm below the tabletop at rest in the eval
replays, so the table showed through its cup-holder well). Rotation is unchanged; the shift is a few mm.
  lift_to_rest.py MESH.glb OUT.glb NAME T1.npz,T2.npz,... [--frame 0] [--ztop 0.60]
"""
import argparse

import numpy as np
import trimesh
from scipy.spatial.transform import Rotation as R

p = argparse.ArgumentParser(); p.add_argument('mesh'); p.add_argument('out'); p.add_argument('name'); p.add_argument('traces')
p.add_argument('--frame', type=int, default=0); p.add_argument('--ztop', type=float, default=0.60); a = p.parse_args()
m = trimesh.load(a.mesh, force='mesh'); V = np.asarray(m.vertices)
poses = []
for t in a.traces.split(','):
    d = np.load(t); L = [str(x) for x in d['labels']]; i = [k for k, l in enumerate(L) if l.split('/')[0] == f'track3_{a.name}'][0]
    poses.append(d['q'][a.frame, i])
u = np.mean([R.from_quat(q[3:]).inv().apply([0, 0, 1.0]) for q in poses], 0); u /= np.linalg.norm(u)
dips = [a.ztop - (R.from_quat(q[3:]).apply(V) + q[:3])[:, 2].min() for q in poses]
shift = max(0.0, float(np.max(dips)))
m.apply_translation(u * shift); m.export(a.out)
after = [(R.from_quat(q[3:]).apply(np.asarray(m.vertices)) + q[:3])[:, 2].min() - a.ztop for q in poses]
print(f'{a.name}: rest-up axis {np.round(u, 4)}, dips before (mm) {np.round(np.array(dips) * 1000, 1)}, shift {shift * 1000:.1f} mm, '
      f'lowest point after (mm) {np.round(np.array(after) * 1000, 1)}')
