"""GT-free candidate features and vetoes (module M13 of SPEC section 7; full form, build step B5).

Frozen definitions: PREREG A.2-A.4 (selection itself: select.py, PREREG A.5). Nothing here reads a scan, a label, a
mocap pose or an eval output; scripts/mesh_metric.py is never imported (SPEC section 2): the kit decode and the
self-ambiguity are own copies, checked against the originals by tests/test_score.py.

Held-out time blocks and folds (PREREG A.2, A.4)
  plan(bundle, obj, K, gen_views=None) -> dict   the object's good frames in time order split into K contiguous
                                        blocks of equal frame count; held-out sets H_k (owned points, one per 4 mm
                                        voxel per frame, then <= 20,000 at random, seed 0); generator view hold-out
                                        (frames within 8 deg of a generator input view removed for all candidates;
                                        skipped and flagged gen_view_overlap if > 80 % of the frames would go)
  heldout(bundle, obj, K=None)          the plan's blocks (B1 interface)
  train_frames(plan, k)                 the good frames outside block k (fold k's build frames)
  view_dirs(bundle, obj, frames)        unit direction from the object's centre (median owned point) to the camera
                                        centre, object frame; the view of a frame
  build_folds(producer, ctx, plan, post=None)   fold candidates c_k = producer.produce(ctx, frames=train_frames(plan,
                                        k)), matched by cid; a producer that cannot rebuild leaves its candidates
                                        fixed; post = the caller's marker attach applied to every fold mesh (A.2)
  fold_meshes(cand, folds, K)           [c_1..c_K] for one candidate: its fold rebuilds, or its all-frames mesh in
                                        every fold ('fixed': fixed meshes, X0 replay, producers without a fold build)
  evidence(meshes, bundle, obj, blocks, fsv)   PREREG A.4 ray score: c_k cast against H_k; R_k, E, per-frame sums
  bootstrap_reps(blocks) / e_reps(...)  200 moving-block replicates (seed 0) of contiguous runs of L = max(1,
                                        round(n_k^(1/3))) frames inside each block, shared by every candidate (paired)
  se_diff(reps_c, reps_best)            SD over replicates of E(c) - E(best)
Vetoes and features
  kit_decode(path_or_mesh), decoded_mesh, v1      own copy of the kit packer's budget_mesh at 4096 (V1)
  fsv_far(mesh, obs)                    PREREG A.3 (20,000 area-weighted samples, seed 0; FREE and no OBSERVED voxel
                                        within 2 voxels, Chebyshev)
  v2(mesh, bundle, obj), v3(fsv_c, fsv_s, tau), below_table(mesh, bundle, obj)   PREREG A.3 V2, V3, V4
  fold_fsv_diffs(folds_c, folds_s, obs) PREREG A.3 fold null D(c, k) = fsv_far(c_k) - fsv_far(s_k) (all-frames grid)
  tau_q99(diffs)                        PREREG A.3 tau: the 99th percentile of the fold null D(c, k)
  ambiguity(v, f, kind)                 own copy of scripts/mesh_metric.ambiguity with own copies of the kit AUC
                                        helpers it calls (_pca_basis, _initial_rotations, _kabsch,
                                        _symmetric_mean_distance, _surface_moments, _sample_mesh_surface,
                                        _axial_rotations; ICP 40 iterations, trim 0.9)
  self_ambiguity(mesh, kind=None)       ambiguity + the V5 rule: flip_risk = amb - floor < floor; flip_units =
                                        floor((amb - floor) / floor) (A.5 key 2). The caller passes the mesh with
                                        TRUSTED balls only (base mesh when the object's balls are not trusted);
                                        score_pool does this and reports unknown (amb_unknown) when the balls are
                                        untrusted and no ball-free base_mesh exists
  kit_symmetry(obj)                     'axial' / 'half' / None from the kit config (config/tracks.json, role kit)
  obs_flip_margin(mesh, obs, kind)      diagnostic: ICP of our owned points onto the candidate from the kit's 24 PCA
                                        starts; o2m residual of the best flipped solution minus the identity-start one
  score_pool(cands, bundle, obj, ...)   all features of one pool; select.pick(pool) takes it as is
"""
from __future__ import annotations

import itertools
import math
import os

import numpy as np
import trimesh
from scipy import ndimage
from scipy.spatial import cKDTree

from gmg import contact as CT, geom, guard
from gmg.bundle import STATE_FREE, STATE_OBSERVED

KIT_FACES = KIT_VERTICES = 4096
# kit AUC.py constants used by the ambiguity copy (metric_code/track_3/AUC.py; kit scorer code, copied, never imported)
KIT_ALIGNMENT_SAMPLES = 3000
KIT_ICP_ITERATIONS = 40
KIT_TRIM_FRACTION = 0.9
KIT_SYMMETRY_ANGLES = 360
AMB_SEEDS = (101, 202)          # mesh_metric.ambiguity: the two independent surface samples
FLIP_UNITS_INF = 10 ** 6        # flip_units when no start stays a flip (amb infinite): the safest possible value


def consts():
    return dict(
        kit_faces=guard.constant('kit_budget_faces', KIT_FACES, 'kit:mesh_budget 4096'),
        kit_vertices=guard.constant('kit_budget_vertices', KIT_VERTICES, 'kit:mesh_budget 4096'),
        fsv_n=guard.constant('fsv_far_samples', 20000, 'generic:PREREG A.3 20,000 area-weighted samples'),
        fsv_band=guard.constant('fsv_far_band_vox', 2, 'generic:PREREG A.6 fsv_far band 2 voxels'),
        fsv_w=guard.constant('fsv_far_weight', 10.0, 'generic:PREREG A.6 fsv_far weight 10'),
        K=guard.constant('blocks_K', 3, 'generic:PREREG A.6 K = 3'),
        n_boot=guard.constant('bootstrap_n', 200, 'generic:PREREG A.6 bootstrap 200'),
        seed=guard.constant('seed', 0, 'generic:PREREG A.6 seed 0'),
        ray_band=guard.constant('ray_band_sigma', 3.0, 'generic:PREREG A.6 ray band 3 sigma'),
        ray_clip=guard.constant('ray_clip_sigma', 10.0, 'generic:PREREG A.6 ray clip 10 sigma'),
        heldout_max=guard.constant('heldout_max_points', 20000, 'generic:PREREG A.2 held-out subsample'),
        v2_cos=guard.constant('v2_normal_cos', 0.5, 'generic:PREREG A.6 V2 normal cosine > 0.5'),
        v2_min=guard.constant('v2_count_min', 3, 'generic:PREREG A.6 V2 count > max(3, 1 %)'),
        v2_frac=guard.constant('v2_count_frac', 0.01, 'generic:PREREG A.6 V2 count > max(3, 1 %)'),
        v4_share=guard.constant('v4_share_max', 0.01, 'generic:PREREG A.6 V4 1 %'),
        v4_floor=guard.constant('v4_depth_floor_m', 0.002, 'generic:PREREG A.6 V4 max(3 sigma, 2 mm)'),
        v4_k=guard.constant('v4_depth_sigma', 3.0, 'generic:PREREG A.6 V4 max(3 sigma, 2 mm)'),
        v4_n=guard.constant('v4_volume_samples', 20000, 'generic:PREREG A.3 V4 20,000 volume samples'),
    )


