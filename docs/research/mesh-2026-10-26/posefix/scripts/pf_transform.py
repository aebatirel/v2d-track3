"""posefix transform (GT-free): rest projection of our tracked poses at hands-off (H30) segments.

Reads only our tracks (TRACKS_ROOT/ep<e>/poses_world_vo.npz), our pack 9a+ visual meshes (budget_mesh 4096/4096), our
gmg v6 M1 MediaPipe hands and our v6 table plane. Writes OUT_ROOT/ep<e>/poses_world_vo.npz (same keys, float64) and
OUT_ROOT/ep<e>/posefix.json (segments, shifts, penetration before / after). Rule: PREREG.md (this folder), section 4.

Usage: python -I pf_transform.py VARIANT TRACKS_ROOT OUT_ROOT EP [EP ...]      VARIANT in A, B, C, D
  A: the pre-registered rule (gated).
  B: A + drop floating rest segments onto their support (report only).
  C: A, but segments that contain frame 0 keep their tracked pose (report only).
  D: A with object-object constraints only (no table constraint) (report only).
"""
import json, os, sys, time
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pf_lib as L

# ---- constants (PREREG section 4) ---------------------------------------------------------------------------------
HAND_M = 0.030            # H30: a hand joint within 30 mm of the object's mesh surface (or inside it) = hand-near
L_MIN = 5                 # a rest segment is a run of >= 5 consecutive hands-off frames (0.25 s at 20 fps)
SUPPORT_H = 0.010         # an object whose lowest point is >= 10 mm above the table does not stand on the table
CONTACT = 0.005           # inheritance needs contact: the mover's probes within 5 mm of the partner (or inside it)
TOL = 0.0010              # a constraint frame is clean when its max penetration depth <= 1.0 mm
Q_OK = 0.50               # a segment is resolved when >= 50 % of its constraint frames are clean (median frame)
CAP_T = 0.030             # translation cap, m
CAP_R = np.deg2rad(5.0)   # rotation bound (stage 2 only)
STEP_T = 0.005            # trust region per Gauss-Newton iteration: 5 mm ...
STEP_R = np.deg2rad(1.0)  # ... and 1 deg
ITERS = 60                # iteration cap per stage
DAMP = 1e-9               # Levenberg damping, times the number of violating probes, added to J^T J
SWEEPS = 2                # Gauss-Seidel sweeps over all segments; the last sweep's shifts are final
STALL = 20                # a stage also stops when its clean share has not improved for 20 iterations
LIFT_STEP = 0.0005        # stage 1b: lift along the table normal in 0.5 mm steps up to the translation cap
RAMP = 3                  # linear ramp, frames, outside each end of a shifted segment
SUP_MIN, SUP_MAX = 0.002, 0.015   # variant B: drop a rest segment whose median clearance is in (2, 15] mm


def hand_near(P, o, sd, J):
    T = len(P[o]); hd = np.full(T, np.inf)
    for t in range(T):
        if len(J[t]):
            X = L.tf(L.inv(P[o][t]), J[t])
            d = sd.surf_dist(X)
            d = np.where(sd.query(X) < 0, 0.0, d)
            hd[t] = d.min()
    return hd < HAND_M, hd


def runs(mask):
    out, s = [], None
    for t, m in enumerate(list(mask) + [False]):
        if m and s is None:
            s = t
        if not m and s is not None:
            out.append((s, t - 1)); s = None
    return out


def rigid(delta, c):
    """4x4 world transform: rotate by rotation vector delta[3:] about point c, then translate by delta[:3]."""
    from scipy.spatial.transform import Rotation as Rot
    D = np.eye(4)
    R = Rot.from_rotvec(delta[3:]).as_matrix()
    D[:3, :3] = R
    D[:3, 3] = c - R @ c + delta[:3]
    return D


class Seg:
    def __init__(self, o, s, e):
        self.o, self.s, self.e = o, s, e
        self.delta = np.zeros(6); self.c = np.zeros(3); self.status = 'clean'; self.info = {}; self.fp = []


