"""Contact-budget gate, part 1 (PREREG F-I4.17.1; INTERLOCK.md section 20.14; board slot round 3). File name: F-I4.17.6
step 1 says gmg/contactgate.py; the concurrent collision-carve F-I5.16 build plans a new gmg/contactgate.py of its own, so
this module is contactgate_fi4.py to keep the two from colliding (no change in substance).

Plain MuJoCo (our venv's mujoco) counts of the contacts (ncon) and constraint rows (nefc) of a pair of plate bodies on a
table, with the solver options of the training / evaluator configuration sim=rl, against its per-world limits.

  sim_rl()                       the sim=rl values, read from the committed copy docs/research/work/15-verify/
                                 cfg_sim_rl.yaml (sha256 checked against PREREG F-I4.17.1; a differing value is
                                 reported in 'mismatch')
  count_xml(...)                 the P1 pre-check settle scene of simphys.settle_xml (table plane, both boards free,
                                 0.3 kg uniform-solid props, mesh geoms condim 3, friction 0.5, gravity along -n) with
                                 the sim=rl options: timestep 1 / (fps x substeps), Newton, pyramidal, implicitfast,
                                 iterations / ls_iterations, impratio, <size njmax nconmax>
  count_copy(m, d, steps)        per physics step d.ncon, d.nefc and the CONTACTFULL / CNSTRFULL warning counters;
                                 the maxima, their steps and the contacts by class (board-board, board-table) at the
                                 step of max nefc
  count_scene(...)               16 jittered copies (simphys.jitters, seed 1, guest jittered: as simphys.settle), 2.0 s
  scenes_bundle / scenes_synth   S1 = the median assembled frame (asm[len // 2], the pre-check frame), S2 = the first
                                 assembled frame; world poses and table as simphys.pair_physics; for a synthetic pair
                                 (no table in the bundle): host frame = world, table normal -d, 1 mm beyond the pair's
                                 lowest piece vertex along d, gravity along d (d = the run's unit insertion direction)
  lowered(scene, sets)           the pair moved rigidly along -n so its lowest piece vertex is 1 mm above the table
                                 (determined-wright's diagnostic pose; report only)
  control_hulls(body)            one F-I4.2 rectangle-frame box per board (L x W x t about c0; axes a_L, a_W, a_T)
  gate(scenes, sets)             PASS iff no copy of any scene overflows with the delivered pieces (max ncon > 256,
                                 max nefc > 512, or a CONTACTFULL / CNSTRFULL warning) AND max nefc (delivered) <= 2.0 x
                                 max nefc (control); default and every other set reported
  count_replay(...)              the P3 replay scene (simphys.replay_xml, its own options; no table) with the same
                                 counters (report only)
Plain MuJoCo does not stop at njmax / nconmax (it grows its arena; [M] mujoco 3.17.0), so the limits are applied to the
counts. nconmax is per world here (MuJoCo-Warp pools it over worlds: the stricter reading, F-I4.17.1).
Part 2 (determined-wright's budget.py, max nefc per world <= 380 in the full eval scene) is not run by this module.
GT-free: pieces and poses are our own (tracks, picks); no scan, mocap or parquet pose is read.
"""
from __future__ import annotations

import hashlib
import os
import time

import numpy as np
from scipy.spatial.transform import Rotation as Rot

from gmg import guard
from gmg import simphys as PH

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, '..', '..', '..', '..'))
SIM_RL_PATH = os.path.join(REPO, 'docs', 'research', 'work', '15-verify', 'cfg_sim_rl.yaml')
SIM_RL_SHA = '695536b798ff5f7b1d391e3a6932288e23329c026f27cd364f77230d703f4b66'
SIM_RL_PREREG = dict(fps=20.0, substeps=5, solver='newton', integrator='implicitfast', cone='pyramidal', njmax=512,
                     nconmax=256, impratio=20.0, iterations=100, ls_iterations=50, use_mujoco_contacts=True)

