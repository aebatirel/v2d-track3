# Object-object overlap of two meshes posed by a poses.npz (census1 method: 2 mm winding-number solid samples of each
# mesh, mapped into the other, exact winding-sign distance; reported overlap = mean of both directions, cm^3).
# Inference-legal when POSES are our tracks; a diagnostic when POSES come from mocap (then say so in the tag).
# Usage: eval_pair.py MESH_A MESH_B POSES.npz NAME_A NAME_B FRAMES(a:b:s) [WINDOW a:b ...]
import sys, os, json, numpy as np, trimesh
sys.path.insert(0, '/tmp/claude-0/-home-user-v2d-track3/8c892c5e-fd7c-57aa-abef-68d2af098e4f/scratchpad/interact')
import vox2
PITCH = 0.002; H3 = PITCH ** 3 * 1e6
mA, mB, poses, nA, nB, fr = sys.argv[1:7]; wins = sys.argv[7:]
def load(p):
    m = trimesh.load(p, force='mesh'); m.merge_vertices(); sd = vox2.SD(m, 'winding')
    pts = vox2.solid_samples(m, sd, PITCH)[0]
    return dict(m=m, sd=sd, pts=np.asarray(pts, np.float64), lo=m.bounds[0] - 1e-3, hi=m.bounds[1] + 1e-3)
A, B = load(mA), load(mB)
P = np.load(poses); TA, TB = P[f'cam_T_{nA}'], P[f'cam_T_{nB}']
a, b, s = map(int, fr.split(':')); b = min(b, len(TA))
def ov(X, Y, T):
    Q = X['pts'] @ T[:3, :3].T + T[:3, 3]; box = np.all((Q >= Y['lo']) & (Q <= Y['hi']), 1)
    if not box.any():
        return 0.0, 0.0
    d = Y['sd'](Q[box]); k = d < 0
    return k.sum() * H3, float(-d[k].min()) * 1e3 if k.any() else 0.0
rows = []
for t in range(a, b, s):
    T_BA = np.linalg.inv(TB[t]) @ TA[t]
    o1, p1 = ov(A, B, T_BA); o2, p2 = ov(B, A, np.linalg.inv(T_BA))
    rows.append((t, (o1 + o2) / 2, max(p1, p2)))
R = np.array(rows)
out = dict(meshA=mA, meshB=mB, volA_cm3=round(len(A['pts']) * H3, 1), volB_cm3=round(len(B['pts']) * H3, 1),
           max_overlap_cm3=round(float(R[:, 1].max()), 2), frame_of_max=int(R[np.argmax(R[:, 1]), 0]),
           frames_gt1cm3=int((R[:, 1] > 1).sum()), n_frames=len(R), max_pen_mm=round(float(R[:, 2].max()), 1))
for w in wins:
    w0, w1 = map(int, w.split(':')); sel = (R[:, 0] >= w0) & (R[:, 0] < w1)
    if sel.any():
        out[f'win_{w}'] = dict(median_cm3=round(float(np.median(R[sel, 1])), 2), max_cm3=round(float(R[sel, 1].max()), 2),
                               median_pen_mm=round(float(np.median(R[sel, 2])), 1))
print(json.dumps(out))
