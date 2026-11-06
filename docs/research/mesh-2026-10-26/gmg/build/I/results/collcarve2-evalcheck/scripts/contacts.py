"""Eval precheck, contact numbers (PREREG F-I5.16 (3)(a); DIAGNOSTIC ONLY, decides nothing): the packed collision
pieces of each eval pair in the G1 pair scene under the sim=rl limits.

Scene (mirrors gmg/contactgate5.py 'settle' with the S draws, standalone because the gmg guard refuses the pack's
library_v3 / parquet inputs): both objects free (0.3 kg each, F-I1.14 placeholder; COM / inertia of the uniform solid
of the pieces' union on a 1.5 mm grid, as simpieces.props), the table plane at the reference's support top (z up),
plain MuJoCo 3.17.0 with the sim=rl options read from docs/research/work/15-verify/cfg_sim_rl.yaml (sha256 checked):
timestep 1 / (fps x substeps) = 0.01 s, Newton, implicitfast, pyramidal, impratio 20, 100 / 50 iterations,
<size njmax nconmax>; geoms condim 3, friction 1.0 (FlashCHORD's); 16 copies with the S jitter draws (simphys.jitters
seed 2: 0.5 mm / 0.005 rad on the guest), 2 s each. Per step d.ncon / d.nefc and the CONTACTFULL / CNSTRFULL counters;
overflow := ncon > nconmax or nefc > njmax or a warning in any step of a copy (plain MuJoCo grows its arena, so the
limits are applied to the counts; one world per copy). Caveats: plain MuJoCo, not the evaluator's MuJoCo-Warp; no
hands, no ground; zero-action.

Frames (F-I5.16 (3)(a)): up to 3 per pair, middles of the 3 longest static stretches (F-I1.1: guest origin in the
receiver frame moves < 2 mm per frame for >= 5 frames) in which the packed colliders are within s_max = 4 mm,
hands-off frames first (no robot hand point within 30 mm, then no contact label). Post-hoc fallback (this step, stated
in the README): if fewer than 3 stretches qualify, the middles of the longest runs of contact-label-free frames with
the packed colliders within 4 mm (flag not_static), then of any such frames (flag in_hand).

Usage: python -I contacts.py CONFIG.json GEO_DIR OUT_DIR [ep,...]
"""
import hashlib
import json
import os
import sys
import time

import numpy as np
import trimesh
from scipy.spatial import ConvexHull
from scipy.spatial.transform import Rotation as Rot

SIM_RL = '/home/user/v2d-track3/docs/research/work/15-verify/cfg_sim_rl.yaml'
SIM_RL_SHA = '695536b798ff5f7b1d391e3a6932288e23329c026f27cd364f77230d703f4b66'
COPIES, SECS, MASS, FRICTION, CONDIM = 16, 2.0, 0.3, 1.0, 3
JIT_M, JIT_RAD, JIT_SEED = 0.0005, 0.005, 2
SMAX_MM, STATIC_MM, STATIC_N = 4.0, 2.0, 5


def sim_rl():
    raw = open(SIM_RL, 'rb').read()
    sha = hashlib.sha256(raw).hexdigest()
    if sha != SIM_RL_SHA:
        raise RuntimeError(f'cfg_sim_rl.yaml sha {sha} differs from PREREG F-I5.16')
    v = {}
    for line in raw.decode().splitlines():
        if ':' in line and not line.startswith('_'):
            k, x = (s.strip() for s in line.split(':', 1))
            v[k] = x
    opt = dict(timestep=1.0 / (float(v['fps']) * int(v['substeps'])), solver='Newton', cone=v['cone'],
               integrator=v['integrator'], iterations=int(v['iterations']), ls_iterations=int(v['ls_iterations']),
               impratio=float(v['impratio']), njmax=int(v['njmax']), nconmax=int(v['nconmax']))
    return opt, dict(path='docs/research/work/15-verify/cfg_sim_rl.yaml', sha256=sha, values=v)


