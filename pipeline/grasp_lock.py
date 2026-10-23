"""Grasp-lock reference (2026-10-23, owner: "replicate the grasps, not the whole policy; a secure grasp matters more
than replicating it"; docs/research/notes/23). Rewrites a FlashCHORD reference so that, in every hold phase
(pipeline/hold_phases.py), the robot hand keeps ONE grasp and moves with the object:
  - grasp frame g* = the frame, from the hold start to SEARCH frames after the object starts moving, where the
    reference hand is most on the object (most distal links within 5 mm of its collision hulls, then the smallest mean
    distance). v1 took CLOSE frames before the move: on eval ep3 the human fingers were still 3.5 cm off the spoon
    there, so the locked grasp squeezed air. The wrist pose in the object frame at g* is held from the hold start h0 to
    the end, so the wrist follows the object's reference path (an in-hand roll by the human becomes a wrist rotation);
    h0 = min(hold start, move - CLOSE) so the fingers close before the object moves; the wrist blends into the locked
    pose over BLEND frames before h0 with the fingers pre-opened by PREOPEN rad;
  - fingers: the reference grasp at g*, closed by SQUEEZE rad on the flexion joints (clipped to the joint limits) over
    CLOSE frames from h0, so the PD targets sit inside the object and press (finger kp 1.7 N m/rad);
  - wrist feed-forward lift: + m g / kp_wrist (kp 25 N/m) shared by the hands holding the object, so the soft wrist
    does not sag under the object (0.3 kg -> 11.8 cm). It is a control offset only: added to the wrist TARGET column
    while the reference has the object off its rest height (ramping in over its first cm of rise); the robot frames
    (rewards, keypoints) keep the locked grasp pose (v1 put the lift into the frames too: the reference hand floated
    12 cm above the spoon and the simulated hand left without it);
  - after the phase the fingers reopen and the wrist blends back to the original reference over OPEN frames.
Object trajectories are not touched. Only our own reference is read (no ground truth). The candidate is not trusted:
pipeline/grasp_test.py replays it in the evaluator's physics and measures whether the object is held.
Usage (FlashCHORD python, from the flash_chord dir, FC set):
  python grasp_lock.py IN_PARQUET OUT_PARQUET [--squeeze 0.4] [--close 6] [--open 6] [--lift 1]
OUT_PARQUET must sit in a reference tree with reconstructed_stage/ like IN_PARQUET.
"""
import argparse, json, os, sys, time

import numpy as np
import pyarrow.parquet as pq
from scipy.spatial.transform import Rotation as Rot, Slerp

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import contact_retarget as cr  # noqa: E402
from hold_phases import hold_phases  # noqa: E402

WRIST_KP, G = 25.0, 9.81


def flexion_mask(names):
    return np.array([any(k in n for k in ('_FE', '_PIP', '_DIP', '_IP')) for n in names], float)


def blend(a, b, w):
    return (1 - w) * a + w * b