def consts_b5():
    """Constants added by the full form (B5)."""
    return dict(
        K_menu=guard.constant('variant_menu_K', [3, 5], 'generic:PREREG A.7 menu K in {3, 5}'),
        gen_deg=guard.constant('gen_view_holdout_deg', 8.0, 'generic:PREREG A.6 generator view hold-out 8 deg '
                                                             '(the view-spacing constant)'),
        gen_skip=guard.constant('gen_view_holdout_skip_frac', 0.8, 'generic:PREREG A.6 hold-out skipped if > 80 % '
                                                                     'removed'),
        block_rate=guard.constant('bootstrap_block_rate', 1.0 / 3.0, 'generic:PREREG A.6 block length '
                                                                     'round(n_k^(1/3))'),
        tau_q=guard.constant('v3_tau_percentile', 99.0, 'generic:PREREG A.3 tau = 99th percentile of the fold null'),
        amb_n=guard.constant('amb_samples', KIT_ALIGNMENT_SAMPLES, 'kit:AUC.py _ALIGNMENT_SAMPLES 3000 '
                                                                    '(mesh_metric.ambiguity)'),
        icp_it=guard.constant('amb_icp_iterations', KIT_ICP_ITERATIONS, 'kit:AUC.py _ICP_ITERATIONS 40'),
        icp_trim=guard.constant('amb_icp_trim', KIT_TRIM_FRACTION, 'kit:AUC.py _TRIM_FRACTION 0.9'),
        flip_deg=guard.constant('amb_flip_deg', 90.0, 'generic:SPEC section 10 flip = rotation > 90 deg '
                                                     '(mesh_metric.ambiguity)'),
    )


# ------------------------------------------------------------------------------------------------ V1: kit decode
def kit_decode(path, faces=KIT_FACES, vertices=KIT_VERTICES):
    """Copy of the kit packer v2dlb/mesh_budget.budget_mesh (weld, simplify to both limits, pad to the exact row
    counts). Kept line for line; tests/test_score.py checks it against the kit file. PATH may also be an in-memory
    Trimesh (then the file round trip, e.g. GLB float32 vertices, is skipped; the shipped file is the reference)."""
    import fast_simplification
    if isinstance(path, trimesh.Trimesh):
        mesh = trimesh.Trimesh(np.asarray(path.vertices), np.asarray(path.faces), process=False)
    else:
        mesh = trimesh.load(path, force="mesh", process=False)
    welded = trimesh.Trimesh(mesh.vertices, mesh.faces, process=True)
    v = np.asarray(welded.vertices, dtype=np.float64)
    f = np.asarray(welded.faces, dtype=np.int64)
    while len(f) > faces or len(v) > vertices:
        target = faces if len(v) <= vertices else min(faces, int(len(f) * vertices / len(v) * 0.95))
        if target < 1:
            raise ValueError(f"{path}: cannot fit a surface within the mesh budget")
        old_size = (len(v), len(f))
        v, f = fast_simplification.simplify(v, f, target_count=target)
        reduced = trimesh.Trimesh(v, f, process=False)
        reduced.remove_unreferenced_vertices()
        v = np.asarray(reduced.vertices, dtype=np.float64)
        f = np.asarray(reduced.faces, dtype=np.int64)
        if not len(f) or (len(v), len(f)) == old_size:
            raise ValueError(f"{path}: mesh simplification cannot satisfy the budget")
    v = np.concatenate([v, np.repeat(v[:1], vertices - len(v), axis=0)])
    f = np.concatenate([f, np.zeros((faces - len(f), 3), dtype=np.int64)])
    return v, f


def decoded_mesh(path):
    v, f = kit_decode(path)
    tri = v[f]
    ar = 0.5 * np.linalg.norm(np.cross(tri[:, 1] - tri[:, 0], tri[:, 2] - tri[:, 0]), axis=1)
    return trimesh.Trimesh(v, f[ar > 1e-14], process=True)


def v1(path):
    consts()
    try:
        m = decoded_mesh(path)
    except ValueError as e:
        return dict(veto=True, watertight=False, error=str(e))
    wt = bool(m.is_watertight)
    return dict(veto=not wt, watertight=wt, faces=int(len(m.faces)), vertices=int(len(m.vertices)),
                bodies=int(m.body_count), volume_cm3=round(float(m.volume) * 1e6, 3) if wt else None)


# ------------------------------------------------------------------------------------------------ fsv_far
def far_free_grid(obs):
    c = consts()
    st = np.asarray(obs['state'])
    k = 2 * int(c['fsv_band']) + 1
    near_obs = ndimage.binary_dilation(st == STATE_OBSERVED, structure=np.ones((k, k, k), bool))
    return (st == STATE_FREE) & ~near_obs


def fsv_far(mesh, obs, far=None):
    c = consts()
    if len(mesh.faces) == 0:
        return dict(fsv_far=None, outside_grid=None)
    far = far_free_grid(obs) if far is None else far
    P, _ = geom.surface_samples(mesh, int(c['fsv_n']), seed=int(c['seed']))
    lo, vox = np.asarray(obs['lo'], np.float64), float(obs['vox'])
    vi = np.floor((P - lo) / vox).astype(np.int64)
    ins = np.all((vi >= 0) & (vi < np.asarray(far.shape)), axis=1)
    hit = np.zeros(len(P), bool)
    hit[ins] = far[tuple(vi[ins].T)]
    return dict(fsv_far=float(hit.mean()), outside_grid=float(1 - ins.mean()))


def fold_fsv_diffs(folds_c, folds_s, obs):
    """PREREG A.3 null for tau: D(c, k) = fsv_far(c_k) - fsv_far(s_k) for every fold k, both measured against the
    all-frames grid of OBS (the bundle's grid). folds_c, folds_s: [c_1..c_K], [s_1..s_K] (fold rebuilds; a None fold
    gives None)."""
    far = far_free_grid(obs)
    out = []
    for ck, sk in zip(folds_c, folds_s):
        if ck is None or sk is None:
            out.append(None); continue
        a, b = fsv_far(ck, obs, far)['fsv_far'], fsv_far(sk, obs, far)['fsv_far']
        out.append(None if a is None or b is None else float(a - b))
    return out


def tau_q99(diffs):
    """PREREG A.3: tau = the 99th percentile of D(c, k) = fsv_far(c_k) - fsv_far(s_k) over every CPU candidate and
    fold (numpy linear interpolation between order statistics). No floor, no cap. None if there is no difference."""
    q = consts_b5()['tau_q']
    d = np.asarray([x for x in diffs if x is not None and np.isfinite(x)], np.float64)
    return float(np.percentile(d, q)) if len(d) else None


# ------------------------------------------------------------------------------------------------ blocks and folds
def view_dirs(bundle, obj, frames):
    """(n,3) unit view directions of FRAMES in OBJ's frame: from the object's centre (median of its owned points,
    all frames) to the camera centre inv(cam_T_obj[f]) . 0."""
    obs = bundle.obs(obj)
    P = np.asarray(obs['pts'], np.float64)[np.asarray(obs['own']) == 0]
    centre = np.median(P, axis=0) if len(P) else np.zeros(3)
    out = []
    for f in frames:
        T = np.asarray(bundle.poses[f'cam_T_{obj}'][int(f)], np.float64)
        c = -T[:3, :3].T @ T[:3, 3]
        d = c - centre
        out.append(d / max(np.linalg.norm(d), 1e-12))
    return np.asarray(out, np.float64).reshape(-1, 3)


