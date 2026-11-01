"""Repair (b) "no mover, no motion" for a reference parquet (2026-11-01, GT-free; docs/research/grasp-ep13-20261101 §8).

Perception writes object motion that no hand produces: eval 32's blue cup swings ~15 cm sideways inside a left-hand hold
and jumps back at 322 cm/s (perfect-following session, H5p7); objects drift or keep moving after release. A physically
possible object track moves only while something moves it.
  - Holds come from pipeline/hold_phases.py (MANO contact labels + object displacement; our reference only).
  - Inside a hold, the object pose is expressed in the perceived human wrist frame (MANO joint 0 position and
    orientation, mano_<side>_joints / mano_<side>_joints_wxyz: the hand perception saw, not the robot target that a grasp
    lock may already have tied to the object). The relative translation is Hampel-filtered (glitch rejection: median /
    MAD over a window), then smoothed with a centred moving median; the relative rotation with an outlier-rejected
    rotation mean over the same window (a firm grasp is near-rigid). The pose is recomposed with the wrist and blended
    with the input over BLEND frames at each hold edge. Where two hands hold at once (a hand-over), the first phase is
    used before the overlap's midpoint and the second after it.
  - Outside holds (--rest freeze, default), the object is held at its settled pose: the median pose of the REST_WIN
    frames that follow a release (or of the first REST_WIN frames before the first hold), blended over BLEND frames.
    --rest keep leaves rest frames unchanged; frames where the input moves more than FLAG_CM outside any hold are
    reported either way (they may be real pushes the contact labels missed: the public gate decides).
Only object_body_position / object_body_wxyz change. Apply it to a reference BEFORE the grasp lock (the lock builds the
robot hand targets from the object track), then rebuild the lock. No ground truth is read.
Usage: python hold_filter.py IN.parquet OUT.parquet [--win 15] [--hampel 3] [--glitch_cm 5] [--blend 4] [--rest freeze|keep]
       [--rest_win 10] [--flag_cm 3] [--objects a,b]   (writes OUT_hold_filter.json)
"""
import argparse, json, os, sys

import numpy as np
from scipy.spatial.transform import Rotation as R

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from hold_phases import hold_phases, POST  # noqa: E402


def rot_wxyz(q):
    return R.from_quat(np.asarray(q, float)[..., [1, 2, 3, 0]])


def hampel(x, k, nsig):
    """Replace outliers of x (T, D) by the window median (per row distance to the median > nsig * 1.4826 MAD)."""
    T = len(x); y = x.copy(); n_out = 0
    for t in range(T):
        a, b = max(0, t - k), min(T, t + k + 1); med = np.median(x[a:b], 0)
        d = np.linalg.norm(x[a:b] - med, axis=1); mad = 1.4826 * np.median(d) + 1e-4
        if np.linalg.norm(x[t] - med) > nsig * mad:
            y[t] = med; n_out += 1
    return y, n_out


def smooth_rel(Pr, Rr, win, nsig, glitch_m=0.05):
    """Relative translations (T, 3) and rotations (Rotation, T) -> filtered (T, 3), Rotation (T).
    Stage 1 (rigid-grasp prior over the whole hold): frames whose relative position is more than GLITCH_M from the hold's
    median are glitches (a moving median cannot reject a glitch longer than half its window; eval 32's lasts 18 frames);
    they are replaced by linear interpolation of the remaining frames (their rotations by the nearest kept frame).
    Stage 2: Hampel + centred moving median (WIN) on the translation, outlier-rejected rotation mean on the rotation."""
    k = win // 2; T = len(Pr)
    bad = np.linalg.norm(Pr - np.median(Pr, 0), axis=1) > glitch_m
    if bad.any() and (~bad).sum() >= 2:
        good = np.nonzero(~bad)[0]; Pr = Pr.copy()
        for d in range(3):
            Pr[bad, d] = np.interp(np.nonzero(bad)[0], good, Pr[good, d])
        near = good[np.abs(good[None, :] - np.arange(T)[:, None]).argmin(1)]
        Rr = Rr[near]
    P1, n_out = hampel(Pr, k, nsig); n_out += int(bad.sum())
    P2 = np.array([np.median(P1[max(0, t - k):min(T, t + k + 1)], 0) for t in range(T)])
    out = []
    for t in range(T):
        a, b = max(0, t - k), min(T, t + k + 1); W = Rr[a:b]; m = W.mean()
        ang = (W * m.inv()).magnitude(); keep = ang <= max(nsig * 1.4826 * np.median(ang), np.radians(2.0))
        out.append(W[keep].mean() if keep.any() else m)
    return P2, R.concatenate(out), n_out


def movmed(X, k):
    T = len(X); return np.array([np.median(X[max(0, t - k):min(T, t + k + 1)], 0) for t in range(T)])


