"""G3 (hands-free settle) and G4 (contact counts, indicative) of GATES.md, plain MuJoCo, for one set.

  python -I settle.py CONFIG.json OUT_DIR VARIANT [VARIANT ...]     (VARIANT: packed | a | b)

Scene: every object of the episode free at its reference pose (zero velocity) with the URDF's mass / COM / inertia;
the target carries the variant's pieces (OUT_DIR/cand_<v>/<target>/piece_*.obj, or the packed ones), partners their
packed pieces; table = plane at the support top; sim=rl options of docs/research/work/15-verify/cfg_sim_rl.yaml
(sha256 checked); condim 3, friction 1.0, margin 0, MuJoCo default solref / solimp; no hands; 2.0 s.
Frames: frame 0 if it is a T-rest frame, plus the middles of the up to 3 longest T-rest runs (frames.json). If the set
has no T-rest frame, frame 0 is run as a diagnostic (flagged). G3 copy = exact reference pose; G4 = 16 copies with the
target jittered 0.5 mm / 0.005 rad (seed 2). Writes OUT_DIR/settle_<variant>.json.
"""
import glob
import hashlib
import json
import os
import re
import sys
import time

import numpy as np
import trimesh
from scipy.spatial.transform import Rotation as Rot

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import rebase as rb  # noqa: E402

SIM_RL = '/home/user/v2d-track3/docs/research/work/15-verify/cfg_sim_rl.yaml'
SIM_RL_SHA = '695536b798ff5f7b1d391e3a6932288e23329c026f27cd364f77230d703f4b66'
SECS, COPIES, JIT_M, JIT_RAD, JIT_SEED = 2.0, 16, 0.0005, 0.005, 2
G3_MM, G3_DEG = 4.0, 5.0


def sim_rl():
    raw = open(SIM_RL, 'rb').read(); sha = hashlib.sha256(raw).hexdigest()
    assert sha == SIM_RL_SHA, sha
    v = {}
    for line in raw.decode().splitlines():
        if ':' in line and not line.startswith('_'):
            k, x = (s.strip() for s in line.split(':', 1)); v[k] = x
    return dict(timestep=1.0 / (float(v['fps']) * int(v['substeps'])), cone=v['cone'], integrator=v['integrator'],
                iterations=int(v['iterations']), ls_iterations=int(v['ls_iterations']), impratio=float(v['impratio']),
                njmax=int(v['njmax']), nconmax=int(v['nconmax']))


def urdf_inertial(p):
    s = open(p).read()
    blk = re.search(r'<inertial>(.*?)</inertial>', s, re.S).group(1)
    c = [float(x) for x in re.search(r'<origin xyz="([^"]*)"', blk).group(1).split()]
    m = float(re.search(r'<mass value="([^"]*)"', blk).group(1))
    I = {k: float(re.search(rf'{k}="([^"]*)"', blk).group(1)) for k in ('ixx', 'iyy', 'izz', 'ixy', 'ixz', 'iyz')}
    return dict(com=c, mass=m, I=I)


def xml(objs, T0, top, opt):
    a, b = [], []
    for k, (n, hulls, ine) in enumerate(objs):
        for i, V in enumerate(hulls):
            a.append(f'<mesh name="m{k}_{i}" vertex="{" ".join(f"{x:.7f}" for x in np.asarray(V).ravel())}"/>')
        T = T0[k]; q = Rot.from_matrix(T[:3, :3]).as_quat()[[3, 0, 1, 2]]; t = T[:3, 3]; c = ine['com']; I = ine['I']
        g = ''.join(f'<geom type="mesh" mesh="m{k}_{i}" condim="3" friction="1 0.005 0.0001"/>' for i in range(len(hulls)))
        b.append(f'<body name="o{k}" pos="{t[0]:.7f} {t[1]:.7f} {t[2]:.7f}" quat="{q[0]:.8f} {q[1]:.8f} {q[2]:.8f} {q[3]:.8f}">'
                 f'<freejoint/><inertial pos="{c[0]:.6f} {c[1]:.6f} {c[2]:.6f}" mass="{ine["mass"]}" fullinertia="{I["ixx"]:.9g} '
                 f'{I["iyy"]:.9g} {I["izz"]:.9g} {I["ixy"]:.9g} {I["ixz"]:.9g} {I["iyz"]:.9g}"/>{g}</body>')
    return (f'<mujoco><compiler inertiafromgeom="false" balanceinertia="true"/>'
            f'<option timestep="{opt["timestep"]:.6g}" gravity="0 0 -9.81" solver="Newton" cone="{opt["cone"]}" '
            f'integrator="{opt["integrator"]}" iterations="{opt["iterations"]}" ls_iterations="{opt["ls_iterations"]}" '
            f'impratio="{opt["impratio"]:.6g}"/><size njmax="{opt["njmax"]}" nconmax="{opt["nconmax"]}"/>'
            f'<asset>{"".join(a)}</asset><worldbody><geom name="table" type="plane" size="2 2 0.1" pos="0 0 {top:.7f}" '
            f'condim="3" friction="1 0.005 0.0001"/>{"".join(b)}</worldbody></mujoco>')


