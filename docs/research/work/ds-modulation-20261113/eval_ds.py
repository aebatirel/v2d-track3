"""Phase-2 evaluation of DS obstacle modulation (PREREG.md in this folder). Written in phase 1, NOT run on any episode in
phase 1. GT-free: reads only our references, our meshes (library_v3) and the simulator's own geometry; mocap is never
opened. Every number it prints is a property of our reference in the simulator's collision geometry.

Subcommands (run in this order by run_phase2.sh; FlashCHORD venv, from the flash_chord directory, FC set):
  stage    SRC_PARQUET ASSETS OUT_TREE      copy a reference into OUT_TREE with its object mesh/URDF paths pointing at
                                            ASSETS (pipeline/make_assets.py output of OUR library); every other column is
                                            checked byte-identical
  metric   ARM_PARQUET PHASES_JSON OUT.json per frame and hand, the deepest penetration (MuJoCo, the simulator's own convex
                                            pieces, geom margin 0, scene at the reference frame, no step) into each object
                                            and the other hand, plus object-object contacts
  summary  OUT_DIR EPS...                   pooled metrics, guards and the pre-registered verdict (PREREG section 6)
  bystander TRACE.npz ARM_PARQUET PHASES_JSON   optional physics check (descriptive): zero-action replay displacement
                                            of objects while no hand holds them
"""
import json, os, sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, '..', '..', '..', '..'))
PEN = 0.002            # m: a frame-hand pair "collides" with an object when it is more than 2 mm inside (PREREG 5.1)
ARMS = ('orig', 'clear', 'ds')


# ----------------------------------------------------------------------------- stage
def stage(src, assets, out_tree):
    import shutil, glob, pyarrow as pa, pyarrow.parquet as pq
    tree = os.path.abspath(src).split('/processed/')[0]; sub = os.path.abspath(src).split('/processed/')[1]
    shutil.copytree(f'{tree}/reconstructed_stage', f'{out_tree}/reconstructed_stage', dirs_exist_ok=True)
    t = pq.read_table(src); names = t.column('object_body_names')[0].as_py(); new = t
    for c, fmt in (('object_mesh_paths', '{a}/mesh/{n}/{n}.glb'), ('object_urdf_paths', '{a}/urdf/{n}_rigid.urdf')):
        v = [fmt.format(a=os.path.abspath(assets), n=n) for n in names]
        assert all(os.path.isfile(x) for x in v), v
        new = new.set_column(new.schema.get_field_index(c), new.schema.field(c), pa.array([v], type=t.schema.field(c).type))
    dst = f'{out_tree}/processed/{sub}'; os.makedirs(os.path.dirname(dst), exist_ok=True); pq.write_table(new, dst)
    back = pq.read_table(dst)
    assert all(back.column(c).equals(t.column(c)) for c in t.column_names if c not in ('object_mesh_paths', 'object_urdf_paths'))
    print(dst)


# ----------------------------------------------------------------------------- metric (FlashCHORD scene, CPU MuJoCo)
def owner_map(labels, names, ngeom, g2s, sb):
    """Per MuJoCo geom: 'left' / 'right' (robot), an object name, or 'env' (table, ground). An object body's name is the
    longest object name contained in its label (white_pot vs white_pot_lid)."""
    own = []
    for g in range(ngeom):
        sh = g2s[g]
        if sh < 0 or sb[sh] < 0:
            own.append('env'); continue
        lab = labels[sb[sh]]; last = lab.split('/')[-1]
        if last.startswith('left_') or last.startswith('right_'):
            own.append(last.split('_')[0]); continue
        hits = [n for n in names if n in lab]
        own.append(max(hits, key=len) if hits else 'env')
    return own