def _gen_holdout(bundle, obj, frames, gen_views):
    """PREREG A.2 generator view hold-out. gen_views: frame indices of the generator inputs, or (n,3) unit view
    directions in OBJ's frame. Returns (removed frames, info)."""
    c = consts_b5()
    gv = np.asarray(gen_views)
    if gv.ndim == 2 and gv.shape[1] == 3 and gv.dtype.kind == 'f':
        G = gv / np.linalg.norm(gv, axis=1, keepdims=True)
        src = 'directions'
    else:
        G = view_dirs(bundle, obj, [int(x) for x in gv.ravel()])
        src = 'frames'
    D = view_dirs(bundle, obj, frames)
    cosmax = (D @ G.T).max(axis=1) if len(G) and len(D) else np.full(len(D), -1.0)
    near = cosmax >= np.cos(np.radians(c['gen_deg'])) - 1e-12
    removed = [int(f) for f, n in zip(frames, near) if n]
    frac = len(removed) / max(len(frames), 1)
    info = dict(gen_views=int(len(G)), source=src, deg=c['gen_deg'], near_frames=len(removed), frames=len(frames),
                near_frac=round(frac, 4))
    if frac > c['gen_skip']:
        info.update(applied=False, gen_view_overlap=True)
        return [], info
    info.update(applied=True, gen_view_overlap=False)
    return removed, info


def plan(bundle, obj, K=None, gen_views=None):
    """PREREG A.2 blocks and held-out sets. The object's good frames, in time order, are split into K contiguous
    blocks of equal frame count (np.array_split). With gen_views (only when the pool holds GEN or FUSE candidates),
    frames whose view lies within 8 deg of a generator input view are removed from every H_k, unless more than 80 %
    of the good frames would go (then nothing is removed and the plan is flagged gen_view_overlap). H_k = owned points
    (own == 0) of block k's remaining frames, at most one per 4 mm voxel per frame (random choice, seed 0), then at
    most 20,000 at random (seed 0). Returns dict(K, frames, blocks=[dict(frames, kept, idx)], removed,
    gen_view_overlap, holdout)."""
    c = consts()
    consts_b5()
    K = int(c['K'] if K is None else K)
    obs = bundle.obs(obj)
    good = [int(f) for f in bundle.good_frames(obj)]
    removed, hinfo = [], None
    if gen_views is not None and len(np.asarray(gen_views).ravel()):
        removed, hinfo = _gen_holdout(bundle, obj, good, gen_views)
    rem = set(removed)
    fr = np.asarray(obs['frame'])
    own = np.asarray(obs['own']) == 0
    P = np.asarray(obs['pts'], np.float64)
    lo, vox = np.asarray(obs['lo'], np.float64), float(obs['vox'])
    rng = np.random.default_rng(int(c['seed']))
    blocks = []
    for bf in np.array_split(np.asarray(good, np.int64), K):
        kept = [int(f) for f in bf if int(f) not in rem]
        m = np.nonzero(np.isin(fr, kept) & own)[0]
        if len(m) == 0:
            blocks.append(dict(frames=[int(x) for x in bf], kept=kept, idx=np.zeros(0, np.int64)))
            continue
        perm = rng.permutation(len(m))
        mm = m[perm]
        key = np.concatenate([fr[mm, None].astype(np.int64), np.floor((P[mm] - lo) / vox).astype(np.int64)], 1)
        _, first = np.unique(key, axis=0, return_index=True)
        sel = mm[np.sort(first)]
        if len(sel) > int(c['heldout_max']):
            sel = rng.choice(sel, int(c['heldout_max']), replace=False)
        blocks.append(dict(frames=[int(x) for x in bf], kept=kept, idx=np.sort(sel)))
    return dict(K=K, frames=good, blocks=blocks, removed=sorted(rem),
                gen_view_overlap=bool(hinfo and hinfo.get('gen_view_overlap')), holdout=hinfo)


def heldout(bundle, obj, K=None):
    """B1 interface: the blocks of plan(bundle, obj, K) (no generator hold-out)."""
    return plan(bundle, obj, K)['blocks']


def train_frames(pl, k):
    """Fold k's build frames: the plan's good frames outside block k (PREREG A.2 'frames outside block k'). Frames
    removed by the generator hold-out stay in training (they leave the held-out sets only)."""
    out = set(pl['blocks'][k]['frames'])
    return [f for f in pl['frames'] if f not in out]


def build_folds(producer, ctx, pl, post=None):
    """Fold rebuilds of every candidate of PRODUCER: produce(ctx, frames=train_frames(pl, k)) for k = 1..K, matched
    to the all-frames candidates by cid. Returns {cid: [mesh or None per fold]} and a status dict. A producer that
    cannot rebuild on a frame subset (NotImplementedError) returns {} with status 'fixed' (its candidates are then
    scored with their all-frames mesh in every fold, fold_meshes).
    post: optional callable mesh -> mesh applied to every fold mesh, the hook for PREREG A.2 "markers attached to
    every fold candidate alike": pass the same attach (and pack) the shipped mesh got, e.g.
    post=lambda m: markers.attach(m, episode_balls, obs). score_pool flags a row fold_balls_missing when its shipped
    mesh has balls and a rebuilt fold mesh does not carry the same markers.attach report."""
    folds, status = {}, dict(producer=getattr(producer, '__name__', str(producer)), K=pl['K'], state='rebuilt',
                             missing={}, post=None if post is None else getattr(post, '__name__', str(post)))
    for k in range(pl['K']):
        try:
            cands = producer.produce(ctx, frames=train_frames(pl, k))
        except NotImplementedError as e:
            status.update(state='fixed', reason=str(e))
            return {}, status
        for c in cands:
            folds.setdefault(c.cid, [None] * pl['K'])[k] = c.mesh if post is None else post(c.mesh)
    for cid, ms in folds.items():
        miss = [k for k, m in enumerate(ms) if m is None]
        if miss:
            status['missing'][cid] = miss
    return folds, status


def fold_meshes(mesh, folds, K):
    """[c_1..c_K] of one candidate and its fold state: 'rebuilt' (every fold rebuilt), 'fixed' (no fold rebuild: the
    all-frames mesh in every fold; fixed meshes, X0 replay, producers without a fold build), or 'partial' (a fold
    whose rebuild produced no such candidate is scored as an EMPTY mesh: every held-out ray of that block then counts
    as missing surface, the candidate did not exist on those training frames)."""
    if not folds:
        return [mesh] * int(K), 'fixed'
    out, state = [], 'rebuilt'
    for m in folds:
        if m is None:
            out.append(trimesh.Trimesh(np.zeros((0, 3)), np.zeros((0, 3), np.int64), process=False))
            state = 'partial'
        else:
            out.append(m)
    return out, state


# ------------------------------------------------------------------------------------------------ held-out ray score
def _huber(x, d):
    ax = np.abs(x)
    return np.where(ax <= d, x * x / (2 * d), ax - d / 2)


def ray_costs(mesh, bundle, obj, idx):
    """Per held-out point: Delta = d_hit - d_obs along the ray from its camera through it, and its cost (A.4)."""
    c = consts()
    s = bundle.sigma(obj)
    obs = bundle.obs(obj)
    P = np.asarray(obs['pts'], np.float64)[idx]
    fr = np.asarray(obs['frame'])[idx]
    tris = np.asarray(mesh.vertices, np.float64)[np.asarray(mesh.faces, np.int64)] if len(mesh.faces) else \
        np.zeros((0, 3, 3))
    delta = np.full(len(idx), np.inf)
    for f in np.unique(fr):
        m = fr == f
        T = bundle.poses[f'cam_T_{obj}'][int(f)].astype(np.float64)
        Pc = P[m] @ T[:3, :3].T + T[:3, 3]
        tc = tris @ T[:3, :3].T + T[:3, 3]
        r = geom.ray_ranges(tc, Pc)
        delta[m] = r - np.linalg.norm(Pc, axis=1)
    band, clip = c['ray_band'] * s, c['ray_clip'] * s
    cost = np.where(np.abs(delta) <= band, _huber(np.where(np.isfinite(delta), delta, 0.0), s),
                    np.minimum(np.abs(np.where(np.isfinite(delta), delta, clip)), clip))
    return delta, cost, fr


