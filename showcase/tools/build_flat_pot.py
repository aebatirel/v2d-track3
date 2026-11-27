"""Clean, flat-bottomed saucepan for the showcase renders (owner 2026-11-27: "use a flat bottom version of the pot so it
doesn't pass into the table ... you can showcase another pot for that").

Why: in the scan's own frame the pot's symmetry axis is NOT the x axis. The pot rests flat on the table only with the
frame tilted ~12.5 deg (physics and the mocap-checked reference agree), so a lathe built around x (library_c0) dips up to
8 mm into the table at rest (a brown spot shows through its floor).

Here the axis is taken from the resting pose: u = R_rest^T * world-up, from a recorded replay frame where the pot sits on
the table. The base plane is perpendicular to u and passes through the scan's lowest points along -u, so the flat base
coincides with the tabletop at rest.
The body is a lathe with:
  - outer radius per height from the scan (robust percentile, marker balls and the handle excluded, smoothed);
  - 3 mm wall, 4 mm floor, 8 mm bottom fillet, rolled rim.
The handle is library_c0's (already ICP-aligned onto the scan), cut where it leaves the body and unioned (manifold).
library_c0's marker balls are kept where they still sit on the new surface. Output in the scan's frame, so the
recorded body poses apply unchanged. Rendering only; the physics used the official scan.
  build_flat_pot.py TRACE.npz OUT_DIR   (OUT_DIR/mesh/white_pot/white_pot.glb + OUT_DIR/urdf/white_pot_rigid.urdf)
"""
import os, sys

import numpy as np
import trimesh
from scipy.spatial.transform import Rotation as R

trace, out = sys.argv[1], sys.argv[2]
scan = trimesh.load('/content/t3/mesh/white_pot/white_pot.glb', force='mesh'); V = np.asarray(scan.vertices)
c0 = trimesh.load('/content/showcase/objects_clean/mesh/white_pot/white_pot.glb', force='mesh')   # ICP-aligned library_c0
d = np.load(trace); Q = d['q']; L = [str(x) for x in d['labels']]
i = [k for k, l in enumerate(L) if 'white_pot' in l][0]
q = Q[5, i]                                               # resting on the table (frame 5)
u = R.from_quat(q[3:]).inv().apply([0, 0, 1.0]); u /= np.linalg.norm(u)
print('pot axis in the scan frame', np.round(u, 4), 'tilt from x', round(float(np.degrees(np.arccos(abs(u[0])))), 2), 'deg')
# orthonormal frame (u, e1, e2); e1 toward the handle (scan +z side, projected)
hv = np.array([0, 0, 1.0]); e1 = hv - u * (u @ hv); e1 /= np.linalg.norm(e1); e2 = np.cross(u, e1)
h = V @ u; b0 = h.min()                                   # base plane along u
body = V[(V @ e1) < 0.065]                                # exclude the handle side beyond the body
hb = body @ u - b0
yz = np.c_[body @ e1, body @ e2]
sel = (hb > 0.02) & (hb < 0.10)
A = np.c_[2 * yz[sel], np.ones(sel.sum())]; sol = np.linalg.lstsq(A, (yz[sel] ** 2).sum(1), rcond=None)[0]; cxy = sol[:2]
r = np.linalg.norm(yz - cxy, axis=1)
H = float(np.percentile(hb, 99.8))                        # rim height
bins = np.linspace(0, H, 14); prof = []
for a, b in zip(bins[:-1], bins[1:]):
    s = (hb >= a) & (hb < b)
    if s.sum() > 200: prof.append(((a + b) / 2, float(np.percentile(r[s], 80))))
prof = np.array(prof); prof[:, 1] = np.convolve(np.pad(prof[:, 1], 1, mode='edge'), np.ones(3) / 3, mode='valid')
R_mid = float(np.median(prof[(prof[:, 0] > 0.3 * H) & (prof[:, 0] < 0.9 * H), 1]))
R_bot = float(prof[0, 1])
print(f'height {H * 100:.1f} cm, outer radius bottom {R_bot * 100:.1f} / mid {R_mid * 100:.1f} cm, axis offset {np.round(cxy * 100, 2)} cm')
# profile (r, z) closed loop through the axis: flat base, fillet, slightly flared wall, rolled rim, inner wall, flat floor
wall, floor, fil, rim = 0.003, 0.004, 0.008, 0.0025
def r_out(z):
    return float(np.interp(z, prof[:, 0], prof[:, 1]))
