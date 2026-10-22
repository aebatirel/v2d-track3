# GT-free: overlap of two of OUR meshes posed by OUR tracks (2 mm solid samples, exact winding-number signed distance,
# both directions averaged), at selected frames. Usage (fcvenv):
#   pairovl.py POSES NAME_A MESH_A NAME_B MESH_B FRAMES(a:b[,c:d]) [STRIDE]
import sys, json, numpy as np, trimesh
sys.path.insert(0, '/tmp/claude-0/-home-user-v2d-track3/8c892c5e-fd7c-57aa-abef-68d2af098e4f/scratchpad/interact')
import vox2
PITCH = 0.002
P = np.load(sys.argv[1]); na, ma, nb, mb = sys.argv[2:6]
fr = []
for seg in sys.argv[6].split(','):
    a, b = map(int, seg.split(':')); fr += list(range(a, b, int(sys.argv[7]) if len(sys.argv) > 7 else 2))
M = {}
for n, path in ((na, ma), (nb, mb)):
    m = trimesh.load(path, force='mesh'); m.merge_vertices(); sd = vox2.SD(m, 'winding')
    pts, _, _ = vox2.solid_samples(m, sd, PITCH)
    M[n] = (m, sd, pts)
ov = []; pen = []
for t in fr:
    if t >= len(P[f'cam_T_{na}']):
        continue
    vals = []; pp = []
    for A, B in ((na, nb), (nb, na)):
        T = np.linalg.inv(P[f'cam_T_{B}'][t]) @ P[f'cam_T_{A}'][t]
        Q = M[A][2] @ T[:3, :3].T + T[:3, 3]
        lo, hi = M[B][0].bounds
        sel = np.all((Q >= lo - 0.001) & (Q <= hi + 0.001), 1)
        d = M[B][1](Q[sel]); vals.append(float((d < 0).sum()) * PITCH ** 3 * 1e6); pp.append(float(max(0, -d.min())) if len(d) else 0)
    ov.append(np.mean(vals)); pen.append(max(pp))
ov = np.array(ov); pen = np.array(pen)
r = dict(frames=len(ov), overlap_med_cm3=round(float(np.median(ov)), 2), overlap_max_cm3=round(float(ov.max()), 2),
         pen_med_mm=round(float(np.median(pen)) * 1e3, 1), vol_a_cm3=round(len(M[na][2]) * PITCH ** 3 * 1e6, 1), vol_b_cm3=round(len(M[nb][2]) * PITCH ** 3 * 1e6, 1))
print(json.dumps(r))
