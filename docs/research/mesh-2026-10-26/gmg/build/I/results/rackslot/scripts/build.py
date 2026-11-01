"""Build a candidate rack piece set: the packed rack hulls, with every hull that reaches into the forbidden region
F = RV minus the rack mesh (RV: the guest's swept rest volume, rs_lib.rest_volume) replaced by convex cells of it.

Per touched hull P (method [H], GATES.md):
  K = what must stay: rack-mesh surface samples (0.3 mm spacing, seed 0) and rack-mesh 1 mm cell centres inside P;
  F = forbidden 1 mm cell centres inside P;  Q = all 1 mm cell centres of P (volume bookkeeping).
  clip(cell): up to MAX_CLIP planes, each keeping every K point of the cell and cutting off every F point beyond the
    K support in its direction (plane placed half a cell short of the nearest cut F centre, never past K); the normal
    is chosen among 1,000 Fibonacci directions to maximise (F cut) - W_COLL x (non-RV cells cut).
  split(cell): when F points remain inside the hull of the cell's K, cut the cell by a plane through the remaining F,
    chosen among 120 directions x 3 offsets (F quantiles 25/50/75 %) to minimise the F points still inside the hull
    of either half's K (1 mm decimated K for the choice); recurse (depth <= MAX_DEPTH).
  Every leaf is P intersected with half-spaces, so it is convex, lies inside P and keeps every K point of P.
Construction target (GATES.md Amendment 2): F' = F minus the cells whose centre is within BAND = 0.87 mm of the
rack-mesh surface (they straddle the surface at 1 mm resolution); K is unchanged (the mesh is never cut).
Then greedy merges of piece pairs into their joint hull. A merge never adds a cell of F' (band cells may be added). First every merge that adds
no new fill outside the packed union (it only restores packed fill; least added volume first); then, while the count
exceeds the packed count (the owner's piece-count rule, 43), the merges adding the least new fill, at most
MERGE_MAX_CM3 each and none of it inside the guest's packed pieces + clearance at ANY frame of the scope's episodes.

Usage: build.py SCOPE OUT_DIR    SCOPE: 30, 14 or both
"""
import json, os, sys, time
import numpy as np, trimesh
from scipy.spatial import ConvexHull, HalfspaceIntersection
from scipy.optimize import linprog
import rs_lib as L

MAX_CLIP = 6
MAX_DEPTH = int(os.environ.get('RS_DEPTH', 5))       # BSP depth (generic)
TOL_F = int(os.environ.get('RS_TOL', 20))   # leftover F cells (1 mm) allowed per leaf; generic, numerical (G2 <= 1 cm3 total)
KDEC = float(os.environ.get('RS_KDEC', 0.001))   # K decimation for the split choice (m)
BAND = 0.00087              # GATES.md Amendment 2: F cells within half a cell diagonal of the mesh surface are not targeted
W_COLL = 0.25              # collateral weight in the clip-plane choice (a non-RV cell cut counts 1/4 of an F cell)
MERGE_MAX_CM3 = 2.0        # largest NEW fill (outside the packed union) a merge may add (generic)
SAMPLE_M = 0.0003


def fib(n):
    i = np.arange(n) + 0.5
    phi = np.arccos(1 - 2 * i / n); th = np.pi * (1 + 5 ** 0.5) * i
    return np.stack([np.cos(th) * np.sin(phi), np.sin(th) * np.sin(phi), np.cos(phi)], 1)


DIRS = fib(1000)
SDIRS = fib(120)


def inside(eq, X, tol=1e-9):
    return np.all(X @ eq[:, :3].T + eq[:, 3] <= tol, 1) if len(eq) else np.ones(len(X), bool)


def hull_vertices(X):
    if len(X) < 5:
        return X
    try:
        return X[ConvexHull(X).vertices]
    except Exception:
        return X


def decimate(X, pitch=0.001):
    if not len(X):
        return X
    k = np.floor(X / pitch).astype(np.int64)
    _, idx = np.unique(k, axis=0, return_index=True)
    return X[idx]


def trapped(K, F):
    """F points inside the convex hull of K."""
    if len(K) < 5 or not len(F):
        return 0
    try:
        e = ConvexHull(K).equations
    except Exception:
        return 0
    return int(inside(e, F, 1e-9).sum())


