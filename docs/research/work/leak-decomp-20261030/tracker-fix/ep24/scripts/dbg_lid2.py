import sys, json
sys.path.insert(0, '/tmp/claude-0/-home-user-v2d-track3/68c88876-77c0-55d9-bea4-03de8a3f6ee7/scratchpad/leak/diag_24/scripts')
import numpy as np
import vo_anchor_test as V
XF = V.XF
ep = int(sys.argv[1]); n = sys.argv[2]; a, b = int(sys.argv[3]), int(sys.argv[4])
names, gt = XF.mocap(V.T3D, ep, None)
Vv = np.load(f'{V.ROOT}/Po/ep{ep}/poses_world_vo.npz'); T = Vv[n].astype(float)
P = V.lib_pts(n).mean(0)
x = T[:, :3, :3] @ P + T[:, :3, 3]
s = names.index(n); H = XF.host_geometry(V.T3D, n, s)
m = gt[n][:, :3, :3] @ H['anchor'] + gt[n][:, :3, 3]
kf = json.load(open(f'{V.S}/refine/in/ep{ep}/vo.json'))['keyframes']
print('keyframes', [k for k in kf if a <= k <= b])
for i in range(a, b):
    print(i, 'KF' if i in kf else '  ', 'ours', np.round((x[i] - x[a]) * 100, 2), round(float(np.linalg.norm(x[i] - x[a]) * 100), 2), ' mocap', round(float(np.linalg.norm(m[i] - m[a]) * 100), 2))