def constraints(o, fp, P0, Pc, sdfs, table, delta, c, use_table=True, want_rows=True):
    """Constraint frames fp = [(t, partners)]: per frame the max penetration depth (m) of object o at pose
    rigid(delta, c) @ P0[o][t] against the table and the partners at their current poses Pc[p][t]; with want_rows the
    Gauss-Newton rows [n, 6] (d depth / d (t, rotvec)) and depths [n] of the violating probes."""
    n_t, d_t = table
    sd = sdfs[o]
    D = rigid(delta, c)
    fdepth, rows, deps = {}, [], []
    for t, partners in fp:
        M = D @ P0[o][t]
        x = L.tf(M, sd.probes)
        dm = 0.0
        if use_table:
            h = x @ n_t + d_t
            dm = max(dm, -h.min())
            if want_rows and (h < 0).any():
                v = h < 0
                g = np.repeat(n_t[None], v.sum(), 0)
                rows.append(np.hstack([g, np.cross(x[v] - c, g)])); deps.append(-h[v])
        for p in partners:
            Mp = Pc[p][t]
            s, g = sdfs[p].query(L.tf(L.inv(Mp) @ M, sd.probes), grad=True)       # o's probes inside p
            dm = max(dm, -s.min())
            if want_rows and (s < 0).any():
                v = s < 0
                gw = g[v] @ Mp[:3, :3].T
                rows.append(np.hstack([gw, np.cross(x[v] - c, gw)])); deps.append(-s[v])
            y = L.tf(Mp, sdfs[p].probes)
            s2, g2 = sd.query(L.tf(L.inv(M), y), grad=True)                      # p's probes inside o
            dm = max(dm, -s2.min())
            if want_rows and (s2 < 0).any():
                v = s2 < 0
                gw = g2[v] @ M[:3, :3].T
                rows.append(np.hstack([-gw, -np.cross(y[v] - c, gw)])); deps.append(-s2[v])
        fdepth[t] = max(dm, 0.0)
    if want_rows:
        R = np.vstack(rows) if rows else np.zeros((0, 6)); d = np.concatenate(deps) if deps else np.zeros(0)
        return fdepth, R, d
    return fdepth


def ok_frac(fd):
    v = np.array(list(fd.values()))
    return float(np.mean(v <= TOL)) if len(v) else 1.0


def stats(fd):
    v = np.array(list(fd.values())) if fd else np.zeros(1)
    return dict(ok=round(ok_frac(fd), 3), max_mm=round(1000 * float(v.max()), 2),
                median_mm=round(1000 * float(np.median(v)), 2))


def solve(o, fp, P0, Pc, sdfs, table, c, dof, use_table, init):
    """Projected Gauss-Newton on the squared depths of the violating probes, from `init` (zero, or the inherited
    support shift); stops at the first iterate with >= Q_OK clean constraint frames (success), at the translation cap,
    at ITERS or after STALL iterations without a better clean share (failure)."""
    delta = init.copy(); last = {}; best, best_it = -1.0, 0
    for it in range(ITERS + 1):
        fd, R, d = constraints(o, fp, P0, Pc, sdfs, table, delta, c, use_table)
        q = ok_frac(fd)
        last = dict(it=it, ok=round(q, 3), max_mm=round(1000 * max(fd.values()), 2), viol=int(len(d)),
                    t_mm=np.round(1000 * delta[:3], 2).tolist(), r_deg=round(float(np.degrees(np.linalg.norm(delta[3:]))), 2))
        if q >= Q_OK:
            return delta, True, last
        if q > best:
            best, best_it = q, it
        if it == ITERS or len(d) == 0 or it - best_it >= STALL:
            break
        A = R[:, :dof]
        step = np.linalg.solve(A.T @ A + DAMP * len(d) * np.eye(dof), A.T @ d)
        nt = np.linalg.norm(step[:3])
        if nt > STEP_T:
            step = step * (STEP_T / nt)
        if dof == 6:
            nr = np.linalg.norm(step[3:])
            if nr > STEP_R:
                step[3:] *= STEP_R / nr
        delta[:dof] += step
        if dof == 6 and np.linalg.norm(delta[3:]) > CAP_R:            # projection onto the rotation bound
            delta[3:] *= CAP_R / np.linalg.norm(delta[3:])
        if np.linalg.norm(delta[:3]) > CAP_T:
            last['stop'] = 'translation cap'
            return delta, False, last
    last['stop'] = 'iterations' if it == ITERS else ('stall' if it - best_it >= STALL else 'no violators')
    return delta, False, last


