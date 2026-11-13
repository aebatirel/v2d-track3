"""Release check and delayed release (2026-11-13; the Track 3 winner's "where an early release would drop an object, the
robot hand holds a little longer"). GT-free: our reference only.

For every hold phase of the reference (pipeline/hold_phases.py) that ends in a PLACEMENT (the reference keeps the object
within --still_cm of its release pose for the next --k frames), a drop test runs in FlashCHORD: the environment is reset
EXPLICITLY at frame end-2 (object, hands and fingers exactly as the reference says), VOC assist 0, zero residual action
(the hands follow the reference), for --k + D frames; the object's largest position / rotation deviation from the
reference after the release is the drift. If the drift at D = 0 exceeds --max_cm or --max_deg, the releasing hand's wrist,
fingers and frames are held at frame end-1 for D frames (D from --delays, bounded by the hand's next hold start minus
--blend), then blended back to the reference over --blend frames; the smallest D whose drop test passes is kept.
"end" holds the hand to the end of the clip (tools/hold_freeze.py; eval 16 on 2 Nov: 0.850 -> 0.974 official). Releases
are processed in time order on the progressively modified reference. Object poses are never changed.
Run with FlashCHORD's venv from the flash_chord directory (as tools/trace_rollout.py):
  release_fix.py IN.parquet OUT.parquet REPORT.json [--k 20] [--max_cm 1.5] [--max_deg 10] [--delays 4,8,12,20,40,end]
Env: EMB (embodiment config name), DEV (cpu|cuda, default cpu)."""
import argparse, dataclasses, json, os, sys, tempfile, time

import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq
from scipy.spatial.transform import Rotation as R, Slerp

REPO = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
sys.path.insert(0, os.path.join(REPO, 'pipeline'))
from hold_phases import hold_phases  # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument('inp'); ap.add_argument('out'); ap.add_argument('report')
ap.add_argument('--k', type=int, default=20)
ap.add_argument('--still_cm', type=float, default=1.0)
ap.add_argument('--max_cm', type=float, default=1.5)
ap.add_argument('--max_deg', type=float, default=10.0)
ap.add_argument('--delays', default='4,8,12,20,40,end')
ap.add_argument('--blend', type=int, default=6)
ap.add_argument('--pre', type=int, default=2, help='start the drop test this many frames before the release')
a = ap.parse_args()
for q in (a.inp,):
    assert not any(s in q for s in ('observation', 'score_registered', '_pf.npz', '/gt/')), q
HAND_COLS = ('wrist_position', 'wrist_wxyz', 'finger_joints', 'frames')


def load(path):
    t = pq.read_table(path)
    T = len(np.array(t.column('robot_left_wrist_position')[0].as_py(), float).reshape(-1, 3))
    names = t.column('object_body_names')[0].as_py()
    OP = np.array(t.column('object_body_position')[0].as_py(), float).reshape(T, len(names), 3)
    OQ = np.array(t.column('object_body_wxyz')[0].as_py(), float).reshape(T, len(names), 4)
    return t, T, names, OP, OQ


def hold_hand(t, T, side, e, D, blend):
    """Hold hand `side` at frame e-1 for frames [e, e+D) (D=None: to the end), then blend back over `blend` frames."""
    for c in HAND_COLS:
        col = f'robot_{side}_{c}'
        v = np.array(t.column(col)[0].as_py(), float); sh = v.shape; v = v.reshape(T, -1); orig = v.copy()
        hold_end = T if D is None else min(T, e + D)
        v[e:hold_end] = orig[e - 1]
        if D is not None:
            for i in range(blend):
                f = hold_end + i
                if f >= T: break
                w = (i + 1) / (blend + 1)                       # weight of the reference
                if c == 'wrist_wxyz':
                    q0, q1 = orig[e - 1][[1, 2, 3, 0]], orig[f][[1, 2, 3, 0]]
                    q = Slerp([0, 1], R.from_quat([q0, q1]))(w).as_quat(); v[f] = q[[3, 0, 1, 2]]
                else:
                    v[f] = (1 - w) * orig[e - 1] + w * orig[f]
        i_ = t.column_names.index(col)
        t = t.set_column(i_, col, pa.array([v.reshape(sh).tolist()], type=t.schema.field(col).type))
    return t


class Sim:
    """One FlashCHORD scene per reference file, reset explicitly at any frame, zero residual action, VOC 0."""
    def __init__(self):
        import warp as wp
        from hydra import compose, initialize_config_dir
        self.wp, self.compose, self.icd = wp, compose, initialize_config_dir

    def drop(self, parquet, start, n, obj_index):
        import warp as wp
        from flash_chord.configuration import instantiate_typed
        from flash_chord.embodiments.base import Embodiment
        from flash_chord.envs.rl import RLEnv, RLEnvConfig
        from flash_chord.scene.collision import CollisionPolicy
        from flash_chord.scene.setup import setup_scene
        off = [f'termination.{k}.enabled=false' for k in ('wrist_position', 'object_position', 'object_orientation', 'reference_end')]
        with self.icd(version_base='1.3', config_dir=os.path.abspath('src/flash_chord/configs')):
            cfg = self.compose(config_name='train_flash_sac', overrides=['experiment=sharpa_flash_sac', f"task.parquet='{parquet}'"] + off
                               + ([f"embodiment={os.environ['EMB']}"] if os.environ.get('EMB') else []))
        env_config = dataclasses.replace(instantiate_typed(cfg.env, RLEnvConfig), auto_reset=False, voc_scale=0.0)
        emb = instantiate_typed(cfg.embodiment, Embodiment); col = instantiate_typed(cfg.collision, CollisionPolicy)
        with wp.ScopedDevice(os.environ.get('DEV', 'cpu')):
            st = setup_scene(parquet=parquet, control_fps=env_config.sim.fps, motion_speed=1.0, embodiment=emb, collision=col,
                             world_count=1, include_support=True, decompose_objects=True)
            env = RLEnv(st.scene, st.reference, config=env_config)
            if os.environ.get('DEV', 'cpu') == 'cpu':           # Warp graph capture is not available on the CPU
                env._capture_step = lambda *x, **y: None
            env.reset(frame_id=start)
            bid = int(env.command.body_ids.numpy()[obj_index]) if hasattr(env, 'command') else None
            out = []
            for _ in range(n):
                env.step(None)
                q = env.state_0.body_q.numpy()
                out.append(q[bid] if bid is not None else q)
        return np.array(out)


