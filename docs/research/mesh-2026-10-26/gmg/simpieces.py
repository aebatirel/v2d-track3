"""Simulator copy as convex pieces CoACD cannot refill (INTERLOCK.md 6.1, PREREG F-I1.8; build step BI1).

Port of pipeline/collision_decomp.py (free-space-guided split; Warp signed distance replaced by gmg.geom winding
numbers) and of pipeline/interaction_carve.py clip / region_cut (exact convex clipping), applied to OUR pick, never to
library meshes. FlashCHORD's CoACD returns each convex piece unchanged, so `make_assets.py --pieces` keeps them.

  solid_grid(mesh, pitch)                         grid points inside the mesh (pitch 2 mm)
  keepout_points(...)                             keep-out = carved + FREE + SIL + persistent partner occupancy, within
                                                  2 voxels of the surface, outside the carved solid
  decompose(mesh, carve_sub=None, keep=...)       convex pieces: split by the plane that minimises the weighted keep-out
                                                  volume inside the children until every hull holds <= 0.3 cm3, cap
                                                  32 (64 above 300 cm3), <= 64 vertices per hull
  remove_box(hulls, box)                          exact removal of an oriented box from convex hulls (<= 6 parts each)
  remove_voxels(...)                              voxel carves: decomposition of the carved solid with the carve as
                                                  keep-out (weight 10)
  build(...)                                      default and carved pieces of one object, with the report
  fit_mesh(hulls)                                 union of the pieces (one watertight mesh: the `_fit` mesh)
  props(hulls, mass)                              COM and inertia of the uniform solid of the pieces
  pieces_gate(sets, KP, KW)                       F-I3.8: deliver only a piece set with <= 0.3 cm3 keep-out per hull
                                                  (ours, else CoACD's), else mark the delivery do-not-use
  write_round(...)                                RUN/sim/<split>/ep<N>/r<k>/ layout + manifest gmg-sim/2 (objects.<obj>.
                                                  {files, fiducials}, code identity, interlock state), props_gmg.json in
                                                  the phys_fit layout (F-I3.9)
"""
from __future__ import annotations

import hashlib
import json
import os

import numpy as np
import trimesh
from scipy.optimize import linprog
from scipy.spatial import ConvexHull, HalfspaceIntersection

from gmg import guard, geom

C = dict(
    pitch_m=(0.002, 'generic:F-I1.8 solid at 1.5-2 mm'),
    tol_cm3=(0.3, 'informed:F-I1.14 0.3 cm3 keep-out (collision_decomp.py, 26 Oct)'),
    max_pieces=(32, 'informed:F-I1.14 32/64 pieces (collision_decomp.py)'),
    max_pieces_big=(64, 'informed:F-I1.14 32/64 pieces (collision_decomp.py)'),
    big_cm3=(300.0, 'informed:F-I1.14 64 pieces above 300 cm3 (collision_decomp.py)'),
    maxv=(64, 'informed:F-I1.14 64 vertices per hull (MuJoCo limit)'),
    margin_m=(0.00075, 'generic:collision_decomp.py free margin 0.75 mm'),
    overlap_m=(0.001, 'generic:collision_decomp.py cells overlap 1 mm across a cut'),
    lam=(10.0, 'generic:collision_decomp.py partner weight 10'),
    near_vox=(2, 'generic:F-I1.8 keep-out within 2 voxels of the surface'),
    mass_kg=(0.3, 'generic:F-I1.14 placeholder mass 0.3 kg (make_assets default; owner decision D-I1 open)'),
    nsurf=(60000, 'generic:numerical surface samples'),
)


def k_(name):
    v, o = C[name]
    if o.startswith('generic'):
        guard.constant(f'sp.{name}', v, o)
    return v


