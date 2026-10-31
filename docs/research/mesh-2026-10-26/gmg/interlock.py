"""INTERLOCK stage (gmg; design `INTERLOCK.md` v2, pre-registration PREREG F-I1; build step BI1).

One implementation of the region builder and the carve rule, used by the gmg on our own tracks and by the Embodiment
session on its intrusion export (INTERLOCK section 11). GT-free: our bundle (grids, tracks, owned points), our
candidates, our images (gmg.silhouette), placed generator meshes (gmg.gen_slot) and the poses the simulator replays.

  load_bundle_any(path)                         our bundle (own run, role own; dev mode: a clean run's bundle, role
                                                clean_run)
  Evidence(b, obj, mesh)                        one object's grids in its own frame + candidate occupancy (4 mm, 2 mm)
  partner_points(b, p, exclude=None)            p's OBSERVED and shared voxels as 2 mm sub-samples (INTERLOCK 3.3)
  intrusions_from_tracks(b, o, p, ev_o, frames, poses=None, exclude_p=None) -> Intrusions
  intrusions_from_export(path, val, o, p, ev_o, partner_samples)  the same object from an export (gmg-intrusion/2)
  make_side(b, t, q, ev, intr, frames, sources, identity, ...)   one target of a pair, the same on both paths (F-I3.1)
  write_sources / load_sources                  sources (a), (b) and notches saved with a delivered round (F-I3.1)
  engaged_runs(intr, contact, stride)           runs, kinds (INSERTION / SEAT / SLIDE / TRANSIENT), d, assembled frames
  blocks(run)                                   10-frame build / check blocks (F-I1.1)
  regions(intr, run, ev_o, j)                   persistent 26-connected components with the sweep test (3.3)
  through_column(comp, d, ev)                   true through-column test (3.3)
  image_width(vox_lin, b, obj, poses)           image-plane width of a component in the views where stereo hit it (4.1)
  push_distance(...)                            smallest rigid translation of the partner that removes the intrusion
  decide_pair(...)                              F-I1.3 per component and pair: CARVE | PUSH | OFFSET | IGNORE
  offset(region, notches, d, ...)               OFFSET shift (4.4)
  agree(region, sources) -> tier                cross-check (3.4)
  carve_solid(...)                              the removed solid at width w (2 mm sub-voxels or an oriented box)
  icarve(mesh, solids)                          ICARVE candidate (manifold boolean)
  validate(path, sim_dir, ref_poses, tracks)    the export validator (11.2, F-I3.10; the Embodiment tool's header)
  carve_from_intrusions(...)                    the function the Embodiment session calls (11.3, F-I3.1, F-I3.3)
  round_accept(...)                             A1-A4 of round k (11.5, F-I3.3)
  default_physics()                             the physics_fn of carve_from_intrusions (simphys.pair_physics)
  load_sim(dir, episode)                        a delivered sim folder, refused for another episode (6.4) or when
                                                marked do-not-use (F-I3.8)

Constants: CONST below (F-I1.14 values and origins). guard.INFORMED_A6 (guard.py, build 1's file) does not list the
F-I1.14 rows yet, so the informed constants are kept in this module's registry and written into every report; generic
ones are also registered with the guard. Hook for B10: add 'F-I1.14' to INFORMED_A6 and register all.
"""
from __future__ import annotations

import builtins as _bi
import dataclasses
import hashlib
import json
import math
import os
import sys
import time

import numpy as np
from scipy import ndimage

from gmg import guard, contact as CT, geom

STATE_UNKNOWN, STATE_FREE, STATE_OBSERVED = 0, 1, 2
SCHEMA_INTR = 'gmg-intrusion/2'
SCHEMA_SIM = 'gmg-sim/1'

# name: (value, origin)  -- PREREG F-I1.14
CONST = dict(
    engaged_min_vox=(3, 'generic:F-I1.14 engaged >= 3 voxels'),
    gap_bridge_frames=(2, 'generic:F-I1.1 gaps <= 2 stride frames bridged'),
    transient_frames=(5, 'generic:F-I1.14 TRANSIENT < 5 frames'),
    static_speed_m=(0.002, 'generic:F-I1.14 static < 2 mm per frame'),
    static_min_frames=(5, 'generic:F-I1.1 static stretch >= 5 frames'),
    insert_travel_m=(0.020, 'informed:F-I1.14 travel 20 mm (XCarve design 22 Oct)'),
    insert_straightness=(0.7, 'informed:F-I1.14 straightness 0.7 (XCarve design 22 Oct)'),
    block_frames=(10, 'generic:F-I1.14 10-frame build/check blocks'),
    holdout_min_frames=(20, 'generic:F-I1.14 20-frame minimum'),
    persist_min=(5, 'generic:F-I1.14 Embodiment minimum frame count'),
    persist_share=(0.25, 'generic:F-I1.14 quartile'),
    sweep_min_m=(0.008, 'generic:F-I1.14 sweep max(8 mm, 3 j)'),
    sweep_k_j=(3.0, 'generic:F-I1.14 sweep max(8 mm, 3 j)'),
    through_beyond_vox=(1, 'generic:F-I1.14 through-column test 1 voxel'),
    class_o_max=(0.25, 'generic:F-I1.14 25 % class O'),
    swept_share=(0.5, 'generic:F-I1.14 50 % majority'),
    push_prior_m=(0.010, 'generic:F-I1.14 phys_fit v1 prior 10 mm'),
    push_prior_deg=(3.0, 'generic:F-I1.14 phys_fit v1 prior 3 deg'),
    push_step_m=(0.002, 'generic:numerical 2 mm (one sub-voxel)'),
    push_cap_m=(0.060, 'generic:numerical cap of the push search (6 x the prior)'),
    push_frames_max=(12, 'generic:numerical subsample of the build frames for the push proxy'),
    silgap_share=(0.75, 'generic:F-I1.3 (iii) 75 %'),
    budget_vol=(0.10, 'generic:F-I1.14 budget 10 %'),
    budget_reach=(0.6, 'generic:F-I1.14 reach 0.6'),
    w_bridge_px=(8.0, 'generic:F-I1.14 w_bridge 8 depth pixels [H]'),
    depth_scale=(0.5, 'sensor:depth input at half the 1600 x 1000 rectified resolution (depths_fs0.5)'),
    clearance_m=(0.001, 'informed:F-I1.14 1 mm clearance (26 Oct pre-registered carve rule)'),
    link_share=(0.5, 'generic:F-I1.14 linking share 50 %'),
    agree_dist_m=(0.010, 'generic:F-I1.14 = K-c 10 mm'),
    agree_deg=(15.0, 'generic:F-I1.14 = K-c 15 deg'),
    agree_share=(0.5, 'generic:F-I1.14 50 % majority'),
    min_testable=(3, 'generic:INTERLOCK 3.4 fewer than 3 testable voxels = absent'),
    offset_tmax_m=(0.020, 'informed:F-I1.14 OFFSET t_max 20 mm (dev offset 10.5-12.9 mm seen)'),
    offset_lateral=(0.5, 'generic:F-I1.14 OFFSET lateral share 0.5'),
    offset_grid_m=(0.002, 'generic:F-I1.14 OFFSET 2 mm grid'),
    sub_m=(0.002, 'generic:INTERLOCK 3 2 mm refinement'),
    fid_tol_m=(0.0005, 'generic:F-I1.14 fiducials 0.5 mm'),
    contain_share=(0.99, 'generic:F-I1.14 99 % containment'),
    contain_n=(10000, 'generic:INTERLOCK 11.2 10,000 samples'),
    max_rounds=(3, 'generic:F-I1.13 at most 3 rounds'),
)


def K(name):
    v, origin = CONST[name]
    if origin.startswith(('generic', 'sensor', 'kit')):
        guard.constant(f'il.{name}', v, origin)
    return v


def constants_report():
    return {k: dict(value=v, origin=o) for k, (v, o) in CONST.items()}


# ------------------------------------------------------------------------------------------------ bundle access
def load_bundle_any(path):
    """bundle.load_bundle with the role chosen by the path: the current run (role own) or, in dev mode, a clean run's
    bundle folder (role clean_run, DEV tier). Same Bundle object as bundle.load_bundle."""
    from gmg import bundle as BU
    rp = os.path.realpath(path)
    role = 'own'
    runs = os.path.realpath(os.path.join(guard.CFG['data'], 'gmg', 'runs'))
    if rp.startswith(runs + os.sep) and guard.mode() == 'dev':
        role = 'clean_run'
    if role == 'own':
        return BU.load_bundle(path)
    meta = guard.load_json(os.path.join(path, 'episode.json'), role)
    tp = meta['tracks']['path']
    guard.open_input(tp, 'tracks', expect_sha256=meta['tracks']['sha256'])
    poses = guard.load_npz(tp, 'tracks')
    obs = {}
    for o in meta['objects']:
        z = guard.load_npz(os.path.join(path, f'{o}.npz'), role, keys=list(BU.BUNDLE_KEYS))
        d = {k: z[k] for k in BU.BUNDLE_KEYS}
        d['vox'] = float(d['vox']); d['args'] = str(d['args'])
        obs[o] = d
    return BU.Bundle(meta, obs, poses, path=path)


class Grid:
    """A regular grid in an object's frame: voxel i has centre lo + (i + 0.5) vox."""

    def __init__(self, lo, vox, shape):
        self.lo = np.asarray(lo, np.float64); self.vox = float(vox); self.shape = tuple(int(s) for s in shape)

    def centres(self, lin=None):
        if lin is None:
            idx = np.indices(self.shape).reshape(3, -1).T
        else:
            idx = np.stack(np.unravel_index(np.asarray(lin, np.int64), self.shape), 1)
        return self.lo + (idx + 0.5) * self.vox

    def lin(self, P):
        vi = np.floor((np.asarray(P, np.float64) - self.lo) / self.vox).astype(np.int64)
        ok = np.all((vi >= 0) & (vi < np.asarray(self.shape)), axis=1)
        out = np.full(len(vi), -1, np.int64)
        if ok.any():
            out[ok] = np.ravel_multi_index(vi[ok].T, self.shape)
        return out, ok

    def sub(self, k=2):
        return Grid(self.lo, self.vox / k, [s * k for s in self.shape])

    @property
    def size(self):
        return int(np.prod(self.shape))


def sub_lin(grid, lin, k=2):
    """Linear indices on grid.sub(k) of the k^3 sub-voxels of voxels LIN of GRID."""
    idx = np.stack(np.unravel_index(np.asarray(lin, np.int64), grid.shape), 1)
    off = np.indices((k, k, k)).reshape(3, -1).T
    sidx = (idx[:, None, :] * k + off[None]).reshape(-1, 3)
    return np.ravel_multi_index(sidx.T, [s * k for s in grid.shape])


