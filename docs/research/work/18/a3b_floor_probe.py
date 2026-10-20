"""Probe the height distribution of map points along the reference-fit gravity (debug for the floor plane)."""
import json, numpy as np, pycolmap, sys
rec = pycolmap.Reconstruction(sys.argv[1]); J = json.load(open(sys.argv[2]))
Rf = np.array(J["reg"]["R_full"]); up = Rf.T @ np.array([0, 0, 1.0])
P = np.array([p.xyz for p in rec.points3D.values()]); E = np.array([p.error for p in rec.points3D.values()])
TL = np.array([p.track.length() for p in rec.points3D.values()])
Cs = []
for im in rec.images.values():
    T = im.cam_from_world(); R = T.rotation.matrix(); Cs.append(-R.T @ np.asarray(T.translation))
Cs = np.array(Cs); Cm = np.median(Cs, 0)
h = (P - Cm) @ up; g = (E < 2) & (TL >= 3)
print("cam spread along up (m): p5-p95", np.percentile((Cs - Cm) @ up, [5, 95]).round(3), "horiz sd", np.std(Cs - np.outer((Cs - Cm) @ up, up), 0).round(3))
hist, edges = np.histogram(h[g], bins=np.arange(-3, 3.01, 0.05))
for a, b in zip(edges[:-1], hist):
    if b > 30: print(f"{a:+.2f} {b:5d} " + "#" * int(b / 40))
d = np.linalg.norm(P - Cm, axis=1); print("point distance from camera median, p10-p90:", np.median(d[g]).round(2), np.percentile(d[g], [10, 90]).round(2))
