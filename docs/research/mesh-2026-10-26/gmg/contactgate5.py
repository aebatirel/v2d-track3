"""Contact-budget gate of the collision carve (PREREG F-I5.16 (1); INTERLOCK.md 21.14.2; collision-carve round 2).

Named contactgate5 (not contactgate as F-I5.16 (6)(i) wrote): the board-slot lane builds its own F-I4.17 gate in
gmg/contactgate.py at the same time (seen untracked at 22:52 UTC); the two modules share no code, so neither edits the
other's file. Recorded as an F-I5.16 as-built deviation (a file name, no rule change).

  sim_rl()                          the sim=rl values from the committed copy docs/research/work/15-verify/
                                    cfg_sim_rl.yaml; its sha256 is checked against PREREG F-I5.16 before every gate run
                                    (a mismatch raises: the run stops)
  scene_xml(kind, ...)              G1 scenes with the sim=rl options: 'S' (receiver static, guest free, table plane:
                                    simphys.sink_xml) and 'settle' (both free, table plane: simphys.settle_xml);
                                    timestep 1 / (fps x substeps), Newton, implicitfast, pyramidal, impratio,
                                    iterations, ls_iterations, <size njmax nconmax>, geoms condim 3, friction 1.0;
                                    every other option at the MuJoCo default (nativeccd, multiccd on)
  count_copy / count_scene          per step d.ncon, d.nefc, the CONTACTFULL / CNSTRFULL counters; per copy maxima,
                                    steps, classes (guest-receiver, guest-table, receiver-table) at the max-nefc step;
                                    overflow := max ncon > nconmax or max nefc > njmax or a warning (plain MuJoCo grows
                                    its arena, so the limits are applied to the counts; one world per copy)
  packed_default(mesh)              FlashCHORD's decomposition of the object's visual mesh: coacd.run_coacd(threshold
                                    0.05, max_convex_hull -1, preprocess auto) with coacd 1.0.11 from a separate target
                                    (child process; the venv's coacd 1.0.14 stays for route 3)
  g1(rows)                          pass iff no delivered copy overflows at any gated scene / frame AND max nefc
                                    (delivered) <= 1.5 x max nefc (packed default), maxima over all gated rows
  g2_status(...)                    G2 (determined-wright's budget.py, max_nefc_per_world <= 380) needs FlashCHORD's
                                    environment: here it reports why it cannot run (CONTACT_GATE_PENDING.json)
GT-free: our pieces, our poses, our table plane.
"""
from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import tempfile

import numpy as np
from scipy.spatial.transform import Rotation as Rot

from gmg import guard
from gmg import simphys as PH

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, '..', '..', '..', '..'))
SIM_RL_PATH = os.path.join(REPO, 'docs', 'research', 'work', '15-verify', 'cfg_sim_rl.yaml')
SIM_RL_SHA = '695536b798ff5f7b1d391e3a6932288e23329c026f27cd364f77230d703f4b66'
SIM_RL_PREREG = dict(fps=20.0, substeps=5, solver='newton', integrator='implicitfast', cone='pyramidal', njmax=512,
                     nconmax=256, impratio=20.0, iterations=100, ls_iterations=50)
COACD_TARGET = os.environ.get('GMG_COACD1011', os.path.join(guard.SCRATCH_DEFAULT, 'coacd1011'))

C = dict(
    copies=(16, 'informed:F-I5.10 16 copies and the S jitters'),
    secs=(2.0, 'informed:F-I5.10 2 s per copy'),
    ratio=(1.5, 'decision:orchestrator decision 2 (31 Oct ~22:30 UTC) delivered max nefc <= 1.5 x packed default'),
    budget_rows=(380, 'decision:orchestrator absolute bound (~22:40 UTC) max_nefc_per_world <= 380 (G2)'),
    friction=(1.0, 'informed:F-I5.16 (5) FlashCHORD contact_friction 1.0 on every colliding shape'),
    condim=(3, 'informed:F-I5.16 (5) condim 3'),
    coacd_thr=(0.05, 'kit:FlashCHORD fc_mesh.py threshold 0.05 (the evaluator code)'),
    mass_kg=(0.3, 'informed:F-I1.14 0.3 kg placeholder'),
)