def parent_lin(grid, slin, k=2):
    sidx = np.stack(np.unravel_index(np.asarray(slin, np.int64), [s * k for s in grid.shape]), 1)
    return np.ravel_multi_index((sidx // k).T, grid.shape)


def fast_inside(mesh, X):
    """Inside test for candidate meshes: for a watertight mesh, the median over the three axis directions of the
    signed-crossing winding number (geom.winding_ray; exact for closed oriented meshes up to rays through edges, which
    the median over three axes removes); otherwise geom.inside (exact winding number). geom.inside's random check
    against the float32 solid-angle sum falls back to the exact sum for ALL points on a single disagreement, which
    takes tens of minutes on the 2 mm sub-grids; points within float precision of the surface are not decisive here."""
    X = np.asarray(X, np.float64).reshape(-1, 3)
    if len(X) == 0:
        return np.zeros(0, bool)
    if len(X) > 250000:                                   # chunks: the crossing-pair arrays grow with the queries
        return np.concatenate([fast_inside(mesh, X[i:i + 250000]) for i in range(0, len(X), 250000)])
    if mesh.is_watertight or len(X) > 20000:
        # a mesh that is not watertight after loading (a packed HULL can lose closure in trimesh's vertex merge) is
        # still tested by signed crossings when the query set is large: the exact solid-angle sum over a 1 mm grid
        # takes hours (median over three axes; the error is confined to rays through the open edges)
        w = np.median(np.stack([geom.winding_ray(mesh, X, k) for k in range(3)]), axis=0)
        return w >= 0.5
    return geom.inside(mesh, X)[0]


class Evidence:
    """Grids of one object (its bundle grids, 4 mm) and the occupancy of one candidate mesh on them; also the 2 mm
    sub-grid occupancy used for carving."""

    def __init__(self, b, obj, mesh, sub=True):
        ob = b.obs(obj)
        self.b, self.obj, self.mesh = b, obj, mesh
        self.grid = Grid(ob['lo'], ob['vox'], np.asarray(ob['state']).shape)
        self.state = np.asarray(ob['state']).ravel()
        self.hits = np.asarray(ob['hits']).ravel()
        self.shared = np.asarray(ob.get('shared', np.zeros(self.grid.shape))).ravel()
        self.occ = fast_inside(mesh, self.grid.centres())
        self.sgrid = self.grid.sub(2)
        self.socc = fast_inside(mesh, self.sgrid.centres()) if sub else None
        self.sigma = b.sigma(obj)

    def extent_along(self, u):
        C = self.grid.centres(np.nonzero(self.occ)[0])
        s = C @ u
        return float(s.max() - s.min() + self.grid.vox) if len(s) else 0.0

    def solid_cm3(self):
        if self.socc is not None:
            return float(self.socc.sum()) * self.sgrid.vox ** 3 * 1e6
        return float(self.occ.sum()) * self.grid.vox ** 3 * 1e6


def partner_points(b, p, exclude=None):
    """INTERLOCK 3.3: p's OBSERVED and shared voxels, each as 8 sub-samples on a 2 mm lattice (+-vox/4), in p's frame.
    exclude: optional (Grid, bool array on that grid) in p's frame (p's own carved region): samples inside are dropped."""
    ob = b.obs(p)
    g = Grid(ob['lo'], ob['vox'], np.asarray(ob['state']).shape)
    st = np.asarray(ob['state']).ravel()
    sh = np.asarray(ob.get('shared', np.zeros(g.shape))).ravel()
    lin = np.nonzero((st == STATE_OBSERVED) | (sh > 0))[0]
    C = g.centres(lin)
    q = g.vox / 4.0
    off = np.array([[sx, sy, sz] for sx in (-q, q) for sy in (-q, q) for sz in (-q, q)])
    X = (C[:, None, :] + off[None]).reshape(-1, 3)
    if exclude is not None:
        eg, em = exclude
        el, ok = eg.lin(X)
        drop = np.zeros(len(X), bool)
        drop[ok] = em[el[ok]]
        X = X[~drop]
    return X


@dataclasses.dataclass
class Intrusions:
    """Partner samples inside the target candidate, per frame, in the target frame (pts) and in the partner frame
    (pts_p); lin = target voxel (4 mm); rel[f] = T_{o<-p}[f]; all_frames = the frames examined (contact frames).
    source: 'tracks' (our tracks, full partner samples available for the push proxy) or 'export'."""
    target: str
    partner: str
    frame: np.ndarray
    pts: np.ndarray
    pts_p: np.ndarray
    lin: np.ndarray
    rel: dict
    all_frames: list
    source: str
    Xp: np.ndarray = None                    # full partner samples (partner frame), tracks only
    pushed_residual: dict = None             # export: frame -> pushed_residual_m (NaN if refused)

    def entered(self, f):
        return np.unique(self.lin[self.frame == f])

    def count(self, f):
        return int(len(self.entered(f)))


def rel_pose(poses, o, p, f):
    return CT.rel(poses, o, p, f)


def intrusions_from_tracks(b, o, p, ev_o, frames, poses=None, exclude_p=None):
    poses = b.poses if poses is None else poses
    Xp = partner_points(b, p, exclude_p)
    fr, P, Pp, L, rel = [], [], [], [], {}
    for f in frames:
        T = rel_pose(poses, o, p, f)
        rel[int(f)] = T
        X = Xp @ T[:3, :3].T + T[:3, 3]
        lin, ok = ev_o.grid.lin(X)
        k = ok.copy()
        k[ok] = ev_o.occ[lin[ok]]
        if k.any():
            fr.append(np.full(int(k.sum()), int(f), np.int64)); P.append(X[k]); Pp.append(Xp[k]); L.append(lin[k])
    cat = (lambda a, d: np.concatenate(a) if a else np.zeros((0,) + d))
    return Intrusions(o, p, cat(fr, ()).astype(np.int64), cat(P, (3,)), cat(Pp, (3,)), cat(L, ()).astype(np.int64),
                      rel, [int(f) for f in frames], 'tracks', Xp=Xp)


# ------------------------------------------------------------------------------------------------ runs and blocks
@dataclasses.dataclass
class Run:
    frames: list
    kind: str
    travel_m: float
    straightness: float
    d: np.ndarray
    assembled: list
    static: list
    build: list
    check: list
    flags: list

    def summary(self):
        return dict(frames=[self.frames[0], self.frames[-1]], n=len(self.frames), kind=self.kind,
                    travel_mm=round(self.travel_m * 1e3, 1), straightness=round(self.straightness, 3),
                    d=np.round(self.d, 4).tolist(), assembled=[self.assembled[0], self.assembled[-1]]
                    if self.assembled else [], n_assembled=len(self.assembled), n_build=len(self.build),
                    n_check=len(self.check), flags=list(self.flags))


def _static_stretches(frames, path):
    """Maximal stretches of consecutive frames with speed < static_speed (per frame), >= static_min frames long."""
    v_max, n_min = K('static_speed_m'), K('static_min_frames')
    out, cur = [], [frames[0]]
    for i in range(1, len(frames)):
        sp = np.linalg.norm(path[i] - path[i - 1]) / max(frames[i] - frames[i - 1], 1)
        if sp < v_max:
            cur.append(frames[i])
        else:
            if len(cur) >= n_min:
                out.append(cur)
            cur = [frames[i]]
    if len(cur) >= n_min:
        out.append(cur)
    return out


def blocks(run_frames):
    """F-I1.1: consecutive 10-frame blocks, even blocks build, odd blocks check; < 20 frames: all build, no hold-out."""
    nb, nmin = K('block_frames'), K('holdout_min_frames')
    fr = list(run_frames)
    if len(fr) < nmin:
        return fr, [], ['no_holdout']
    build, check = [], []
    for i in range(0, len(fr), nb):
        (build if (i // nb) % 2 == 0 else check).extend(fr[i:i + nb])
    return build, check, []


def classify_path(frames, rel):
    path = np.array([rel[f][:3, 3] for f in frames])
    if len(path) < 2:
        return 0.0, 0.0, np.array([1.0, 0, 0]), path
    c = path - path.mean(0)
    _, s, Vt = np.linalg.svd(c, full_matrices=False)
    d = Vt[0]
    if (path[-1] - path[0]) @ d < 0:
        d = -d
    pr = c @ d
    travel = float(pr.max() - pr.min())
    straight = float(s[0] / max(s.sum(), 1e-12))
    return travel, straight, d, path


def engaged_runs(intr, contact_frames, stride, holdout=None):
    """F-I1.1 engaged runs of one ordered pair (target <- partner). holdout (F-I3.3, iteration): the check frames fixed
    by an earlier round; they are never build frames, and frames outside them follow the 10-frame blocks."""
    nmin = K('engaged_min_vox'); gap = K('gap_bridge_frames'); ntr = K('transient_frames')
    cf = sorted(int(f) for f in contact_frames if int(f) in intr.rel)
    eng = [f for f in cf if intr.count(f) >= nmin]
    runs = []
    if not eng:
        return runs
    groups, cur = [], [eng[0]]
    for f in eng[1:]:
        if f - cur[-1] <= (gap + 1) * stride:
            cur.append(f)
        else:
            groups.append(cur); cur = [f]
    groups.append(cur)
    for g in groups:
        fr = [f for f in cf if g[0] <= f <= g[-1]]
        travel, straight, d, path = classify_path(fr, intr.rel)
        static = _static_stretches(fr, path) if len(fr) >= 2 else []
        if len(fr) < ntr:
            kind = 'TRANSIENT'
        elif travel >= K('insert_travel_m') and straight >= K('insert_straightness'):
            kind = 'INSERTION'
        elif static:
            kind = 'SEAT'
        else:
            kind = 'SLIDE'
        asm = static[-1] if (static and kind in ('INSERTION', 'SEAT')) else []
        build, check, flags = blocks(fr)
        if holdout:
            hs = set(int(f) for f in holdout)
            if hs & set(fr):                      # a run seen before: its check frames stay the earlier round's
                check = sorted(hs & set(fr))
                build = [f for f in fr if f not in hs]
                flags = [x for x in flags if x != 'no_holdout'] + ['holdout_fixed']
        runs.append(Run(fr, kind, travel, straight, d, asm, static, build, check, flags))
    return runs


# ------------------------------------------------------------------------------------------------ regions
@dataclasses.dataclass
class Component:
    target: str
    partner: str
    lin: np.ndarray            # target voxels (4 mm) of the component (before any split)
    n_v: np.ndarray            # build-frame entry counts of those voxels
    swept: np.ndarray          # bool per voxel
    ext90_mm: np.ndarray       # sweep extent per voxel (mm)
    run: Run
    nmin: int
    carve_lin: np.ndarray = None   # after the split (entry side) or = lin
    split: dict = None
    info: dict = dataclasses.field(default_factory=dict)

    def region(self):
        return self.lin if self.carve_lin is None else self.carve_lin


def regions(intr, run, ev_o, j_m):
    """INTERLOCK 3.3 on the run's build frames: persistent voxels n_v >= max(5, ceil(0.25 N_build)), sweep test per
    voxel (partner-local positions of the entering samples span >= max(8 mm, 3 j) at their 5-95 % extent along their
    principal axis), 26-connected components."""
    B = run.build
    nmin = max(K('persist_min'), int(math.ceil(K('persist_share') * len(B))))
    sel = np.isin(intr.frame, B)
    fr, lin, pp = intr.frame[sel], intr.lin[sel], intr.pts_p[sel]
    if len(lin) == 0:
        return [], nmin
    key = np.unique(np.stack([lin, fr], 1), axis=0)
    cnt = np.bincount(key[:, 0], minlength=ev_o.grid.size)
    P = cnt >= nmin
    if not P.any():
        return [], nmin
    s_min = max(K('sweep_min_m'), K('sweep_k_j') * float(j_m))
    lab, n = ndimage.label(P.reshape(ev_o.grid.shape), structure=np.ones((3, 3, 3)))
    lab = lab.ravel()
    # sweep extents for persistent voxels
    m = P[lin]
    lv, pv = lin[m], pp[m]
    o = np.argsort(lv, kind='stable'); lv, pv = lv[o], pv[o]
    uv, st = np.unique(lv, return_index=True)
    ext = {}
    for i, v in enumerate(uv):
        Q = pv[st[i]: st[i + 1] if i + 1 < len(st) else len(pv)]
        if len(Q) < 2:
            ext[int(v)] = 0.0; continue
        c = Q - Q.mean(0)
        ax = np.linalg.svd(c, full_matrices=False)[2][0]
        s = c @ ax
        ext[int(v)] = float(np.percentile(s, 95) - np.percentile(s, 5))
    comps = []
    for k in range(1, n + 1):
        cl = np.nonzero(lab == k)[0]
        e = np.array([ext.get(int(v), 0.0) for v in cl])
        comps.append(Component(intr.target, intr.partner, cl, cnt[cl], e >= s_min, e * 1e3, run, nmin,
                               info=dict(s_min_mm=round(s_min * 1e3, 2))))
    return comps, nmin


def through_column(lin, d, ev):
    """True through-column (3.3): along d the component exits the target at both ends. Each end of the component is
    its end layer (voxels within one voxel of its smallest / largest coordinate along d); from every end-layer voxel
    the first point at least one voxel further along -d / +d that is not in the component is tested: outside the
    candidate or FREE = exits; the end exits if the majority of its layer does. Returns (bool, info)."""
    g = ev.grid
    C = g.centres(lin)
    d = d / np.linalg.norm(d)
    s = C @ d
    member = np.zeros(g.size, bool); member[lin] = True
    shares = {}
    for sign, name in ((-1, 'entry'), (+1, 'far')):
        end = (s <= s.min() + g.vox) if sign < 0 else (s >= s.max() - g.vox)
        ex = []
        for x in C[end]:
            ok = None
            for step in range(1, 4):
                q = x + sign * d * g.vox * step * K('through_beyond_vox')
                ql, inside_grid = g.lin(q[None])
                if not inside_grid[0]:
                    ok = True; break
                if member[ql[0]]:
                    continue
                ok = (not ev.occ[ql[0]]) or ev.state[ql[0]] == STATE_FREE
                break
            ex.append(bool(ok))
        shares[name] = float(np.mean(ex)) if ex else 0.0
    lo, hi = shares['entry'], shares['far']
    return (lo >= 0.5 and hi >= 0.5), dict(exit_share_entry_end=round(lo, 3), exit_share_far_end=round(hi, 3),
                                           extent_along_d_mm=round(float(s.max() - s.min() + g.vox) * 1e3, 1))


# ------------------------------------------------------------------------------------------------ topology
def topology(occ_grid):
    """(components (26-connected), Euler number (26-connectivity)) of a boolean 3-D grid."""
    from skimage.measure import euler_number
    if not occ_grid.any():
        return 0, 0
    _, n = ndimage.label(occ_grid, structure=np.ones((3, 3, 3)))
    return int(n), int(euler_number(np.pad(occ_grid, 1), connectivity=3))


def topology_kept(ev, remove_lin, sub=False):
    """Removing voxels REMOVE_LIN (4 mm grid, or the 2 mm sub-grid when sub) keeps the candidate's component count
    and Euler number (a notch, not a hole or a split)."""
    if sub:
        g, occ = ev.sgrid, ev.socc
    else:
        g, occ = ev.grid, ev.occ
    A = occ.reshape(g.shape)
    Bm = occ.copy(); Bm[np.asarray(remove_lin, np.int64)] = False
    t0, t1 = topology(A), topology(Bm.reshape(g.shape))
    return t0 == t1, dict(before=list(t0), after=list(t1))


# ------------------------------------------------------------------------------------------------ image width (GAP)
class FrameHits:
    """Per frame, the voxels of OBJ's grid with at least one owned depth point of that frame."""

    def __init__(self, b, obj, grid):
        ob = b.obs(obj)
        own = np.asarray(ob.get('own', np.zeros(len(ob['pts']), np.uint8)))
        P = np.asarray(ob['pts'])[own == 0]
        fr = np.asarray(ob['frame'])[own == 0]
        lin, ok = grid.lin(P)
        key = np.unique(np.stack([fr[ok].astype(np.int64), lin[ok]], 1), axis=0)
        self.f, self.l = key[:, 0], key[:, 1]

    def hit(self, f, lin):
        a, bb = np.searchsorted(self.f, [f, f + 1])
        return np.isin(lin, self.l[a:bb])


def project(K_, Xc):
    z = Xc[:, 2]
    return np.stack([K_[0, 0] * Xc[:, 0] / z + K_[0, 2], K_[1, 1] * Xc[:, 1] / z + K_[1, 2]], 1), z


def image_width(lin, b, obj, grid, frames, poses=None, fh=None):
    """INTERLOCK 4.1 GAP: in every frame in which >= 3 of the component's voxels have depth hits, project the
    component's 1 mm lattice points (inside its voxels) into the depth image (rectified K x depth_scale), rasterise,
    close 3 x 3, and take 2 x the largest inscribed radius (distance transform; radius from a pixel centre to the edge
    = dt - 0.5). Median over those frames, in depth pixels; None if no such frame."""
    import cv2
    poses = b.poses if poses is None else poses
    fh = fh or FrameHits(b, obj, grid)
    sc = K('depth_scale')
    Kd = np.asarray(b.meta['K'], np.float64).copy()
    Kd[0, 0] *= sc; Kd[1, 1] *= sc
    Kd[0, 2] = (Kd[0, 2] + 0.5) * sc - 0.5; Kd[1, 2] = (Kd[1, 2] + 0.5) * sc - 0.5
    W, H = int(CT.IMG_W * sc), int(CT.IMG_H * sc)
    # the region as the partner's body: closed in 3-D (2 iterations) inside the voxels it spans, so the gap between the
    # partner's two observed faces (its UNKNOWN interior has no evidence samples) does not split it (T-I1 fix, F-I2.3)
    Rm = np.zeros(grid.size, bool); Rm[np.asarray(lin, np.int64)] = True
    Rc = ndimage.binary_closing(np.pad(Rm.reshape(grid.shape), 3), structure=np.ones((3, 3, 3)), iterations=2)
    lin = np.nonzero(Rc[3:-3, 3:-3, 3:-3].ravel() | Rm)[0]
    C = grid.centres(lin)
    t = (-1.5, -0.5, 0.5, 1.5)
    off = np.array([[a, bb, c] for a in t for bb in t for c in t]) * (grid.vox / 4.0)   # 1 mm lattice in a 4 mm voxel
    X = (C[:, None, :] + off[None]).reshape(-1, 3)
    widths = []
    for f in frames:
        if fh.hit(f, lin).sum() < 3:
            continue
        T = poses[f'cam_T_{obj}'][f].astype(np.float64)
        Xc = X @ T[:3, :3].T + T[:3, 3]
        if (Xc[:, 2] <= 0.05).any():
            continue
        uv, _ = project(Kd, Xc)
        ui, vi = np.floor(uv[:, 0]).astype(int), np.floor(uv[:, 1]).astype(int)
        ok = (ui >= 0) & (ui < W) & (vi >= 0) & (vi < H)
        if ok.sum() < 3:
            continue
        x0, y0 = ui[ok].min() - 3, vi[ok].min() - 3
        m = np.zeros((vi[ok].max() - y0 + 4, ui[ok].max() - x0 + 4), np.uint8)
        m[vi[ok] - y0, ui[ok] - x0] = 1
        m = cv2.morphologyEx(m, cv2.MORPH_CLOSE, np.ones((3, 3), np.uint8))
        m = ndimage.binary_fill_holes(m).astype(np.uint8)      # holes = partner interior without evidence (T-I1 fix)
        dt = cv2.distanceTransform(m, cv2.DIST_L2, cv2.DIST_MASK_PRECISE)
        widths.append(max(0.0, 2.0 * (float(dt.max()) - 0.5)))
    if not widths:
        return None, dict(views=0)
    return float(np.median(widths)), dict(views=len(widths), p10_p90=[round(float(np.percentile(widths, 10)), 2),
                                                                       round(float(np.percentile(widths, 90)), 2)])


# ------------------------------------------------------------------------------------------------ push proxy
def _dirs26(extra=()):
    D = np.array([[i, j, k] for i in (-1, 0, 1) for j in (-1, 0, 1) for k in (-1, 0, 1) if (i, j, k) != (0, 0, 0)],
                 np.float64)
    D /= np.linalg.norm(D, axis=1, keepdims=True)
    for e in extra:
        e = np.asarray(e, np.float64); e = e / np.linalg.norm(e)
        D = np.vstack([D, e, -e])
    return D


def push_distance(intr, frames, region_lin, ev, normal=None):
    """F-I1.3 (ii) proxy: per frame, the smallest rigid translation of the partner (26 directions plus +-normal, 2 mm
    steps up to push_cap) that leaves < 3 entered voxels in the region dilated by 2 voxels; median over (at most
    push_frames_max evenly spaced) frames. Tracks input moves all partner samples; export input moves only the exported
    samples (a lower bound of re-entry, i.e. the push is easier there). Returns (median m, per-frame list)."""
    g = ev.grid
    Rm = np.zeros(g.size, bool); Rm[region_lin] = True
    Rm = ndimage.binary_dilation(Rm.reshape(g.shape), structure=np.ones((3, 3, 3)), iterations=2).ravel() & ev.occ
    D = _dirs26([normal] if normal is not None else [])
    step, cap = K('push_step_m'), K('push_cap_m')
    steps = np.arange(step, cap + 1e-9, step)
    fr = list(frames)
    nmax = K('push_frames_max')
    if len(fr) > nmax:
        fr = [fr[i] for i in np.linspace(0, len(fr) - 1, nmax).round().astype(int)]
    out = []
    for f in fr:
        if intr.Xp is not None:
            T = intr.rel[f]
            X = intr.Xp @ T[:3, :3].T + T[:3, 3]
        else:
            X = intr.pts[intr.frame == f]
        lo, hi = g.lo - cap - g.vox, g.lo + np.asarray(g.shape) * g.vox + cap + g.vox
        X = X[np.all((X > lo) & (X < hi), axis=1)]
        best = np.inf
        for dvec in D:
            for s in steps:
                if s >= best:
                    break
                l, ok = g.lin(X + dvec * s)
                n = len(np.unique(l[ok][Rm[l[ok]]]))
                if n < K('engaged_min_vox'):
                    best = s
                    break
        out.append(float(best))
    med = float(np.median(out)) if out else float('nan')
    return med, out


# ------------------------------------------------------------------------------------------------ geometry helpers
def axes_of(C, d=None):
    """Principal axes of points C; with d: (d, n, m) where n is the thinner in-plane axis perpendicular to d."""
    c = C.mean(0)
    if len(C) < 3:
        B = np.eye(3) if d is None else None
        if d is None:
            return c, B, np.zeros(3)
        d = d / np.linalg.norm(d)
        n = np.cross(d, [1.0, 0, 0]) if abs(d[0]) < 0.9 else np.cross(d, [0, 1.0, 0])
        n /= np.linalg.norm(n)
        return c, np.stack([d, n, np.cross(d, n)]), np.zeros(2)
    if d is None:
        _, s, Vt = np.linalg.svd(C - c, full_matrices=False)
        return c, Vt, s
    d = d / np.linalg.norm(d)
    Q = (C - c) - np.outer((C - c) @ d, d)
    _, s, Vt = np.linalg.svd(Q, full_matrices=False)
    m, n = Vt[0], Vt[1]
    n = n - (n @ d) * d; n /= np.linalg.norm(n)
    m = np.cross(d, n)
    return c, np.stack([d, n, m]), s


def mean_pose(Ts):
    from scipy.spatial.transform import Rotation as Rot
    Ts = np.asarray(Ts)
    R = Rot.from_matrix(Ts[:, :3, :3]).mean().as_matrix()
    T = np.eye(4); T[:3, :3] = R; T[:3, 3] = np.median(Ts[:, :3, 3], axis=0)
    return T


def map_occ(ev_src, T_dst_src, ev_dst):
    """Voxels of ev_dst whose centres, mapped into ev_src's frame, lie in ev_src's candidate occupancy."""
    Ti = np.linalg.inv(T_dst_src)
    C = ev_dst.grid.centres()
    X = C @ Ti[:3, :3].T + Ti[:3, 3]
    l, ok = ev_src.grid.lin(X)
    out = np.zeros(ev_dst.grid.size, bool)
    out[ok] = ev_src.occ[l[ok]]
    return out


def dilate(grid, lin, it=1):
    m = np.zeros(grid.size, bool); m[np.asarray(lin, np.int64)] = True
    return ndimage.binary_dilation(m.reshape(grid.shape), structure=np.ones((3, 3, 3)), iterations=it).ravel()


# ------------------------------------------------------------------------------------------------ widths, solids
def partner_thickness(C_world_o, n, ev_o):
    """1-99 % extent along n of points (in o's frame) inside o's candidate dilated by 2 voxels."""
    Dm = ndimage.binary_dilation(ev_o.occ.reshape(ev_o.grid.shape), structure=np.ones((3, 3, 3)), iterations=2).ravel()
    l, ok = ev_o.grid.lin(C_world_o)
    k = np.zeros(len(C_world_o), bool); k[ok] = Dm[l[ok]]
    if k.sum() < 10:
        return None
    s = C_world_o[k] @ n
    return float(np.percentile(s, 99) - np.percentile(s, 1)), float(0.5 * (np.percentile(s, 99) + np.percentile(s, 1)))


def carve_solid(ev, comp_lin, frame3, centre_n, w, plate=True, extend=0.003, exclude_lin=None):
    """The removed solid of a component at width w (INTERLOCK 3.5): the candidate's 2 mm sub-voxels inside the
    component's (d, m) footprint (its voxels' squares, +-2 mm) with |n - centre_n| <= w / 2 (F-I2.5: the width also
    applies when the region is not plate-like). Plate-like regions (both other extents >= 2 w) are also described
    as an oriented box, extended by EXTEND on every side where the component reaches the candidate surface, so the
    pieces can be cut exactly (simpieces.remove_box). Returns dict(kind 'box' | 'voxels', sub_lin, cm3, ...)."""
    d, n, m = frame3
    C = ev.grid.centres(comp_lin)
    sd, sm = C @ d, C @ m
    h = ev.grid.vox / 2
    ext_d = [sd.min() - h, sd.max() + h]
    ext_m = [sm.min() - h, sm.max() + h]
    slin = np.nonzero(ev.socc)[0]
    S = ev.sgrid.centres(slin)
    sg = ev.sgrid.vox
    # footprint of the component in (d, m) on a 2 mm raster
    fd = np.floor((S @ d - ext_d[0]) / sg).astype(np.int64); fm = np.floor((S @ m - ext_m[0]) / sg).astype(np.int64)
    nd, nm = int(np.ceil((ext_d[1] - ext_d[0]) / sg)) + 1, int(np.ceil((ext_m[1] - ext_m[0]) / sg)) + 1
    F = np.zeros((nd, nm), bool)
    cd = np.floor((sd - ext_d[0]) / sg).astype(np.int64); cm = np.floor((sm - ext_m[0]) / sg).astype(np.int64)
    for a_ in (-1, 0, 1):
        for b_ in (-1, 0, 1):
            F[np.clip(cd + a_, 0, nd - 1), np.clip(cm + b_, 0, nm - 1)] = True
    okf = (fd >= 0) & (fd < nd) & (fm >= 0) & (fm < nm)
    inF = np.zeros(len(S), bool); inF[okf] = F[fd[okf], fm[okf]]
    slab = np.abs(S @ n - centre_n) <= w / 2
    sel = inF & slab
    if exclude_lin is not None and len(exclude_lin):              # class O voxels are never carved (4.2 (iii))
        ex = np.zeros(ev.sgrid.size, bool); ex[sub_lin(ev.grid, exclude_lin)] = True
        sel &= ~ex[slin]
    out = dict(kind='voxels', sub_lin=slin[sel], cm3=float(sel.sum()) * sg ** 3 * 1e6, width_mm=round(w * 1e3, 2))
    if plate and (ext_d[1] - ext_d[0]) >= 2 * w:
        def open_side(axis, val, sign):
            q = C[np.abs(C @ axis - val) <= ev.grid.vox] + sign * axis * ev.grid.vox * 1.5
            l, ok = ev.grid.lin(q)
            occ = np.zeros(len(q), bool); occ[ok] = ev.occ[l[ok]]
            return float((~occ).mean()) >= 0.5 if len(q) else False
        lo_d = ext_d[0] - (extend if open_side(d, sd.min(), -1) else 0.0)
        hi_d = ext_d[1] + (extend if open_side(d, sd.max(), +1) else 0.0)
        lo_m = ext_m[0] - (extend if open_side(m, sm.min(), -1) else 0.0)
        hi_m = ext_m[1] + (extend if open_side(m, sm.max(), +1) else 0.0)
        cen = d * 0.5 * (lo_d + hi_d) + n * centre_n + m * 0.5 * (lo_m + hi_m)
        half = np.array([0.5 * (hi_d - lo_d), 0.5 * w, 0.5 * (hi_m - lo_m)])
        A = np.stack([d, n, m])
        inside = np.all(np.abs((S - cen) @ A.T) <= half, axis=1)
        if exclude_lin is not None and len(exclude_lin) and (inside & ex[slin]).any():
            return out                                        # a box would cut seen-solid voxels: voxel carve
        out.update(kind='box', axes=A.tolist(), centre=cen.tolist(), half=half.tolist(), sub_lin=slin[inside],
                   cm3=float(inside.sum()) * sg ** 3 * 1e6)
    return out


def solid_mesh(ev, solid):
    """A watertight mesh of a carve solid (box: exact box extended 0.5 mm; voxels: marching cubes of the 2 mm
    sub-voxels dilated by one sub-voxel) in the target's frame."""
    import trimesh
    if solid['kind'] == 'box':
        A = np.asarray(solid['axes']); cen = np.asarray(solid['centre']); half = np.asarray(solid['half'])
        T = np.eye(4); T[:3, :3] = A.T; T[:3, 3] = cen
        return trimesh.creation.box(extents=2 * half + 0.0005, transform=T)
    from skimage import measure
    g = ev.sgrid
    occ = np.zeros(g.size, bool); occ[solid['sub_lin']] = True
    occ = ndimage.binary_dilation(occ.reshape(g.shape), iterations=1)
    v, f, _, _ = measure.marching_cubes(np.pad(occ.astype(np.float32), 1), level=0.5)
    v = g.lo + (v - 1 + 0.5) * g.vox
    msh = trimesh.Trimesh(v, f[:, ::-1], process=True)
    if msh.is_watertight and msh.volume < 0:
        msh.invert()
    return msh


def icarve(mesh, solids_meshes):
    """ICARVE(c) = c minus the carve solids by a manifold boolean (trimesh / manifold3d). Returns (mesh, info)."""
    import trimesh
    out = mesh
    for s in solids_meshes:
        out = trimesh.boolean.difference([out, s], engine='manifold')
    info = dict(watertight=bool(out.is_watertight), faces=int(len(out.faces)),
                volume_cm3=round(float(out.volume) * 1e6, 2) if out.is_watertight else None,
                removed_cm3=round(float(mesh.volume - out.volume) * 1e6, 2) if (out.is_watertight and
                                                                                 mesh.is_watertight) else None,
                bodies=int(len(out.split(only_watertight=False))))
    return out, info


# ------------------------------------------------------------------------------------------------ sources and classes
def sil_classes(sil, lin, grid=None):
    """Per voxel of LIN: 'SIL' (see-through), 'SOLID' (testable, not see-through) or None (silhouette absent for it:
    gate failed, not run, or NMV < 3). sil = dict(nmv, nmf, gate_ok[, nmv_sub, nmf_sub]) on the 4 mm grid (and its
    2 mm sub-grid). With sub-grid votes (PREREG F-I2.1, T-I1 fix) a 4 mm voxel is SIL if any of its 8 sub-voxels is
    see-through and SOLID if none is and one is testable: a 4 mm voxel straddling a slot edge is not seen solid."""
    out = np.full(len(lin), None, object)
    if not sil or not sil.get('gate_ok'):
        return out
    lin = np.asarray(lin, np.int64)
    if sil.get('nmv_sub') is not None and grid is not None:
        sl = sub_lin(grid, lin).reshape(len(lin), 8)
        nmv, nmf = np.asarray(sil['nmv_sub'])[sl], np.asarray(sil['nmf_sub'])[sl]
        test = nmv >= 3
        see = test & (nmf >= 3) & (nmf >= 0.5 * nmv)
        out[test.any(1)] = 'SOLID'
        out[see.any(1)] = 'SIL'
        return out
    nmv, nmf = np.asarray(sil['nmv'])[lin], np.asarray(sil['nmf'])[lin]
    test = nmv >= 3
    see = test & (nmf >= 3) & (nmf >= 0.5 * nmv)
    out[test] = 'SOLID'
    out[see] = 'SIL'
    return out


def entry_open_share(lin, d, ev):
    """Share of the columns (along d) of voxel set LIN whose entry end (-d) exits the candidate (3.4 (a) open test)."""
    _, info = through_column(lin, d, ev)
    return info['exit_share_entry_end']


def touching_components(grid, mask, near):
    """Linear indices of the whole 26-connected components of MASK (bool on GRID) that touch NEAR (bool)."""
    lab, n = ndimage.label(np.asarray(mask, bool).reshape(grid.shape), structure=np.ones((3, 3, 3)))
    lab = lab.ravel()
    ids = np.unique(lab[np.asarray(near, bool) & (lab > 0)])
    return np.nonzero(np.isin(lab, ids) & (lab > 0))[0] if len(ids) else np.zeros(0, np.int64)


def agree(R, d, ev, gen=None, sil=None, N_b=None, comp_axes=None):
    """INTERLOCK 3.4 for one region R (4 mm voxels of the target): presence and agreement of (a) generator concavity,
    (b) silhouette, with (c) = R itself (present when this is called). Returns dict with present/agree per source
    and pair, the tier candidates and the reasons.
    PREREG F-I3.5 (two-way, notch-shaped (a)): the (a) notch is the WHOLE connected components of C_a that touch R
    dilated by 2 voxels (v1 cut C_a down to that neighbourhood first, so a concavity covering the whole candidate
    'agreed' with any R); centroid and principal axis are those of the whole components, >= 50 % of R must lie in them
    dilated by one voxel AND >= 50 % of them must lie in R dilated by one voxel (reverse share). The (a, b) test is
    two-way in the same way."""
    g = ev.grid
    rep = dict(a=dict(present=False), b=dict(present=False), ab=None)
    Rm = np.zeros(g.size, bool); Rm[R] = True
    CR = g.centres(R)
    near = dilate(g, R, 2)
    Rd1 = dilate(g, R, 1)
    if gen is not None and gen.get('C_a') is not None and gen.get('survived', True):
        Ca = np.asarray(gen['C_a'], bool)
        Cn = touching_components(g, Ca, near)
        if len(Cn) >= K('min_testable'):
            CC = g.centres(Cn)
            dist = float(np.linalg.norm(CC.mean(0) - CR.mean(0)))
            ax_r = axes_of(CR)[1][0]; ax_a = axes_of(CC)[1][0]
            ang = float(np.degrees(np.arccos(min(1.0, abs(float(ax_r @ ax_a))))))
            Cd = dilate(g, Cn, 1)
            share = float(Cd[R].mean())
            rev = float(Rd1[Cn].mean())
            side = None
            if gen.get('side_resolved'):
                side = entry_open_share(Cn, d, ev) >= 0.5
            ok = (dist <= K('agree_dist_m') and ang <= K('agree_deg') and share >= K('agree_share') and
                  rev >= K('agree_share') and side is not False)
            rep['a'] = dict(present=True, agree=bool(ok), centroid_mm=round(dist * 1e3, 1), axis_deg=round(ang, 1),
                            share_in_Ca=round(share, 3), share_Ca_in_R=round(rev, 3), side_open=side,
                            side_tested=side is not None, voxels=int(len(Cn)),
                            cm3=round(len(Cn) * g.vox ** 3 * 1e6, 2), R_cm3=round(len(R) * g.vox ** 3 * 1e6, 2))
        else:
            rep['a'] = dict(present=False, reason='C_a has < 3 voxels near R')
    elif gen is not None:
        rep['a'] = dict(present=False, reason='gen notch lost in remesh' if gen.get('survived') is False else 'no C_a')
    if sil and sil.get('gate_ok'):
        cls = sil_classes(sil, R, g)
        testable = np.array([c is not None for c in cls])
        if testable.sum() >= K('min_testable'):
            share = float(np.mean([c == 'SIL' for c in cls[testable]]))
            rep['b'] = dict(present=True, agree=share >= K('agree_share'), sil_share=round(share, 3),
                            testable=int(testable.sum()))
        else:
            rep['b'] = dict(present=False, reason='fewer than 3 testable voxels')
    elif sil is not None:
        rep['b'] = dict(present=False, reason='silhouette gate failed' if not sil.get('gate_ok') else 'absent')
    if rep['a']['present'] and N_b is not None and len(N_b):
        Nb = np.zeros(g.size, bool); Nb[N_b] = True
        Rb = touching_components(g, Nb, near)
        if len(Rb) == 0:
            Rb = np.nonzero(Nb)[0]
        Ca_t = touching_components(g, np.asarray(gen['C_a'], bool), dilate(g, Rb, 2))
        if len(Ca_t) == 0:
            rep['ab'] = dict(agree=False, share=0.0, reverse=0.0)
        else:
            s1 = float(dilate(g, Ca_t, 1)[Rb].mean())
            s2 = float(dilate(g, Rb, 1)[Ca_t].mean())
            rep['ab'] = dict(agree=bool(s1 >= K('agree_share') and s2 >= K('agree_share')), share=round(s1, 3),
                             reverse=round(s2, 3))
    return rep


def tier_of(decision, rep, offset_ab=None):
    """3.4 tiers from the decision and the agreement report. offset_ab: (a, b) agreement on the notch N for T2o."""
    a, b = rep['a'], rep['b']
    a_dis = a.get('present') and not a.get('agree')
    b_dis = b.get('present') and not b.get('agree')
    ab_dis = rep.get('ab') is not None and not rep['ab']['agree']
    disagree = a_dis or b_dis or ab_dis
    if decision == 'OFFSET':
        return ('T2o' if offset_ab else 'T1'), disagree
    if decision != 'CARVE':
        return 'T0', disagree
    if disagree:
        return 'T1', True
    if a.get('present') and b.get('present'):
        return 'T3', False
    if a.get('present') or b.get('present'):
        return 'T2', False
    return 'T1', False


# ------------------------------------------------------------------------------------------------ the decision
@dataclasses.dataclass
class Side:
    """Everything decide_pair needs about one target of the pair."""
    name: str
    ev: Evidence
    intr: Intrusions
    comps: list
    runs: list
    sil: dict = None                 # silhouette votes on the 4 mm grid (gmg.silhouette.votes)
    gen: dict = None                 # placed generator concavity (gmg.gen_slot.concavity)
    notches: list = None             # observed notches N (lists of 4 mm voxel indices) for OFFSET: SIL + GEN
    notches_sil: list = None         # the silhouette's notches N_b (for the (a, b) cross-check)
    track_ok: bool = True
    track_reason: str = ''
    partner_collider: np.ndarray = None   # partner's collider volume samples in the PARTNER frame (round 0: its pick)
    carved_cm3_before: float = 0.0   # earlier rounds' carves (cumulative budget, F-I1.3 (iv); F-I3.3)
    fh: FrameHits = None
    solid_ref_cm3: float = None      # the budget's base: the ROUND-0 solid volume (F-I3.3), else ev.solid_cm3()
    carved_now_cm3: float = 0.0      # carves accepted for this target in this call (running total)
    gate: dict = None                # identity / track gate record (make_side)


def _budget(side, ev, sol, d, applies=True):
    """F-I1.3 (iv) for one carve solid of SIDE (CARVE or OFFSET, F-I3.4): cumulative volume over rounds and over the
    components of this call <= 10 % of the round-0 solid (F-I3.3), reach <= 0.6 of the extent along d, and the
    topology of the carved sub-voxels kept. applies=False (an R_U-only carve, F-I2.6): topology only."""
    Cs = ev.sgrid.centres(sol['sub_lin']) if len(sol['sub_lin']) else np.zeros((0, 3))
    ext_d = ev.extent_along(d)
    reach = float((Cs @ d).max() - (Cs @ d).min() + ev.sgrid.vox) / max(ext_d, 1e-9) if len(Cs) else 0.0
    base = side.solid_ref_cm3 if side.solid_ref_cm3 else ev.solid_cm3()
    vol_share = (side.carved_cm3_before + side.carved_now_cm3 + sol['cm3']) / max(base, 1e-9)
    okt, tinfo = topology_kept(ev, sol['sub_lin'], sub=True)
    ok = bool(okt and (not applies or (vol_share <= K('budget_vol') and reach <= K('budget_reach'))))
    return dict(carve_cm3=round(sol['cm3'], 2), vol_share=round(vol_share, 4), reach=round(reach, 3), topology=tinfo,
                applies=bool(applies), ok=ok, base_cm3=round(base, 2),
                carved_before_cm3=round(side.carved_cm3_before + side.carved_now_cm3, 2),
                note='(iv) applies to R_O and OFFSET carves; an R_U-only carve has the topology guard only')


def _comp_frame(comp, ev, side=None):
    """(centroid, (d, n, m)) of a component: d = the insertion direction; n = the across direction. 3.5 defines n
    as the component's thinnest principal axis perpendicular to d (PREREG F-I2.2, T-I1 fix): n is the direction perpendicular to d in which the partner's
    evidence near the crossing (inside the target candidate dilated by 2 voxels, at the median assembled pose) is
    thinnest, i.e. the partner plate's normal; the component's own thinnest axis equals min(target thickness, partner
    thickness) and picked the target's thickness whenever the target is the thinner plate. Fallback (fewer than 20
    partner samples, or export input without full partner samples): the component's thinnest axis."""
    C = ev.grid.centres(comp.lin)
    c, A, s = axes_of(C, comp.run.d)
    if side is not None and side.intr.Xp is not None:
        T = _asm_pose(side.intr, comp.run)
        X = side.intr.Xp @ T[:3, :3].T + T[:3, 3]
        D = ndimage.binary_dilation(ev.occ.reshape(ev.grid.shape), structure=np.ones((3, 3, 3)), iterations=2).ravel()
        l, ok = ev.grid.lin(X)
        k = np.zeros(len(X), bool); k[ok] = D[l[ok]]
        if k.sum() >= 20:
            _, A2, s2 = axes_of(X[k], comp.run.d)
            d, n, m = A2
            return c, np.stack([d, n, m])
    return c, A


def _orphans(ev, remove_lin, R_lin):
    """Candidate voxels that the removal cuts off from the largest remaining component, hold no OBSERVED voxel and
    lie inside the convex hull of the region R (4 mm grid)."""
    from scipy.spatial import Delaunay
    g = ev.grid
    occ = ev.occ.copy(); occ[np.asarray(remove_lin, np.int64)] = False
    lab, n = ndimage.label(occ.reshape(g.shape), structure=np.ones((3, 3, 3)))
    lab = lab.ravel()
    if n < 2:
        return np.zeros(0, np.int64)
    sizes = np.bincount(lab)[1:]
    big = int(np.argmax(sizes)) + 1
    CR = g.centres(R_lin)
    try:
        hull = Delaunay(CR)
    except Exception:
        return np.zeros(0, np.int64)
    out = []
    for k in range(1, n + 1):
        if k == big:
            continue
        l = np.nonzero(lab == k)[0]
        if (ev.state[l] == STATE_OBSERVED).any():
            continue
        if (hull.find_simplex(g.centres(l)) >= 0).mean() >= 0.5:
            out.append(l)
    return np.concatenate(out) if out else np.zeros(0, np.int64)


def decide_component(comp, side, b, poses, R_lin, report):
    """F-I1.3 steps 1-4 for one component R (after the split). Returns (decision, reasons dict)."""
    ev = side.ev
    g = ev.grid
    reasons = report
    run = comp.run
    if run.kind == 'TRANSIENT' or len(R_lin) < 3:
        reasons['step'] = 1
        return 'IGNORE', reasons
    st = ev.state[R_lin]
    silc = sil_classes(side.sil, R_lin, g)
    U = (st != STATE_OBSERVED)
    obs = ~U
    sil_v = obs & (silc == 'SIL')
    solid_v = obs & (silc == 'SOLID')
    absent_v = obs & np.array([c is None for c in silc])
    # GAP: OBSERVED, silhouette absent, image width <= w_bridge, topology kept on removal
    gap_v = np.zeros(len(R_lin), bool)
    if absent_v.any():
        wpx, winfo = image_width(R_lin, b, side.name, g, b.good_frames(side.name), poses=None, fh=side.fh)
        reasons['image_width_px'] = None if wpx is None else round(wpx, 2)
        reasons['image_width_info'] = winfo
        if wpx is not None and wpx <= K('w_bridge_px'):
            okt, tinfo = topology_kept(ev, R_lin[absent_v])
            reasons['gap_topology'] = tinfo
            if okt:
                gap_v = absent_v
    o_v = obs & ~sil_v & ~gap_v
    n = len(R_lin)
    mix = dict(U=int(U.sum()), SIL=int(sil_v.sum()), GAP=int(gap_v.sum()), O=int(o_v.sum()),
               O_testable_solid=int(solid_v.sum()))
    reasons['class_mix'] = mix
    reasons['class_o_share'] = round(float(o_v.mean()), 3)
    if o_v.mean() > K('class_o_max'):
        reasons['step'] = 2
        reasons['why'] = 'more than 25 % of R is class O (seen solid): the pose is wrong, not the shape'
        return 'PUSH', reasons
    carve = np.zeros(n, bool)
    # step 3: R_U
    if U.any():
        okt, tinfo = topology_kept(ev, R_lin[U])
        if not okt:
            # F-I2.4 (T-I1 fix): the partner's evidence is its observed surface, so a hollow region can cut off
            # unseen candidate material inside the partner (a cup's core); candidate components split off by the
            # carve that hold no OBSERVED voxel and lie inside the convex hull of R are removed with R
            orphan = _orphans(ev, R_lin[U], R_lin)
            if len(orphan):
                okt2, tinfo2 = topology_kept(ev, np.concatenate([R_lin[U], orphan]))
                reasons['ru_orphans'] = dict(voxels=int(len(orphan)), topology=tinfo2)
                if okt2:
                    okt, tinfo = True, tinfo2
                    reasons['_orphan_lin'] = orphan
        reasons['ru_topology'] = tinfo
        if okt:
            carve |= U
        else:
            reasons['ru'] = 'PUSH (topology guard)'
    # step 4: R_O
    RO = obs
    if RO.any():
        sw = comp.swept[np.isin(comp.lin, R_lin)] if comp.carve_lin is not None else comp.swept
        sw_map = dict(zip(comp.lin.tolist(), comp.swept.tolist()))
        swept = np.array([sw_map.get(int(v), False) for v in R_lin[RO]])
        i_ok = (swept.mean() >= K('swept_share')) and run.kind in ('INSERTION', 'SLIDE')
        frames_R = [f for f in run.build if np.isin(side.intr.entered(f), R_lin).any()]
        normal = _comp_frame(comp, ev, side)[1][1]
        push_m, per = push_distance(side.intr, frames_R, R_lin, ev, normal=normal)
        ii_ok = push_m > K('push_prior_m')
        pr = side.intr.pushed_residual
        if pr:
            vals = [pr.get(f) for f in frames_R if pr.get(f) is not None and np.isfinite(pr.get(f))]
            if vals:
                band = float(b.band(side.name, side.intr.partner))
                ii_ok = float(np.mean([v > band for v in vals])) >= 0.5
                reasons['pushed_residual_used'] = dict(frames=len(vals), band_mm=round(band * 1e3, 2))
        iii_share = float((sil_v[RO] | gap_v[RO]).mean())
        iii_ok = iii_share >= K('silgap_share')
        reasons.update(swept_share=round(float(swept.mean()), 3), run_kind=run.kind, push_mm=round(push_m * 1e3, 1)
                       if np.isfinite(push_m) else 'inf', push_frames=len(frames_R),
                       silgap_share=round(iii_share, 3), i=bool(i_ok), ii=bool(ii_ok), iii=bool(iii_ok))
        if i_ok and ii_ok and iii_ok:
            carve |= (sil_v | gap_v)
            if U.any() and not carve[U].all():
                # U voxels rejected alone (an internal void) are carved with R_O when the union keeps the topology
                okt3, tinfo3 = topology_kept(ev, R_lin[carve | U])
                reasons['ru_with_ro_topology'] = tinfo3
                if okt3:
                    carve |= U
        else:
            if not ii_ok:
                reasons['ro'] = 'PUSH (a pose correction within the prior removes it)'
            else:
                reasons['ro'] = 'PUSH, interlock_unresolved (not pushable, but (i) or (iii) fails)'
                reasons.setdefault('flags', []).append('interlock_unresolved')
            if not (carve.any()):
                reasons['step'] = 4
                return 'PUSH', reasons
    reasons['step'] = 4 if RO.any() else 3
    drop = np.zeros(n, bool)
    if carve.any() and o_v.any() and run.kind in ('INSERTION', 'SLIDE'):
        # F-I3.12 column rule: a partner that passes through a plate fills the plate's thickness (the carve frame's
        # m axis); a voxel whose column along m holds a class-O voxel of R cannot be used by it, so carving it only
        # makes a pocket under a seen face (round-1 review: o2sil, offset_asm). Such voxels are not carved and are
        # kept out of the carve solid's footprint.
        A3 = _comp_frame(comp, ev, side)[1]
        C = g.centres(R_lin)
        key = np.stack([np.round(C @ A3[0] / g.vox), np.round(C @ A3[1] / g.vox)], 1).astype(np.int64)
        okey = {tuple(k) for k in key[o_v]}
        blocked = np.array([tuple(k) in okey for k in key])
        drop = carve & blocked
        carve = carve & ~blocked
        if drop.any():
            reasons['pocket_dropped_voxels'] = int(drop.sum())
        if not carve.any():
            reasons['why'] = 'every carvable voxel lies in a column with a seen-solid voxel (F-I3.12)'
            return 'PUSH', reasons
    reasons['carve_voxels'] = int(carve.sum())
    reasons['_o_lin'] = np.concatenate([R_lin[o_v], R_lin[drop]])
    cl = R_lin[carve]
    if '_orphan_lin' in reasons:
        cl = np.concatenate([cl, reasons.pop('_orphan_lin')])
    reasons['_carve_lin'] = cl
    return 'CARVE', reasons


def offset(R_lin, d, ev, notches, ev_p=None, R_p=None, notches_p=None, T_op=None):
    """INTERLOCK 4.4: t on a 2 mm grid, |t| <= t_max, |t . d| <= 0.5 |t|, maximising the overlap of N + t with R
    (jointly with the partner's notch for a linked pair, t_p = -R_op^T t); holds if >= 50 % of R lies in (N + t)
    dilated by one voxel and N keeps the topology. Returns dict or None."""
    if not notches:
        return None
    g = ev.grid
    tmax, gs, lat = K('offset_tmax_m'), K('offset_grid_m'), K('offset_lateral')
    ax = np.arange(-tmax, tmax + 1e-9, gs)
    T = np.stack(np.meshgrid(ax, ax, ax, indexing='ij'), -1).reshape(-1, 3)
    nt = np.linalg.norm(T, axis=1)
    keep = (nt <= tmax + 1e-9) & (np.abs(T @ d) <= lat * nt + 1e-12)
    T = T[keep]
    Rm = np.zeros(g.size, bool); Rm[R_lin] = True
    CR = g.centres(R_lin)
    best = None
    for N in notches:
        N = np.asarray(N, np.int64)
        if len(N) < 3:
            continue
        CN = g.centres(N)
        if np.min(np.linalg.norm(CN[:, None, :] - CR[None, :, :], axis=2)) > tmax:
            continue
        S = (CN[:, None, :] + np.array([[a, bb, c] for a in (-1, 1) for bb in (-1, 1) for c in (-1, 1)])[None] *
             g.vox / 4).reshape(-1, 3)
        for t in T:
            l, ok = g.lin(S + t)
            sc = int(Rm[l[ok]].sum())
            if best is None or sc > best[0]:
                best = (sc, t, N)
    if best is None or best[0] == 0:
        return None
    sc, t, N = best
    l, ok = g.lin(g.centres(N) + t)
    moved = np.unique(l[ok])
    md = dilate(g, moved, 1)
    share = float(md[R_lin].mean())
    # F-I3.5: two-way, as in agree(): >= 50 % of N + t must also lie in R dilated by one voxel (a notch the size of
    # the region, not a concavity that covers it)
    rev = float(dilate(g, R_lin, 1)[moved].mean()) if len(moved) else 0.0
    okt, tinfo = topology_kept(ev, N)
    return dict(t_mm=np.round(t * 1e3, 1).tolist(), t_norm_mm=round(float(np.linalg.norm(t)) * 1e3, 1),
                t_along_d_mm=round(float(t @ d) * 1e3, 1), share_R_in_N_t=round(share, 3),
                share_N_t_in_R=round(rev, 3), holds=bool(share >= 0.5 and rev >= 0.5 and okt),
                topology=tinfo, N=N, N_moved=moved, o_displaced=int((ev.state[moved] == STATE_OBSERVED).sum()))


def crossing(ev_o, ev_p, T_op):
    """Crossing volume X (o's candidate intersected with p's at T_op = T_{o<-p}, dilated by one voxel), in both
    frames."""
    Xo = ev_o.occ & map_occ(ev_p, T_op, ev_o)
    Xp = ev_p.occ & map_occ(ev_o, np.linalg.inv(T_op), ev_p)
    Xo = dilate(ev_o.grid, np.nonzero(Xo)[0], 1)
    Xp = dilate(ev_p.grid, np.nonzero(Xp)[0], 1)
    return Xo, Xp


def _asm_pose(intr, run):
    fr = run.assembled if run.assembled else run.build
    return mean_pose([intr.rel[f] for f in fr])


def decide_pair(b, so, sp, poses_sim=None, round_k=0):
    """F-I1.3 for one pair (both ordered directions): components of so (o <- p) and sp (p <- o). Returns the list of
    decision records (one per component), each with the carve solids for the simulator copy (width w_sim) and, at
    T2/T3/T2o, for submitted candidates (width w_sub)."""
    if int(round_k) > K('max_rounds'):
        raise ValueError(f'round {round_k} > {K("max_rounds")} (F-I1.13)')
    out = []
    sides = {so.name: so, sp.name: sp}
    # linking at the median assembled pose (per run of o <- p)
    links = {}
    for co in so.comps:
        T_op = _asm_pose(so.intr, co.run)
        Xo, Xp = crossing(so.ev, sp.ev, T_op)
        for cp in sp.comps:
            if Xo[co.lin].mean() >= K('link_share') and Xp[cp.lin].mean() >= K('link_share'):
                links.setdefault(id(co), []).append(cp)
                links.setdefault(id(cp), []).append(co)
    # shared split plane per linked pair; own plane otherwise
    planes = {}
    for co in so.comps:
        if id(co) in links:
            cp = links[id(co)][0]
            T_op = _asm_pose(so.intr, co.run)
            Co = so.ev.grid.centres(co.lin)
            Cp = sp.ev.grid.centres(cp.lin) @ T_op[:3, :3].T + T_op[:3, 3]
            c = np.vstack([Co, Cp]).mean(0)
            d = co.run.d
            planes[id(co)] = (c, d, +1)                                 # o carves (x - c).d < 0
            Ti = np.linalg.inv(T_op)
            planes[id(cp)] = (Ti[:3, :3] @ c + Ti[:3, 3], Ti[:3, :3] @ d, -1)   # p carves (y - c').d' > 0
    for side in (so, sp):
        for comp in side.comps:
            if id(comp) not in planes:
                C = side.ev.grid.centres(comp.lin)
                planes[id(comp)] = (C.mean(0), comp.run.d, +1)
            thr, tinfo = through_column(comp.lin, comp.run.d, side.ev)
            c, dd, sign = planes[id(comp)]
            comp.split = dict(through_column=bool(thr), **tinfo)
            if thr:
                C = side.ev.grid.centres(comp.lin)
                s = (C - c) @ dd
                keep = (s < 0) if sign > 0 else (s > 0)
                comp.carve_lin = comp.lin[keep]
                comp.split.update(plane_point=np.round(c, 5).tolist(), plane_normal=np.round(dd, 4).tolist(),
                                  carve_side='entry (s < 0)' if sign > 0 else 'entry of the partner pair (s > 0)',
                                  shared=id(comp) in links, kept_voxels=int((~keep).sum()),
                                  carved_side_voxels=int(keep.sum()))
            else:
                comp.carve_lin = comp.lin
    # per component decision
    recs = {}
    for side in (so, sp):
        for comp in side.comps:
            R = comp.region()
            rep = dict(target=side.name, partner=comp.partner, run=comp.run.summary(), voxels=int(len(comp.lin)),
                       region_voxels=int(len(R)), cm3=round(len(R) * side.ev.grid.vox ** 3 * 1e6, 2),
                       nmin=comp.nmin, split=comp.split, linked=id(comp) in links, flags=[], _comp=comp)
            if not side.track_ok:
                rep['flags'].append('c_absent_track:' + side.track_reason)
                dec = 'IGNORE'
            else:
                dec, rep = decide_component(comp, side, b, poses_sim, R, rep)
            rep['decision'] = dec
            recs[id(comp)] = (side, comp, rep)
    # widths, solids and the budget (iv) for every component that carves on its own
    for key, (side, comp, rep) in recs.items():
        ev = side.ev
        R = comp.region()
        c3, A = _comp_frame(comp, ev, side)
        d, n, m = A
        T_op = _asm_pose(side.intr, comp.run)
        # w_sim: entering samples (assembled build frames) across n, and the partner collider thickness
        fr_asm = [f for f in (comp.run.assembled or comp.run.build) if f in comp.run.build] or comp.run.build
        selr = np.isin(side.intr.frame, fr_asm) & np.isin(side.intr.lin, R)
        Pn = side.intr.pts[selr] @ n
        w_samp = float(np.percentile(Pn, 99) - np.percentile(Pn, 1)) if len(Pn) >= 10 else 0.0
        cen_n = float(0.5 * (np.percentile(Pn, 99) + np.percentile(Pn, 1))) if len(Pn) >= 10 else float(c3 @ n)
        w_col = None
        if side.partner_collider is not None and len(side.partner_collider):
            Xc = side.partner_collider @ T_op[:3, :3].T + T_op[:3, 3]
            pt = partner_thickness(Xc, n, ev)
            if pt is not None:
                w_col = pt[0]
        w_sim = max(w_samp, w_col or 0.0) + 2 * K('clearance_m')
        # w_sub: the partner's evidence thickness at the crossing (its OBSERVED samples), capped at w_sim
        Xe = partner_points(b, comp.partner) @ T_op[:3, :3].T + T_op[:3, 3]
        pe = partner_thickness(Xe, n, ev)
        w_sub = min(pe[0], w_sim) if pe is not None else min(w_col or w_sim, w_sim)
        rep['widths'] = dict(w_sim_mm=round(w_sim * 1e3, 2), entering_samples_mm=round(w_samp * 1e3, 2),
                             partner_collider_mm=None if w_col is None else round(w_col * 1e3, 2),
                             w_sub_mm=round(w_sub * 1e3, 2), centre_n_mm=round(cen_n * 1e3, 2),
                             axes_dnm=np.round(A, 4).tolist())
        rep['_frame3'] = A; rep['_cen_n'] = cen_n
        if rep['decision'] == 'CARVE':
            cl = rep.pop('_carve_lin')
            o_lin = rep.get('_o_lin')
            sol = carve_solid(ev, cl, A, cen_n, w_sim, plate=comp.run.kind in ('INSERTION', 'SLIDE'),
                              exclude_lin=o_lin)
            rep['_sim_solid'] = sol
            rep['_carve_lin_kept'] = cl
            has_ro = (rep.get('class_mix', {}).get('SIL', 0) + rep.get('class_mix', {}).get('GAP', 0)) > 0
            bud = _budget(side, ev, sol, d, applies=bool(has_ro))
            rep['budget'] = bud
            if not bud['ok']:
                rep['decision'] = 'PUSH'
                rep['flags'].append('interlock_partner_too_thick' if (w_col and w_col + 2 * K('clearance_m') >= w_sim
                                                                      and bud['vol_share'] > K('budget_vol'))
                                    else 'budget_iv_fail')
                rep.pop('_sim_solid', None)
            else:
                side.carved_now_cm3 += sol['cm3']
        rep['own_decision'] = rep['decision']
    # OFFSET for class-O pushes (4.4)
    offs = {}
    for key, (side, comp, rep) in recs.items():
        ev = side.ev
        R = comp.region()
        A = rep['_frame3']; d = A[0]
        rep['sources'] = agree(R, d, ev, gen=side.gen, sil=side.sil,
                               N_b=np.concatenate(side.notches_sil) if side.notches_sil else None)
        if rep['decision'] == 'PUSH' and rep.get('step') == 2:
            off = offset(R, d, ev, side.notches or [])
            if off is not None:
                if off['holds']:
                    # F-I3.4: N + t is a carve like any other: budget (iv) (cumulative), reach and the topology of the
                    # carved sub-voxels at w_sim, before the pair level decides
                    w = float(rep['widths']['w_sim_mm']) * 1e-3
                    sol = carve_solid(ev, off['N_moved'], A, rep['_cen_n'], w, plate=False)
                    bud = _budget(side, ev, sol, d, applies=True)
                    off['budget'] = bud
                    if bud['ok']:
                        off['_sim_solid'] = sol
                    else:
                        off['holds'] = False
                        off['why_not'] = 'budget_iv_fail (N + t)'
                offs[key] = off
                rep['offset'] = {k: v for k, v in off.items() if k not in ('N', 'N_moved', '_sim_solid')}
    # pair level (4.3): a linked pair carves only if each side either carves on its own or has a holding OFFSET (both
    # OFFSET: one relative offset, t_p = -R^T t_o within two grid steps); otherwise both PUSH (interlock_pair_fail)
    def status(k):
        r = recs[k][2]
        if r['decision'] == 'CARVE':
            return 'CARVE'
        if k in offs and offs[k]['holds']:
            return 'OFFSET'
        return r['decision']
    done = set()
    for key, (side, comp, rep) in recs.items():
        if key in done or key not in links:
            continue
        group = [key] + [id(c) for c in links[key]]
        done |= set(group)
        st = {k: status(k) for k in group}
        ok = all(v in ('CARVE', 'OFFSET') for v in st.values())
        offk = [k for k in group if st[k] == 'OFFSET']
        if ok and len(offk) == 2:
            k0, k1 = offk
            s0 = recs[k0][0]
            T01 = _asm_pose(s0.intr, recs[k0][1].run)
            t0_ = np.asarray(offs[k0]['t_mm']) * 1e-3; t1_ = np.asarray(offs[k1]['t_mm']) * 1e-3
            mism = float(np.linalg.norm(t1_ + T01[:3, :3].T @ t0_))
            recs[k0][2]['offset']['pair_mismatch_mm'] = round(mism * 1e3, 1)
            if mism > 2 * K('offset_grid_m'):
                ok = False
        if not ok:
            for k in group:
                r = recs[k][2]
                if st[k] in ('CARVE', 'OFFSET'):
                    r['flags'].append('interlock_pair_fail')
                if r['decision'] == 'CARVE':
                    r['decision'] = 'PUSH'; r.pop('_sim_solid', None)
                if k in offs:
                    offs[k]['holds'] = False
                    r.setdefault('offset', {})['pair'] = 'the linked partner neither carves nor has an OFFSET: both PUSH'
        rep['pair_status'] = {recs[k][2]['target']: st[k] for k in group}
    for key, (side, comp, rep) in recs.items():
        ev = side.ev
        A = rep['_frame3']
        ag = rep['sources']
        off = offs.get(key)
        if off is not None and off['holds'] and rep['decision'] == 'PUSH':
            rep['decision'] = 'OFFSET'
            rep['_sim_solid'] = off['_sim_solid']
            rep['budget'] = off['budget']
            side.carved_now_cm3 += off['_sim_solid']['cm3']
            rep['o_displaced'] = off['o_displaced']
            rep['flags'].append('o_displaced')
            rep['push_list'] = dict(kind='OFFSET', t_mm=off['t_mm'], frames=[comp.run.frames[0], comp.run.frames[-1]],
                                    hypothesis='partner offset t in the target frame over these frames')
        elif rep['decision'] == 'PUSH':
            rep['push_list'] = dict(kind='PUSH', frames=[comp.run.frames[0], comp.run.frames[-1]],
                                    push_mm=rep.get('push_mm'), why=rep.get('why') or rep.get('ro'))
        elif rep['decision'] == 'CARVE' and rep.get('_o_lin') is not None and len(rep['_o_lin']):
            # F-I3.6: the class-O voxels of a carved region are never carved (F-I1.3); the intrusion left there is a
            # pose error and goes to the push list next to the carve
            rep['flags'].append('o_residual_push')
            rep['push_list'] = dict(kind='PUSH_RESIDUAL', frames=[comp.run.frames[0], comp.run.frames[-1]],
                                    o_voxels=int(len(rep['_o_lin'])),
                                    why='class-O voxels of a carved region (seen solid): pose correction, not carve')
        offset_ab = bool(off is not None and off['holds'] and ag['a'].get('present') and ag['b'].get('present') and
                         (ag.get('ab') or {}).get('agree') and comp.run.kind in ('INSERTION', 'SEAT'))
        tier, dis = tier_of(rep['decision'], ag, offset_ab=offset_ab)
        rep['tier'] = tier
        if dis:
            rep['flags'].append('interlock_disagree')
        if rep['decision'] == 'PUSH':
            rep['flags'].append('interlock_push')
        rep['submitted'] = tier in ('T2', 'T3', 'T2o') and not dis
        if rep['submitted']:
            w = float(rep['widths']['w_sub_mm']) * 1e-3
            if tier == 'T2o':
                lin_sub = np.asarray(off['N'], np.int64)
                o_sub = _o_class(side, lin_sub)
            else:
                lin_sub = rep.get('_carve_lin_kept', comp.region())
                o_sub = rep.get('_o_lin')
            # F-I3.2 (B4): the submitted solid excludes the class-O voxels exactly as the simulator solid does
            rep['_sub_solid'] = carve_solid(ev, lin_sub, A, rep['_cen_n'], w,
                                            plate=comp.run.kind in ('INSERTION', 'SLIDE'), exclude_lin=o_sub)
            if not len(rep['_sub_solid']['sub_lin']):
                rep['submitted'] = False
                rep['flags'].append('submitted_solid_empty')
                rep.pop('_sub_solid')
        rep['sim_carve'] = rep['decision'] in ('CARVE', 'OFFSET') and '_sim_solid' in rep
        rep['round'] = int(round_k)
        out.append(rep)
    # F-I3.7: a region on one side only (the partner side has none) is flagged; with a sparse partner evidence the
    # partner's half-slot cannot be decided
    names = {so.name: bool(so.comps), sp.name: bool(sp.comps)}
    if names[so.name] != names[sp.name]:
        for r in out:
            r['flags'].append('one_sided_region')
    return out


def _o_class(side, lin):
    """Class-O voxels of LIN outside a component decision (OFFSET notch N): OBSERVED and not see-through (SIL)."""
    lin = np.asarray(lin, np.int64)
    if not len(lin):
        return lin
    silc = sil_classes(side.sil, lin, side.ev.grid)
    o = (side.ev.state[lin] == STATE_OBSERVED) & (silc != 'SIL')
    return lin[o]


def public(rec):
    """A decision record without its private arrays (for JSON)."""
    r = {k: v for k, v in rec.items() if not k.startswith('_')}
    for k in ('_sim_solid', '_sub_solid'):
        if k in rec:
            s = rec[k]
            r[k[1:]] = {kk: vv for kk, vv in s.items() if kk != 'sub_lin'}
    return json.loads(json.dumps(r, default=_jdefault))


def _jdefault(o):
    if isinstance(o, np.ndarray):
        return o.tolist()
    if isinstance(o, (np.integer,)):
        return int(o)
    if isinstance(o, (np.floating,)):
        return float(o)
    if isinstance(o, (np.bool_,)):
        return bool(o)
    raise TypeError(type(o))


# ------------------------------------------------------------------------------------------------ contract (11)
def _sha(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for blk in iter(lambda: f.read(1 << 20), b''):
            h.update(blk)
    return h.hexdigest()


def _man_objects(man):
    """Object names of a delivered manifest: `objects` is a list (gmg-sim/1 as delivered on 31 Oct) or the dict
    objects.<obj>.{files, fiducials} (F-I3.9, the layout the Embodiment reader expects)."""
    objs = man.get('objects') or []
    if isinstance(objs, dict):
        return list(man.get('object_order') or objs.keys())
    return [o if isinstance(o, str) else o.get('name') for o in objs]


def man_piece_files(man, o):
    """{basename: sha256} of the collision pieces piece_*.obj of object O in a delivered manifest (either layout)."""
    objs = man.get('objects')
    if isinstance(objs, dict) and isinstance(objs.get(o), dict) and objs[o].get('files'):
        fs = {os.path.basename(k): v for k, v in objs[o]['files'].items()}
    else:
        fs = {k.split('/', 1)[1]: v for k, v in (man.get('files') or {}).items() if k.startswith(o + '/')}
    return {k: v for k, v in fs.items() if k.startswith('piece_') and k.endswith('.obj')}


def man_fiducials(man, o):
    objs = man.get('objects')
    if isinstance(objs, dict) and isinstance(objs.get(o), dict) and objs[o].get('fiducials') is not None:
        return np.asarray(objs[o]['fiducials'], np.float64).reshape(8, 3)
    return np.asarray((man.get('fiducials') or {})[o], np.float64).reshape(8, 3)


def load_sim(sim_dir, episode=None, allow_do_not_use=False):
    """A delivered round (6.1 layout). Refused (ValueError) when the manifest names another episode (6.4), a file's
    sha256 differs from the manifest, or the folder is marked do-not-use (F-I3.8: a DO_NOT_USE.json next to the
    manifest or manifest['do_not_use']; diagnostics may pass allow_do_not_use=True). Returns dict(manifest, pieces
    {obj: [vertex arrays]}, fit {obj: mesh}, objects [names])."""
    import trimesh
    with open(os.path.join(sim_dir, 'manifest.json')) as fh:
        man = json.load(fh)
    if episode is not None and int(man['episode']) != int(episode):
        raise ValueError(f'load_sim: {sim_dir} is episode {man["episode"]}, not {episode} (one folder per episode)')
    dnu = os.path.join(sim_dir, 'DO_NOT_USE.json')
    if (man.get('do_not_use') or os.path.exists(dnu)) and not allow_do_not_use:
        why = man.get('do_not_use') or json.load(open(dnu))
        raise ValueError(f'load_sim: {sim_dir} is marked do-not-use: {why}')
    for rel, sha in man['files'].items():
        if _sha(os.path.join(sim_dir, rel)) != sha:
            raise ValueError(f'load_sim: {rel} changed since delivery')
    pieces, fit = {}, {}
    objs = _man_objects(man)
    for o in objs:
        fs = sorted(man_piece_files(man, o))
        on_disk = sorted(f for f in os.listdir(os.path.join(sim_dir, o)) if f.startswith('piece_') and f.endswith('.obj'))
        if fs != on_disk:
            raise ValueError(f'load_sim: {o} piece files on disk {on_disk} differ from the manifest {fs}')
        pieces[o] = [np.asarray(trimesh.load(os.path.join(sim_dir, o, f), force='mesh').vertices) for f in fs]
        fit[o] = trimesh.load(os.path.join(sim_dir, '_fit', f'{o}.glb'), force='mesh')
    return dict(manifest=man, pieces=pieces, fit=fit, objects=objs)


def _union_grid(hulls, pitch):
    from gmg.simpieces import grid_points, inside_any
    P = np.vstack(hulls)
    G = grid_points(P.min(0) - pitch, P.max(0) + pitch, pitch)
    return G[inside_any(hulls, G)]


# ------------------------------------------------------------------------------------------------ sources (F-I3.1)
def write_sources(folder, obj, sil=None, gen=None, notches=None, notches_sil=None, grid=None):
    """Sources (a) and (b) of one target as computed by the gmg from OUR evidence (video, generator mesh), saved next to
    a delivered round (`<round>/sources/<obj>.npz`) so carve_from_intrusions decides with the same inputs as the
    tracks path (F-I3.1). Arrays only (no pickles)."""
    os.makedirs(folder, exist_ok=True)
    arr = {}
    if grid is not None:
        arr.update(grid_lo=np.asarray(grid.lo), grid_vox=np.float64(grid.vox), grid_shape=np.asarray(grid.shape))
    if sil:
        arr['sil_gate_ok'] = np.bool_(bool(sil.get('gate_ok')))
        for k in ('nmv', 'nmf', 'nmv_sub', 'nmf_sub'):
            if sil.get(k) is not None:
                arr['sil_' + k] = np.asarray(sil[k], np.int32)
    if gen and gen.get('C_a') is not None:
        arr['gen_C_a'] = np.asarray(gen['C_a'], bool)
        arr['gen_survived'] = np.bool_(bool(gen.get('survived', True)))
        arr['gen_side_resolved'] = np.bool_(bool(gen.get('side_resolved')))
    for key, ns in (('notches', notches), ('notches_sil', notches_sil)):
        ns = [np.asarray(n, np.int64) for n in (ns or [])]
        arr[key + '_lin'] = np.concatenate(ns) if ns else np.zeros(0, np.int64)
        arr[key + '_len'] = np.asarray([len(n) for n in ns], np.int64)
    path = os.path.join(folder, f'{obj}.npz')
    np.savez_compressed(path, **arr)
    return path


def load_sources(folder, obj, grid=None):
    """The dict make_side takes (sil, gen, notches, notches_sil) from write_sources' file, or {} if absent. Refused
    (ValueError) if its grid differs from GRID (the target's bundle grid)."""
    path = os.path.join(folder, f'{obj}.npz')
    if not os.path.exists(path):
        return {}
    z = dict(np.load(path, allow_pickle=False))
    if grid is not None and 'grid_shape' in z:
        if tuple(int(x) for x in z['grid_shape']) != tuple(grid.shape) or not np.allclose(z['grid_lo'], grid.lo) or \
                abs(float(z['grid_vox']) - grid.vox) > 1e-9:
            raise ValueError(f'load_sources: {path} is on another grid than the bundle of {obj}')
    out = {}
    if 'sil_gate_ok' in z:
        out['sil'] = dict(gate_ok=bool(z['sil_gate_ok']), **{k: z['sil_' + k] for k in ('nmv', 'nmf', 'nmv_sub',
                                                                                          'nmf_sub')
                                                              if 'sil_' + k in z})
    if 'gen_C_a' in z:
        out['gen'] = dict(C_a=z['gen_C_a'].astype(bool), survived=bool(z['gen_survived']),
                          side_resolved=bool(z['gen_side_resolved']))
    for key in ('notches', 'notches_sil'):
        L = z.get(key + '_len', np.zeros(0, np.int64))
        flat = z.get(key + '_lin', np.zeros(0, np.int64))
        out[key] = list(np.split(flat, np.cumsum(L)[:-1])) if len(L) else []
    return out


def make_side(b, t, q, ev_t, intr, contact_frames, sources=None, identity='public', partner_collider=None, fh=None,
              holdout=None, carved_before=0.0, solid_ref_cm3=None):
    """One target (t <- q) of a pair, built the SAME way on our tracks and on an Embodiment export (F-I3.1): engaged
    runs (with the fixed hold-out of earlier rounds), persistent regions, the identity / track gate of F-I1.2 (public:
    TRACK_FAIL or IDENTITY_SWAP makes (c) absent; eval: IDENTITY_SWAP only flags), sources (a) and (b) and the
    observed notches from SOURCES (write_sources / load_sources or the driver's in-memory dicts)."""
    runs = engaged_runs(intr, contact_frames, int(b.meta['stride']), holdout=holdout)
    j = float(b.contact(t, q).get('j_mm') or 0) * 1e-3
    comps = []
    for r in runs:
        comps += regions(intr, r, ev_t, j)[0]
    good = set(b.good_frames(t)) & set(b.good_frames(q))
    okfr = [len([f for f in r.frames if f in good]) / max(len(r.frames), 1) for r in runs]
    san = b.meta.get('sanity') or {}
    sflags = sorted(set((san.get(t) or {}).get('flags', []) or []) | set((san.get(q) or {}).get('flags', []) or []))
    failing = ('TRACK_FAIL', 'IDENTITY_SWAP') if identity == 'public' else ('TRACK_FAIL',)
    track_ok = all(x >= 0.8 for x in okfr) and not any(f in failing for f in sflags)
    src = sources or {}
    return Side(t, ev_t, intr, comps, runs, sil=src.get('sil'), gen=src.get('gen'),
                notches=list(src.get('notches') or []), notches_sil=list(src.get('notches_sil') or []),
                track_ok=track_ok, track_reason=f'good share {np.round(okfr, 2).tolist()} flags {sflags} identity '
                                                f'{identity}',
                partner_collider=partner_collider, fh=fh or FrameHits(b, t, ev_t.grid),
                carved_cm3_before=float(carved_before or 0.0), solid_ref_cm3=solid_ref_cm3,
                gate=dict(good_share=[round(x, 3) for x in okfr], flags=sflags, identity=identity, track_ok=track_ok))


# ------------------------------------------------------------------------------------------------ export (11.2)
def write_export(path, b, sim_dir, pair, reference, poses=None, frames=None, pitch=0.002, shift_fiducials=0.0,
                 fit=None, pushed=None, f_star=None):
    """Reference writer of the export `gmg-intrusion/2` in the header layout of the Embodiment tool
    (tools/intrusion.py, determined-wright 759032e): meshes {obj: {basename: sha256}}, `frames` (T), `fiducials_file`,
    `f_star`, `fiducials_world`, `fiducials_back`, `reference`, `fit`, `pose_source`. Partner solid samples = 2 mm grid
    points inside the union of the partner's delivered pieces; pts_local in the target's file coordinates (rel_T =
    T_{target<-partner} from POSES, default our tracks). shift_fiducials: test hook (a geom-frame mistake)."""
    from gmg.simpieces import inside_any
    sim = load_sim(sim_dir)
    man = sim['manifest']
    poses = b.poses if poses is None else poses
    objs = list(pair)
    frames = list(frames) if frames is not None else sorted(set(b.contact(objs[0], objs[1])['contact']))
    S = {o: _union_grid(sim['pieces'][o], pitch) for o in objs}
    from gmg import geom as G_
    rows = dict(frame=[], target=[], partner=[], pts_local=[], depth_m=[])
    fp = dict(fp_frame=[], fp_target=[], fp_partner=[], rel_T=[], pushed_residual_m=[], intr_vol_m3=[])
    for ti, t in enumerate(objs):
        cl = G_.Closest(sim['fit'][t])
        for qi, q in enumerate(objs):
            if q == t:
                continue
            for f in frames:
                T = rel_pose(poses, t, q, f)
                X = S[q] @ T[:3, :3].T + T[:3, 3]
                k = inside_any(sim['pieces'][t], X)
                n = int(k.sum())
                if n:
                    rows['frame'].append(np.full(n, f, np.int32)); rows['target'].append(np.full(n, ti, np.int16))
                    rows['partner'].append(np.full(n, qi, np.int16)); rows['pts_local'].append(X[k].astype(np.float32))
                    rows['depth_m'].append(cl.query(X[k])[0].astype(np.float32))
                fp['fp_frame'].append(f); fp['fp_target'].append(ti); fp['fp_partner'].append(qi); fp['rel_T'].append(T)
                fp['pushed_residual_m'].append(np.nan if pushed is None else pushed.get((t, q, f), np.nan))
                fp['intr_vol_m3'].append(n * pitch ** 3)
    cat = {k: (np.concatenate(v) if v else np.zeros((0, 3) if k == 'pts_local' else 0)) for k, v in rows.items()}
    f_star = frames[len(frames) // 2] if f_star is None else int(f_star)
    fw, fb, ff = {}, {}, {}
    for o in objs:
        F = man_fiducials(man, o)
        Wo = (poses['world_T_cam'][f_star].astype(np.float64) @ poses[f'cam_T_{o}'][f_star].astype(np.float64))
        Xw = F @ Wo[:3, :3].T + Wo[:3, 3] + shift_fiducials
        fw[o] = Xw.tolist()
        Wi = np.linalg.inv(Wo)
        fb[o] = (Xw @ Wi[:3, :3].T + Wi[:3, 3]).tolist()
        ff[o] = F.tolist()
    np.savez_compressed(path, **cat, **{k: np.asarray(v) for k, v in fp.items()})
    hdr = dict(schema=SCHEMA_INTR, objects=objs, round=int(man['round']), sim_dir=os.path.abspath(sim_dir),
               meshes={o: dict(man_piece_files(man, o)) for o in objs}, pitch_m=pitch, tool='gmg.interlock.write_export',
               commit=guard._git('rev-parse', 'HEAD'), argv=sys.argv, reference=reference, fit=fit,
               pose_source='reference', frames=int(b.meta['T']), f_star=int(f_star), fiducials_file=ff,
               fiducials_world=fw, fiducials_back=fb)
    with open(_hdr_path(path), 'w') as f:
        json.dump(hdr, f, indent=1, default=_jdefault)
    return path


def _hdr_path(path):
    return path[:-4] + '.json' if path.endswith('.npz') else path + '.json'


def _kabsch(X, Y):
    """R, t minimising sum |R X + t - Y|^2."""
    cx, cy = X.mean(0), Y.mean(0)
    H = (X - cx).T @ (Y - cy)
    U, _, Vt = np.linalg.svd(H)
    D = np.diag([1.0, 1.0, np.sign(np.linalg.det(Vt.T @ U.T))])
    R = Vt.T @ D @ U.T
    return R, cy - R @ cx


def _chain_items(prov):
    """(inputs {path: sha256 or None}, artifacts {path: sha256 or None}, steps) of a reference provenance in either
    layout: the Embodiment tool's {chain: [{tool, commit, run_id, artifact, sha256, inputs {path: sha}}], ...} or our
    old {chain: [...], inputs {path: sha}} (F-I3.10)."""
    chain = prov.get('chain') or []
    steps = [s for s in chain if isinstance(s, dict)]
    inputs, arts = {}, {}
    for s in steps:
        for p, h in (s.get('inputs') or {}).items():
            inputs[str(p)] = h
        if s.get('artifact'):
            arts[str(s['artifact'])] = s.get('sha256')
    for p, h in (prov.get('inputs') or {}).items():
        inputs[str(p)] = h
    return inputs, arts, steps


MESH_SUFFIX = ('.glb', '.obj', '.ply', '.stl', '.urdf', '.xml', '.gltf')
DATASET_PARQUET = ('track_3/', '/hfds/', '/data/chunk-', 'episode_0')


def chain_path_reason(path, sha=None):
    """Why a path of a reference provenance chain is refused (F-I3.10), or (None, flag). Ground truth anywhere
    (mocap, scans, *_align, oracle, /loc/, the deny-list globs and sha256, the gmg REFUSED folders) is refused;
    `.parquet` is allowed except the public / eval dataset's episode parquets (by location); library_v1..v4 files are
    allowed only as simulator mesh assets (a mesh suffix: flag `ref_sim_assets_library`), never as an object-motion
    source."""
    raw = str(path)
    low = raw.lower()
    for s in ('mocap', '/scan', '_scan', '_align', 'oracle', '/loc/'):
        if s in low:
            return f'path contains {s!r}', None
    if sha and sha in guard.DENY['sha256']:
        return f'sha256 on the deny-list ({guard.DENY["sha256"][sha]})', None
    if '.parquet' in low and any(s in low for s in DATASET_PARQUET):
        return 'a dataset episode parquet (ground-truth pose field)', None
    flag = None
    import re as _re
    if _re.search(r'meshes/library_v(?:[1-4]|3x)/', low) or _re.search(r'library_v[1-4]', low):
        if low.endswith(MESH_SUFFIX) or '/content/assets' in low:
            flag = 'ref_sim_assets_library'
        else:
            return 'library_v1..v4 file that is not a simulator mesh asset (object-motion source?)', None
    if low.startswith(('hf://', 'http://', 'https://')) or '(box-local' in low or '/content/' in low:
        return None, flag
    q = os.path.abspath(raw)
    if q.lower().endswith('.parquet'):            # the '.parquet' substring alone is not a reason here; the rest is
        q = q[:-len('.parquet')] + '.pqref'
    why = guard._path_reason(q, 'own')
    if why and flag and 'library_v' in why:
        why = None
    return why, flag


def _prov_check(ref, rep, synthetic_ok=False):
    """F-I1.13 step (2) with F-I3.10: the chain may come from the Embodiment tool (per-step inputs) or be reconstructed
    (flag `prov_reconstructed`); every step names a tool and a run id; the chain holds a perception `poses.npz` with a
    sha256; nothing in it is ground truth (chain_path_reason). Returns the chain's {path: sha256} inputs."""
    prov = (ref or {}).get('provenance') or {}
    if not ref or not prov:
        rep['refused'].append('reference provenance missing')
        return {}
    if synthetic_ok and prov.get('chain') == ['synthetic test']:
        rep['flags'].append('synthetic_reference')
        return {}
    inputs, arts, steps = _chain_items(prov)
    if not steps:
        rep['refused'].append('reference provenance has no chain steps')
        return inputs
    bad = [i for i, s in enumerate(steps) if not s.get('tool') or not s.get('run_id')]
    if bad:
        rep['refused'].append(f'reference provenance incomplete: steps {bad} lack tool or run_id')
    src = str(prov.get('source') or '')
    if prov.get('reconstructed') or src.startswith(('--prov', 'inferred')) or any(
            'reconstructed' in str(s.get('tool', '')) for s in steps):
        rep['flags'].append('prov_reconstructed')
    poses = {p: h for p, h in {**inputs, **arts}.items() if os.path.basename(p.split(' ')[0]) == 'poses.npz' and h}
    if not poses:
        rep['refused'].append('reference provenance names no perception poses.npz with a sha256')
    unhashed = [p for p, h in inputs.items() if not h]
    if unhashed:
        rep['flags'].append('prov_input_unhashed')
        rep['prov_unhashed'] = unhashed[:20]
    flags = set()
    for pth, h in list(inputs.items()) + list(arts.items()) + [(ref.get('path', ''), ref.get('sha256'))]:
        why, fl = chain_path_reason(pth, h)
        if why:
            rep['refused'].append(f'reference chain input {pth}: {why}')
        if fl:
            flags.add(fl)
    rep['flags'] += sorted(flags)
    return {**inputs, **arts}


def _rel_check(z, objs, F_man, O, fs):
    """rel_T rows at f_star against the independent poses O {obj: 4x4 at f_star, reference frame}: the partner's file
    fiducials mapped by the export's rel_T and by inv(O_t) O_p; max distance (m) per ordered pair. A geom-frame or
    re-centred object frame shows here at full size (R_rel c_p - c_t), while a common world transform cannot hide it
    (rel_T is frame-free)."""
    out = {}
    for i, (f, t, q) in enumerate(zip(z['fp_frame'], z['fp_target'], z['fp_partner'])):
        if int(f) != fs:
            continue
        to, qo = objs[int(t)], objs[int(q)]
        Rp = np.linalg.inv(O[to]) @ O[qo]
        Re = np.asarray(z['rel_T'][i], np.float64)
        F = F_man[qo]
        d = np.linalg.norm((F @ Re[:3, :3].T + Re[:3, 3]) - (F @ Rp[:3, :3].T + Rp[:3, 3]), axis=1).max()
        out[f'{to}<-{qo}'] = float(d)
    return out


def _ref_pose_check(hdr, objs, F_man, T_hdr, chain, ref_poses=None, tracks=None, z=None):
    """F-I1.13 step (1) `fiducials_world` against an INDEPENDENT reference pose at f_star (F-I3.10, the orchestrator's
    resolution 2). Sources: (i) ref_poses {obj: 4x4 world_T_obj at f_star in the reference frame} from an independent
    reader (hook for B10: a guard role for our reference parquets' object_body_* columns); (ii) our tracks
    (dict(path, sha256, poses), role tracks) when their sha256 is the chain's perception poses.npz: then the pose is
    world_T_cam @ cam_T_obj at f_star, mapped into the reference frame by ONE rigid transform common to all objects
    plus a per-object vertical shift (mkref's per-object table snap), fitted on the fiducials. Returns (status
    'pass' | 'fail' | 'unavailable', info)."""
    tol = K('fid_tol_m')
    fs = int(hdr['f_star'])
    fw = {o: np.asarray(hdr['fiducials_world'][o], np.float64).reshape(8, 3) for o in objs}
    if ref_poses is not None:
        W = ref_poses(fs) if callable(ref_poses) else ref_poses
        err = {o: float(np.linalg.norm(F_man[o] @ np.asarray(W[o])[:3, :3].T + np.asarray(W[o])[:3, 3] - fw[o],
                                       axis=1).max()) for o in objs}
        rel = _rel_check(z, objs, F_man, {o: np.asarray(W[o], np.float64) for o in objs}, fs) if z is not None else {}
        ok = all(v <= tol for v in err.values()) and all(v <= tol for v in rel.values())
        return ('pass' if ok else 'fail'), dict(mode='independent reader', err_mm={o: round(v * 1e3, 3)
                                                                                      for o, v in err.items()},
                                                rel_T_f_star_mm={k: round(v * 1e3, 3) for k, v in rel.items()})
    if tracks is None:
        return 'unavailable', dict(reason='no independent reference pose (no reader, no tracks)')
    shas = {h for p, h in chain.items() if os.path.basename(str(p).split(' ')[0]) == 'poses.npz' and h}
    if tracks.get('sha256') not in shas:
        return 'unavailable', dict(reason='our tracks are not the chain\'s perception poses.npz (sha256 differs)',
                                   tracks_sha256=tracks.get('sha256'), chain_poses_sha256=sorted(shas))
    P = tracks['poses']
    if int(len(P['world_T_cam'])) != int(T_hdr):
        return 'fail', dict(reason=f'frame count {T_hdr} differs from the chain tracks ({len(P["world_T_cam"])})')
    W = {o: P['world_T_cam'][fs].astype(np.float64) @ P[f'cam_T_{o}'][fs].astype(np.float64) for o in objs}
    X = {o: F_man[o] @ W[o][:3, :3].T + W[o][:3, 3] for o in objs}
    s = {o: 0.0 for o in objs}
    ez = np.array([0.0, 0.0, 1.0])
    for _ in range(20):
        R, t = _kabsch(np.vstack([X[o] for o in objs]), np.vstack([fw[o] - s[o] * ez for o in objs]))
        s_new = {o: float(np.mean((fw[o] - (X[o] @ R.T + t)) @ ez)) for o in objs}
        if max(abs(s_new[o] - s[o]) for o in objs) < 1e-9:
            s = s_new
            break
        s = s_new
    res = {o: float(np.linalg.norm(fw[o] - s[o] * ez - (X[o] @ R.T + t), axis=1).max()) for o in objs}
    Tc = np.eye(4); Tc[:3, :3] = R; Tc[:3, 3] = t
    O = {}
    for o in objs:
        O[o] = Tc @ W[o]; O[o][:3, 3] += s[o] * ez
    rel = _rel_check(z, objs, F_man, O, fs) if z is not None else {}
    ok = all(v <= tol for v in res.values()) and all(v <= tol for v in rel.values())
    # report only (not enforced): rel_T deviation over ALL rows with the same frame and shifts; a re-centring along
    # the vertical at f_star is absorbed by the vertical shift there, but not once the object turns
    allrows = []
    if z is not None:
        for f in sorted(set(int(x) for x in z['fp_frame'])):
            Of = {}
            for o in objs:
                Wf = P['world_T_cam'][f].astype(np.float64) @ P[f'cam_T_{o}'][f].astype(np.float64)
                Of[o] = Tc @ Wf; Of[o][:3, 3] += s[o] * ez
            allrows += list(_rel_check(z, objs, F_man, Of, f).values())
    allrep = dict(n=len(allrows), median_mm=round(float(np.median(allrows)) * 1e3, 3) if allrows else None,
                  p90_mm=round(float(np.percentile(allrows, 90)) * 1e3, 3) if allrows else None,
                  max_mm=round(float(np.max(allrows)) * 1e3, 3) if allrows else None)
    return ('pass' if ok else 'fail'), dict(mode='chain tracks (frame-free: common rigid frame + per-object vertical '
                                                 'shift)', residual_mm={o: round(v * 1e3, 3) for o, v in res.items()},
                                            vertical_shift_mm={o: round(v * 1e3, 2) for o, v in s.items()},
                                            rel_T_f_star_mm={k: round(v * 1e3, 3) for k, v in rel.items()},
                                            rel_T_all_rows_report_only=allrep)


def validate(path, sim_dir, ref_poses=None, tracks=None, synthetic_ok=False, allow_do_not_use=False):
    """INTERLOCK 11.2 / F-I1.13 validator with the F-I3.10 corrections (works on the Embodiment tool's header).
    Returns (ok, report); report['refused'] lists the reasons of a refusal, report['pushed_residual'] = 'none' |
    'kept' | 'forced_nan' (flag fit_provenance_refused). Never raises on a malformed export (it is refused). Same on
    public and eval. ref_poses / tracks: the independent reference pose of step (1) (_ref_pose_check); without one the
    export is refused. synthetic_ok: tests only (a reference whose provenance chain is the literal 'synthetic test')."""
    from gmg.simpieces import inside_any
    rep = dict(refused=[], flags=[])
    try:
        hdr = json.load(open(_hdr_path(path)))
        z = dict(np.load(path, allow_pickle=False))
    except Exception as e:
        rep['refused'].append(f'unreadable export: {type(e).__name__}: {e}')
        return False, rep
    try:
        sim = load_sim(sim_dir, allow_do_not_use=allow_do_not_use)
    except Exception as e:
        rep['refused'].append(f'sim folder: {e}')
        return False, rep
    if allow_do_not_use and (sim['manifest'].get('do_not_use') or os.path.exists(os.path.join(sim_dir,
                                                                                               'DO_NOT_USE.json'))):
        rep['flags'].append('do_not_use_overridden (diagnostic only)')
    man = sim['manifest']
    if hdr.get('schema') != SCHEMA_INTR:
        rep['refused'].append(f'schema {hdr.get("schema")!r}')
    objs = list(hdr.get('objects') or [])
    unknown = [o for o in objs if o not in sim['objects']]
    if not objs or unknown:
        rep['refused'].append(f'objects {objs} not in the delivered round ({sim["objects"]})')
        return False, rep
    need = ('frame', 'target', 'partner', 'pts_local', 'fp_frame', 'fp_target', 'fp_partner', 'rel_T',
            'pushed_residual_m', 'intr_vol_m3')
    miss = [k for k in need if k not in z]
    if miss:
        rep['refused'].append(f'export arrays missing: {miss}')
        return False, rep
    # (1a) mesh hashes: the header's piece files (keys '<obj>/piece_XX.obj' or 'piece_XX.obj') == the round's pieces
    for o in objs:
        mf = man_piece_files(man, o)
        hm = {os.path.basename(k): v for k, v in ((hdr.get('meshes') or {}).get(o) or {}).items()}
        hp = {k: v for k, v in hm.items() if k.startswith('piece_') and k.endswith('.obj')}
        if not hp:
            rep['refused'].append(f'no piece hashes for {o}')
            continue
        if set(hp) != set(mf):
            rep['refused'].append(f'{o}: piece files {sorted(set(hp) ^ set(mf))[:6]} not in both the export and the '
                                  f'delivered round')
        bad = [k for k in hp if k in mf and hp[k] != mf[k]]
        if bad:
            rep['refused'].append(f'{o}: piece hashes {bad[:6]} differ from the delivered round')
    # (1b) frames, indices, frame-pair rows, rigidity
    T_hdr = hdr.get('T', hdr.get('frames'))
    if T_hdr is None:
        rep['refused'].append('no frame count in the header (T or frames)')
        return False, rep
    T_hdr = int(T_hdr)
    fr, fpf = np.asarray(z['frame']), np.asarray(z['fp_frame'])
    if (len(fr) and (fr.min() < 0 or fr.max() >= T_hdr)) or (len(fpf) and (fpf.min() < 0 or fpf.max() >= T_hdr)):
        rep['refused'].append(f'frames out of range [0, {T_hdr})')
        return False, rep
    B = len(objs)
    for k in ('target', 'partner', 'fp_target', 'fp_partner'):
        v = np.asarray(z[k])
        if len(v) and (v.min() < 0 or v.max() >= B):
            rep['refused'].append(f'{k} index out of range')
            return False, rep
    fpi = {}
    for i, (f, t, q) in enumerate(zip(fpf, z['fp_target'], z['fp_partner'])):
        key = (int(f), int(t), int(q))
        if key in fpi:
            rep['refused'].append(f'duplicate frame-pair row {key}')
            return False, rep
        fpi[key] = i
    keys = set(zip(fr.tolist(), np.asarray(z['target']).tolist(), np.asarray(z['partner']).tolist()))
    orphan = [k for k in keys if k not in fpi]
    if orphan:
        rep['refused'].append(f'{len(orphan)} sample groups have no frame-pair row (e.g. {sorted(orphan)[:3]})')
        return False, rep
    R = np.asarray(z['rel_T'])[:, :3, :3]
    if len(R) and (np.abs(np.einsum('nji,njk->nik', R, R) - np.eye(3)).max() > 1e-4 or
                   np.abs(np.linalg.det(R) - 1).max() > 1e-4):
        rep['refused'].append('rel_T not rigid')
    # (1c) fiducials: file fiducials == the round's, round trip, and the independent reference pose
    tol = K('fid_tol_m')
    F_man = {o: man_fiducials(man, o) for o in objs}
    try:
        fs = int(hdr['f_star'])
        if not 0 <= fs < T_hdr:
            raise ValueError('f_star out of range')
        for o in objs:
            if hdr.get('fiducials_file') is not None and \
                    np.abs(np.asarray(hdr['fiducials_file'][o], np.float64).reshape(8, 3) - F_man[o]).max() > 1e-6:
                rep['refused'].append(f'fiducials_file of {o} differ from the round manifest (stale manifest?)')
            Fb = np.asarray(hdr['fiducials_back'][o], np.float64).reshape(8, 3)
            if np.linalg.norm(F_man[o] - Fb, axis=1).max() > tol:
                rep['refused'].append(f'fiducial round trip {o} > 0.5 mm')
            np.asarray(hdr['fiducials_world'][o], np.float64).reshape(8, 3)
    except Exception as e:
        rep['refused'].append(f'fiducial fields missing or malformed: {type(e).__name__}: {e}')
        return False, rep
    if 'reference_poses_f_star' in hdr:
        rep['flags'].append('header_reference_poses_ignored')
    # (2) reference provenance (needed by (1c)'s chain-tracks source)
    chain = _prov_check(hdr.get('reference') or {}, rep, synthetic_ok=synthetic_ok)
    status, info = _ref_pose_check(hdr, objs, F_man, T_hdr, chain, ref_poses=ref_poses, tracks=tracks, z=z)
    info_pub = {k: v for k, v in info.items() if not k.startswith('_')}
    rep['reference_pose'] = dict(status=status, **info_pub)
    if status == 'fail':
        rep['refused'].append(f'fiducials_world off the independent reference pose at f_star by > 0.5 mm: {info_pub}')
    elif status == 'unavailable':
        rep['refused'].append(f'no independent reference pose for the fiducial check (F-I1.13 (1), F-I3.10): '
                              f'{info.get("reason")}')
    # (1d) containment of 10,000 samples in the target's pieces and, mapped back, in the partner's
    rng = np.random.default_rng(0)
    n = len(fr)
    if n:
        idx = rng.choice(n, min(K('contain_n'), n), replace=False)
        ins_t = np.zeros(len(idx), bool); ins_p = np.zeros(len(idx), bool)
        tg, pa, ff = np.asarray(z['target'])[idx], np.asarray(z['partner'])[idx], fr[idx]
        X = np.asarray(z['pts_local'])[idx].astype(np.float64)
        for ti, t in enumerate(objs):
            m = tg == ti
            if not m.any():
                continue
            ins_t[m] = inside_any(sim['pieces'][t], X[m])
            for qi, q in enumerate(objs):
                mq = m & (pa == qi)
                if not mq.any():
                    continue
                Y = np.zeros((int(mq.sum()), 3))
                for j, (ii, f) in enumerate(zip(np.nonzero(mq)[0], ff[mq])):
                    Ti = np.linalg.inv(np.asarray(z['rel_T'][fpi[(int(f), ti, qi)]], np.float64))
                    Y[j] = Ti[:3, :3] @ X[ii] + Ti[:3, 3]
                ins_p[mq] = inside_any(sim['pieces'][q], Y)
        rep['containment'] = dict(target=round(float(ins_t.mean()), 4), partner=round(float(ins_p.mean()), 4),
                                  n=int(len(idx)))
        if ins_t.mean() < K('contain_share') or ins_p.mean() < K('contain_share'):
            rep['refused'].append(f'containment {rep["containment"]} < 99 %')
    # (3) fit block: pushed_residual_m counts only for a fit on this round's _fit meshes and props_gmg.json, 1 cm / 3 deg
    pr = np.asarray(z['pushed_residual_m'], np.float64)
    rep['pushed_residual'] = 'none' if not np.isfinite(pr).any() else 'kept'
    if np.isfinite(pr).any():
        fit = hdr.get('fit') or {}
        why = []
        if not fit:
            why.append('no fit block')
        if fit and not fit.get('commit'):
            why.append('fit commit unknown')
        want = {o: man['files'].get(f'_fit/{o}.glb') for o in objs}
        if fit and {o: (fit.get('meshes') or {}).get(o) for o in objs} != want:
            why.append('fit meshes are not the round\'s _fit/<obj>.glb')
        if fit and (fit.get('props') or {}).get('sha256') != man['files'].get('props_gmg.json'):
            why.append('fit props are not the round\'s props_gmg.json')
        pri = fit.get('prior') or {}
        try:
            if fit and not (abs(float(pri.get('sig_p', 0)) - 0.01) < 1e-9 and
                            abs(float(pri.get('sig_r_deg', 0)) - 3.0) < 1e-9):
                why.append('fit prior is not 1 cm / 3 deg')
        except (TypeError, ValueError):
            why.append('fit prior unreadable')
        if fit.get('nan_reasons'):
            why.append(f'exporter nan_reasons {fit.get("nan_reasons")}')
        if why:
            rep['pushed_residual'] = 'forced_nan'
            rep['flags'].append('fit_provenance_refused')
            rep['fit_refused'] = why
    ok = not rep['refused']
    return ok, rep


def intrusions_from_export(path, val, o, p, ev_o, partner_samples=None):
    """Intrusions of target o by partner p from a validated export (pts_local in o's file frame = our object frame).
    partner_samples (F-I3.1): the partner's full solid samples in its own frame (the union of its delivered pieces at
    2 mm, what the exporter samples), so the push proxy moves the whole partner and the across axis n comes from the
    partner's body, as on the tracks path."""
    hdr = json.load(open(_hdr_path(path)))
    z = dict(np.load(path, allow_pickle=False))
    objs = hdr['objects']
    ti, qi = objs.index(o), objs.index(p)
    m = (z['target'] == ti) & (z['partner'] == qi)
    fr = z['frame'][m].astype(np.int64)
    P = z['pts_local'][m].astype(np.float64)
    rel = {}
    pushed = {}
    for i, (f, t, q) in enumerate(zip(z['fp_frame'], z['fp_target'], z['fp_partner'])):
        if int(t) == ti and int(q) == qi:
            rel[int(f)] = np.asarray(z['rel_T'][i], np.float64)
            v = float(z['pushed_residual_m'][i])
            pushed[int(f)] = (np.nan if val.get('pushed_residual') == 'forced_nan' else v)
    Pp = np.zeros_like(P)
    for f in np.unique(fr):
        k = fr == f
        Ti = np.linalg.inv(rel[int(f)])
        Pp[k] = P[k] @ Ti[:3, :3].T + Ti[:3, 3]
    lin, ok = ev_o.grid.lin(P)
    k = ok.copy(); k[ok] = ev_o.occ[lin[ok]]
    return Intrusions(o, p, fr[k], P[k], Pp[k], lin[k], rel, sorted(rel), 'export', Xp=partner_samples,
                      pushed_residual=pushed if any(np.isfinite(v) for v in pushed.values()) else None)


def default_physics(copies=None, log=None):
    """The physics_fn carve_from_intrusions uses by default (F-I1.8 P2-P7 and the plain-MuJoCo P1 pre-check, on the
    export's own relative poses P_sim; the FlashCHORD P1 settle is the Embodiment's jitter_check, A3)."""
    from gmg import simphys as PH

    def fn(b, o, p, carved, default, recs, rels=None, run=None):
        cm3 = {r['target']: r['_sim_solid']['cm3'] for r in recs if r.get('sim_carve')}
        return PH.pair_physics(b, o, p, carved[o], carved[p], run, cm3, default[o], default[p],
                               copies or PH.k_('copies'), 'export round', rels=rels, log=log)
    return fn


def carve_from_intrusions(pair, intrusions, evidence, sim_dir, out_dir, round, visual=None, physics_fn='default',
                          sources=None, identity=None, ref_poses=None, copies=None, allow_do_not_use=False):
    """INTERLOCK 11.3, the function the Embodiment session calls; the SAME rule as our tracks path (F-I3.1): the export
    is validated (11.2, F-I3.10), its samples go through make_side (engaged runs with the hold-out fixed by earlier
    rounds, persistent regions, the identity / track gate, sources (a) and (b) and the observed notches from
    `sim_dir/sources/<obj>.npz` written by the gmg at round 0, or SOURCES) and decide_pair with the cumulative budget
    (F-I3.3: earlier rounds' carves against the round-0 solid). The carved pieces go through physics_fn ('default':
    default_physics(); None: no physics) and are delivered only if it says so; otherwise round `round` delivers the
    previous pieces and the carved ones go to out_dir/_carved_pending_p1/. Writes round `round` into out_dir (never
    overwritten) with the interlock state for the next round. Returns dict(pieces_dir, decisions, physics,
    validation, manifest)."""
    from gmg import simpieces as SP
    if int(round) > K('max_rounds'):
        raise ValueError(f'round {round} > {K("max_rounds")} (F-I1.13)')
    b = evidence if hasattr(evidence, 'meta') and hasattr(evidence, 'poses') else load_bundle_any(evidence)
    tracks = None
    if b.meta.get('tracks'):
        tracks = dict(path=b.meta['tracks'].get('path'), sha256=b.meta['tracks'].get('sha256'), poses=b.poses)
    ok, val = validate(intrusions, sim_dir, ref_poses=ref_poses, tracks=tracks, allow_do_not_use=allow_do_not_use)
    if not ok:
        return dict(pieces_dir=None, decisions=[], physics=None, validation=val)
    hdr = json.load(open(_hdr_path(intrusions)))
    sim = load_sim(sim_dir, episode=b.meta.get('ep'), allow_do_not_use=allow_do_not_use)
    st = sim['manifest'].get('interlock') or {}
    identity = identity or ('eval' if b.meta.get('split') == 'eval' else 'public')
    o, p = pair
    ev = {x: Evidence(b, x, sim['fit'][x]) for x in pair}
    S = {x: _union_grid(sim['pieces'][x], 0.002) for x in pair}
    src_dir = os.path.join(sim_dir, 'sources')
    sides, intrs = {}, {}
    for t, q in ((o, p), (p, o)):
        intr = intrusions_from_export(intrusions, val, t, q, ev[t], partner_samples=S[q])
        intrs[t] = intr
        src = (sources or {}).get(t) if sources is not None else load_sources(src_dir, t, ev[t].grid)
        hold = (st.get('holdout') or {}).get(f'{t}<-{q}')
        # F-I3.1: the export's frame-pairs on OUR frame grid (the bundle's census frames, its stride): the gate's good
        # share, the blocks and the gap bridging then count the same frames as on the tracks path (an export holds
        # every frame; with stride 2 half of them have no evidence and would halve the good share)
        grid_fr = set(int(f) for f in (b.contact(t, q).get('frames') or
                                       range(0, int(b.meta['T']), int(b.meta['stride']))))
        cf = sorted(f for f in intr.rel if f in grid_fr)
        sides[t] = make_side(b, t, q, ev[t], intr, cf, sources=src, identity=identity,
                             partner_collider=S[q], holdout=hold,
                             carved_before=(st.get('carved_cm3') or {}).get(t, 0.0),
                             solid_ref_cm3=(st.get('solid_ref_cm3') or {}).get(t) or ev[t].solid_cm3())
    recs = decide_pair(b, sides[o], sides[p], round_k=round)
    carved = {}
    for x in pair:
        cv = [r['_sim_solid'] for r in recs if r['target'] == x and r.get('sim_carve')]
        hl = list(sim['pieces'][x])
        for c in cv:
            if c['kind'] == 'box':
                hl, _ = SP.remove_box(hl, c)
        vox = [c for c in cv if c['kind'] == 'voxels']
        if vox:
            res = SP.build(sim['fit'][x], ev[x], vox)
            hl = res['carved']
        carved[x] = hl
    any_carve = any(r.get('sim_carve') for r in recs)
    if physics_fn == 'default':
        physics_fn = default_physics(copies)
    phys = None
    if any_carve and physics_fn is not None:
        run = next((r['_comp'].run for r in recs if r.get('sim_carve')), None)
        phys = physics_fn(b, o, p, carved, sim['pieces'], recs, rels=intrs[o].rel, run=run)
    deliver = bool(phys is not None and phys.get('deliver_carved'))
    # the interlock state for the next round (F-I3.3): fixed hold-out, cumulative carves, round-0 solid, regions
    hold_new = dict(st.get('holdout') or {})
    reg = {}
    for t, q in ((o, p), (p, o)):
        key = f'{t}<-{q}'
        ch = sorted(set(hold_new.get(key) or []) | {int(f) for r in sides[t].runs for f in r.check})
        hold_new[key] = ch
        carved_lin = [r['_comp'].region() for r in recs if r['target'] == t and r.get('sim_carve')]
        reg[key] = np.unique(np.concatenate(carved_lin)) if carved_lin else np.zeros(0, np.int64)
    cum = dict(st.get('carved_cm3') or {})
    for x in pair:
        add = sum(r['_sim_solid']['cm3'] for r in recs if r['target'] == x and r.get('sim_carve')) if deliver else 0.0
        cum[x] = _bi.round(float(cum.get(x, 0.0)) + float(add), 4)
    dnu_prev = sim['manifest'].get('do_not_use') or (json.load(open(os.path.join(sim_dir, 'DO_NOT_USE.json')))
                                                       if os.path.exists(os.path.join(sim_dir, 'DO_NOT_USE.json'))
                                                       else None)
    state = dict(round=int(round), holdout=hold_new, carved_cm3=cum,
                 solid_ref_cm3={x: (st.get('solid_ref_cm3') or {}).get(x) or sides[x].solid_ref_cm3 for x in pair},
                 default_collider_cm3=st.get('default_collider_cm3') or
                 {x: _bi.round(SP.hull_volume(sim['pieces'][x]) * 1e6, 3) for x in pair},
                 previous=os.path.abspath(sim_dir), delivered='carved' if deliver else 'previous',
                 regions_file='interlock_regions.npz')
    objects = {x: dict(visual=(visual or {}).get(x, sim['fit'][x]),
                       gate=dict(do_not_use=f'built on a do-not-use round ({sim_dir}): {dnu_prev}') if dnu_prev
                       else None,
                       hulls=carved[x] if deliver else sim['pieces'][x],
                       carve=dict(round=round, delivered='carved' if deliver else 'previous',
                                  decisions=[public(r) for r in recs if r['target'] == x],
                                  intrusions=os.path.abspath(intrusions), validation=val,
                                  physics=None if phys is None else {k: v for k, v in phys.items()
                                                                     if k != 'overlap_series'})) for x in pair}
    if os.path.exists(os.path.join(out_dir, 'manifest.json')):
        raise FileExistsError(f'{out_dir}: a delivered round is never overwritten')
    os.makedirs(out_dir, exist_ok=True)
    if os.path.isdir(src_dir) and sources is None:          # the sources travel with every round (hashed below)
        import shutil
        shutil.copytree(src_dir, os.path.join(out_dir, 'sources'))
    elif sources is not None:
        for x in pair:
            s_ = sources.get(x) or {}
            write_sources(os.path.join(out_dir, 'sources'), x, s_.get('sil'), s_.get('gen'), s_.get('notches'),
                          s_.get('notches_sil'), ev[x].grid)
    np.savez_compressed(os.path.join(out_dir, 'interlock_regions.npz'),
                        **{f'lin::{k}': v for k, v in reg.items()},
                        **{f'grid_lo::{x}': ev[x].grid.lo for x in pair},
                        **{f'grid_vox::{x}': np.float64(ev[x].grid.vox) for x in pair},
                        **{f'grid_shape::{x}': np.asarray(ev[x].grid.shape) for x in pair})
    man = SP.write_round(out_dir, b.meta.get('ep'), b.meta.get('split', 'public'), round, objects,
                         dict(source='embodiment export', reference=hdr.get('reference')), interlock=state)
    if any_carve and not deliver:
        import trimesh
        for x in pair:
            dd = os.path.join(out_dir, '_carved_pending_p1', x)
            os.makedirs(dd, exist_ok=True)
            for k, V in enumerate(carved[x]):
                trimesh.convex.convex_hull(V).export(os.path.join(dd, f'piece_{k:02d}.obj'))
    return dict(pieces_dir=out_dir, decisions=[public(r) for r in recs], physics=phys, validation=val, manifest=man)


def _export_volumes(path, regions, frames_check, engaged):
    """Per ordered pair key 't<-q': persistent intrusion volume (samples in the round's carved regions) on the engaged
    check frames, and total volume per phase ('engaged_check', 'other')."""
    hdr = json.load(open(_hdr_path(path)))
    z = dict(np.load(path, allow_pickle=False))
    objs = hdr['objects']
    pitch = float(hdr.get('pitch_m', 0.002))
    out = {}
    for ti, t in enumerate(objs):
        for qi, q in enumerate(objs):
            if t == q:
                continue
            key = f'{t}<-{q}'
            chk = set(frames_check.get(key) or []) & set(engaged.get(key) or [])
            m = (z['target'] == ti) & (z['partner'] == qi)
            f = z['frame'][m]
            pers = 0.0
            if key in regions and len(regions[key]['lin']):
                g = regions[key]['grid']
                lin, ok = g.lin(z['pts_local'][m].astype(np.float64))
                inR = np.zeros(len(lin), bool)
                inR[ok] = np.isin(lin[ok], regions[key]['lin'])
                pers = float((inR & np.isin(f, list(chk))).sum()) * pitch ** 3 * 1e6
            mf = (z['fp_target'] == ti) & (z['fp_partner'] == qi)
            ff = z['fp_frame'][mf]
            vv = z['intr_vol_m3'][mf].astype(np.float64) * 1e6
            ech = np.isin(ff, list(chk))
            out[key] = dict(persistent_check_cm3=pers, engaged_check_cm3=float(vv[ech].sum()),
                            other_cm3=float(vv[~ech].sum()))
    return out


def round_accept(intr_prev, intr_new, sim_prev, sim_new, band_m=None, settle=None, ref_poses=None, tracks=None):
    """F-I1.13 / INTERLOCK 11.5 acceptance of round k (sim_new, built from intr_prev on sim_prev; intr_new = the
    Embodiment's export on sim_new), with the F-I3.3 corrections: both exports must validate (else not accepted, A1
    not computed); check frames and the targeted regions are the ones fixed in sim_new's interlock state (never
    recomputed from the new export); A1 = on the engaged check frames the persistent intrusion (samples in the carved
    regions) falls by >= 10 % AND no other ordered pair or phase gains > 0.1 cm3; A2 = check-frame pairs with
    pushed_residual_m > band do not increase (both fit blocks validated, band given); A3 = every carved pair passed
    P2-P7 here AND the external settle (Embodiment jitter_check, `settle` = {pair: dict(pass_=bool, ...)}) passed;
    without that report A3 is pending and the round is not accepted; A4 = cumulative budget (10 % of the round-0 solid
    where (iv) applies), >= 90 % of the round-0 default collider volume, topology kept, <= 165 shapes."""
    from gmg import simpieces as SP
    out = dict(valid=[], refused=[])
    for path, sd in ((intr_prev, sim_prev), (intr_new, sim_new)):
        ok, val = validate(path, sd, ref_poses=ref_poses, tracks=tracks)
        out['valid'].append(ok)
        out['refused'].append(val.get('refused'))
        out.setdefault('pushed_state', []).append(val.get('pushed_residual'))
    if not all(out['valid']):
        out.update(A1=None, A2=None, A3=None, A4=None, accept=False, why='an export did not validate')
        return out
    simn = load_sim(sim_new)
    man = simn['manifest']
    st = man.get('interlock') or {}
    rz = dict(np.load(os.path.join(sim_new, st.get('regions_file', 'interlock_regions.npz')), allow_pickle=False))
    regions = {}
    for k, v in rz.items():
        if k.startswith('lin::'):
            key = k[5:]
            t = key.split('<-')[0]
            regions[key] = dict(lin=v, grid=Grid(rz[f'grid_lo::{t}'], float(rz[f'grid_vox::{t}']),
                                                rz[f'grid_shape::{t}']))
    hold = st.get('holdout') or {}
    engaged = {}
    for o in _man_objects(man):
        cj = json.load(open(os.path.join(sim_new, o, 'carve.json')))
        for d in cj.get('decisions') or []:
            key = f'{d["target"]}<-{d["partner"]}'
            fr = d.get('run', {}).get('frames') or []
            if len(fr) == 2:
                engaged.setdefault(key, set()).update(range(int(fr[0]), int(fr[1]) + 1))
    engaged = {k: sorted(v) for k, v in engaged.items()}
    v0 = _export_volumes(intr_prev, regions, hold, engaged)
    v1 = _export_volumes(intr_new, regions, hold, engaged)
    out['volumes_prev'] = {k: {kk: round(vv, 4) for kk, vv in v.items()} for k, v in v0.items()}
    out['volumes_new'] = {k: {kk: round(vv, 4) for kk, vv in v.items()} for k, v in v1.items()}
    targeted = [k for k in regions if len(regions[k]['lin'])]
    if not targeted:
        out.update(A1=None, accept=False, why='the round adds no CARVE (stop)')
    else:
        p0 = sum(v0[k]['persistent_check_cm3'] for k in targeted if k in v0)
        p1 = sum(v1[k]['persistent_check_cm3'] for k in targeted if k in v1)
        gains = []
        for k in set(v0) | set(v1):
            for ph in ('engaged_check_cm3', 'other_cm3'):
                if k in targeted and ph == 'engaged_check_cm3':
                    continue
                dv = v1.get(k, {}).get(ph, 0.0) - v0.get(k, {}).get(ph, 0.0)
                if dv > 0.1:
                    gains.append((k, ph, round(dv, 3)))
        out['A1_detail'] = dict(persistent_prev_cm3=round(p0, 4), persistent_new_cm3=round(p1, 4), gains=gains)
        out['A1'] = bool(p0 > 0 and p1 <= 0.9 * p0 and not gains)
    # A2
    pr = []
    for path in (intr_prev, intr_new):
        z = dict(np.load(path, allow_pickle=False))
        chk = np.zeros(len(z['fp_frame']), bool)
        hdr = json.load(open(_hdr_path(path)))
        for i, (f, t, q) in enumerate(zip(z['fp_frame'], z['fp_target'], z['fp_partner'])):
            key = f'{hdr["objects"][int(t)]}<-{hdr["objects"][int(q)]}'
            chk[i] = int(f) in set(hold.get(key) or [])
        pr.append(None if band_m is None else int((np.asarray(z['pushed_residual_m'])[chk] > band_m).sum()))
    out['A2'] = (pr[1] <= pr[0]) if (None not in pr and all(s == 'kept' for s in out['pushed_state'])) else None
    # A3
    objs = _man_objects(man)
    phys = [json.load(open(os.path.join(sim_new, o, 'carve.json'))).get('physics') for o in objs]
    delivered = st.get('delivered') == 'carved'
    p27 = all((ph or {}).get('P2_P7_pass') for ph in phys) if delivered else None
    out['A3_detail'] = dict(delivered=st.get('delivered'), P2_P7_pass=p27, settle=settle)
    if not delivered:
        out['A3'] = None
    elif settle is None:
        out['A3'] = None
        out['A3_detail']['pending'] = 'the FlashCHORD settle (Embodiment jitter_check --k 16) has not been reported'
    else:
        out['A3'] = bool(p27 and all(v.get('pass_') for v in settle.values()))
    # A4
    cum = st.get('carved_cm3') or {}
    base = st.get('solid_ref_cm3') or {}
    dcol = st.get('default_collider_cm3') or {}
    shares = {o: (float(cum.get(o, 0.0)) / float(base[o])) if base.get(o) else None for o in objs}
    keep = {o: round(SP.hull_volume(simn['pieces'][o]) * 1e6 / dcol[o], 4) if dcol.get(o) else None for o in objs}
    shapes = sum(len(simn['pieces'][o]) for o in objs)
    topo = all(((d.get('budget') or {}).get('topology') or {}).get('before') ==
               ((d.get('budget') or {}).get('topology') or {}).get('after')
               for o in objs for d in json.load(open(os.path.join(sim_new, o, 'carve.json'))).get('decisions') or []
               if d.get('sim_carve'))
    a4 = all(v is None or v <= K('budget_vol') + 1e-9 for v in shares.values()) and \
        all(v is None or v >= 0.9 for v in keep.values()) and topo and shapes <= 165
    out['A4_detail'] = dict(cum_share=shares, collider_kept=keep, shapes=shapes, topology=topo)
    out['A4'] = bool(a4)
    out['accept'] = bool(out.get('A1') and out['A2'] is not False and out['A3'] and out['A4'])
    return out


def _tracks_of(evidence):
    if not evidence:
        return None
    b = load_bundle_any(evidence)
    t = b.meta.get('tracks') or {}
    return dict(path=t.get('path'), sha256=t.get('sha256'), poses=b.poses) if t else None


def _cli():
    import argparse
    ap = argparse.ArgumentParser(prog='python -m gmg.interlock')
    sub = ap.add_subparsers(dest='cmd', required=True)
    c = sub.add_parser('carve')
    c.add_argument('--pair', nargs=2, required=True); c.add_argument('--intrusions', required=True)
    c.add_argument('--evidence', required=True); c.add_argument('--sim-in', required=True)
    c.add_argument('--out', required=True); c.add_argument('--round', type=int, required=True)
    c.add_argument('--no-physics', action='store_true')
    v = sub.add_parser('validate')
    v.add_argument('--intrusions', required=True); v.add_argument('--sim-in', required=True)
    v.add_argument('--evidence', help='our bundle: its tracks are the independent reference pose when they are the '
                                      'chain\'s poses.npz (F-I3.10)')
    r = sub.add_parser('accept')
    r.add_argument('--prev', required=True); r.add_argument('--new', required=True)
    r.add_argument('--sim-prev', required=True); r.add_argument('--sim-new', required=True)
    r.add_argument('--evidence'); r.add_argument('--band-m', type=float); r.add_argument('--settle')
    a = ap.parse_args()
    if a.cmd == 'validate':
        ok, rep = validate(a.intrusions, a.sim_in, tracks=_tracks_of(a.evidence))
        print(json.dumps(dict(ok=ok, **rep), indent=1, default=_jdefault))
        return
    if a.cmd == 'accept':
        st = json.load(open(a.settle)) if a.settle else None
        res = round_accept(a.prev, a.new, a.sim_prev, a.sim_new, band_m=a.band_m, settle=st,
                           tracks=_tracks_of(a.evidence))
        print(json.dumps(res, indent=1, default=_jdefault))
        return
    if a.round > K('max_rounds'):
        raise SystemExit(f'round {a.round} > {K("max_rounds")} (F-I1.13)')
    res = carve_from_intrusions(tuple(a.pair), a.intrusions, a.evidence, a.sim_in, a.out, a.round,
                                physics_fn=None if a.no_physics else 'default')
    print(json.dumps({k: v for k, v in res.items() if k != 'manifest'}, indent=1, default=_jdefault)[:20000])


if __name__ == '__main__':
    _cli()