def clip(K, F, Q, notRV):
    """Planes (n, b) with kept side n.x <= b. Returns planes, F left, Q kept mask."""
    planes = []
    Fm = np.ones(len(F), bool); Qm = np.ones(len(Q), bool)
    Kv = hull_vertices(K)
    for _ in range(MAX_CLIP):
        if Fm.sum() <= TOL_F:
            break
        Fr = F[Fm]
        bK = (Kv @ DIRS.T).max(0)                       # (D,)
        s = Fr @ DIRS.T                                  # (nF, D)
        rem = s > bK[None, :] + 1e-7
        nrem = rem.sum(0)
        if nrem.max() == 0:
            break
        smin = np.where(rem, s, np.inf).min(0)
        b = np.maximum(bK, smin - 0.0005)
        cand = np.nonzero(nrem > 0)[0]
        Qa = Q[Qm & notRV]
        coll = np.array([(Qa @ DIRS[j] > b[j]).sum() for j in cand])
        score = nrem[cand] - W_COLL * coll
        j = cand[int(np.argmax(score))]
        if score.max() <= 0:
            break
        n, bb = DIRS[j], b[j]
        planes.append((n.tolist(), float(bb)))
        Fm &= ~(F @ n > bb)
        Qm &= ~(Q @ n > bb)
    return planes, Fm, Qm


def best_split(Kd, F):
    """Plane through the F region that leaves the fewest F points inside the hull of either half's K."""
    best = None
    dirs = list(SDIRS)
    for X in (F, Kd):
        if len(X) > 3:
            w, v = np.linalg.eigh(np.cov((X - X.mean(0)).T))
            dirs += [v[:, k] for k in range(3)]
    for n in dirs:
        s = F @ n; k = Kd @ n
        for q in (10, 30, 50, 70, 90):
            b = float(np.percentile(s, q))
            Kp, Km = Kd[k > b], Kd[k <= b]
            if len(Kp) < 20 or len(Km) < 20:
                continue
            t = trapped(Kp, F[s > b]) + trapped(Km, F[s <= b])
            key = (t, abs(len(Kp) - len(Km)))
            if best is None or key < best[0]:
                best = (key, np.asarray(n).copy(), b)
    return best


def process(eq, K, F, Q, notRV, depth, log, tag):
    """Returns leaves: list of dict(planes=[(n,b)], F_left, Q_kept)."""
    planes, Fm, Qm = clip(K, F, Q, notRV)
    if Fm.sum() <= TOL_F or depth >= MAX_DEPTH:
        return [dict(planes=planes, F_left=int(Fm.sum()), Q_kept=int(Qm.sum()), tag=tag, depth=depth)]
    Kd = decimate(K, KDEC)
    bs = best_split(Kd, F)
    if bs is None:
        return [dict(planes=planes, F_left=int(Fm.sum()), Q_kept=int(Qm.sum()), tag=tag, depth=depth)]
    (t, _), n, b = bs
    log(f'  split {tag} depth {depth}: F {len(F)} (clip alone leaves {int(Fm.sum())}), trapped after split {t}')
    out = []
    for sgn, sub in ((1, 'a'), (-1, 'b')):
        # half 'a': n.x >= b  ->  -n.x <= -b ; half 'b': n.x <= b
        nn, bb = (-n, -b) if sgn == 1 else (n, b)
        mk, mf, mq = K @ nn <= bb + 1e-12, F @ nn <= bb, Q @ nn <= bb
        if mk.sum() == 0:
            continue
        leaves = process(eq, K[mk], F[mf], Q[mq], notRV[mq], depth + 1, log, tag + sub)
        for lf in leaves:
            lf['planes'] = [(nn.tolist(), float(bb))] + lf['planes']
        out += leaves
    return out


def cell_vertices(eq, planes):
    A = np.vstack([eq[:, :3]] + [np.array(n)[None] for n, b in planes])
    c = np.concatenate([eq[:, 3]] + [np.array([-b]) for n, b in planes])        # A x + c <= 0
    norm = np.linalg.norm(A, axis=1)
    res = linprog(np.r_[np.zeros(3), -1], A_ub=np.hstack([A, norm[:, None]]), b_ub=-c,
                  bounds=[(None, None)] * 3 + [(0, None)], method='highs')
    if not res.success or res.x[3] <= 1e-6:
        return None, 0.0
    hs = HalfspaceIntersection(np.hstack([A, c[:, None]]), res.x[:3])
    V = hs.intersections
    return V, float(res.x[3])


def write_obj(path, V):
    m = trimesh.convex.convex_hull(V)
    m.export(path)
    return m