def main():
    p = argparse.ArgumentParser(); p.add_argument('inp'); p.add_argument('out')
    p.add_argument('--squeeze', type=float, default=0.4); p.add_argument('--close', type=int, default=6)
    p.add_argument('--open', type=int, default=6); p.add_argument('--lift', type=int, default=1)
    p.add_argument('--move_cm', type=float, default=1.0); p.add_argument('--search', type=int, default=10)
    p.add_argument('--blend', type=int, default=8); p.add_argument('--preopen', type=float, default=0.3)
    a = p.parse_args(); t0 = time.time(); fc = os.environ.get('FC', os.getcwd())
    st, env = cr.build_scene(os.path.abspath(a.inp), fc); m = st.scene.model
    t = pq.read_table(a.inp); qref = np.asarray(st.scene.robot_reference.joint_q, float).copy(); T = len(qref)
    names = t.column('object_body_names')[0].as_py()
    OP = np.array(t.column('object_body_position')[0].as_py(), float).reshape(T, len(names), 3)
    OR = [Rot.from_quat(np.array(t.column('object_body_wxyz')[0].as_py(), float).reshape(T, len(names), 4)[:, j][:, [1, 2, 3, 0]])
          for j in range(len(names))]
    blabels = list(getattr(m, 'body_label', None) or getattr(m, 'body_key', []))
    mass = [float(m.body_mass.numpy()[next(i for i, l in enumerate(blabels) if l.startswith(f'track3_{n}/'))]) for n in names]
    lo_lim, hi_lim = m.joint_limit_lower.numpy(), m.joint_limit_upper.numpy(); dstart = m.joint_qd_start.numpy()
    jl = list(getattr(m, 'joint_label', None) or getattr(m, 'joint_key', [])); jidx = {l: i for i, l in enumerate(jl)}
    lim, flex = {}, {}
    for side in cr.SIDES:
        fj = t.column(f'{side}_robot_finger_joint_names')[0].as_py(); flex[side] = flexion_mask(fj)
        lim[side] = (np.array([lo_lim[dstart[jidx[f'{side}_sharpa_wave/{n}']]] for n in fj]),
                     np.array([hi_lim[dstart[jidx[f'{side}_sharpa_wave/{n}']]] for n in fj]))
    ph = hold_phases(a.inp)[0]['phases']
    obj_body = [next(i for i, l in enumerate(blabels) if l.startswith(f'track3_{n}/')) for n in names]
    sdf = {}; fk = cr.FK(m); dp = {}
    for side in cr.SIDES:
        bodies, pb, pl = cr.hand_geometry(m, side); dp[side] = [(pb == bodies[f'{side}_{fn}_DP'], fn) for fn in cr.FINGERS] + [(pb, pl)]

    def on_object(side, j, f):                                     # (fingers within 5 mm, mean distal-link distance)
        if j not in sdf:
            sdf[j] = cr.HullSDF(m, obj_body[j])
        pb, pl = dp[side][-1]; X = cr.world_points(fk(qref[f]), pb, pl); Xo = OR[j][f].inv().apply(X - OP[f, j]); d = sdf[j](Xo)
        per = np.array([d[msk].min() for msk, _ in dp[side][:-1]]); return int((per < 0.005).sum()), float(np.clip(per, 0, None).mean())
    # how many hands hold each object at each frame (weight sharing for the lift)
    n_hold = np.zeros((T, len(names)))
    for x in ph:
        n_hold[x['start']:x['end'], names.index(x['object'])] += 1
    q_new = qref.copy(); report = []; lift = {s: np.zeros(T) for s in cr.SIDES}
    zrise = OP[:, :, 2] - OP[0, :, 2]                                 # object height above its frame-0 rest
    in_air = np.clip(zrise / 0.01, 0.0, 1.0)
    for x in ph:
        side, j, s0, s1 = x['hand'], names.index(x['object']), x['start'], x['end']; o = cr.SIDES[side]
        disp = np.linalg.norm(OP[s0:s1, j] - OP[s0, j], axis=1) * 100
        mv = np.nonzero(disp > a.move_cm)[0]; move = s0 + (int(mv[0]) if len(mv) else 0)
        cand = range(s0, max(s0 + 1, min(s1 - 1, move + a.search)))
        scored = [(on_object(side, j, f), f) for f in cand]
        (n_on, gap), g = max(scored, key=lambda r: (r[0][0], -r[0][1]))
        h0 = max(0, min(s0, move - a.close))
        Rw_g = Rot.from_quat(qref[g, o + 3:o + 7]); T_ow_p = OR[j][g].inv().apply(qref[g, o:o + 3] - OP[g, j]); R_ow = OR[j][g].inv() * Rw_g
        lo, hi = lim[side]; qf = qref[g, o + 7:o + 29]; qs = np.clip(qf + a.squeeze * flex[side], lo, hi)
        qpre = np.clip(qf - a.preopen * flex[side], lo, hi)
        for f in range(max(0, h0 - a.blend), h0):                  # approach: blend into the locked pose, fingers pre-open
            wb = (f - (h0 - a.blend) + 1) / (a.blend + 1)
            pos = OR[j][f].apply(T_ow_p) + OP[f, j]; rot = OR[j][f] * R_ow
            q_new[f, o:o + 3] = blend(qref[f, o:o + 3], pos, wb)
            q_new[f, o + 3:o + 7] = Slerp([0, 1], Rot.from_quat([qref[f, o + 3:o + 7], rot.as_quat()]))([wb]).as_quat()[0]
            q_new[f, o + 7:o + 29] = blend(qref[f, o + 7:o + 29], qpre, wb)
        end = min(T, s1 + a.open)
        for f in range(h0, end):
            pos = OR[j][f].apply(T_ow_p) + OP[f, j]; rot = OR[j][f] * R_ow
            wc = min(1.0, (f - h0 + 1) / a.close)                  # finger closing ramp (from pre-open)
            if a.lift and f < s1:                                  # weight shared by the hands holding it, while in the air
                lift[side][f] = max(lift[side][f], in_air[f, j] * mass[j] * G / WRIST_KP / max(1.0, n_hold[f, j]))
            if f < s1:                                             # hold: locked grasp, fingers closing then held
                q_new[f, o:o + 3] = pos; q_new[f, o + 3:o + 7] = rot.as_quat()
                q_new[f, o + 7:o + 29] = blend(qpre, qs, wc)
            else:                                                  # release: reopen, blend back to the reference
                wr = (f - s1 + 1) / (end - s1)
                q_new[f, o:o + 3] = blend(pos, qref[f, o:o + 3], wr)
                q_new[f, o + 3:o + 7] = Slerp([0, 1], Rot.from_quat([rot.as_quat(), qref[f, o + 3:o + 7]]))([wr]).as_quat()[0]
                q_new[f, o + 7:o + 29] = blend(qs, qref[f, o + 7:o + 29], wr)
        report.append(dict(x, grasp_frame=int(g), hold_from=int(h0), move_frame=int(move), fingers_on=n_on,
                           grasp_gap_mm=round(1000 * gap, 1), squeeze_rad=a.squeeze, mass_kg=round(mass[j], 3),
                           lift_cm=round(100 * mass[j] * G / WRIST_KP, 1) if a.lift else 0.0,
                           joints_at_limit_after_squeeze=int(((qs >= hi - 1e-6) & (flex[side] > 0)).sum())))
        print(f"{side} {x['object']} {s0}-{s1}: grasp pose from f{g} ({n_on} fingers on, mean gap {1000 * gap:.1f} mm), "
              f"hold from f{h0}, object moves f{move}, lift {report[-1]['lift_cm']} cm", flush=True)
    out, attached = cr.write_robot(t, m, fk, qref, q_new)          # frames from the kinematic (lift-free) grasp
    if a.lift:                                                     # the lift goes into the wrist target column only
        import pyarrow as pa
        for side, o in cr.SIDES.items():
            lf = lift[side].copy()
            for f in range(1, T):                                  # ramp out over OPEN frames when a hold ends
                lf[f] = max(lf[f], lf[f - 1] - lift[side].max() / max(1, a.open))
            c = f'robot_{side}_wrist_position'; w = q_new[:, o:o + 3] + np.c_[np.zeros((T, 2)), lf]
            i = out.column_names.index(c); out = out.set_column(i, c, pa.array([w.tolist()], type=out.schema.field(c).type))
            print(f'{side}: wrist target lift max {100 * lf.max():.1f} cm on {int((lf > 1e-4).sum())} frames', flush=True)
    os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True); pq.write_table(out, a.out)
    json.dump(dict(phases=report, attached=attached, args=vars(a)), open(os.path.splitext(a.out)[0] + '_grasp_lock.json', 'w'), indent=1)
    print(f'[{time.time() - t0:.0f}s] wrote {a.out}; frames attached {attached}', flush=True)


if __name__ == '__main__':
    import warp as wp
    with wp.ScopedDevice('cpu'):
        main()