def lift(o, fp, P0, Pc, sdfs, table, c, use_table, init):
    """Stage 1b: the smallest lift s (0.5 mm steps) along the table normal n (up), from `init`, that makes >= Q_OK of
    the constraint frames clean, with |translation| <= CAP_T."""
    n_t = table[0]
    k = 1
    while True:
        d = init.copy(); d[:3] += k * LIFT_STEP * n_t
        if np.linalg.norm(d[:3]) > CAP_T:
            return init, False, dict(stop='translation cap', lift_mm=round(1000 * (k - 1) * LIFT_STEP, 1))
        fd = constraints(o, fp, P0, Pc, sdfs, table, d, c, use_table, False)
        if ok_frac(fd) >= Q_OK:
            return d, True, dict(lift_mm=round(1000 * k * LIFT_STEP, 1), **stats(fd))
        k += 1


def inherited(g, P, Pc, hmin, sdfs):
    """Support inheritance (PREREG 4.5): if the mover rests on a partner (on most pair frames its lowest point is
    >= SUPPORT_H above the partner's and its probes come within CONTACT of the partner, original poses) and that
    partner is shifted at those frames, the mover's start shift is the partner's shift applied to the mover's centre
    (mean over the shifted pair frames; the partner with most such frames)."""
    best = None
    for p in {q for _, ps in g.fp for q in ps}:
        fr = [t for t, ps in g.fp if p in ps]
        up = np.mean([(hmin[g.o][t] - hmin[p][t] >= SUPPORT_H) and
                      (sdfs[p].query(L.tf(L.inv(P[p][t]) @ P[g.o][t], sdfs[g.o].probes)).min() <= CONTACT) for t in fr])
        moved = [t for t in fr if np.any(Pc[p][t] != P[p][t])]
        if up > 0.5 and moved and (best is None or len(moved) > best[1]):
            disp = [L.tf(Pc[p][t] @ L.inv(P[p][t]), g.c[None])[0] - g.c for t in moved]
            best = (p, len(moved), np.mean(disp, 0))
    if best is None:
        return None, np.zeros(6)
    return best[0], np.r_[best[2], 0, 0, 0]


