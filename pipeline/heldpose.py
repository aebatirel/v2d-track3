"""Refine step S10 (31 Oct 2026, perception sprint "heldpose") [H until its public gate]: held objects posed by our
perceived palm frame times a constant per-hold grasp transform. GROUND-TRUTH-FREE: it reads only our track, our hands
(hands_refined.npz: joints_<side>, measured_<side>, KR) and our meshes, all through refine's checked inputs.

Hypothesis [H-HP]: while an object is held, wrist x G (G estimated at hold onset from the tracker) poses it better
than the tracker under occlusion (thin objects: the spoon, the sweeper, the dust pan).
Pre-registration and results: docs/research/work/perception-sprint-20261031/heldpose/README.md.

Per object (S10 runs after S2 in refine's STEP_ORDER, because the hands are not time-shifted):
  palm frame  W(t) per hand: origin = mean of MediaPipe joints 0, 5, 9, 13, 17; x = 0 -> 9; z = normal of
              (5 - 0) x (17 - 0), orthogonalised; smoothed over a centred SMOOTH-frame window of measured frames (median
              position, chordal mean rotation, members > TRIM deg from the first mean dropped).
  contact     d(t) = nearest of the 21 measured joints to our mesh surface (600 samples) at the tracked pose.
  holds       runs of d < CONTACT cm, gaps <= BRIDGE frames bridged, >= MIN_LEN frames, with co-motion: the palm origin
              and the object's tracked centroid each travel >= CARRY cm (max distance from the run's first frame).
              Longer runs claim frames first: one hand per object per frame.
  visibility  v = share of the surface samples that do not project (KR, world_T_cam) behind a measured hand's image
              region (bones as RADIUS capsules, the palm polygon of joints 0, 1, 5, 9, 13, 17). Self-occlusion and
              other objects are not modelled.
  grasp       G = mean of inv(W(t)) O(t) (chordal mean rotation, median translation) over the hold's first ONSET
              measured frames whose visibility at the tracked pose is >= VIS_G (fewer than 3: the 5 most visible of
              its first 2*ONSET measured frames). P(t) = W(t) G; W is screw-interpolated over unmeasured hold frames.
  modes       gate     (primary) O'(t) = O(t) (inv O(t) P(t))^w, w = clip((VIS_HI - v_P) / (VIS_HI - VIS_LO), 0, 1),
                       v_P = visibility at the predicted pose (interpolated on unmeasured frames), SMOOTH-frame mean;
              replace  w = 1 on the hold (ungated; the direct test of [H-HP]);
              trans    rotation kept from the tracker; translation so that the palm origin keeps its onset position in
                       the object frame (ungated; palm orientation unused).
              Every mode ramps w in and out over RAMP frames at the hold's ends. Frame 0 is never changed.
"""
import numpy as np

PALM = [0, 5, 9, 13, 17]
PALM_POLY = [0, 1, 5, 9, 13, 17]
BONES = [(0, 1), (1, 2), (2, 3), (3, 4), (0, 5), (5, 6), (6, 7), (7, 8), (5, 9), (9, 10), (10, 11), (11, 12), (9, 13),
         (13, 14), (14, 15), (15, 16), (13, 17), (17, 18), (18, 19), (19, 20), (0, 17)]


# ------------------------------------------------------------------ rotations
def _R():
    from scipy.spatial.transform import Rotation
    return Rotation


