"""Refine step S12 (31 Oct 2026, perception sprint "mask10") [H until its public gate]: a GT-free nest constraint for
two cups, the eval-10 fix. GROUND-TRUTH-FREE: it reads only our track, our hands, our meshes (and optional collision
pieces), our frame-0 table plane and, for the optional depth veto, our stereo depth, all through refine's checked
inputs.

Failure it targets (public ep11 DIAG, eval-10 screen): when a cup is lowered into another, FoundationPose's track of the
OUTER cup climbs along its axis toward the stack's top surface (+5.3 cm peak on ep11 with our mesh, +2.5 cm held after
the hands leave), while the inner cup is tracked well. The outer cup is the bottom of the stack: it cannot rise unless
it is lifted, and a lifted stack also moves sideways.

Rule (per ordered pair outer j / inner i of the --s12_cups objects; heights along our table normal n, n up):
  nested(t)  the inner's vertex centroid is above the outer's (zeta > 0), within --s12_coax_cm horizontally (coaxial),
             and the inner's lowest vertex is at most --s12_enter_cm above the outer's highest vertex (entering or
             inside: the cups overlap in height). Runs of nested frames with gaps <= --s12_bridge are bridged; a run of
             >= --s12_min_len frames is a nest window [ts, te).
  pre-nest   P* = the outer's pose at the frame of [ts - --s12_pre, ts) whose centroid height is the median of those
             frames' heights (a real tracked frame, no synthesis).
  guard G1   the outer stands where it stood: its lowest-vertex height at P* is within --s12_g1_cm of its frame-0 one
             (an outer cup that is already lifted, e.g. a hand-held cup receiving something, is left alone).
  release    the hold ends at the first window frame where the tracked outer is more than --s12_release_cm away
             horizontally from P* (the stack is carried), or at te; from there the pose ramps back to the track over
             --s12_ramp frames (SE(3) screw). A window that runs to the last frame needs no ramp.
  hold       --s12_mode hold (V1, the task's "keep the outer cup at its pre-nest pose"): O_j(t) = P*;
             --s12_mode height (V1h): O_j(t) = the tracked pose moved along n so that its centroid height is P*'s
             (horizontal motion and rotation kept).
  depth veto (optional, --s12_depth: the full depths_fs0.5.npy or a grid npz {frames, depth}): on the depth frames in
             the window, the outer's visible pixels (our renders at the tracked and the held pose, other objects in
             front removed, our hands removed (--s12_hand_cm), points within --s12_table_cm of the table removed) are
             back-projected; the median distance of the
             points to our mesh surface is computed at the held and at the tracked pose (points within --s12_band_cm of
             either). The window is vetoed (no hold) when on more than half of the frames with >= 150 points the held
             pose's median exceeds the tracked pose's by more than --s12_veto_cm.
  inner      --s12_inner none (V1, V1h): the inner's track is kept (it is the well-tracked cup).
             --s12_inner floor (V2, the task's literal "inner cup's bottom on the outer cup's inner floor"): the inner's
             bottom (lowest point along n) is put on the outer's inner floor height on window frames where the inner
             rests (not moving per refine's labels and no measured hand within --hand_cm), and is kept at or above it
             on the other window frames. The floor and the inner's bottom come from --s12_pieces (collision pieces
             DIR/<obj>/piece_*.obj: the cavity floor by a ray down the pieces' axis) or, without pieces, from our mesh.
Frame 0 is never changed (ts >= 1). Objects outside --s12_cups are never touched.
"""
import glob
import os

import numpy as np


def _rot():
    from scipy.spatial.transform import Rotation
    return Rotation


def runs_bridged(mask, bridge, min_len):
    """[(s, e)] runs of True with gaps <= bridge filled, length >= min_len."""
    m = np.asarray(mask, bool).copy()
    idx = np.nonzero(m)[0]
    for a_, b_ in zip(idx[:-1], idx[1:]):
        if 1 < b_ - a_ <= bridge + 1:
            m[a_:b_] = True
    d = np.diff(np.r_[0, m.astype(np.int8), 0])
    return [(int(s), int(e)) for s, e in zip(np.nonzero(d == 1)[0], np.nonzero(d == -1)[0]) if e - s >= min_len]