def object_glitches(OP, win, dist_m, vmax_m, phases=(), wrists=None):
    """Frames where the object's OWN track makes an excursion no mover explains: further than DIST_M from its centred
    moving median over WIN frames (a long window, so a glitch shorter than WIN/2 cannot move the median) AND, inside a
    hold, its position relative to the holding (MANO) wrist also departs from its own moving median by DIST_M (the hand
    did not go along: eval 32's cup swings 15 cm while the wrist stays). A genuine carry or lift moves with the hand and
    passes; an accurate object track (public ep13) with a noisy hand track passes. Far runs are widened to the velocity
    spikes (> VMAX_M per frame) that bound them (eval 32 jumps back at 322 cm/s)."""
    T = len(OP); k = win // 2
    far = np.linalg.norm(OP - movmed(OP, k), axis=1) > dist_m
    for side, s0, s1 in phases:
        if wrists is None or s1 - s0 < 3:
            continue
        wp, wr = wrists[side]; fr = np.arange(s0, s1); rel = wr[fr].inv().apply(OP[fr] - wp[fr])
        far[fr] &= np.linalg.norm(rel - movmed(rel, k), axis=1) > dist_m
    v = np.r_[0.0, np.linalg.norm(np.diff(OP, axis=0), axis=1)]; spike = v > vmax_m
    bad = far.copy()
    for s0, s1 in runs(far):                               # widen a far run to the velocity spikes that bound it
        a0 = s0
        while a0 > 0 and spike[a0]:
            a0 -= 1
        b0 = s1
        while b0 < T and spike[b0]:
            b0 += 1
        bad[a0:b0] = True
    return bad


def fill_glitches(OP, Rin, bad, phases, wrists):
    """Replace glitch frames: inside a hold, by interpolating the hand-relative pose of the good frames around the gap
    (the object moves with the hand across it); elsewhere by interpolating the world pose. Good frames are untouched."""
    T = len(OP); P = OP.copy(); Q = Rin.as_quat().copy(); good = np.nonzero(~bad)[0]
    if len(good) < 2:
        return P, Q
    hold_side = np.full(T, '', dtype=object)
    for side, s0, s1 in phases:
        hold_side[s0:s1] = side
    for s0, s1 in runs(bad):
        g0 = good[good < s0]; g1 = good[good >= s1]
        if not len(g0) or not len(g1):                     # at an episode end: hold the nearest good pose
            src = g0[-1] if len(g0) else g1[0]; P[s0:s1] = OP[src]; Q[s0:s1] = Rin[src].as_quat(); continue
        a0, b0 = g0[-1], g1[0]; side = hold_side[a0] if hold_side[a0] == hold_side[b0] else ''
        lam = (np.arange(s0, s1) - a0) / float(b0 - a0)
        if side:
            wp, wr = wrists[side]
            pa, pb = wr[a0].inv().apply(OP[a0] - wp[a0]), wr[b0].inv().apply(OP[b0] - wp[b0])
            ra, rb = wr[a0].inv() * Rin[a0], wr[b0].inv() * Rin[b0]
            for i, t in enumerate(range(s0, s1)):
                rel = R.from_quat([ra.as_quat(), rb.as_quat()]).mean(weights=[1 - lam[i], lam[i]])
                P[t] = wp[t] + wr[t].apply((1 - lam[i]) * pa + lam[i] * pb); Q[t] = (wr[t] * rel).as_quat()
        else:
            for i, t in enumerate(range(s0, s1)):
                P[t] = (1 - lam[i]) * OP[a0] + lam[i] * OP[b0]
                Q[t] = R.from_quat([Rin[a0].as_quat(), Rin[b0].as_quat()]).mean(weights=[1 - lam[i], lam[i]]).as_quat()
    return P, Q


def repair_object(OP, Rin, phases, wrists, a):
    """Minimal-change repair (default mode): fill the object's own glitches; at rest outside holds, freeze motion below
    REST_CM (jitter) at the settled pose and only FLAG larger motion (it may be a real push the contact labels missed)."""
    T = len(OP); bad = object_glitches(OP, a.gwin, a.glitch_cm / 100.0, a.vmax_cms / 100.0 / a.fps, phases, wrists)
    P, Q = fill_glitches(OP, Rin, bad, phases, wrists); info = dict(glitch_frames=int(bad.sum()),
        glitch_runs=[(int(s0), int(s1)) for s0, s1 in runs(bad)], rest=[])
    held = np.zeros(T, bool)
    for _, s0, s1 in phases:
        held[s0:s1] = True
    Rf = R.from_quat(Q)
    for s0, s1 in runs(~held):
        a0 = 0 if s0 == 0 else min(s0 + POST, s1 - 1); ref_fr = np.arange(a0, min(s1, a0 + a.rest_win))
        Pm = np.median(P[ref_fr], 0); moved = 100 * float(np.linalg.norm(P[s0:s1] - Pm, axis=1).max())
        frozen = moved <= a.rest_cm and a.rest == 'freeze'
        if frozen:
            P[s0:s1] = Pm; Q[s0:s1] = Rf[ref_fr].mean().as_quat()
        info['rest'].append(dict(start=int(s0), end=int(s1), moved_cm=round(moved, 1), frozen=bool(frozen), flag=bool(moved > a.flag_cm)))
    shift = 100 * np.linalg.norm(P - OP, axis=1)
    info.update(changed_frames=int((shift > 1e-6).sum() + 0), max_shift_cm=round(float(shift.max()), 2))
    return P, Q[:, [3, 0, 1, 2]], info