pts = [(0.0, 0.0), (r_out(fil) - fil, 0.0)]
for t in np.linspace(-np.pi / 2, 0, 8)[1:]:                       # bottom fillet
    pts.append((r_out(fil) - fil + fil * np.cos(t), fil + fil * np.sin(t)))
for z in np.linspace(fil, H - rim, 18)[1:]:
    pts.append((r_out(z), z))
for t in np.linspace(0, np.pi, 10)[1:]:                         # rolled rim (half circle over the wall top)
    rc = r_out(H - rim) - rim; pts.append((rc + rim * np.cos(t), H - rim + rim * np.sin(t)))
for z in np.linspace(H - rim, floor + 0.002, 18)[1:]:
    pts.append((r_out(z) - wall - (rim * 2 - wall) * 0, z) if False else (r_out(z) - 2 * rim, z))
pts += [(r_out(floor) - 2 * rim - 0.002, floor), (0.0, floor)]
prof2 = np.array(pts)
lathe = trimesh.creation.revolve(prof2[::-1], sections=96)          # around local +Z
# local -> scan frame: local z = u, local x = e1, local y = e2, origin = base centre
M = np.eye(4); M[:3, 0], M[:3, 1], M[:3, 2] = e1, e2, u; M[:3, 3] = u * b0 + e1 * cxy[0] + e2 * cxy[1]
lathe.apply_transform(M)
if lathe.volume < 0:
    lathe.invert()
print('lathe watertight', lathe.is_watertight, 'volume cm3', round(lathe.volume * 1e6, 1))
# handle from library_c0: beyond the body on the handle side; a box around the handle bar (from its far part) keeps the
# bar only, not a sliver of the old wall; it overlaps the new wall by 4 mm for the union
C = np.asarray(c0.vertices); ce1 = C @ e1 - (M[:3, 3] @ e1); ce2 = C @ e2 - (M[:3, 3] @ e2); cu = C @ u - b0
far = ce1 > R_mid + 0.03
w2 = (np.percentile(ce2[far], 1) - 0.006, np.percentile(ce2[far], 99) + 0.006)
hu = (np.percentile(cu[far], 1) - 0.012, np.percentile(cu[far], 99) + 0.008)
L1 = ce1.max() + 0.01 - (R_mid - 0.004)
box = trimesh.creation.box(extents=[L1, w2[1] - w2[0], hu[1] - hu[0]])
Bm = np.eye(4); Bm[:3, 0], Bm[:3, 1], Bm[:3, 2] = e1, e2, u
Bm[:3, 3] = M[:3, 3] + e1 * ((R_mid - 0.004) + L1 / 2) + e2 * ((w2[0] + w2[1]) / 2) + u * ((hu[0] + hu[1]) / 2)
box.apply_transform(Bm)
c0_main = max(c0.split(only_watertight=False), key=lambda m: len(m.faces))
handle = trimesh.boolean.intersection([c0_main, box], engine='manifold')
print('handle watertight', handle.is_watertight, 'extent cm', np.round(handle.extents * 100, 1), 'width cm', round((w2[1] - w2[0]) * 100, 1), 'height band cm', np.round(np.array(hu) * 100, 1))
pot = trimesh.boolean.union([lathe, handle], engine='manifold')
# marker balls from library_c0 that still sit on the new surface (within 6 mm)
balls = [m for m in c0.split(only_watertight=False) if m.extents.max() < 0.02]
keep = []
for bm in balls:
    dist = abs(trimesh.proximity.signed_distance(pot, [bm.centroid])[0])
    if dist < 0.012: keep.append(bm)
if keep:
    pot = trimesh.boolean.union([pot] + keep, engine='manifold')
print('pot watertight', pot.is_watertight, 'faces', len(pot.faces), 'marker balls kept', len(keep), 'of', len(balls))
os.makedirs(f'{out}/mesh/white_pot', exist_ok=True); os.makedirs(f'{out}/urdf', exist_ok=True)
pot.export(f'{out}/mesh/white_pot/white_pot.glb')
u_txt = open('/content/t3/urdf/white_pot_rigid.urdf').read().replace('../mesh/white_pot/white_pot.glb', os.path.abspath(f'{out}/mesh/white_pot/white_pot.glb'))
open(f'{out}/urdf/white_pot_rigid.urdf', 'w').write(u_txt)
# resting check: lowest point at the rest pose vs the tabletop (0.60)
W = R.from_quat(q[3:]).apply(np.asarray(pot.vertices)) + q[:3]
print(f'rest pose: new pot min z {W[:, 2].min():.4f} (tabletop 0.6000); scan min z {(R.from_quat(q[3:]).apply(V) + q[:3])[:, 2].min():.4f}')
