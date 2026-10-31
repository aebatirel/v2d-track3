"""Source (a) of the INTERLOCK stage: generator shape placed in our frame (INTERLOCK.md 3.1 and 7, PREREG F-I1.2,
F-I1.10; build step BI1).

  layout_consensus(runs, flips=())        consensus of per-view generator layouts (R, t, s) in the object frame:
                                          chordal L1 rotation mean (Weiszfeld on SO(3)) after aligning each run to the
                                          consensus modulo the mesh's flip set, geometric-median translation, median
                                          scale; outliers > 15 deg or > 10 mm flagged. For G1/G2 runs that save layouts.
  place_by_depth(mesh, b, obj)            placement used when no layout was saved (the 29 Oct runs): scale from our
                                          observed in-plane extents, rigid trimmed ICP to our observed samples from the
                                          4 PCA sign starts; the flip member is chosen by the depth residual, never by
                                          the slot side; margin < 1 sigma -> side unresolved
  solid_on(ev, mesh)                      the placed solid on the target's 2 mm sub-grid
  concavity(ev, mesh, r)                  notches = closing(S, r) - S; cavities = convex hull(S) - S (2 mm), with the
                                          4 mm voxel masks used by the cross-check
  remesh_survival(ev, mesh, notch, r)     share of the notch volume that survives a watertight remesh at 2 mm and the
                                          4000-face budget (M10 stand-in until B15's remesh exists)
  source_a(ev, mesh_placed, r, ...)       dict(C_a, survived, side_resolved, ...) for interlock.agree / offset

Generator inputs of 29 Oct (scratchpad gen/mesh-*) were made from crops seeded with library_v3: refused in clean mode
by the guard; read here only through the dev role x0_pool.
"""
from __future__ import annotations

import numpy as np
import trimesh
from scipy import ndimage
from scipy.spatial import cKDTree
from scipy.spatial.transform import Rotation as Rot

from gmg import guard, interlock as IL

C = dict(
    out_deg=(15.0, 'generic:F-I1.10 consensus outliers > 15 deg'),
    out_m=(0.010, 'generic:F-I1.10 consensus outliers > 10 mm'),
    notch_r_min=(0.006, 'generic:F-I1.2 closing radius max(6 mm, partner thickness)'),
    survive=(0.8, 'generic:F-I1.14 80 % remesh survival'),
    icp_iters=(40, 'generic:numerical ICP iterations'),
    icp_trim=(0.8, 'generic:numerical trimmed ICP share'),
    dec_faces=(40000, 'generic:numerical decimation of the raw generator mesh before voxelising'),
    margin_sigma=(1.0, 'generic:F-I1.2 flip separated by >= 1 sigma'),
)


def k_(n):
    v, o = C[n]
    guard.constant(f'gs.{n}', v, o)
    return v


def load_gen(path):
    """Dev only: a generator output of the 29 Oct batch (role x0_pool)."""
    rp = guard.open_input(path, 'x0_pool')
    m = trimesh.load(rp, force='mesh')
    return trimesh.Trimesh(np.asarray(m.vertices), np.asarray(m.faces), process=True)


def decimate(m, n):
    if len(m.faces) <= n:
        return m
    import fast_simplification
    v, f = fast_simplification.simplify(np.asarray(m.vertices, np.float32), np.asarray(m.faces, np.int32),
                                        target_reduction=1 - n / len(m.faces))
    return trimesh.Trimesh(v, f, process=True)


# ------------------------------------------------------------------------------------------------ consensus
def _chordal_l1(Rs, iters=50):
    """Weiszfeld iterations for the rotation minimising the sum of chordal distances (Hartley et al. 2011)."""
    R = Rot.from_matrix(np.mean(Rs, axis=0)).as_matrix() if len(Rs) else np.eye(3)
    U, _, Vt = np.linalg.svd(np.mean(Rs, axis=0)); R = U @ np.diag([1, 1, np.linalg.det(U @ Vt)]) @ Vt
    for _ in range(iters):
        d = np.array([np.linalg.norm(R - Q) for Q in Rs]) + 1e-9
        M = np.sum([Q / di for Q, di in zip(Rs, d)], axis=0) / np.sum(1 / d)
        U, _, Vt = np.linalg.svd(M); R = U @ np.diag([1, 1, np.linalg.det(U @ Vt)]) @ Vt
    return R


def _geomedian(X, iters=100):
    y = np.median(X, axis=0)
    for _ in range(iters):
        d = np.linalg.norm(X - y, axis=1) + 1e-12
        y = (X / d[:, None]).sum(0) / (1 / d).sum()
    return y


