"""Floor crossing in a carve_fc_test run: the beige collision pieces vs the blue cup's one-piece floor plate (ev10cs4).
The plate's thin direction is the cup axis. Per frame: the beige piece vertices in the blue mesh frame (relT), their
depth past the plate's cavity face, and whether any goes past the far face (through). Our reference only."""
import glob, json, sys
import numpy as np, trimesh
P, RUN = sys.argv[1], sys.argv[2]
blue = {f: trimesh.load(f, force='mesh') for f in sorted(glob.glob(f'{P}/blue_cup/piece_*.obj'))}
beige = np.vstack([np.asarray(trimesh.load(f, force='mesh').vertices) for f in sorted(glob.glob(f'{P}/beige_cup/piece_*.obj'))])
vol = {f: abs(m.volume) for f, m in blue.items()}
plate_f = min(vol, key=lambda f: abs(vol[f] - 22.665e-6)); plate = np.asarray(blue[plate_f].vertices)
c = plate.mean(0); u, s, vt = np.linalg.svd(plate - c); n = vt[2]                    # thin direction = cup axis
pr = (plate - c) @ n; lo, hi = pr.min(), pr.max()
wall = np.vstack([np.asarray(m.vertices) for f, m in blue.items() if f != plate_f]); side = np.sign(np.median((wall - c) @ n))
cav_face, far_face = (hi, lo) if side > 0 else (lo, hi)                              # the face toward the cavity, the far face
sgn = -side                                                                          # positive = going from the cavity into the plate
rows = json.load(open(RUN))['series']; out = []
for r in rows:
    T = np.array(r['relT']); X = beige @ T[:3, :3].T + T[:3, 3]; p = (X - c) @ n
    depth = sgn * (p - cav_face); radial = np.linalg.norm((X - c) - np.outer((X - c) @ n, n), axis=1)
    inside = radial < 0.034                                                          # within the plate's ring (r >= 34 mm)
    d = depth[inside].max() if inside.any() else -1.0
    out.append(dict(f=r['f'], max_depth_mm=round(float(d) * 1000, 2), through=bool(d > (hi - lo))))
md = max(o['max_depth_mm'] for o in out)
d_all = [o['max_depth_mm'] for o in out]; late = [o['max_depth_mm'] for o in out if o['f'] >= out[0]['f'] + 6]
print(json.dumps(dict(settled_median_depth_mm=float(np.median(late)) if late else None, settled_max_depth_mm=float(max(late)) if late else None, plate=plate_f.split('/')[-1], plate_thickness_mm=round(float(hi - lo) * 1000, 2), plate_cm3=round(vol[plate_f] * 1e6, 2),
                      frames=len(out), max_depth_into_plate_mm=md, frames_into_plate=sum(o['max_depth_mm'] > 0 for o in out),
                      frames_through=sum(o['through'] for o in out), worst=sorted(out, key=lambda o: -o['max_depth_mm'])[:3])))