def k_(name):
    v, o = C[name]
    if o.startswith(('generic', 'kit')):
        guard.constant(f'cg5.{name}', v, o)
    return v


# ------------------------------------------------------------------------------------------------ config
def sim_rl(path=None, strict=True):
    """The sim=rl values (simple 'key: value' YAML), sha256, and the values that differ from PREREG F-I5.16."""
    path = path or SIM_RL_PATH
    raw = open(path, 'rb').read()
    vals = {}
    for line in raw.decode().splitlines():
        if ':' not in line or line.strip().startswith('#'):
            continue
        k, v = (x.strip() for x in line.split(':', 1))
        v = v.split('#', 1)[0].strip()
        if v.lower() in ('true', 'false'):
            vals[k] = v.lower() == 'true'
            continue
        try:
            vals[k] = int(v)
        except ValueError:
            try:
                vals[k] = float(v)
            except ValueError:
                vals[k] = v
    sha = hashlib.sha256(raw).hexdigest()
    mism = {k: (vals.get(k), v) for k, v in SIM_RL_PREREG.items()
            if (str(vals.get(k)).lower() if isinstance(v, str) else vals.get(k)) != v}
    out = dict(path=os.path.relpath(path, REPO), sha256=sha, sha_matches_prereg=bool(sha == SIM_RL_SHA),
               values={k: v for k, v in vals.items() if not str(k).startswith('_')}, mismatch=mism or None)
    if strict and (sha != SIM_RL_SHA or mism):
        raise RuntimeError(f'sim=rl config differs from PREREG F-I5.16 (sha {sha}, mismatch {mism}): gate run stopped')
    return out


def options(cfg=None):
    cfg = cfg or sim_rl()
    v = cfg['values']
    return dict(timestep=1.0 / (float(v['fps']) * int(v['substeps'])), solver='Newton', cone=str(v['cone']).lower(),
                integrator=str(v['integrator']).lower(), iterations=int(v['iterations']),
                ls_iterations=int(v['ls_iterations']), impratio=float(v['impratio']), njmax=int(v['njmax']),
                nconmax=int(v['nconmax']))


# ------------------------------------------------------------------------------------------------ scenes
def _geoms(hulls, tag, group):
    f = k_('friction')
    return ''.join(f'<geom type="mesh" mesh="{tag}{i}" density="0" condim="{k_("condim")}" friction="{f} 0.005 0.0001"/>'
                   for i in range(len(hulls)))


def _plane(n_table, d_table):
    n = np.asarray(n_table, float)
    p0 = -d_table * n
    z = n
    x = np.cross([0, 1.0, 0], z) if abs(z[1]) < 0.9 else np.cross([1.0, 0, 0], z)
    x /= np.linalg.norm(x)
    y = np.cross(z, x)
    q = PH._quat(np.stack([x, y, z], 1))
    return (f'<geom name="table" type="plane" size="2 2 0.1" pos="{p0[0]:.7f} {p0[1]:.7f} {p0[2]:.7f}" '
            f'quat="{q[0]:.7f} {q[1]:.7f} {q[2]:.7f} {q[3]:.7f}" condim="{k_("condim")}" friction="{k_("friction")} 0.005 0.0001"/>')