def metric(arm_parquet, phases_json, out_json):
    import mujoco, warp as wp, pyarrow.parquet as pq
    from hydra import compose, initialize_config_dir
    from flash_chord.configuration import instantiate_typed
    from flash_chord.embodiments.base import Embodiment
    from flash_chord.envs.rl import RLEnv, RLEnvConfig
    from flash_chord.scene.collision import CollisionPolicy
    from flash_chord.scene.setup import setup_scene
    fc = os.environ['FC']
    with initialize_config_dir(version_base='1.3', config_dir=f'{fc}/src/flash_chord/configs'):
        cfg = compose(config_name='train_flash_sac', overrides=['experiment=sharpa_flash_sac', f"task.parquet='{arm_parquet}'"])
    ec = instantiate_typed(cfg.env, RLEnvConfig)
    names = pq.read_table(arm_parquet, columns=['object_body_names']).column('object_body_names')[0].as_py()
    with wp.ScopedDevice('cpu'):
        st = setup_scene(parquet=arm_parquet, control_fps=ec.sim.fps, motion_speed=1.0,
                         embodiment=instantiate_typed(cfg.embodiment, Embodiment),
                         collision=instantiate_typed(cfg.collision, CollisionPolicy), world_count=1, include_support=True,
                         decompose_objects=True)
        env = RLEnv(st.scene, st.reference, config=ec); m = st.scene.model; sol = env.solver
        mm = sol.mj_model; mm.geom_margin[:] = 0.0; md = mujoco.MjData(mm)          # contacts only when penetrating
        if hasattr(mm, 'geom_gap'):
            mm.geom_gap[:] = 0.0
        g2s = sol.mjc_geom_to_newton_shape.numpy(); g2s = g2s[0] if g2s.ndim == 2 else g2s
        labels = list(getattr(m, 'body_label', None) or getattr(m, 'body_key', []))
        own = owner_map(labels, names, mm.ngeom, g2s, m.shape_body.numpy())
        assert all(n in own for n in names), ('object without geoms', names)
        state = m.state(); T = int(st.reference.num_frames)
        rows = []
        for t in range(T):
            env.reset(frame_id=t)
            state.joint_q.assign(env.state_0.joint_q.numpy().astype(np.float32))
            sol._update_mjc_data(md, m, state); mujoco.mj_kinematics(mm, md); mujoco.mj_collision(mm, md)
            r = {s: {} for s in ('left', 'right')}; oo = {}; n = md.ncon
            G, D = (md.contact.geom[:n], md.contact.dist[:n]) if n else ([], [])     # as pipeline/contact_retarget.MjPen
            for (g0, g1), dist in zip(G, D):
                if dist >= 0:
                    continue
                a, b = own[g0], own[g1]; dep = float(-dist)
                if a == b:
                    continue
                for x, y in ((a, b), (b, a)):
                    if x in r:
                        key = 'hand' if y in ('left', 'right') else y
                        r[x][key] = max(r[x].get(key, 0.0), dep)
                if a in names and b in names:
                    k = '|'.join(sorted((a, b))); oo[k] = max(oo.get(k, 0.0), dep)
            rows.append(dict(hands=r, objects=oo))
    json.dump(dict(parquet=os.path.abspath(arm_parquet), frames=T, objects=names, rows=rows), open(out_json, 'w'))


# ----------------------------------------------------------------------------- summary and verdict
def classify(M, ph):
    """Per (frame, hand): deepest non-target object penetration, target penetration, hand-hand; per frame the held-object
    vs other-object overlap in transport frames. Labels come from the ORIGINAL reference (same frames for every arm)."""
    names = M['objects']; T = M['frames']; out = {k: [] for k in ('nt', 'tg', 'hh', 'win', 'oo_x')}
    for t in range(T):
        for s in ('left', 'right'):
            tgt = ph[s]['target'][t]; tname = names[tgt] if tgt >= 0 else None
            d = M['rows'][t]['hands'][s]
            out['nt'].append(max([v for k, v in d.items() if k in names and k != tname] + [0.0]))
            out['tg'].append(d.get(tname, 0.0) if tname else 0.0)
            out['hh'].append(d.get('hand', 0.0)); out['win'].append(ph[s]['role'][t] in 'AX')
            if ph[s]['role'][t] == 'X':
                out['oo_x'].append(max([v for k, v in M['rows'][t]['objects'].items() if tname in k.split('|')] + [0.0]))
    return {k: np.array(v) for k, v in out.items()}


