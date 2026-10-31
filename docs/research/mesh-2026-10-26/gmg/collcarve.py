"""Collision carve for every colliding pair under the owner's extended waiver (PREREG F-I5, INTERLOCK.md section 21).

New code path. interlock.decide_pair(..., waiver_fi5=FI5(...)) calls FI5.apply() after the F-I1..F-I3 decisions of a
pair whose Sides were built from COLLIDER intrusions (intrusions_colliders below on our tracks; an Embodiment export is
already collider-based, F-I5.1). With the flag off (waiver_fi5=None) nothing here runs.

Owner, 31 Oct (recorded 17:13 UTC): "but like we said it doesnt have to be a board it can be a cup of what ever like if
2 mesh collide we can carve it". Scope (F-I5.0): every non-plate pair whose simulator colliders interpenetrate
persistently, any non-TRANSIENT engaged run; class O, the silhouette, GAP, OFFSET and the push test no longer block or
replace a carve; simulator copy only.

  collider_evidence(b, obj, hulls, mesh)     an interlock.Evidence whose occupancy is the union of the pieces
  collider_samples(hulls)                    2 mm grid points inside the union of the pieces (F-I5.1)
  intrusions_colliders(...)                  partner collider samples inside the target's pieces, per frame
  FI5(...).apply(b, so, sp, recs, links)     F-I5.2 gates, F-I5.3 receiver / rest / overshoot / c / swept carve / caps,
                                             F-I5.5 acceptance (S, P2-P7, pieces gate), F-I5.7 report; mutates RECS
  deliver(sim_dir, ...)                      F-I5.6 round folder
  run_episode(...)                           the driver branch (tools/interlock_dev.py --waiver-fi5)
GT-free: our bundle (grids, tracks, owned points, census, identity flags, sigma), our candidates, our hands (M1), our
table plane (F-I5.8).
"""
from __future__ import annotations

import json
import math
import os
import time

import numpy as np
from scipy.spatial import ConvexHull, cKDTree
from scipy.spatial.transform import Rotation as Rot

from gmg import guard, interlock as IL, cavpieces as CP

WAIVER_QUOTE = 'but like we said it doesnt have to be a board it can be a cup of what ever like if 2 mesh collide we can carve it'
WAIVER_REF = ('PREREG F-I5 (d156571, 6b16c2f); owner, session_01W8Softjo2xx7o6ofSiheuQ, 31 Oct (recorded 17:13 UTC): "' +
              WAIVER_QUOTE + '"')

# name: (value, origin) -- PREREG F-I5.10
C = dict(
    c0_m=(0.001, 'informed:F-I5.10 c_0 1.0 mm (F-I1.14 clearance)'),
    smax_m=(0.004, 'informed:F-I5.10 s_max 4 mm (F-I1.14 sink and free-travel bound)'),
    half=(0.5, 'generic:F-I5.10 half-budget factor 0.5'),
    sup_q=(99.0, 'generic:F-I5.10 99th percentile of the support slope'),
    c_round_m=(0.00005, 'generic:F-I5.10 c rounded down to 0.05 mm'),
    surf_m=(0.0005, 'generic:F-I5.3 (d) guest surface samples at 0.5 mm spacing'),
    tie=(0.1, 'generic:F-I5.10 containment tie 0.1'),
    hand_m=(0.030, 'generic:F-I5.10 hands distance 30 mm (F-I1.9 rest distance)'),
    sample_m=(0.002, 'generic:F-I5.1 2 mm grid inside the partner pieces (the Embodiment export definition)'),
    s_frames=(3, 'generic:F-I5.5 up to 3 hands-off static frames'),
    s_secs=(2.0, 'informed:F-I5.10 S 2 s'),
    s_dt=(0.002, 'informed:F-I5.10 S 2 ms (ev10w M3 setup)'),
    s_disp_m=(0.004, 'informed:F-I5.10 S mean displacement 4 mm'),
    s_tilt_deg=(5.0, 'informed:F-I5.10 S mean tilt 5 deg'),
    budget_vol=(0.10, 'generic:F-I1.14 budget 10 %'),
    budget_reach=(0.6, 'generic:F-I1.14 reach 0.6'),
    shift_t_m=(0.010, 'informed:F-I5.10 rigid shift within 1 cm'),
    shift_deg=(3.0, 'informed:F-I5.10 rigid shift within 3 deg'),
    shift_cm3=(2.0, 'informed:F-I5.10 rigid shift clears to <= 2 cm3'),
    shift_frames=(12, 'informed:F-I5.7 at most 12 build frames (ev10w M2)'),
    shift_az=(8, 'informed:F-I5.7 tilts at 8 azimuths (ev10w M2)'),
    shift_grid_m=(0.002, 'informed:F-I5.7 2 mm translation grid then 0.5 mm'),
    shift_fine_m=(0.0005, 'informed:F-I5.7 0.5 mm refinement'),
    shift_occ_m=(0.001, 'generic:numerical 1 mm occupancy grid of the receiver for the shift search (report only)'),
    shift_sample_m=(0.004, 'generic:numerical 4 mm guest samples for the shift search (report only)'),
    shift_share=(0.75, 'informed:F-I5.10 carve_of_pose_error at >= 75 % of the frames'),
    onesided=(0.75, 'informed:F-I5.10 one-sided: >= 75 % of the intrusion in one 180 deg half'),
    p6_stride=(4, 'generic:F-I5.5 P6 stride 4 frames'),
)


def k_(name):
    v, o = C[name]
    if o.startswith('generic'):
        guard.constant(f'cc.{name}', v, o)
    return v


def _tf(T, X):
    return np.asarray(X, np.float64) @ T[:3, :3].T + T[:3, 3]


# ------------------------------------------------------------------------------------------------ colliders (F-I5.1)
def collider_samples(hulls, pitch=None):
    """Points of a 2 mm grid inside the union of the pieces (cell volume pitch^3)."""
    pitch = pitch or k_('sample_m')
    H = CP.Hulls(hulls)
    lo, hi = H.bounds()
    G, _ = CP.grid_points(lo - pitch, hi + pitch, pitch)
    return G[H.inside(G)]


def collider_evidence(b, obj, hulls, mesh=None):
    """interlock.Evidence of OBJ on its bundle grids whose candidate occupancy is the union of the pieces (exact
    half-space tests); ev.hulls keeps the pieces for the per-frame tests."""
    ob = b.obs(obj)
    ev = IL.Evidence.__new__(IL.Evidence)
    ev.b, ev.obj, ev.mesh = b, obj, mesh
    ev.grid = IL.Grid(ob['lo'], ob['vox'], np.asarray(ob['state']).shape)
    ev.state = np.asarray(ob['state']).ravel()
    ev.hits = np.asarray(ob['hits']).ravel()
    ev.shared = np.asarray(ob.get('shared', np.zeros(ev.grid.shape))).ravel()
    H = CP.Hulls(hulls)
    ev.hulls = H
    ev.occ = H.inside(ev.grid.centres())
    ev.sgrid = ev.grid.sub(2)
    ev.socc = H.inside(ev.sgrid.centres())
    ev.sigma = b.sigma(obj)
    return ev


def intrusions_colliders(b, o, p, ev_o, Xp, frames, poses=None):
    """F-I5.1: partner collider samples XP (p frame) inside o's pieces, per frame, counted on o's 4 mm bundle grid."""
    poses = b.poses if poses is None else poses
    H = ev_o.hulls
    lo, hi = H.bounds()
    fr, P, Pp, L, rel = [], [], [], [], {}
    for f in frames:
        T = IL.rel_pose(poses, o, p, f)
        rel[int(f)] = T
        X = _tf(T, Xp)
        m = np.all((X >= lo) & (X <= hi), axis=1)
        k = np.zeros(len(X), bool)
        if m.any():
            k[m] = H.inside(X[m])
        lin, ok = ev_o.grid.lin(X)
        k &= ok
        if k.any():
            fr.append(np.full(int(k.sum()), int(f), np.int64)); P.append(X[k]); Pp.append(Xp[k]); L.append(lin[k])
    cat = (lambda a, d: np.concatenate(a) if a else np.zeros((0,) + d))
    return IL.Intrusions(o, p, cat(fr, ()).astype(np.int64), cat(P, (3,)), cat(Pp, (3,)), cat(L, ()).astype(np.int64),
                         rel, [int(f) for f in frames], 'colliders', Xp=Xp)


def overlap_track(Ho, Hp_samples, cell, b, o, p, frames, poses=None):
    """Collider overlap (cm3) of p's samples inside o's pieces along the track (P42)."""
    poses = b.poses if poses is None else poses
    H = Ho if isinstance(Ho, CP.Hulls) else CP.Hulls(Ho)
    out = {}
    for f in frames:
        X = _tf(IL.rel_pose(poses, o, p, f), Hp_samples)
        out[int(f)] = float(H.inside(X).sum()) * cell * 1e6
    return out


# ------------------------------------------------------------------------------------------------ helpers
def _world(b, obj, f, poses=None):
    poses = b.poses if poses is None else poses
    return poses['world_T_cam'][f].astype(np.float64) @ poses[f'cam_T_{obj}'][f].astype(np.float64)


def _hands_off(b, guest, frames, Xg, hands, poses=None):
    """Frames with no hand joint within 30 mm of the guest's collider samples (F-I5.3 (b)); hands None -> every frame
    (flag hands_absent)."""
    if hands is None:
        return set(int(f) for f in frames), ['hands_absent']
    tree = cKDTree(Xg)
    out = set()
    for f in frames:
        Mi = np.linalg.inv(_world(b, guest, f, poses))
        near = False
        for side in ('left', 'right'):
            vk = f'valid_{side}'
            if vk in hands and f < len(hands[vk]) and hands[vk][f]:
                J = np.asarray(hands[f'joints_{side}'][f], np.float64)
                J = J[np.isfinite(J).all(1)]
                if len(J) and (tree.query(_tf(Mi, J))[0] < k_('hand_m')).any():
                    near = True
        if not near:
            out.add(int(f))
    return out, []


def _segments(frames):
    out, cur = [], []
    for f in sorted(frames):
        if cur and f != cur[-1] + 1:
            out.append(cur); cur = []
        cur.append(f)
    if cur:
        out.append(cur)
    return out


def surface_samples(hulls, spacing=None):
    """Samples of the union's surface of the pieces: points on each piece's facets (about one per spacing^2) that are
    not strictly inside another piece; with their outward facet normals."""
    spacing = spacing or k_('surf_m')
    H = CP.Hulls(hulls)
    P, N = [], []
    rng = np.random.default_rng(0)
    for i, V in enumerate(H.V):
        h = ConvexHull(V)
        for s, eq in zip(h.simplices, h.equations):
            A, B, Cc = V[s]
            area = 0.5 * np.linalg.norm(np.cross(B - A, Cc - A))
            n = max(int(math.ceil(area / spacing ** 2)), 1)
            u = rng.random((n, 2)); m = u.sum(1) > 1; u[m] = 1 - u[m]
            P.append(A + u[:, :1] * (B - A) + u[:, 1:] * (Cc - A)); N.append(np.tile(eq[:3], (n, 1)))
    P, N = np.vstack(P), np.vstack(N)
    keep = np.ones(len(P), bool)
    for i in range(len(H)):
        m = np.all((P >= H.lo[i] - 1e-9) & (P <= H.hi[i] + 1e-9), axis=1)
        j = np.nonzero(m)[0]
        if len(j):
            strict = np.all(P[j] @ H.eq[i][:, :3].T + H.eq[i][:, 3] < -1e-7, axis=1)
            keep[j[strict]] = False
    return P[keep], N[keep]


def _mask_fn(grid, mask):
    def f(X):
        l, ok = grid.lin(np.asarray(X, np.float64))
        out = np.zeros(len(l), bool)
        out[ok] = mask[l[ok]]
        return out
    return f


def _occ_grid(H, pitch):
    lo, hi = H.bounds()
    lo = lo - 2 * pitch; hi = hi + 2 * pitch
    G, n = CP.grid_points(lo, hi, pitch)
    return dict(lo=lo, pitch=pitch, n=n, occ=H.inside(G).reshape(n))


def _occ_count(og, X):
    i = np.floor((X - og['lo']) / og['pitch']).astype(np.int64)
    ok = np.all((i >= 0) & (i < og['n']), axis=1)
    return int(og['occ'][i[ok, 0], i[ok, 1], i[ok, 2]].sum())


