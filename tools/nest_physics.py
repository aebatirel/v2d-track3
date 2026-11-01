#!/usr/bin/env python3
"""Physics projection of a cup nest (perception sprint "mask10", option c; 31 Oct 2026) [H until its public gate].
GROUND-TRUTH-FREE: reads a perception directory (poses.npz: world_T_cam, cam_T_<obj>), the S12 record of a refine run
(pose_opt.json: the nest windows and our table plane), our hands (hands_refined.npz) and our collision pieces
(DIR/<obj>/piece_*.obj + inertia.json, the make_assets layout; meshes/carve/ev10 for the eval-10 cups). Every path passes
refine.assert_inference_input. Runs in the FlashCHORD venv (MuJoCo 3.8.1, CPU).

For each S12 window that was applied (frames [start, hold_end)), on each frame where no measured hand is within
--hand_cm of the cup(s) being settled (refine.hand_distances at the tracked pose):
  --mode inner  the inner cup is a free body started at its pose in --in (zero velocity); the outer cup is static at
                its pose in --in (for the S12 V1 output: the held pre-nest pose); the table is a static plane (our
                frame-0 plane from pose_opt.json, S12's).
  --mode both   both cups are free bodies started at their poses in --in (use the S12 detection on the raw track).
Gravity along -n, timestep --dt (2 ms), --settle seconds (1.0) of mj_step, MuJoCo default contact parameters; each frame
is settled independently. The settled pose replaces the input pose; at the edges of each run of settled frames the pose
ramps from the input to the settled pose over --ramp frames (SE(3) screw), inside the window only. Writes OUT/poses.npz
(world_T_cam copied, cam_T_<obj> in float64: a float32 round trip of a held pose leaves ~1e-8 rad jitter that
refine.se3_log's small-angle branch does not cover; with --mode inner on an S12 hold the held outer frames are restored
to one exact pose), OUT/poses_world_vo.npz, OUT/nest_physics.json, and links vo.json, depth0.npy and
hands_refined.npz from --in so that refine (e.g. --steps S2) can run on OUT.
Usage: nest_physics.py --in DIR --popt DIR/pose_opt.json --pieces meshes/carve/ev10 --hands H.npz --mode inner --out OUT
"""
import argparse
import glob
import json
import os
import shutil
import sys
import time

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(REPO, 'pipeline'))
import refine as RF  # noqa: E402


def table_frame(n, d):
    """4x4 A mapping world -> table frame (z = n, plane at z = 0)."""
    n = np.asarray(n, float) / np.linalg.norm(n)
    e1 = np.cross(n, [1.0, 0, 0] if abs(n[0]) < 0.9 else [0, 1.0, 0])
    e1 /= np.linalg.norm(e1)
    e2 = np.cross(n, e1)
    R = np.stack([e1, e2, n])
    A = np.eye(4)
    A[:3, :3] = R
    A[:3, 3] = -R @ (-d * n)
    return A


def quat_wxyz(R):
    from scipy.spatial.transform import Rotation
    q = Rotation.from_matrix(R).as_quat()
    return np.r_[q[3], q[:3]]


def build_xml(cups, pieces, free, dt):
    """cups: names; free: set of names that get a free joint; static ones are placed by the caller via body pos/quat."""
    assets, bodies = [], []
    for c in cups:
        pcs = sorted(glob.glob(os.path.join(pieces, c, 'piece_*.obj')))
        if not pcs:
            raise SystemExit(f'no collision pieces for {c} in {pieces}')
        for k, p in enumerate(pcs):
            assets.append(f'<mesh name="{c}_{k}" file="{RF.checked(os.path.abspath(p))}"/>')
        ine = json.load(open(RF.checked(os.path.join(pieces, c, 'inertia.json'))))
        I = np.asarray(ine['inertia'], float)
        geoms = ''.join(f'<geom type="mesh" mesh="{c}_{k}"/>' for k in range(len(pcs)))
        if c in free:
            bodies.append(f'<body name="{c}" pos="0 0 0.5"><freejoint name="{c}_j"/>'
                          f'<inertial pos="{" ".join(map(str, ine["com"]))}" mass="{ine["mass"]}" '
                          f'fullinertia="{I[0,0]} {I[1,1]} {I[2,2]} {I[0,1]} {I[0,2]} {I[1,2]}"/>{geoms}</body>')
        else:
            bodies.append(f'<body name="{c}" mocap="true">{geoms}</body>')
    return (f'<mujoco><compiler angle="radian"/><option timestep="{dt}" gravity="0 0 -9.81"/>'
            f'<asset>{"".join(assets)}</asset><worldbody><geom name="table" type="plane" size="2 2 0.01"/>'
            f'{"".join(bodies)}</worldbody></mujoco>')