def layout_consensus(runs, flips=()):
    """runs: list of dict(R (3x3), t (3,), s) mapping the generated mesh into the object frame. flips: rotations G of
    the mesh's own flip set (x -> G x maps the mesh onto itself). Returns dict(R, t, s, outliers, aligned)."""
    Rs = [np.asarray(r['R'], float) for r in runs]
    G = [np.eye(3)] + [np.asarray(g, float) for g in flips]
    ref = Rs[0]
    for _ in range(3):
        al = []
        for R in Rs:
            cand = [R @ g for g in G]
            al.append(min(cand, key=lambda Q: np.linalg.norm(Q - ref)))
        ref = _chordal_l1(al)
    t = _geomedian(np.array([r['t'] for r in runs], float))
    s = float(np.median([r['s'] for r in runs]))
    out = []
    for i, (R, r) in enumerate(zip(al, runs)):
        ang = float(np.degrees(Rot.from_matrix(ref.T @ R).magnitude()))
        dt = float(np.linalg.norm(np.asarray(r['t']) - t))
        if ang > k_('out_deg') or dt > k_('out_m'):
            out.append(dict(run=i, deg=round(ang, 1), mm=round(dt * 1e3, 1)))
    return dict(R=ref, t=t, s=s, outliers=out, aligned=al)


# ------------------------------------------------------------------------------------------------ placement by depth
def _icp(src, tgt_tree, tgt, R, t, s, iters, trim, scale=False):
    for _ in range(iters):
        X = s * src @ R.T + t
        d, j = tgt_tree.query(X, k=1)
        k = d <= np.quantile(d, trim)
        A, B = src[k], tgt[j[k]]
        mA, mB = A.mean(0), B.mean(0)
        H = (A - mA).T @ (B - mB)
        U, S_, Vt = np.linalg.svd(H)
        D = np.diag([1, 1, np.sign(np.linalg.det(Vt.T @ U.T))])
        R = Vt.T @ D @ U.T
        if scale:
            s = float(np.trace(np.diag(S_) @ D) / ((A - mA) ** 2).sum())
        t = mB - s * R @ mA
    X = s * src @ R.T + t
    d, _ = tgt_tree.query(X, k=1)
    return R, t, s, d


def place_by_depth(mesh, b, obj, seed=0):
    """Scale + rigid fit of a generated mesh (any frame, any scale) to OBJ's observed samples (its frame).
    Returns dict(mesh placed, R, t, s, residual_mm per start, flip margin in sigma, side_resolved)."""
    P = b.samples(obj)[0]
    sig = b.sigma(obj)
    G = trimesh.sample.sample_surface(mesh, 20000, seed=seed)[0]
    cP, cG = P.mean(0), G.mean(0)
    UP = np.linalg.svd(P - cP, full_matrices=False)[2]; UG = np.linalg.svd(G - cG, full_matrices=False)[2]
    eP = np.percentile((P - cP) @ UP.T, 99, 0) - np.percentile((P - cP) @ UP.T, 1, 0)
    eG = np.percentile((G - cG) @ UG.T, 99, 0) - np.percentile((G - cG) @ UG.T, 1, 0)
    s0 = float(np.median([eP[0] / eG[0], eP[1] / eG[1]]))
    # icp from our points onto the generated surface (one-sided observations), via the inverse map
    treeG = cKDTree(G)
    res = []
    for sx in (1, -1):
        for sy in (1, -1):
            Sg = np.diag([sx, sy, sx * sy])
            R0 = UP.T @ Sg @ UG                      # gen axes -> our axes
            t0 = cP - s0 * R0 @ cG
            # inverse: our points into gen frame
            Ri, ti, si = R0.T, -R0.T @ t0 / s0, 1 / s0
            Ri, ti, si, d = _icp(P, treeG, G, Ri, ti, si, k_('icp_iters'), k_('icp_trim'), scale=True)
            k = d <= np.quantile(d, k_('icp_trim'))
            resid = float(d[k].mean()) / si          # in our metric units
            R = Ri.T; s = 1 / si; t = -R @ ti * s
            res.append(dict(R=R, t=t, s=s, resid=resid, start=(sx, sy)))
    res.sort(key=lambda r: r['resid'])
    best, second = res[0], res[1]
    margin = (second['resid'] - best['resid']) / max(sig, 1e-6)
    V = best['s'] * np.asarray(mesh.vertices) @ best['R'].T + best['t']
    placed = trimesh.Trimesh(V, np.asarray(mesh.faces), process=False)
    return dict(mesh=placed, R=best['R'], t=best['t'], s=best['s'],
                residual_mm=[round(r['resid'] * 1e3, 3) for r in res], margin_sigma=round(float(margin), 2),
                side_resolved=bool(margin >= k_('margin_sigma')), scale_init=round(s0, 5),
                extent_ours_mm=np.round(eP * 1e3, 1).tolist())


# ------------------------------------------------------------------------------------------------ concavity
def solid_on(ev, mesh):
    """Placed solid on ev's 2 mm sub-grid: surface voxels + fill (robust to small holes in raw generator meshes)."""
    g = ev.sgrid
    vg = mesh.voxelized(pitch=g.vox).fill()
    pts = vg.points
    l, ok = g.lin(pts)
    S = np.zeros(g.size, bool); S[l[ok]] = True
    S = ndimage.binary_fill_holes(S.reshape(g.shape))
    return S