def evidence(meshes, bundle, obj, blocks, fsv):
    """PREREG A.4: R_k = mean cost / sigma of c_k's rays over H_k; E = mean_k R_k + 10 fsv_far (fsv_far of the
    all-frames candidate). MESHES: [c_1..c_K] (fold candidates) or one mesh (all-frames form: the same mesh in every
    fold). Returns E, R_blocks, ray summary, per-block summaries and the per-frame (cost sum, count) for the
    bootstrap."""
    c = consts()
    s = bundle.sigma(obj)
    if isinstance(meshes, trimesh.Trimesh):
        meshes = [meshes] * len(blocks)
    if len(meshes) != len(blocks):
        raise ValueError(f'evidence: {len(meshes)} fold meshes for {len(blocks)} blocks')
    R, per_frame, n, miss, extra, raw, per_block = [], [], 0, 0, 0, [], []
    for mk, bk in zip(meshes, blocks):
        if len(bk['idx']) == 0:
            R.append(np.nan); per_frame.append({}); per_block.append(dict(n=0)); continue
        delta, cost, fr = ray_costs(mk, bundle, obj, bk['idx'])
        R.append(float(cost.mean() / s))
        uf, inv = np.unique(fr, return_inverse=True)
        per_frame.append({int(f): (float(a), int(b)) for f, a, b in
                          zip(uf, np.bincount(inv, cost), np.bincount(inv))})
        mi = int((delta > c['ray_band'] * s).sum()); ex = int((delta < -c['ray_band'] * s).sum())
        per_block.append(dict(n=int(len(cost)), miss_frac=round(mi / len(cost), 5), extra_frac=round(ex / len(cost), 5),
                              no_hit_frac=round(float((~np.isfinite(delta)).mean()), 5),
                              mean_cost_sigma=round(float(cost.mean() / s), 5)))
        n += len(cost); miss += mi; extra += ex
        raw.append(np.abs(delta[np.isfinite(delta)]))
    Rm = float(np.nanmean(R)) if np.isfinite(R).any() else float('nan')
    allabs = np.concatenate(raw) if raw else np.zeros(0)
    return dict(E=Rm + c['fsv_w'] * fsv, R_blocks=[round(x, 5) for x in R], ray=dict(
        n=n, miss_frac=round(miss / max(n, 1), 5), extra_frac=round(extra / max(n, 1), 5),
        mean_cost_sigma=round(Rm, 5), median_abs_delta_mm=round(float(np.median(allabs)) * 1e3, 4) if len(allabs)
        else None), per_block=per_block, per_frame=per_frame)


def block_length(nk):
    """PREREG A.4 moving-block length L = max(1, round(n_k^(1/3)))."""
    return max(1, int(round(nk ** consts_b5()['block_rate'])))


def bootstrap_reps(blocks):
    """PREREG A.4: per replicate and block, the block's held-out frames (those left after the generator hold-out, in
    time order) resampled as contiguous runs of L = max(1, round(n_k^(1/3))) frames with replacement (run starts
    uniform over the n_k - L + 1 possible starts, ceil(n_k / L) runs), truncated to n_k. 200 replicates, seed 0.
    Every candidate is scored on the same replicates (paired)."""
    c = consts()
    rng = np.random.default_rng(int(c['seed']))
    reps = []
    for _ in range(int(c['n_boot'])):
        r = []
        for bk in blocks:
            fl = np.asarray(bk.get('kept', bk['frames']), np.int64)
            nk = len(fl)
            if nk == 0:
                r.append(fl); continue
            L = block_length(nk)
            starts = rng.integers(0, nk - L + 1, size=int(np.ceil(nk / L)))
            r.append(fl[(starts[:, None] + np.arange(L)[None]).ravel()[:nk]])
        reps.append(r)
    return reps


def e_reps(ev, fsv, sigma, reps):
    """E of one candidate on every bootstrap replicate (ratio estimator per block: summed cost / summed count of the
    resampled frames), plus 10 fsv_far (constant across replicates). A block whose resampled frames hold no held-out
    point has no R_k in that replicate and is dropped from its mean over blocks, as the point estimate drops a block
    without held-out points (nanmean); a replicate with no block left is NaN (se_diff skips it). The per-frame point
    counts are the same for every candidate (every held-out ray gets a cost), so the drops stay paired. (B5 round 2:
    the earlier form scored such a block R_k = 0, a perfect fit.)"""
    c = consts()
    out = np.empty(len(reps))
    for i, r in enumerate(reps):
        Rk = []
        for pf, fl in zip(ev['per_frame'], r):
            if not pf:
                continue
            a = sum(pf.get(int(f), (0.0, 0))[0] for f in fl)
            b = sum(pf.get(int(f), (0.0, 0))[1] for f in fl)
            if b == 0:
                continue
            Rk.append(a / b / sigma)
        out[i] = (float(np.mean(Rk)) if Rk else float('nan')) + c['fsv_w'] * fsv
    return out


def se_diff(reps_c, reps_best):
    """PREREG A.4 SE_diff(c) = SD over the paired replicates of E(c) - E(best) (numpy population SD), over the
    replicates where both are defined (NaN if none)."""
    d = np.asarray(reps_c, np.float64) - np.asarray(reps_best, np.float64)
    d = d[np.isfinite(d)]
    return float(np.std(d)) if len(d) else float('nan')


# ------------------------------------------------------------------------------------------------ V2
_OWN_TREE = {}


def _own_tree(bundle, obj):
    key = (id(bundle), obj)
    if key not in _OWN_TREE:
        obs = bundle.obs(obj)
        P = np.asarray(obs['pts'], np.float64)[np.asarray(obs['own']) == 0]
        _OWN_TREE[key] = cKDTree(P)
    return _OWN_TREE[key]


def v2(mesh, bundle, obj):
    """PREREG A.3 V2 against every other tracked object p with contact frames."""
    c = consts()
    out = dict(veto=False, partners={})
    if len(mesh.faces) == 0:
        out['veto'] = True
        out['empty'] = True
        return out
    cl = None
    for p in bundle.partners(obj):
        frames = sorted(set(bundle.contact(obj, p)['contact']))
        if not frames:
            out['partners'][p] = dict(contact_frames=0, veto=False)
            continue
        X, N, fid, n_p = CT.partner_samples(bundle, obj, p, frames)
        b = bundle.band(obj, p)
        thr = max(c['v2_min'], c['v2_frac'] * n_p)
        lo, hi = mesh.bounds
        near = np.all((X >= lo - b) & (X <= hi + b), axis=1)
        va = np.zeros(len(X), bool); vb = np.zeros(len(X), bool)
        info = {}
        if near.any():
            cl = cl or geom.Closest(mesh)
            Xn = X[near]
            d, _, fn = cl.query(Xn)
            ins, info = geom.inside(mesh, Xn)
            a = ins & (d > b)
            close = d <= b
            cosv = np.einsum('ij,ij->i', N[near], fn)
            bb = close & (cosv > c['v2_cos'])
            if bb.any():
                down = _own_tree(bundle, obj).query(Xn[bb], k=1, distance_upper_bound=b)[0]
                tmp = np.zeros(bb.sum(), bool)
                tmp[:] = ~np.isfinite(down) | (down > b)
                bb[np.nonzero(bb)[0]] = tmp
            va[np.nonzero(near)[0]] = a
            vb[np.nonzero(near)[0]] = bb & ~a
        pos = {f: i for i, f in enumerate(frames)}
        fi = np.array([pos[int(f)] for f in fid], np.int64)
        cnt = np.bincount(fi[va | vb], minlength=len(frames))
        ca = np.bincount(fi[va], minlength=len(frames)); cb = np.bincount(fi[vb], minlength=len(frames))
        med = float(np.median(cnt))
        rec = dict(contact_frames=len(frames), n_p=int(n_p), band_mm=round(b * 1e3, 4), threshold=round(thr, 3),
                   n_median=med, a_median=float(np.median(ca)), b_median=float(np.median(cb)),
                   n_max=int(cnt.max()), frames_violating=int((cnt > thr).sum()), veto=bool(med > thr),
                   inside_method=info.get('method'), inside_check=dict(checked=info.get('checked'),
                                                                       disagree=info.get('disagree')))
        out['partners'][p] = rec
        out['veto'] |= rec['veto']
    return out


