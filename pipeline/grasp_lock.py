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
With --wrap, elongated objects (hull PCA ratio >= WRAP_RATIO with a narrow part) get a BUILT wrap (power) grasp
instead of the copied human one (pipeline/wrap_grasp.py; owner: the copied grasps pinch, a wrap is the strongest): the
hand comes in open, backed off BACK along its palm normal, slides onto the handle and closes until each finger touches.
With --single_hand 1, each object is carried by ONE hand from its first pick-up to its last release (the hand with the
most hold frames on it): the other hand's holds on that object are dropped and, if it holds nothing else, it stays
parked at its frame-0 pose (eval ep35: the human passes the spoon between hands six times; the locked two-hand
handovers flung it at f230). Security first: one locked grasp, no handovers.
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
import wrap_grasp as wg  # noqa: E402
from hold_phases import hold_phases  # noqa: E402

WRIST_KP, G = float(os.environ.get('GL_WRIST_KP', 25.0)), 9.81   # GL_WRIST_KP: wrist position kp of the embodiment used


def flexion_mask(names):
    return np.array([any(k in n for k in ('_FE', '_PIP', '_DIP', '_IP')) for n in names], float)


def distal_mask(names):                                            # PIP, DIP and the thumb IP: unrolled first on release
    return np.array([n.split('_')[-1] in ('PIP', 'DIP', 'IP') for n in names], float)


def blend(a, b, w):
    return (1 - w) * a + w * b


