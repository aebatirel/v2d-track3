"""Evolutionary grasp refinement against the simulator (2026-10-24; owner: "lets test that", the DexEvolve / DemoGrasp
question). One hold of a grasp-lock reference is edited by a constant grasp edit theta, applied through FlashCHORD's own
residual hand-pose action (runtime/actions/hand_pose.py: wrist target = reference + offset in m, wrist orientation =
reference * rpy residual, finger targets = reference + offset; raw input, EMA 0.3, clips 0.2 m / 1 rad / 1 rad):
  theta = [wrist offset in the OBJECT frame (3, m), wrist rotation in the wrist frame (3, rpy rad), finger offsets (nf, rad)]
ramped in over RAMP frames from the approach start, held through the hold, ramped out after the release. Every world of
one batched simulation runs a different candidate (world_count = population), so a generation costs one rollout.
Fitness (no ground truth): the kit's ADD AUC (1-9 cm, 500 points on a 5 cm sphere, as pipeline/qa.py) of the simulated
object against OUR reference over the window [hold start - PRE, hold end + POST], for the held object (others too if
--all_objects). The window starts from an explicit reset at its first frame (objects and hands on the reference).
Search: CMA-ES (default; Hansen's (mu/mu_w, lambda) with rank-mu and rank-one updates, in units of --sigma per block) or
--algo ga (DexEvolve-style: tournament selection, uniform crossover, Gaussian mutation, elitist archive). Generation 0
evaluates theta = 0 (the unedited grasp) in world 0.
Writes OUT.json (per generation: best / mean / timing; the best theta in physical units) and, with --bake OUT.parquet,
the reference with the best edit written into the hand's wrist pose and finger joints (check it with a plain zero-action
replay: tools/trace_rollout.py zero + tools/trace_score.py).
Usage (FlashCHORD venv, from the flash_chord dir; EMB = embodiment config, DEV = cpu | cuda):
  grasp_evolve.py REF.parquet GRASP_LOCK.json OUT.json [--phase 0] [--pop 16] [--gens 10] [--algo cmaes|ga] [--bake OUT.parquet]
"""
import argparse, dataclasses, json, os, sys, time

import numpy as np
from scipy.spatial.transform import Rotation as R

p = argparse.ArgumentParser()
p.add_argument('ref'); p.add_argument('grasp_lock'); p.add_argument('out')
p.add_argument('--phase', type=int, default=0); p.add_argument('--pop', type=int, default=16); p.add_argument('--gens', type=int, default=10)
p.add_argument('--algo', default='cmaes', choices=['cmaes', 'ga']); p.add_argument('--seed', type=int, default=0)
p.add_argument('--sigma_pos', type=float, default=0.02); p.add_argument('--sigma_rot', type=float, default=0.15)
p.add_argument('--sigma_fin', type=float, default=0.15); p.add_argument('--no_fingers', action='store_true')
p.add_argument('--pre', type=int, default=6); p.add_argument('--post', type=int, default=20); p.add_argument('--ramp', type=int, default=8)
p.add_argument('--all_objects', action='store_true'); p.add_argument('--bake', default='')
p.add_argument('--max_steps', type=int, default=0, help='debug: cap the rollout length')
p.add_argument('--init', default='', help="a previous OUT.json: start from its best theta (the search mean / the GA's first parent)")
a = p.parse_args()
rng = np.random.default_rng(a.seed)

import pyarrow as pa  # noqa: E402
import pyarrow.parquet as pq  # noqa: E402
t = pq.read_table(a.ref); names = t.column('object_body_names')[0].as_py(); B = len(names)
T = len(t.column('robot_left_wrist_position')[0].as_py())
OP = np.array(t.column('object_body_position')[0].as_py(), float).reshape(T, B, 3)
OQ = np.array(t.column('object_body_wxyz')[0].as_py(), float).reshape(T, B, 4)[..., [1, 2, 3, 0]]   # xyzw
ph = json.load(open(a.grasp_lock))['phases'][a.phase]
side, obj, hs, he = ph['hand'], ph['object'], int(ph['start']), int(ph['end'])
j_obj = names.index(obj)
a0 = int((ph.get('approach') or {}).get('from_frame', ph.get('hold_from', hs)))   # edit starts with the approach
f0 = max(0, min(a0, hs) - a.pre); f1 = min(T - 1, he + a.post)
if a.max_steps:
    f1 = min(f1, f0 + a.max_steps)
win = np.arange(f0, f1 + 1)


def weight(f):  # ramp in from the approach start, hold, ramp out after the release
    w_in = np.clip((f - a0) / max(a.ramp, 1), 0.0, 1.0)
    w_out = np.clip(1.0 - (f - he) / max(a.ramp, 1), 0.0, 1.0)
    return float(min(w_in, w_out))