def filter_object(OP, Rin, phases, wrists, a):
    """OP (T, 3), Rin Rotation (T); phases [(hand, start, end)]; wrists {side: (pos (T, 3), Rotation (T))}."""
    T = len(OP); P = OP.copy(); Q = Rin.as_quat().copy(); w_in = np.zeros(T)   # w_in: weight of the filtered value
    held = np.zeros(T, bool); owner = np.full(T, -1); info = dict(phases=[], rest=[])
    for i, (side, s0, s1) in enumerate(phases):            # hand-over overlaps: split at the midpoint
        for t in range(s0, s1):
            if owner[t] < 0:
                owner[t] = i
            else:
                j = owner[t]; mid = (max(phases[j][1], s0) + min(phases[j][2], s1)) / 2.0
                if t >= mid:
                    owner[t] = i
    for i, (side, s0, s1) in enumerate(phases):
        fr = np.nonzero(owner == i)[0]
        if len(fr) < 3:
            continue
        wp, wr = wrists[side]; Wr = wr[fr]
        Pr = Wr.inv().apply(OP[fr] - wp[fr]); Rr = Wr.inv() * Rin[fr]
        P2, R2, n_out = smooth_rel(Pr, Rr, a.win, a.hampel, a.glitch_cm / 100.0)
        Pf = wp[fr] + Wr.apply(P2); Rf = Wr * R2
        P[fr], Q[fr] = Pf, Rf.as_quat(); held[fr] = True
        dev = np.linalg.norm(Pf - OP[fr], axis=1)
        info['phases'].append(dict(hand=side, start=int(fr[0]), end=int(fr[-1]) + 1, glitch_frames=int(n_out),
                                   max_shift_cm=round(100 * float(dev.max()), 1), mean_shift_cm=round(100 * float(dev.mean()), 2)))
    if a.rest == 'freeze':                                 # rest windows: hold the settled pose
        for s0, s1 in runs(~held):
            if s0 == 0:                                    # before the first hold (or no hold): the first REST_WIN frames
                ref_fr = np.arange(0, min(s1, a.rest_win))
            else:                                          # after a release: the frames once it has settled
                a0 = min(s0 + POST, s1 - 1); ref_fr = np.arange(a0, min(s1, a0 + a.rest_win))
            Pm = np.median(OP[ref_fr], 0); Rm = Rin[ref_fr].mean()
            P[s0:s1] = Pm; Q[s0:s1] = Rm.as_quat()
            moved = 100 * float(np.linalg.norm(OP[s0:s1] - Pm, axis=1).max())
            info['rest'].append(dict(start=int(s0), end=int(s1), moved_in_input_cm=round(moved, 1), flag=bool(moved > a.flag_cm)))
    else:
        for s0, s1 in runs(~held):
            moved = 100 * float(np.linalg.norm(OP[s0:s1] - OP[s0], axis=1).max())
            info['rest'].append(dict(start=int(s0), end=int(s1), moved_in_input_cm=round(moved, 1), flag=bool(moved > a.flag_cm)))
    # blend at every boundary between filtered segments and their neighbours (and the input at the episode ends)
    out_P, out_R = P.copy(), R.from_quat(Q)
    changed = np.any(np.abs(P - OP) > 0, 1) | np.any(np.abs(Q - Rin.as_quat()) > 0, 1)
    for t in range(1, T):
        if held[t] != held[t - 1]:                         # hold edge: ramp from the previous segment's value
            for k in range(1, a.blend + 1):
                u = t - 1 + k
                if u >= T:
                    break
                lam = k / (a.blend + 1.0)
                out_P[u] = (1 - lam) * P[t - 1] + lam * P[u]
                out_R = _set(out_R, u, R.from_quat([Q[t - 1], Q[u]]).mean(weights=[1 - lam, lam]))
    info['changed_frames'] = int(changed.sum())
    q = out_R.as_quat()[:, [3, 0, 1, 2]]
    return out_P, q, info