def inside_eq(eq, Q, tol=1e-9, chunk=4000000):
    out = np.zeros(len(Q), bool)
    if len(Q) == 0:
        return out
    step = max(1000, chunk // max(1, len(eq)))
    for i in range(0, len(Q), step):
        out[i:i + step] = np.all(Q[i:i + step] @ eq[:, :3].T + eq[:, 3] <= tol, axis=1)
    return out


def inside_any(hulls, Q):
    hit = np.zeros(len(Q), bool)
    for V in hulls:
        hit |= inside_eq(ConvexHull(V).equations, Q)
    return hit


def reduce_hull(V, k):
    """At most k vertices by furthest-point insertion (collision_decomp.reduce_hull)."""
    if len(V) <= k:
        return V
    c = V.mean(0); ax = np.linalg.svd(V - c, full_matrices=False)[2]
    sel = sorted({int(np.argmax(V @ (s * u))) for u in ax for s in (1, -1)} |
                 {int(np.argmax(np.linalg.norm(V - c, axis=1)))})
    while len(sel) < k:
        try:
            eq = ConvexHull(V[sel]).equations
        except Exception:
            sel.append(int(np.argmax(np.linalg.norm(V - V[sel].mean(0), axis=1)))); continue
        dist = (V @ eq[:, :3].T + eq[:, 3]).max(1)
        j = int(np.argmax(dist))
        if dist[j] <= 1e-7:
            break
        sel.append(j)
    return V[sel]


def grid_points(lo, hi, pitch):
    n = np.ceil((hi - lo) / pitch).astype(int) + 1
    return np.stack(np.meshgrid(*[lo[k] + pitch * np.arange(n[k]) for k in range(3)], indexing='ij'), -1).reshape(-1, 3)


def solid_grid(mesh, pitch):
    lo = mesh.bounds[0] - 2 * pitch; hi = mesh.bounds[1] + 2 * pitch
    G = grid_points(lo, hi, pitch)
    from gmg.interlock import fast_inside
    ins = fast_inside(mesh, G)
    return G, ins


def decompose(SOL, SURF, KEEP, KW, pitch, tol=None, max_pieces=None, maxv=None, log=None):
    """collision_decomp.decompose on given point sets: SOL solid grid points, SURF surface samples, KEEP keep-out points
    with weights KW. Returns (hulls, report)."""
    tol = k_('tol_cm3') if tol is None else tol
    VOX = pitch ** 3 * 1e6
    if max_pieces is None:
        max_pieces = k_('max_pieces_big') if len(SOL) * VOX > k_('big_cm3') else k_('max_pieces')
    maxv = maxv or k_('maxv')
    ov = k_('overlap_m')
    PTS = np.vstack([SURF, SOL])
    gax = np.linalg.svd(SOL - SOL.mean(0), full_matrices=False)[2] if len(SOL) > 3 else np.eye(3)
    rng = np.random.default_rng(0)

    class Piece:
        def __init__(self, idx):
            self.idx = idx
            h = ConvexHull(PTS[idx]); self.eq, self.V = h.equations, PTS[idx][h.vertices]
            k = inside_eq(self.eq, KEEP)
            self.F = KEEP[k]; self.FW = KW[k]; self.excess = self.FW.sum() * VOX

    def split(pc):
        P = PTS[pc.idx]
        axes = [*np.linalg.svd(P - P.mean(0), full_matrices=False)[2], *gax]
        if len(pc.F) >= 10:
            axes += [*np.linalg.svd(pc.F - pc.F.mean(0), full_matrices=False)[2]]
        U = []
        for u in axes:
            u = u / np.linalg.norm(u)
            if all(abs(u @ w) < 0.985 for w in U):
                U.append(u)
        sub = P if len(P) <= 6000 else P[rng.choice(len(P), 6000, replace=False)]
        ks = np.arange(len(pc.F)) if len(pc.F) <= 40000 else rng.choice(len(pc.F), 40000, replace=False)
        Fs, Ws = pc.F[ks], pc.FW[ks]; scale = len(pc.F) / max(1, len(Fs)); best = None
        for u in U:
            s = sub @ u; offs = list(np.quantile(s, np.linspace(0.05, 0.95, 19)))
            if len(pc.F):
                fs = pc.F @ u; offs += [fs.min() - 0.5 * pitch, fs.max() + 0.5 * pitch, float(np.median(fs))]
            for o in offs:
                L = sub[s <= o + ov]; R = sub[s >= o - ov]
                if len(L) < 20 or len(R) < 20:
                    continue
                try:
                    eL = ConvexHull(L).equations; eR = ConvexHull(R).equations
                except Exception:
                    continue
                sc = (Ws[inside_eq(eL, Fs)].sum() + Ws[inside_eq(eR, Fs)].sum()) * scale * VOX
                if best is None or sc < best[0]:
                    best = (sc, u, o)
        return best

    pieces = [Piece(np.arange(len(PTS)))]
    steps = []
    while len(pieces) < max_pieces:
        pieces.sort(key=lambda p: -p.excess)
        pc = pieces[0]
        if pc.excess <= tol:
            break
        best = split(pc)
        if best is None or best[0] >= 0.9 * pc.excess:
            steps.append(dict(stuck=round(pc.excess, 3))); pc.excess = -pc.excess - 1e-9; continue
        s = PTS[pc.idx] @ best[1]
        li, ri = pc.idx[s <= best[2] + ov], pc.idx[s >= best[2] - ov]
        if len(li) < 4 or len(ri) < 4:
            pc.excess = -pc.excess - 1e-9; continue
        l, r = Piece(li), Piece(ri)
        steps.append(dict(parent=round(pc.excess, 3), children=[round(l.excess, 3), round(r.excess, 3)]))
        pieces = pieces[1:] + [l, r]
    hulls, rows = [], []
    for p in sorted(pieces, key=lambda p: -len(p.idx)):
        V = reduce_hull(p.V, maxv)
        eq = ConvexHull(V).equations
        hulls.append(V)
        rows.append(dict(verts=int(len(V)), excess_cm3=round(float(KW[inside_eq(eq, KEEP)].sum()) * VOX, 3)))
    rep = dict(n_pieces=len(hulls), pitch_mm=round(pitch * 1e3, 2), tol_cm3=tol, max=max_pieces,
               max_piece_excess_cm3=max(r['excess_cm3'] for r in rows) if rows else 0.0, steps=len(steps), pieces=rows)
    return hulls, rep


# --------------------------------------------------------------------------- exact convex clipping (interaction_carve)
def clip(V, planes):
    """Convex hull of V intersected with half-spaces n.x + d <= 0; None if empty or thinner than a 0.2 mm ball."""
    try:
        eq = ConvexHull(V).equations
    except Exception:
        return None
    H = np.vstack([eq] + [np.r_[n, d][None] for n, d in planes])
    A, b = H[:, :3], -H[:, 3]; nrm = np.linalg.norm(A, axis=1)
    res = linprog(np.r_[0, 0, 0, -1.0], A_ub=np.c_[A, nrm], b_ub=b, bounds=[(None, None)] * 3 + [(0, None)])
    if not res.success or res.x[3] < 2e-4:
        return None
    try:
        P = HalfspaceIntersection(H, res.x[:3]).intersections
        return P[ConvexHull(P).vertices]
    except Exception:
        return None


def box_planes(box):
    """The 6 half-spaces (n, d) with n.x + d <= 0 inside an oriented box {axes A (3x3 rows), centre, half}."""
    A = np.asarray(box['axes'], float); c = np.asarray(box['centre'], float); h = np.asarray(box['half'], float)
    out = []
    for i in range(3):
        out.append((A[i], -(A[i] @ c + h[i])))           # A_i.x <= A_i.c + h_i
        out.append((-A[i], (A[i] @ c - h[i])))           # -A_i.x <= -(A_i.c - h_i)
    return out


def remove_box(hulls, box):
    """Remove an oriented box from every hull: a hull meeting the box is replaced by its disjoint convex parts outside
    the box (part i = outside face i and inside faces < i); untouched hulls stay whole."""
    P = box_planes(box)
    out, touched = [], 0
    for V in hulls:
        if clip(V, P) is None:
            out.append(V); continue
        touched += 1
        for i, (n, d) in enumerate(P):
            planes = [(-n, -d)] + P[:i]                    # outside face i: n.x + d >= 0
            Q = clip(V, planes)
            if Q is not None and len(Q) >= 4:
                out.append(Q)
    return out, touched


def hull_volume(hulls):
    return float(sum(ConvexHull(V).volume for V in hulls))


def union_points(hulls, pitch=0.0015):
    P = np.vstack(hulls); G = grid_points(P.min(0) - pitch, P.max(0) + pitch, pitch)
    return G[inside_any(hulls, G)]


def fit_mesh(hulls):
    """One watertight mesh = union of the convex pieces (manifold boolean)."""
    ms = [trimesh.convex.convex_hull(V) for V in hulls]
    if len(ms) == 1:
        return ms[0]
    return trimesh.boolean.union(ms, engine='manifold')


def props(hulls, mass, pitch=0.0015):
    """COM and inertia (about the COM) of the uniform solid of the pieces' union (grid samples)."""
    X = union_points(hulls, pitch)
    c = X.mean(0); d = X - c
    I = mass * (np.eye(3) * (d ** 2).sum(1).mean() - (d[:, :, None] * d[:, None, :]).mean(0))
    return dict(com=c.tolist(), inertia=I.tolist(), mass=float(mass), volume_cm3=round(len(X) * pitch ** 3 * 1e6, 2))


def keepout_points(mesh_sol_pts, G, ins, pitch, ev, near_m, carve_mask=None, partner_occ_lin=None, sil_lin=None):
    """Keep-out points: grid points G outside the solid (ins False) by more than the margin approximation (the
    grid cell centre is outside), within near_m of a solid point, and either in a FREE or SIL voxel of the target's
    grid, in the carved region, or in the partner's persistent occupancy. Weights: carved and partner = lam, else 1."""
    from scipy.spatial import cKDTree
    from gmg.interlock import STATE_FREE
    out = ~ins
    if carve_mask is not None:
        out = out | carve_mask
    S = G[~out]
    tree = cKDTree(S)
    dist, _ = tree.query(G[out], k=1, distance_upper_bound=near_m + 1e-9)
    cand = np.nonzero(out)[0][np.isfinite(dist)]
    X = G[cand]
    lin, ok = ev.grid.lin(X)
    st = np.full(len(X), -1); st[ok] = ev.state[lin[ok]]
    w = np.zeros(len(X))
    w[st == STATE_FREE] = 1.0
    if sil_lin is not None and len(sil_lin):
        sm = np.zeros(ev.grid.size, bool); sm[sil_lin] = True
        w[ok & sm[np.maximum(lin, 0)]] = np.maximum(w[ok & sm[np.maximum(lin, 0)]], 1.0)
    if partner_occ_lin is not None and len(partner_occ_lin):
        pm = np.zeros(ev.grid.size, bool); pm[partner_occ_lin] = True
        sel = ok & pm[np.maximum(lin, 0)]
        w[sel] = k_('lam')
    if carve_mask is not None:
        w[carve_mask[cand]] = k_('lam')
    keep = w > 0
    return X[keep], w[keep]


def build(mesh, ev, carves=(), partner_occ_lin=None, sil_lin=None, log=None):
    """Default and carved pieces of one object (pick MESH, target evidence EV). carves: list of solids from
    interlock.carve_solid (box or voxels). Returns dict(default=hulls, carved=hulls or None, report)."""
    pitch = k_('pitch_m')
    m = trimesh.Trimesh(np.asarray(mesh.vertices), np.asarray(mesh.faces), process=True)
    G, ins = solid_grid(m, pitch)
    SURF = geom.surface_samples(m, k_('nsurf'), seed=0)[0]
    near = k_('near_vox') * ev.grid.vox
    KP, KW = keepout_points(None, G, ins, pitch, ev, near, None, partner_occ_lin, sil_lin)
    default, rep_d = decompose(G[ins], SURF, KP, KW, pitch)
    rep = dict(default=rep_d, solid_cm3=round(float(ins.sum()) * pitch ** 3 * 1e6, 2), keepout_points=int(len(KP)))
    if not carves:
        return dict(default=default, carved=None, report=rep, keep=(KP, KW))
    carved = list(default)
    vox_carves = [c for c in carves if c['kind'] == 'voxels']
    box_carves = [c for c in carves if c['kind'] == 'box']
    if vox_carves:
        sl = np.concatenate([c['sub_lin'] for c in vox_carves])
        Cs = ev.sgrid.centres(sl)
        from scipy.spatial import cKDTree
        dd, _ = cKDTree(Cs).query(G, k=1)
        cm = dd <= ev.sgrid.vox * 0.75
        ins2 = ins & ~cm
        SURF2 = SURF[cKDTree(Cs).query(SURF, k=1)[0] > ev.sgrid.vox * 0.75]
        KP2, KW2 = keepout_points(None, G, ins2, pitch, ev, near, cm, partner_occ_lin, sil_lin)
        carved, rep_c = decompose(G[ins2], SURF2, KP2, KW2, pitch)
        rep['carved_voxels'] = rep_c
    touched = 0
    for bx in box_carves:
        carved, t = remove_box(carved, bx)
        touched += t
    for i, V in enumerate(carved):
        carved[i] = reduce_hull(V, k_('maxv'))
    rep['box_cut'] = dict(boxes=len(box_carves), hulls_touched=touched, pieces=len(carved))
    return dict(default=default, carved=carved, report=rep, keep=(KP, KW))


# --------------------------------------------------------------------------- delivery layout (6.1)
def _sha(p):
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for blk in iter(lambda: f.read(1 << 20), b''):
            h.update(blk)
    return h.hexdigest()


def fiducials(hulls):
    """8 fiducials of an object (file coordinates; F-I3.9 definition): the oriented bounding box of ALL vertices of
    its pieces, with axes = the principal axes (SVD) of those vertices about their mean; each corner is moved 1 mm
    inward along each of the three box axes (so a corner moves sqrt(3) = 1.73 mm along the box diagonal and every box
    face lies 1 mm inside the extreme vertex on that side). The Embodiment tool's fiducial_box check expects exactly
    this (margins 1 mm on every face)."""
    P = np.vstack(hulls)
    c = P.mean(0); U = np.linalg.svd(P - c, full_matrices=False)[2]
    A = (P - c) @ U.T
    lo, hi = A.min(0) + 0.001, A.max(0) - 0.001
    cs = np.array([[x, y, z] for x in (lo[0], hi[0]) for y in (lo[1], hi[1]) for z in (lo[2], hi[2])])
    return (cs @ U + c).tolist()


def keepout_excess(hulls, KP, KW, pitch=None):
    """Keep-out volume (cm3) inside each convex piece (the F-I1.8 per-hull quantity, weights as in decompose)."""
    pitch = k_('pitch_m') if pitch is None else pitch
    VOX = pitch ** 3 * 1e6
    return [float(KW[inside_eq(ConvexHull(V).equations, KP)].sum()) * VOX for V in hulls]


def pieces_gate(sets, KP, KW, tol=None):
    """F-I3.8: the delivered pieces must hold <= tol (0.3 cm3) of keep-out per hull (F-I1.8). SETS = {name: hulls}
    in preference order (ours first, then CoACD's): the first set that complies is chosen; if none does, the set with
    the smallest maximum is reported and the delivery is marked do-not-use. Returns dict(choice, hulls, report,
    do_not_use)."""
    tol = k_('tol_cm3') if tol is None else tol
    rep, first = {}, None
    for name, hl in sets.items():
        if hl is None:
            continue
        ex = keepout_excess(hl, KP, KW)
        rep[name] = dict(n=len(hl), max_cm3=round(max(ex), 3) if ex else 0.0, sum_cm3=round(sum(ex), 3),
                         over_tol=int(sum(e > tol for e in ex)))
        if first is None and (max(ex) if ex else 0.0) <= tol:
            first = name
    if first is not None:
        return dict(choice=first, hulls=sets[first], report=rep, do_not_use=None)
    best = min(rep, key=lambda k: rep[k]['max_cm3'])
    return dict(choice=best, hulls=sets[best], report=rep,
                do_not_use=f'no piece set holds <= {tol} cm3 of keep-out per hull (F-I1.8): '
                           + ', '.join(f'{k} max {v["max_cm3"]} cm3' for k, v in rep.items()))


def write_object(out_dir, obj, visual_mesh, hulls, carve_rec):
    d = os.path.join(out_dir, obj)
    os.makedirs(d, exist_ok=True)
    vm = trimesh.Trimesh(np.asarray(visual_mesh.vertices), np.asarray(visual_mesh.faces), process=True)
    vm.export(os.path.join(d, f'{obj}.glb'))
    for k, V in enumerate(hulls):
        trimesh.convex.convex_hull(V).export(os.path.join(d, f'piece_{k:02d}.obj'))
    pr = props(hulls, k_('mass_kg'))
    with open(os.path.join(d, 'inertia.json'), 'w') as fh:
        json.dump(pr, fh, indent=1)
    with open(os.path.join(d, 'carve.json'), 'w') as fh:
        json.dump(carve_rec, fh, indent=1, default=str)
    os.makedirs(os.path.join(out_dir, '_fit'), exist_ok=True)
    fm = fit_mesh(hulls)
    fm.export(os.path.join(out_dir, '_fit', f'{obj}.glb'))
    return pr, dict(watertight_fit=bool(fm.is_watertight))


CODE_FILES = ('interlock.py', 'simpieces.py', 'simphys.py', 'silhouette.py', 'gen_slot.py', 'physcheck.py',
              'tools/interlock_dev.py', 'platebody.py', 'collcarve.py', 'cavpieces.py')


def code_identity():
    """The code that wrote a delivery (non-blocking review item): HEAD of the checkout, whether the gmg interlock files
    differ from HEAD (dirty), and the sha256 of each of them, so the identity holds without a clean commit."""
    here = os.path.dirname(os.path.abspath(__file__))
    sha = {f: _sha(os.path.join(here, f)) for f in CODE_FILES if os.path.exists(os.path.join(here, f))}
    dirty = guard._git('status', '--porcelain', '--', *[os.path.join(here, f) for f in CODE_FILES])
    return dict(commit=guard._git('rev-parse', 'HEAD'), dirty=bool(dirty and str(dirty).strip()),
                dirty_files=str(dirty).strip().splitlines() if dirty else [], sha256=sha)


def write_round(out_dir, episode, split, round_k, objects, p_sim, commit=None, interlock=None, extra=None,
                dnu_rule='F-I3.8'):
    """objects: {obj: dict(visual=mesh, hulls=list, carve=dict[, gate=pieces_gate result])}. Writes the per-object
    files, props_gmg.json (the phys_fit layout {obj: {physics: {mass_kg, com_m, inertia_kgm2}}}, F-I3.9) and
    manifest.json (schema gmg-sim/2: objects.<obj>.{files, fiducials} as the Embodiment reader expects, plus the
    top-level files / fiducials of gmg-sim/1, the code identity and the interlock state). A delivery with any object
    whose pieces fail the keep-out gate is marked do-not-use (F-I3.8). Never overwrites an existing round folder.
    PREREG F-I4.8 (board slot, owner waiver): an object dict may carry 'default_hulls' (written to
    _default/<obj>/piece_XX.obj, hashed with the rest); EXTRA = top-level manifest keys (owner_waiver, p1_pending);
    DNU_RULE names the rule in DO_NOT_USE.json."""
    if os.path.exists(os.path.join(out_dir, 'manifest.json')):
        raise FileExistsError(f'{out_dir}: a delivered round is never overwritten')
    os.makedirs(out_dir, exist_ok=True)
    props_all, files, fids = {}, {}, {}
    props_all['_note'] = ('gmg simulator copy (INTERLOCK 6.1, PREREG F-I1.8, F-I3.9): mass = the 0.3 kg placeholder '
                          '(owner decision D-I1 open; props_masses_only.json is scan-derived), com_m and inertia_kgm2 '
                          '(about the COM, file axes) of the uniform solid of the pieces. Layout as '
                          'props_masses_only.json, read by pipeline/phys_fit.py (props[name]["physics"]).')
    dnu = {}
    for obj, o in objects.items():
        if o.get('default_hulls') is not None:
            dd = os.path.join(out_dir, '_default', obj)
            os.makedirs(dd, exist_ok=True)
            for k, V in enumerate(o['default_hulls']):
                trimesh.convex.convex_hull(V).export(os.path.join(dd, f'piece_{k:02d}.obj'))
        pr, info = write_object(out_dir, obj, o['visual'], o['hulls'], o['carve'])
        props_all[obj] = dict(physics=dict(model='gmg pieces (uniform solid)', mass_kg=k_('mass_kg'), com_m=pr['com'],
                                           inertia_kgm2=pr['inertia'], volume_cm3=pr['volume_cm3'],
                                           provenance=dict(pieces=f'{obj}/piece_*.obj',
                                                           mass='placeholder 0.3 kg (D-I1 open)')))
        fids[obj] = fiducials(o['hulls'])
        g = o.get('gate') or {}
        if g.get('do_not_use'):
            dnu[obj] = g['do_not_use']
    with open(os.path.join(out_dir, 'props_gmg.json'), 'w') as fh:
        json.dump(props_all, fh, indent=1)
    for root, _, fs in os.walk(out_dir):
        for f in fs:
            p = os.path.join(root, f)
            files[os.path.relpath(p, out_dir)] = _sha(p)
    per = {obj: dict(files={k.split('/', 1)[1]: v for k, v in files.items() if k.startswith(obj + '/')},
                     fiducials=fids[obj], gate={k: v for k, v in (objects[obj].get('gate') or {}).items()
                                                if k in ('choice', 'report', 'do_not_use')})
           for obj in objects}
    man = dict(schema='gmg-sim/2', episode=int(episode), split=split, round=int(round_k), p_sim=p_sim,
               objects=per, object_order=list(objects), files=files, fiducials=fids, code=code_identity(),
               commit=commit or guard._git('rev-parse', 'HEAD'), interlock=interlock,
               do_not_use=dnu or None,
               fiducial_definition='8 corners of the PCA-oriented bounding box of all piece vertices, each coordinate '
                                   '1 mm inward along each box axis (simpieces.fiducials)',
               note='visual <obj>.glb = submitted mesh (geometry only); collisions = piece_XX.obj (make_assets.py '
                    '--pieces); _fit/<obj>.glb = union of the pieces for phys_fit --meshes; props_gmg.json for '
                    'phys_fit --props')
    if extra:
        man.update(extra)
    with open(os.path.join(out_dir, 'manifest.json'), 'w') as fh:
        json.dump(man, fh, indent=1, default=str)
    if dnu:
        with open(os.path.join(out_dir, 'DO_NOT_USE.json'), 'w') as fh:
            json.dump(dict(do_not_use=dnu, rule=dnu_rule), fh, indent=1)
    return man