def run(x, opt, nb):
    import mujoco
    m = mujoco.MjModel.from_xml_string(x); d = mujoco.MjData(m); mujoco.mj_forward(m, d)
    p0 = d.xpos[1:nb + 1].copy(); q0 = d.xquat[1:nb + 1].copy()
    steps = int(round(SECS / opt['timestep'])); mxd = np.zeros(nb); mxr = np.zeros(nb); mc = me = 0; nan = False
    n0c, n0e = int(d.ncon), int(d.nefc)
    rot = lambda qa, qb: np.degrees(2 * np.arccos(np.clip(abs(float(np.dot(qa, qb))), 0, 1)))
    for k in range(steps):
        mujoco.mj_step(m, d)
        if not np.all(np.isfinite(d.qpos)):
            nan = True; break
        mc, me = max(mc, int(d.ncon)), max(me, int(d.nefc))
        for i in range(nb):
            mxd[i] = max(mxd[i], np.linalg.norm(d.xpos[i + 1] - p0[i]) * 1e3); mxr[i] = max(mxr[i], rot(d.xquat[i + 1], q0[i]))
    W = [int(d.warning[int(mujoco.mjtWarning.mjWARN_CONTACTFULL)].number), int(d.warning[int(mujoco.mjtWarning.mjWARN_CNSTRFULL)].number)]
    fin_d = [None if nan else round(float(np.linalg.norm(d.xpos[i + 1] - p0[i]) * 1e3), 2) for i in range(nb)]
    fin_r = [None if nan else round(float(rot(d.xquat[i + 1], q0[i])), 2) for i in range(nb)]
    return dict(final_mm=fin_d, final_deg=fin_r, max_mm=np.round(mxd, 2).tolist(), max_deg=np.round(mxr, 2).tolist(),
                ncon0=n0c, nefc0=n0e, max_ncon=mc, max_nefc=me, warn=W, nan=nan,
                overflow=bool(mc > opt['nconmax'] or me > opt['njmax'] or W[0] > 0 or W[1] > 0))


def main():
    cfg = json.load(open(sys.argv[1])); out = sys.argv[2]; variants = sys.argv[3:]
    fr = json.load(open(f'{out}/frames.json')); R = rb.load_ref(cfg['ref']); top = rb.support(cfg['usda'])['top_z']
    names = R['names']; tgt = cfg['target']; io = names.index(tgt)
    rr = sorted(fr['rest_runs'], key=lambda r: -(r[1] - r[0]))[:3]
    test = sorted(set(([0] if any(a <= 0 <= b for a, b in fr['rest_runs']) else []) + [(a + b) // 2 for a, b in rr]))
    diag = False
    if not test:
        test, diag = [0], True
    opt = sim_rl(); rng = np.random.default_rng(JIT_SEED)
    J = np.hstack([rng.normal(0, JIT_M, (COPIES, 3)), rng.normal(0, JIT_RAD, (COPIES, 3))])
    ine = {n: urdf_inertial(cfg['objects'][n]['urdf']) for n in names}
    packed = {n: rb.load_pieces(cfg['objects'][n]['packed'])[0] for n in names}
    import mujoco
    for v in variants:
        t0 = time.time()
        hulls_t = packed[tgt] if v == 'packed' else [np.asarray(trimesh.load(p, force='mesh').vertices) for p in
                                                       sorted(glob.glob(f'{out}/cand_{v}/{tgt}/piece_*.obj'))]
        objs = [(n, hulls_t if n == tgt else packed[n], ine[n]) for n in names]
        res = dict(set=cfg['set'], variant=v, target=tgt, names=names, test_frames=test, diagnostic_only=diag,
                   options=opt, mujoco=mujoco.__version__, secs=SECS, pieces=[len(h) for _, h, _ in objs], frames=[])
        for f in test:
            T0 = [R['T'][f, k] for k in range(len(names))]
            g3 = run(xml(objs, T0, top, opt), opt, len(names))
            cp = []
            for j in J:
                Jm = np.eye(4); Jm[:3, :3] = Rot.from_rotvec(j[3:]).as_matrix(); Jm[:3, 3] = j[:3]
                T1 = list(T0); T1[io] = T0[io] @ Jm
                cp.append(run(xml(objs, T1, top, opt), opt, len(names)))
            ok = (not g3['nan']) and g3['final_mm'][io] <= G3_MM and g3['final_deg'][io] <= G3_DEG
            res['frames'].append(dict(frame=int(f), G3=g3, G3_pass=bool(ok),
                                      G4=dict(max_nefc=max(c['max_nefc'] for c in cp), max_ncon=max(c['max_ncon'] for c in cp),
                                              overflow_copies=int(sum(c['overflow'] for c in cp)),
                                              nan_copies=int(sum(c['nan'] for c in cp)),
                                              target_final_mm=rb.stats([c['final_mm'][io] for c in cp if not c['nan']]),
                                              target_final_deg=rb.stats([c['final_deg'][io] for c in cp if not c['nan']]),
                                              partner_final_mm={n: rb.stats([c['final_mm'][k] for c in cp if not c['nan']])
                                                                for k, n in enumerate(names) if n != tgt})))
            print(f"{cfg['set']} {v} f{f}: target {g3['final_mm'][io]} mm / {g3['final_deg'][io]} deg (max {g3['max_mm'][io]} / "
                  f"{g3['max_deg'][io]}), all {g3['final_mm']} mm {g3['final_deg']} deg, nefc0 {g3['nefc0']} max {g3['max_nefc']}; "
                  f"G4 16 copies max nefc {res['frames'][-1]['G4']['max_nefc']} overflow {res['frames'][-1]['G4']['overflow_copies']}", flush=True)
        res['G3_pass'] = bool(all(x['G3_pass'] for x in res['frames'])) if not diag else None
        res['secs_run'] = round(time.time() - t0, 1)
        json.dump(res, open(f'{out}/settle_{v}.json', 'w'), indent=1)


if __name__ == '__main__':
    main()
