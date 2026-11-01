"""Do the robot hands disturb objects at rest during the zero-action replay? (CPU, report only; keen-heisenberg's
falsifier.) Two runs of the same FlashCHORD env (as tools/trace_rollout.py zero: explicit reset at frame 0, VOC 0):
  hands  : zero action, the hands follow the reference (the pack's rest check);
  parked : the actuator gains are zeroed and the wrists parked 3 m away, the objects untouched, no drive.
Per object, over its rest_check window (frames 0 .. first hold start - 6, pipeline/hold_phases), the largest
displacement / rotation from its simulated frame-0 pose, and in the hands run the first robot-object contacts (frame,
robot body). Our reference only; no ground truth.  Usage: rest_probe.py REF.parquet OUT.json"""
import collections, json, os, sys
if os.environ.get('USE_COPY'):
    sys.path.insert(0, os.path.join(os.environ['USE_COPY'], 'src'))
sys.path.insert(0, '/home/user/v2d-track3/tools/physics_solve'); sys.path.insert(0, '/home/user/v2d-track3/pipeline')
import numpy as np, warp as wp, mujoco
from scipy.spatial.transform import Rotation as R
wp.config.log_level = wp.LOG_WARNING
import solve as S
from hold_phases import hold_phases
ref = sys.argv[1]; ph = hold_phases(ref)[0]['phases']
res = {}
for mode in ('hands', 'parked'):
    env, labels = S.build_env(ref, 1, planner=False); sol = env.solver; m = sol.mj_model; md = sol.mjw_data
    bname = [mujoco.mj_id2name(m, mujoco.mjtObj.mjOBJ_BODY, b) or f'body{b}' for b in range(m.nbody)]; gb = [int(x) for x in m.geom_bodyid]
    objs = [l for l in labels if l.startswith('track3_') and l.endswith('/object')]; oi = [labels.index(l) for l in objs]; names = [l[7:-7] for l in objs]
    win = {}
    for n in names:
        first = min((x['start'] for x in ph if x['object'] == n), default=min((x['start'] for x in ph), default=10 ** 6)); win[n] = first - 6
    T = max(1, max(win.values()))
    with S.on(env):
        env.reset(frame_id=0)
        if mode == 'parked':
            for nm in ('actuator_gainprm', 'actuator_biasprm'):
                arr = getattr(sol.mjw_model, nm); v = arr.numpy(); v[...] = 0; arr.assign(v)
            q = env.state_0.joint_q.numpy().copy(); q[0:3] = [3.0, 0.0, 0.3]; q[29:32] = [-3.0, 0.0, 0.3]
            env.state_0.joint_q.assign(q.astype(np.float32)); env.state_0.joint_qd.zero_()
            import newton; newton.eval_fk(env.scene.model, env.state_0.joint_q, env.state_0.joint_qd, env.state_0)
        Q = [env.state_0.body_q.numpy()[oi].copy()]; first_touch = {}; touch_log = collections.Counter()
        for k in range(T):
            if mode == 'parked':
                sub = int(env.config.sim.substeps); dt = float(env.config.sim.sim_dt)
                for s in range(sub):
                    env.state_0.clear_forces(); sol.step(env.state_0, env.state_1, env.control, env.contacts, dt); env.state_0, env.state_1 = env.state_1, env.state_0
            else:
                env.step(None)
            Q.append(env.state_0.body_q.numpy()[oi].copy())
            n = int(md.nacon.numpy()[0]); g = md.contact.geom.numpy()[:n]
            for a_, b_ in g:
                A, B = bname[gb[int(a_)]], bname[gb[int(b_)]]
                for x, y in ((A, B), (B, A)):
                    if 'track3_' in x and 'track3_' not in y and 'support' not in y.lower() and y != 'world':
                        o = x.split('track3_')[1].split('/')[0]; o = o[:-len('_object')] if o.endswith('_object') else o
                        if k + 1 > win.get(o, 0):
                            continue                                       # only inside that object's rest window
                        touch_log[(o, y)] += 1
                        if o not in first_touch: first_touch[o] = dict(frame=k + 1, robot_body=y)
    Q = np.array(Q); out = {}
    for j, n in enumerate(names):
        e = min(len(Q), max(1, win[n]))
        dp = 1000 * np.linalg.norm(Q[:e, j, :3] - Q[0, j, :3], axis=1); dr = np.degrees((R.from_quat(Q[:e, j, 3:7]) * R.from_quat(Q[0, j, 3:7]).inv()).magnitude())
        out[n] = dict(until_frame=int(e), max_mm=round(float(dp.max()), 1), max_deg=round(float(dr.max()), 1),
                      first_robot_touch=first_touch.get(n), touches_in_window={y: c for (o, y), c in touch_log.items() if o == n})
    res[mode] = out; print(mode, json.dumps(out), flush=True)
json.dump(res, open(sys.argv[2], 'w'), indent=1)