C = dict(
    copies=(16, 'generic:F-I1.14 16 jittered copies (simphys.jitters, seed 1, as the settle)'),
    secs=(2.0, 'informed:F-I4.17.8 2.0 s per copy (the settle time, F-I1.14)'),
    ratio_max=(2.0, 'informed:F-I4.17.8 delivered max nefc <= 2.0 x one-box-per-board control (decision 2)'),
    lower_gap_m=(0.001, 'informed:F-I4.17.8 1 mm table gap of the synthetic scene and the lowered diagnostic '
                        '(determined-wright)'),
    mass_kg=(0.3, 'informed:F-I1.14 0.3 kg placeholder mass per board (as the settle)'),
)


def k_(name):
    v, o = C[name]
    if o.startswith('generic'):
        guard.constant(f'cg.{name}', v, o)
    return v


def sim_rl(path=None):
    """The sim=rl values from the committed copy (simple 'key: value' YAML), its sha256, and any value that differs
    from PREREG F-I4.17.1 (mismatch)."""
    path = path or SIM_RL_PATH
    with open(path, 'rb') as fh:
        raw = fh.read()
    vals = {}
    for line in raw.decode().splitlines():
        if ':' not in line or line.strip().startswith('#'):
            continue
        k, v = (x.strip() for x in line.split(':', 1))
        if k.startswith('_'):
            vals[k] = v
            continue
        if v.lower() in ('true', 'false'):
            vals[k] = v.lower() == 'true'
        else:
            try:
                vals[k] = int(v)
            except ValueError:
                try:
                    vals[k] = float(v)
                except ValueError:
                    vals[k] = v
    sha = hashlib.sha256(raw).hexdigest()
    mism = {k: (vals.get(k), v) for k, v in SIM_RL_PREREG.items() if vals.get(k) != v}
    return dict(path=os.path.relpath(path, REPO), sha256=sha, sha_matches_prereg=bool(sha == SIM_RL_SHA),
                values={k: v for k, v in vals.items() if not k.startswith('_')}, mismatch=mism or None,
                source_note='committed copy of FlashCHORD configs/sim/rl.yaml (the FlashCHORD source is not on this '
                            'machine)')


def options(cfg=None):
    cfg = cfg or sim_rl()
    v = cfg['values']
    return dict(timestep=1.0 / (float(v['fps']) * int(v['substeps'])), solver='Newton', cone=v['cone'].lower(),
                integrator=v['integrator'].lower(), iterations=int(v['iterations']),
                ls_iterations=int(v['ls_iterations']), impratio=float(v['impratio']), njmax=int(v['njmax']),
                nconmax=int(v['nconmax']))


def count_xml(host, guest, T_wh, T_wg, n_table, d_table, hp, gp, opt):
    """simphys.settle_xml with the sim=rl options and size (same bodies, geoms, plane, gravity)."""
    g = -9.81 * np.asarray(n_table, float)
    n = np.asarray(n_table, float)
    p0 = -d_table * n
    z = n
    x = np.cross([0, 1.0, 0], z) if abs(z[1]) < 0.9 else np.cross([1.0, 0, 0], z)
    x /= np.linalg.norm(x)
    y = np.cross(z, x)
    qp = PH._quat(np.stack([x, y, z], 1))

    def body(name, hulls, T, props, tag):
        q = PH._quat(T[:3, :3])
        t = T[:3, 3]
        return (f'<body name="{name}" pos="{t[0]:.6f} {t[1]:.6f} {t[2]:.6f}" quat="{q[0]:.6f} {q[1]:.6f} {q[2]:.6f} '
                f'{q[3]:.6f}"><freejoint/>{PH._inertial(props)}{PH._geoms(hulls, tag)}</body>')
    return f'''<mujoco><option timestep="{opt['timestep']:.6g}" gravity="{g[0]:.5f} {g[1]:.5f} {g[2]:.5f}" solver="{opt['solver']}" cone="{opt['cone']}" integrator="{opt['integrator']}" iterations="{opt['iterations']}" ls_iterations="{opt['ls_iterations']}" impratio="{opt['impratio']:.6g}"/>
<size njmax="{opt['njmax']}" nconmax="{opt['nconmax']}"/>
<asset>{PH._mesh_assets(host, 'a')}{PH._mesh_assets(guest, 'b')}</asset><worldbody>
<geom name="table" type="plane" size="2 2 0.1" pos="{p0[0]:.6f} {p0[1]:.6f} {p0[2]:.6f}" quat="{qp[0]:.6f} {qp[1]:.6f} {qp[2]:.6f} {qp[3]:.6f}" friction="0.5"/>
{body('H', host, T_wh, hp, 'a')}{body('G', guest, T_wg, gp, 'b')}
</worldbody></mujoco>'''