def settle(model, data, poses_tab, free, steps):
    """poses_tab: {name: 4x4 table-frame pose}. Returns ({name: settled 4x4}, info)."""
    import mujoco
    mujoco.mj_resetData(model, data)
    for c, P in poses_tab.items():
        b = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_BODY, c)
        if c in free:
            j = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_JOINT, f'{c}_j')
            a = model.jnt_qposadr[j]
            data.qpos[a:a + 3] = P[:3, 3]
            data.qpos[a + 3:a + 7] = quat_wxyz(P[:3, :3])
        else:
            m = model.body_mocapid[b]
            data.mocap_pos[m] = P[:3, 3]
            data.mocap_quat[m] = quat_wxyz(P[:3, :3])
    mujoco.mj_forward(model, data)
    pen0 = float(min([data.contact[k].dist for k in range(data.ncon)], default=0.0))
    for _ in range(steps):
        mujoco.mj_step(model, data)
    out = {}
    from scipy.spatial.transform import Rotation
    for c in free:
        b = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_BODY, c)
        P = np.eye(4)
        q = data.xquat[b]
        P[:3, :3] = Rotation.from_quat([q[1], q[2], q[3], q[0]]).as_matrix()
        P[:3, 3] = data.xpos[b]
        out[c] = P
    return out, dict(start_min_contact_dist_mm=round(pen0 * 1000, 2), end_speed_cm_s=round(float(np.abs(data.qvel).max() * 100), 3),
                     ncon_end=int(data.ncon))