class CupGeom:
    """Points of a cup in its body frame for heights (our mesh vertices, or the collision pieces' vertices) and the
    cavity floor (body-frame point on the axis), from the pieces when given, else from our mesh."""

    def __init__(self, o, pieces_dir, checked):
        import trimesh
        self.name = o.name
        self.V = o.V
        self.src = 'library mesh'
        mesh = o.mesh
        pcs = sorted(glob.glob(os.path.join(pieces_dir, o.name, 'piece_*.obj'))) if pieces_dir else []
        if pcs:
            parts = [trimesh.load(checked(p), force='mesh') for p in pcs]
            self.V = np.concatenate([np.asarray(p.vertices, float) for p in parts])
            mesh = trimesh.util.concatenate(parts)
            self.src = f'collision pieces {pieces_dir}/{o.name} ({len(pcs)})'
        c = self.V.mean(0)
        w, U = np.linalg.eigh(np.cov((self.V - c).T))
        k = int(np.argmax([abs(w[i] - np.mean(np.delete(w, i))) for i in range(3)]))
        ax = U[:, k]
        h = (self.V - c) @ ax
        # the open end is the wider one (cups taper toward the base)
        rad = np.linalg.norm((self.V - c) - h[:, None] * ax, axis=1)
        lo, hi = h < np.quantile(h, 0.15), h > np.quantile(h, 0.85)
        if np.median(rad[lo]) > np.median(rad[hi]):
            ax = -ax                                           # +ax points from the open end to the base
            h = -h
        self.axis, self.c = ax, c
        loc, _, _ = mesh.ray.intersects_location([c - ax * 0.3], [ax], multiple_hits=True)
        hh = sorted(float((x - c) @ ax) for x in loc)
        # first surface met going down the axis from the open end = the cavity floor (inner surface of the base)
        self.floor_h = hh[0] if hh else float(h.max())
        self.base_h = float(h.max())
        self.floor = c + self.floor_h * ax                     # body-frame point on the floor
        self.floor_above_base_cm = round((self.base_h - self.floor_h) * 100, 2)


def _world(T, X):
    return X @ T[:3, :3].T + T[:3, 3]