def _classes(m, d):
    nc = int(d.ncon)
    if nc == 0:
        return dict(board_board=0, board_table=0, other=0)
    g1 = np.asarray(d.contact.geom1[:nc])
    g2 = np.asarray(d.contact.geom2[:nc])
    b1, b2 = m.geom_bodyid[g1], m.geom_bodyid[g2]
    tab = (b1 == 0) | (b2 == 0)
    bb = (~tab) & (b1 != b2)
    return dict(board_board=int(bb.sum()), board_table=int(tab.sum()), other=int(nc - bb.sum() - tab.sum()))


def count_copy(m, d, steps, opt):
    """Steps the model, recording ncon / nefc after every mj_step (the counts of that step's collision pass)."""
    import mujoco
    W_C, W_E = int(mujoco.mjtWarning.mjWARN_CONTACTFULL), int(mujoco.mjtWarning.mjWARN_CNSTRFULL)
    mx_c = mx_e = 0
    st_c = st_e = -1
    cls = None
    nc_all, ne_all = [], []
    nan = False
    for k in range(steps):
        mujoco.mj_step(m, d)
        if not np.all(np.isfinite(d.qpos)):
            nan = True
            break
        nc, ne = int(d.ncon), int(d.nefc)
        nc_all.append(nc)
        ne_all.append(ne)
        if ne > mx_e:
            mx_e, st_e, cls = ne, k, _classes(m, d)
        if nc > mx_c:
            mx_c, st_c = nc, k
    wc, we = int(d.warning[W_C].number), int(d.warning[W_E].number)
    over = bool(mx_c > opt['nconmax'] or mx_e > opt['njmax'] or wc > 0 or we > 0)
    return dict(max_ncon=mx_c, step_max_ncon=st_c, max_nefc=mx_e, step_max_nefc=st_e, classes_at_max_nefc=cls,
                median_ncon=float(np.median(nc_all)) if nc_all else None,
                median_nefc=float(np.median(ne_all)) if ne_all else None, warn_contactfull=wc, warn_cnstrfull=we,
                nan=nan, steps=len(nc_all), overflow=over)


def count_scene(host, guest, T_wh, T_wg, table, hp, gp, opt, copies=None, secs=None):
    """COPIES jittered copies of one scene (the guest jittered as simphys.settle; the same draws for every set)."""
    import mujoco
    n_t, d_t = table
    J = PH.jitters(copies or k_('copies'), seed=1)
    steps = int(round((secs or k_('secs')) / opt['timestep']))
    rows = []
    for j in J:
        Jm = np.eye(4)
        Jm[:3, :3] = Rot.from_rotvec(j[3:]).as_matrix()
        Jm[:3, 3] = j[:3]
        m = mujoco.MjModel.from_xml_string(count_xml(host, guest, T_wh, T_wg @ Jm, n_t, d_t, hp, gp, opt))
        d = mujoco.MjData(m)
        mujoco.mj_forward(m, d)
        r0 = dict(ncon0=int(d.ncon), nefc0=int(d.nefc))
        rows.append(dict(count_copy(m, d, steps, opt), **r0))
    return _agg(rows)


def _agg(rows):
    me = [r['max_nefc'] for r in rows]
    mc = [r['max_ncon'] for r in rows]
    return dict(copies=len(rows), max_nefc=int(max(me)), median_max_nefc=float(np.median(me)), max_ncon=int(max(mc)),
                median_max_ncon=float(np.median(mc)), overflow_copies=int(sum(r['overflow'] for r in rows)),
                nan_copies=int(sum(r['nan'] for r in rows)), per_copy=rows)


def control_hulls(body):
    """One F-I4.2 rectangle-frame box: L x W of the frame rectangle, thickness t, centred on c0 in the mid plane, axes
    a_L, a_W, a_T (the body record's axes / centre / half, which are the frame's)."""
    A = np.asarray(body['axes'], np.float64)
    c = np.asarray(body['centre'], np.float64)
    h = np.asarray(body['half'], np.float64)
    s = np.array([[x, y, z] for x in (-1, 1) for y in (-1, 1) for z in (-1, 1)], np.float64)
    return [c + (s * h) @ A]