def scene_xml(kind, host, guest, T_wh, T_wg, table, hp, gp, opt):
    """KIND 'S': host static at T_wh, guest free; 'settle': both free. Table (n, d) in world; gravity along -n."""
    n_t, d_t = np.asarray(table[0], float), float(table[1])
    g = -9.81 * n_t

    def pose(T):
        q = PH._quat(T[:3, :3]); t = T[:3, 3]
        return f'pos="{t[0]:.7f} {t[1]:.7f} {t[2]:.7f}" quat="{q[0]:.7f} {q[1]:.7f} {q[2]:.7f} {q[3]:.7f}"'
    if kind == 'S':
        hb = f'<body name="H" {pose(T_wh)}>{_geoms(host, "a", 1)}</body>'
    else:
        hb = f'<body name="H" {pose(T_wh)}><freejoint/>{PH._inertial(hp)}{_geoms(host, "a", 1)}</body>'
    gb = f'<body name="G" {pose(T_wg)}><freejoint/>{PH._inertial(gp)}{_geoms(guest, "b", 2)}</body>'
    return f'''<mujoco><option timestep="{opt['timestep']:.6g}" gravity="{g[0]:.5f} {g[1]:.5f} {g[2]:.5f}" solver="{opt['solver']}" cone="{opt['cone']}" integrator="{opt['integrator']}" iterations="{opt['iterations']}" ls_iterations="{opt['ls_iterations']}" impratio="{opt['impratio']:.6g}"/>
<size njmax="{opt['njmax']}" nconmax="{opt['nconmax']}"/>
<asset>{PH._mesh_assets(host, 'a')}{PH._mesh_assets(guest, 'b')}</asset><worldbody>
{_plane(n_t, d_t)}
{hb}{gb}
</worldbody></mujoco>'''


def _classes(m, d):
    import mujoco
    nc = int(d.ncon)
    if nc == 0:
        return dict(guest_receiver=0, guest_table=0, receiver_table=0, other=0)
    hid = mujoco.mj_name2id(m, mujoco.mjtObj.mjOBJ_BODY, 'H')
    gid = mujoco.mj_name2id(m, mujoco.mjtObj.mjOBJ_BODY, 'G')
    b1 = m.geom_bodyid[np.asarray(d.contact.geom1[:nc])]
    b2 = m.geom_bodyid[np.asarray(d.contact.geom2[:nc])]
    gr = int(sum((({int(x), int(y)} == {hid, gid})) for x, y in zip(b1, b2)))
    gt = int(sum((({int(x), int(y)} == {gid, 0})) for x, y in zip(b1, b2)))
    rt = int(sum((({int(x), int(y)} == {hid, 0})) for x, y in zip(b1, b2)))
    return dict(guest_receiver=gr, guest_table=gt, receiver_table=rt, other=int(nc - gr - gt - rt))


def count_copy(m, d, steps, opt, stop_on_overflow=False):
    """Steps the model; after every mj_step records ncon / nefc (that step's collision pass). STOP_ON_OVERFLOW: stop
    the copy at its first overflowing step (the verdict is already 'overflow'; the maxima are then lower bounds,
    flagged 'stopped_at_overflow')."""
    import mujoco
    W_C, W_E = int(mujoco.mjtWarning.mjWARN_CONTACTFULL), int(mujoco.mjtWarning.mjWARN_CNSTRFULL)
    mx_c = mx_e = 0
    st_c = st_e = -1
    cls = None
    nan = False
    stopped = False
    k = -1
    for k in range(steps):
        mujoco.mj_step(m, d)
        if not np.all(np.isfinite(d.qpos)):
            nan = True
            break
        nc, ne = int(d.ncon), int(d.nefc)
        if ne > mx_e:
            mx_e, st_e, cls = ne, k, _classes(m, d)
        if nc > mx_c:
            mx_c, st_c = nc, k
        if stop_on_overflow and (nc > opt['nconmax'] or ne > opt['njmax']):
            stopped = True
            break
    wc, we = int(d.warning[W_C].number), int(d.warning[W_E].number)
    over = bool(mx_c > opt['nconmax'] or mx_e > opt['njmax'] or wc > 0 or we > 0)
    return dict(max_ncon=mx_c, step_max_ncon=st_c, max_nefc=mx_e, step_max_nefc=st_e, classes_at_max_nefc=cls,
                warn_contactfull=wc, warn_cnstrfull=we, nan=nan, steps=k + 1, overflow=over,
                stopped_at_overflow=stopped)


