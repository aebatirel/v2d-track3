"""Gate 4 (no ground truth): frame-0 byte identity of refined vs input poses, per arm/episode/object.
Also counts changed frames and the max position/rotation change per object. Writes arms/frame0_check.json."""
import json, sys
import numpy as np
R = '/tmp/claude-0/-home-user-v2d-track3/68c88876-77c0-55d9-bea4-03de8a3f6ee7/scratchpad/refine'
EPS = [0, 2, 11, 12, 13, 18, 21, 22, 23, 24, 26, 27, 31, 39, 40, 41, 42, 43, 44, 45]
out = {}
for arm in sys.argv[1:]:
    out[arm] = {}
    for e in EPS:
        I = np.load(f'{R}/in/ep{e}/poses.npz'); O = np.load(f'{R}/arms/{arm}/ep{e}/poses.npz')
        IW = np.load(f'{R}/in/ep{e}/poses_world_vo.npz'); OW = np.load(f'{R}/arms/{arm}/ep{e}/poses_world_vo.npz')
        r = dict(world_T_cam_identical=bool(I['world_T_cam'].tobytes() == O['world_T_cam'].tobytes()),
                 keys_same=sorted(I.files) == sorted(O.files), obj={})
        for k in I.files:
            if not k.startswith('cam_T_'):
                continue
            n = k[6:]
            a, b = I[k], O[k]; wa, wb = IW[n], OW[n]
            ch = np.array([a[t].tobytes() != b[t].tobytes() for t in range(len(a))])
            dp = np.linalg.norm(wa[:, :3, 3] - wb[:, :3, 3], axis=1) * 100
            dR = np.einsum('tij,tik->tjk', wa[:, :3, :3], wb[:, :3, :3])
            ang = np.degrees(np.arccos(np.clip((np.trace(dR, axis1=1, axis2=2) - 1) / 2, -1, 1)))
            r['obj'][n] = dict(f0_cam_identical=bool(a[0].tobytes() == b[0].tobytes()),
                               f0_world_identical=bool(wa[0].tobytes() == wb[0].tobytes()),
                               dtype=str(b.dtype), frames_changed=int(ch.sum()), T=len(a),
                               max_dpos_cm=round(float(dp.max()), 3), max_drot_deg=round(float(ang.max()), 3),
                               f0_dpos_cm=round(float(dp[0]), 3), f0_drot_deg=round(float(ang[0]), 3))
        out[arm][e] = r
json.dump(out, open(f'{R}/arms/frame0_check.json', 'w'), indent=1)
for arm in out:
    f0 = [(e, n) for e in out[arm] for n, v in out[arm][e]['obj'].items() if not v['f0_cam_identical']]
    nch = sum(v['frames_changed'] for e in out[arm] for v in out[arm][e]['obj'].values())
    wtc = all(out[arm][e]['world_T_cam_identical'] and out[arm][e]['keys_same'] for e in out[arm])
    print(f'{arm:5s} world_T_cam+keys ok={wtc} frames_changed_total={nch} f0_changed={len(f0)} {f0[:12]}')