def _tf(T, X):
    return np.asarray(X, np.float64) @ T[:3, :3].T + T[:3, 3]


def scenes_bundle(b, o, p, run, rels=None):
    """S1 (median assembled frame = the P1 pre-check frame of simphys.pair_physics) and S2 (first assembled frame):
    world poses of host o and guest p and the bundle's table (n, d) in the world frame."""
    T = int(b.meta['T'])
    from gmg import interlock as IL
    if rels is None:
        rels = {f: IL.rel_pose(b.poses, o, p, f) for f in range(T)}
    asm = [f for f in (run.assembled or run.build[-5:]) if f in rels] or [f for f in run.frames if f in rels][-5:]
    out = {}
    for name, f in (('S1', asm[len(asm) // 2]), ('S2', asm[0])):
        W0 = b.poses['world_T_cam'][f].astype(np.float64) @ b.poses[f'cam_T_{o}'][f].astype(np.float64)
        tb = b.meta['table']
        out[name] = dict(frame=int(f), T_wh=W0, T_wg=W0 @ rels[f], table=(np.asarray(tb['n'], np.float64),
                                                                         float(tb['d'])), table_kind='bundle')
    return out, asm


def scenes_synth(run, rels, sets):
    """Synthetic pair (no table in the bundle): host frame = world; for each scene a table with normal -d through the
    point 1 mm beyond the lowest piece vertex along d over every set (so all sets share the table), gravity along d."""
    asm = [f for f in (run.assembled or run.build[-5:]) if f in rels] or [f for f in run.frames if f in rels][-5:]
    dvec = np.asarray(run.d, np.float64)
    dvec = dvec / np.linalg.norm(dvec)
    out = {}
    for name, f in (('S1', asm[len(asm) // 2]), ('S2', asm[0])):
        Th, Tg = np.eye(4), np.asarray(rels[f], np.float64)
        smax = max(max(float((np.vstack(h) @ dvec).max()), float((_tf(Tg, np.vstack(g)) @ dvec).max()))
                   for h, g in sets.values())
        out[name] = dict(frame=int(f), T_wh=Th, T_wg=Tg, table=(-dvec, smax + k_('lower_gap_m')),
                         table_kind='synthetic (normal -d, 1 mm beyond the lowest vertex along d)')
    return out, asm


def lowered(sc, sets):
    """The scene with the pair moved rigidly along -n so that its lowest piece vertex (over every set) is 1 mm above
    the table (report only; determined-wright's lowered diagnostic)."""
    n, dd = sc['table']
    lo = min(min(float((_tf(sc['T_wh'], np.vstack(h)) @ n).min()), float((_tf(sc['T_wg'], np.vstack(g)) @ n).min()))
             for h, g in sets.values())
    shift = -(lo + dd) + k_('lower_gap_m')                 # height above the plane n.x + d = 0 becomes 1 mm
    S = np.eye(4)
    S[:3, 3] = shift * n
    return dict(sc, T_wh=S @ sc['T_wh'], T_wg=S @ sc['T_wg'], lowered_by_mm=round(-shift * 1e3, 3))


def gate(scenes, sets, props=None, copies=None, delivered='delivered', control='control', lower=False, log=None):
    """PREREG F-I4.17.1 part 1. SCENES = {name: dict(T_wh, T_wg, table, frame)}; SETS = {name: (host_hulls,
    guest_hulls)} with at least DELIVERED and CONTROL. Pass iff no copy of any scene overflows with DELIVERED and its
    max nefc (all scenes, copies) <= 2.0 x CONTROL's. LOWER: also the lowered diagnostic (report only)."""
    from gmg import simpieces as SP
    log = log or (lambda *a: None)
    cfg = sim_rl()
    opt = options(cfg)
    t0 = time.time()
    props = props or {k: (SP.props(h, k_('mass_kg')), SP.props(g, k_('mass_kg'))) for k, (h, g) in sets.items()}
    res = {}
    for sname, sc in scenes.items():
        for kname, (h, g) in sets.items():
            t = time.time()
            r = count_scene(h, g, sc['T_wh'], sc['T_wg'], sc['table'], props[kname][0], props[kname][1], opt,
                            copies=copies)
            r['sec'] = round(time.time() - t, 1)
            res.setdefault(kname, {})[sname] = r
            log(f'contact gate {sname} f{sc["frame"]} {kname}: max ncon {r["max_ncon"]} max nefc {r["max_nefc"]} '
                f'(median {r["median_max_nefc"]}) overflow {r["overflow_copies"]} / {r["copies"]} {r["sec"]} s')
    low = {}
    if lower:
        for sname, sc in scenes.items():
            sl = lowered(sc, sets)
            for kname, (h, g) in sets.items():
                r = count_scene(h, g, sl['T_wh'], sl['T_wg'], sl['table'], props[kname][0], props[kname][1], opt,
                                copies=copies)
                low.setdefault(kname, {})[sname] = dict({k: v for k, v in r.items() if k != 'per_copy'},
                                                        lowered_by_mm=sl['lowered_by_mm'])
                log(f'contact gate lowered {sname} {kname}: max nefc {r["max_nefc"]} overflow {r["overflow_copies"]}')
    summ = {k: dict(max_nefc=max(v[s]['max_nefc'] for s in v), max_ncon=max(v[s]['max_ncon'] for s in v),
                    overflow_copies=int(sum(v[s]['overflow_copies'] for s in v)),
                    by_scene={s: dict(max_nefc=v[s]['max_nefc'], max_ncon=v[s]['max_ncon'],
                                      median_max_nefc=v[s]['median_max_nefc'], overflow_copies=v[s]['overflow_copies'])
                              for s in v}) for k, v in res.items()}
    dl, ct = summ[delivered], summ[control]
    ratio = dl['max_nefc'] / ct['max_nefc'] if ct['max_nefc'] > 0 else float('inf')
    ok = bool(dl['overflow_copies'] == 0 and ratio <= k_('ratio_max'))
    return dict(rule='PREREG F-I4.17.1 part 1 (plain MuJoCo, sim=rl options and limits)', sim_rl=cfg, options=opt,
                delivered_set=delivered, control_set=control,
                mujoco_version=__import__('mujoco').__version__, ratio_max=k_('ratio_max'),
                scenes={s: dict(frame=sc['frame'], table_kind=sc.get('table_kind'),
                                table_n=np.round(sc['table'][0], 6).tolist(), table_d=round(float(sc['table'][1]), 6))
                        for s, sc in scenes.items()},
                pieces={k: [len(h), len(g)] for k, (h, g) in sets.items()}, summary=summ,
                ratio_delivered_to_control=round(ratio, 4), no_overflow_delivered=bool(dl['overflow_copies'] == 0),
                pass_=ok, per_set=res, lowered=low or None, sec=round(time.time() - t0, 1),
                note='overflow per copy := max ncon > nconmax or max nefc > njmax or a CONTACTFULL / CNSTRFULL warning; '
                     'plain MuJoCo does not stop at the limits. Part 2 (budget.py, <= 380 rows per world in the full '
                     'eval scene) is separate.')


def count_replay(host, guest, rels, frames, copies=None, guest_props=None):
    """The P3 replay scene (simphys.replay_xml, collide, its own options and time step; no table): per copy (the P3
    jitters, simphys.jitters seed 0) the max ncon / nefc over the replayed frames (report only)."""
    import mujoco
    J = PH.jitters(copies)
    xml = PH.replay_xml(host, guest, True, guest_props)
    rows = []
    for jit in J:
        m = mujoco.MjModel.from_xml_string(xml)
        d = mujoco.MjData(m)
        Jm = np.eye(4)
        Jm[:3, :3] = Rot.from_rotvec(jit[3:]).as_matrix()
        Jm[:3, 3] = jit[:3]
        T0 = rels[frames[0]] @ Jm
        d.qpos[:3] = T0[:3, 3]
        d.qpos[3:7] = PH._quat(T0[:3, :3])
        d.mocap_pos[0] = T0[:3, 3]
        d.mocap_quat[0] = PH._quat(T0[:3, :3])
        mujoco.mj_forward(m, d)
        mx_c = mx_e = 0
        nan = False
        for f in frames:
            Tf = rels[f] @ Jm
            d.mocap_pos[0] = Tf[:3, 3]
            d.mocap_quat[0] = PH._quat(Tf[:3, :3])
            for _ in range(PH.k_('sub')):
                mujoco.mj_step(m, d)
                mx_c, mx_e = max(mx_c, int(d.ncon)), max(mx_e, int(d.nefc))
            if not np.all(np.isfinite(d.qpos)):
                nan = True
                break
        rows.append(dict(max_ncon=mx_c, max_nefc=mx_e, nan=nan))
    return dict(copies=len(rows), max_nefc=int(max(r['max_nefc'] for r in rows)),
                median_max_nefc=float(np.median([r['max_nefc'] for r in rows])),
                max_ncon=int(max(r['max_ncon'] for r in rows)), nan_copies=int(sum(r['nan'] for r in rows)),
                frames=[int(frames[0]), int(frames[-1])], note='simphys.replay_xml options (2 ms, weld to the '
                                                               'replayed target, no table); report only')


def scenes_frames(b, o, p, frames, rels=None):
    """Scenes at explicit frames {name: frame} (bundle table; as scenes_bundle)."""
    from gmg import interlock as IL
    out = {}
    tb = b.meta['table']
    for name, f in frames.items():
        rel = rels[f] if rels is not None else IL.rel_pose(b.poses, o, p, f)
        W0 = b.poses['world_T_cam'][f].astype(np.float64) @ b.poses[f'cam_T_{o}'][f].astype(np.float64)
        out[name] = dict(frame=int(f), T_wh=W0, T_wg=W0 @ rel, table=(np.asarray(tb['n'], np.float64), float(tb['d'])),
                         table_kind='bundle')
    return out


def gate_pair(b, o, p, run, W, copies=None, extra_sets=None, replay=True, log=None):
    """F-I4.17.1 part 1 for one carved waiver pair (host o, guest p; W = {obj: waiver record with '_waiver'}): sets
    delivered (slotted pieces), default (unslotted pieces), control (one rectangle-frame box per board) plus
    EXTRA_SETS; scenes S1 / S2 from the bundle table, or the synthetic table when the bundle has none; the lowered
    diagnostic; the P3 replay counts when REPLAY (report only)."""
    from gmg import interlock as IL, simpieces as SP
    T = int(b.meta['T'])
    rels = {f: IL.rel_pose(b.poses, o, p, f) for f in range(T)}
    sets = {'delivered': (W[o]['_waiver']['slotted'], W[p]['_waiver']['slotted']),
            'default': (W[o]['_waiver']['default'], W[p]['_waiver']['default']),
            'control': (control_hulls(W[o]['_waiver']['body']), control_hulls(W[p]['_waiver']['body']))}
    sets.update(extra_sets or {})
    if b.meta.get('table'):
        scenes, asm = scenes_bundle(b, o, p, run, rels)
    else:
        scenes, asm = scenes_synth(run, rels, sets)
    res = gate(scenes, sets, copies=copies, lower=True, log=log)
    res['assembled_frames'] = [int(f) for f in asm]
    if replay and run.kind == 'INSERTION':
        t0 = max(0, run.frames[0] - PH.k_('pre'))
        frames = [f for f in range(t0, T) if f in rels]
        rp = {}
        for k, (h, g) in sets.items():
            t = time.time()
            rp[k] = count_replay(h, g, rels, frames, copies=copies, guest_props=SP.props(g, k_('mass_kg')))
            rp[k]['sec'] = round(time.time() - t, 1)
            if log:
                log(f'contact gate P3 replay {k}: max ncon {rp[k]["max_ncon"]} max nefc {rp[k]["max_nefc"]} '
                    f'{rp[k]["sec"]} s')
        res['p3_replay'] = rp
    return res


def summary_line(res):
    """One line for DO_NOT_USE.json / logs."""
    s = res['summary']
    dk, ck = res.get('delivered_set', 'delivered'), res.get('control_set', 'control')
    return (f"{dk} max nefc {s[dk]['max_nefc']} / max ncon {s[dk]['max_ncon']} (overflow copies "
            f"{s[dk]['overflow_copies']}), {ck} max nefc {s[ck]['max_nefc']}, ratio "
            f"{res['ratio_delivered_to_control']} (<= {res['ratio_max']}), default max nefc "
            f"{(s.get('default') or {}).get('max_nefc')}")