def jitters(n=COPIES, seed=JIT_SEED):
    rng = np.random.default_rng(seed)
    return np.hstack([rng.normal(0, JIT_M, (n, 3)), rng.normal(0, JIT_RAD, (n, 3))])


def quat(R):
    return Rot.from_matrix(R).as_quat()[[3, 0, 1, 2]]


def props(hulls, pitch=0.0015):
    allv = np.vstack(hulls)
    lo, hi = allv.min(0), allv.max(0)
    ax = [np.arange(lo[k] + pitch / 2, hi[k], pitch) for k in range(3)]
    G = np.stack(np.meshgrid(*ax, indexing='ij'), -1).reshape(-1, 3)
    ins = np.zeros(len(G), bool)
    for V in hulls:
        e = ConvexHull(V).equations
        m = np.all((G >= V.min(0)) & (G <= V.max(0)), 1) & ~ins
        idx = np.nonzero(m)[0]
        ins[idx[np.all(G[idx] @ e[:, :3].T + e[:, 3] <= 1e-9, 1)]] = True
    X = G[ins]
    c = X.mean(0); d = X - c
    I = MASS * (np.eye(3) * (d ** 2).sum(1).mean() - (d[:, :, None] * d[:, None, :]).mean(0))
    return dict(com=c, inertia=I, volume_cm3=float(len(X)) * pitch ** 3 * 1e6)


def inertial(p):
    c, I = p['com'], p['inertia']
    return (f'<inertial pos="{c[0]:.6f} {c[1]:.6f} {c[2]:.6f}" mass="{MASS}" fullinertia="{I[0,0]:.9g} {I[1,1]:.9g} '
            f'{I[2,2]:.9g} {I[0,1]:.9g} {I[0,2]:.9g} {I[1,2]:.9g}"/>')


def assets(hulls, tag):
    return ''.join(f'<mesh name="{tag}{i}" vertex="{" ".join(map(str, np.round(V.ravel(), 6)))}"/>'
                   for i, V in enumerate(hulls))


def geoms(hulls, tag):
    return ''.join(f'<geom type="mesh" mesh="{tag}{i}" density="0" condim="{CONDIM}" friction="{FRICTION} 0.005 0.0001"/>'
                   for i in range(len(hulls)))


def body(name, T, hulls, p, tag):
    q = quat(T[:3, :3]); t = T[:3, 3]
    return (f'<body name="{name}" pos="{t[0]:.7f} {t[1]:.7f} {t[2]:.7f}" quat="{q[0]:.7f} {q[1]:.7f} {q[2]:.7f} '
            f'{q[3]:.7f}"><freejoint/>{inertial(p)}{geoms(hulls, tag)}</body>')


def scene(hr, hg, T_wr, T_wg, top, pr, pg, opt):
    return f'''<mujoco><option timestep="{opt['timestep']:.6g}" gravity="0 0 -9.81" solver="{opt['solver']}" cone="{opt['cone']}" integrator="{opt['integrator']}" iterations="{opt['iterations']}" ls_iterations="{opt['ls_iterations']}" impratio="{opt['impratio']:.6g}"/>
<size njmax="{opt['njmax']}" nconmax="{opt['nconmax']}"/>
<asset>{assets(hr, 'a')}{assets(hg, 'b')}</asset><worldbody>
<geom name="table" type="plane" size="2 2 0.1" pos="0 0 {top:.7f}" condim="{CONDIM}" friction="{FRICTION} 0.005 0.0001"/>
{body('H', T_wr, hr, pr, 'a')}{body('G', T_wg, hg, pg, 'b')}
</worldbody></mujoco>'''


def classes(m, d):
    import mujoco
    nc = int(d.ncon)
    if nc == 0:
        return dict(guest_receiver=0, guest_table=0, receiver_table=0)
    hid = mujoco.mj_name2id(m, mujoco.mjtObj.mjOBJ_BODY, 'H')
    gid = mujoco.mj_name2id(m, mujoco.mjtObj.mjOBJ_BODY, 'G')
    b = list(zip(m.geom_bodyid[np.asarray(d.contact.geom1[:nc])], m.geom_bodyid[np.asarray(d.contact.geom2[:nc])]))
    return dict(guest_receiver=int(sum({int(x), int(y)} == {hid, gid} for x, y in b)),
                guest_table=int(sum({int(x), int(y)} == {gid, 0} for x, y in b)),
                receiver_table=int(sum({int(x), int(y)} == {hid, 0} for x, y in b)))