def robust_mean_rot(Rs, trim_deg):
    """Chordal L2 mean of (n,3,3); members more than TRIM_DEG from the first mean dropped (if >= half remain)."""
    Rot = _R()
    R = Rot.from_matrix(np.asarray(Rs))
    m = R.mean()
    if len(Rs) > 2:
        d = np.degrees((R * m.inv()).magnitude())
        keep = d <= trim_deg
        if keep.sum() >= max(2, (len(Rs) + 1) // 2) and not keep.all():
            m = R[keep].mean()
    return m.as_matrix()


def palm_frames(J):
    """(T,21,3) world joints -> (T,4,4) raw palm frames."""
    J = np.asarray(J, float)
    p0, p5, p9, p17 = J[:, 0], J[:, 5], J[:, 9], J[:, 17]
    x = p9 - p0
    x /= np.maximum(np.linalg.norm(x, axis=1, keepdims=True), 1e-9)
    n = np.cross(p5 - p0, p17 - p0)
    n /= np.maximum(np.linalg.norm(n, axis=1, keepdims=True), 1e-9)
    z = n - (n * x).sum(1, keepdims=True) * x
    z /= np.maximum(np.linalg.norm(z, axis=1, keepdims=True), 1e-9)
    y = np.cross(z, x)
    W = np.tile(np.eye(4), (len(J), 1, 1))
    W[:, :3, 0], W[:, :3, 1], W[:, :3, 2] = x, y, z
    W[:, :3, 3] = J[:, PALM].mean(1)
    return W


def smooth_frames(W, M, smooth=5, trim_deg=20.0):
    """Centred SMOOTH-frame robust smoothing of the palm frames over measured frames (unmeasured frames unchanged)."""
    T = len(W)
    h = smooth // 2
    out = W.copy()
    for t in np.nonzero(M)[0]:
        k = [i for i in range(max(0, t - h), min(T, t + h + 1)) if M[i]]
        if len(k) < 2:
            continue
        out[t, :3, :3] = robust_mean_rot(W[k, :3, :3], trim_deg)
        out[t, :3, 3] = np.median(W[k, :3, 3], axis=0)
    return out


# ------------------------------------------------------------------ geometry
def contact_cm(O, S, J, M):
    """(T,) cm: nearest measured joint of ONE hand to the surface samples S posed by O (inf when not measured)."""
    from scipy.spatial import cKDTree
    T = len(O)
    d = np.full(T, np.inf)
    for t in np.nonzero(M)[0]:
        X = S @ O[t, :3, :3].T + O[t, :3, 3]
        d[t] = float(cKDTree(X).query(J[t])[0].min()) * 100
    return d


def _in_convex(P2, Q2):
    """Points P2 (n,2) inside the convex hull of Q2 (k,2)."""
    from scipy.spatial import ConvexHull
    try:
        h = ConvexHull(Q2)
    except Exception:  # noqa: BLE001  (degenerate polygon)
        return np.zeros(len(P2), bool)
    return (P2 @ h.equations[:, :2].T + h.equations[:, 2] <= 0).all(axis=1)


def occluded_by_hand(Xc, Jc, KR, radius=0.01):
    """Bool (n,): camera-frame points Xc behind the image region of one hand Jc (21,3) (camera frame, z forward)."""
    z = Xc[:, 2]
    ok = z > 1e-3
    uv = (Xc[:, :2] / np.maximum(z, 1e-3)[:, None]) * np.diag(KR)[:2] + KR[:2, 2]
    zj = Jc[:, 2]
    if (zj <= 1e-3).any():
        return np.zeros(len(Xc), bool)
    uj = (Jc[:, :2] / zj[:, None]) * np.diag(KR)[:2] + KR[:2, 2]
    f = float(KR[0, 0])
    occ = np.zeros(len(Xc), bool)
    for a, b in BONES:
        A, B = uj[a], uj[b]
        AB = B - A
        L2 = float(AB @ AB)
        s = np.clip(((uv - A) @ AB) / L2, 0, 1) if L2 > 1e-9 else np.zeros(len(uv))
        Cp = A + s[:, None] * AB
        dist = np.linalg.norm(uv - Cp, axis=1)
        zb = zj[a] + s * (zj[b] - zj[a])
        occ |= (dist < f * radius / zb) & (z > zb)
    zp = float(zj[PALM_POLY].mean())
    occ |= _in_convex(uv, uj[PALM_POLY]) & (z > zp)
    return occ & ok


def visibility(Ot, S, Wc, KR, hands_t, radius=0.01):
    """Share of the surface samples S posed by Ot (world) not hidden behind any of the given hands (list of (21,3)
    world joints) seen from the camera Wc (world_T_cam)."""
    if KR is None or not hands_t:
        return 1.0
    Ci = np.linalg.inv(Wc)
    X = S @ Ot[:3, :3].T + Ot[:3, 3]
    Xc = X @ Ci[:3, :3].T + Ci[:3, 3]
    occ = np.zeros(len(S), bool)
    for J in hands_t:
        Jc = J @ Ci[:3, :3].T + Ci[:3, 3]
        occ |= occluded_by_hand(Xc, Jc, KR, radius)
    return 1.0 - float(occ.mean())


# ------------------------------------------------------------------ holds
def runs(mask):
    m = np.r_[False, np.asarray(mask, bool), False].astype(np.int8)
    d = np.diff(m)
    return list(zip(np.nonzero(d == 1)[0].tolist(), np.nonzero(d == -1)[0].tolist()))


def bridge(mask, gap):
    out = np.asarray(mask, bool).copy()
    r = runs(out)
    for (_, a1), (b0, _) in zip(r, r[1:]):
        if b0 - a1 <= gap:
            out[a1:b0] = True
    return out


def detect_holds(O, com, S, J, M, Wraw, contact=2.0, gap=6, min_len=10, carry=2.0):
    """Candidate holds of one object: list of dict(side, a, b, ...), longest first, frames not yet claimed."""
    T = len(O)
    c = O[:, :3, :3] @ com + O[:, :3, 3]
    cand = []
    for side in J:
        d = contact_cm(O, S, J[side], M[side])
        near = bridge(d < contact, gap)
        for a, b in runs(near):
            if b - a < min_len:
                continue
            mt = np.nonzero(M[side][a:b])[0] + a
            if len(mt) < 3:
                continue
            ptr = float(np.linalg.norm(Wraw[side][mt, :3, 3] - Wraw[side][mt[0], :3, 3], axis=1).max() * 100)
            otr = float(np.linalg.norm(c[a:b] - c[a], axis=1).max() * 100)
            cand.append(dict(side=side, a=int(a), b=int(b), palm_travel_cm=round(ptr, 2), obj_travel_cm=round(otr, 2),
                             d_med_cm=round(float(np.median(d[mt])), 2), comotion=bool(ptr >= carry and otr >= carry)))
    cand.sort(key=lambda h: -(h['b'] - h['a']))
    claimed = np.zeros(T, bool)
    holds, rejected = [], []
    for h in cand:
        if not h['comotion']:
            rejected.append(dict(h, why=f'no co-motion (palm {h["palm_travel_cm"]} cm, object {h["obj_travel_cm"]} cm, '
                                        f'need >= {carry:g} each)'))
            continue
        free = ~claimed[h['a']:h['b']]
        rr = [(s + h['a'], e + h['a']) for s, e in runs(free)]
        rr = [x for x in rr if x[1] - x[0] >= min_len and M[h['side']][x[0]:x[1]].sum() >= 3]
        if not rr:
            rejected.append(dict(h, why='frames claimed by a longer hold'))
            continue
        a, b = max(rr, key=lambda x: x[1] - x[0])
        # a hold starts and ends on measured frames (for the palm interpolation)
        mt = np.nonzero(M[h['side']][a:b])[0] + a
        a, b = int(mt[0]), int(mt[-1]) + 1
        if b - a < min_len:
            rejected.append(dict(h, why='too short after trimming'))
            continue
        claimed[a:b] = True
        holds.append(dict(h, a=a, b=b))
    holds.sort(key=lambda h: h['a'])
    return holds, rejected


def fill_frames(W, M, a, b, interp):
    """Palm frames on [a, b): measured frames as given, unmeasured ones screw-interpolated between measured neighbours."""
    out = W[a:b].copy()
    mt = np.nonzero(M[a:b])[0]
    for i in range(b - a):
        if M[a + i]:
            continue
        lo = mt[mt < i]
        hi = mt[mt > i]
        if len(lo) and len(hi):
            i0, i1 = lo[-1], hi[0]
            out[i] = interp(W[a + i0], W[a + i1], (i - i0) / (i1 - i0))
        else:
            out[i] = W[a + (lo[-1] if len(lo) else hi[0])]
    return out


def step_S10(a, objs, O, W_C, Jh, Mh, KR, interp, log=print):
    """Apply S10 in place on O (list of (T,4,4) world poses). Returns the record for pose_opt.json."""
    from scipy.ndimage import uniform_filter1d
    mode = a.s10_mode
    rec = dict(mode=mode, contact_cm=a.s10_contact_cm, bridge=a.s10_bridge, min_len=a.s10_min_len,
               carry_cm=a.s10_carry_cm, onset=a.s10_onset, vis_g=a.s10_vis_g, vis_hi=a.s10_vis_hi,
               vis_lo=a.s10_vis_lo, ramp=a.s10_ramp, smooth=a.s10_smooth, radius_cm=a.s10_radius_cm, objects={})
    if not Jh:
        rec['skipped'] = 'no hands file'
        log('S10 skipped: no hands file')
        return rec
    if KR is None and mode == 'gate':
        rec['skipped'] = 'no KR (visibility needs the camera)'
        log('S10 skipped: no KR')
        return rec
    T = len(O[0])
    Wraw = {s: palm_frames(Jh[s]) for s in Jh}
    Ws = {s: smooth_frames(Wraw[s], Mh[s], a.s10_smooth, a.s10_trim_deg) for s in Jh}
    r_m = a.s10_radius_cm / 100.0

    def vis(Ot, t, S):
        hands = [Jh[s][t] for s in Jh if Mh[s][t]]
        return visibility(Ot, S, W_C[t].astype(np.float64), KR, hands, r_m)

    aux = {}
    for j, o in enumerate(objs):
        side_code = np.full(T, -1, np.int8)                       # per-frame diagnostics (pose_opt_aux.npz)
        w_all = np.zeros(T)
        vP_all = np.full(T, np.nan)
        P_all = np.full((T, 4, 4), np.nan)
        holds, rejected = detect_holds(O[j], o.com, o.S, Jh, Mh, Wraw, a.s10_contact_cm, a.s10_bridge, a.s10_min_len,
                                       a.s10_carry_cm)
        orec = dict(holds=[], rejected=rejected)
        Onew = O[j].copy()
        for h in holds:
            s, h0, h1 = h['side'], h['a'], h['b']
            M = Mh[s]
            mt = np.nonzero(M[h0:h1])[0] + h0
            win = mt[:a.s10_onset]
            vtrk = np.array([vis(O[j][t], t, o.S) for t in mt[:2 * a.s10_onset]]) if KR is not None else None
            if vtrk is not None:
                g = [t for t, v in zip(win, vtrk[:len(win)]) if v >= a.s10_vis_g]
                if len(g) < 3:
                    order = np.argsort(-vtrk)[:5]
                    g = sorted(int(mt[i]) for i in order)
                    gsrc = f'fewer than 3 onset frames with v >= {a.s10_vis_g:g}: the 5 most visible of the first {len(vtrk)}'
                else:
                    gsrc = f'onset frames with v >= {a.s10_vis_g:g}'
            else:
                g, gsrc = list(win), 'first onset frames (no KR)'
            Gs = np.einsum('tij,tjk->tik', np.linalg.inv(Ws[s][g]), O[j][g])
            G = np.eye(4)
            G[:3, :3] = robust_mean_rot(Gs[:, :3, :3], a.s10_trim_deg)
            G[:3, 3] = np.median(Gs[:, :3, 3], axis=0)
            Wf = fill_frames(Ws[s], M, h0, h1, interp)              # (h1-h0,4,4)
            P = np.einsum('tij,jk->tik', Wf, G)
            n = h1 - h0
            ramp = np.minimum(1.0, np.minimum(np.arange(1, n + 1) / a.s10_ramp, np.arange(n, 0, -1) / a.s10_ramp))
            vP = None
            if KR is not None:                                    # visibility at the prediction (all modes: diagnostics)
                vm = np.array([vis(P[t - h0], t, o.S) if M[t] else np.nan for t in range(h0, h1)])
                idx = np.arange(n)
                okv = ~np.isnan(vm)
                vP = np.interp(idx, idx[okv], vm[okv])
            if mode == 'gate':
                w = np.clip((a.s10_vis_hi - vP) / (a.s10_vis_hi - a.s10_vis_lo), 0, 1)
                w = uniform_filter1d(w, a.s10_smooth, mode='nearest')
            else:
                w = np.ones(n)
            w = w * ramp
            if h0 == 0:
                w[0] = 0.0
            side_code[h0:h1] = 0 if s == 'left' else 1
            w_all[h0:h1] = w
            P_all[h0:h1] = P
            if vP is not None:
                vP_all[h0:h1] = vP
            if mode == 'trans':
                pg = np.array([np.linalg.inv(O[j][t]) @ np.r_[Ws[s][t][:3, 3], 1.0] for t in g])[:, :3]
                gp = np.median(pg, axis=0)
                tgt = O[j][h0:h1].copy()
                tgt[:, :3, 3] = Wf[:, :3, 3] - np.einsum('tij,j->ti', tgt[:, :3, :3], gp)
            else:
                tgt = P
            ch_cm, ch_deg = [], []
            for i in range(n):
                t = h0 + i
                if w[i] <= 0:
                    continue
                Onew[t] = interp(O[j][t], tgt[i], float(w[i]))
                ch_cm.append(float(np.linalg.norm((Onew[t][:3, :3] - O[j][t][:3, :3]) @ o.com + Onew[t][:3, 3]
                                                  - O[j][t][:3, 3]) * 100))
                ch_deg.append(float(np.degrees(np.linalg.norm(_R().from_matrix(Onew[t][:3, :3] @ O[j][t][:3, :3].T).as_rotvec()))))
            # residual of the tracker vs the prediction (GT-free; centroid distance and angle)
            res_cm = np.linalg.norm((P[:, :3, :3] - O[j][h0:h1, :3, :3]) @ o.com + P[:, :3, 3] - O[j][h0:h1, :3, 3], axis=1) * 100
            res_deg = np.degrees(_R().from_matrix(np.einsum('tij,tkj->tik', P[:, :3, :3], O[j][h0:h1, :3, :3])).magnitude())
            hr = dict(h, g_frames=[int(x) for x in g], g_source=gsrc, g_spread_deg=round(float(np.median(np.degrees(
                _R().from_matrix(np.einsum('tij,kj->tik', Gs[:, :3, :3], G[:3, :3])).magnitude()))), 2),
                g_spread_cm=round(float(np.median(np.linalg.norm(Gs[:, :3, 3] - G[:3, 3], axis=1)) * 100), 2),
                measured_frames=int(len(mt)), w_mean=round(float(w.mean()), 3), w_max=round(float(w.max()), 3),
                frames_changed=len(ch_cm), change_cm_mean=round(float(np.mean(ch_cm)), 3) if ch_cm else 0.0,
                change_cm_max=round(float(np.max(ch_cm)), 3) if ch_cm else 0.0,
                change_deg_max=round(float(np.max(ch_deg)), 2) if ch_deg else 0.0,
                residual_cm_med=round(float(np.median(res_cm)), 2), residual_deg_med=round(float(np.median(res_deg)), 1))
            if vtrk is not None:
                hr['vis_trk_onset_med'] = round(float(np.median(vtrk)), 3)
            if vP is not None:
                hr['vis_pred_med'] = round(float(np.median(vP)), 3)
                hr['vis_pred_min'] = round(float(vP.min()), 3)
            orec['holds'].append(hr)
            log(f'S10 {o.name}: hold {s} [{h0},{h1}) palm {h["palm_travel_cm"]} cm obj {h["obj_travel_cm"]} cm, G from '
                f'{len(g)} frames (spread {hr["g_spread_cm"]} cm {hr["g_spread_deg"]} deg), residual med '
                f'{hr["residual_cm_med"]} cm {hr["residual_deg_med"]} deg, w mean {hr["w_mean"]}, changed '
                f'{hr["frames_changed"]} frames (max {hr["change_cm_max"]} cm {hr["change_deg_max"]} deg)'
                + (f', v_P med {hr["vis_pred_med"]}' if vP is not None else ''))
        O[j] = Onew
        aux.update({f'S10_{o.name}_side': side_code, f'S10_{o.name}_w': w_all, f'S10_{o.name}_vP': vP_all,
                    f'S10_{o.name}_P': P_all})
        orec['frames_changed'] = int(sum(x['frames_changed'] for x in orec['holds']))
        rec['objects'][o.name] = orec
    rec['_aux'] = aux
    return rec