def v3(fsv_c, fsv_s, tau):
    d = None if fsv_c is None or fsv_s is None else float(fsv_c - fsv_s)
    if tau is None:
        return dict(diff=d, tau=None, veto=False, applied=False,
                    note='tau is fitted on the public clean CPU batch (PREREG A.3, build step B13); not applied')
    return dict(diff=d, tau=float(tau), veto=bool(d is not None and d > tau), applied=True)


# ------------------------------------------------------------------------------------------------ V4
def below_table(mesh, bundle, obj):
    c = consts()
    r = (bundle.meta.get('rest') or {}).get(obj)
    if not r or not r.get('applies'):
        return dict(applies=False, veto=False, rest_share=(r or {}).get('share'))
    n, d = bundle.rest_plane(obj)
    s = bundle.sigma(obj)
    X, info = geom.volume_samples(mesh, int(c['v4_n']), seed=int(c['seed']), axis=int(np.argmax(np.abs(n))))
    if len(X) == 0:
        return dict(applies=True, veto=False, share=None, note='no enclosed volume', rest_share=r['share'])
    thr = max(c['v4_k'] * s, c['v4_floor'])
    h = X @ n + d
    share = float((h < -thr).mean())
    return dict(applies=True, veto=bool(share > c['v4_share']), share=round(share, 5), depth_mm=round(thr * 1e3, 3),
                rest_share=r['share'], min_height_mm=round(float(h.min()) * 1e3, 3), samples=info)


# ------------------------------------------------------------------------------------------------ self-ambiguity (V5)
# Own copies of the kit AUC.py helpers used by scripts/mesh_metric.ambiguity (kit scorer code is refused to the gmg
# at run time; these are copied line for line and checked against mesh_metric by tests/test_score.py).
def _sample_mesh_surface(vertices, faces, count, seed):
    a, b, c = vertices[faces[:, 0]], vertices[faces[:, 1]], vertices[faces[:, 2]]
    area = 0.5 * np.linalg.norm(np.cross(b - a, c - a), axis=1)
    total = area.sum()
    if not np.isfinite(total) or total <= 0:
        raise ValueError("object mesh has no surface area")
    rng = np.random.default_rng(seed)
    chosen = rng.choice(len(faces), size=count, p=area / total)
    r1, r2 = rng.random(count), rng.random(count)
    s = np.sqrt(r1)[:, None]
    return (1 - s) * a[chosen] + s * (1 - r2[:, None]) * b[chosen] + s * r2[:, None] * c[chosen]


def _pca_basis(points):
    centered = points - points.mean(axis=0)
    _, vectors = np.linalg.eigh(centered.T @ centered / max(len(centered), 1))
    basis = vectors[:, ::-1]
    if np.linalg.det(basis) < 0.0:
        basis[:, -1] *= -1.0
    return basis


def _initial_rotations(reference, candidate, maximum):
    ref_basis, cand_basis = _pca_basis(reference), _pca_basis(candidate)
    rotations = [np.eye(3)]
    seen = {tuple(np.round(rotations[0], 10).ravel())}
    for permutation in itertools.permutations(range(3)):
        permuted = np.eye(3)[:, permutation]
        for signs in itertools.product((-1.0, 1.0), repeat=3):
            mapping = permuted @ np.diag(signs)
            if np.linalg.det(mapping) <= 0.0:
                continue
            rotation = ref_basis @ mapping @ cand_basis.T
            if np.linalg.det(rotation) < 0.0:
                continue
            key = tuple(np.round(rotation, 10).ravel())
            if key in seen:
                continue
            seen.add(key)
            rotations.append(rotation)
            if len(rotations) >= maximum:
                return rotations
    return rotations


def _kabsch(source, target):
    source_center, target_center = source.mean(axis=0), target.mean(axis=0)
    left, _, right_t = np.linalg.svd((source - source_center).T @ (target - target_center))
    rotation = right_t.T @ left.T
    if np.linalg.det(rotation) < 0.0:
        right_t[-1, :] *= -1.0
        rotation = right_t.T @ left.T
    return rotation, target_center - rotation @ source_center


def _symmetric_mean_distance(reference, candidate):
    to_reference = cKDTree(reference).query(candidate, k=1)[0]
    to_candidate = cKDTree(candidate).query(reference, k=1)[0]
    return 0.5 * (float(np.mean(to_reference)) + float(np.mean(to_candidate)))


def _surface_moments(vertices, faces):
    triangles = vertices[faces]
    areas = 0.5 * np.linalg.norm(np.cross(triangles[:, 1] - triangles[:, 0],
                                          triangles[:, 2] - triangles[:, 0]), axis=1)
    keep = np.isfinite(areas) & (areas > 1e-12)
    if not keep.any():
        raise ValueError("object mesh has no surface area")
    triangles, areas = triangles[keep], areas[keep]
    total = float(areas.sum())
    centroid = (triangles.mean(axis=1) * areas[:, None]).sum(axis=0) / total
    centered = triangles - centroid
    squared = np.einsum("tij,tij->ti", centered, centered).sum(axis=1)
    cross = (np.einsum("ti,ti->t", centered[:, 0], centered[:, 1])
             + np.einsum("ti,ti->t", centered[:, 0], centered[:, 2])
             + np.einsum("ti,ti->t", centered[:, 1], centered[:, 2]))
    radius = float(np.sqrt(max(float((areas * (squared + cross) / 6.0).sum() / total), 0.0)))
    if not np.isfinite(radius) or radius <= 1e-12:
        raise ValueError("object mesh has zero or invalid extent")
    return centroid, radius


def _axial_rotations(axis, order=KIT_SYMMETRY_ANGLES):
    angles = np.arange(order) * (2 * np.pi / order)
    x, y, z = axis
    skew = np.array([[0, -z, y], [z, 0, -x], [-y, x, 0]])
    return (np.cos(angles)[:, None, None] * np.eye(3)
            + (1 - np.cos(angles))[:, None, None] * np.outer(axis, axis)
            + np.sin(angles)[:, None, None] * skew)


# copies of scripts/mesh_metric.py (rot_about, angle_deg, sym_axis, sym_rot_err, icp_from, ambiguity)
def rot_about(axis, angle):
    axis = np.asarray(axis, float) / np.linalg.norm(axis)
    x, y, z = axis
    K = np.array([[0, -z, y], [z, 0, -x], [-y, x, 0]])
    return np.eye(3) + math.sin(angle) * K + (1 - math.cos(angle)) * K @ K


