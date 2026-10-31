"""GT-free: frame-0 -> frame-1 pose step vs later steps in the static prefix (our tracks only)."""
import sys, numpy as np
from scipy.spatial.transform import Rotation as Rot
S = '/tmp/claude-0/-home-user-v2d-track3/68c88876-77c0-55d9-bea4-03de8a3f6ee7/scratchpad'
EPS = [0, 2, 11, 12, 13, 18, 21, 22, 23, 24, 26, 27, 31, 39, 40, 41, 42, 43, 44, 45]
arm = sys.argv[1]
for ep in EPS:
    f = {'Po': f'{S}/leak/t1/in_Po/ep{ep}/poses_world_vo.npz', 'Ps': f'{S}/leak/p1/oracle_roots/Ps_scan/ep{ep}/poses_world_vo.npz',
         'rP': f'{S}/refine/in/ep{ep}/poses_world_vo.npz'}[arm]
    V = np.load(f); row = []
    for n in V.files:
        T = V[n].astype(float)
        def step(a, b):
            return np.linalg.norm(T[b][:3, 3] - T[a][:3, 3]) * 100, np.degrees(Rot.from_matrix(T[b][:3, :3] @ T[a][:3, :3].T).magnitude())
        s01 = step(0, 1); s15 = [step(i, i + 1) for i in range(1, 6)]
        row.append(f'{n[:12]} 0-1 {s01[0]:.2f}cm/{s01[1]:.2f}d  1-6 max {max(x[0] for x in s15):.2f}cm/{max(x[1] for x in s15):.2f}d')
    print(ep, ' | '.join(row))
