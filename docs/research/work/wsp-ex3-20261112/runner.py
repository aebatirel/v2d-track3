"""Headless runner for NVIDIA's CoRL exercise 3 (flask handover), recording full traces.

Loads the exercise's simulation.py / policy.py from a directory given as an argument (third-party code; the package
__init__ needs IPython and is skipped). The policy is the exercise's own numpy forward pass with weights from any
actor npz of the same format, so an edit lives entirely in the npz.

The loop is the same as Simulation.run (reset, then policy -> step, threshold check after every step, BLAS limited
to one thread) except that it takes a start frame and a delay, records traces, and can keep going after the first
threshold failure for diagnosis (the success flag always uses the first failure).

Usage (one rollout):
  python -I runner.py WORKSHOP_DIR ACTOR_NPZ OUT_NPZ [--frame F] [--delay D] [--continue N] [--label TEXT]
Library: run_one(workshop, actor, frame, delay, continue_after_fail, record) -> dict
"""
import argparse, importlib.util, json, sys, time, types
import numpy as np

_MODS = {}


def load_workshop(d):
    if d in _MODS:
        return _MODS[d]
    pkg = types.ModuleType('chord_workshop'); pkg.__path__ = [d]; sys.modules['chord_workshop'] = pkg
    out = []
    for name in ('simulation', 'policy'):
        spec = importlib.util.spec_from_file_location(f'chord_workshop.{name}', f'{d}/{name}.py')
        m = importlib.util.module_from_spec(spec); sys.modules[spec.name] = m; spec.loader.exec_module(m); out.append(m)
    _MODS[d] = tuple(out)
    return _MODS[d]


def make_policy(polmod, actor_npz):
    p = object.__new__(polmod.Policy)
    with np.load(actor_npz, allow_pickle=False) as data:
        p.weights = {k: data[k] for k in data.files}
    return p


class ContactProbe:
    """Hand-object contact normal forces per side, read from the native MuJoCo data after each control step."""
    def __init__(self, sim):
        import mujoco
        self.mj = mujoco
        m = sim.solver.mj_model
        names = [mujoco.mj_id2name(m, mujoco.mjtObj.mjOBJ_BODY, i) or '' for i in range(m.nbody)]
        self.obj = [i for i, n in enumerate(names) if 'obj_' in n and n.endswith('object')]
        assert len(self.obj) == 1, names
        self.obj = self.obj[0]
        self.side = np.full(m.nbody, -1)
        for i, n in enumerate(names):
            if 'right_' in n or n.endswith('_R'):
                self.side[i] = 0
            elif 'left_' in n or n.endswith('_L'):
                self.side[i] = 1
        self.support = [i for i, n in enumerate(names) if n.endswith('support')]

    def read(self, sim):
        m, d = sim.solver.mj_model, sim.solver.mj_data
        force = np.zeros(3); count = np.zeros(3, int)   # right, left, support/other
        f6 = np.zeros(6)
        for k in range(d.ncon):
            c = d.contact[k]
            b1, b2 = m.geom_bodyid[c.geom1], m.geom_bodyid[c.geom2]
            if self.obj not in (b1, b2):
                continue
            other = b2 if b1 == self.obj else b1
            self.mj.mj_contactForce(m, d, k, f6)
            s = self.side[other] if self.side[other] >= 0 else 2
            force[s] += abs(f6[0]); count[s] += 1
        return force, count


def run_one(workshop, actor, frame=0, delay=0, continue_after_fail=0, record=True):
    from threadpoolctl import threadpool_limits
    simmod, polmod = load_workshop(workshop)
    policy = make_policy(polmod, actor)
    with threadpool_limits(limits=1, user_api='blas'):
        sim = simmod.Simulation(delay_steps=delay)
        sim._ensure_solver()
        obs = sim.reset(frame=frame)
        probe = ContactProbe(sim) if record else None
        count = sim.num_frames - 1 - frame
        T = dict(obs=[], act=[], target=[], qpos=[sim.qpos.copy()], qvel=[sim.qvel.copy()], frames=[sim.frame],
                 err=[sim.errors()], cforce=[], ccount=[])
        t0 = time.perf_counter(); fail_frame = -1; reason = ''; extra = 0
        for i in range(count):
            action = policy(obs)
            if not np.isfinite(action).all():   # e.g. a network with a negative batch-norm variance
                fail_frame = sim.frame; reason = 'non-finite action from the policy'
                break
            if record:
                T['obs'].append(obs.copy()); T['act'].append(action.copy())
            obs = sim.step(action)
            pos, ang, wrist = sim.errors()
            T['frames'].append(sim.frame); T['err'].append((pos, ang, wrist))
            if record:
                T['target'].append(sim.target.copy()); T['qpos'].append(sim.qpos.copy()); T['qvel'].append(sim.qvel.copy())
                f, c = probe.read(sim); T['cforce'].append(f); T['ccount'].append(c)
            if not np.isfinite(sim.qpos).all():
                if fail_frame < 0:
                    fail_frame = sim.frame; reason = 'non-finite simulation state'
                break
            if fail_frame < 0 and (pos > .1 or ang > .5 or wrist > .15):
                fail_frame = sim.frame
                reason = f'tracking threshold at {sim.frame/20:.2f}s (object {pos:.3f}m, {ang:.3f}rad; wrist {wrist:.3f}m)'
            if fail_frame >= 0:
                extra += 1
                if extra > continue_after_fail:
                    break
        elapsed = time.perf_counter() - t0
    err = np.asarray(T['err'])
    res = dict(success=fail_frame < 0, fail_frame=int(fail_frame), reason=reason or 'reference completed',
               start_frame=frame, delay=delay, last_frame=int(T['frames'][-1]), compute_s=round(elapsed, 2),
               max_obj_err_before_fail=float(err[:(len(err) if fail_frame < 0 else len(err) - extra + 1), 0].max()),
               actor=str(actor))
    if record:
        res['trace'] = {k: np.asarray(v) for k, v in T.items()}
    return res


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('workshop'); ap.add_argument('actor'); ap.add_argument('out')
    ap.add_argument('--frame', type=int, default=0); ap.add_argument('--delay', type=int, default=0)
    ap.add_argument('--continue', dest='cont', type=int, default=0); ap.add_argument('--label', default='')
    a = ap.parse_args()
    r = run_one(a.workshop, a.actor, a.frame, a.delay, a.cont, record=True)
    tr = r.pop('trace')
    np.savez_compressed(a.out, **tr, meta=json.dumps(r))
    r['label'] = a.label; r['out'] = a.out
    e = tr['err']
    for fr in (100, 200, 300, 320, 340, 352, 400, 500, 600, 700, 800, 900, 1000, 1022):
        idx = np.flatnonzero(tr['frames'] == fr)
        if len(idx):
            r[f'err@{fr}'] = [round(float(x), 4) for x in e[idx[0]]]
    print(json.dumps(r))


if __name__ == '__main__':
    main()