def angle_deg(R):
    return math.degrees(math.acos(max(-1.0, min(1.0, (np.trace(R) - 1) / 2))))


def sym_axis(points, kind):
    """GT-free choice of the symmetry axis among the PCA axes: the one the shape is most invariant under
    (90 deg turn for axial, 180 deg for half-turn)."""
    if kind is None:
        return None
    basis = _pca_basis(points)
    ang = math.pi / 2 if kind == 'axial' else math.pi
    tree = cKDTree(points)
    best = None
    for k in range(3):
        d = tree.query(points @ rot_about(basis[:, k], ang).T)[0].mean()
        if best is None or d < best[0]:
            best = (d, basis[:, k].copy())
    return best[1]


def sym_rot_err(R, kind, axis):
    """Kit orientation error of a constant body rotation R (AUC.py _symmetry_orientation_errors, static)."""
    if kind is None:
        return angle_deg(R)
    if kind == 'half':
        return min(angle_deg(R), angle_deg(R @ rot_about(axis, math.pi)))
    a = R @ axis
    return math.degrees(math.atan2(np.linalg.norm(np.cross(a, axis)), np.clip(a @ axis, -1, 1)))


def icp_from(reference, candidate, start):
    """The kit's _align_rigid inner loop (trimmed ICP) from ONE start rotation."""
    tree = cKDTree(reference)
    rotation = start.copy()
    translation = reference.mean(axis=0) - rotation @ candidate.mean(axis=0)
    previous = math.inf
    for _ in range(KIT_ICP_ITERATIONS):
        moved = candidate @ rotation.T + translation
        distances, indices = tree.query(moved, k=1)
        keep = max(3, int(math.ceil(len(distances) * KIT_TRIM_FRACTION)))
        chosen = (np.argpartition(distances, keep - 1)[:keep] if keep < len(distances) else np.arange(len(distances)))
        step_rotation, step_translation = _kabsch(moved[chosen], reference[indices[chosen]])
        rotation = step_rotation @ rotation
        translation = step_rotation @ translation + step_translation
        error = float(np.mean(distances[chosen]))
        if math.isfinite(previous) and abs(previous - error) <= 1e-8 * max(previous, 1.0):
            break
        previous = error
    return rotation, translation, _symmetric_mean_distance(reference, candidate @ rotation.T + translation)


def ambiguity(v, f, kind):
    """Copy of scripts/mesh_metric.ambiguity: GT-free self-ambiguity [M]. Two independent 3000-point surface samples
    of the same mesh (kit sampler); ICP from each of the kit's non-identity PCA starts; residual of the best start
    that stays a flip (symmetry-aware rotation > 90 deg). Returns mm values and the noise floor (identity residual)."""
    c, r = _surface_moments(v, f)
    a = _sample_mesh_surface(v, f, KIT_ALIGNMENT_SAMPLES, AMB_SEEDS[0]) - c
    b = _sample_mesh_surface(v, f, KIT_ALIGNMENT_SAMPLES, AMB_SEEDS[1]) - c
    axis = sym_axis(a, kind)
    floor = _symmetric_mean_distance(a, b)
    starts = _initial_rotations(a, b, 10 ** 6)[1:]           # all signed-permutation PCA starts, minus identity
    best, best90, best45 = None, math.inf, math.inf
    for R0 in starts:
        R, t, d = icp_from(a, b, R0)
        e = sym_rot_err(R, kind, axis)
        if e > 90 and d < best90:
            best90, best = d, (e, angle_deg(R0))
        if e > 45:
            best45 = min(best45, d)
    return dict(amb_mm=best90 * 1e3, amb45_mm=best45 * 1e3, amb_floor_mm=floor * 1e3, amb_rel=best90 / r,
                amb_rot=None if best is None else round(best[0], 1), radius_mm=r * 1e3, n_starts=len(starts))


def flip_units(amb_mm, floor_mm):
    """PREREG A.5 key 2: floor((amb - floor) / floor); FLIP_UNITS_INF when no start stays a flip (amb infinite)."""
    if amb_mm is None or floor_mm is None:
        return None
    if not np.isfinite(amb_mm):
        return FLIP_UNITS_INF
    return int(math.floor((amb_mm - floor_mm) / max(floor_mm, 1e-12)))


def is_flip_risk(amb_mm, floor_mm):
    """PREREG A.3 V5 / SPEC section 10: flip-risk if amb - floor < floor."""
    if amb_mm is None or floor_mm is None:
        return None
    return bool(np.isfinite(amb_mm) and (amb_mm - floor_mm) < floor_mm)


def self_ambiguity(mesh, kind=None):
    """ambiguity() on MESH (vertices and faces as given: pass the packed mesh, which the kit decode only welds; with
    TRUSTED balls only) plus the V5 quantities. kind: the kit's declared symmetry of the object (kit_symmetry)."""
    consts_b5()
    v = np.asarray(mesh.vertices, np.float64)
    f = np.asarray(mesh.faces, np.int64)
    r = ambiguity(v, f, kind)
    out = dict(r)
    out['kind'] = kind
    out['flip_risk'] = is_flip_risk(r['amb_mm'], r['amb_floor_mm'])
    out['flip_units'] = flip_units(r['amb_mm'], r['amb_floor_mm'])
    if not np.isfinite(out['amb_mm']):
        out['amb_mm'] = None
        out['no_flip_start'] = True
    if not np.isfinite(out['amb45_mm']):
        out['amb45_mm'] = None
    return out


_KIT_SYM = {}


def kit_symmetry(obj):
    """The kit's declared symmetry of OBJ ('axial', 'half' or None) from {KIT}/config/tracks.json (role kit; kit
    metadata, not authored). Kit-symmetric objects skip V5 and the flip-safety key (PREREG A.3, A.5)."""
    if not _KIT_SYM:
        t = guard.load_json(os.path.join(guard.CFG['kit'], 'config', 'tracks.json'), 'kit')['tracks']['track_3']
        _KIT_SYM.update({n: 'axial' for n in t['axially_symmetric_objects']})
        _KIT_SYM.update({n: 'half' for n in t['half_turn_symmetric_objects']})
    return _KIT_SYM.get(obj)


def obs_flip_margin(mesh, obs, kind=None, n=KIT_ALIGNMENT_SAMPLES, seed=0):
    """Diagnostic (SPEC section 10): ICP of our own owned points onto the candidate from the kit's PCA starts (the
    identity start plus every signed-permutation start, as the kit's _initial_rotations lists them). The residual of
    a solution is the mean distance from the moved owned points to the candidate's surface samples (observed-to-model:
    the owned points cover one side, so the model-to-observed half would charge unseen surface alike for every start).
    Returns the identity-start residual, the best residual among solutions that end more than 90 deg (symmetry-aware)
    from the identity, and margin = flipped - identity (mm). Large = flips are clearly worse."""
    consts_b5()
    P = np.asarray(obs['pts'], np.float64)[np.asarray(obs['own']) == 0]
    if len(P) < 10 or len(mesh.faces) == 0:
        return dict(margin_mm=None, note='too few owned points or empty mesh')
    rng = np.random.default_rng(seed)
    Q = P[rng.choice(len(P), min(n, len(P)), replace=False)]
    v = np.asarray(mesh.vertices, np.float64); f = np.asarray(mesh.faces, np.int64)
    S = _sample_mesh_surface(v, f, n, AMB_SEEDS[0])
    axis = sym_axis(S - S.mean(0), kind)
    tree = cKDTree(S)
    starts = _initial_rotations(S, Q, 10 ** 6)
    ident, flipped, rot = None, math.inf, None
    for i, R0 in enumerate(starts):
        R, t, _ = icp_from(S, Q, R0)
        d = float(tree.query(Q @ R.T + t, k=1)[0].mean())
        if i == 0:
            ident = d
        e = sym_rot_err(R, kind, axis)
        if e > 90 and d < flipped:
            flipped, rot = d, e
    return dict(identity_mm=ident * 1e3, flipped_mm=flipped * 1e3 if np.isfinite(flipped) else None,
                margin_mm=(flipped - ident) * 1e3 if np.isfinite(flipped) else None,
                flipped_rot_deg=None if rot is None else round(rot, 1), n_starts=len(starts), points=int(len(Q)))