def count_copy(xml, opt, steps):
    import mujoco
    m = mujoco.MjModel.from_xml_string(xml)
    d = mujoco.MjData(m)
    mujoco.mj_forward(m, d)
    n0c, n0e = int(d.ncon), int(d.nefc)
    W_C, W_E = int(mujoco.mjtWarning.mjWARN_CONTACTFULL), int(mujoco.mjtWarning.mjWARN_CNSTRFULL)
    mx_c = mx_e = 0; st_c = st_e = -1; cls = None; nan = False; k = -1
    q0 = d.qpos.copy()
    for k in range(steps):
        mujoco.mj_step(m, d)
        if not np.all(np.isfinite(d.qpos)):
            nan = True
            break
        nc, ne = int(d.ncon), int(d.nefc)
        if ne > mx_e:
            mx_e, st_e, cls = ne, k, classes(m, d)
        if nc > mx_c:
            mx_c, st_c = nc, k
    wc, we = int(d.warning[W_C].number), int(d.warning[W_E].number)
    disp = None if nan else [round(float(np.linalg.norm(d.qpos[7 * i:7 * i + 3] - q0[7 * i:7 * i + 3])) * 1e3, 1)
                             for i in range(2)]
    return dict(ncon0=n0c, nefc0=n0e, max_ncon=mx_c, step_max_ncon=st_c, max_nefc=mx_e, step_max_nefc=st_e,
                classes_at_max_nefc=cls, warn_contactfull=wc, warn_cnstrfull=we, nan=nan, steps=k + 1,
                overflow=bool(mx_c > opt['nconmax'] or mx_e > opt['njmax'] or wc > 0 or we > 0),
                disp_mm_receiver_guest=disp)


def runs_of(mask):
    out, f, n = [], 0, len(mask)
    while f < n:
        if mask[f]:
            g = f
            while g + 1 < n and mask[g + 1]:
                g += 1
            out.append((f, g))
            f = g + 1
        else:
            f += 1
    return out


def pick_frames(rows, pair, k=3):
    nf = len(rows)
    near = np.array([p['dist_packed_mm'] <= SMAX_MM for p in pair])
    st = np.array([r['rel_speed_mm'] < STATIC_MM for r in rows])
    H0 = np.array([r['H0'] for r in rows]); H30 = np.array([r['H30'] for r in rows])
    cand = []
    for a, b in runs_of(st & near):
        if b - a + 1 >= STATIC_N:
            mid = (a + b) // 2
            cand.append(dict(frame=int(mid), run=[a, b], length=b - a + 1, kind='static',
                             hands='H30' if H30[mid] else ('H0' if H0[mid] else 'in_hand')))
    order = {'H30': 0, 'H0': 1, 'in_hand': 2}
    cand.sort(key=lambda c: (order[c['hands']], -c['length']))
    sel = cand[:k]
    if len(sel) < k:
        used = {c['frame'] for c in sel}
        fb = []
        for a, b in runs_of(H0 & near):
            mid = (a + b) // 2
            if mid not in used:
                fb.append(dict(frame=int(mid), run=[a, b], length=b - a + 1, kind='not_static', hands='H0'))
        fb.sort(key=lambda c: -c['length'])
        sel += fb[:k - len(sel)]
    if len(sel) < k:
        used = {c['frame'] for c in sel}
        fb = []
        for a, b in runs_of(near):
            mid = (a + b) // 2
            if mid not in used:
                fb.append(dict(frame=int(mid), run=[a, b], length=b - a + 1, kind='not_static', hands='in_hand'))
        fb.sort(key=lambda c: -c['length'])
        sel += fb[:k - len(sel)]
    return sel, dict(static_near_runs=len(cand), frames_near=int(near.sum()), frames=nf)