def _ball(r_vox):
    r = int(np.ceil(r_vox))
    z, y, x = np.ogrid[-r:r + 1, -r:r + 1, -r:r + 1]
    return (x * x + y * y + z * z) <= r_vox * r_vox


def concavity(ev, S, r):
    """notches = closing(S, r) - S, cavities = convex hull(S) - S on the 2 mm sub-grid (bool grids)."""
    g = ev.sgrid
    rv = max(r / g.vox, 1.0)
    pad = int(np.ceil(rv)) + 1
    Sp = np.pad(S, pad)
    cl = ndimage.binary_closing(Sp, structure=_ball(rv))[pad:-pad, pad:-pad, pad:-pad]
    notch = cl & ~S
    cav = np.zeros_like(S)
    idx = np.argwhere(S)
    if len(idx) > 10:
        from scipy.spatial import ConvexHull
        try:
            eq = ConvexHull(idx.astype(np.float64)).equations
            box = np.argwhere(np.ones_like(S)).astype(np.float64)
            ins = np.ones(len(box), bool)
            for e in eq:                                   # half-space tests, facet by facet (fast, exact)
                ins &= box @ e[:3] + e[3] <= 1e-9
            cav = ins.reshape(S.shape) & ~S
        except Exception:
            pass
    return notch, cav


def to_vox4(ev, sub_mask):
    """4 mm voxel mask: a voxel is set if any of its 8 sub-voxels is."""
    g = ev.grid
    s = sub_mask.reshape([n * 2 for n in g.shape] if sub_mask.ndim == 1 else sub_mask.shape)
    s = s.reshape(g.shape[0], 2, g.shape[1], 2, g.shape[2], 2)
    return s.any(axis=(1, 3, 5)).ravel()


def remesh_survival(ev, mesh, notch, r):
    """Watertight remesh of the placed solid (marching cubes at 2 mm), 4000-face budget (autokit.program.fit_budget),
    re-voxelised; share of the notch volume still a notch."""
    from skimage import measure
    from autokit import program
    g = ev.sgrid
    S = solid_on(ev, mesh)
    v, f, _, _ = measure.marching_cubes(np.pad(S.astype(np.float32), 1), level=0.5)
    v = g.lo + (v - 1 + 0.5) * g.vox
    m = trimesh.Trimesh(v, f[:, ::-1], process=True)
    if m.is_watertight and m.volume < 0:
        m.invert()
    mb, _ = program.fit_budget(m, [], 4000)
    mb = trimesh.Trimesh(np.asarray(mb.vertices), np.asarray(mb.faces), process=True)
    S2 = IL.fast_inside(mb, g.centres()).reshape(g.shape) if mb.is_watertight else solid_on(ev, mb)
    n2, _ = concavity(ev, S2, r)
    share = float((n2 & notch).sum()) / max(int(notch.sum()), 1)
    return share, mb


def source_a(ev, placed, side_resolved, r, near_lin=None, kind='INSERTION', check_remesh=True):
    """Source (a) for one target: C_a on the 4 mm grid (notches for INSERTION/SLIDE, notches and cavities for SEAT),
    restricted later by interlock.agree to within 2 voxels of R_c; remesh survival of the notch near R_c."""
    S = solid_on(ev, placed)
    notch, cav = concavity(ev, S, r)
    sub = notch | cav if kind in ('SEAT', 'REST') else notch
    if near_lin is not None:
        near = IL.dilate(ev.grid, near_lin, int(np.ceil(0.020 / ev.grid.vox)))
        nsub = np.repeat(np.repeat(np.repeat(near.reshape(ev.grid.shape), 2, 0), 2, 1), 2, 2)
        sub = sub & nsub
    out = dict(C_a=to_vox4(ev, sub), C_a_sub=sub.ravel(), notch_cm3=round(float(notch.sum()) * ev.sgrid.vox ** 3 * 1e6, 2),
               cavity_cm3=round(float(cav.sum()) * ev.sgrid.vox ** 3 * 1e6, 2),
               near_cm3=round(float(sub.sum()) * ev.sgrid.vox ** 3 * 1e6, 2), side_resolved=bool(side_resolved),
               solid_cm3=round(float(S.sum()) * ev.sgrid.vox ** 3 * 1e6, 1), survived=True, flags=[])
    if not side_resolved:
        out['flags'].append('gen_side_unresolved')
    if check_remesh and sub.any():
        share, _ = remesh_survival(ev, placed, sub.reshape(S.shape), r)
        out['remesh_survival'] = round(share, 3)
        out['survived'] = share >= k_('survive')
        if not out['survived']:
            out['flags'].append('gen_slot_lost_in_remesh')
    return out