def drift(sim_q, OP, OQ, j, start):
    """Largest position (cm) / rotation (deg) deviation of object j from the reference, frames start+1 .. start+len."""
    n = len(sim_q); f = np.arange(start + 1, start + 1 + n).clip(0, len(OP) - 1)
    dp = 100 * np.linalg.norm(sim_q[:, :3] - OP[f, j], axis=1)
    rs = R.from_quat(sim_q[:, 3:7]); rr = R.from_quat(OQ[f, j][:, [1, 2, 3, 0]])
    dr = np.degrees((rs.inv() * rr).magnitude())
    return float(dp.max()), float(dr.max())


t0 = time.time()
t, T, names, OP, OQ = load(a.inp)
phases = hold_phases(a.inp)[0]['phases']
sim = Sim(); rep = dict(input=a.inp, settings=vars(a), releases=[])
# candidates live in a mirrored reference tree: FlashCHORD resolves the support USDA as <seq dir>/../../reconstructed_stage
src = os.path.abspath(a.inp); assert '/processed/' in src, 'IN must sit in a reference tree (.../processed/<seq>/<robot>/x.parquet)'
root, sub = src.split('/processed/', 1)
tmproot = tempfile.mkdtemp(prefix='relfix_', dir=os.path.dirname(os.path.abspath(a.out)))
tmpdir = os.path.join(tmproot, 'processed', os.path.dirname(sub)); os.makedirs(tmpdir)
os.symlink(os.path.join(root, 'reconstructed_stage'), os.path.join(tmproot, 'reconstructed_stage'))
cur = a.inp
for ph in sorted(phases, key=lambda p: p['end']):
    side, o, e = ph['hand'], ph['object'], ph['end']
    j = names.index(o)
    r = dict(hand=side, object=o, release=e)
    if e >= T - 2:
        r['skip'] = 'held to the end already'; rep['releases'].append(r); continue
    after = OP[e:min(T, e + a.k), j]
    if 100 * np.linalg.norm(after - after[0], axis=1).max() > a.still_cm:
        r['skip'] = 'not a placement (object moves after the release in the reference)'; rep['releases'].append(r); continue
    nxt = [p['start'] for p in phases if p['hand'] == side and p['start'] > e]
    dmax = (min(nxt) - e - a.blend) if nxt else None
    start = max(0, e - a.pre)
    q = sim.drop(cur, start, a.k + a.pre, j)
    d0 = drift(q, OP, OQ, j, start); r['drift_D0'] = [round(d0[0], 2), round(d0[1], 1)]
    print('drop test', o, side, 'release', e, 'D=0 drift cm/deg', r['drift_D0'], flush=True)
    if d0[0] <= a.max_cm and d0[1] <= a.max_deg:
        r['decision'] = 'release as is'; rep['releases'].append(r); continue
    chosen = None
    for dd in a.delays.split(','):
        D = None if dd == 'end' else int(dd)
        if D is not None and dmax is not None and D > dmax: continue
        if D is None and nxt: continue                       # the hand is needed later
        tc = hold_hand(pq.read_table(cur), T, side, e, D, a.blend)
        cand = os.path.join(tmpdir, f'{o}_{side}_{e}_{dd}.parquet'); pq.write_table(tc, cand)
        n = a.k + a.pre + (0 if D is None else D)
        q = sim.drop(cand, start, min(n, T - start - 1), j)
        dD = drift(q, OP, OQ, j, start); r.setdefault('tried', []).append(dict(D=dd, drift=[round(dD[0], 2), round(dD[1], 1)]))
        if dD[0] <= a.max_cm and dD[1] <= a.max_deg:
            chosen = (dd, cand); break
    if chosen:
        r['decision'] = f'hold {chosen[0]} frames longer'; cur = chosen[1]
    else:
        r['decision'] = 'no delay passes; release kept'
    rep['releases'].append(r)
    print(json.dumps(r), flush=True)
pq.write_table(pq.read_table(cur), a.out)
rep['changed'] = cur != a.inp; rep['seconds'] = round(time.time() - t0, 1)
json.dump(rep, open(a.report, 'w'), indent=1)
print('release_fix:', sum('hold' in x.get('decision', '') for x in rep['releases']), 'releases delayed of',
      len(rep['releases']), '; wrote', a.out, flush=True)