def load_hulls(oc):
    if oc.get('packed_npz'):
        z = np.load(oc['packed_npz'])
        return [z[f'v{i}'] for i in range(int(z['n']))]
    return [np.asarray(trimesh.load(p, force='mesh').vertices, float) for p in oc['pieces']]


def main():
    cfg = json.load(open(sys.argv[1]))
    geo, out = sys.argv[2], sys.argv[3]
    os.makedirs(out, exist_ok=True)
    eps = sys.argv[4].split(',') if len(sys.argv) > 4 else list(cfg['episodes'])
    opt, cfg_info = sim_rl()
    import mujoco
    steps = int(round(SECS / opt['timestep']))
    J = jitters()
    lf = open(os.path.join(out, 'contacts.log'), 'a')

    def log(s):
        line = time.strftime('%H:%M:%S ', time.gmtime()) + s
        print(line, flush=True); lf.write(line + '\n'); lf.flush()
    for ep in eps:
        fr = json.load(open(os.path.join(geo, f'ep{ep}_frames.json')))
        po = np.load(os.path.join(geo, f'ep{ep}_poses.npz'))
        T, ir, ig = po['T'], int(po['ir']), int(po['ig'])
        names = [str(x) for x in po['names']]
        top = fr['summary']['support']['top_z']
        ec = cfg['episodes'][ep]
        hr, hg = load_hulls(ec['objects'][names[ir]]), load_hulls(ec['objects'][names[ig]])
        pr, pg = props(hr), props(hg)
        sel, info = pick_frames(fr['per_frame']['rows'], fr['per_frame']['pair'])
        res = dict(ep=ep, receiver=names[ir], guest=names[ig], pieces=[len(hr), len(hg)], table_top_z=top,
                   sim_rl=cfg_info, options=opt, copies=COPIES, secs=SECS, steps=steps, mass_kg=MASS,
                   friction=FRICTION, condim=CONDIM, mujoco=mujoco.__version__, frame_pick=info, frames=[])
        for c in sel:
            f = c['frame']
            t0 = time.time()
            rows = []
            for j in J:
                Jm = np.eye(4)
                Jm[:3, :3] = Rot.from_rotvec(j[3:]).as_matrix(); Jm[:3, 3] = j[:3]
                rows.append(count_copy(scene(hr, hg, T[f, ir], T[f, ig] @ Jm, top, pr, pg, opt), opt, steps))
            me = [r['max_nefc'] for r in rows]; mc = [r['max_ncon'] for r in rows]
            i = int(np.argmax(me))
            agg = dict(c, max_nefc=int(max(me)), median_max_nefc=float(np.median(me)), max_ncon=int(max(mc)),
                       median_max_ncon=float(np.median(mc)), overflow_copies=int(sum(r['overflow'] for r in rows)),
                       nan_copies=int(sum(r['nan'] for r in rows)), step_max_nefc=rows[i]['step_max_nefc'],
                       classes_at_max_nefc=rows[i]['classes_at_max_nefc'],
                       pair_at_frame={k: fr['per_frame']['pair'][f][k] for k in ('V_packed', 'dist_packed_mm',
                                                                                 'V_faithful')},
                       secs=round(time.time() - t0, 1), per_copy=rows)
            res['frames'].append(agg)
            log(f"ep{ep} f{f} ({c['kind']}, {c['hands']}): max nefc {agg['max_nefc']} ncon {agg['max_ncon']} "
                f"overflow {agg['overflow_copies']}/{COPIES} classes {agg['classes_at_max_nefc']} {agg['secs']} s")
        res['overflow_any'] = bool(any(a['overflow_copies'] for a in res['frames']))
        res['max_nefc'] = max([a['max_nefc'] for a in res['frames']], default=None)
        res['max_ncon'] = max([a['max_ncon'] for a in res['frames']], default=None)
        json.dump(res, open(os.path.join(out, f'ep{ep}_contacts.json'), 'w'), indent=1, default=float)


if __name__ == '__main__':
    main()