def wrist_dev(arm_parquet, orig_parquet):
    import pyarrow.parquet as pq
    a, o = pq.read_table(arm_parquet), pq.read_table(orig_parquet); T = None; dev = []
    for s in ('left', 'right'):
        wa = np.array(a.column(f'robot_{s}_wrist_position')[0].as_py()).reshape(-1, 3)
        wo = np.array(o.column(f'robot_{s}_wrist_position')[0].as_py()).reshape(-1, 3); dev.append(np.linalg.norm(wa - wo, axis=1))
    B = len(a.column('object_body_names')[0].as_py())
    pa_ = np.array(a.column('object_body_position')[0].as_py()).reshape(-1, B, 3)
    po_ = np.array(o.column('object_body_position')[0].as_py()).reshape(-1, B, 3)
    return np.stack(dev, 1).reshape(-1), np.linalg.norm(pa_ - po_, axis=2).max(1)   # (T*2,) frame-major like classify


def verdict(S):
    """S: per-arm pooled numbers. Returns (verdict, reasons). Rules of PREREG section 6, fixed before any phase-2 run."""
    Po, Pc, Pd = S['orig']['P'], S['clear']['P'], S['ds']['P']
    if Po < 10:
        return 'NOT_APPLICABLE', [f'original has {Po} non-target collision frame-hand pairs (< 10): nothing to remove']
    Rd, Rc = 1 - Pd / Po, 1 - Pc / Po; Dd, Dc = S['ds']['D95_cm'], S['clear']['D95_cm']
    guards = []
    for k in ('TG', 'HH', 'OOX'):
        lim = S['orig'][k] + max(5, 0.1 * S['orig'][k])
        if S['ds'][k] > lim:
            guards.append(f'{k} {S["ds"][k]} > {lim:.1f}')
    if not S['ds']['ends_ok']:
        guards.append('a window end or a frame outside the windows changed')
    why = [f'R_ds {Rd:.3f}, R_clear {Rc:.3f}, D95_ds {Dd:.2f} cm, D95_clear {Dc:.2f} cm'] + guards
    if Rd < 0.2 or (Rd < Rc and Dd >= Dc) or guards:
        return 'FAIL', why
    if Rd >= 0.5 and Dd < Dc and Rd >= Rc - 0.10:
        return 'PASS', why
    return 'INCONCLUSIVE', why


def summary(out_dir, eps):
    S = {a: dict(P=0, P_win=0, depth_mm_frames=0.0, TG=0, HH=0, OOX=0, dev=[], objdev=[], ends_ok=True) for a in ARMS}
    per = {}
    for e in eps:
        ph = json.load(open(f'{out_dir}/ep{e}/phases.json')); orig = f'{out_dir}/ep{e}/orig.parquet'
        per[e] = {}
        for a in ARMS:
            C = classify(json.load(open(f'{out_dir}/ep{e}/metric_{a}.json')), ph)
            dev, odev = wrist_dev(f'{out_dir}/ep{e}/{a}.parquet', orig)
            hit = C['nt'] > PEN
            d = dict(P=int(hit.sum()), P_win=int((hit & C['win']).sum()), depth_mm_frames=float(1000 * C['nt'][hit].sum()),
                     TG=int((C['tg'] > PEN).sum()), HH=int((C['hh'] > PEN).sum()), OOX=int((C['oo_x'] > PEN).sum()),
                     D95_cm=float(np.percentile(dev, 95) * 100), Dmax_cm=float(dev.max() * 100),
                     objdev_max_cm=float(odev.max() * 100))
            per[e][a] = d
            for k in ('P', 'P_win', 'depth_mm_frames', 'TG', 'HH', 'OOX'):
                S[a][k] += d[k]
            S[a]['dev'].append(dev); S[a]['objdev'].append(odev)
        rep = json.load(open(f'{out_dir}/ep{e}/ds_report.json'))
        S['ds']['ends_ok'] &= bool(ends_unchanged(f'{out_dir}/ep{e}/ds.parquet', orig, ph))
        per[e]['ds']['stalled_windows'] = sum(w['stalled'] for v in rep['hands'].values() for w in v)
        per[e]['ds']['windows'] = sum(len(v) for v in rep['hands'].values())
    for a in ARMS:
        dev = np.concatenate(S[a].pop('dev')); od = np.concatenate(S[a].pop('objdev'))
        S[a].update(D95_cm=float(np.percentile(dev, 95) * 100), Dmax_cm=float(dev.max() * 100),
                    objdev_p95_cm=float(np.percentile(od, 95) * 100), objdev_max_cm=float(od.max() * 100))
    v, why = verdict(S)
    res = dict(verdict=v, reasons=why, pooled=S, per_episode=per, episodes=list(eps), pen_threshold_m=PEN)
    json.dump(res, open(f'{out_dir}/summary.json', 'w'), indent=1); print(json.dumps(dict(verdict=v, reasons=why), indent=1))