import warp as wp  # noqa: E402
from hydra import compose, initialize_config_dir  # noqa: E402
from flash_chord.configuration import instantiate_typed  # noqa: E402
from flash_chord.embodiments.base import Embodiment  # noqa: E402
from flash_chord.envs.rl import RLEnv, RLEnvConfig  # noqa: E402
from flash_chord.scene.collision import CollisionPolicy  # noqa: E402
from flash_chord.scene.setup import setup_scene  # noqa: E402

W = a.pop
off = [f'termination.{k}.enabled=false' for k in ('wrist_position', 'object_position', 'object_orientation', 'reference_end')]
with initialize_config_dir(version_base='1.3', config_dir=os.path.abspath('src/flash_chord/configs')):
    cfg = compose(config_name='train_flash_sac', overrides=['experiment=sharpa_flash_sac', f"task.parquet='{a.ref}'"] + off
                  + ([f"embodiment={os.environ['EMB']}"] if os.environ.get('EMB') else []))
env_config = dataclasses.replace(instantiate_typed(cfg.env, RLEnvConfig), auto_reset=False, voc_scale=0.0)
emb = instantiate_typed(cfg.embodiment, Embodiment); col = instantiate_typed(cfg.collision, CollisionPolicy)
t_setup = time.time()
dev = wp.get_device(os.environ.get('DEV', 'cuda')); wp.set_device(dev)
st = setup_scene(parquet=a.ref, control_fps=env_config.sim.fps, motion_speed=1.0, embodiment=emb, collision=col,
                 world_count=W, include_support=True, decompose_objects=True)
env = RLEnv(st.scene, st.reference, config=env_config)
labels = list(getattr(st.scene.model, 'body_label', None) or getattr(st.scene.model, 'body_key', []))
nb = len(labels) // W
ob = [labels.index(f'track3_{n}/object') for n in names]                  # world 0 indices (labels repeat per world)
buf = env.action.buffers; lay = buf.layout; A = lay.action_dim
h = list(lay.sides).index(side); h0 = lay.hand_action_starts[h]; nf = lay.finger_counts[h]
# physical residual p (steady state of the EMA) -> policy input, inverting runtime/residual.py map_residual_input:
# identity: input = p / scale; linear: input = p / clip; rational: out = p / scale, input = out / (1 + |out| - |out| / s),
# s = input_scale (the experiment's normalised 'rational' mapping)
MODE = buf.input_mapping
PSCALE, PCLIP, PIS = (np.array(x.numpy(), float)[:A] for x in (buf.scale, buf.clip, buf.input_scale))
SCALE = PSCALE                                                                # for the log only


def to_input(phys, sl):
    ph_ = np.clip(phys, -0.98 * PCLIP[sl], 0.98 * PCLIP[sl])
    if MODE == 'identity':
        return ph_ / PSCALE[sl]
    if MODE == 'linear':
        return ph_ / PCLIP[sl]
    out = ph_ / PSCALE[sl]; m = np.abs(out)
    return out / (1.0 + m - m / PIS[sl])
dim = 6 + (0 if a.no_fingers else nf)
sig = np.concatenate([[a.sigma_pos] * 3, [a.sigma_rot] * 3, [a.sigma_fin] * (0 if a.no_fingers else nf)])
print(f'action input mapping {MODE}, scale {PSCALE[h0:h0 + 7].round(3).tolist()}, clip {PCLIP[h0:h0 + 7].round(3).tolist()}', flush=True)
print(f'setup {time.time() - t_setup:.1f} s: {W} worlds x {nb} bodies, action_dim {A}, {side} hand fingers {nf}, '
      f'phase {a.phase} {obj} hold {hs}-{he} approach {a0}, window {f0}-{f1} ({len(win)} frames), dim {dim}', flush=True)

# a constant (normalised) edit theta (W, dim) -> raw actions per frame (W, A); the action is in raw mode: physical = raw * scale
R_obj = R.from_quat(OQ[:, j_obj])


def actions(theta_phys, f):
    w = weight(f); act = np.zeros((W, A), np.float32)
    if w <= 0.0:
        return act
    dp_w = R_obj[f].apply(theta_phys[:, :3]) * w                                  # object frame -> world frame
    act[:, h0:h0 + 3] = to_input(dp_w, slice(h0, h0 + 3))
    act[:, h0 + 3:h0 + 6] = to_input(theta_phys[:, 3:6] * w, slice(h0 + 3, h0 + 6))
    if not a.no_fingers:
        act[:, h0 + 6:h0 + 6 + nf] = to_input(theta_phys[:, 6:6 + nf] * w, slice(h0 + 6, h0 + 6 + nf))
    return act