def depth_veto(j, win, objs, O, P_hold, W_C, KR, H, dsrc, plane, a, log):
    """Per depth frame in the window: median point-to-mesh distance at the held vs the tracked pose of object j."""
    from scipy.spatial import cKDTree
    import offsetfix as OF
    K2 = np.diag([0.5, 0.5, 1.0]) @ np.asarray(KR, float)
    n_w, d_w = plane
    out = []
    for t in [f for f in dsrc.frames if win[0] <= f < win[1]]:
        dep = dsrc.get(t)
        Wt = W_C[t].astype(float)
        Wi = np.linalg.inv(Wt)
        Ph = P_hold[t]
        pix = np.zeros(dep.shape, bool)
        for Tw in (O[j][t], Ph):                    # j front-most (others at their tracked poses), at either pose
            items = [(k, Wi @ (Tw if k == j else O[k][t]), OF.mesh_model(objs[k])[0]) for k in range(len(objs))]
            _, lab = OF.render(items, K2, dep.shape)
            pix |= lab == j
        pix &= ~OF.hand_mask(H, t, Wi, K2, dep.shape, a.s12_hand_cm)
        cloud = OF.backproject(pix, dep, K2)
        if len(cloud):
            Xw = cloud @ Wt[:3, :3].T + Wt[:3, 3]
            cloud = Xw[(Xw @ n_w + d_w) > a.s12_table_cm / 100]
        P = OF.mesh_model(objs[j])[0]
        P = P[::max(1, len(P) // 60000)]
        dd = {}
        for tag, Tw in (('tracked', O[j][t]), ('held', Ph)):
            dd[tag] = cKDTree(_world(Tw, P)).query(cloud)[0] if len(cloud) else np.zeros(0)
        keep = (dd['tracked'] < a.s12_band_cm / 100) | (dd['held'] < a.s12_band_cm / 100) if len(cloud) else np.zeros(0, bool)
        r = dict(frame=int(t), points=int(keep.sum()))
        if keep.sum() >= 150:
            r.update(tracked_med_cm=round(float(np.median(dd['tracked'][keep]) * 100), 3),
                     held_med_cm=round(float(np.median(dd['held'][keep]) * 100), 3))
            r['contradicts'] = bool(r['held_med_cm'] - r['tracked_med_cm'] > a.s12_veto_cm)
        out.append(r)
    used = [r for r in out if 'contradicts' in r]
    nc = sum(r['contradicts'] for r in used)
    veto = bool(used) and nc > len(used) / 2
    log(f'S12 depth veto {objs[j].name} window {win}: {len(used)} frames with >= 150 points, {nc} contradict -> '
        f'{"VETO" if veto else "no veto"}')
    return veto, out


def step_S12(a, objs, O, plane, lab, W_C, KR, H, dsrc, checked, log):
    """O: list of (T,4,4) world poses (modified in place). Returns the pose_opt record."""
    import refine as RF
    n, d, src = plane
    cups = [s.strip() for s in a.s12_cups.split(',') if s.strip()]
    rec = dict(mode=a.s12_mode, inner=a.s12_inner, cups=cups, plane=dict(source=src), windows=[], changed=[],
               params={k: getattr(a, k) for k in vars(a) if k.startswith('s12_')})
    if n is None:
        rec['skipped'] = src
        log('S12 skipped:', src)
        return rec
    n = np.asarray(n, float) / np.linalg.norm(n)
    rec['plane'].update(n=np.round(n, 6).tolist(), d=round(float(d), 6))
    J = [j for j, o in enumerate(objs) if o.name in cups]
    if len(J) < 2:
        rec['skipped'] = f'fewer than two of {cups} in the roster'
        log('S12 skipped:', rec['skipped'])
        return rec
    T = len(O[0])
    G = {j: CupGeom(objs[j], a.s12_pieces, checked) for j in J}
    rec['geometry'] = {objs[j].name: dict(source=G[j].src, floor_above_base_cm=G[j].floor_above_base_cm) for j in J}
    O_in = [x.copy() for x in O]
    C = {j: _world_c(O_in[j], objs[j].V.mean(0)) for j in J}
    hgt = {j: C[j] @ n + d for j in J}
    lo = {j: np.array([(_world(O_in[j][t], G[j].V) @ n).min() + d for t in range(T)]) for j in J}
    hi = {j: np.array([(_world(O_in[j][t], objs[j].V) @ n).max() + d for t in range(T)]) for j in J}
    claimed = {j: np.zeros(T, bool) for j in J}
    for jo in J:
        for ji in J:
            if ji == jo:
                continue
            e = C[ji] - C[jo]
            zeta = e @ n
            rho = np.linalg.norm(e - zeta[:, None] * n[None], axis=1)
            nested = (zeta > 0) & (rho < a.s12_coax_cm / 100) & (lo[ji] < hi[jo] + a.s12_enter_cm / 100)
            nested[0] = False
            for ts, te in runs_bridged(nested, a.s12_bridge, a.s12_min_len):
                w = dict(outer=objs[jo].name, inner=objs[ji].name, start=ts, end=te,
                         rho_cm_median=round(float(np.median(rho[ts:te]) * 100), 2),
                         zeta_cm_median=round(float(np.median(zeta[ts:te]) * 100), 2))
                pre = np.arange(max(0, ts - a.s12_pre), ts)
                if len(pre) == 0 or claimed[jo][ts:te].any() or claimed[ji][ts:te].any():
                    w['applied'] = False
                    w['reason'] = 'no pre-nest frames' if len(pre) == 0 else 'frames already in another window'
                    rec['windows'].append(w)
                    log(f'S12 window {w}')
                    continue
                med = np.median(hgt[jo][pre])
                tstar = int(pre[np.argmin(np.abs(hgt[jo][pre] - med))])
                Pst = O_in[jo][tstar].copy()
                b0 = float(lo[jo][0])
                bst = float((_world(Pst, G[jo].V) @ n).min() + d)
                w.update(pre_frame=tstar, pre_height_cm=round(float(hgt[jo][tstar] * 100), 3),
                         pre_bottom_minus_f0_cm=round((bst - b0) * 100, 3),
                         outer_lift_in_window_cm=dict(max=round(float((hgt[jo][ts:te] - hgt[jo][tstar]).max() * 100), 3),
                                                      end=round(float((hgt[jo][te - 1] - hgt[jo][tstar]) * 100), 3)))
                if abs(bst - b0) * 100 >= a.s12_g1_cm:
                    w['applied'] = False
                    w['reason'] = f'G1: outer bottom {abs(bst - b0) * 100:.2f} cm from its frame-0 height (lifted)'
                    rec['windows'].append(w)
                    log(f'S12 window {w}')
                    continue
                # release: tracked outer more than release_cm away horizontally from P*
                ch = C[jo] - _world_c(Pst[None], objs[jo].V.mean(0))[0]
                hor = np.linalg.norm(ch - (ch @ n)[:, None] * n[None], axis=1)
                rel = np.nonzero(hor[ts:te] > a.s12_release_cm / 100)[0]
                th = ts + int(rel[0]) if len(rel) else te
                w['hold_end'] = th
                w['released_by'] = 'outer moved horizontally' if len(rel) else ('window end' if te < T else 'episode end')
                if th <= ts:
                    w['applied'] = False
                    w['reason'] = 'released at the first window frame'
                    rec['windows'].append(w)
                    log(f'S12 window {w}')
                    continue
                Ph = O_in[jo].copy()
                for t in range(ts, th):
                    if a.s12_mode == 'hold':
                        Ph[t] = Pst
                    else:
                        Ph[t] = O_in[jo][t].copy()
                        Ph[t][:3, 3] += n * (hgt[jo][tstar] - hgt[jo][t])
                if dsrc is not None and dsrc.frames and KR is not None:
                    veto, vinfo = depth_veto(jo, (ts, th), objs, O_in, Ph, W_C, KR, H, dsrc, (n, d), a, log)
                    w['depth_veto'] = dict(vetoed=veto, frames=vinfo)
                    if veto:
                        w['applied'] = False
                        w['reason'] = 'depth veto'
                        rec['windows'].append(w)
                        continue
                O[jo][ts:th] = Ph[ts:th]
                for k in range(1, a.s12_ramp + 1):                   # ramp back to the track after a release
                    t = th - 1 + k
                    if t >= T:
                        break
                    O[jo][t] = RF.interp_pose(Ph[th - 1], O_in[jo][t], k / (a.s12_ramp + 1))
                claimed[jo][ts:th] = True
                claimed[ji][ts:th] = True
                w['applied'] = True
                dz = [(O[jo][t][:3, :3] @ objs[jo].V.mean(0) + O[jo][t][:3, 3] - C[jo][t]) @ n for t in range(ts, th)]
                w['outer_change_cm'] = dict(height_mean=round(float(np.mean(dz) * 100), 3),
                                            height_min=round(float(np.min(dz) * 100), 3))
                if a.s12_inner == 'floor':
                    w['inner_floor'] = inner_floor(a, jo, ji, ts, th, objs, O, O_in, G, lab, n, d)
                rec['windows'].append(w)
                for nm in (objs[jo].name, objs[ji].name if a.s12_inner == 'floor' else None):
                    if nm and nm not in rec['changed']:
                        rec['changed'].append(nm)
                log(f'S12 window {objs[jo].name} <- {objs[ji].name} [{ts}, {te}) hold to {th} ({w["released_by"]}), '
                    f'pre-nest f{tstar}, outer height change mean {w["outer_change_cm"]["height_mean"]:+.2f} cm '
                    f'(min {w["outer_change_cm"]["height_min"]:+.2f}); inner {a.s12_inner}')
    if not rec['windows']:
        log('S12: no nest window')
    return rec


def _world_c(Ot, c):
    return Ot[:, :3, :3] @ c + Ot[:, :3, 3]


def inner_floor(a, jo, ji, ts, th, objs, O, O_in, G, lab, n, d):
    """V2: the inner's bottom on the outer's cavity floor (resting frames) or at least at it (other window frames)."""
    gi, go = G[ji], G[jo]
    rest = ~lab[ji]['moving'] & ~(lab[ji]['hand_cm'] < a.hand_cm)
    sh = []
    for t in range(ts, th):
        floor_h = float(_world(O[jo][t], go.floor[None])[0] @ n + d)
        bot = float((_world(O_in[ji][t], gi.V) @ n).min() + d)
        dz = floor_h - bot if rest[t] else max(0.0, floor_h - bot)
        if dz != 0.0:
            O[ji][t] = O_in[ji][t].copy()
            O[ji][t][:3, 3] += n * dz
        sh.append(dz)
    sh = np.array(sh)
    return dict(resting_frames=int(rest[ts:th].sum()), mean_shift_cm=round(float(sh.mean() * 100), 3),
                min_shift_cm=round(float(sh.min() * 100), 3), max_shift_cm=round(float(sh.max() * 100), 3))
