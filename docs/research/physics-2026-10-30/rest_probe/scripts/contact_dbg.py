import collections, os, sys
sys.path.insert(0, '/home/user/v2d-track3/tools/physics_solve')
import numpy as np, warp as wp, mujoco
wp.config.log_level = wp.LOG_WARNING
import solve as S
env, labels = S.build_env(sys.argv[1], 1, planner=False); sol = env.solver; m = sol.mj_model; md = sol.mjw_data
bname = [mujoco.mj_id2name(m, mujoco.mjtObj.mjOBJ_BODY, b) or f'body{b}' for b in range(m.nbody)]; gb = [int(x) for x in m.geom_bodyid]
print('nbody', m.nbody, 'ngeom', m.ngeom, 'sample body names', bname[:3], [b for b in bname if 'track3' in b][:4])
cnt = collections.Counter(); first = {}
with S.on(env):
    env.reset(frame_id=0)
    for k in range(int(sys.argv[2])):
        env.step(None); n = int(md.nacon.numpy()[0]); g = md.contact.geom.numpy()[:n]; dist = md.contact.dist.numpy()[:n] if hasattr(md.contact, 'dist') else np.zeros(n)
        for (a, b), d in zip(g, dist):
            p = tuple(sorted((bname[gb[int(a)]], bname[gb[int(b)]])))
            if any('track3' in x for x in p) and d < 0.002:
                cnt[p] += 1; first.setdefault(p, k + 1)
for p, c in cnt.most_common(12): print(c, first[p], p)