def count_scene(kind, host, guest, T_wh, T_wg, table, opt, hp=None, gp=None, copies=None, secs=None,
                stop_on_overflow=False):
    """COPIES jittered copies of one scene (common random numbers: S jitters the guest with simphys.jitters seed 2, as
    simphys.sink_test; settle with seed 1, as simphys.settle). Returns aggregate + per-copy rows."""
    import mujoco
    from gmg import simpieces as SP
    hp = hp or SP.props(host, k_('mass_kg'))
    gp = gp or SP.props(guest, k_('mass_kg'))
    J = PH.jitters(copies or k_('copies'), seed=2 if kind == 'S' else 1)
    steps = int(round((secs or k_('secs')) / opt['timestep']))
    rows = []
    for j in J:
        Jm = np.eye(4)
        Jm[:3, :3] = Rot.from_rotvec(j[3:]).as_matrix()
        Jm[:3, 3] = j[:3]
        m = mujoco.MjModel.from_xml_string(scene_xml(kind, host, guest, T_wh, T_wg @ Jm, table, hp, gp, opt))
        d = mujoco.MjData(m)
        mujoco.mj_forward(m, d)
        r = count_copy(m, d, steps, opt, stop_on_overflow=stop_on_overflow)
        rows.append(r)
    me = [r['max_nefc'] for r in rows]
    mc = [r['max_ncon'] for r in rows]
    return dict(kind=kind, copies=len(rows), pieces=[len(host), len(guest)], max_nefc=int(max(me)),
                median_max_nefc=float(np.median(me)), max_ncon=int(max(mc)), median_max_ncon=float(np.median(mc)),
                overflow_copies=int(sum(r['overflow'] for r in rows)), nan_copies=int(sum(r['nan'] for r in rows)),
                per_copy=rows)


# ------------------------------------------------------------------------------------------------ packed default
_CHILD = r'''
import sys, json, numpy as np
sys.path.insert(0, sys.argv[1])
import coacd, importlib.metadata as md
d = np.load(sys.argv[2])
parts = coacd.run_coacd(coacd.Mesh(d["V"], d["F"]), threshold=float(sys.argv[4]), max_convex_hull=-1,
                        preprocess_mode="auto")
np.savez(sys.argv[3], *[np.asarray(v, np.float64) for v, f in parts if len(v) >= 4])
print(json.dumps(dict(version=md.version("coacd"), file=coacd.__file__, n=len(parts))))
'''
_PACKED = {}


def packed_default(mesh, timeout_s=3600):
    """FlashCHORD's convex decomposition of the visual mesh (fc_mesh.py:62-90): coacd 1.0.11, threshold 0.05,
    max_convex_hull -1, preprocess auto. Child process with the separate coacd target first on sys.path. Returns
    (hulls, info)."""
    V = np.asarray(mesh.vertices, np.float64); F = np.asarray(mesh.faces, np.int64)
    key = hashlib.sha1(V.tobytes() + F.tobytes()).hexdigest()
    if key in _PACKED:
        return _PACKED[key]
    if not os.path.isdir(os.path.join(COACD_TARGET, 'coacd')):
        raise RuntimeError(f'coacd 1.0.11 target missing: {COACD_TARGET}')
    with tempfile.TemporaryDirectory(dir=guard.SCRATCH_DEFAULT if os.path.isdir(guard.SCRATCH_DEFAULT) else None) as td:
        inp, outp = os.path.join(td, 'in.npz'), os.path.join(td, 'out.npz')
        np.savez(inp, V=V, F=F)
        r = subprocess.run([sys.executable, '-I', '-c', _CHILD, COACD_TARGET, inp, outp, str(k_('coacd_thr'))],
                           capture_output=True, text=True, timeout=timeout_s)
        if r.returncode != 0:
            raise RuntimeError(f'packed default child failed: {r.stderr[-500:]}')
        info = json.loads(r.stdout.strip().splitlines()[-1])
        z = np.load(outp)
        hulls = [z[k] for k in sorted(z.files, key=lambda s: int(s.split('_')[1]))]
    info.update(threshold=k_('coacd_thr'), max_convex_hull=-1, preprocess_mode='auto',
                source='FlashCHORD fc_mesh.py:62-90 call on the visual mesh (PREREG F-I5.16 (1d))')
    if not info['version'].startswith('1.0.11'):
        raise RuntimeError(f'packed default ran coacd {info["version"]}, not 1.0.11')
    _PACKED[key] = (hulls, info)
    return hulls, info