def ends_unchanged(ds_parquet, orig_parquet, ph):
    """Guard: frames outside the DS windows, and each window's first and last frame, are bit-identical to the original."""
    import pyarrow.parquet as pq
    a, o = pq.read_table(ds_parquet), pq.read_table(orig_parquet)
    for s in ('left', 'right'):
        wa = np.array(a.column(f'robot_{s}_wrist_position')[0].as_py()).reshape(-1, 3)
        wo = np.array(o.column(f'robot_{s}_wrist_position')[0].as_py()).reshape(-1, 3)
        role = np.array(list(ph[s]['role'])); win = np.isin(role, ['A', 'X'])
        if not np.array_equal(wa[~win], wo[~win]):
            return False
        m = np.concatenate([[0], win.astype(int), [0]]); d = np.diff(m)
        for a0, b0 in zip(np.nonzero(d == 1)[0], np.nonzero(d == -1)[0] - 1):
            if not (np.array_equal(wa[a0], wo[a0]) and np.array_equal(wa[b0], wo[b0])):
                return False
    return True


# ----------------------------------------------------------------------------- optional physics check
def bystander(trace_npz, arm_parquet, phases_json):
    """Zero-action replay (tools/trace_rollout.py zero): per object, the largest displacement (cm) of its simulated pose
    from its reference pose over frames where no hand holds it and it has not yet been held (a bystander knocked)."""
    import pyarrow.parquet as pq
    d = np.load(trace_npz); L = [str(x) for x in d['labels']]; q = d['q']; fr = d['frame']
    t = pq.read_table(arm_parquet); names = t.column('object_body_names')[0].as_py(); B = len(names)
    OP = np.array(t.column('object_body_position')[0].as_py()).reshape(-1, B, 3); ph = json.load(open(phases_json))
    out = {}
    longest = [max([x for x in names if x in l], key=len, default=None) for l in L]   # white_pot vs white_pot_lid
    for k, n in enumerate(names):
        bi = longest.index(n)
        held = np.zeros(len(OP), bool)
        for s in ('left', 'right'):
            held |= np.array(ph[s]['held']) == k
        first = int(np.argmax(held)) if held.any() else len(OP)
        rows = [i for i, f in enumerate(fr) if f < first]
        out[n] = round(float(max([np.linalg.norm(q[i, bi, :3] - OP[fr[i], k]) for i in rows] + [0.0]) * 100), 2)
    print(json.dumps(out))


if __name__ == '__main__':
    cmd, args = sys.argv[1], sys.argv[2:]
    {'stage': stage, 'metric': metric, 'summary': lambda d, *e: summary(d, [int(x) for x in e]),
     'bystander': bystander}[cmd](*args)
