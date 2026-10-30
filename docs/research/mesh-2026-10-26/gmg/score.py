"""GT-free candidate features and vetoes (module M13 of SPEC section 7; minimal form for build step B1).

Frozen definitions: PREREG A.2-A.4. B1 implements the all-frames form (candidates are built once on all frames and
not rebuilt per block; the K = 3 held-out blocks define the held-out point sets and the bootstrap units, as in the X0
rule form of PREREG B.1). B5 adds the fold rebuilds, the generator view hold-out, self-ambiguity (V5) and the
observed flip margin.

  kit_decode(path) -> (v, f)            own copy of the kit packer's budget_mesh (v2dlb/mesh_budget.py) at 4096 faces
                                        and 4096 vertices: weld, simplify to both limits, pad (SPEC section 2: the gmg
                                        carries its own copy; scripts/mesh_metric.py is never imported)
  decoded_mesh(path) -> Trimesh         the decode with its zero-area padding rows dropped (as the kit's scorer sees it)
  v1(path) -> dict                      V1: watertight after the kit decode
  fsv_far(mesh, obs) -> dict            PREREG A.3: share of 20,000 area-weighted surface samples (seed 0) in FREE
                                        voxels with no OBSERVED voxel within 2 voxels (Chebyshev)
  heldout(obs, frames, K) -> blocks     PREREG A.2 blocks and held-out sets
  evidence(mesh, bundle, obj, blocks)   PREREG A.4 ray score on the held-out sets (all-frames candidate), per-frame
                                        sums for the moving-block bootstrap
  bootstrap_reps(blocks) / e_reps(...)  PREREG A.4: 200 replicates (seed 0) of contiguous runs of round(n_k^(1/3))
                                        frames inside each block, shared by all candidates (paired)
  v2(mesh, bundle, obj) -> dict         PREREG A.3 V2 (sample-based contact test, band b)
  v3(fsv_c, fsv_s, tau) -> dict         PREREG A.3 V3; tau is fitted at B13 (A.3), so in B1 V3 is reported and not
                                        applied (tau None)
  below_table(mesh, bundle, obj)        PREREG A.3 V4
"""
from __future__ import annotations

import numpy as np
import trimesh
from scipy import ndimage
from scipy.spatial import cKDTree

from gmg import contact as CT, geom, guard
from gmg.bundle import STATE_FREE, STATE_OBSERVED

KIT_FACES = KIT_VERTICES = 4096


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


# ------------------------------------------------------------------------------------------------ V1: kit decode
def kit_decode(path, faces=KIT_FACES, vertices=KIT_VERTICES):
    """Copy of the kit packer v2dlb/mesh_budget.budget_mesh (weld, simplify to both limits, pad to the exact row
    counts). Kept line for line; tests/test_score.py checks it against the kit file."""
    import fast_simplification
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


# ------------------------------------------------------------------------------------------------ held-out ray score
def heldout(bundle, obj):
    """PREREG A.2: the object's good frames in time order, split into K contiguous blocks of equal frame count
    (np.array_split); H_k = owned points of block k, at most one per 4 mm voxel per frame (random choice, seed 0),
    then at most 20,000 at random (seed 0). Returns [dict(frames, idx)] with idx into obs arrays."""
    c = consts()
    obs = bundle.obs(obj)
    good = bundle.good_frames(obj)
    fr = np.asarray(obs['frame'])
    own = np.asarray(obs['own']) == 0
    P = np.asarray(obs['pts'], np.float64)
    lo, vox = np.asarray(obs['lo'], np.float64), float(obs['vox'])
    rng = np.random.default_rng(int(c['seed']))
    blocks = []
    for bf in np.array_split(np.asarray(good), int(c['K'])):
        m = np.nonzero(np.isin(fr, bf) & own)[0]
        if len(m) == 0:
            blocks.append(dict(frames=[int(x) for x in bf], idx=np.zeros(0, np.int64)))
            continue
        perm = rng.permutation(len(m))
        mm = m[perm]
        key = np.concatenate([fr[mm, None].astype(np.int64), np.floor((P[mm] - lo) / vox).astype(np.int64)], 1)
        _, first = np.unique(key, axis=0, return_index=True)
        sel = mm[np.sort(first)]
        if len(sel) > int(c['heldout_max']):
            sel = rng.choice(sel, int(c['heldout_max']), replace=False)
        blocks.append(dict(frames=[int(x) for x in bf], idx=np.sort(sel)))
    return blocks


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
    tris = np.asarray(mesh.vertices, np.float64)[np.asarray(mesh.faces, np.int64)]
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


def evidence(mesh, bundle, obj, blocks, fsv):
    """PREREG A.4, all-frames form: R_k = mean cost / sigma over H_k; E = mean_k R_k + 10 fsv_far."""
    c = consts()
    s = bundle.sigma(obj)
    R, per_frame, n, miss, extra, raw = [], [], 0, 0, 0, []
    for bk in blocks:
        if len(bk['idx']) == 0:
            R.append(np.nan); per_frame.append({}); continue
        delta, cost, fr = ray_costs(mesh, bundle, obj, bk['idx'])
        R.append(float(cost.mean() / s))
        uf, inv = np.unique(fr, return_inverse=True)
        per_frame.append({int(f): (float(a), int(b)) for f, a, b in
                          zip(uf, np.bincount(inv, cost), np.bincount(inv))})
        n += len(cost)
        miss += int((delta > c['ray_band'] * s).sum())
        extra += int((delta < -c['ray_band'] * s).sum())
        raw.append(np.abs(delta[np.isfinite(delta)]))
    Rm = float(np.nanmean(R))
    allabs = np.concatenate(raw) if raw else np.zeros(0)
    return dict(E=Rm + c['fsv_w'] * fsv, R_blocks=[round(x, 5) for x in R], ray=dict(
        n=n, miss_frac=round(miss / max(n, 1), 5), extra_frac=round(extra / max(n, 1), 5),
        mean_cost_sigma=round(Rm, 5), median_abs_delta_mm=round(float(np.median(allabs)) * 1e3, 4) if len(allabs)
        else None), per_frame=per_frame)


def bootstrap_reps(blocks):
    """PREREG A.4: per replicate and block, the block's frames (those with held-out points) resampled as contiguous
    runs of L = max(1, round(n_k^(1/3))) frames with replacement, truncated to n_k. Shared by all candidates."""
    c = consts()
    rng = np.random.default_rng(int(c['seed']))
    reps = []
    for _ in range(int(c['n_boot'])):
        r = []
        for bk in blocks:
            fl = np.asarray(bk.get('frames_with_points', bk['frames']))
            nk = len(fl)
            if nk == 0:
                r.append(fl); continue
            L = max(1, int(round(nk ** (1 / 3))))
            starts = rng.integers(0, nk - L + 1, size=int(np.ceil(nk / L)))
            r.append(fl[(starts[:, None] + np.arange(L)[None]).ravel()[:nk]])
        reps.append(r)
    return reps


def e_reps(ev, fsv, sigma, reps):
    c = consts()
    out = np.empty(len(reps))
    for i, r in enumerate(reps):
        Rk = []
        for pf, fl in zip(ev['per_frame'], r):
            if not pf:
                continue
            a = sum(pf.get(int(f), (0.0, 0))[0] for f in fl)
            b = sum(pf.get(int(f), (0.0, 0))[1] for f in fl)
            Rk.append(a / max(b, 1) / sigma)
        out[i] = float(np.mean(Rk)) + c['fsv_w'] * fsv
    return out


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
