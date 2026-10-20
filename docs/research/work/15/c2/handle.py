"""Pot handle free length: cross-section width of white_pot scan along its long axis (scan frame, mm)."""
import trimesh, numpy as np
m = trimesh.load('/Users/aebatirel/Documents/Code/v2d-research/data/track_3/public/mesh/white_pot/white_pot.glb', force='mesh')
v = np.asarray(m.vertices) * 1000.0
ext = v.max(0) - v.min(0); ax = int(np.argmax(ext)); oth = [i for i in range(3) if i != ax]
print('extent mm', ext.round(1), 'long axis', ax)
lo, hi = v[:, ax].min(), v[:, ax].max()
for x in np.arange(lo, hi, 10.0):
    s = v[(v[:, ax] >= x) & (v[:, ax] < x + 10)]
    if len(s) < 20: print(f'{x - lo:6.0f} n={len(s)}'); continue
    w = np.percentile(s[:, oth], 99, 0) - np.percentile(s[:, oth], 1, 0)
    print(f'{x - lo:6.0f}-{x - lo + 10:4.0f}  w{oth[0]}={w[0]:6.1f}  w{oth[1]}={w[1]:6.1f}  n={len(s)}')