def run_episode(e, variant, root, out_root, sdfs):
    t0 = time.time()
    Z = np.load(f'{root}/ep{e}/poses_world_vo.npz')
    names = list(Z.files)
    P = {n: np.asarray(Z[n], np.float64) for n in names}
    T = len(P[names[0]])
    for n in names:
        if n not in sdfs:
            sdfs[n] = L.SDF(n, *L.load_mesh(n))
    table = L.table_plane(e)
    n_t, d_t = table
    use_table = variant != 'D'
    J = L.hands(e)
    near, hd, hmin = {}, {}, {}
    for o in names:
        near[o], hd[o] = hand_near(P, o, sdfs[o], J)
        hmin[o] = np.array([(L.tf(P[o][t], sdfs[o].probes) @ n_t + d_t).min() for t in range(T)])
    segs, start = [], {}
    for o in names:
        start[o] = np.full(T, -1)
        for s, e_ in runs(~near[o]):
            if e_ - s + 1 >= L_MIN:
                segs.append(Seg(o, s, e_)); start[o][s:e_ + 1] = s
    vol = {o: sdfs[o].volume_cm3 for o in names}
    slot = {o: i for i, o in enumerate(names)}

    def mover(a, b, t):
        """Released last moves; tie: smaller volume; tie: later slot. Support: if that object is the lower one and the
        other does not stand on the table (lowest point >= SUPPORT_H), the other (upper, supported) object moves."""
        if start[a][t] != start[b][t]:
            m = a if start[a][t] > start[b][t] else b
        elif vol[a] != vol[b]:
            m = a if vol[a] < vol[b] else b
        else:
            m = a if slot[a] > slot[b] else b
        q = b if m == a else a
        if hmin[m][t] < hmin[q][t] and hmin[q][t] >= SUPPORT_H:
            m = q
        return m

    segs.sort(key=lambda g: (g.s, -vol[g.o], slot[g.o]))
    for g in segs:
        g.fp = [(t, [p for p in names if p != g.o and start[p][t] >= 0 and mover(g.o, p, t) == g.o])
                for t in range(g.s, g.e + 1)]
        g.info['constraint_frames'] = len(g.fp)
        g.info['pair_frames'] = {p: int(sum(p in q for _, q in g.fp)) for p in names if p != g.o}
        tm = (g.s + g.e) // 2
        g.c = L.tf(P[g.o][tm], sdfs[g.o].vol_centroid[None])[0]
        g.info['before'] = stats(constraints(g.o, g.fp, P, P, sdfs, table, np.zeros(6), g.c, use_table, False))
        g.info['hand_min_mm'] = round(float(1000 * hd[g.o][g.s:g.e + 1].min()), 1)
        g.info['lowest_above_table_mm_median'] = round(float(1000 * np.median(hmin[g.o][g.s:g.e + 1])), 2)
    Pc = {n: P[n].copy() for n in names}
    for sweep in range(SWEEPS):
        for g in segs:
            g.delta = np.zeros(6); g.info.pop('drop_mm', None)
            if variant == 'C' and g.s == 0:
                g.status = 'frame0_kept'
            else:
                sup, init = inherited(g, P, Pc, hmin, sdfs)
                g.info['inherited_from'] = sup
                g.info['inherited_t_mm'] = np.round(1000 * init[:3], 2).tolist()
                fd0 = constraints(g.o, g.fp, P, Pc, sdfs, table, init, g.c, use_table, False)
                g.info[f'sweep{sweep}_start'] = stats(fd0)
                g.info.pop('stage1', None); g.info.pop('stage1b', None); g.info.pop('stage2', None)
                if ok_frac(fd0) >= Q_OK:
                    g.delta, g.status = init, ('inherited' if sup else 'clean')
                else:
                    d3, ok3, h3 = solve(g.o, g.fp, P, Pc, sdfs, table, g.c, 3, use_table, init)
                    g.info['stage1'] = h3; g.info.pop('stage1b', None)
                    if ok3:
                        g.delta, g.status = d3, 'shift_t'
                    else:
                        dl, okl, hl = lift(g.o, g.fp, P, Pc, sdfs, table, g.c, use_table, init)
                        g.info['stage1b'] = hl
                    if not ok3 and okl:
                        g.delta, g.status = dl, 'shift_lift'
                    elif not ok3:
                        d6, ok6, h6 = solve(g.o, g.fp, P, Pc, sdfs, table, g.c, 6, use_table, init)
                        g.info['stage2'] = h6
                        if ok6:
                            g.delta, g.status = d6, 'shift_tr'
                        else:
                            g.delta, g.status = init, ('unresolved_inherited' if sup else 'unresolved')
                if variant == 'B' and g.status in ('clean', 'inherited', 'shift_t', 'shift_lift', 'shift_tr'):
                    drop(g, P, Pc, sdfs, table, names, start)
            D = rigid(g.delta, g.c)
            for t in range(g.s, g.e + 1):
                Pc[g.o][t] = D @ P[g.o][t]
    for g in segs:
        g.info['after'] = stats(constraints(g.o, g.fp, Pc, Pc, sdfs, table, np.zeros(6), g.c, use_table, False))
        g.info['after_all_rest_partners'] = stats(constraints(
            g.o, [(t, [p for p in names if p != g.o and start[p][t] >= 0]) for t, _ in g.fp], Pc, Pc, sdfs, table,
            np.zeros(6), g.c, True, False))
    # ---- assemble with ramps (PREREG 4.7) ----
    Q = {n: P[n].copy() for n in names}
    for o in names:
        sg = sorted([g for g in segs if g.o == o], key=lambda g: g.s)
        for g in sg:
            D = rigid(g.delta, g.c)
            for t in range(g.s, g.e + 1):
                Q[o][t] = D @ P[o][t]
        ends = [(None, -1)] + [(g, None) for g in sg] + [(None, T)]
        for i in range(len(ends) - 1):
            ga, gb = ends[i][0], ends[i + 1][0]
            a_end = ga.e if ga is not None else ends[i][1]
            b_start = gb.s if gb is not None else ends[i + 1][1]
            gap = list(range(a_end + 1, b_start))
            n_ = len(gap)
            for k, t in enumerate(gap, 1):
                if ga is not None and gb is not None and n_ <= 2 * RAMP:
                    f = k / (n_ + 1)
                    d = (1 - f) * ga.delta + f * gb.delta; c = (1 - f) * ga.c + f * gb.c
                else:
                    d = np.zeros(6); c = np.zeros(3); kb = n_ + 1 - k
                    if ga is not None and k <= RAMP:
                        d = d + ga.delta * (1 - k / (RAMP + 1)); c = ga.c
                    if gb is not None and kb <= RAMP:
                        d = d + gb.delta * (1 - kb / (RAMP + 1)); c = gb.c
                if np.any(d):
                    Q[o][t] = rigid(d, c) @ P[o][t]
    od = f'{out_root}/ep{e}'
    os.makedirs(od, exist_ok=True)
    np.savez(f'{od}/poses_world_vo.npz', **Q)
    changed = {n: int((np.abs(Q[n] - P[n]).max((1, 2)) > 0).sum()) for n in names}
    rep = dict(ep=e, variant=variant, objects=names, frames=T, changed_frames=changed,
               rest_frames={o: int((start[o] >= 0).sum()) for o in names},
               segments=[dict(obj=g.o, start=g.s, end=g.e, status=g.status,
                              t_mm=np.round(1000 * g.delta[:3], 3).tolist(),
                              t_norm_mm=round(float(1000 * np.linalg.norm(g.delta[:3])), 3),
                              r_deg=round(float(np.degrees(np.linalg.norm(g.delta[3:]))), 3),
                              rotvec=np.round(g.delta[3:], 6).tolist(),
                              centre=np.round(g.c, 6).tolist(), **g.info) for g in segs],
               seconds=round(time.time() - t0, 1))
    json.dump(rep, open(f'{od}/posefix.json', 'w'), indent=1)
    return rep


