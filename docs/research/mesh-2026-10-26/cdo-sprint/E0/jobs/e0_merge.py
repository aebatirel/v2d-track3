"""Concatenate obs_points.py files (pts, cam, frame), as the public 'ep21+22' blue-cup points were merged (2.31 M =
1.20 M + 1.11 M, no alignment). Usage: e0_merge.py OUT.npz IN1.npz IN2.npz ..."""
import sys
import numpy as np
Z = [np.load(f) for f in sys.argv[2:]]
np.savez_compressed(sys.argv[1], **{k: np.concatenate([z[k] for z in Z]) for k in ('pts', 'cam', 'frame')})
print(sys.argv[1], sum(len(z['pts']) for z in Z), 'points from', len(Z), 'files')