# ------------------------------------------------------------------------------------------------ one pool
def _get(c, k, default=None):
    return c.get(k, default) if isinstance(c, dict) else getattr(c, k, default)


def _attach_report(mesh):
    """The markers.attach per-ball report on MESH (metadata['balls']; pack.pack keeps it), or None when absent."""
    md = getattr(mesh, 'metadata', None)
    if not isinstance(md, dict) or 'balls' not in md or md['balls'] is None:
        return None
    return list(md['balls'])


def _ball_count(x, mesh):
    """(count, from_metadata) of the balls on the candidate: the declared count (Candidate.balls), or the length of
    the markers.attach report in mesh.metadata['balls'] when that is larger (a ball mesh whose count was not carried
    over; pack.pack keeps the report). A candidate with a base_mesh (balls attached) whose count is 0 and whose mesh
    carries no report raises (B5 round 3): the count is unknowable, and treating it as 0 would measure V5 on the
    mesh with untrusted balls or drop the trusted markers of A.5 key 3. Called before any scoring."""
    nd = int(_get(x, 'balls', 0) or 0)
    rep = _attach_report(mesh)
    nm = 0 if rep is None else len(rep)
    if _get(x, 'base_mesh') is not None and max(nd, nm) == 0 and rep is None:
        raise ValueError(f'score_pool: candidate {_get(x, "cid")!r} has a base_mesh (balls attached) but a ball count '
                         f'of 0 and no markers.attach report on its mesh (mesh.metadata["balls"]); set '
                         f'Candidate.balls or pass the mesh with its report (pack.pack keeps it)')
    return max(nd, nm), nm > nd


def amb_unknown(kind, reason):
    """The self-ambiguity of a candidate that cannot be measured as PREREG A.3 V5 / A.5 key 2 require ('trusted balls
    only'): neither safe nor risky for V5 (select.pick counts only True / False), last on the flip-safety key."""
    return dict(amb_mm=None, amb45_mm=None, amb_floor_mm=None, amb_rel=None, flip_risk=None, flip_units=None,
                kind=kind, unknown=True, reason=reason)


def _amb_rows(row, mesh, base, kind, trusted):
    """PREREG A.3 V5 and A.5 key 2: the self-ambiguity with TRUSTED balls only, else ball-free. A candidate has balls
    when its count is > 0 OR it has a base_mesh (B5 round 3: a base_mesh is never ignored).
      no balls                         -> the shipped mesh (ball-free)
      balls, trusted                   -> the shipped mesh (with its trusted balls); amb_noball on base_mesh if given
      balls, untrusted, base_mesh      -> base_mesh (ball-free)
      balls, untrusted, no base_mesh   -> unknown (amb_unknown): the ball-free shape is not available and the mesh
                                          with untrusted balls must not stand in for it (B5 round 2 fix)."""
    if row['balls'] == 0 and base is None:
        row['amb'] = row['amb_noball'] = self_ambiguity(mesh, kind)
        row['amb_source'] = 'shipped mesh (no balls)'
    elif trusted:
        row['amb'] = self_ambiguity(mesh, kind)
        row['amb_noball'] = self_ambiguity(base, kind) if base is not None else None
        row['amb_source'] = 'shipped mesh with its trusted balls'
    elif base is not None:
        row['amb'] = row['amb_noball'] = self_ambiguity(base, kind)
        row['amb_source'] = 'base_mesh (balls not trusted: ball-free)'
    else:
        row['amb'] = amb_unknown(kind, 'balls not trusted and no ball-free base_mesh supplied')
        row['amb_noball'] = None
        row['amb_source'] = 'unknown'
        row['flags'].append('amb_unknown_untrusted_balls_no_base')


def _fold_balls_missing(nballs, fm, fstate):
    """True when the shipped mesh has balls and a rebuilt fold mesh does not carry a markers.attach report of the
    same length (PREREG A.2: markers attached to every fold candidate alike; build_folds(post=...))."""
    if nballs == 0 or fstate == 'fixed':
        return False
    for m in fm:
        if len(getattr(m, 'faces', [])) == 0:
            continue                                         # 'partial': no candidate on that fold
        rep = _attach_report(m)
        if rep is None or len(rep) != nballs:
            return True
    return False


def _check_shell_args(cands, shell_cid, shell_fsv, t0_mm):
    """B5 round 3: a SHELL candidate that carries t_mm may be an A.1 t0-alternate (0.6 or 1.6 x t0); without
    shell_fsv, shell_cid or t0_mm the pool cannot tell, so t0_mm is required (raises before any scoring)."""
    if shell_fsv is not None or shell_cid is not None or t0_mm is not None:
        return
    tm = [_get(x, 'cid') for x in cands if _get(x, 'cls') == 'SHELL' and _get(x, 't_mm') is not None]
    if tm:
        raise ValueError(f'score_pool: SHELL candidates {sorted(map(str, tm))} carry t_mm and none of t0_mm, '
                         f'shell_cid, shell_fsv is given: pass t0_mm (the main run) or shell_fsv (A.1 t0-alternate '
                         f're-runs) so that an alternate shell cannot become the V3 reference')


def _shell_reference(rows, shell_cid, shell_fsv, t0_mm):
    """The reference s of V3 (PREREG A.3: the route-A shell at t0 of the same episode). shell_fsv (its fsv_far,
    measured in the main run) wins; else the row SHELL_CID; else the SHELL row whose t_mm is t0_mm; else the pool's
    only SHELL row, if it carries no t_mm (a SHELL row with t_mm and none of the three raises: _check_shell_args).
    Several SHELL rows and no way to tell which is at t0 raise (A.1 t0-alternate re-runs hold a shell at 0.6 or
    1.6 x t0: pass shell_fsv of the t0 shell). Returns (cid, fsv, source)."""
    if shell_fsv is not None:
        return shell_cid, float(shell_fsv), 'given shell_fsv'
    _check_shell_args(rows, shell_cid, shell_fsv, t0_mm)
    shells = [r for r in rows if r['cls'] == 'SHELL']
    if shell_cid is not None:
        r = next((r for r in rows if r['cid'] == shell_cid), None)
        if r is None or r['cls'] != 'SHELL':
            raise ValueError(f'score_pool: shell_cid {shell_cid!r} is not a SHELL candidate of the pool')
        return r['cid'], r['fsv_far'], 'shell_cid'
    if t0_mm is not None:
        at = [r for r in shells if r.get('t_mm') is not None and abs(float(r['t_mm']) - float(t0_mm)) <= 1e-3]
        if len(at) != 1:
            raise ValueError(f'score_pool: {len(at)} SHELL candidates at t0 = {t0_mm} mm (t_mm of the SHELL rows: '
                             f'{[r.get("t_mm") for r in shells]}); pass shell_cid or shell_fsv')
        return at[0]['cid'], at[0]['fsv_far'], f't_mm == t0_mm {t0_mm}'
    if len(shells) > 1:
        raise ValueError(f'score_pool: {len(shells)} SHELL candidates ({sorted(r["cid"] for r in shells)}) and no '
                         f'shell_cid, shell_fsv or t0_mm: the V3 reference (the shell at t0) is ambiguous')
    if shells:
        return shells[0]['cid'], shells[0]['fsv_far'], 'the only SHELL row'
    return None, None, 'none (no SHELL candidate; V3 diff undefined, no veto)'