pts = rng.normal(size=(500, 3)); pts = 0.05 * pts / np.linalg.norm(pts, axis=1, keepdims=True)
THR = np.arange(0.01, 0.10, 0.01); AX = np.linspace(0.0, 1.0, THR.size)
trap = getattr(np, 'trapezoid', None) or np.trapz


def add_auc(sim_p, sim_q, ref_p, ref_q):  # (F, 3), (F, 4 xyzw): kit ADD AUC on sphere points
    a_ = R.from_quat(sim_q).as_matrix(); r_ = R.from_quat(ref_q).as_matrix()
    off_ = np.einsum('fij,vj->fvi', a_ - r_, pts) + (sim_p - ref_p)[:, None, :]
    add = np.linalg.norm(off_, axis=-1).mean(axis=-1)
    return float(trap(np.array([np.mean(add < x) for x in THR]), x=AX)), add


def evaluate(theta_phys):
    env.reset(frame_id=int(f0))
    track, frames = [], []
    for f in win:
        if f > f0:
            env.step(wp.array(actions(theta_phys, int(f)).reshape(-1), dtype=wp.float32, device=dev))
        q = env.state_0.body_q.numpy().reshape(W, nb, 7); track.append(q[:, ob].copy()); frames.append(int(env.timestep.numpy()[0]))
    if frames != [int(x) for x in win]:
        print('WARNING: env frames', frames[:3], '...', frames[-3:], 'vs window', int(win[0]), '...', int(win[-1]), flush=True)
    track = np.array(track)                                                       # (F, W, B, 7)
    objs = range(B) if a.all_objects else [j_obj]
    fit = np.zeros(W); detail = []
    for w_ in range(W):
        s = [add_auc(track[:, w_, j, :3], track[:, w_, j, 3:7], OP[win, j], OQ[win, j]) for j in objs]
        fit[w_] = np.mean([x[0] for x in s])
        hold = (win >= hs) & (win <= he)
        dz = track[hold, w_, j_obj, 2] - OP[win[hold], j_obj, 2]
        detail.append(dict(auc=round(fit[w_], 4), hold_add_cm_median=round(100 * float(np.median(s[0][1][hold])), 1),
                           lift_err_cm_median=round(100 * float(np.median(dz)), 1)))
    if os.environ.get('GE_DEBUG'):
        for k in (0, 1, 5, 10, len(win) - 1):
            print('debug frame', int(win[k]), 'sim', track[k, 0, j_obj, :3].round(4).tolist(), 'ref', OP[win[k], j_obj].round(4).tolist(),
                  'sim q', track[k, 0, j_obj, 3:7].round(3).tolist(), 'ref q', OQ[win[k], j_obj].round(3).tolist(), flush=True)
    return fit, detail, track


log = dict(args=vars(a), side=side, object=obj, hold=[hs, he], approach_from=a0, window=[int(f0), int(f1)], dim=dim,
           sigma=sig.tolist(), generations=[])
best = dict(fit=-1.0)
mean, C, ps, pc, sigma = np.zeros(dim), np.eye(dim), np.zeros(dim), np.zeros(dim), 1.0          # CMA-ES state (normalised)
if a.init:                                                                    # continue from an earlier search's best
    th0 = np.array(json.load(open(a.init))['best']['theta'], float); mean = (th0[:dim] / sig).copy(); log['init'] = a.init