def main():
    import mujoco
    ap = argparse.ArgumentParser()
    ap.add_argument('--in', dest='inp', required=True)
    ap.add_argument('--popt', required=True)
    ap.add_argument('--pieces', required=True)
    ap.add_argument('--hands', required=True)
    ap.add_argument('--meshes', default=os.path.join(REPO, 'meshes', 'library_v3'))
    ap.add_argument('--mode', choices=['inner', 'both'], required=True)
    ap.add_argument('--out', required=True)
    ap.add_argument('--hand_cm', type=float, default=5.0)
    ap.add_argument('--dt', type=float, default=0.002)
    ap.add_argument('--settle', type=float, default=1.0)
    ap.add_argument('--ramp', type=int, default=5)
    a = ap.parse_args()
    for p in (a.inp, a.popt, a.pieces, a.hands, a.meshes):
        RF.assert_inference_input(p)
    if os.path.realpath(a.inp) == os.path.realpath(a.out):
        raise SystemExit('--out must differ from --in')
    os.makedirs(a.out, exist_ok=True)
    t0 = time.time()
    P = np.load(RF.checked(os.path.join(a.inp, 'poses.npz')))
    W = P['world_T_cam'].astype(np.float64)
    names = [k[6:] for k in P.files if k.startswith('cam_T_')]
    O_in = {n: np.einsum('tij,tjk->tik', W, P[f'cam_T_{n}'].astype(np.float64)) for n in names}
    O = {n: v.copy() for n, v in O_in.items()}
    T = len(W)
    rec = json.load(open(RF.checked(a.popt)))['steps']['S12']
    H = np.load(RF.checked(a.hands))
    J = {s: H[f'joints_{s}'].astype(np.float64) for s in ('left', 'right') if f'joints_{s}' in H.files}
    M = {s: (H[f'measured_{s}'] if f'measured_{s}' in H.files else H[f'valid_{s}']).astype(bool) for s in J}
    A = table_frame(rec['plane']['n'], rec['plane']['d'])
    Ai = np.linalg.inv(A)
    out = dict(tool='tools/nest_physics.py', argv=sys.argv, mode=a.mode, pieces=a.pieces, dt=a.dt, settle_s=a.settle,
               hand_cm=a.hand_cm, inputs={k: dict(path=v, sha256=RF.sha256(v)) for k, v in
                                          (('poses.npz', os.path.join(a.inp, 'poses.npz')), ('pose_opt.json', a.popt),
                                           ('hands', a.hands))},
               code=dict(nest_physics_sha256=RF.sha256(os.path.abspath(__file__)), refine=RF.code_version()),
               mujoco=mujoco.__version__, windows=[])
    steps = int(round(a.settle / a.dt))
    for w in rec.get('windows', []):
        win = dict(outer=w['outer'], inner=w['inner'])
        if a.mode == 'inner' and not w.get('applied'):
            win['skipped'] = 'S12 window not applied'
            out['windows'].append(win)
            continue
        ts, te = int(w['start']), int(w.get('hold_end', w['end']))
        free = {w['inner']} if a.mode == 'inner' else {w['inner'], w['outer']}
        if a.mode == 'inner' and rec.get('mode') == 'hold':
            # the held outer is one pose P*; reading it back through float32 cam_T leaves ~1e-8 rad of frame-to-frame
            # jitter, on which refine.se3_log (small-angle branch below 1e-8 only) can divide by zero in a later S2 run.
            # Restore one exact pose on the held frames (it is P* to float32 precision).
            O[w['outer']][ts:te] = O_in[w['outer']][ts]
            win['outer_snapped_to_frame'] = ts
        objs = {n: RF.Obj(n, os.path.join(a.meshes, f'{n}.glb')) for n in (w['outer'], w['inner'])}
        hd = np.min([RF.hand_distances(O_in[n], objs[n].S, J, M) for n in free], axis=0)
        rel = np.zeros(T, bool)
        rel[ts:te] = hd[ts:te] >= a.hand_cm
        model = mujoco.MjModel.from_xml_string(build_xml([w['outer'], w['inner']], a.pieces, free, a.dt))
        data = mujoco.MjData(model)
        settled, finfo = {n: {} for n in free}, {}
        for t in np.nonzero(rel)[0]:
            s, inf = settle(model, data, {n: A @ O_in[n][t] for n in (w['outer'], w['inner'])}, free, steps)
            for n in free:
                settled[n][int(t)] = Ai @ s[n]
                c = objs[n].V.mean(0)
                dc = settled[n][int(t)][:3, :3] @ c + settled[n][int(t)][:3, 3] - (O_in[n][t][:3, :3] @ c + O_in[n][t][:3, 3])
                nn = A[2, :3]
                inf[f'{n}_dz_cm'] = round(float(dc @ nn * 100), 3)
                inf[f'{n}_dxy_cm'] = round(float(np.linalg.norm(dc - (dc @ nn) * nn) * 100), 3)
            finfo[int(t)] = inf
        for n in free:
            for s0, e0 in RF.runs(rel):
                for t in range(s0, e0):
                    O[n][t] = settled[n][t]
                for k in range(1, a.ramp + 1):
                    al = 1 - k / (a.ramp + 1)
                    if s0 - k >= ts and not rel[s0 - k]:
                        O[n][s0 - k] = RF.interp_pose(O_in[n][s0 - k], settled[n][s0], al)
                    if e0 - 1 + k < te and not rel[e0 - 1 + k]:
                        O[n][e0 - 1 + k] = RF.interp_pose(O_in[n][e0 - 1 + k], settled[n][e0 - 1], al)
        dzs = {n: [v[f'{n}_dz_cm'] for v in finfo.values()] for n in free}
        win.update(window=[ts, te], frames_settled=int(rel.sum()), runs=RF.runs(rel),
                   dz_cm={n: dict(median=round(float(np.median(v)), 3), min=round(float(np.min(v)), 3),
                                  max=round(float(np.max(v)), 3)) for n, v in dzs.items() if v},
                   frames={k: v for k, v in list(finfo.items())[::5]})
        out['windows'].append(win)
        print(f'nest_physics {a.mode}: window {w["outer"]} <- {w["inner"]} [{ts}, {te}), settled {int(rel.sum())} frames; '
              f'dz {win["dz_cm"]}', flush=True)
    if sum(w.get('frames_settled', 0) for w in out['windows']) == 0:   # nothing settled: the input files, byte for byte
        shutil.copyfile(os.path.join(a.inp, 'poses.npz'), os.path.join(a.out, 'poses.npz'))
        if os.path.exists(os.path.join(a.inp, 'poses_world_vo.npz')):
            shutil.copyfile(os.path.join(a.inp, 'poses_world_vo.npz'), os.path.join(a.out, 'poses_world_vo.npz'))
        out['copied_input'] = True
    else:
        Ct = {}
        for n in names:                                   # float64 out (unchanged frames: the input values exactly)
            Ct[n] = P[f'cam_T_{n}'].astype(np.float64)
            for t in range(T):
                if not np.array_equal(O[n][t], O_in[n][t]):
                    Ct[n][t] = np.linalg.inv(W[t]) @ O[n][t]
        np.savez(os.path.join(a.out, 'poses.npz'), world_T_cam=P['world_T_cam'], **{f'cam_T_{n}': Ct[n] for n in names})
        np.savez(os.path.join(a.out, 'poses_world_vo.npz'),
                 **{n: np.einsum('tij,tjk->tik', W, Ct[n].astype(np.float64)) for n in names})
    for f in ('vo.json', 'depth0.npy', 'hands_refined.npz'):
        src = os.path.join(a.inp, f)
        if os.path.lexists(src):
            dst = os.path.join(a.out, f)
            if os.path.lexists(dst):
                os.remove(dst)
            if f == 'vo.json':
                shutil.copyfile(src, dst)
            else:
                os.symlink(os.path.realpath(src), dst)
    out['seconds'] = round(time.time() - t0, 1)
    json.dump(out, open(os.path.join(a.out, 'nest_physics.json'), 'w'), indent=1)
    print('wrote', a.out, out['seconds'], 's')


if __name__ == '__main__':
    main()
