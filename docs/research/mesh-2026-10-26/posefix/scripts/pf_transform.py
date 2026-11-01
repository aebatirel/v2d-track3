"""posefix transform (GT-free): rest projection of our tracked poses at hands-off (H30) segments.

Reads only our tracks (TRACKS_ROOT/ep<e>/poses_world_vo.npz), our pack 9a+ visual meshes (budget_mesh 4096/4096), our
gmg v6 M1 MediaPipe hands and our v6 table plane. Writes OUT_ROOT/ep<e>/poses_world_vo.npz (same keys, float64) and
OUT_ROOT/ep<e>/posefix.json (segments, shifts, penetration before / after). Rule: PREREG.md (this folder).

Usage: python -I pf_transform.py VARIANT TRACKS_ROOT OUT_ROOT EP [EP ...]      VARIANT in A, B, C
  A: the pre-registered rule (gated).  B: A + drop floating rest segments onto their support (report only).
  C: A, but segments that contain frame 0 keep their tracked pose (report only).
"""
import json, os, sys, time
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pf_lib as L

# ---- constants (PREREG section 4) ---------------------------------------------------------------------------------
HAND_M = 0.030        # H30: a hand joint within 30 mm of the object's mesh surface (or inside it) = hand-near
L_MIN = 5             # a rest segment is a run of >= 5 consecutive hands-off frames (0.25 s at 20 fps)
TOL = 0.0010          # penetration tolerance, m: a constraint frame is clean when its max depth <= 1.0 mm
Q_OK = 0.90           # a segment is resolved when >= 90 % of its constraint frames are clean
CAP_T = 0.030         # translation cap, m
CAP_R = np.deg2rad(5.0)   # rotation bound (stage 2 only), rad
STEP_T = 0.005        # trust region per Gauss-Newton iteration: 5 mm ...
STEP_R = np.deg2rad(1.0)  # ... and 1 deg
ITERS = 60            # iteration cap per stage
DAMP = 1e-9           # Levenberg damping added to J^T J (m^2 units)
RAMP = 3              # linear ramp, frames, outside each end of a shifted segment
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
    R = Rot.from_rotvec(delta[3:]).as_matrix() if len(delta) > 3 else np.eye(3)
    D[:3, :3] = R
    D[:3, 3] = c - R @ c + delta[:3]
    return D


class Seg:
    def __init__(self, o, s, e):
        self.o, self.s, self.e = o, s, e
        self.delta = np.zeros(6); self.c = np.zeros(3); self.status = 'clean'; self.info = {}


def constraints(seg, frames_pairs, Pc, sdfs, table, delta, c, want_rows=True):
    """Per constraint frame: max depth (m); with want_rows: Jacobian rows [n,6] and depths [n] of the violators."""
    n_t, d_t = table
    o = seg.o; sd = sdfs[o]
    D = rigid(delta, c)
    fdepth, rows, deps = {}, [], []
    for t, partners in frames_pairs:
        M = D @ Pc[o][t]
        x = L.tf(M, sd.probes)
        h = x @ n_t + d_t
        dm = max(0.0, -h.min())
        if want_rows:
            v = h < 0
            if v.any():
                g = np.repeat(n_t[None], v.sum(), 0)
                rows.append(np.hstack([g, np.cross(x[v] - c, g)])); deps.append(-h[v])
        for p in partners:
            Mp = Pc[p][t]
            s, g = sdfs[p].query(L.tf(L.inv(Mp) @ M, sd.probes), grad=True)
            dm = max(dm, -s.min())
            if want_rows and (s < 0).any():
                v = s < 0
                gw = g[v] @ Mp[:3, :3].T
                rows.append(np.hstack([gw, np.cross(x[v] - c, gw)])); deps.append(-s[v])
            y = L.tf(Mp, sdfs[p].probes)
            s2, g2 = sd.query(L.tf(L.inv(M), y), grad=True)
            dm = max(dm, -s2.min())
            if want_rows and (s2 < 0).any():
                v = s2 < 0
                gw = g2[v] @ M[:3, :3].T
                rows.append(np.hstack([-gw, -np.cross(y[v] - c, gw)])); deps.append(-s2[v])
        fdepth[t] = dm
    if want_rows:
        R = np.vstack(rows) if rows else np.zeros((0, 6)); d = np.concatenate(deps) if deps else np.zeros(0)
        return fdepth, R, d
    return fdepth