def drop(g, P, Pc, sdfs, table, names, start):
    """Variant B: lower a rest segment along -n by the largest s <= median clearance (clearance in (SUP_MIN, SUP_MAX])
    that keeps >= Q_OK of its frames clean against the table and every object at rest in the same frame."""
    n_t, d_t = table
    o = g.o; sd = sdfs[o]; D = rigid(g.delta, g.c)
    cl = []
    for t in range(g.s, g.e + 1):
        x = L.tf(D @ P[o][t], sd.probes)
        m = (x @ n_t + d_t).min()
        for p in names:
            if p != o and start[p][t] >= 0:
                m = min(m, sdfs[p].query(L.tf(L.inv(Pc[p][t]), x)).min())
        cl.append(m)
    c50 = float(np.median(cl)); g.info['clearance_mm'] = round(1000 * c50, 2)
    if not (SUP_MIN < c50 <= SUP_MAX):
        return
    fp_all = [(t, [p for p in names if p != o and start[p][t] >= 0]) for t, _ in g.fp]
    lo, hi = 0.0, c50
    for _ in range(12):                                            # bisection on the drop distance
        mid = 0.5 * (lo + hi)
        dd = g.delta.copy(); dd[:3] -= mid * n_t
        if ok_frac(constraints(o, fp_all, P, Pc, sdfs, table, dd, g.c, True, False)) >= Q_OK:
            lo = mid
        else:
            hi = mid
    g.delta = g.delta.copy(); g.delta[:3] -= lo * n_t
    g.info['drop_mm'] = round(1000 * lo, 2)
    if lo > 0 and g.status == 'clean':
        g.status = 'drop'


if __name__ == '__main__':
    variant, root, out_root = sys.argv[1], sys.argv[2], sys.argv[3]
    assert variant in ('A', 'B', 'C', 'D')
    sdfs = {}
    for e in [int(x) for x in sys.argv[4:]]:
        r = run_episode(e, variant, root, out_root, sdfs)
        print(e, variant, [(s['obj'], s['start'], s['end'], s['status'], s['t_norm_mm'], s['r_deg'])
                           for s in r['segments']], r['seconds'], 's', flush=True)