def _set(rots, i, r):
    q = rots.as_quat(); q[i] = r.as_quat(); return R.from_quat(q)


def runs(mask):
    m = np.concatenate([[0], np.asarray(mask, int), [0]]); d = np.diff(m)
    return list(zip(np.nonzero(d == 1)[0], np.nonzero(d == -1)[0]))


def main():
    import pyarrow as pa, pyarrow.parquet as pq
    p = argparse.ArgumentParser(); p.add_argument('inp'); p.add_argument('out')
    p.add_argument('--win', type=int, default=15); p.add_argument('--hampel', type=float, default=3.0)
    p.add_argument('--blend', type=int, default=4); p.add_argument('--rest', default='freeze', choices=('freeze', 'keep'))
    p.add_argument('--rest_win', type=int, default=10); p.add_argument('--flag_cm', type=float, default=3.0)
    p.add_argument('--glitch_cm', type=float, default=5.0, help='hold-wide rigid-grasp glitch threshold on the hand-relative position')
    p.add_argument('--objects', default='', help='only these objects (default: all)')
    p.add_argument('--mode', default='glitch', choices=('glitch', 'rigid'), help='glitch (default, minimal change): fill '
                   'the object track own glitches, freeze rest jitter; rigid: tie the object to the MANO wrist in every hold '
                   '(1 Nov: worse on public ep13, where the hand track, not the object track, is off; kept for comparison)')
    p.add_argument('--gwin', type=int, default=61); p.add_argument('--vmax_cms', type=float, default=150.0)
    p.add_argument('--rest_cm', type=float, default=1.5, help='glitch mode: rest motion up to this is frozen jitter')
    p.add_argument('--fps', type=float, default=20.0)
    a = p.parse_args()
    t = pq.read_table(a.inp); g = lambda c: t.column(c)[0].as_py()  # noqa: E731
    names = g('object_body_names'); B = len(names); T = len(g('robot_left_wrist_position'))
    shp_p, shp_q = np.array(g('object_body_position')).shape, np.array(g('object_body_wxyz')).shape
    OP = np.array(g('object_body_position'), float).reshape(T, B, 3); OQ = np.array(g('object_body_wxyz'), float).reshape(T, B, 4)
    wrists = {s: (np.array(g(f'mano_{s}_joints'), float).reshape(T, -1, 3)[:, 0],
                  rot_wxyz(np.array(g(f'mano_{s}_joints_wxyz'), float).reshape(T, -1, 4)[:, 0])) for s in ('left', 'right')}
    hp, _ = hold_phases(a.inp); want = [x for x in a.objects.split(',') if x] or names
    P2, Q2 = OP.copy(), OQ.copy(); info = dict(inp=os.path.abspath(a.inp), args=vars(a), objects={})
    for j, n in enumerate(names):
        if n not in want:
            continue
        ph = [(x['hand'], x['start'], x['end']) for x in hp['phases'] if x['object'] == n]
        Rin = rot_wxyz(OQ[:, j])
        fn = repair_object if a.mode == 'glitch' else filter_object
        P2[:, j], q, inf = fn(OP[:, j], Rin, ph, wrists, a)
        q[np.sum(q * OQ[:, j], 1) < 0] *= -1.0
        Q2[:, j] = q; info['objects'][n] = inf
    ip, iq = t.column_names.index('object_body_position'), t.column_names.index('object_body_wxyz')
    t2 = t.set_column(ip, 'object_body_position', pa.array([P2.reshape(shp_p).tolist()], type=t.schema.field(ip).type))
    t2 = t2.set_column(iq, 'object_body_wxyz', pa.array([Q2.reshape(shp_q).tolist()], type=t.schema.field(iq).type))
    pq.write_table(t2, a.out)
    json.dump(info, open(os.path.splitext(a.out)[0] + '_hold_filter.json', 'w'), indent=1)
    for n, d in info['objects'].items():
        if a.mode == 'glitch':
            print(f"{n}: glitch runs {d['glitch_runs']} | rest {[(x['start'], x['end'], x['moved_cm']) + (('frozen',) if x['frozen'] else ()) + (('FLAG',) if x['flag'] else ()) for x in d['rest']]} | changed {d['changed_frames']} frames, max shift {d['max_shift_cm']} cm")
            continue
        print(f"{n}: holds {[(x['hand'][0], x['start'], x['end'], x['glitch_frames'], x['max_shift_cm']) for x in d['phases']]} "
              f"| rest {[(x['start'], x['end'], x['moved_in_input_cm']) + (('FLAG',) if x['flag'] else ()) for x in d['rest']]} "
              f"| changed {d['changed_frames']}")


if __name__ == '__main__':
    main()