def main():
    scope, out = sys.argv[1], sys.argv[2]
    eps = ['30', '14'] if scope == 'both' else [scope]
    os.makedirs(f'{out}/plastic_dish_rack', exist_ok=True)
    lf = open(f'{out}/build.log', 'w')

    def log(s):
        line = time.strftime('%H:%M:%S ', time.gmtime()) + s
        print(line, flush=True); lf.write(line + '\n'); lf.flush()
    t0 = time.time()
    rack = L.load_mesh(L.RACK_MESH); H = L.load_hulls(L.RACK_PACKED); G = L.Grid(H)
    z0 = np.load(f'{L.SCR}/rackslot/grid_base.npz'); M, PK = z0['M'], z0['PK']
    RV = np.zeros(G.n, bool); frames = {}; swept_all = []
    for ep in eps:
        R, info = L.rest_frames(ep); P = L.poses(ep); gh = L.load_hulls(L.GUEST[ep]['packed'])
        frames[ep] = dict(R=R, **info)
        RV |= L.rest_volume(G, gh, P['rel'], R, PK)
        swept_all.append((gh, P['rel']))

    def in_swept_all(occ):
        """Any cell of OCC inside the guest's packed pieces + clearance at ANY frame of the scope's episodes."""
        n = 0
        for gh, rel in swept_all:
            n += L.rest_volume(G, gh, rel, list(range(len(rel))), occ).sum()
        return int(n)
    F_all = RV & PK & ~M
    rack_s = np.asarray(trimesh.sample.sample_surface_even(rack, int(rack.area / 0.0003 ** 2), seed=3)[0])
    from scipy.spatial import cKDTree
    fi = np.argwhere(F_all)
    dsurf = cKDTree(rack_s).query(G.lo + (fi + 0.5) * G.pitch)[0]
    F = np.zeros(G.n, bool)
    keep = dsurf > BAND
    F[fi[keep, 0], fi[keep, 1], fi[keep, 2]] = True          # F' (GATES.md Amendment 2): F beyond the surface band
    log(f'F all {F_all.sum() / 1e3:.2f} cm3, band (<= {BAND * 1e3:.2f} mm from the mesh surface) {(~keep).sum() / 1e3:.2f}, '
        f"F' {F.sum() / 1e3:.2f}")
    log(f'scope {scope}: R {[len(v["R"]) for v in frames.values()]}, RV {RV.sum() / 1e3:.2f} cm3, '
        f'F {F.sum() / 1e3:.2f} cm3 ({time.time() - t0:.0f} s)')
    S = np.asarray(trimesh.sample.sample_surface_even(rack, int(rack.area / SAMPLE_M ** 2), seed=0)[0])
    Mc, Fc = G.centres(M), G.centres(F)
    pieces, report = [], []
    for i, V in enumerate(H):
        eq = ConvexHull(V).equations
        fin = inside(eq, Fc)
        if fin.sum() <= TOL_F:
            pieces.append(dict(src=i, V=V, kind='packed'))
            continue
        lo, hi = V.min(0) - 1e-3, V.max(0) + 1e-3
        Ks = S[np.all((S >= lo) & (S <= hi), 1)]; Ks = Ks[inside(eq, Ks)]
        Km = Mc[np.all((Mc >= lo) & (Mc <= hi), 1)]; Km = Km[inside(eq, Km)]
        K = np.vstack([Ks, Km])
        occ = G.hull_occ(V)
        Q = G.centres(occ)
        idx = np.floor((Q - G.lo) / G.pitch).astype(int)
        notRV = ~RV[idx[:, 0], idx[:, 1], idx[:, 2]]
        log(f'piece {i}: F {int(fin.sum())} cells, K {len(K)}, Q {len(Q)}')
        leaves = process(eq, K, Fc[fin], Q, notRV, 0, log, f'p{i}')
        for lfv in leaves:
            Vc, r = cell_vertices(eq, lfv['planes'])
            if Vc is None:
                log(f'  leaf {lfv["tag"]}: empty cell, dropped'); continue
            pieces.append(dict(src=i, V=Vc, kind='cut', tag=lfv['tag'], planes=lfv['planes'], F_left=lfv['F_left'],
                               cheb_mm=round(r * 1e3, 2)))
            log(f'  leaf {lfv["tag"]}: planes {len(lfv["planes"])}, F left {lfv["F_left"]}, '
                f'vol {ConvexHull(Vc).volume * 1e6:.2f} cm3, verts {len(Vc)}')
        report.append(dict(piece=i, F_cells=int(fin.sum()), K=len(K), leaves=len(leaves),
                           vol_cm3=round(ConvexHull(V).volume * 1e6, 2)))
    log(f'after cut: {len(pieces)} pieces ({time.time() - t0:.0f} s)')
    # merges (GATES.md C1: <= the packed count): a merge never adds an RV cell; first every merge whose hull adds
    # no new fill outside the packed union (it only restores packed fill), then, while the count exceeds the packed
    # count, the merges adding the least new fill (<= MERGE_MAX_CM3, none of it where the guest goes at any frame)
    merges = []
    target = len(H)
    occs = [G.hull_occ(p['V']) for p in pieces]
    cache = {}

    def pair_eval(a, b):
        Va, Vb = pieces[a]['V'], pieces[b]['V']
        if np.any(Va.min(0) > Vb.max(0) + 0.002) or np.any(Vb.min(0) > Va.max(0) + 0.002):
            return None
        Vm = np.vstack([Va, Vb])
        mo = G.hull_occ(Vm)
        added = mo & ~(occs[a] | occs[b])
        if (added & F).sum() > 0:
            return None
        newf = added & ~PK
        nn = int(newf.sum())
        if nn * 1e-3 > MERGE_MAX_CM3:
            return None
        return (nn, int(added.sum()))

    for u, p in enumerate(pieces):
        p['uid'] = u
    uid_next = [len(pieces)]

    def key(a, b):
        return (pieces[a]['uid'], pieces[b]['uid'])
    while True:
        best = None
        for a in range(len(pieces)):
            for b in range(a + 1, len(pieces)):
                kk = key(a, b)
                if kk not in cache:
                    cache[kk] = pair_eval(a, b)
                ev = cache[kk]
                if ev is None:
                    continue
                if ev[0] > 0 and len(pieces) <= target:
                    continue
                if best is None or ev < best[0]:
                    best = (ev, a, b)
        if best is None:
            break
        (nn, na), a, b = best
        if nn > 0:
            mo = G.hull_occ(np.vstack([pieces[a]['V'], pieces[b]['V']]))
            if in_swept_all(mo & ~(occs[a] | occs[b]) & ~PK) > 0:
                cache[key(a, b)] = None
                continue
        Vm = np.vstack([pieces[a]['V'], pieces[b]['V']])
        Vm = Vm[ConvexHull(Vm).vertices]
        mo_ = G.hull_occ(np.vstack([pieces[a]['V'], pieces[b]['V']]))
        band_add = int((mo_ & ~(occs[a] | occs[b]) & RV).sum())
        merges.append(dict(a=pieces[a].get('tag') or f'p{pieces[a]["src"]}', b=pieces[b].get('tag') or f'p{pieces[b]["src"]}',
                           new_fill_cm3=nn / 1e3, added_cm3=na / 1e3, band_cells_added=band_add))
        log(f'merge {merges[-1]} -> {len(pieces) - 1} pieces')
        mo = G.hull_occ(Vm)
        tag = f"({merges[-1]['a']}+{merges[-1]['b']})"
        srcs = [x for p in (pieces[a], pieces[b]) for x in (p['src'] if isinstance(p['src'], list) else [p['src']])]
        pieces = [p for k, p in enumerate(pieces) if k not in (a, b)] + [dict(src=srcs, V=Vm, kind='merged', tag=tag,
                                                                              uid=uid_next[0])]
        uid_next[0] += 1
        occs = [o for k, o in enumerate(occs) if k not in (a, b)] + [mo]
    log(f'after merges: {len(pieces)} pieces ({time.time() - t0:.0f} s)')
    files = []
    for k, p in enumerate(pieces):
        m = write_obj(f'{out}/plastic_dish_rack/piece_{k:02d}.obj', p['V'])
        files.append(dict(file=f'piece_{k:02d}.obj', src=[int(x) for x in p['src']] if isinstance(p['src'], list)
                          else int(p['src']), kind=p['kind'], tag=p.get('tag'), verts=len(m.vertices),
                          vol_cm3=round(m.volume * 1e6, 3), watertight=bool(m.is_watertight)))
    json.dump(dict(scope=scope, episodes=frames, constants=dict(MAX_CLIP=MAX_CLIP, MAX_DEPTH=MAX_DEPTH, TOL_F=TOL_F, KDEC=KDEC,
                   W_COLL=W_COLL, MERGE_MAX_CM3=MERGE_MAX_CM3, SAMPLE_M=SAMPLE_M, CLEAR=L.CLEAR, PITCH=L.PITCH),
                   RV_cm3=RV.sum() / 1e3, F_all_cm3=F_all.sum() / 1e3, F_target_cm3=F.sum() / 1e3, touched=report,
                   merges=merges, pieces=files, n_pieces=len(files), secs=round(time.time() - t0, 1)),
              open(f'{out}/build.json', 'w'), indent=1, default=float)
    log(f'done: {len(files)} pieces, {time.time() - t0:.0f} s')


if __name__ == '__main__':
    main()
