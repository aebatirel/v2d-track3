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
With --sim_trace TRACE.npz (a zero-action replay of the previous version, tools/trace_rollout.py), each hold is
re-planned against the SIMULATED world (owner, 2026-10-23: "the drop shouldn't stop our recipe, it should still go
after the grasp"): if the simulated object is off its reference at the hold start by more than REPLAN_MM / REPLAN_DEG
(public ep18: the brush fell over at f4-8), the hand approaches and grasps it where it lies in the simulation (the
grasp is the same, defined in the object frame) and carries it back onto its reference path over CARRY frames after
closing. The objects' reference trajectories are not changed (the policy is still asked to track them).
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
import grasp_force as gf  # noqa: E402
import wrap_grasp as wg  # noqa: E402
from task_wrench import wrench as task_wrench  # noqa: E402
from hold_phases import hold_phases  # noqa: E402

WRIST_KP, G = float(os.environ.get('GL_WRIST_KP', 25.0)), 9.81   # GL_WRIST_KP: wrist position kp of the embodiment used


def flexion_mask(names):
    return np.array([any(k in n for k in ('_FE', '_PIP', '_DIP', '_IP')) for n in names], float)


def squeeze_weights(names, profile):  # per flexion joint, x the squeeze; 'anatomic' (2026-10-24, docs/research/grasp/
    # human-hand-biomechanics.md: 5-8 N at a fingertip with finger kp 1.7 N m/rad needs dq MCP:PIP:DIP ~ 0.31-0.49 :
    # 0.17-0.27 : 0.08-0.12 rad; a uniform squeeze puts 26 N at the DIP vs 6.5 N at the MCP and curls the tip off a plate)
    if profile != 'anatomic':
        return flexion_mask(names)
    w = {'MCP_FE': 1.0, 'PIP': 0.55, 'DIP': 0.25, 'IP': 0.4, 'CMC_FE': 0.6}
    return np.array([next((v for k, v in w.items() if n.endswith(k)), 0.0) for n in names], float)


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
    p.add_argument('--force_design', type=int, default=0, help='1: squeeze from a per-frame contact-force LP (grasp_force.py)')
    p.add_argument('--sf', type=float, default=gf.SF); p.add_argument('--f_min', type=float, default=gf.F_MIN)
    p.add_argument('--lead', type=int, default=2); p.add_argument('--oblique_deg', type=float, default=0.0)
    p.add_argument('--withdraw', type=float, default=0.06)
    p.add_argument('--palm_clear', type=float, default=wg.CLEAR, help='wrap: palm-handle clearance (m); < 0 presses')
    p.add_argument('--mcp_first', type=int, default=0, help='close MCP/knuckle joints first, IPs second, thumb last')
    p.add_argument('--wrap_where_held', type=int, default=0, help='1: wrap only where the human holds the narrow part '
                   '(MANO contacts); elsewhere (e.g. a spoon bowl) keep the human grasp + squeeze')
    p.add_argument('--snap', type=int, default=0, help='non-wrap grasps: curl each finger from the human pose until it '
                   'touches the object hulls, then squeeze (eval ep35: the copied bowl grasp was 11.5 mm off the bowl)')
    p.add_argument('--sim_trace', default='', help='zero-action trace of the previous version: re-plan holds whose object '
                   'is off its reference at the hold start (see the docstring)')
    p.add_argument('--replan_mm', type=float, default=20.0); p.add_argument('--replan_deg', type=float, default=10.0)
    p.add_argument('--carry', type=int, default=20, help='frames to carry a re-planned object back onto its reference path')
    p.add_argument('--approach_cm', type=float, default=0.0, help='> 0: once the reference hand comes within this distance '
                   '(cm, hand surface to object surface) of the object it will grasp, it follows the backed-off, open '
                   'pre-grasp pose (moving with the object) and slides in over the last BLEND/2 frames (public ep18: the '
                   'reference hand passing 7 cm from the standing brush knocked it over at f24-28)')
    p.add_argument('--approach_back', type=float, default=0.04, help='pre-grasp back-off along the palm normal (m), all grasps')
    p.add_argument('--templates', default='', help='grasp templates JSON (tools/extract_grasp_templates.py): a hold on an object '
                   'with a template, by the template\'s hand, uses its object-frame wrist pose and finger posture (2026-10-24: the '
                   'ep18 0.889 policy\'s dust-pan key pinch and sweeper neck clamp); with --single_hand that hand carries the object')
    p.add_argument('--template_squeeze', type=float, default=0.2, help='templates: extra flexion beyond the (touching) template posture')
    p.add_argument('--squeeze_profile', default='uniform', choices=['uniform', 'anatomic'],
                   help='anatomic: squeeze weighted MCP 1 : PIP 0.55 : DIP 0.25 (thumb CMC 0.6, IP 0.4) instead of equal')
    p.add_argument('--onset_anchor', type=int, default=0, help='1: lock the hand from the object motion onset in OUR reference '
                   '(from its rest pose before the hold) when the hold would start later (2026-10-24: ep39 dust pan lifted '
                   '18 cm, ep18 sweeper 12 cm, ep24 board 10 cm before the human hand track reaches them)')
    p.add_argument('--onset_deg', type=float, default=8.0, help='onset: rotation from rest (deg), besides MOVE_CM')
    p.add_argument('--approach_step', type=float, default=0.03, help='onset anchor: approach length = wrist distance / this (m/frame)')
    p.add_argument('--held_tol', type=float, default=0.08, help='human hold within this distance (m) of the narrow part '
                   'counts as holding the handle (eval ep35: right hand 3-6 cm from it, left hand on the bowl 17-21 cm)')
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
    lim, flex, distal, kpf, thumb, sqw = {}, {}, {}, {}, {}, {}; ke = m.joint_target_ke.numpy()
    for side in cr.SIDES:
        fj = t.column(f'{side}_robot_finger_joint_names')[0].as_py(); flex[side] = flexion_mask(fj); distal[side] = distal_mask(fj)
        sqw[side] = squeeze_weights(fj, a.squeeze_profile)
        kpf[side] = np.array([ke[dstart[jidx[f'{side}_sharpa_wave/{n}']]] for n in fj]); thumb[side] = np.array(['_thumb_' in n for n in fj], float)
        lim[side] = (np.array([lo_lim[dstart[jidx[f'{side}_sharpa_wave/{n}']]] for n in fj]),
                     np.array([hi_lim[dstart[jidx[f'{side}_sharpa_wave/{n}']]] for n in fj]))
    ph = hold_phases(a.inp)[0]['phases']
    TPL = json.load(open(a.templates))['templates'] if a.templates else {}
    parked = []
    if a.single_hand:                                              # one carrier per object, from first grasp to last release
        merged = []
        for o_ in sorted({x['object'] for x in ph}):
            xs = [x for x in ph if x['object'] == o_]
            frames = {sd: sum(x['frames'] for x in xs if x['hand'] == sd) for sd in ('left', 'right')}
            hand = max(frames, key=frames.get); s1_ = max(x['end'] for x in xs)
            if o_ in TPL and frames.get(TPL[o_]['side'], 0) > 0:     # the hand that has a proven grasp for this object
                hand = TPL[o_]['side']
            first = min((x for x in xs if x['hand'] == hand), key=lambda x: x['start'])
            merged.append(dict(first, end=s1_, frames=s1_ - first['start'], merged_from=len(xs)))
        held_by = {x['hand'] for x in merged}; parked = [sd for sd in ('left', 'right') if sd not in held_by]
        ph = merged
        print(f'single-hand carry: {[(x["hand"], x["object"], x["start"], x["end"]) for x in ph]}; parked {parked}', flush=True)
    obj_body = [next(i for i, l in enumerate(blabels) if l.startswith(f'track3_{n}/')) for n in names]
    SIM = {}                                                       # simulated object poses of the previous version
    if a.sim_trace:
        d_ = np.load(a.sim_trace); L_ = [str(x_) for x_ in d_['labels']]; fr_ = np.asarray(d_['frame']).astype(int)
        for j_, n_ in enumerate(names):
            i_ = L_.index(f'track3_{n_}/object'); P_ = np.full((T, 3), np.nan); Q_ = np.full((T, 4), np.nan)
            ok_ = (fr_ >= 0) & (fr_ < T); P_[fr_[ok_]] = d_['q'][ok_, i_, :3]; Q_[fr_[ok_]] = d_['q'][ok_, i_, 3:7]
            SIM[j_] = (P_, Q_)
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
        onset_info = None
        if a.onset_anchor:                                         # the object moves in OUR reference before this hold starts
            pe = max([x2['end'] for x2 in ph if x2['object'] == x['object'] and x2['end'] <= s0], default=0)   # its rest
            d_ = np.linalg.norm(OP[pe:s0, j] - OP[pe, j], axis=1) * 100
            r_ = np.degrees((OR[j][pe:s0] * OR[j][pe].inv()).magnitude()) if s0 > pe else np.zeros(0)
            mv_ = np.nonzero((d_ > a.move_cm) | (r_ > a.onset_deg))[0]
            if len(mv_) and pe + int(mv_[0]) - a.close < h0:       # lock from the onset; the grasp shape stays from f g
                onset = pe + int(mv_[0])
                onset_info = dict(onset=onset, hold_from_before=int(h0), hold_start_phase=int(s0),
                                  travel_cm_at_old_hold=round(float(np.linalg.norm(OP[h0, j] - OP[pe, j]) * 100), 1))
                h0 = max(pe, onset - a.close)
                print(f"{side} {x['object']}: ONSET ANCHOR {json.dumps(onset_info)} -> hold from f{h0}", flush=True)
        Rw_g = Rot.from_quat(qref[g, o + 3:o + 7]); T_ow_p = OR[j][g].inv().apply(qref[g, o:o + 3] - OP[g, j]); R_ow = OR[j][g].inv() * Rw_g
        lo, hi = lim[side]; qf = qref[g, o + 7:o + 29]; qs = np.clip(qf + a.squeeze * flex[side], lo, hi)
        qpre = np.clip(qf - a.preopen * flex[side], lo, hi); back = 0.0; wrap_info = None
        V = hull_vertices(j)
        sv = np.linalg.svd(V - V.mean(0), compute_uv=False)
        held_on_narrow, s_med = True, None
        if a.wrap_where_held:                                      # where does the human hand hold it? (our MANO contacts)
            Pc = np.array(t.column(f'mano_{side}_object_contact_positions')[0].as_py(), float).reshape(T, -1, 3)
            pid = np.array(t.column(f'mano_{side}_object_contact_part_ids')[0].as_py()).reshape(T, -1)
            pts = [OR[j][f].inv().apply(Pc[f][pid[f] == j + 1] - OP[f, j]) for f in range(s0, s1) if (pid[f] == j + 1).any()]
            if pts:
                c0_ = V.mean(0); ax_ = np.linalg.svd(V - c0_, full_matrices=False)[2][0]
                _, _, _, rng_, _ = wg.handle_geometry(V, c0_); s_med = float(np.median((np.vstack(pts) - c0_) @ ax_))
                held_on_narrow = rng_[0] - a.held_tol <= s_med <= rng_[1] + a.held_tol
        if a.wrap and sv[0] / max(sv[1], 1e-9) >= a.wrap_ratio and held_on_narrow:   # elongated: wrap on the handle
            bodies, pb, pl = cr.hand_geometry(m, side); bq = fk(qref[g])
            knuckles = np.mean([bq[bodies[f'{side}_{fn}_PP'], :3] for fn in wg.FINGERS], 0)
            c, ax, r, rng, tpos = wg.handle_geometry(V, OR[j][g].inv().apply(knuckles - OP[g, j]))
            R_ow, T_ow_p = wg.wrap_pose(R_ow, c, ax, r, oblique=np.radians(a.oblique_deg) * (-1 if side == 'right' else 1),
                                        clear=a.palm_clear)
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
        if a.snap and wrap_info is None:                           # snap the human grasp onto the surface (fingers curl to contact)
            if j not in sdf:
                sdf[j] = cr.HullSDF(m, obj_body[j])
            bodies, pb, pl = cr.hand_geometry(m, side); fj = t.column(f'{side}_robot_finger_joint_names')[0].as_py()
            qh = qref[g].copy(); qh[o + 7:o + 29] = np.clip(qf - a.preopen * flex[side], lo, hi)   # from slightly open
            qf, qs, closing = wg.close_fingers(fk, qh, o, side, fj, lo, hi, bodies, pb, pl, sdf[j],
                                               lambda X: OR[j][g].inv().apply(X - OP[g, j]), a.squeeze)
            qpre = np.clip(qf - a.preopen * flex[side], lo, hi)
            print(f"{side} {x['object']}: SNAP human grasp, closing {json.dumps(closing)}", flush=True)
        if a.squeeze_profile != 'uniform':                         # knuckle-heavy squeeze from the touching grasp
            qs = np.clip(qf + (a.wrap_squeeze if wrap_info else a.squeeze) * sqw[side], lo, hi)
        tpl_info = None
        if x['object'] in TPL and TPL[x['object']]['side'] == side:  # a proven grasp from a successful policy
            tp = TPL[x['object']]; fjn = t.column(f'{side}_robot_finger_joint_names')[0].as_py()
            qt = dict(zip(tp['finger_joint_names'], tp['finger_joints']))
            T_ow_p = np.array(tp['wrist_pos_obj'], float); R_ow = Rot.from_quat(tp['wrist_quat_obj_xyzw'])
            qf = np.clip(np.array([qt[n] for n in fjn], float), lo, hi)
            qs = np.clip(qf + a.template_squeeze * sqw[side], lo, hi); qpre = np.clip(qf - a.preopen * flex[side], lo, hi)
            wrap_info = None; back = max(back, a.approach_back)
            tpl_info = dict(template=os.path.basename(a.templates), frame=tp['frame'], squeeze=a.template_squeeze)
            print(f"{side} {x['object']}: TEMPLATE grasp {json.dumps(tpl_info)}", flush=True)
        QS = np.repeat(qs[None], T, 0); fd_info = None; d_obj = None
        if a.force_design:                                         # physics-aware squeeze (grasp_force.py)
            if j not in sdf:
                sdf[j] = cr.HullSDF(m, obj_body[j])
            bodies, pb, pl = cr.hand_geometry(m, side)
            qg = qref[g].copy(); qg[o:o + 3] = OR[j][g].apply(T_ow_p) + OP[g, j]; qg[o + 3:o + 7] = (OR[j][g] * R_ow).as_quat()
            qg[o + 7:o + 29] = qf; con = gf.find_contacts(fk(qg), side, bodies, pb, pl, sdf[j], OR[j][g], OP[g, j])
            Jc = gf.contact_jacobians(fk, qg, o, con, OR[j][g]) if con else None
            com = m.body_com.numpy()[obj_body[j]].astype(float); Ib = np.diag(m.body_inertia.numpy()[obj_body[j]]).astype(float)
            tw = task_wrench(OP[:, j], OR[j].as_quat(), mass[j], Ib, 20.0, com=com)          # reference rows at 20 fps
            fdz = gf.ForceDesign(con, Jc, com, kpf[side], np.maximum(hi - qf, 0), np.maximum(qf - lo, 0), sf=a.sf, f_min=a.f_min) if len(con) >= 2 else None
            tau = np.full((T, 22), np.nan); fn = np.full(T, np.nan); bad = 0
            for f in range(h0, s1):
                if fdz is None:
                    break
                share = in_air[f, j] / max(1.0, n_hold[f, j])          # on the table the support carries the load
                W = np.r_[OR[j][f].inv().apply(tw['F'][f]), OR[j][f].inv().apply(tw['tau'][f])] * share
                lam, tq = fdz.solve(W)
                if lam is None:
                    bad += 1; continue
                tau[f] = tq; fn[f] = fdz.normal_forces(lam).sum()
            ok = ~np.isnan(tau[:, 0])
            if fdz is not None and ok.any():
                idx = np.nonzero(ok)[0]
                for k_ in range(22):                                   # fill infeasible frames, then lead + smooth
                    tau[h0:s1, k_] = np.interp(np.arange(h0, s1), idx, tau[idx, k_])
                tl = np.array([tau[f:min(s1, f + a.lead + 1)].max(0) for f in range(h0, s1)])
                tl = np.array([tl[max(0, i - 1):i + 2].mean(0) for i in range(len(tl))])
                QS[h0:s1] = np.clip(qf + tl / np.maximum(kpf[side], 1e-6), lo, hi)
            fd_info = dict(contacts=[(c_['link'], c_['gap_mm']) for c_ in con], infeasible_frames=int(bad),
                           normal_force_total_N=[round(float(np.nanpercentile(fn, q_)), 2) for q_ in (5, 50, 95)] if ok.any() else None,
                           squeeze_rad_max=[round(float(x_), 3) for x_ in (QS[h0:s1] - qf).max(0)] if ok.any() else None,
                           joints_at_limit=int(((QS[h0:s1] >= hi - 1e-6) & (QS[h0:s1] - qf > 1e-4)).any(0).sum()))
            qo_ = qg.copy(); qo_[o + 7:o + 29] = qpre                   # release direction from the OPENED hand
            Xo = OR[j][g].inv().apply(cr.world_points(fk(qo_), pb, pl) - OP[g, j]); near = sdf[j](Xo) < 0.015
            if near.any():
                d_obj, s_sep = gf.separating_direction(sdf[j].grad(Xo[near]))
                fd_info.update(separating_dir_obj=[round(float(x_), 3) for x_ in d_obj], separating_margin=round(float(s_sep), 3))
                if s_sep <= 0.05:
                    d_obj = None
            print(f"{side} {x['object']}: FORCE DESIGN {json.dumps(fd_info)}", flush=True)
        OPh, ORh, replan = OP[:, j], OR[j], None                    # the object path the hand follows
        fa = max(0, h0 - a.blend - 2)                              # before the previous version's hand got there (ep18: its
        if j in SIM and not np.isnan(SIM[j][0][fa]).any():         # approach pushed the fallen brush at f43-51)
            sp, sq = SIM[j][0][fa], SIM[j][1][fa]
            dpos = float(np.linalg.norm(sp - OP[fa, j])); drot = float(np.degrees((Rot.from_quat(sq) * OR[j][fa].inv()).magnitude()))
            if dpos * 1000 > a.replan_mm or drot > a.replan_deg:  # off its reference: go for it where it lies, carry it back
                c0 = h0 + a.close; OPh = OP[:, j].copy(); qh_ = OR[j].as_quat().copy()
                for f in range(T):
                    if f < c0:
                        OPh[f] = sp; qh_[f] = sq
                    elif f < c0 + a.carry:
                        w_ = (f - c0 + 1) / (a.carry + 1); OPh[f] = (1 - w_) * sp + w_ * OP[f, j]
                        qh_[f] = Slerp([0, 1], Rot.from_quat([sq, OR[j][f].as_quat()]))([w_]).as_quat()[0]
                ORh = Rot.from_quat(qh_)
                replan = dict(seen_at_frame=int(fa), hold_from=int(h0), off_cm=round(100 * dpos, 1), off_deg=round(drot, 1), carry_back=[int(c0), int(c0 + a.carry)])
                print(f"{side} {x['object']}: REPLAN against the simulation {json.dumps(replan)}", flush=True)
        a0 = max(0, h0 - a.blend); appr = None
        if a.approach_cm > 0:                                      # early approach: no sweep through the object
            back = max(back, a.approach_back)
            if j not in sdf:
                sdf[j] = cr.HullSDF(m, obj_body[j])
            bodies_, pb_, pl_ = cr.hand_geometry(m, side)
            prev_end = max([min(T, x2['end'] + 4 * a.open) for x2 in ph if x2['hand'] == side and x2['end'] <= s0], default=0)
            for f in range(max(prev_end, h0 - 60), a0):
                Xh = OR[j][f].inv().apply(cr.world_points(fk(qref[f]), pb_, pl_) - OP[f, j])
                if sdf[j](Xh).min() < a.approach_cm / 100:
                    a0 = f; break
            appr = dict(from_frame=int(a0), hold_from=int(h0), back_cm=round(100 * back, 1))
        n_in, n_slide = max(1, a.blend // 2), max(1, a.blend // 2)
        if onset_info is not None:                                 # the human hand track is still far: a long enough approach
            back = max(back, a.approach_back)
            prev_end = max([min(T, x2['end'] + 4 * a.open) for x2 in ph if x2['hand'] == side and x2['end'] <= s0], default=0)
            dist = float(np.linalg.norm(qref[max(0, h0 - a.blend), o:o + 3] - (ORh[h0].apply(T_ow_p) + OPh[h0])))
            n_app = int(np.clip(np.ceil(dist / a.approach_step), a.blend, 40))
            a0 = max(prev_end, min(a0, h0 - n_app)); n_in = max(n_in, (h0 - a0) - n_slide)
            appr = dict(from_frame=int(a0), hold_from=int(h0), back_cm=round(100 * back, 1), dist_cm=round(100 * dist, 1), onset_anchor=True)
            onset_info.update(approach_from=int(a0), approach_dist_cm=round(100 * dist, 1))
        x_back = lambda f: (ORh[f] * R_ow).apply([-back, 0.0, 0.0])  # noqa: E731  palm backed off along -x (hand frame)
        for f in range(a0, h0):
            if appr is None:                                       # approach: blend into the (backed-off) pose, then slide in
                wb = (f - a0 + 1) / (a.blend + 1); w_in, w_rot = min(1.0, 2 * wb), wb
                w_back = 1.0 if wb < 0.5 else 2 * (1 - wb)          # backed off in the first half, slid in over the second
            else:                                                  # early approach: into the backed-off open pose, follow the
                w_in = w_rot = min(1.0, (f - a0 + 1) / (n_in + 1))  # object, slide in over the last N_SLIDE frames
                w_back = 1.0 - float(np.clip((n_slide - (h0 - f) + 1) / n_slide, 0.0, 1.0))
            pos = ORh[f].apply(T_ow_p) + OPh[f] + x_back(f) * w_back
            rot = ORh[f] * R_ow
            q_new[f, o:o + 3] = blend(qref[f, o:o + 3], pos, w_in)
            q_new[f, o + 3:o + 7] = Slerp([0, 1], Rot.from_quat([qref[f, o + 3:o + 7], rot.as_quat()]))([w_rot]).as_quat()[0]
            q_new[f, o + 7:o + 29] = blend(qref[f, o + 7:o + 29], qpre, w_rot)
        end = min(T, s1 + 4 * a.open)                             # release: relax, unroll (OPEN frames each), withdraw (2 x OPEN)
        for f in range(h0, end):
            pos = ORh[f].apply(T_ow_p) + OPh[f]; rot = ORh[f] * R_ow
            wc = min(1.0, (f - h0 + 1) / a.close)                  # finger closing ramp (from pre-open)
            if a.lift and f < s1:                                  # weight shared by the hands holding it, while in the air
                lift[side][f] = max(lift[side][f], in_air[f, j] * mass[j] * G / WRIST_KP / max(1.0, n_hold[f, j]))
            if f < s1:                                             # hold: locked grasp, fingers closing then held
                q_new[f, o:o + 3] = pos; q_new[f, o + 3:o + 7] = rot.as_quat()
                if a.mcp_first:                                     # anatomy: MCP first, then the IPs, thumb last (IP-first
                    wv = np.where(thumb[side] > 0, np.clip(2 * wc - 1, 0, 1),   # "roll-up" pushes objects out of the palm,
                                  np.where(distal[side] > 0, np.clip(2 * wc - 1, 0, 1), min(1.0, 2 * wc)))  # Muzykewicz 2013)
                    q_new[f, o + 7:o + 29] = blend(qpre, QS[f], wv)
                else:
                    q_new[f, o + 7:o + 29] = blend(qpre, QS[f], wc)
            else:                                                  # release (eval ep35: opening all joints at once hooked and
                k = f - s1 + 1                                     # flicked the spoon up, f396; sliding off along the handle
                wo = min(1.0, k / a.open)                          # with the fingers still wrapped dragged it away, f404)
                wu = float(np.clip((k - a.open) / a.open, 0, 1))   # 1) relax to the touching grasp, wrist locked
                ww = max(0.0, (k - 2 * a.open) / max(1, end - s1 - 2 * a.open))   # 2) unroll: PIP/DIP/IP first, then the
                wj = np.minimum(1.0, 2 * wu) * distal[side] + np.clip(2 * wu - 1, 0, 1) * (1 - distal[side])  # knuckles
                qo = blend(qf, qpre, wj)                           # 3) withdraw along the palm normal, then to the reference
                away = pos + (ORh[f].apply(d_obj * a.withdraw) if d_obj is not None else
                              (ORh[f] * R_ow).apply([-max(back, 0.04), 0.0, 0.0])) * min(1.0, 2 * ww)
                q_new[f, o:o + 3] = away if ww < 0.5 else blend(away, qref[f, o:o + 3], 2 * ww - 1)
                q_new[f, o + 3:o + 7] = Slerp([0, 1], Rot.from_quat([rot.as_quat(), qref[f, o + 3:o + 7]]))([max(0.0, 2 * ww - 1)]).as_quat()[0]
                q_new[f, o + 7:o + 29] = blend(QS[s1 - 1], qf, wo) if wu == 0 else blend(qo, qref[f, o + 7:o + 29], ww)
        report.append(dict(x, grasp_frame=int(g), hold_from=int(h0), move_frame=int(move), fingers_on=n_on, wrap=wrap_info, force_design=fd_info, replan=replan, approach=appr, onset_anchor=onset_info, template=tpl_info,
                           human_hold_axis_cm=None if s_med is None else round(100 * s_med, 1),
                           grasp_gap_mm=round(1000 * gap, 1), squeeze_rad=a.squeeze, mass_kg=round(mass[j], 3),
                           lift_cm=round(100 * mass[j] * G / WRIST_KP, 1) if a.lift else 0.0,
                           joints_at_limit_after_squeeze=int(((qs >= hi - 1e-6) & (flex[side] > 0)).sum())))
        if wrap_info:
            print(f"{side} {x['object']}: WRAP grasp {json.dumps(wrap_info)}", flush=True)
        print(f"{side} {x['object']} {s0}-{s1}: {'WRAP' if wrap_info else 'human grasp'} (human holds at axis "
              f"{None if s_med is None else round(100 * s_med, 1)} cm), grasp pose from f{g} ({n_on} fingers on, mean gap {1000 * gap:.1f} mm), "
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