def ok_frac(fd):
    v = np.array(list(fd.values()))
    return float(np.mean(v <= TOL)) if len(v) else 1.0


def solve(seg, fp, Pc, sdfs, table, c, dof):
    delta = np.zeros(6); hist = []
    for it in range(ITERS + 1):
        fd, R, d = constraints(seg, fp, Pc, sdfs, table, delta, c)
        q = ok_frac(fd)
        hist.append(dict(it=it, ok=round(q, 3), max_mm=round(1000 * max(fd.values()), 2), viol=int(len(d)),
                         t_mm=np.round(1000 * delta[:3], 2).tolist(), r_deg=round(float(np.degrees(np.linalg.norm(delta[3:]))), 2)))
        if q >= Q_OK:
            return delta, True, hist
        if it == ITERS or len(d) == 0:
            break
        A = R[:, :dof]
        H = A.T @ A + DAMP * len(d) * np.eye(dof)
        step = np.linalg.solve(H, A.T @ d)
        st = step[:3]; nt = np.linalg.norm(st)
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
            return delta, False, hist + [dict(it=it + 1, stop='translation cap')]
    return delta, False, hist


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
    J = L.hands(e)
    near, hd = {}, {}
    for o in names:
        near[o], hd[o] = hand_near(P, o, sdfs[o], J)
    segs, start = [], {}
    for o in names:
        start[o] = np.full(T, -1)
        for s, e_ in runs(~near[o]):
            if e_ - s + 1 >= L_MIN:
                segs.append(Seg(o, s, e_)); start[o][s:e_ + 1] = s
    vol = {o: sdfs[o].volume_cm3 for o in names}
    slot = {o: i for i, o in enumerate(names)}

    def mover(a, b, t):          # later rest start moves; tie: smaller volume moves; tie: later slot moves
        if start[a][t] != start[b][t]:
            return a if start[a][t] > start[b][t] else b
        if vol[a] != vol[b]:
            return a if vol[a] < vol[b] else b
        return a if slot[a] > slot[b] else b

    segs.sort(key=lambda g: (g.s, -vol[g.o], slot[g.o]))
    Pc = {n: P[n].copy() for n in names}
    for g in segs:
        fp = []
        for t in range(g.s, g.e + 1):
            fp.append((t, [p for p in names if p != g.o and start[p][t] >= 0 and mover(g.o, p, t) == g.o]))
        g.info['constraint_frames'] = len(fp)
        g.info['pair_frames'] = {p: int(sum(p in q for _, q in fp)) for p in names if p != g.o}
        tm = (g.s + g.e) // 2
        g.c = L.tf(Pc[g.o][tm], sdfs[g.o].vol_centroid[None])[0]
        fd0 = constraints(g, fp, Pc, sdfs, table, np.zeros(6), g.c, want_rows=False)
        g.info['before'] = dict(ok=round(ok_frac(fd0), 3), max_mm=round(1000 * max(fd0.values()), 2),
                                median_mm=round(1000 * float(np.median(list(fd0.values()))), 2))
        if variant == 'C' and g.s == 0:
            g.status = 'frame0_kept'
        elif ok_frac(fd0) >= Q_OK:
            g.status = 'clean'
        else:
            d3, ok3, h3 = solve(g, fp, Pc, sdfs, table, g.c, 3)
            g.info['stage1'] = h3[-1]
            if ok3:
                g.delta, g.status = d3, 'shift_t'
            else:
                d6, ok6, h6 = solve(g, fp, Pc, sdfs, table, g.c, 6)
                g.info['stage2'] = h6[-1]
                if ok6:
                    g.delta, g.status = d6, 'shift_tr'
                else:
                    g.status = 'unresolved'
        if variant == 'B' and g.status in ('clean', 'shift_t', 'shift_tr'):
            drop(g, fp, Pc, sdfs, table, names, start)
        if np.any(g.delta):
            D = rigid(g.delta, g.c)
            for t in range(g.s, g.e + 1):
                Pc[g.o][t] = D @ P[g.o][t]
            fd1 = constraints(g, fp, Pc, sdfs, table, np.zeros(6), g.c, want_rows=False)
            g.info['after'] = dict(ok=round(ok_frac(fd1), 3), max_mm=round(1000 * max(fd1.values()), 2),
                                   median_mm=round(1000 * float(np.median(list(fd1.values()))), 2))
    # ---- assemble with ramps (PREREG 4.6) ----
    Q = {n: P[n].copy() for n in names}
    for o in names:
        sg = sorted([g for g in segs if g.o == o], key=lambda g: g.s)
        nodes = [(g.s, g.e, g.delta, g.c) for g in sg]
        for i, (s, e_, d, c) in enumerate(nodes):
            for t in range(s, e_ + 1):
                Q[o][t] = rigid(d, c) @ P[o][t]
        # gaps: before first, between, after last
        bounds = [(-1, None)] + [(g.s, g.e) for g in sg] + [(T, None)]
        dl = [None] + [(g.delta, g.c) for g in sg] + [None]
        for i in range(len(bounds) - 1):
            a_end = bounds[i][1] if bounds[i][1] is not None else bounds[i][0]
            b_start = bounds[i + 1][0]
            gap = list(range(a_end + 1, b_start))
            if not gap:
                continue
            A, B = dl[i], dl[i + 1]
            zero = (np.zeros(6), None)
            A = A if A is not None else zero; B = B if B is not None else zero
            g_ = len(gap)
            for k, t in enumerate(gap, 1):
                if A[1] is not None and B[1] is not None and g_ <= 2 * RAMP:
                    f = k / (g_ + 1)
                    d = (1 - f) * A[0] + f * B[0]; c = (1 - f) * A[1] + f * B[1]
                else:
                    d = np.zeros(6); c = np.zeros(3)
                    if A[1] is not None and k <= RAMP:
                        d = d + A[0] * (1 - k / (RAMP + 1)); c = A[1]
                    kb = g_ + 1 - k
                    if B[1] is not None and kb <= RAMP:
                        d = d + B[0] * (1 - kb / (RAMP + 1)); c = B[1]
                if np.any(d):
                    Q[o][t] = rigid(d, c) @ P[o][t]
    od = f'{out_root}/ep{e}'
    os.makedirs(od, exist_ok=True)
    np.savez(f'{od}/poses_world_vo.npz', **Q)
    rep = dict(ep=e, variant=variant, objects=names, frames=T,
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


def drop(g, fp, Pc, sdfs, table, names, start):
    """Variant B: lower a floating rest segment along -n (table normal) by the largest s <= clearance (<= SUP_MAX)
    that keeps the segment resolved; clearance = median over frames of the min gap to the table and to every object at
    rest in the same frame."""
    n_t, d_t = table
    o = g.o; sd = sdfs[o]; D = rigid(g.delta, g.c)
    cl = []
    for t in range(g.s, g.e + 1):
        x = L.tf(D @ Pc[o][t], sd.probes)
        m = (x @ n_t + d_t).min()
        for p in names:
            if p != o and start[p][t] >= 0:
                m = min(m, sdfs[p].query(L.tf(L.inv(Pc[p][t]), x)).min())
        cl.append(m)
    c50 = float(np.median(cl)); g.info['clearance_mm'] = round(1000 * c50, 2)
    if not (SUP_MIN < c50 <= SUP_MAX):
        return
    fp_all = [(t, [p for p in names if p != o and start[p][t] >= 0]) for t, _ in fp]
    lo, hi = 0.0, c50
    for _ in range(12):                                            # bisection on the drop distance
        mid = 0.5 * (lo + hi)
        dd = g.delta.copy(); dd[:3] -= mid * n_t
        if ok_frac(constraints(g, fp_all, Pc, sdfs, table, dd, g.c, want_rows=False)) >= Q_OK:
            lo = mid
        else:
            hi = mid
    g.delta = g.delta.copy(); g.delta[:3] -= lo * n_t
    g.info['drop_mm'] = round(1000 * lo, 2)
    if lo > 0 and g.status == 'clean':
        g.status = 'drop'


if __name__ == '__main__':
    variant, root, out_root = sys.argv[1], sys.argv[2], sys.argv[3]
    sdfs = {}
    for e in [int(x) for x in sys.argv[4:]]:
        r = run_episode(e, variant, root, out_root, sdfs)
        print(e, variant, [(s['obj'], s['start'], s['end'], s['status'], s['t_norm_mm']) for s in r['segments']],
              r['seconds'], 's', flush=True)