# ------------------------------------------------------------------------------------------------ the gate
def g1(rows, opt=None):
    """ROWS: list of dict(scene, frame, gated, sets={name: count_scene result}) with sets 'delivered' and 'packed'.
    G1 pass iff no gated delivered copy overflows and max nefc (delivered) <= 1.5 x max nefc (packed), both over the
    gated rows. Returns the verdict dict."""
    gated = [r for r in rows if r.get('gated')]
    if not gated:
        return dict(pass_=True, flag='contact_gate_pair_vacuous', gated_rows=0)
    ov = sum(r['sets']['delivered']['overflow_copies'] for r in gated)
    md = max(r['sets']['delivered']['max_nefc'] for r in gated)
    mp = max(r['sets']['packed']['max_nefc'] for r in gated)
    p_over = sum(r['sets']['packed']['overflow_copies'] for r in gated)
    ratio = md / max(mp, 1)
    fail = 'contact_overflow' if ov else ('contact_ratio' if ratio > k_('ratio') + 1e-12 else None)
    out = dict(pass_=fail is None, fail=fail, gated_rows=len(gated), delivered_overflow_copies=int(ov),
               delivered_max_nefc=int(md), packed_max_nefc=int(mp), ratio=round(ratio, 4), ratio_max=k_('ratio'),
               delivered_max_ncon=int(max(r['sets']['delivered']['max_ncon'] for r in gated)))
    if p_over:
        out['flag_packed'] = 'packed_overflow'
    if opt:
        out['limits'] = dict(njmax=opt['njmax'], nconmax=opt['nconmax'])
    return out


def g2_status(r0_dir=None):
    """G2 needs FlashCHORD's environment (make_assets.py, budget.py, mujoco_warp): report whether it can run here."""
    why = []
    for mod in ('mujoco_warp', 'warp', 'newton'):
        try:
            __import__(mod)
        except Exception:                                            # noqa: BLE001
            why.append(f'no {mod} in this environment')
    fc = os.environ.get('FLASHCHORD_DIR')
    if not fc or not os.path.isdir(fc):
        why.append('no FlashCHORD source tree (FLASHCHORD_DIR unset or missing)')
    return dict(can_run=not why, why=why, r0=r0_dir, bound=k_('budget_rows'),
                caveat='zero-action rollouts; a grasping policy may add hand-object contacts',
                hand_off='determined-wright (budget.py at 9c1d100, build/I/budget_py_usage.md)')


def write_pending(r0_dir, status):
    p = os.path.join(r0_dir, 'CONTACT_GATE_PENDING.json')
    with open(p, 'w') as fh:
        json.dump(dict(rule='PREREG F-I5.16 (1)(g): G2 (budget.py, max_nefc_per_world <= 380) has not run; the '
                            'folder is not called usable until a passing G2 is recorded', **status), fh, indent=1)
    return p


def versions():
    import mujoco
    import importlib.metadata as md
    return dict(mujoco=mujoco.__version__, coacd_route3=md.version('coacd'), coacd_packed_target=COACD_TARGET)