# ------------------------------------------------------------------------------------------------ the branch
class FI5:
    """Context of an F-I5 run. objects: {name: dict(hulls=default pieces, body=trimesh (the body the pieces stand
    for), route=str, lathe=(Lathe, pieces) or None, plate_like=bool, n_ring=int (lathe ring pieces before the handle
    hulls), cap=int)}. hands: our M1 hands npz dict or None. physics False skips the acceptance (decision only).
    Diagnostic overrides (tests x4, x5 only; never in a delivery): c_override (m), no_overshoot. diag_rest: PREREG
    F-I5.13 diagnostic D2 (post hoc; never delivered): rest-anchored pocket, band edges at the carve's ends with <= 30 mm
    bands inside it (amended 18:41 before any D2 result), volume and reach caps reported only (topology still gates), S
    also on default and failed carves. diag_sink: PREREG F-I5.14 (post hoc, report only, written before the T-I13 public
    runs): when an in-scope pair's carve stops before the acceptance (caps or no feasible carve), S rows on the default
    and the failed carve are reported as diag_S_rows; nothing about the decision or the delivery changes."""

    def __init__(self, b, objects, hands=None, copies=None, log=None, physics=True, c_override=None,
                 no_overshoot=False, poses=None, n_objects=None, diag_rest=False, diag_sink=False):
        self.b, self.objects, self.hands = b, objects, hands
        self.copies = copies or 16
        self.log = log or (lambda *a: None)
        self.physics = physics
        self.c_override, self.no_overshoot = c_override, no_overshoot
        self.diag_rest = bool(diag_rest)
        self.diag_sink = bool(diag_sink)
        self.poses = poses
        self.n_objects = n_objects or len(objects)
        self.results = {}
        self.Xs = {o: collider_samples(v['hulls']) for o, v in objects.items()}
        for o, v in objects.items():
            v.setdefault('K', [])                       # accepted carves: list of (vertices, allow fn)
            v.setdefault('carved', None)
            v.setdefault('carved_cm3', 0.0)
            v.setdefault('vol0_cm3', None)

    # ---- F-I5.2 gates
    def _gates(self, side, comp):
        g = dict(voxels=int(len(comp.lin)), run_kind=comp.run.kind, run=[comp.run.frames[0], comp.run.frames[-1]],
                 n_build=len(comp.run.build))
        if comp.run.kind == 'TRANSIENT' or len(comp.lin) < IL.K('engaged_min_vox'):
            return dict(g, pass_=False, fail='transient_or_size')
        if not side.track_ok:
            return dict(g, pass_=False, fail='track_identity', track=side.track_reason)
        obs = side.ev.state[comp.lin] == IL.STATE_OBSERVED
        share = float(comp.swept[obs].mean()) if obs.any() else 1.0
        g.update(sweep_share=round(share, 3), observed_voxels=int(obs.sum()), persistent_nmin=int(comp.nmin))
        if share < IL.K('swept_share'):
            return dict(g, pass_=False, fail='sweep')
        return dict(g, pass_=True)

    def _frames_R(self, side, comp):
        return [f for f in comp.run.build if np.isin(side.intr.entered(f), comp.lin).any()]

    # ---- F-I5.3 (a) receiver
    def _receiver(self, so, sp, comps):
        o, p = so.name, sp.name
        fr = sorted(set(f for (side, c) in comps for f in self._frames_R(side, c)))
        T = IL.mean_pose([IL.rel_pose(self.b.poses if self.poses is None else self.poses, o, p, f) for f in fr])
        ho = ConvexHull(np.vstack(self.objects[o]['hulls'])).equations
        hp = ConvexHull(np.vstack(self.objects[p]['hulls'])).equations
        Xp = _tf(T, self.Xs[p]); Xo = _tf(np.linalg.inv(T), self.Xs[o])
        s_o = float(np.mean(np.all(Xp @ ho[:, :3].T + ho[:, 3] <= 1e-9, axis=1)))
        s_p = float(np.mean(np.all(Xo @ hp[:, :3].T + hp[:, 3] <= 1e-9, axis=1)))
        info = dict(containment={o: round(s_o, 4), p: round(s_p, 4)}, frames=len(fr))
        if abs(s_o - s_p) >= k_('tie'):
            return (o if s_o > s_p else p), info
        sp_ = {}
        for x in (o, p):
            W = np.array([_world(self.b, x, f, self.poses)[:3, 3] for f in fr])
            sp_[x] = float(np.median(np.linalg.norm(np.diff(W, axis=0), axis=1))) if len(W) > 1 else 0.0
        info['tie_speed_m_per_frame'] = {k: round(v, 6) for k, v in sp_.items()}
        return (o if sp_[o] <= sp_[p] else p), info

    # ---- F-I5.3 (b) rest pose and overshoot
    def _rest(self, side, comp, guest):
        b = self.b
        run = comp.run
        stat = [f for st in run.static for f in st]
        hoff, hflags = _hands_off(b, guest, stat, self.Xs[guest], self.hands, self.poses)
        asm_off = [f for f in run.assembled if f in hoff]
        all_off = [f for f in stat if f in hoff]
        rest_fr = asm_off or all_off
        segs = []
        for st in run.static:                         # hands-off runs of consecutive frames of the stretch (stride)
            cur = []
            for f in list(st) + [None]:
                if f is not None and f in hoff:
                    cur.append(f); continue
                if len(cur) >= IL.K('static_min_frames'):
                    segs.append(cur)
                cur = []
        segs.sort(key=lambda s: -len(s))
        S_frames = [s[len(s) // 2] for s in segs[:k_('s_frames')]]
        info = dict(static_frames=len(stat), hands_off_static=len(all_off), assembled_hands_off=len(asm_off),
                    s_frames=S_frames, flags=hflags)
        T_rest = IL.mean_pose([side.intr.rel[f] for f in rest_fr]) if rest_fr else None
        info['rest_source'] = 'assembled' if asm_off else ('static' if all_off else None)
        return T_rest, S_frames, info

    def _gravity(self, recv, frames):
        b = self.b
        if not b.meta.get('table') or not frames:
            return None
        f = frames[len(frames) // 2]
        pl = b.table_in_obj(recv, f) if self.poses is None else None
        if pl is None:
            W = _world(b, recv, f, self.poses)
            n = W[:3, :3].T @ np.asarray(b.meta['table']['n'], float)
        else:
            n = np.asarray(pl[0], float)
        return -n / np.linalg.norm(n)

    # ---- F-I5.3 (d) clearance
    def _clearance(self, guest, T, Rplus_fn, g):
        P, N = surface_samples(self.objects[guest]['hulls'])
        X = _tf(T, P); Nn = N @ T[:3, :3].T
        m = Rplus_fn(X)
        info = dict(surface_samples=int(len(P)), in_Rplus=int(m.sum()))
        if not m.any() or g is None:
            info['sigma_sup'] = None
            return 0.0, info
        sig = np.maximum(0.0, Nn[m] @ g)
        s99 = float(np.percentile(sig, k_('sup_q')))
        c = min(k_('c0_m'), k_('half') * k_('smax_m') * s99)
        c = max(0.0, math.floor(c / k_('c_round_m') + 1e-9) * k_('c_round_m'))
        info.update(sigma_sup=round(s99, 5), c_mm=round(c * 1e3, 3))
        return c, info

    # ---- carve geometry (F-I5.3 (c), F-I5.4)
    def _carve(self, recv, K, A):
        """Carved pieces of the receiver for the cumulative carve (earlier accepted carves + this one); A = the R+
        mask function of each K piece."""
        ob = self.objects[recv]
        Kall = [k for k, _ in ob['K']] + list(K)
        Aall = [a for _, a in ob['K']] + list(A)
        rep = dict(route=ob['route'], K_pieces=len(Kall))
        if ob.get('lathe') is not None and ob['route'] == '2_lathe':
            L, pcs0 = ob['lathe']
            extra = ob['hulls'][ob.get('n_ring', len(ob['hulls'])):]
            ns0 = int(round(2 * math.pi / ([p for p in pcs0 if p['kind'] != 'disc'][0]['phi'][1] -
                                           [p for p in pcs0 if p['kind'] != 'disc'][0]['phi'][0])))
            for n_s in [ns0] + [x for x in CP.k_('sector_fallback') if x < ns0]:
                base = L.pieces(n_s)
                ranges = L.carved_ranges(base, Kall, Aall)
                pcs = L.pieces(n_s, carved=ranges,             # D2 (b, amended 18:41): edges at the carve's ends,
                               lim_carved=CP.k_('band_m') if self.diag_rest else None)   # <= 30 mm bands inside it
                cp, crep = L.carve(pcs, Kall, Aall)
                hl = L.hulls(cp) + list(extra)
                if len(hl) <= ob['cap']:
                    break
            rep.update(n_sectors=n_s, carved_ranges_mm={int(s): [round(a * 1e3, 2), round(c * 1e3, 2)]
                                                        for s, (a, c) in ranges.items()}, lathe=crep, pieces=len(hl))
            if len(hl) > ob['cap']:
                rep['why'] = 'lathe carve over the piece cap'
                return None, rep, None
            return hl, rep, None
        # boolean route: carved body = body minus (K inside R+), then the ladder without the lathe route
        body = ob['body']
        cut = self._cut_mesh(Kall, Aall, recv)
        if cut is None:
            rep['why'] = 'empty cut'
            return [np.asarray(V) for V in ob['hulls']], rep, body
        import trimesh
        carved_body = trimesh.boolean.difference([body, cut], engine='manifold')
        rep['cut_cm3'] = round(float(cut.volume) * 1e6, 3)
        rep['carved_body_cm3'] = round(float(carved_body.volume) * 1e6, 3)
        kin = self._k_inside(Kall, Aall)
        r = CP.route_pieces(carved_body, ob.get('ev'), ob['cap'], k_inside=kin, skip=('2',) +
                            (('3',) if ob['route'] == '4_voxels' else ()))
        rep['ladder'] = r['tried']
        rep['carved_route'] = r['route']
        return r['hulls'], rep, carved_body

    def _cut_mesh(self, Kall, Aall, recv):
        """Union of the K pieces intersected with the union of their R+ voxel boxes (exact boolean, manifold)."""
        import trimesh
        ob = self.objects[recv]
        ks = [trimesh.convex.convex_hull(V) for V in Kall]
        if not ks:
            return None
        Kmesh = trimesh.boolean.union(ks, engine='manifold') if len(ks) > 1 else ks[0]
        g = ob['ev'].grid
        boxes = []
        for msk in {id(a): a for a in Aall if a is not None}.values():
            lin = np.nonzero(msk.mask)[0]
            for c in g.centres(lin):
                bx = trimesh.creation.box(extents=[g.vox * 1.0001] * 3)
                bx.apply_translation(c)
                boxes.append(bx)
        if not boxes:
            return Kmesh
        Rm = trimesh.boolean.union(boxes, engine='manifold')
        cut = trimesh.boolean.intersection([Kmesh, Rm], engine='manifold')
        return cut if cut.volume > 0 else None

    def _k_inside(self, Kall, Aall):
        KH = CP.Hulls(Kall)

        def f(X):
            hit, idx = KH.inside(X, which=True)
            out = np.zeros(len(X), bool)
            for j in np.unique(idx[hit]):
                sel = idx == j
                a = Aall[j]
                out[sel] = a(X[sel]) if a is not None else True
            return out
        return f

    # ---- F-I5.3 (e) caps
    def _caps(self, recv, carved, d, kind, carved_before, kin=None):
        """F-I5.3 (e): removed collider volume (default minus carved, Monte Carlo) cumulative <= 10 % of the round-0
        collider volume; reach of the carve (the default collider's samples inside K and R+, as interlock._budget
        measures the carve solid) <= 0.6 of the collider's extent along d (INSERTION / SLIDE); topology on 2 mm."""
        from gmg import simphys as PH
        ob = self.objects[recv]
        Xd, cell = PH.guest_samples(ob['hulls'])
        if ob['vol0_cm3'] is None:
            ob['vol0_cm3'] = len(Xd) * cell * 1e6
        inC = CP.Hulls(carved).inside(Xd)
        removed = float((~inC).sum()) * cell * 1e6
        share = (carved_before + removed) / max(ob['vol0_cm3'], 1e-9)
        inK = kin(Xd) if kin is not None else ~inC
        carve_cm3 = float(inK.sum()) * cell * 1e6
        reach = None
        if kind in ('INSERTION', 'SLIDE') and inK.any():
            s_all = Xd @ d
            s_rm = Xd[inK] @ d
            reach = float((s_rm.max() - s_rm.min()) / max(s_all.max() - s_all.min(), 1e-9))
        # topology on the 2 mm grid
        pitch = CP.k_('pitch_m')
        Hd, Hc = CP.Hulls(ob['hulls']), CP.Hulls(carved)
        lo = np.minimum(Hd.bounds()[0], Hc.bounds()[0]) - 2 * pitch
        hi = np.maximum(Hd.bounds()[1], Hc.bounds()[1]) + 2 * pitch
        G, n = CP.grid_points(lo, hi, pitch)
        t0 = IL.topology(Hd.inside(G).reshape(n))
        t1 = IL.topology(Hc.inside(G).reshape(n))
        ok_v = share <= k_('budget_vol')
        ok_r = reach is None or reach <= k_('budget_reach')
        ok_t = t0 == t1
        return dict(removed_cm3=round(removed, 3), carve_in_body_cm3=round(carve_cm3, 3),
                    cumulative_share=round(share, 4), vol0_cm3=round(ob['vol0_cm3'], 2),
                    reach=None if reach is None else round(reach, 3), topology=dict(default=list(t0), carved=list(t1)),
                    ok_vol=bool(ok_v), ok_reach=bool(ok_r), ok_topology=bool(ok_t), pass_=bool(ok_v and ok_r and ok_t),
                    fail=None if (ok_v and ok_r and ok_t) else ('topology_fail' if not ok_t else 'budget_iv_fail'))

    # ---- F-I5.7 report
    def _rigid_shift(self, side, comp, recv, guest):
        """Rigid-shift alternative on <= 12 build frames (report only): the smallest translation (2 mm grid within
        1 cm, then 0.5 mm) combined with tilts 0-3 deg at 8 azimuths about the guest's collider centroid that brings
        the guest's collider intrusion into the receiver's default pieces to <= 2 cm3; share of frames cleared."""
        fr = self._frames_R(side, comp)
        nmax = k_('shift_frames')
        if len(fr) > nmax:
            fr = [fr[i] for i in np.linspace(0, len(fr) - 1, nmax).round().astype(int)]
        Hr = CP.Hulls(self.objects[recv]['hulls'])
        og = _occ_grid(Hr, k_('shift_occ_m'))
        Xs = collider_samples(self.objects[guest]['hulls'], k_('shift_sample_m'))
        cell = k_('shift_sample_m') ** 3 * 1e6
        cg = Xs.mean(0)
        st, tmax = k_('shift_grid_m'), k_('shift_t_m')
        r = np.arange(-tmax, tmax + 1e-9, st)
        Tr = np.array([[x, y, z] for x in r for y in r for z in r if x * x + y * y + z * z <= tmax ** 2 + 1e-12])
        Tr = Tr[np.argsort(np.linalg.norm(Tr, axis=1))]
        rots = [np.eye(3)]
        for tilt in range(1, int(k_('shift_deg')) + 1):
            for az in range(k_('shift_az')):
                ax = np.array([math.cos(2 * math.pi * az / k_('shift_az')), math.sin(2 * math.pi * az / k_('shift_az')), 0])
                rots.append(Rot.from_rotvec(ax * math.radians(tilt)).as_matrix())
        rows = []
        for f in fr:
            T = side.intr.rel[f]
            X0 = Xs - cg
            v0 = _occ_count(og, _tf(T, Xs)) * cell
            best = None
            if v0 <= k_('shift_cm3'):
                rows.append(dict(f=int(f), cm3=round(v0, 2), cleared=True, t_mm=0.0, tilt_deg=0)); continue
            for ri, R in enumerate(rots):
                Y = _tf(T, X0 @ R.T + cg)
                for t in Tr:
                    if best is not None and np.linalg.norm(t) >= best[0]:
                        break
                    v = _occ_count(og, Y + t) * cell
                    if v <= k_('shift_cm3'):
                        best = (float(np.linalg.norm(t)), ri, v); break
            rows.append(dict(f=int(f), cm3=round(v0, 2), cleared=best is not None,
                             t_mm=None if best is None else round(best[0] * 1e3, 1),
                             tilt_deg=None if best is None else (0 if best[1] == 0 else (best[1] - 1) // k_('shift_az') + 1)))
        share = float(np.mean([r_['cleared'] for r_ in rows])) if rows else 0.0
        return dict(frames=len(rows), cleared_share=round(share, 3), per_frame=rows,
                    note='report only (F-I5.7); 1 mm occupancy grid of the receiver, 4 mm guest samples')

    def _one_sided(self, side, comp, recv):
        ob = self.objects[recv]
        if ob.get('lathe') is None:
            return None
        L = ob['lathe'][0]
        fr = self._frames_R(side, comp)
        n1 = 0
        for f in fr:
            P = side.intr.pts[side.intr.frame == f]
            if len(P) < 3:
                continue
            _, _, phi = L.cyl(P)
            a = np.sort(np.mod(phi, 2 * math.pi))
            a2 = np.r_[a, a + 2 * math.pi]
            j = np.searchsorted(a2, a + math.pi, side='right')
            best = int((j - np.arange(len(a))).max())
            n1 += best / len(a) >= k_('onesided')
        return dict(frames=len(fr), one_sided_share=round(n1 / max(len(fr), 1), 3))

    def _sink_rows(self, recv, guest, carved, S_frames):
        """D2 diagnostic: S on the default pieces and on a carve that failed its gate (rows only, decides nothing)."""
        from gmg import simphys as PH, simpieces as SP
        b = self.b
        tb = b.meta['table']
        poses = self.poses or b.poses
        gh = self.objects[guest]['hulls']
        gp = SP.props(gh, SP.k_('mass_kg'))
        rows = []
        for f in S_frames:
            Wr = _world(b, recv, f, self.poses)
            Wg = Wr @ IL.rel_pose(poses, recv, guest, f)
            row = dict(frame=int(f))
            for name, H in (('default', self.objects[recv]['hulls']), ('carved_failed', carved)):
                if H is None:
                    continue
                r = PH.sink_test(H, gh, Wr, Wg, (np.asarray(tb['n']), float(tb['d'])), gp, copies=self.copies,
                                 secs=k_('s_secs'), dt=k_('s_dt'), disp_max=k_('s_disp_m'), tilt_max=k_('s_tilt_deg'))
                row[name] = {k: v for k, v in r.items() if k != 'per_copy'}
            rows.append(row)
            self.log('S (D2 diag rows)', recv, '<-', guest, f, json.dumps(row, default=IL._jdefault))
        return rows

    # ---- F-I5.5 acceptance
    def _accept(self, recv, guest, carved, side, comp, T_rest, S_frames, g_dir, K, A, n_axis, carved_body=None):
        from gmg import simphys as PH, simpieces as SP
        b = self.b
        ob, og = self.objects[recv], self.objects[guest]
        default_r, guest_h = ob['hulls'], og['hulls']
        out = {}
        T = int(b.meta['T'])
        poses = self.poses or b.poses
        rels = {f: IL.rel_pose(poses, recv, guest, f) for f in range(T)}
        gp = SP.props(guest_h, SP.k_('mass_kg'))
        # S
        if S_frames and b.meta.get('table'):
            tb = b.meta['table']
            rows = []
            for f in S_frames:
                Wr = _world(b, recv, f, self.poses)
                Wg = Wr @ rels[f]
                sc = PH.sink_test(carved, guest_h, Wr, Wg, (np.asarray(tb['n']), float(tb['d'])), gp,
                                  copies=self.copies, secs=k_('s_secs'), dt=k_('s_dt'), disp_max=k_('s_disp_m'),
                                  tilt_max=k_('s_tilt_deg'))
                sd = PH.sink_test(default_r, guest_h, Wr, Wg, (np.asarray(tb['n']), float(tb['d'])), gp,
                                  copies=self.copies, secs=k_('s_secs'), dt=k_('s_dt'), disp_max=k_('s_disp_m'),
                                  tilt_max=k_('s_tilt_deg'))
                rows.append(dict(frame=int(f), carved={k: v for k, v in sc.items()},
                                 default={k: v for k, v in sd.items() if k != 'per_copy'}))
                self.log('S', recv, '<-', guest, f, 'carved', {k: v for k, v in sc.items() if k != 'per_copy'},
                         'default', {k: v for k, v in sd.items() if k != 'per_copy'})
            out['S'] = dict(frames=rows, pass_=bool(all(r['carved']['pass_'] for r in rows)))
        else:
            out['S'] = dict(untestable=True, flag='sink_untestable', pass_=True,
                            why='no hands-off static frame' if not S_frames else 'no table plane')
        # P2 free travel at T_rest (else the median engaged pose)
        Tp = T_rest if T_rest is not None else IL.mean_pose([rels[f] for f in comp.run.frames])
        dirs = {'+d': comp.run.d, '+n': n_axis, '-n': -n_axis}
        if g_dir is not None:
            dirs['gravity'] = g_dir
        Xg, cell = PH.guest_samples(guest_h)
        tr_c, base_c = PH.free_travel(carved, guest_h, Tp, dirs, Xg, cell)
        tr_d, base_d = PH.free_travel(default_r, guest_h, Tp, dirs, Xg, cell)
        p2 = all(tr_c[k] <= max(PH.k_('travel_max_m'), tr_d[k] + PH.k_('travel_default_plus_m')) for k in tr_c)
        out['P2'] = dict(carved_mm={k: round(v * 1e3, 1) for k, v in tr_c.items()},
                         default_mm={k: round(v * 1e3, 1) for k, v in tr_d.items()},
                         overlap_at_pose_cm3=[round(base_d, 3), round(base_c, 3)], pass_=bool(p2),
                         pose='T_rest' if T_rest is not None else 'median engaged')
        # P3 replay proxy (every run kind)
        asm = list(S_frames) or [f for f in comp.run.frames]
        t0 = max(0, comp.run.frames[0] - PH.k_('pre'))
        frames = [f for f in range(t0, comp.run.frames[-1] + 1)]
        res = PH.replay_proxy(carved, guest_h, rels, frames, asm,
                              dict(default=(default_r, guest_h, True), carved=(carved, guest_h, True),
                                   nocollide=(default_r, guest_h, False)), copies=self.copies, guest_props=gp)
        ovs = PH.overlap_series(carved, guest_h, rels, asm, Xg, cell)
        res['judge'] = PH.p3_pass(res, overlap_cm3=float(np.median(list(ovs.values()))))
        out['P3'] = res
        # P4
        kin = self._k_inside(K, A)
        Xd, celld = PH.guest_samples(default_r)
        carve_cm3 = float(kin(Xd).sum()) * celld * 1e6
        out['P4'] = PH.over_removal(default_r, carved, carve_cm3)
        # P5 (this pair's objects at their delivered sizes plus the other objects' defaults)
        counts = {x: len(v['hulls']) for x, v in self.objects.items()}
        counts[recv] = len(carved)
        out['P5'] = PH.shape_budget(counts)
        # P6 / P7
        fr6 = sorted(set([f for f in range(0, T, k_('p6_stride'))] + list(S_frames)))
        od = PH.overlap_series(default_r, guest_h, rels, fr6, Xg, cell)
        oc = PH.overlap_series(carved, guest_h, rels, fr6, Xg, cell)
        worse = [f for f in fr6 if oc[f] > od[f] + PH.k_('p6_tol_cm3')]
        out['P6'] = dict(frames=len(fr6), n_worse=len(worse), worse=worse[:20], pass_=not worse,
                         default_max=round(max(od.values()), 3), carved_max=round(max(oc.values()), 3))
        chk = comp.run.check
        if chk:
            a = PH.overlap_series(default_r, guest_h, rels, chk, Xg, cell)
            c = PH.overlap_series(carved, guest_h, rels, chk, Xg, cell)
            sd, sc = float(sum(a.values())), float(sum(c.values()))
            out['P7'] = dict(check_frames=len(chk), default_sum_cm3=round(sd, 3), carved_sum_cm3=round(sc, 3),
                             pass_=bool(sc <= PH.k_('p7_share') * sd) if sd > 0 else True)
        else:
            out['P7'] = dict(applies=False, flag='no_holdout', pass_=True)
        # pieces gate on the carved and the default sets
        out['gate_carved'] = CP.gate(carved, carved_body if carved_body is not None else ob['body'], ob.get('ev'),
                                     self._k_inside([k for k, _ in ob['K']] + list(K), [a for _, a in ob['K']] + list(A)))
        out['gate_default'] = CP.gate(default_r, ob['body'], ob.get('ev'))
        tests = dict(S=out['S']['pass_'], P2=out['P2']['pass_'], P3=out['P3']['judge']['pass_'],
                     P4=out['P4']['pass_'], P5=out['P5']['pass_'], P6=out['P6']['pass_'], P7=out['P7']['pass_'],
                     gate=out['gate_carved']['pass_'])
        out['tests'] = tests
        out['failing'] = [k for k, v in tests.items() if not v]
        out['pass_all_but_P1'] = not out['failing']
        out['P1'] = 'pending (Embodiment jitter_check --k 16 on the delivered folder; F-I5.5)'
        return out

    # ---- the pair
    def apply(self, b, so, sp, recs, links, round_k=0):
        o, p = so.name, sp.name
        byc = {id(r['_comp']): r for r in recs}
        W = dict(rule=WAIVER_REF, pair=[o, p])
        self.results[(o, p)] = W
        if self.objects[o].get('plate_like') and self.objects[p].get('plate_like'):
            W['scope'] = 'plate pair: F-I4 decides (F-I5.0); nothing changed here'
            for r in recs:
                r['waiver_fi5'] = dict(scope='plate_pair_fi4')
            return recs
        rows = []
        for side in (so, sp):
            for comp in side.comps:
                r = byc[id(comp)]
                g = self._gates(side, comp)
                r['waiver_fi5_gates'] = g
                r['decision_f_i3'] = r['decision']
                r['tier_f_i3'] = r.get('tier')
                if not g['pass_']:
                    r['flags'].append(f'waiver_gate_fail:{g["fail"]}')
                rows.append((side, comp, r, g))
        W['gates'] = {f'{s.name}<-{c.partner}#{i}': g for i, (s, c, r, g) in enumerate(rows)}
        passing = [(s, c, r, g) for s, c, r, g in rows if g['pass_']]
        for s, c, r, g in rows:                        # F-I5: the simulator copy comes from F-I5 pieces only
            r.pop('_sim_solid', None)
            r['sim_carve'] = False
            r['submitted'] = False
            r.pop('_sub_solid', None)
        if not passing:
            W['in_scope'] = False
            W['why'] = 'no persistent component passes the kept gates'
            for s, c, r, g in rows:
                r['waiver_fi5'] = dict(scope='out', why=W['why'])
            return recs
        W['in_scope'] = True
        recv, rinfo = self._receiver(so, sp, [(s, c) for s, c, r, g in passing])
        guest = p if recv == o else o
        W['receiver'], W['guest'], W['receiver_info'] = recv, guest, rinfo
        rside = so if recv == o else sp
        rcomps = [(c, r, g) for s, c, r, g in passing if s is rside]
        for s, c, r, g in rows:
            if s is not rside:
                r['waiver_fi5'] = dict(role='guest', receiver=recv, note='the guest is never carved by this pair')
                r['flags'].append('fi5_guest_not_carved')
        if not rcomps:
            W['why'] = 'receiver_no_region (only the guest side holds a passing component)'
            for s, c, r, g in rows:
                r.setdefault('waiver_fi5', dict(role='receiver', why=W['why']))
            return recs
        ev_r = rside.ev
        Kall, allow_masks, comp_rows = [], [], []
        c_all = []
        offs = [CP.offset_hull(V, 0.0) for V in self.objects[guest]['hulls']]
        g_dir = None
        rest = None
        rcomps.sort(key=lambda x: -len(x[0].lin))
        for comp, r, g in rcomps:
            T_rest, S_frames, rinf = self._rest(rside, comp, guest)
            g_dir = self._gravity(recv, S_frames or comp.run.frames)
            Rp = IL.dilate(ev_r.grid, comp.lin, 1)
            Rfn = _mask_fn(ev_r.grid, Rp)
            Rfn.mask = Rp
            # overshoot frames
            F = self._frames_R(rside, comp)
            cg = self.Xs[guest].mean(0)
            over = []
            if T_rest is not None and not self.no_overshoot:
                p0 = _tf(T_rest, cg[None])[0]
                for f in F:
                    dv = _tf(rside.intr.rel[f], cg[None])[0] - p0
                    a_d = float(dv @ comp.run.d)
                    a_g = float(dv @ g_dir) if g_dir is not None else -np.inf
                    if a_d > k_('smax_m') or a_g > k_('smax_m'):
                        over.append(dict(f=int(f), along_d_mm=round(a_d * 1e3, 2),
                                         along_g_mm=None if g_dir is None else round(a_g * 1e3, 2)))
            of = {x['f'] for x in over}
            Fc = [f for f in F if f not in of]
            # clearance
            Tc = T_rest if T_rest is not None else IL.mean_pose([rside.intr.rel[f] for f in comp.run.frames])
            gd = g_dir if g_dir is not None else comp.run.d
            c, cinfo = self._clearance(guest, Tc, Rfn, gd)
            if g_dir is None:
                cinfo['flag'] = 'no_table: gravity proxy = the run direction d'
            if self.c_override is not None:
                cinfo['c_override_mm'] = round(self.c_override * 1e3, 3)
                cinfo['flag_diag'] = 'DIAGNOSTIC c override (never delivered)'
                c = float(self.c_override)
            if c == 0:
                cinfo['flag_c_zero'] = 'c_zero'
            c_all.append(c)
            gofs = [CP.offset_hull(V, c) for V in self.objects[guest]['hulls']] if c > 0 else offs
            d2 = None
            if self.diag_rest and T_rest is not None:  # F-I5.13 D2 (a): rest pose + straight approach channel along d
                p0 = _tf(T_rest, cg[None])[0]
                sf = np.array([float((_tf(rside.intr.rel[f], cg[None])[0] - p0) @ comp.run.d) for f in F])
                s_min = float(min(0.0, sf.min())) if len(sf) else 0.0
                Tsh = np.eye(4); Tsh[:3, 3] = comp.run.d * s_min
                K = []
                for V in gofs:
                    U = np.vstack([_tf(T_rest, V), _tf(Tsh @ T_rest, V)])
                    K.append(U[ConvexHull(U).vertices])
                dev = [_tf(rside.intr.rel[f], cg[None])[0] - p0 for f in F]
                lat = [float(np.linalg.norm(v - (v @ comp.run.d) * comp.run.d)) for v in dev]
                d2 = dict(s_min_mm=round(s_min * 1e3, 2), frames_deeper_than_rest=int((sf > 0).sum()),
                          deepest_mm=round(float(sf.max()) * 1e3, 2) if len(sf) else None,
                          lateral_dev_mm_median_max=[round(float(np.median(lat)) * 1e3, 2),
                                                     round(float(max(lat)) * 1e3, 2)] if lat else None,
                          note='DIAGNOSTIC D2 (F-I5.13): K = rest pose + approach channel along d; never delivered')
            else:
                K = [_tf(rside.intr.rel[f], V) for f in Fc for V in gofs]
            Kall += K
            allow_masks += [Rfn] * len(K)
            row = dict(gates=g, rest=rinf, T_rest=None if T_rest is None else np.round(T_rest, 6).tolist(),
                       overshoot_frames=over, carve_frames=len(Fc), build_frames_entered=len(F), clearance=cinfo,
                       R_voxels=int(len(comp.lin)), Rplus_voxels=int(Rp.sum()))
            if d2 is not None:
                row['diag_rest'] = d2
            comp_rows.append(row)
            if rest is None:
                rest = (T_rest, S_frames, comp, Rfn, K, c)
            if r is not None:
                r['push_list_fi5'] = dict(kind='OVERSHOOT', frames=[x['f'] for x in over]) if over else None
        W['components'] = comp_rows
        self.log('F-I5', recv, '<-', guest, json.dumps(comp_rows, default=IL._jdefault)[:1500])
        t = time.time()
        carved, crep, carved_body = self._carve(recv, Kall, allow_masks)
        crep['sec'] = round(time.time() - t, 1)
        W['carve'] = crep
        self.log('F-I5 carve', recv, json.dumps(crep, default=IL._jdefault)[:1500])
        T_rest, S_frames, comp0, Rfn0, K0, c0 = rest
        if carved is None:
            W['caps'] = dict(pass_=False, fail='budget_iv_fail', why=crep.get('why'))
        else:
            W['caps'] = self._caps(recv, carved, comp0.run.d, comp0.run.kind, self.objects[recv]['carved_cm3'],
                                   kin=self._k_inside([k for k, _ in self.objects[recv]['K']] + Kall,
                                                      [a for _, a in self.objects[recv]['K']] + allow_masks))
        # report (F-I5.7)
        rep = {}
        try:
            rep['rigid_shift'] = self._rigid_shift(rside, comp0, recv, guest)
            rep['carve_of_pose_error'] = bool(rep['rigid_shift']['cleared_share'] >= k_('shift_share'))
        except Exception as e:                                          # noqa: BLE001
            rep['rigid_shift'] = dict(error=f'{type(e).__name__}: {e}')
        rep['one_sided'] = self._one_sided(rside, comp0, recv)
        rep['decision_f_i3_same_sides'] = {f'{s.name}<-{c.partner}': r.get('decision_f_i3') for s, c, r, g in rows}
        W['report'] = rep
        # acceptance
        acc = None
        caps_gate = W['caps']['pass_']
        if self.diag_rest and carved is not None:        # D2 (c): volume and reach reported, topology gates
            caps_gate = bool(W['caps'].get('ok_topology'))
            W['caps']['diag_gating'] = 'D2: topology only (volume and reach reported)'
        if (self.diag_rest or self.diag_sink) and self.physics and not caps_gate and rest[1] and \
                self.b.meta.get('table'):                # D2 / F-I5.14: report-only S rows, never deciding
            W['diag_S_rows'] = self._sink_rows(recv, guest, carved, rest[1])
        if carved is not None and caps_gate and self.physics:
            n_axis = IL.axes_of(ev_r.grid.centres(comp0.lin), comp0.run.d)[1][1]
            acc = self._accept(recv, guest, carved, rside, comp0, T_rest, S_frames, g_dir, Kall, allow_masks, n_axis,
                               carved_body)
            W['acceptance'] = acc
            self.log('F-I5 acceptance', recv, '<-', guest, json.dumps(acc['tests']), acc['failing'])
        deliver = bool(acc is not None and acc['pass_all_but_P1'] and self.c_override is None and
                       not self.no_overshoot and not self.diag_rest)
        W['deliver'] = 'carved (p1_pending)' if deliver else 'default'
        if self.diag_rest:
            W['diag_D2_would_pass_all_but_P1'] = bool(acc is not None and acc['pass_all_but_P1'])
        if self.c_override is not None or self.no_overshoot or self.diag_rest:
            W['diagnostic'] = 'override set: never delivered'
        W['_carved'] = carved
        if deliver:
            ob = self.objects[recv]
            ob['K'] += list(zip(Kall, allow_masks))
            ob['carved'] = carved
            ob['carved_body'] = carved_body
            ob['carved_cm3'] += W['caps']['removed_cm3']
        for comp, r, g in rcomps:
            r['waiver_fi5'] = dict(role='receiver', receiver=recv, guest=guest)
            r['flags'].append('owner_waiver_fi5')
            if carved is None or not W['caps']['pass_']:
                r['decision'] = 'PUSH'
                r['flags'].append(W['caps'].get('fail') or 'budget_iv_fail')
            else:
                r['decision'] = 'CARVE'
                r['tier'] = 'T1'
                r['sim_carve'] = deliver
            r['fi5_delivered'] = W['deliver']
        return recs


def public_result(W):
    return {k: v for k, v in W.items() if not k.startswith('_')}


# ------------------------------------------------------------------------------------------------ F-I5.6 delivery
def deliver(sim_dir, b, ep, split, ctx, visuals, p_sim, commit=None):
    """Round folder (never overwritten): per object the carved pieces when its pair passed F-I5.5, else its default
    pieces; _default/ for every object; failed carves under _carved_failed/<pair>/; manifest owner_waiver_fi5 block,
    p1_pending true; props 0.3 kg placeholder."""
    import trimesh
    from gmg import simpieces as SP
    if os.path.exists(os.path.join(sim_dir, 'manifest.json')):
        raise FileExistsError(f'{sim_dir}: a delivered round is never overwritten')
    os.makedirs(sim_dir, exist_ok=True)
    pairs = {}
    for (o, p), W in ctx.results.items():
        pairs[f'{o}|{p}'] = public_result(W)
        if W.get('_carved') is not None and not str(W.get('deliver', '')).startswith('carved'):
            d = os.path.join(sim_dir, '_carved_failed', f'{o}_{p}')
            os.makedirs(d, exist_ok=True)
            for k, V in enumerate(W['_carved']):
                trimesh.convex.convex_hull(V).export(os.path.join(d, f'piece_{k:02d}.obj'))
            with open(os.path.join(d, 'why.json'), 'w') as fh:
                json.dump(dict(failing=(W.get('acceptance') or {}).get('failing'), caps=W.get('caps'),
                               diagnostic=W.get('diagnostic')), fh, indent=1, default=IL._jdefault)
    objects = {}
    dnu = {}
    for x, ob in ctx.objects.items():
        carved = ob.get('carved')
        g = ob.get('gate_default') or {}
        objects[x] = dict(visual=visuals[x], hulls=carved if carved is not None else ob['hulls'],
                          default_hulls=ob['hulls'],
                          gate=dict(choice=ob['route'], report=g, do_not_use=None if g.get('pass_', True) else
                                    f'default pieces fail the F-I5.4 gate (max {g.get("max_cm3")} cm3)'),
                          carve=dict(delivered='carved (p1_pending)' if carved is not None else 'default',
                                     route=ob['route'], flags=['owner_waiver_fi5', 'sim_pose_fallback'] +
                                     (['p1_pending'] if carved is not None else [])))
    extra = dict(owner_waiver_fi5=dict(rule=WAIVER_REF, quote=WAIVER_QUOTE,
                                       scope='every non-plate pair whose simulator colliders interpenetrate '
                                             'persistently, simulator copy only (F-I5.0)',
                                       routes={x: ob['route'] for x, ob in ctx.objects.items()}, pairs=pairs,
                                       default_pieces='_default/<obj>/piece_XX.obj'),
                 p1_pending=True)
    return SP.write_round(sim_dir, ep, split, 0, objects, p_sim, commit=commit, extra=extra, dnu_rule='F-I5.4 / F-I5.6')


# ------------------------------------------------------------------------------------------------ driver branch
def object_routes(b, objs, bodies, picks_mesh, out_dir, log, structure=None, plate=None, n_objects=None):
    """Default pieces of every object (F-I5.4): lathe test (structure.hypotheses, cached in OUT_DIR), plate-like test
    (platebody.plate_info steps 1-2), route ladder on the body mesh. Returns {obj: dict} for FI5."""
    from gmg import structure as ST, platebody as PB
    n = n_objects or len(objs)
    cap = CP.piece_cap(n)
    out = {}
    for o in objs:
        t = time.time()
        sp = os.path.join(out_dir, f'structure_{o}.json')
        if structure and o in structure:
            hyp = structure[o]
        elif os.path.exists(sp):
            with open(sp) as fh:
                hyp = json.load(fh)
        else:
            hyp = ST.hypotheses(b.obs(o), sigma=b.sigma(o))
            with open(sp, 'w') as fh:
                json.dump(hyp, fh, indent=1, default=IL._jdefault)
        ax = hyp.get('axis') or {}
        lathe_ok = bool((hyp.get('accepted') or {}).get('lathe'))
        if plate is not None and o in plate:
            pl = plate[o]
        else:
            pi = PB.plate_info(b, o, picks_mesh[o])
            pl = bool(pi.get('plate'))
        ev = IL.Evidence(b, o, bodies[o], sub=False)
        r = CP.route_pieces(bodies[o], ev, cap, lathe_axis=(ax.get('c'), ax.get('a')) if ax else None,
                            lathe_ok=lathe_ok, plate_like=pl, sigma=b.sigma(o), log=log)
        log('F-I5 pieces', o, r['route'], 'n', None if r['hulls'] is None else len(r['hulls']), json.dumps(
            r['tried'], default=IL._jdefault)[:1500], f'{time.time() - t:.0f}s')
        out[o] = dict(hulls=r['hulls'], body=bodies[o], route=r['route'], lathe=r.get('lathe'), plate_like=pl,
                      n_ring=len(r['hulls']) - r.get('n_handle', 0) if r['hulls'] is not None else 0, cap=cap, ev=ev,
                      gate_default=r['gate'], tried=r['tried'], lathe_test=dict(accepted=lathe_ok,
                                                                               rotc_sigma=hyp.get('rotc_sigma')))
    return out


def run_pairs(b, objects, fh=None, hands=None, identity='eval', copies=16, log=None, physics=True, c_override=None,
              no_overshoot=False, pairs=None, diag_rest=False, diag_sink=False):
    """Collider sides of every pair (F-I5.1, make_side: the same constructor as the export path), decide_pair with the
    F-I5 branch. OBJECTS as in FI5. Returns (ctx, report)."""
    log = log or print
    objs = list(objects)
    ctx = FI5(b, objects, hands=hands, copies=copies, log=log, physics=physics, c_override=c_override,
              no_overshoot=no_overshoot, diag_rest=diag_rest, diag_sink=diag_sink)
    pairs = pairs or [(objs[i], objs[j]) for i in range(len(objs)) for j in range(i + 1, len(objs))]
    report = dict(pairs={}, overlap_track={}, decisions=[])
    for o, p in pairs:
        sides = {}
        for t_, q in ((o, p), (p, o)):
            cf = b.contact(t_, q)['contact']
            evc = collider_evidence(b, t_, objects[t_]['hulls'], mesh=objects[t_].get('body'))
            intr = intrusions_colliders(b, t_, q, evc, ctx.Xs[q], cf)
            sides[t_] = IL.make_side(b, t_, q, evc, intr, cf, sources={}, identity=identity,
                                     partner_collider=ctx.Xs[q], fh=(fh or {}).get(t_))
        T = int(b.meta['T'])
        ser = overlap_track(objects[o]['hulls'], ctx.Xs[p], k_('sample_m') ** 3, b, o, p, range(0, T, 4))
        report['overlap_track'][f'{o}|{p}'] = dict(max_cm3=round(max(ser.values()), 3),
                                                   median_cm3=round(float(np.median(list(ser.values()))), 3))
        recs = IL.decide_pair(b, sides[o], sides[p], waiver_fi5=ctx)
        report['decisions'] += [IL.public(r) for r in recs]
        report['pairs'][f'{o}|{p}'] = public_result(ctx.results.get((o, p), {}))
        report.setdefault('_sides', {})[(o, p)] = sides
        report.setdefault('_recs', {})[(o, p)] = recs
    return ctx, report


def run_episode(b, ep, objs, cands, picks, bodies, fh, hands, out_dir, sim_dir, identity='eval', copies=16, log=None,
                structure=None, plate=None, physics=True, split='public', diag_sink=True, rev=None):
    """tools/interlock_dev.py --waiver-fi5: default colliders (object_routes), run_pairs, delivery. Returns the F-I5
    report (JSON-ready). diag_sink (PREREG F-I5.14, report only): S rows on the default and the failed carve of an
    in-scope pair whose carve stops before the acceptance. rev (None: the module's REV, 1 unless the round-2 driver
    tools/collcarve2_dev.py set it): 2 selects round 2 (PREREG F-I5.15 / F-I5.16, run_episode2)."""
    if (rev if rev is not None else REV) == 2:
        return run_episode2(b, ep, objs, cands, picks, bodies, fh, hands, out_dir, sim_dir, identity=identity,
                            copies=copies, log=log, structure=structure, plate=plate, physics=physics, split=split)
    log = log or print
    t0 = time.time()
    objects = object_routes(b, objs, bodies, {o: cands[o][picks[o]] for o in objs}, out_dir, log, structure, plate)
    missing = [o for o, v in objects.items() if v['hulls'] is None]
    report = dict(rule=WAIVER_REF, routes={o: dict(route=v['route'], n=None if v['hulls'] is None else len(v['hulls']),
                                                   gate=v['gate_default'], lathe_test=v['lathe_test'],
                                                   plate_like=v['plate_like'], tried=v['tried'])
                                           for o, v in objects.items()})
    if missing:
        report['do_not_use'] = f'no compliant default pieces: {missing}'
        return report
    ctx, rp = run_pairs(b, objects, fh=fh, hands=hands, identity=identity, copies=copies, log=log, physics=physics,
                        diag_sink=diag_sink)
    report['diag_sink'] = bool(diag_sink)
    report.update({k: v for k, v in rp.items() if not k.startswith('_')})
    if sim_dir:
        man = deliver(sim_dir, b, ep, split, ctx, {o: cands[o][picks[o]] for o in objs},
                      dict(source='P_sel', flag='sim_pose_fallback', tracks=b.meta.get('tracks')))
        report['sim_dir'] = sim_dir
        report['do_not_use'] = man.get('do_not_use')
    report['sec'] = round(time.time() - t0, 1)
    return report


# ================================================================================================================
# Round 2 (PREREG F-I5.15 and F-I5.16; INTERLOCK.md 21.13, 21.14). Selected by run_episode(..., rev=2) (driver
# tools/collcarve2_dev.py --fi5-rev 2 --waiver-fi5 ...); rev 1 (the default, F-I5 as built) is unchanged above.
#   Faithful(body)                       F-I5.15 (3): the SHELL's 2 mm cells merged into boxes (faithful collider)
#   precheck(...)                        F-I5.15 (3) (a) table, (b) support, (c) overlap carvable (exact SHELL boolean,
#                                        1 mm topology, wall integrity); pose_impossible frames -> push list
#   FI5R2(FI5).apply                     F-I5.15 (6): D2 carve at the precheck-passing rest, wall-band clearance,
#                                        exact K-inside-R+ clip, ring carve with forced band edges or boolean route,
#                                        1 mm topology (C, T), wall integrity (min wall, removed share), off-axis rule
#                                        (7), acceptance with S at the precheck-passing frames and S_ref beside it
#   floor_and_gate(ctx, ...)             F-I5.15 (4c) floor (share, S where S_ref passes) and F-I5.16 (1) G1 / G2
#   deliver2 / run_pairs2 / run_episode2 the round folder with DO_NOT_USE.json, CONTACT_GATE_PENDING.json,
#                                        push_list_fi5r2.json, floor.json, contact_gate.json
REV = 1

C2 = dict(
    c_min_m=(0.00005, 'generic:F-I5.15 (10) c_min 0.05 mm (the rounding unit)'),
    c_max_m=(0.001, 'informed:F-I5.15 (10) c_max = c_0 1.0 mm (F-I1.14)'),
    cap_k_sigma=(3.0, 'generic:F-I5.15 (10) base cap max(3 sigma_g, 2 mm)'),
    cap_min_m=(0.002, 'generic:F-I5.15 (10) base cap max(3 sigma_g, 2 mm)'),
    internal_m=(1e-7, 'generic:F-I5.15 (10) internal-face test 1e-7 m (non-strict)'),
    topo_m=(0.001, 'decision:orchestrator 31 Oct ~21:50 UTC 1 mm topology grid'),
    s_rm=(0.5, 'generic:F-I5.15 (10) removed share s_rm 0.5'),
    floor_frames=(3, 'generic:F-I5.15 (4c) up to 3 floor S frames'),
    wall_rays_max=(20000, 'generic:numerical precheck (c) mesh rays: a seeded subset of 20,000 samples'),
    chord_back_m=(0.3, 'generic:numerical chord rays start 0.3 m behind the sample'),
    sup_samples=(4000, 'generic:numerical 4,000 guest surface samples for the exact-mesh support distance'),
)


def k2_(name):
    v, o = C2[name]
    if o.startswith('generic'):
        guard.constant(f'cc2.{name}', v, o)
    return v


# ------------------------------------------------------------------------------------------------ faithful colliders
class Faithful:
    """F-I5.15 (3): the SHELL's 2 mm cells (centre inside) merged into maximal boxes (no cap)."""

    def __init__(self, body):
        self.body = body
        self.boxes, g = CP.faithful_boxes(body)
        self.lo, self.p, self.occ, self.n = g['lo'], g['pitch'], g['occ'], np.asarray(g['n'])
        idx = np.argwhere(self.occ)
        self.cells = self.lo + (idx + 0.5) * self.p
        cor = np.vstack([self.lo + (idx + np.array(o)) * self.p for o in np.ndindex(2, 2, 2)])
        self.corners = np.unique(np.round(cor, 9), axis=0)
        self.tree = cKDTree(self.cells)
        self.vol_cm3 = float(len(self.cells)) * self.p ** 3 * 1e6

    def inside(self, X):
        i = np.floor((np.asarray(X) - self.lo) / self.p).astype(np.int64)
        ok = np.all((i >= 0) & (i < self.n), axis=1)
        out = np.zeros(len(X), bool)
        out[ok] = self.occ[i[ok, 0], i[ok, 1], i[ok, 2]]
        return out

    def dist(self, X, k=8):
        """Distance from points to the union of the occupied cubes (exact point-to-cube on the k nearest cells)."""
        if not len(X):
            return np.zeros(0)
        d, j = self.tree.query(X, k=min(k, len(self.cells)))
        if j.ndim == 1:
            j = j[:, None]
        C = self.cells[j]
        q = np.maximum(np.abs(np.asarray(X)[:, None, :] - C) - 0.5 * self.p, 0.0)
        return np.linalg.norm(q, axis=2).min(1)


def _signed_table(X, table):
    n, d = np.asarray(table[0], float), float(table[1])
    return np.asarray(X) @ n + d


_TOPO = {}


def _occ_mesh(mesh, lo, n, pitch):
    from gmg.interlock import fast_inside
    G, _ = CP.grid_points(lo, lo + pitch * (np.asarray(n) - 1), pitch)
    return fast_inside(mesh, G).reshape(n), G


def carvable_mesh(recv, guest_in_r):
    """F-I5.15 (3c): would the receiver's SHELL minus the guest's SHELL (posed in the receiver frame) pass the 1 mm
    topology rule (6.3) and the wall-integrity rule (6.4) against the uncut SHELL? Exact boolean for the volumes; the
    1 mm grid for C, T; rays (trimesh) from the guest's surface samples inside the receiver for the walls."""
    import trimesh
    from gmg.interlock import fast_inside
    out = dict()
    cut = trimesh.boolean.difference([recv, guest_in_r], engine='manifold')
    v0 = float(recv.volume)
    removed = v0 - (float(cut.volume) if len(cut.faces) else 0.0)
    out['removed_share'] = round(removed / max(v0, 1e-15), 4)
    ok_b = removed <= k2_('s_rm') * v0
    pitch = k2_('topo_m')
    key = id(recv)
    if key not in _TOPO:
        lo = recv.bounds[0] - 2 * pitch
        n = np.ceil((recv.bounds[1] + 2 * pitch - lo) / pitch).astype(int) + 1
        occ0, G = _occ_mesh(recv, lo, n, pitch)
        _TOPO[key] = (lo, n, occ0, G, CP.topology_ct(occ0))
    lo, n, occ0, G, t0 = _TOPO[key]
    m = np.all((G >= guest_in_r.bounds[0] - pitch) & (G <= guest_in_r.bounds[1] + pitch), axis=1) & occ0.ravel()
    occ1 = occ0.copy().ravel()
    j = np.nonzero(m)[0]
    if len(j):
        occ1[j[fast_inside(guest_in_r, G[j])]] = False
    t1 = CP.topology_ct(occ1.reshape(n))
    ok_t = t1[0] <= t0[0] and t1[1] <= t0[1]
    out['topology'] = dict(default=list(t0), cut=list(t1))
    # wall integrity (a)
    area = float(guest_in_r.area)
    ns = int(math.ceil(area / k_('surf_m') ** 2))
    P, fi = trimesh.sample.sample_surface(guest_in_r, ns, seed=0)
    P = np.asarray(P); N = np.asarray(guest_in_r.face_normals)[fi]
    ins = fast_inside(recv, P)
    P, N = P[ins], N[ins]
    out['samples_inside'] = int(len(P))
    if len(P) > k2_('wall_rays_max'):
        sel = np.random.default_rng(0).choice(len(P), k2_('wall_rays_max'), replace=False)
        P, N = P[sel], N[sel]
        out['samples_used'] = int(len(P))
    ok_a, wmin_left = True, None
    if len(P):
        eps = 1e-6
        ri = trimesh.ray.ray_triangle.RayMeshIntersector(recv)
        rc = trimesh.ray.ray_triangle.RayMeshIntersector(cut) if len(cut.faces) else None

        def first(rr, O, D):
            t = np.full(len(O), np.inf)
            if rr is None:
                return t
            loc, ir, _ = rr.intersects_location(O, D, multiple_hits=False)
            if len(loc):
                t[ir] = np.einsum('ij,ij->i', loc - O[ir], D[ir])
            return t
        f_ = first(ri, P + eps * N, N) + eps
        b_ = first(ri, P - eps * N, -N) + eps
        chord = f_ + b_
        left = first(rc, P + eps * N, N) + eps
        need = chord >= CP.k2_('w_min_m')
        bad = need & (left < CP.k2_('w_min_m'))
        ok_a = not bad.any()
        wmin_left = float(np.min(left[need])) if need.any() else None
        out.update(wall_samples_needing=int(need.sum()), wall_samples_bad=int(bad.sum()),
                   min_wall_left_mm=None if wmin_left is None else round(wmin_left * 1e3, 3))
    out.update(ok_topology=bool(ok_t), ok_wall=bool(ok_a), ok_removed=bool(ok_b), pass_=bool(ok_t and ok_a and ok_b))
    return out


def precheck(fr, fg, T_wr, T_wg, table, recv_body, guest_body, smax=None):
    """F-I5.15 (3) at one frame on the faithful colliders (FR receiver, FG guest; world poses). Returns the record with
    pass_ and the failing check."""
    smax = smax if smax is not None else k_('smax_m')
    T_rg = np.linalg.inv(T_wr) @ T_wg
    out = dict()
    Cg = _tf(T_wg, fg.corners)
    sd = _signed_table(Cg, table)
    low = float(sd.min())
    low_mesh = float(_signed_table(_tf(T_wg, np.asarray(guest_body.vertices)), table).min())
    out['a_table'] = dict(lowest_mm=round(low * 1e3, 2), lowest_mesh_mm=round(low_mesh * 1e3, 2),
                          pass_=bool(low >= -smax))
    Xg = _tf(T_rg, fg.cells)
    inr = fr.inside(Xg)
    v_ov = float(inr.sum()) * fg.p ** 3 * 1e6
    if v_ov > 0:
        d_r = 0.0
    else:
        d1 = fr.dist(_tf(T_rg, fg.corners)).min()
        d2 = fg.dist(_tf(np.linalg.inv(T_rg), fr.corners)).min()
        d_r = float(min(d1, d2))
    import trimesh
    S = np.asarray(trimesh.sample.sample_surface(guest_body, k2_('sup_samples'), seed=0)[0])
    from gmg import geom as G_
    try:
        d_mesh = float(G_.Closest(recv_body).query(_tf(T_rg, S))[0].min())
    except Exception:                                                # noqa: BLE001
        d_mesh = None
    d_t = max(low, 0.0)
    out['b_support'] = dict(table_mm=round(d_t * 1e3, 2), receiver_mm=round(d_r * 1e3, 2),
                            receiver_mesh_mm=None if d_mesh is None else round(d_mesh * 1e3, 2),
                            pass_=bool(min(d_t, d_r) <= smax))
    c = dict(V_ov_cm3=round(v_ov, 3))
    if v_ov > 0:
        g_in_r = guest_body.copy()
        g_in_r.apply_transform(T_rg)
        c.update(carvable_mesh(recv_body, g_in_r))
        c['pass_'] = bool(c['pass_'])
    else:
        c['pass_'] = True
    out['c_overlap'] = c
    fails = [k for k in ('a_table', 'b_support', 'c_overlap') if not out[k]['pass_']]
    out['fail'] = fails[0] if fails else None
    out['fails'] = fails
    out['pass_'] = not fails
    return out


# ------------------------------------------------------------------------------------------------ geometry helpers
def union_boundary_samples(hulls, spacing=None, tol=None):
    """F-I5.15 (6.2): samples of the union's boundary: points on each piece's facets that are not inside or on another
    piece (non-strict, 1e-7 m), with their outward normals and piece index."""
    spacing = spacing or k_('surf_m')
    tol = k2_('internal_m') if tol is None else tol
    H = CP.Hulls(hulls)
    P, N, I = [], [], []
    rng = np.random.default_rng(0)
    for i, V in enumerate(H.V):
        h = ConvexHull(V)
        for s, eq in zip(h.simplices, h.equations):
            A, B, Cc = V[s]
            area = 0.5 * np.linalg.norm(np.cross(B - A, Cc - A))
            n = max(int(math.ceil(area / spacing ** 2)), 1)
            u = rng.random((n, 2)); m = u.sum(1) > 1; u[m] = 1 - u[m]
            P.append(A + u[:, :1] * (B - A) + u[:, 1:] * (Cc - A)); N.append(np.tile(eq[:3], (n, 1)))
            I.append(np.full(n, i))
    P, N, I = np.vstack(P), np.vstack(N), np.concatenate(I)
    keep = np.ones(len(P), bool)
    for i in range(len(H)):
        m = np.all((P >= H.lo[i] - tol) & (P <= H.hi[i] + tol), axis=1) & (I != i)
        j = np.nonzero(m)[0]
        if len(j):
            on = np.all(P[j] @ H.eq[i][:, :3].T + H.eq[i][:, 3] <= tol, axis=1)
            keep[j[on]] = False
    return P[keep], N[keep], I[keep]


def exact_clip(K, grid, mask):
    """F-I5.15 (6.5): the convex fragments of every K piece inside the maximal boxes of the voxel mask (R+)."""
    boxes = CP._boxes(np.asarray(mask).reshape(grid.shape))
    B = [(grid.lo + np.array([i, j, k]) * grid.vox, grid.lo + (np.array([x1, y1, z1]) + 1) * grid.vox)
         for i, j, k, x1, y1, z1 in boxes]
    out = []
    for V in K:
        V = np.asarray(V)
        lo, hi = V.min(0), V.max(0)
        for a, b in B:
            if np.any(hi < a) or np.any(lo > b):
                continue
            pl = np.array([[1, 0, 0, -b[0]], [-1, 0, 0, a[0]], [0, 1, 0, -b[1]], [0, -1, 0, a[1]],
                           [0, 0, 1, -b[2]], [0, 0, -1, a[2]]], np.float64)
            Q = CP.clip_vertices(V, pl)
            if Q is not None:
                out.append(Q)
    return out, len(B)


def _contig(LO, HI, t0, tol=1e-7):
    """Per ray, the end of the covered stretch that contains t0 (or starts within tol after it), from intervals."""
    lo = np.where(np.isfinite(LO), LO, np.inf); hi = np.where(np.isfinite(HI), HI, -np.inf)
    end = np.full(len(LO), np.nan)
    start_ok = (lo <= t0[:, None] + tol) & (hi > t0[:, None])
    cur = np.where(start_ok.any(1), np.max(np.where(start_ok, hi, -np.inf), 1), np.nan)
    for _ in range(LO.shape[1] if LO.ndim == 2 else 0):
        ext = (lo <= cur[:, None] + tol) & (hi > cur[:, None])
        nxt = np.where(ext.any(1), np.max(np.where(ext, hi, -np.inf), 1), cur)
        if np.allclose(np.nan_to_num(nxt), np.nan_to_num(cur)):
            break
        cur = nxt
    end[:] = cur
    return end


def wall_integrity(default_h, carved_h, Kf, w_min=None, s_rm=None):
    """F-I5.15 (6.4) on the pieces: (a) from every union-boundary sample (0.5 mm) of K inside R+ (the fragments) that
    lies inside the default receiver collider, along K's outward normal: where the default chord through the sample is
    >= w_min, the carved material from the sample outward is >= w_min; (b) removed exact volume <= s_rm x the default's
    exact volume."""
    import trimesh
    w_min = CP.k2_('w_min_m') if w_min is None else w_min
    s_rm = k2_('s_rm') if s_rm is None else s_rm
    out = {}
    Ud, Uc = CP.union_mesh(default_h), CP.union_mesh(carved_h)
    vd = float(Ud.volume)
    rem = trimesh.boolean.difference([Ud, Uc], engine='manifold')
    vr = float(rem.volume) if len(rem.faces) else 0.0
    out.update(default_cm3=round(vd * 1e6, 3), removed_cm3=round(vr * 1e6, 3), removed_share=round(vr / max(vd, 1e-15), 4))
    ok_b = vr <= s_rm * vd
    P, N, _ = union_boundary_samples(Kf)
    Hd = CP.Hulls(default_h)
    m = Hd.inside(P, tol=0.0)
    P, N = P[m], N[m]
    out['samples'] = int(len(P))
    ok_a = True
    if len(P):
        L = k2_('chord_back_m')
        LO, HI = CP.ray_hull_intervals(Hd, P - L * N, N, t_min=-np.inf)
        fwd = _contig(LO, HI, np.full(len(P), L)) - L
        LOb, HIb = CP.ray_hull_intervals(Hd, P + L * N, -N, t_min=-np.inf)
        bwd = _contig(LOb, HIb, np.full(len(P), L)) - L
        chord = np.nan_to_num(fwd) + np.nan_to_num(bwd)
        LOc, HIc = CP.ray_hull_intervals(CP.Hulls(carved_h), P, N, t_min=0.0)
        firsts = np.nanmin(np.where(np.isfinite(LOc), LOc, np.nan), axis=1) if LOc.shape[1] else np.full(len(P), np.nan)
        endc = _contig(LOc, HIc, np.nan_to_num(firsts, nan=np.inf))
        left = np.where(np.isfinite(firsts) & np.isfinite(endc), endc - firsts, 0.0)
        need = chord >= w_min
        bad = need & (left < w_min - 1e-9)
        ok_a = not bad.any()
        out.update(need=int(need.sum()), bad=int(bad.sum()),
                   min_left_mm=round(float(left[need].min()) * 1e3, 3) if need.any() else None,
                   min_default_chord_mm=round(float(chord.min()) * 1e3, 3))
    out.update(ok_wall=bool(ok_a), ok_removed=bool(ok_b), pass_=bool(ok_a and ok_b),
               fail=None if (ok_a and ok_b) else 'wall_integrity_fail')
    return out


def topology_1mm(default_h, carved_h):
    """F-I5.15 (6.3): C (26-connected components) and T (tunnels) of the default and carved pieces on one 1 mm grid
    (cell centres inside the union, exact half-space test); fails only when C or T increases."""
    pitch = k2_('topo_m')
    Hd, Hc = CP.Hulls(default_h), CP.Hulls(carved_h)
    lo = np.minimum(Hd.bounds()[0], Hc.bounds()[0]) - 2 * pitch
    hi = np.maximum(Hd.bounds()[1], Hc.bounds()[1]) + 2 * pitch
    G, n = CP.grid_points(lo, hi, pitch)
    t0 = CP.topology_ct(Hd.inside(G).reshape(n))
    t1 = CP.topology_ct(Hc.inside(G).reshape(n))
    ok = t1[0] <= t0[0] and t1[1] <= t0[1]
    return dict(default=dict(C=t0[0], T=t0[1]), carved=dict(C=t1[0], T=t1[1]), pass_=bool(ok),
                fail=None if ok else 'topology_fail')


MANDATE_QUOTE = 'anything that improves the score within the competition rules'
BASE_KINDS = ('base1', 'disc', 'rim')


def reference_for(ob):
    """F-I5.15 (4a): the reference collider of an object (never delivered): 64-sector rings for a route-2 object,
    the SHELL's 2 mm boxes otherwise."""
    if ob.get('route') == '2_lathe' and ob.get('lathe') is not None:
        prof, lay = ob['lathe']
        hl, rlay = CP.reference_rings(prof, ob.get('handle_hulls') or [])
        if hl is not None:
            return hl, dict(kind='rings64', n=len(hl), layout=rlay)
    return [np.asarray(V) for V in ob['faithful'].boxes], dict(kind='boxes_2mm', n=len(ob['faithful'].boxes))


class FI5R2(FI5):
    """Round-2 context (PREREG F-I5.15 / F-I5.16). objects: as FI5, plus per object 'faithful' (Faithful of the body)
    and 'ref' (reference hulls); route-2 objects carry lathe = (Profile2, layout) and handle_hulls."""

    def __init__(self, b, objects, **kw):
        super().__init__(b, objects, **kw)
        self.rev = 2
        self.push = []
        self._pre, self._sink = {}, {}
        for o, v in objects.items():
            if 'faithful' not in v:
                v['faithful'] = Faithful(v['body'])
            if 'ref' not in v:
                v['ref'], v['ref_info'] = reference_for(v)

    # ---- shared helpers
    def table(self):
        tb = self.b.meta.get('table')
        return None if not tb else (np.asarray(tb['n'], float), float(tb['d']))

    def pre(self, recv, guest, f):
        key = (recv, guest, int(f))
        if key not in self._pre:
            fr, fg = self.objects[recv]['faithful'], self.objects[guest]['faithful']
            Wr, Wg = _world(self.b, recv, f, self.poses), _world(self.b, guest, f, self.poses)
            tb = self.table()
            if tb is None:
                self._pre[key] = dict(pass_=True, untestable='no table plane', fail=None, fails=[])
            else:
                self._pre[key] = precheck(fr, fg, Wr, Wg, tb, self.objects[recv]['body'], self.objects[guest]['body'])
        return self._pre[key]

    def sink(self, host, guest_h, recv, guest, f, tag):
        """S (F-I5.5 setup, 16 copies) of guest pieces GUEST_H on host pieces HOST at frame f, cached by tag."""
        from gmg import simphys as PH
        key = (tag, recv, guest, int(f))
        if key not in self._sink:
            Wr = _world(self.b, recv, f, self.poses)
            Wg = Wr @ IL.rel_pose(self.poses or self.b.poses, recv, guest, f)
            gp = CP.exact_props(guest_h, 0.3)
            t = time.time()
            r = PH.sink_test(host, guest_h, Wr, Wg, self.table(), gp, copies=self.copies, secs=k_('s_secs'),
                             dt=k_('s_dt'), disp_max=k_('s_disp_m'), tilt_max=k_('s_tilt_deg'))
            r['sec'] = round(time.time() - t, 1)
            r['pieces'] = [len(host), len(guest_h)]
            self._sink[key] = r
            self.log('S', tag, recv, '<-', guest, f, {k: v for k, v in r.items() if k != 'per_copy'})
        return self._sink[key]

    def _rest2(self, side, comp, guest):
        """Hands-off static segments of the run (F-I5.3 (b)) and their middle frames (up to 3, longest first)."""
        run = comp.run
        stat = [f for st in run.static for f in st]
        hoff, hflags = _hands_off(self.b, guest, stat, self.Xs[guest], self.hands, self.poses)
        segs = []
        for st in run.static:
            cur = []
            for f in list(st) + [None]:
                if f is not None and f in hoff:
                    cur.append(f); continue
                if len(cur) >= IL.K('static_min_frames'):
                    segs.append(cur)
                cur = []
        segs.sort(key=lambda s: -len(s))
        segs = segs[:k_('s_frames')]
        S_frames = [s[len(s) // 2] for s in segs]
        return S_frames, segs, dict(static_frames=len(stat), hands_off_static=len([f for f in stat if f in hoff]),
                                    s_frames=S_frames, segments=[[s[0], s[-1]] for s in segs], flags=hflags)

    def _clearance2(self, guest, T, Rfn, g):
        """F-I5.15 (6.2): c = 0.5 s_max sigma_wall in [c_min, c_max], rounded down to 0.05 mm; sigma_wall = 99th
        percentile of max(0, n . g) over the guest's union-boundary samples inside R+ at T in its wall band."""
        og = self.objects[guest]
        P, N, I = union_boundary_samples(og['hulls'])
        X = _tf(T, P); Nn = N @ T[:3, :3].T
        m = Rfn(X)
        info = dict(union_samples=int(len(P)), in_Rplus=int(m.sum()))
        lowest = float((_tf(T, np.vstack(og['hulls'])) @ g).max())
        capd = max(k2_('cap_k_sigma') * float(self.b.sigma(guest)), k2_('cap_min_m'))
        base_piece = np.zeros(len(P), bool)
        if og.get('route') == '2_lathe' and og.get('lathe') is not None:
            kinds = [p['kind'] for p in og['lathe'][1]['pieces']]
            base_piece = np.array([i < len(kinds) and kinds[i] in BASE_KINDS for i in I])
        cap = ((lowest - X @ g) <= capd) | base_piece
        wall = m & ~cap
        use = wall if wall.any() else (m & cap)
        info.update(wall_band=int(wall.sum()), base_cap=int((m & cap).sum()), source='wall band' if wall.any() else
                    ('base cap (a seat)' if use.any() else 'none in R+'), base_cap_mm=round(capd * 1e3, 2))
        if not use.any():
            c = k2_('c_min_m')
            info.update(sigma_wall=None, c_mm=round(c * 1e3, 3))
            return c, info
        sig = float(np.percentile(np.maximum(0.0, Nn[use] @ g), k_('sup_q')))
        c = min(max(k_('half') * k_('smax_m') * sig, k2_('c_min_m')), k2_('c_max_m'))
        c = math.floor(c / k_('c_round_m') + 1e-9) * k_('c_round_m')
        info.update(sigma_wall=round(sig, 5), c_mm=round(c * 1e3, 3))
        return c, info

    def _off_axis(self, recv, guest, T_rest, c):
        """F-I5.15 (7): both route 2 and the guest's axis at its lowest wall height inside the receiver's cavity at
        T_rest: a nest; not carved when e_ax + c > t_min - w_min."""
        orc, ogs = self.objects[recv], self.objects[guest]
        if not (orc.get('route') == '2_lathe' and ogs.get('route') == '2_lathe' and orc.get('lathe') and ogs.get('lathe')):
            return None
        pr, lr = orc['lathe']; pg, lg = ogs['lathe']
        hw = [p['h0'] for p in lg['pieces'] if p['kind'] == 'wall']
        if not hw:
            return None
        x = _tf(T_rest, (pg.c + min(hw) * pg.a)[None])[0]
        h, r, _ = pr.cyl(x[None])
        h, r = float(h[0]), float(r[0])
        k = int(np.argmin(np.abs(pr.H - h)))
        rin = float(np.nanmedian(pr.rin[k])) if np.isfinite(pr.rin[k]).any() else 0.0
        walls = [p for p in lr['pieces'] if p['kind'] == 'wall' and p['h1'] > h]
        if not walls or r >= rin or not (min(p['h0'] for p in walls) - 1e-3 <= h):
            return dict(nest=False, e_ax_mm=round(r * 1e3, 3), h_mm=round(h * 1e3, 2))
        t_min = min(CP.piece_wall_min(p) for p in walls)
        w = CP.k2_('w_min_m')
        bad = r + c > t_min - w
        return dict(nest=True, e_ax_mm=round(r * 1e3, 3), c_mm=round(c * 1e3, 3), t_min_mm=round(t_min * 1e3, 3),
                    w_min_mm=round(w * 1e3, 3), not_carved=bool(bad), rule='e_ax + c > t_min - w_min')

    def _carve2(self, recv, Kf):
        import trimesh
        ob = self.objects[recv]
        rep = dict(route=ob['route'], K_fragments=len(Kf))
        if ob.get('route') == '2_lathe' and ob.get('lathe') is not None:
            prof, lay = ob['lathe']
            forced = CP.carved_heights(prof, lay, Kf)
            lay2 = CP.forced_layout(prof, lay, forced)
            lay3, crep = CP.carve2(prof, lay2, Kf)
            hl = CP.layout_hulls(prof, lay3) + [np.asarray(V) for V in (ob.get('handle_hulls') or [])]
            rep.update(forced_edges_mm={int(k): [round(x * 1e3, 2) for x in v] for k, v in forced.items()},
                       n_s=lay['n_s'], base=lay['base'], pieces=len(hl), lathe=crep,
                       min_wall_mm=None if lay3['min_wall_mm'] is None else round(lay3['min_wall_mm'], 3))
            ob['_carve_forced'] = forced
            return hl, rep, None
        cut = CP.union_mesh(Kf)
        carved_body = trimesh.boolean.difference([ob['body'], cut], engine='manifold')
        rep.update(cut_cm3=round(float(cut.volume) * 1e6, 3), carved_body_cm3=round(float(carved_body.volume) * 1e6, 3))
        KH = CP.Hulls(Kf)
        r = CP.route_pieces2(carved_body, ob.get('ev'), ob['cap'], k_inside=lambda X: KH.inside(X), skip=('2',))
        rep.update(ladder=r['tried'], carved_route=r['route'])
        return r['hulls'], rep, carved_body

    def _ref_carved(self, recv, Kf, carved_body):
        ob = self.objects[recv]
        if ob.get('route') == '2_lathe' and ob.get('lathe') is not None and ob.get('ref_info', {}).get('kind') == 'rings64':
            prof, _ = ob['lathe']
            rlay = ob['ref_info']['layout']
            lay2 = CP.forced_layout(prof, rlay, ob.get('_carve_forced') or {})
            lay3, _ = CP.carve2(prof, lay2, Kf)
            return CP.layout_hulls(prof, lay3) + [np.asarray(V) for V in (ob.get('handle_hulls') or [])]
        if carved_body is not None:
            return [np.asarray(V) for V in Faithful(carved_body).boxes]
        return ob['ref']

    def _accept2(self, recv, guest, carved, comp, T_rest, ok_frames, g_dir, Kf, n_axis, carved_body):
        from gmg import simphys as PH
        b = self.b
        ob, og = self.objects[recv], self.objects[guest]
        default_r, guest_h = ob['hulls'], og['hulls']
        out = {}
        T = int(b.meta['T'])
        poses = self.poses or b.poses
        rels = {f: IL.rel_pose(poses, recv, guest, f) for f in range(T)}
        gp = CP.exact_props(guest_h, 0.3)
        ref_c = self._ref_carved(recv, Kf, carved_body)
        if ok_frames and self.table() is not None:
            rows = []
            for f in ok_frames:
                sc = self.sink(carved, guest_h, recv, guest, f, f'carved:{id(carved)}')
                sd = self.sink(default_r, guest_h, recv, guest, f, 'default')
                sr = self.sink(ref_c, og['ref'], recv, guest, f, f'ref_carved:{id(carved)}')
                rows.append(dict(frame=int(f), carved=sc, default=sd, ref=sr))
            out['S'] = dict(frames=rows, pass_=bool(all(r['carved']['pass_'] for r in rows)),
                            ref_pass=bool(all(r['ref']['pass_'] for r in rows)))
        else:
            out['S'] = dict(untestable=True, flag='sink_untestable', pass_=True,
                            why='no precheck-passing hands-off static frame' if not ok_frames else 'no table plane')
        dirs = {'+d': comp.run.d, '+n': n_axis, '-n': -n_axis}
        if g_dir is not None:
            dirs['gravity'] = g_dir
        Xg, cell = PH.guest_samples(guest_h)
        tr_c, base_c = PH.free_travel(carved, guest_h, T_rest, dirs, Xg, cell)
        tr_d, base_d = PH.free_travel(default_r, guest_h, T_rest, dirs, Xg, cell)
        p2 = all(tr_c[k] <= max(PH.k_('travel_max_m'), tr_d[k] + PH.k_('travel_default_plus_m')) for k in tr_c)
        out['P2'] = dict(carved_mm={k: round(v * 1e3, 1) for k, v in tr_c.items()},
                         default_mm={k: round(v * 1e3, 1) for k, v in tr_d.items()},
                         overlap_at_pose_cm3=[round(base_d, 3), round(base_c, 3)], pass_=bool(p2), pose='T_rest')
        asm = list(ok_frames) or list(comp.run.frames)
        t0 = max(0, comp.run.frames[0] - PH.k_('pre'))
        frames = list(range(t0, comp.run.frames[-1] + 1))
        res = PH.replay_proxy(carved, guest_h, rels, frames, asm,
                              dict(default=(default_r, guest_h, True), carved=(carved, guest_h, True),
                                   nocollide=(default_r, guest_h, False)), copies=self.copies, guest_props=gp)
        ovs = PH.overlap_series(carved, guest_h, rels, asm, Xg, cell)
        res['judge'] = PH.p3_pass(res, overlap_cm3=float(np.median(list(ovs.values()))))
        out['P3'] = res
        import trimesh
        Ud, Uc = CP.union_mesh(default_r), CP.union_mesh(carved)
        rem = trimesh.boolean.difference([Ud, Uc], engine='manifold')
        removed = float(rem.volume) * 1e6 if len(rem.faces) else 0.0
        kin = trimesh.boolean.intersection([CP.union_mesh(Kf), Ud], engine='manifold')
        carve_cm3 = float(kin.volume) * 1e6 if len(kin.faces) else 0.0
        out['P4'] = dict(removed_cm3=round(removed, 3), carve_in_default_cm3=round(carve_cm3, 3),
                         pass_=bool(removed <= PH.k_('removal_x') * max(carve_cm3, 1e-9)),
                         note='F-I5.15 (6.4): over-removal clause only (exact volumes); the 90 % clause is (6.4)(b)')
        counts = {x: len(v['hulls']) for x, v in self.objects.items()}
        counts[recv] = len(carved)
        out['P5'] = PH.shape_budget(counts)
        fr6 = sorted(set([f for f in range(0, T, k_('p6_stride'))] + list(ok_frames)))
        od = PH.overlap_series(default_r, guest_h, rels, fr6, Xg, cell)
        oc = PH.overlap_series(carved, guest_h, rels, fr6, Xg, cell)
        worse = [f for f in fr6 if oc[f] > od[f] + PH.k_('p6_tol_cm3')]
        out['P6'] = dict(frames=len(fr6), n_worse=len(worse), worse=worse[:20], pass_=not worse,
                         default_max=round(max(od.values()), 3), carved_max=round(max(oc.values()), 3))
        chk = comp.run.check
        if chk:
            a = PH.overlap_series(default_r, guest_h, rels, chk, Xg, cell)
            c = PH.overlap_series(carved, guest_h, rels, chk, Xg, cell)
            sd, sc = float(sum(a.values())), float(sum(c.values()))
            out['P7'] = dict(check_frames=len(chk), default_sum_cm3=round(sd, 3), carved_sum_cm3=round(sc, 3),
                             pass_=bool(sc <= PH.k_('p7_share') * sd) if sd > 0 else True)
        else:
            out['P7'] = dict(applies=False, flag='no_holdout', pass_=True)
        KH = CP.Hulls(Kf)
        out['gate_carved'] = CP.gate(carved, carved_body if carved_body is not None else ob['body'], ob.get('ev'),
                                     lambda X: KH.inside(X))
        tests = dict(S=out['S']['pass_'], P2=out['P2']['pass_'], P3=out['P3']['judge']['pass_'],
                     P4=out['P4']['pass_'], P5=out['P5']['pass_'], P6=out['P6']['pass_'], P7=out['P7']['pass_'],
                     gate=out['gate_carved']['pass_'])
        out['tests'] = tests
        out['failing'] = [k for k, v in tests.items() if not v]
        out['pass_all_but_P1'] = not out['failing']
        out['P1'] = 'pending (Embodiment jitter_check --k 16 on the delivered folder; F-I5.5)'
        out['_ref_carved'] = ref_c
        return out

    # ---- the pair
    def apply(self, b, so, sp, recs, links, round_k=0):
        o, p = so.name, sp.name
        byc = {id(r['_comp']): r for r in recs}
        W = dict(rule=WAIVER_REF, pair=[o, p], rev=2)
        self.results[(o, p)] = W
        if self.objects[o].get('plate_like') and self.objects[p].get('plate_like'):
            W['scope'] = 'plate pair: F-I4 decides (F-I5.0); nothing changed here'
            for r in recs:
                r['waiver_fi5'] = dict(scope='plate_pair_fi4')
            return recs
        rows = []
        for side in (so, sp):
            for comp in side.comps:
                r = byc[id(comp)]
                g = self._gates(side, comp)
                r['waiver_fi5_gates'] = g
                r['decision_f_i3_logic_on_colliders'] = r['decision']
                r['tier_f_i3'] = r.get('tier')
                if not g['pass_']:
                    r['flags'].append(f'waiver_gate_fail:{g["fail"]}')
                rows.append((side, comp, r, g))
        W['gates'] = {f'{s.name}<-{c.partner}#{i}': g for i, (s, c, r, g) in enumerate(rows)}
        passing = [(s, c, r, g) for s, c, r, g in rows if g['pass_']]
        for s, c, r, g in rows:
            r.pop('_sim_solid', None); r['sim_carve'] = False; r['submitted'] = False; r.pop('_sub_solid', None)
        if not passing:
            W['in_scope'] = False
            W['why'] = 'no persistent component passes the kept gates'
            W['deliver'] = 'default'
            for s, c, r, g in rows:
                r['waiver_fi5'] = dict(scope='out', why=W['why'])
            return recs
        W['in_scope'] = True
        recv, rinfo = self._receiver(so, sp, [(s, c) for s, c, r, g in passing])
        guest = p if recv == o else o
        W['receiver'], W['guest'], W['receiver_info'] = recv, guest, rinfo
        rside = so if recv == o else sp
        rcomps = [(c, r, g) for s, c, r, g in passing if s is rside]
        for s, c, r, g in rows:
            if s is not rside:
                r['waiver_fi5'] = dict(role='guest', receiver=recv, note='the guest is never carved by this pair')
                r['flags'].append('fi5_guest_not_carved'); r['flags'].append('owner_waiver_fi5'); r['tier'] = 'T1'
        if not rcomps:
            W['why'] = 'receiver_no_region (only the guest side holds a passing component)'
            W['deliver'] = 'default'
            for s, c, r, g in rows:
                r.setdefault('waiver_fi5', dict(role='receiver', why=W['why']))
            return recs
        ev_r = rside.ev
        rcomps.sort(key=lambda x: -len(x[0].lin))
        run0 = rcomps[0][0].run
        asm0 = list(run0.assembled or run0.build[-5:] or run0.frames[-5:])
        W['settle_frame'] = int(asm0[len(asm0) // 2]) if asm0 else None      # G1 settle scene (F-I5.16 (1c))
        Kall, comp_rows, rest = [], [], None
        cg = self.Xs[guest].mean(0)
        for comp, r, g in rcomps:
            S_frames, segs, rinf = self._rest2(rside, comp, guest)
            pre = {f: self.pre(recv, guest, f) for f in S_frames}
            for f in S_frames:
                if not pre[f]['pass_']:
                    self.push.append(dict(pair=[recv, guest], frame=int(f), check=pre[f]['fail'], kind='pose_impossible',
                                          numbers={k: pre[f][k] for k in ('a_table', 'b_support', 'c_overlap')
                                                   if k in pre[f]}))
            ok_frames = [f for f in S_frames if pre[f]['pass_']]
            rest_fr = [x for s, f in zip(segs, S_frames) if pre[f]['pass_'] for x in s]
            row = dict(gates=g, rest=rinf, precheck={int(f): pre[f] for f in S_frames}, ok_frames=ok_frames,
                       R_voxels=int(len(comp.lin)))
            comp_rows.append(row)
            if not rest_fr:
                row['why'] = 'pose_impossible_all' if S_frames else 'no_rest'
                continue
            T_rest = IL.mean_pose([rside.intr.rel[f] for f in rest_fr])
            g_dir = self._gravity(recv, ok_frames)
            Rp = IL.dilate(ev_r.grid, comp.lin, 1)
            Rfn = _mask_fn(ev_r.grid, Rp)
            c, cinfo = self._clearance2(guest, T_rest, Rfn, g_dir if g_dir is not None else comp.run.d)
            gofs = [CP.offset_hull(V, c) for V in self.objects[guest]['hulls']]
            F = self._frames_R(rside, comp)
            p0 = _tf(T_rest, cg[None])[0]
            sf = np.array([float((_tf(rside.intr.rel[f], cg[None])[0] - p0) @ comp.run.d) for f in F])
            s_min = float(min(0.0, sf.min())) if len(sf) else 0.0
            Tsh = np.eye(4); Tsh[:3, 3] = comp.run.d * s_min
            K = []
            for V in gofs:
                U = np.vstack([_tf(T_rest, V), _tf(Tsh @ T_rest, V)])
                K.append(U[ConvexHull(U).vertices])
            Kf, nbox = exact_clip(K, ev_r.grid, Rp)
            row.update(T_rest=np.round(T_rest, 6).tolist(), rest_frames=len(rest_fr), clearance=cinfo,
                       d2=dict(s_min_mm=round(s_min * 1e3, 2), deeper_frames=int((sf > 0).sum()),
                               deepest_mm=round(float(sf.max()) * 1e3, 2) if len(sf) else None),
                       K_pieces=len(K), K_fragments=len(Kf), Rplus_boxes=nbox, Rplus_voxels=int(Rp.sum()))
            oa = self._off_axis(recv, guest, T_rest, c)
            row['off_axis'] = oa
            if oa and oa.get('not_carved'):
                row['why'] = 'off_axis_nest'
                self.push.append(dict(pair=[recv, guest], kind='off_axis_nest', numbers=oa,
                                      remedy='pose correction (F-I5.15 (7))'))
                continue
            Kall += Kf
            if rest is None:
                rest = (T_rest, ok_frames, comp, g_dir, c)
        W['components'] = comp_rows
        self.log('F-I5 r2', recv, '<-', guest, json.dumps(comp_rows, default=IL._jdefault)[:1500])
        if not Kall:
            W['deliver'] = 'default'
            W['why'] = '; '.join(sorted(set(rw.get('why', '') for rw in comp_rows if rw.get('why')))) or 'no carve'
            for comp, r, g in rcomps:
                r['waiver_fi5'] = dict(role='receiver', receiver=recv, guest=guest, why=W['why'])
                r['flags'] += ['owner_waiver_fi5', W['why']]
                r['decision'] = 'PUSH'
                r['fi5_delivered'] = 'default'
            return recs
        t = time.time()
        carved, crep, carved_body = self._carve2(recv, Kall)
        crep['sec'] = round(time.time() - t, 1)
        W['carve'] = crep
        self.log('F-I5 r2 carve', recv, json.dumps(crep, default=IL._jdefault)[:1500])
        T_rest, ok_frames, comp0, g_dir, c0 = rest
        caps = dict()
        if carved is None:
            caps = dict(pass_=False, fail='no compliant carved pieces')
        else:
            caps['topology'] = topology_1mm(self.objects[recv]['hulls'], carved)
            caps['wall'] = wall_integrity(self.objects[recv]['hulls'], carved, Kall)
            caps['pass_'] = bool(caps['topology']['pass_'] and caps['wall']['pass_'])
            caps['fail'] = caps['topology']['fail'] or caps['wall']['fail']
        W['caps'] = caps
        rep = {}
        try:
            rep['rigid_shift'] = self._rigid_shift(rside, comp0, recv, guest)
            rep['carve_of_pose_error'] = bool(rep['rigid_shift']['cleared_share'] >= k_('shift_share'))
        except Exception as e:                                          # noqa: BLE001
            rep['rigid_shift'] = dict(error=f'{type(e).__name__}: {e}')
        rep['one_sided'] = self._one_sided(rside, comp0, recv)
        W['report'] = rep
        acc = None
        if carved is not None and caps['pass_'] and self.physics:
            n_axis = IL.axes_of(ev_r.grid.centres(comp0.lin), comp0.run.d)[1][1]
            acc = self._accept2(recv, guest, carved, comp0, T_rest, ok_frames, g_dir, Kall, n_axis, carved_body)
            W['_ref_carved'] = acc.pop('_ref_carved')
            W['acceptance'] = acc
            self.log('F-I5 r2 acceptance', recv, '<-', guest, json.dumps(acc['tests']), acc['failing'])
        deliver = bool(acc is not None and acc['pass_all_but_P1'])
        W['deliver'] = 'carved (p1_pending)' if deliver else 'default'
        W['_carved'] = carved
        W['_Kf'] = Kall
        if deliver:
            ob = self.objects[recv]
            ob['carved'] = carved
            ob['carved_body'] = carved_body
            ob['carved_ref'] = W.get('_ref_carved')
        for comp, r, g in rcomps:
            r['waiver_fi5'] = dict(role='receiver', receiver=recv, guest=guest)
            r['flags'].append('owner_waiver_fi5')
            if carved is None or not caps['pass_']:
                r['decision'] = 'PUSH'
                r['flags'].append(caps.get('fail') or 'no_carve')
            else:
                r['decision'] = 'CARVE'
                r['tier'] = 'T1'
                r['sim_carve'] = deliver
            r['fi5_delivered'] = W['deliver']
        return recs


# ------------------------------------------------------------------------------------------------ floor and gate
def _faithful_gap(fr, fg, T_rg):
    if fr.inside(_tf(T_rg, fg.cells)).any():
        return 0.0
    return float(min(fr.dist(_tf(T_rg, fg.corners)).min(), fg.dist(_tf(np.linalg.inv(T_rg), fr.corners)).min()))


def floor_frames(ctx, o, p):
    """F-I5.15 (4c): receiver by containment on the faithful colliders (at the mean relative pose over the pair's
    static frames), the middle frames of up to 3 longest hands-off static segments (F-I1.1 stretches of the relative
    path, hands-off for the guest) in which the faithful colliders are within s_max of each other."""
    b = ctx.b
    poses = ctx.poses or b.poses
    T = int(b.meta['T'])
    rel = {f: IL.rel_pose(poses, o, p, f) for f in range(T)}
    path = np.array([rel[f][:3, 3] for f in range(T)])
    stat = IL._static_stretches(list(range(T)), path) if T >= 2 else []
    info = dict(static_stretches=len(stat))
    if not stat:
        info['flag'] = 's_floor_vacuous'
        return None, None, [], info
    fr_all = [f for s in stat for f in s]
    Tm = IL.mean_pose([rel[f] for f in fr_all])
    Fo, Fp = ctx.objects[o]['faithful'], ctx.objects[p]['faithful']
    ho = ConvexHull(Fo.corners).equations; hp = ConvexHull(Fp.corners).equations
    s_o = float(np.mean(np.all(_tf(Tm, Fp.cells) @ ho[:, :3].T + ho[:, 3] <= 1e-9, axis=1)))
    s_p = float(np.mean(np.all(_tf(np.linalg.inv(Tm), Fo.cells) @ hp[:, :3].T + hp[:, 3] <= 1e-9, axis=1)))
    recv, guest = (o, p) if s_o >= s_p else (p, o)
    info['containment'] = {o: round(s_o, 4), p: round(s_p, 4)}
    hoff, flags = _hands_off(b, guest, fr_all, ctx.Xs[guest], ctx.hands, ctx.poses)
    segs = []
    for st in stat:
        cur = []
        for f in list(st) + [None]:
            if f is not None and f in hoff:
                cur.append(f); continue
            if len(cur) >= IL.K('static_min_frames'):
                segs.append(cur)
            cur = []
    segs.sort(key=lambda s: -len(s))
    out = []
    fr_, fg_ = ctx.objects[recv]['faithful'], ctx.objects[guest]['faithful']
    gaps = []
    for s in segs:
        f = s[len(s) // 2]
        T_rg = IL.rel_pose(poses, recv, guest, f)
        gap = _faithful_gap(fr_, fg_, T_rg)
        gaps.append(dict(frame=int(f), gap_mm=round(gap * 1e3, 2), seg=[s[0], s[-1]]))
        if gap <= k_('smax_m'):
            out.append(int(f))
        if len(out) >= k2_('floor_frames'):
            break
    info.update(hands_off_segments=len(segs), segment_gaps=gaps[:12], flags=flags)
    if not out:
        info['flag'] = 's_floor_vacuous'
    return recv, guest, out, info


def delivered(ob):
    return ob['carved'] if ob.get('carved') is not None else ob['hulls']


def floor_and_gate(ctx, visuals, synthetic=False, r0_dir=None, log=None):
    """F-I5.15 (4c) floor and F-I5.16 (1) G1 (+ G2 status) over every pair of the episode. Returns (floor, gate)."""
    from gmg import contactgate5 as G
    log = log or ctx.log
    objs = list(ctx.objects)
    pairs = [(objs[i], objs[j]) for i in range(len(objs)) for j in range(i + 1, len(objs))]
    floor = dict(rule='PREREG F-I5.15 (4c)', objects={}, pairs={}, fails=[])
    for x, ob in ctx.objects.items():
        sh = CP.exact_share(delivered(ob), ob['body'])
        ok = sh['share'] >= CP.k2_('f_keep') - 1e-12
        floor['objects'][x] = dict(share=round(sh['share'], 4), detail={k: round(v, 3) for k, v in sh.items()},
                                   pieces=len(delivered(ob)), pass_=bool(ok),
                                   delivered='carved' if ob.get('carved') is not None else 'default')
        if not ok:
            floor['fails'].append(dict(kind='share', obj=x, share=round(sh['share'], 4)))
    gated_frames = {}
    for o, p in pairs:
        if ctx.table() is None:
            floor['pairs'][f'{o}|{p}'] = dict(flag='s_floor_untestable (no table plane)')
            continue
        recv, guest, frames, info = floor_frames(ctx, o, p)
        rows = []
        for f in frames:
            pre = ctx.pre(recv, guest, f)
            row = dict(frame=int(f), precheck=pre)
            if pre['pass_']:
                ob_r, ob_g = ctx.objects[recv], ctx.objects[guest]
                ref_r = ob_r.get('carved_ref') if ob_r.get('carved') is not None and ob_r.get('carved_ref') else ob_r['ref']
                sr = ctx.sink(ref_r, ob_g['ref'], recv, guest, f, f'ref:{id(ref_r)}')
                sd = ctx.sink(delivered(ob_r), delivered(ob_g), recv, guest, f, f'delivered:{id(delivered(ob_r))}')
                row.update(S_ref=sr, S=sd, floor_fail=bool(sr['pass_'] and not sd['pass_']))
                if row['floor_fail']:
                    floor['fails'].append(dict(kind='S', pair=[recv, guest], frame=int(f),
                                               S_disp_mm=sd.get('disp_mm'), S_ref_disp_mm=sr.get('disp_mm')))
                gated_frames.setdefault((recv, guest), set()).add(int(f))
            else:
                ctx.push.append(dict(pair=[recv, guest], frame=int(f), check=pre['fail'], kind='pose_impossible (floor)'))
            rows.append(row)
        floor['pairs'][f'{o}|{p}'] = dict(receiver=recv, guest=guest, frames=frames, info=info, rows=rows)
    floor['pass_'] = not floor['fails']
    # ---- G1
    cfg = G.sim_rl()
    opt = G.options(cfg)
    packed = {}
    for x in objs:
        try:
            packed[x] = G.packed_default(visuals[x])
        except Exception as e:                                       # noqa: BLE001
            packed[x] = (None, dict(error=f'{type(e).__name__}: {e}'))
    gate = dict(rule='PREREG F-I5.16 (1)', config=cfg, options=opt, versions=G.versions(),
                packed={x: dict(pieces=None if v[0] is None else len(v[0]), info=v[1]) for x, v in packed.items()},
                pairs={})
    for (o, p), W in ctx.results.items():
        if W.get('receiver'):
            gated_frames.setdefault((W['receiver'], W['guest']), set())
        for comp in W.get('components') or []:
            if W.get('receiver'):
                for f in comp.get('ok_frames') or []:
                    gated_frames.setdefault((W['receiver'], W['guest']), set()).add(int(f))
    tb = ctx.table()
    all_ok = True
    for (recv, guest), frs in sorted(gated_frames.items()):
        rows = []
        ob_r, ob_g = ctx.objects[recv], ctx.objects[guest]
        Pr, Pg = packed[recv][0], packed[guest][0]
        for f in sorted(frs):
            Wr = _world(ctx.b, recv, f, ctx.poses)
            Wg = _world(ctx.b, guest, f, ctx.poses)
            sets = {}
            sets['delivered'] = G.count_scene('S', delivered(ob_r), delivered(ob_g), Wr, Wg, tb, opt)
            if Pr is not None and Pg is not None:
                sets['packed'] = G.count_scene('S', Pr, Pg, Wr, Wg, tb, opt)
            if ob_r.get('carved') is not None:
                sets['our_default'] = G.count_scene('S', ob_r['hulls'], ob_g['hulls'], Wr, Wg, tb, opt)
            rows.append(dict(scene='S', frame=int(f), gated='packed' in sets, sets=sets))
            log('G1', recv, guest, f, {k: {kk: vv for kk, vv in v.items() if kk != 'per_copy'} for k, v in sets.items()})
        W = ctx.results.get((recv, guest)) or ctx.results.get((guest, recv)) or {}
        sf = W.get('settle_frame')
        if sf is not None and W.get('receiver') == recv:
            if ctx.pre(recv, guest, sf)['pass_']:
                rows.append(settle_rows(ctx, recv, guest, sf, packed))
            else:
                rows.append(dict(scene='settle', frame=int(sf), gated=False, why='pose_impossible (report only)'))
        gr = [r for r in rows if r.get('gated')]
        verdict = G.g1(rows, opt) if all('packed' in r['sets'] for r in gr) else dict(
            pass_=False, fail='packed_default_unavailable')
        all_ok &= bool(verdict['pass_'])
        gate['pairs'][f'{recv}|{guest}'] = dict(rows=rows, verdict=verdict)
    if not gated_frames:
        gate['flag'] = 'contact_gate_pair_vacuous (no gated frame in any pair)'
    gate['g1_pass'] = bool(all_ok)
    if synthetic:
        gate['g2'] = dict(applies=False, why='synthetic pair: no FlashCHORD reference (F-I5.16 (1f))')
    else:
        gate['g2'] = G.g2_status(r0_dir)
    gate['caveat'] = 'G2: zero-action rollouts; a grasping policy may add hand-object contacts'
    return floor, gate


def settle_rows(ctx, recv, guest, frame, packed):
    """G1 P1 pre-check settle scene (both free) at the run's assembled frame asm[len // 2] (counts only)."""
    from gmg import contactgate5 as G
    opt = G.options(G.sim_rl())
    Wr = _world(ctx.b, recv, frame, ctx.poses)
    Wg = _world(ctx.b, guest, frame, ctx.poses)
    ob_r, ob_g = ctx.objects[recv], ctx.objects[guest]
    sets = dict(delivered=G.count_scene('settle', delivered(ob_r), delivered(ob_g), Wr, Wg, ctx.table(), opt))
    if packed[recv][0] is not None and packed[guest][0] is not None:
        sets['packed'] = G.count_scene('settle', packed[recv][0], packed[guest][0], Wr, Wg, ctx.table(), opt)
    return dict(scene='settle', frame=int(frame), gated=True, sets=sets)


def write_r2_records(sim_dir, ctx, floor, gate, synthetic=False):
    """Records of a round-2 folder; DO_NOT_USE.json (merged with write_round's) when the floor or G1 fails;
    CONTACT_GATE_PENDING.json while G2 has not run (not for synthetic pairs)."""
    from gmg import contactgate5 as G
    os.makedirs(sim_dir, exist_ok=True)

    def dump(name, obj):
        with open(os.path.join(sim_dir, name), 'w') as fh:
            json.dump(obj, fh, indent=1, default=IL._jdefault)
    dump('floor.json', floor)
    dump('contact_gate.json', gate)
    dump('push_list_fi5r2.json', dict(rule='PREREG F-I5.15 (3), (7): frames and pairs for the pose lanes',
                                      entries=ctx.push))
    reasons = {}
    if not floor.get('pass_', True):
        reasons['floor'] = floor['fails']
    if not gate.get('g1_pass', True):
        reasons['contact_gate_g1'] = {k: v['verdict'] for k, v in gate['pairs'].items() if not v['verdict']['pass_']}
    p = os.path.join(sim_dir, 'DO_NOT_USE.json')
    if reasons:
        prev = json.load(open(p)) if os.path.exists(p) else {}
        prev.update(dict(rule_fi5r2='PREREG F-I5.15 (4d) floor / F-I5.16 (1g) contact gate', reasons_fi5r2=reasons))
        with open(p, 'w') as fh:
            json.dump(prev, fh, indent=1, default=IL._jdefault)
    if not synthetic and not (gate.get('g2') or {}).get('can_run'):
        G.write_pending(sim_dir, gate['g2'])
    return dict(do_not_use=bool(reasons) or os.path.exists(p), reasons=reasons,
                contact_gate_pending=bool(not synthetic and not (gate.get('g2') or {}).get('can_run')))


# ------------------------------------------------------------------------------------------------ driver (rev 2)
def object_routes2(b, objs, bodies, picks_mesh, out_dir, log, structure=None, plate=None, n_objects=None):
    """Default pieces of every object under F-I5.15 / F-I5.16 (route_pieces2). Returns {obj: dict} for FI5R2."""
    from gmg import structure as ST, platebody as PB
    n = n_objects or len(objs)
    cap = CP.piece_cap(n)
    out = {}
    for o in objs:
        t = time.time()
        sp = os.path.join(out_dir, f'structure_{o}.json')
        if structure and o in structure:
            hyp = structure[o]
        elif os.path.exists(sp):
            with open(sp) as fh:
                hyp = json.load(fh)
        else:
            hyp = ST.hypotheses(b.obs(o), sigma=b.sigma(o))
            with open(sp, 'w') as fh:
                json.dump(hyp, fh, indent=1, default=IL._jdefault)
        ax = hyp.get('axis') or {}
        lathe_ok = bool((hyp.get('accepted') or {}).get('lathe'))
        if plate is not None and o in plate:
            pl = plate[o]
        else:
            pi = PB.plate_info(b, o, picks_mesh[o])
            pl = bool(pi.get('plate'))
        ev = IL.Evidence(b, o, bodies[o], sub=False)
        r = CP.route_pieces2(bodies[o], ev, cap, lathe_axis=(ax.get('c'), ax.get('a')) if ax else None,
                             lathe_ok=lathe_ok, plate_like=pl, sigma=b.sigma(o), log=log)
        log('F-I5 r2 pieces', o, r['route'], 'n', None if r['hulls'] is None else len(r['hulls']), json.dumps(
            r['tried'], default=IL._jdefault)[:1500], f'{time.time() - t:.0f}s')
        out[o] = dict(hulls=r['hulls'], body=bodies[o], route=r['route'], lathe=r.get('lathe'), plate_like=pl,
                      handle_hulls=r.get('handle_hulls') or [], cap=cap, ev=ev, gate_default=r['gate'],
                      tried=r['tried'], lathe_test=dict(accepted=lathe_ok, rotc_sigma=hyp.get('rotc_sigma')),
                      n_ring=len(r['hulls']) - r.get('n_handle', 0) if r['hulls'] is not None else 0)
    return out


def run_pairs2(b, objects, fh=None, hands=None, identity='eval', copies=16, log=None, physics=True, pairs=None):
    """As run_pairs with the round-2 context FI5R2."""
    log = log or print
    objs = list(objects)
    ctx = FI5R2(b, objects, hands=hands, copies=copies, log=log, physics=physics)
    pairs = pairs or [(objs[i], objs[j]) for i in range(len(objs)) for j in range(i + 1, len(objs))]
    report = dict(pairs={}, overlap_track={}, decisions=[])
    for o, p in pairs:
        sides = {}
        for t_, q in ((o, p), (p, o)):
            cf = b.contact(t_, q)['contact']
            evc = collider_evidence(b, t_, objects[t_]['hulls'], mesh=objects[t_].get('body'))
            intr = intrusions_colliders(b, t_, q, evc, ctx.Xs[q], cf)
            sides[t_] = IL.make_side(b, t_, q, evc, intr, cf, sources={}, identity=identity,
                                     partner_collider=ctx.Xs[q], fh=(fh or {}).get(t_))
        T = int(b.meta['T'])
        ser = overlap_track(objects[o]['hulls'], ctx.Xs[p], k_('sample_m') ** 3, b, o, p, range(0, T, 4))
        report['overlap_track'][f'{o}|{p}'] = dict(max_cm3=round(max(ser.values()), 3),
                                                   median_cm3=round(float(np.median(list(ser.values()))), 3))
        recs = IL.decide_pair(b, sides[o], sides[p], waiver_fi5=ctx)
        report['decisions'] += [IL.public(r) for r in recs]
        report['pairs'][f'{o}|{p}'] = public_result(ctx.results.get((o, p), {}))
        report.setdefault('_sides', {})[(o, p)] = sides
        report.setdefault('_recs', {})[(o, p)] = recs
    return ctx, report


def run_episode2(b, ep, objs, cands, picks, bodies, fh, hands, out_dir, sim_dir, identity='eval', copies=16, log=None,
                 structure=None, plate=None, physics=True, split='public'):
    """Round 2 (F-I5.15 / F-I5.16): default pieces (route_pieces2), pairs (FI5R2), floor and G1 / G2, delivery with
    the round-2 records. Returns the report (JSON-ready)."""
    from gmg import platebody as PB
    log = log or print
    t0 = time.time()
    objects = object_routes2(b, objs, bodies, {o: cands[o][picks[o]] for o in objs}, out_dir, log, structure, plate)
    missing = [o for o, v in objects.items() if v['hulls'] is None]
    report = dict(rule=WAIVER_REF, fi5_rev=2, routes={o: dict(route=v['route'], n=None if v['hulls'] is None else
                                                               len(v['hulls']), gate=v['gate_default'],
                                                               lathe_test=v['lathe_test'], plate_like=v['plate_like'],
                                                               tried=v['tried']) for o, v in objects.items()})
    if missing:
        report['do_not_use'] = f'no compliant default pieces: {missing}'
        return report
    ctx, rp = run_pairs2(b, objects, fh=fh, hands=hands, identity=identity, copies=copies, log=log, physics=physics)
    report.update({k: v for k, v in rp.items() if not k.startswith('_')})
    visuals = {o: cands[o][picks[o]] for o in objs}
    if physics:
        floor, gate = floor_and_gate(ctx, visuals, synthetic=False, r0_dir=sim_dir, log=log)
        report['floor'] = dict(pass_=floor['pass_'], fails=floor['fails'],
                               shares={x: v['share'] for x, v in floor['objects'].items()})
        report['contact_gate'] = dict(g1_pass=gate['g1_pass'], g2=gate['g2'],
                                      pairs={k: v['verdict'] for k, v in gate['pairs'].items()})
    if sim_dir:
        man = deliver(sim_dir, b, ep, split, ctx, visuals,
                      dict(source='P_sel', flag='sim_pose_fallback', tracks=b.meta.get('tracks')))
        mp = os.path.join(sim_dir, 'manifest.json')
        m = json.load(open(mp))
        m.update(fi5_rev=2, rule_fi5r2='PREREG F-I5.15, F-I5.16', owner_quotes=dict(
            fi4=PB.WAIVER_QUOTE, fi5=WAIVER_QUOTE, mandate_2122=MANDATE_QUOTE))
        with open(mp, 'w') as fh_:
            json.dump(m, fh_, indent=1, default=str)
        if physics:
            report['records'] = write_r2_records(sim_dir, ctx, floor, gate)
        report['sim_dir'] = sim_dir
        report['do_not_use'] = man.get('do_not_use') or (report.get('records') or {}).get('reasons') or None
    report['push_list'] = ctx.push
    report['sec'] = round(time.time() - t0, 1)
    return report