def main():
    p = argparse.ArgumentParser(); p.add_argument('inp'); p.add_argument('out')
    p.add_argument('--squeeze', type=float, default=0.4); p.add_argument('--close', type=int, default=6)
    p.add_argument('--open', type=int, default=6); p.add_argument('--lift', type=int, default=1)
    p.add_argument('--move_cm', type=float, default=1.0); p.add_argument('--search', type=int, default=10)
    p.add_argument('--blend', type=int, default=8); p.add_argument('--preopen', type=float, default=0.3)
    p.add_argument('--wrap', type=int, default=1); p.add_argument('--wrap_ratio', type=float, default=3.0)
    p.add_argument('--back', type=float, default=0.04); p.add_argument('--wrap_squeeze', type=float, default=0.4)
    p.add_argument('--single_hand', type=int, default=0)
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
    lim, flex, distal = {}, {}, {}
    for side in cr.SIDES:
        fj = t.column(f'{side}_robot_finger_joint_names')[0].as_py(); flex[side] = flexion_mask(fj); distal[side] = distal_mask(fj)
        lim[side] = (np.array([lo_lim[dstart[jidx[f'{side}_sharpa_wave/{n}']]] for n in fj]),
                     np.array([hi_lim[dstart[jidx[f'{side}_sharpa_wave/{n}']]] for n in fj]))
    ph = hold_phases(a.inp)[0]['phases']
    parked = []
    if a.single_hand:                                              # one carrier per object, from first grasp to last release
        merged = []
        for o_ in sorted({x['object'] for x in ph}):
            xs = [x for x in ph if x['object'] == o_]
            frames = {sd: sum(x['frames'] for x in xs if x['hand'] == sd) for sd in ('left', 'right')}
            hand = max(frames, key=frames.get); s1_ = max(x['end'] for x in xs)
            first = min((x for x in xs if x['hand'] == hand), key=lambda x: x['start'])
            merged.append(dict(first, end=s1_, frames=s1_ - first['start'], merged_from=len(xs)))
        held_by = {x['hand'] for x in merged}; parked = [sd for sd in ('left', 'right') if sd not in held_by]
        ph = merged
        print(f'single-hand carry: {[(x["hand"], x["object"], x["start"], x["end"]) for x in ph]}; parked {parked}', flush=True)
    obj_body = [next(i for i, l in enumerate(blabels) if l.startswith(f'track3_{n}/')) for n in names]
    sdf = {}; fk = cr.FK(m); dp = {}
    for side in cr.SIDES:
        bodies, pb, pl = cr.hand_geometry(m, side); dp[side] = [(pb == bodies[f'{side}_{fn}_DP'], fn) for fn in cr.FINGERS] + [(pb, pl)]

    def hull_vertices(j):                                          # object-frame vertices of its collision pieces
        sb = m.shape_body.numpy(); sc = m.shape_scale.numpy(); tf = m.shape_transform.numpy(); out = []
        for s_ in range(m.shape_count):
            src = m.shape_source[s_]
            if sb[s_] == obj_body[j] and src is not None and hasattr(src, 'vertices'):
                out.append(Rot.from_quat(tf[s_, 3:7]).apply(np.asarray(src.vertices, float) * sc[s_]) + tf[s_, :3])
        return np.vstack(out)

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
        qpre = np.clip(qf - a.preopen * flex[side], lo, hi); back = 0.0; wrap_info = None
        V = hull_vertices(j)
        sv = np.linalg.svd(V - V.mean(0), compute_uv=False)
        if a.wrap and sv[0] / max(sv[1], 1e-9) >= a.wrap_ratio:       # elongated: build a wrap grasp on the handle
            bodies, pb, pl = cr.hand_geometry(m, side); bq = fk(qref[g])
            knuckles = np.mean([bq[bodies[f'{side}_{fn}_PP'], :3] for fn in wg.FINGERS], 0)
            c, ax, r, rng, tpos = wg.handle_geometry(V, OR[j][g].inv().apply(knuckles - OP[g, j]))
            R_ow, T_ow_p = wg.wrap_pose(R_ow, c, ax, r)
            qw = qref[g].copy(); qw[o:o + 3] = OR[j][g].apply(T_ow_p) + OP[g, j]; qw[o + 3:o + 7] = (OR[j][g] * R_ow).as_quat()
            qw[o + 7:o + 29] = np.clip(0.0, lo, hi)
            if j not in sdf:
                sdf[j] = cr.HullSDF(m, obj_body[j])
            fj = t.column(f'{side}_robot_finger_joint_names')[0].as_py()
            qf, qs, closing = wg.close_fingers(fk, qw, o, side, fj, lo, hi, bodies, pb, pl, sdf[j],
                                               lambda X: OR[j][g].inv().apply(X - OP[g, j]), a.wrap_squeeze)
            qpre = np.clip(np.zeros(22), lo, hi); back = a.back
            wrap_info = dict(grip_obj_m=[round(float(x), 4) for x in c], com_obj_m=[round(float(x), 4) for x in m.body_com.numpy()[obj_body[j]]],
                             radius_cm=round(100 * r, 2), axis_pos_cm=round(100 * tpos, 1), narrow_cm=[round(100 * x, 1) for x in rng],
                             closing=closing, human_angle_deg=round(float(np.degrees((Rw_g.inv() * (OR[j][g] * R_ow)).magnitude())), 1))
        x_back = lambda f: (OR[j][f] * R_ow).apply([-back, 0.0, 0.0])  # noqa: E731  palm backed off along -x (hand frame)
        for f in range(max(0, h0 - a.blend), h0):                  # approach: blend into the (backed-off) pose, then slide in
            wb = (f - (h0 - a.blend) + 1) / (a.blend + 1)
            w_back = 1.0 if wb < 0.5 else 2 * (1 - wb)              # backed off in the first half, slid in over the second
            pos = OR[j][f].apply(T_ow_p) + OP[f, j] + x_back(f) * w_back
            rot = OR[j][f] * R_ow
            q_new[f, o:o + 3] = blend(qref[f, o:o + 3], pos, min(1.0, 2 * wb))
            q_new[f, o + 3:o + 7] = Slerp([0, 1], Rot.from_quat([qref[f, o + 3:o + 7], rot.as_quat()]))([wb]).as_quat()[0]
            q_new[f, o + 7:o + 29] = blend(qref[f, o + 7:o + 29], qpre, wb)
        end = min(T, s1 + 4 * a.open)                             # release: relax, unroll (OPEN frames each), withdraw (2 x OPEN)
        for f in range(h0, end):
            pos = OR[j][f].apply(T_ow_p) + OP[f, j]; rot = OR[j][f] * R_ow
            wc = min(1.0, (f - h0 + 1) / a.close)                  # finger closing ramp (from pre-open)
            if a.lift and f < s1:                                  # weight shared by the hands holding it, while in the air
                lift[side][f] = max(lift[side][f], in_air[f, j] * mass[j] * G / WRIST_KP / max(1.0, n_hold[f, j]))
            if f < s1:                                             # hold: locked grasp, fingers closing then held
                q_new[f, o:o + 3] = pos; q_new[f, o + 3:o + 7] = rot.as_quat()
                q_new[f, o + 7:o + 29] = blend(qpre, qs, wc)
            else:                                                  # release (eval ep35: opening all joints at once hooked and
                k = f - s1 + 1                                     # flicked the spoon up, f396; sliding off along the handle
                wo = min(1.0, k / a.open)                          # with the fingers still wrapped dragged it away, f404)
                wu = float(np.clip((k - a.open) / a.open, 0, 1))   # 1) relax to the touching grasp, wrist locked
                ww = max(0.0, (k - 2 * a.open) / max(1, end - s1 - 2 * a.open))   # 2) unroll: PIP/DIP/IP first, then the
                wj = np.minimum(1.0, 2 * wu) * distal[side] + np.clip(2 * wu - 1, 0, 1) * (1 - distal[side])  # knuckles
                qo = blend(qf, qpre, wj)                           # 3) withdraw along the palm normal, then to the reference
                away = pos + (OR[j][f] * R_ow).apply([-max(back, 0.04), 0.0, 0.0]) * min(1.0, 2 * ww)
                q_new[f, o:o + 3] = away if ww < 0.5 else blend(away, qref[f, o:o + 3], 2 * ww - 1)
                q_new[f, o + 3:o + 7] = Slerp([0, 1], Rot.from_quat([rot.as_quat(), qref[f, o + 3:o + 7]]))([max(0.0, 2 * ww - 1)]).as_quat()[0]
                q_new[f, o + 7:o + 29] = blend(qs, qf, wo) if wu == 0 else blend(qo, qref[f, o + 7:o + 29], ww)
        report.append(dict(x, grasp_frame=int(g), hold_from=int(h0), move_frame=int(move), fingers_on=n_on, wrap=wrap_info,
                           grasp_gap_mm=round(1000 * gap, 1), squeeze_rad=a.squeeze, mass_kg=round(mass[j], 3),
                           lift_cm=round(100 * mass[j] * G / WRIST_KP, 1) if a.lift else 0.0,
                           joints_at_limit_after_squeeze=int(((qs >= hi - 1e-6) & (flex[side] > 0)).sum())))
        if wrap_info:
            print(f"{side} {x['object']}: WRAP grasp {json.dumps(wrap_info)}", flush=True)
        print(f"{side} {x['object']} {s0}-{s1}: grasp pose from f{g} ({n_on} fingers on, mean gap {1000 * gap:.1f} mm), "
              f"hold from f{h0}, object moves f{move}, lift {report[-1]['lift_cm']} cm", flush=True)
    for side in parked:                                            # idle hand: keep its frame-0 pose (out of the way)
        o = cr.SIDES[side]; q_new[:, o:o + 29] = q_new[0, o:o + 29]
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