def score_pool(cands, bundle, obj, *, K=None, folds=None, tau=None, shell_cid=None, shell_fsv=None, t0_mm=None,
               kind='kit', trusted=False, amb=True, flip_margin=False):
    """Every feature of one pool (PREREG A.2-A.4), rows ready for select.pick (pass the returned pool dict itself:
    pick then takes kit_symmetric and gen_view_overlap from it; every row also carries them under 'pool').

    cands: Candidate objects or dicts with cid, cls, n_params, mesh (all-frames, as shipped: packed, with every
    observed ball), and optionally base_mesh (the same without balls; Candidate.base_mesh), balls (count; a larger
    count in mesh.metadata['balls'], as markers.attach leaves it, is used too), t_mm, v1 (the packer's V1 dict on the
    packed file; else V1 is computed on the in-memory mesh and the row is flagged v1_in_memory: pass packed meshes
    and the packer's v1), gen_input_frames (GEN / FUSE: frames fed to the generator).
    folds: {cid: [c_1..c_K]} fold rebuilds (build_folds); a candidate without one is scored 'fixed'.
    tau: V3 threshold (None before B13: V3 reported, not applied). V3 reference s (the route-A shell at t0):
    shell_fsv (its fsv_far from the main run; for the A.1 t0-alternate re-runs), else shell_cid, else the SHELL row
    with t_mm == t0_mm, else the only SHELL row if it has no t_mm; several SHELL rows, or a SHELL row with t_mm, and
    none of the three raise (B5 round 3: the producers' SHELL carries t_mm, so pass t0_mm). kind: the kit symmetry
    ('kit' = look it up; an explicit value that contradicts the kit config raises). trusted: the object's balls
    passed the B.4 repeatability test. Self-ambiguity (V5, A.5 key 2) with trusted balls only: untrusted balls ->
    measured on base_mesh; untrusted balls and no base_mesh -> unknown (neither safe nor risky for V5, last on the
    flip key; row flag amb_unknown_untrusted_balls_no_base). A candidate with balls is one whose count (Candidate.balls
    or the markers.attach report in mesh.metadata['balls'], which pack.pack keeps) is > 0 or that has a base_mesh; a
    base_mesh with a count of 0 and no report raises. Folds: a shipped mesh with balls whose rebuilt fold meshes lack
    the same attach report is flagged fold_balls_missing (build_folds(post=...) attaches them).
    Every row carries the pool tag (obj, K, kit_symmetric, gen_view_overlap, flags), so select.pick on the rows alone
    sees what it sees on the pool dict."""
    c = consts()
    K = int(c['K'] if K is None else K)
    kit = kit_symmetry(obj)
    if kind == 'kit':
        kind = kit
    elif kind != kit:
        raise ValueError(f'score_pool: kind={kind!r} contradicts the kit config for {obj!r} ({kit!r}); pass '
                         f"kind='kit' (PREREG A.3: kit-symmetric objects skip V5)")
    cids = [_get(x, 'cid') for x in cands]
    if len(set(cids)) != len(cids):
        raise ValueError(f'score_pool: duplicate cids {sorted({str(c) for c in cids if cids.count(c) > 1})}')
    nb = {_get(x, 'cid'): _ball_count(x, _get(x, 'mesh')) for x in cands}   # input contract, before any scoring
    _check_shell_args(cands, shell_cid, shell_fsv, t0_mm)
    gen = [x for x in cands if _get(x, 'cls') in ('GEN', 'FUSE')]
    gviews = sorted({int(f) for x in gen for f in (_get(x, 'gen_input_frames') or [])})
    pool_flags = ['gen_input_frames_missing'] if any(not _get(x, 'gen_input_frames') for x in gen) else []
    pl = plan(bundle, obj, K, gen_views=gviews if gen else None)
    reps = bootstrap_reps(pl['blocks'])
    obs = bundle.obs(obj)
    far = far_free_grid(obs)
    s = bundle.sigma(obj)
    pool_tag = dict(obj=obj, K=K, kit_symmetric=kind is not None, gen_view_overlap=bool(pl['gen_view_overlap']))
    rows = []
    for x in cands:
        cid, mesh = _get(x, 'cid'), _get(x, 'mesh')
        fs = fsv_far(mesh, obs, far)
        fm, fstate = fold_meshes(mesh, (folds or {}).get(cid), K)
        ev = evidence(fm, bundle, obj, pl['blocks'], fs['fsv_far'] or 0.0)
        er = e_reps(ev, fs['fsv_far'] or 0.0, s, reps)
        flags = list(_get(x, 'flags', []) or [])
        v1r = _get(x, 'v1')
        if v1r is None:
            v1r = v1(mesh)
            v1r['source'] = 'in-memory mesh'
            flags.append('v1_in_memory')
        nballs, from_meta = nb[cid]
        if from_meta:
            flags.append('balls_count_from_mesh_metadata')
        if _fold_balls_missing(nballs, fm, fstate):
            flags.append('fold_balls_missing')
        t_mm = _get(x, 't_mm')
        row = dict(cid=cid, cls=_get(x, 'cls'), producer=_get(x, 'producer'), n_params=int(_get(x, 'n_params', 0)),
                   t_mm=None if t_mm is None else float(t_mm), balls=nballs, E=ev['E'], E_blocks=ev['R_blocks'],
                   E_se=float(np.nanstd(er)) if np.isfinite(er).any() else float('nan'), E_reps=er, ray=ev['ray'],
                   ray_blocks=ev['per_block'], fold=fstate, fsv_far=fs['fsv_far'], fsv_outside_grid=fs['outside_grid'],
                   v1=v1r, v2=v2(mesh, bundle, obj), v4=below_table(mesh, bundle, obj), flags=flags,
                   pool=dict(pool_tag))
        row['trusted_markers'] = row['balls'] if trusted else 0
        if amb:
            _amb_rows(row, mesh, _get(x, 'base_mesh'), kind, trusted)
        if flip_margin:
            row['obs_flip_margin'] = obs_flip_margin(mesh, obs, kind)
        rows.append(row)
    scid, fsv_s, s_src = _shell_reference(rows, shell_cid, shell_fsv, t0_mm)
    if fsv_s is None:
        pool_flags.append('v3_no_shell_reference')
    for r in rows:
        r['fsv_far_shell'] = fsv_s
        r['v3'] = v3(r['fsv_far'], fsv_s, tau)
        r['pool']['flags'] = list(pool_flags)
    return dict(obj=obj, K=K, kind=kind, kit_symmetric=kind is not None, trusted_balls=bool(trusted),
                gen_view_overlap=bool(pl['gen_view_overlap']), holdout=pl['holdout'], removed_frames=pl['removed'],
                blocks=[dict(frames=len(b['frames']), kept=len(b['kept']), points=int(len(b['idx'])),
                             L=block_length(len(b['kept'])) if b['kept'] else None) for b in pl['blocks']],
                shell_cid=scid, shell_fsv=fsv_s, shell_ref=s_src, tau=tau, rows=rows, plan=pl, flags=pool_flags)