lam = W; mu = lam // 2; wts = np.log(mu + 0.5) - np.log(np.arange(1, mu + 1)); wts /= wts.sum(); mueff = 1.0 / (wts ** 2).sum()
cc = (4 + mueff / dim) / (dim + 4 + 2 * mueff / dim); cs = (mueff + 2) / (dim + mueff + 5)
c1 = 2 / ((dim + 1.3) ** 2 + mueff); cmu = min(1 - c1, 2 * (mueff - 2 + 1 / mueff) / ((dim + 2) ** 2 + mueff))
damps = 1 + 2 * max(0, np.sqrt((mueff - 1) / (dim + 1)) - 1) + cs; chiN = np.sqrt(dim) * (1 - 1 / (4 * dim) + 1 / (21 * dim ** 2))
archive = []                                                                  # GA: (fit, z)
for g in range(a.gens):
    t0 = time.time()
    if a.algo == 'cmaes':
        evals, evecs = np.linalg.eigh(C); evals = np.maximum(evals, 1e-12); Bm = evecs * np.sqrt(evals)
        Z = rng.normal(size=(lam, dim)); Y = Z @ Bm.T; X = mean + sigma * Y
    else:
        if not archive:
            X = mean + rng.normal(size=(lam, dim)) * 0.5
        else:
            par = sorted(archive, key=lambda x: -x[0])[:max(4, lam)]
            X = []
            for _ in range(lam):
                i1, i2 = [int(min(rng.choice(len(par), min(3, len(par)), replace=False))) for _ in range(2)]   # tournaments of 3 (sorted)
                m = rng.random(dim) < 0.5; c_ = np.where(m, par[i1][1], par[i2][1])
                X.append(c_ + rng.normal(size=dim) * 0.3)
            X = np.array(X)
    if g == 0:
        X[0] = 0.0                                                            # the unedited grasp, for reference
        if a.init:
            X[1] = mean                                                       # and the starting point
    X = np.clip(X, -4, 4)
    phys = X * sig
    th = np.zeros((lam, 6 + nf)); th[:, :dim] = phys
    fit, detail, _ = evaluate(th)
    order = np.argsort(-fit)
    if fit[order[0]] > best['fit']:
        best = dict(fit=float(fit[order[0]]), gen=g, theta=th[order[0]].round(5).tolist(), detail=detail[order[0]])
    if a.algo == 'cmaes':
        sel = X[order[:mu]]; old = mean.copy(); mean = (wts[:, None] * sel).sum(0)
        invsq = evecs @ np.diag(1 / np.sqrt(evals)) @ evecs.T
        ps = (1 - cs) * ps + np.sqrt(cs * (2 - cs) * mueff) * invsq @ (mean - old) / sigma
        hsig = np.linalg.norm(ps) / np.sqrt(1 - (1 - cs) ** (2 * (g + 1))) / chiN < 1.4 + 2 / (dim + 1)
        pc = (1 - cc) * pc + hsig * np.sqrt(cc * (2 - cc) * mueff) * (mean - old) / sigma
        art = (sel - old) / sigma
        C = (1 - c1 - cmu) * C + c1 * (np.outer(pc, pc) + (1 - hsig) * cc * (2 - cc) * C) + cmu * (art.T * wts) @ art
        sigma *= np.exp((cs / damps) * (np.linalg.norm(ps) / chiN - 1))
    else:
        archive += [(float(fit[i]), X[i]) for i in range(lam)]
        archive = sorted(archive, key=lambda x: -x[0])[:64]
    rec = dict(gen=g, best=round(float(fit[order[0]]), 4), mean=round(float(fit.mean()), 4), unedited=round(float(fit[0]), 4) if g == 0 else None,
               sigma=round(float(sigma), 3), seconds=round(time.time() - t0, 1), top=[detail[i] for i in order[:3]])
    log['generations'].append(rec); log['best'] = best
    json.dump(log, open(a.out, 'w'), indent=1)
    print(json.dumps({k: rec[k] for k in ('gen', 'best', 'mean', 'unedited', 'sigma', 'seconds')}), 'best so far', round(best['fit'], 4), flush=True)

if a.bake and best.get('theta') is not None:                                   # write the best edit into the reference
    th = np.array(best['theta']); cols = {}
    wp_ = np.array(t.column(f'robot_{side}_wrist_position')[0].as_py(), float).reshape(T, 3)
    wq = np.array(t.column(f'robot_{side}_wrist_wxyz')[0].as_py(), float).reshape(T, 4)
    fj = np.array(t.column(f'robot_{side}_finger_joints')[0].as_py(), float).reshape(T, -1)
    for f in range(T):
        w = weight(f)
        if w <= 0:
            continue
        wp_[f] += R_obj[f].apply(th[:3]) * w
        rq = np.array(wp.quat_rpy(*(float(x) * w for x in th[3:6])))           # xyzw, the action's own rpy convention
        q = R.from_quat(wq[f][[1, 2, 3, 0]]) * R.from_quat(rq); wq[f] = q.as_quat()[[3, 0, 1, 2]]
        if fj.shape[1] == nf:
            fj[f] += th[6:6 + nf] * w
    for c, v in ((f'robot_{side}_wrist_position', wp_), (f'robot_{side}_wrist_wxyz', wq), (f'robot_{side}_finger_joints', fj)):
        t = t.set_column(t.column_names.index(c), c, pa.array([v.tolist()], type=t.schema.field(c).type))
    os.makedirs(os.path.dirname(os.path.abspath(a.bake)), exist_ok=True); pq.write_table(t, a.bake)
    log['baked'] = a.bake; json.dump(log, open(a.out, 'w'), indent=1); print('baked ->', a.bake, flush=True)
