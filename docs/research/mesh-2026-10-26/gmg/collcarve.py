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
    F-I5.13 diagnostic D2 (post hoc; never delivered): rest-anchored pocket, default ring layout, volume and reach caps
    reported only (topology still gates), S also on default and failed carves."""

    def __init__(self, b, objects, hands=None, copies=None, log=None, physics=True, c_override=None,
                 no_overshoot=False, poses=None, n_objects=None, diag_rest=False):
        self.b, self.objects, self.hands = b, objects, hands
        self.copies = copies or 16
        self.log = log or (lambda *a: None)
        self.physics = physics
        self.c_override, self.no_overshoot = c_override, no_overshoot
        self.diag_rest = bool(diag_rest)
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
                pcs = L.pieces(n_s, carved=None if self.diag_rest else ranges)    # D2 (b): default bands
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
        if self.diag_rest and self.physics and not caps_gate and rest[1] and self.b.meta.get('table'):
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
              no_overshoot=False, pairs=None, diag_rest=False):
    """Collider sides of every pair (F-I5.1, make_side: the same constructor as the export path), decide_pair with the
    F-I5 branch. OBJECTS as in FI5. Returns (ctx, report)."""
    log = log or print
    objs = list(objects)
    ctx = FI5(b, objects, hands=hands, copies=copies, log=log, physics=physics, c_override=c_override,
              no_overshoot=no_overshoot, diag_rest=diag_rest)
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
                structure=None, plate=None, physics=True, split='public'):
    """tools/interlock_dev.py --waiver-fi5: default colliders (object_routes), run_pairs, delivery. Returns the F-I5
    report (JSON-ready)."""
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
    ctx, rp = run_pairs(b, objects, fh=fh, hands=hands, identity=identity, copies=copies, log=log, physics=physics)
    report.update({k: v for k, v in rp.items() if not k.startswith('_')})
    if sim_dir:
        man = deliver(sim_dir, b, ep, split, ctx, {o: cands[o][picks[o]] for o in objs},
                      dict(source='P_sel', flag='sim_pose_fallback', tracks=b.meta.get('tracks')))
        report['sim_dir'] = sim_dir
        report['do_not_use'] = man.get('do_not_use')
    report['sec'] = round(time.time() - t0, 1)
    return report
