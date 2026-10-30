"""Generic thin-shell mesh from ONE episode's observed points (autokit route A, no part vocabulary).

Observed surfaces -> denoised oriented surface samples (point-based directional TSDF) -> ONE open surface sheet ->
decimated to the face budget -> solidified into a closed thin shell of thickness t behind the observed face.
README section 6, P5 ("thin-wall fusion": directional TSDF, 1.5-2 mm voxels, 4-5 mm truncation, sub-voxel marching
cubes), done on the obs_points.py samples instead of depth images.

GT-free. Every function reads only the obs dict it is given: pts (N,3) object frame [m], cam (N,3) camera centre of
each point, frame (N,) frame index (scripts/obs_points.py output, loaded by autokit.io_gt, which refuses scan,
*_align, parquet and mocap paths). No object name and no per-object constant appears in this file: every constant
below is a sensor/resolution scale or a generic rule. Unseen thickness is the caller's t (generic grid 1.5 / 2.5 /
4.0 mm, a REQUIRED argument); a measured thickness replaces it only where both faces of a wall were observed.

Method (stage 1b; stage 1 marched a closed slab field at full resolution, which the kit's 4096-face budget_mesh then
tore: 0/24 watertight after decoding, area -1 to -22 %. Now the decimation happens here, on the OPEN sheet, before
solidifying, so budget_mesh only welds.)
 1. Normals, per frame. One depth map sees one side of a wall as ONE layer, so each frame's points -> VOX_N
    centroids, PCA over K_N_FRAME of them; every raw point takes its centroid's normal, turned towards its own camera
    (frames too small for that: pooled K_N fallback). Points whose own-frame neighbourhood is not planar
    (PLANAR_MIN) or that were seen at > 78 deg incidence (COS_GRAZE) are dropped.
 2. Directional fusion (DTSDF idea of Splietker & Behnke 2019 without bin edges): centroids keyed by voxel AND by the
    normal's dominant signed axis, projected onto their own side's local mean surface (implicit MLS, Kolluri 2008),
    merged on a VOXEL/2 grid: open, denoised, oriented samples.
 3. Thickness. From each sample s_j, step along -n_j up to D_MAX; the first opposite-facing sample within R_TAN of
    that line is the other face of the wall (its partner): measured thickness T_j (median over 8 nearest measured
    samples, floored at T_FLOOR). Elsewhere tau_j = t. Optional free-space clamp (carve=True, default off).
 4. One face per wall (resolve_sides). Where both faces were measured, the sheet keeps one of them (the master; patch
    by patch, the heavier observed side) and drops the other (the slave), so the master's measured T reaches the other
    face once instead of two coincident slabs.
 5. Open sheet (front_sheet). Every kept sample gets an internal slab of thickness T_FLOOR behind it; the union is
    marched at pitch 0.95 T_FLOOR / sqrt 3 (stage 1's closed field, continuous, so its surface is clean); its faces
    whose normal agrees with their own slab's normal and that lie in the slab's front half are the observed-side
    faces: an open, oriented sheet whose border is the edge of the observed surface. Holes with a perimeter
    <= HOLE_FILL_LEN are fan-filled (sampling gaps). (A one-sided signed field marched directly left closed bubbles.)
 6. Islands (island_filter). Components are grouped when they come within TOUCH (2 mm, chains allowed; with
    ISLAND_UNION, default off, also when they belong to one body of the step-5 slab union); the group of the largest
    component is the body. Any other group survives
    only if it is ball-like (convex hull sphericity >= BALL_SPHER, hull diameter <= BALL_D; the hull, because a
    single episode sees a ball as a cap; plus a least-squares sphere check) AND has frame support, area >= A_MIN and
    lies within NEAR of the body. Body-group pieces smaller than A_MIN_BODY are dropped as noise. Dropped area is
    reported per reason (dropped_by_reason_cm2).
 7. Budget (decimate_sheet). The open sheet is decimated (fast_simplification quadrics) to the face budget with a
    temporary SKIRT along its border: the skirt's faces act as boundary-constraint planes, so border vertices can only
    slide along the border, and the skirt is removed afterwards (its faces are exactly those that touch the
    decimator's border vertices). Clean-up (manifold_clean) removes only degenerate faces and collapsed fins; every
    other non-manifold configuration is cut instead of deleted (manifold_split: non-manifold edges unzipped, bow-tie
    vertices split into one copy per fan, copies nudged SPLIT_NUDGE into their fan so the kit's weld cannot re-join
    them). Coarse passes divide the face count by DEC_STEP, then a bisection on the target lands within 5 % under the
    budget. Only pieces < A_SPECK (1 mm^2) are dropped afterwards.
 8. Solidify (solidify). Back sheet = front sheet moved by tau along -vertex normal (even-thickness scaling), rim
    quads on every border edge: closed and consistently wound by construction, with 2 * (faces + border edges) faces.
    (rim='taper' shares the border vertices instead and needs no rim faces, but edges joining two border vertices
    must be split first; measured on four dev sheets it gave no coverage gain at equal face count, so 'quad' is the
    default.) The total stays <= max_faces (default 4000 < 4096), so the kit's budget_mesh only welds it.

Usage (library):
    from autokit.io_gt import load_obs, obs_path
    from autokit.shell import thin_shell, shell_sheet, solidify_sheet, surface_patch
    mesh = thin_shell(load_obs(obs_path(OBJ, EP)), t=0.0025)               # closed, <= 4000 faces
    sh = shell_sheet(obs); meshes = [solidify_sheet(sh, t) for t in (0.0015, 0.0025, 0.004)]   # one sheet, t grid
    patch = surface_patch(obs, idx, t=0.0025, max_faces=1500, host=union_of_parts)            # part-program use
CLI:
    shell.py OBJ EP OUT.glb --t 0.0025 [--voxel 0.002] [--mode oriented|symmetric] [--refined 0|1|auto]
             [--no_two_sided] [--carve] [--max_faces 4000]
    --refined defaults to 0 (raw points): refine.py's copies are not trusted yet (stage-1 audit).
"""
import json, math, os, sys, time

import numpy as np
import trimesh
from scipy import ndimage
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import connected_components
from scipy.spatial import cKDTree, ConvexHull

# ---------------------------------------------------------------------------------------------- declared constants
VOXEL = 0.002            # fusion voxel (m); samples are merged on a VOXEL/2 grid
VOX_N = 0.0015           # per-frame normals: points of one frame -> 1.5 mm centroids ...
K_N_FRAME = 24           # ... PCA over 24 of them (~4 mm radius on a single depth layer)
K_N = 96                 # fallback for tiny frames: pooled VOXEL centroids, ~7 mm radius (pooled clouds are thick)
PLANAR_MIN = 0.3         # points whose own-frame neighbourhood is not planar (edges, specks, depth junk) are dropped
COS_GRAZE = 0.2          # points seen at > 78 deg incidence are dropped: their depth is the noisiest and their
                         # normal's side is ambiguous
COS_BIN = 0.5            # two-sided search: candidates for the other face have n . (-axis) > cos 60 deg
SIGMA = 0.002            # MLS window: Gaussian in the TANGENTIAL distance (m), a tube around the query's normal line
TRUNC = 0.005            # ... cut at +-TRUNC along the normal (m) = TSDF truncation band (P5: 4-5 mm)
K_MLS = 128              # MLS neighbours per query (ball of TRUNC + SIGMA holds the tube segment)
COS_SIM = 0.7            # MLS / side patches: neighbours whose normal is within 45 deg of the query's
MLS_ITERS = 3
MIN_NB = 6               # a sample needs >= MIN_NB MLS neighbours (isolated specks are dropped)
D_MAX = 0.010            # two-sided search depth (m) = 2 x TRUNC
R_TAN = 0.0015           # two-sided: the other face must lie within this of the inward normal line (m)
COS_OPP = 0.7            # two-sided: the other face's normal within 45 deg of -n
T_FLOOR = 0.0015         # floor of a measured or carved thickness (m) = the smallest generic grid value
CARVE_RAYS = 1500000     # free-space clamp: at most this many rays (raw points, random subset)
CARVE_EPS = 0.001        # ... a ray is free from CARVE_EPS in front of its (denoised) surface point ...
CARVE_STEP = 0.0005      # ... sampled every CARVE_STEP ...
CARVE_R = 0.0005         # ... a slab point is free if a free sample lies within CARVE_R ...
CARVE_MIN_FRAMES = 3     # ... seen free in >= 3 distinct frames (one mis-tracked frame cannot carve)
R_DISK_FRAC = 0.75       # disc radius as a fraction of VOXEL (samples merged on a VOXEL/2 grid; discs overlap)
SIDE_LINK_FRAC = 1.5     # resolve_sides: two-sided samples within 1.5 VOXEL (and COS_SIM) form one patch
COS_FRONT = 0.5          # front sheet: a slab-union face is on the observed side if its normal is within 60 deg
F_MIN_FRAC, F_MIN_ABS = 0.05, 5   # island support: frames that saw it
A_MIN = 5e-5             # island area floor (m^2) = 0.5 cm^2: smaller groups are dropped (noise, generic)
A_MIN_BODY = A_MIN       # pieces touching the body (TOUCH chain) but smaller than this are dropped as noise; each
                         # kept piece costs closed faces. Measured on two public dev episodes at t 2.5 mm, floor 0.5 /
                         # 0.1 / 0.02 cm^2: kept sheet +0 / +4 / +5 %, GT-free fidelity sum 1.330 / 1.345 / 1.357 and
                         # 1.527 / 1.533 / 1.539 mm (lower is better), so the floor stays at A_MIN
A_SPECK = 1e-6           # after decimation only pieces < 1 mm^2 are dropped. The pieces between 1 mm^2 and A_MIN are
                         # mostly bits of the main sheet cut off at unzipped edges; dropping them at A_MIN (first
                         # stage-1b version) measured dense->decimated share > 3 mm 1.75 / 1.68 / 3.46 % on three
                         # public dev episodes, against 0.06 / 0.01 / 1.85 % when kept (stage-1b shell report)
NEAR = 0.03              # a ball-like island farther than this from the body is dropped (m)
TOUCH = 0.002            # components whose surfaces come within TOUCH form one group (m)
BALL_SPHER = 0.8         # ball-like island: convex-hull sphericity pi^(1/3) (6V)^(2/3) / A >= BALL_SPHER ...
BALL_D = 0.030           # ... and convex-hull diameter <= BALL_D (m): small compact separate rigid feature ...
BALL_FIT_RMS = 0.2       # ... and curved like a ball: a least-squares sphere with radius <= the hull diameter and
                         # rms residual <= 0.2 radius (a few-mm flat speck has a near-ball hull because the sheet's
                         # rim rounding dominates it; measured on the synthetic island test: hull sphericity 0.85)
SKIRT_H_FRAC = 2.0       # decimation skirt height = 2 VOXEL (only its orientation matters to the quadrics)
DEC_AGG = 3              # fast_simplification aggressiveness (7 = default). Measured on two dev sheets with the
                         # bisection target: 3 / 4 / 6 -> sheet area change -12.0 / -16.7 / -20.5 % and -1.8 / -2.0 /
                         # -4.6 %; dense-to-decimated p95 3.30 / 5.16 / 5.66 mm and 0.44 / 0.43 / 0.68 mm
DEC_STEP = 4             # coarse decimation passes divide the face count by this
DEC_REFILL_EDGES = 12    # holes the decimation clean-up opens (<= 12 border edges) are fan-filled again
HOLE_FILL_LEN = 0.02     # dense sheet: holes with a perimeter <= 20 mm (~6 mm across, a few voxels) are sampling
                         # gaps of the fused surface, not openings of the object; they are fan-filled
EVEN_COS_MIN = 0.5       # solidify: even-thickness scaling 1 / mean(n_v . n_f), capped at 2x
ISLAND_UNION = False     # island rule: False = literal rule (a piece joins the body only within TOUCH, chains allowed);
                         # True also joins pieces of one slab-union body (connected through the 1.5 mm slab solid).
                         # Measured kept area with True on six public dev episodes: +0.0 on four, +0.4 % and +1.6 %
                         # on the two largest sheets (stage-1b shell report)
HOST_TRIM_FRAC = 2.0     # surface_patch: keep sheet parts > 2 VOXEL outside the host
HOST_ATTACH = True       # surface_patch (stage-1b integration): border vertices within the island rule's host reach
                         # whose move is supported by observed points go onto the host surface (_host_attach), so an
                         # attached patch touches its host (the residual cut / trim otherwise leaves a 2-4 mm gap >
                         # the gates' TOUCH 2 mm, and G_CONN saw a separate body)
PATCH_MIN_PTS = 200      # surface_patch: fewer residual points than this -> empty patch
MERGE_TOL = 1e-6         # vertices closer than 1 um are merged (the decimator can leave sub-um clusters)
SPLIT_NUDGE = 2e-5       # manifold_split: copies of a split vertex move 20 um into their own fan (>> float32 GLB
                         # resolution ~3e-8 m at 0.3 m, << any geometric scale): the kit's exact weld keeps them apart
RIM = 'quad'             # solidify rim: 'quad' (rim quads, 2 (F + B) faces) or 'taper' (shared border, 2 F faces)
MAX_FACES = 4000         # closed output face budget (< the kit's 4096, so budget_mesh only welds)
AXES = np.array([[1, 0, 0], [-1, 0, 0], [0, 1, 0], [0, -1, 0], [0, 0, 1], [0, 0, -1]], float)


# ---------------------------------------------------------------------------------------------- helpers
def _unit(v):
    return v / np.maximum(np.linalg.norm(v, axis=-1, keepdims=True), 1e-12)


def _voxel_groups(P, vox, extra_key=None):
    """Group points by voxel (and an optional integer key): (inverse index, number of groups)."""
    lo = P.min(0)
    I = np.floor((P - lo) / vox).astype(np.int64)
    dims = I.max(0) + 1
    lin = (I[:, 0] * dims[1] + I[:, 1]) * dims[2] + I[:, 2]
    if extra_key is not None:
        lin = lin + extra_key.astype(np.int64) * int(np.prod(dims))
    _, inv = np.unique(lin, return_inverse=True)
    return inv.ravel(), int(inv.max()) + 1


def _group_mean(inv, n, X, w=None):
    w = np.ones(len(inv)) if w is None else w
    sw = np.bincount(inv, w, minlength=n)
    return np.stack([np.bincount(inv, w * X[:, k], minlength=n) for k in range(X.shape[1])], 1) / sw[:, None], sw


def _chunks(n, size):
    for a in range(0, n, size):
        yield slice(a, min(n, a + size))


def _empty():
    return trimesh.Trimesh(np.zeros((0, 3)), np.zeros((0, 3), np.int64), process=False)


def _components(m):
    """Edge-connected components of m as separate meshes: an exact partition of its faces. (trimesh's split() returned
    3 faces twice on one decimated dev sheet, 1210 -> 1213 faces.)"""
    if len(m.faces) == 0:
        return []
    lab = trimesh.graph.connected_component_labels(m.face_adjacency, node_count=len(m.faces))
    V, F = np.asarray(m.vertices), np.asarray(m.faces)
    order = np.argsort(lab, kind='stable')
    out = []
    for fi in np.split(order, np.flatnonzero(np.diff(lab[order])) + 1):
        u, inv = np.unique(F[fi], return_inverse=True)
        out.append(trimesh.Trimesh(V[u], inv.reshape(-1, 3), process=False))
    return out


# ---------------------------------------------------------------------------------------------- 1. normals
def _pca_normals(Cv, k):
    """Unsigned PCA normal and planarity (1 - l0/l1) of each point over its k nearest neighbours."""
    tree = cKDTree(Cv); k = min(k, len(Cv))
    nrm = np.zeros((len(Cv), 3)); pl = np.zeros(len(Cv))
    for s in _chunks(len(Cv), 100000):
        _, nb = tree.query(Cv[s], k=k, workers=2)
        Q = Cv[nb] - Cv[nb].mean(1, keepdims=True)
        w, V = np.linalg.eigh(np.einsum('nki,nkj->nij', Q, Q) / k)
        nrm[s] = V[:, :, 0]; pl[s] = 1 - w[:, 0] / np.maximum(w[:, 1], 1e-12)
    return nrm, pl


def point_normals(P, C, F, vox):
    """Per raw point: unit normal oriented towards its own camera, and planarity.
    Per frame (one depth map sees one side of a wall as ONE layer, so its local PCA is sharp): the frame's points ->
    VOX_N centroids, PCA over K_N_FRAME neighbours. Frames too small for that use the pooled cloud (K_N centroids at
    vox, which is thick where two faces overlap)."""
    n = np.zeros_like(P); planar = np.zeros(len(P))
    order = np.argsort(F, kind='stable'); Fs = F[order]
    cuts = np.flatnonzero(np.diff(Fs)) + 1
    small = []
    for idx in np.split(order, cuts):
        if len(idx) < 4 * K_N_FRAME:
            small.append(idx); continue
        inv, nv = _voxel_groups(P[idx], VOX_N)
        if nv < 2 * K_N_FRAME:
            small.append(idx); continue
        Cv, _ = _group_mean(inv, nv, P[idx])
        nrm, pl = _pca_normals(Cv, K_N_FRAME)
        n[idx] = nrm[inv]; planar[idx] = pl[inv]
    if small:
        idx = np.concatenate(small)
        if len(idx) >= 4:
            inv, nv = _voxel_groups(P[idx], vox)
            Cv, _ = _group_mean(inv, nv, P[idx])
            if nv >= 4:
                nrm, pl = _pca_normals(Cv, K_N)
                n[idx] = nrm[inv]; planar[idx] = pl[inv]
    view = _unit(C - P)
    n[np.einsum('ni,ni->n', n, view) < 0] *= -1
    return n, planar


# ---------------------------------------------------------------------------------------------- 2. directional fusion
def _mls_project(Cb, Nb, Wb, iters=MLS_ITERS):
    """Project centroids onto their local mean surface: per query, the weighted mean signed offset of the same-side
    centroids in a tube (tangential Gaussian SIGMA, |offset| < TRUNC) around its normal line - the TSDF zero
    crossing along that line. Returns projected positions, normals, neighbour counts."""
    tree = cKDTree(Cb)
    q = Cb.copy(); nq = Nb.copy(); cnt = np.zeros(len(Cb), int)
    k = min(K_MLS, len(Cb))
    for it in range(iters):
        for s in _chunks(len(Cb), 40000):
            d, nb = tree.query(q[s], k=k, distance_upper_bound=TRUNC + SIGMA, workers=2)
            if nb.ndim == 1:
                d, nb = d[:, None], nb[:, None]
            ok = nb < len(Cb); nb = np.where(ok, nb, 0)
            sim = np.einsum('nkj,nj->nk', Nb[nb], nq[s]) > COS_SIM
            v = q[s][:, None, :] - Cb[nb]
            a = np.einsum('nkj,nj->nk', v, nq[s])                       # offset along the current normal
            tan2 = np.maximum(np.einsum('nkj,nkj->nk', v, v) - a * a, 0)
            g = np.where(ok & sim & (np.abs(a) < TRUNC), Wb[nb] * np.exp(-0.5 * tan2 / SIGMA ** 2), 0.0)
            sg = g.sum(1); good = sg > 0
            nbar = _unit(np.einsum('nk,nkj->nj', g, Nb[nb]))
            a = np.einsum('nkj,nj->nk', v, nbar)
            phi = np.einsum('nk,nk->n', g, a) / np.maximum(sg, 1e-12)
            q[s][good] -= phi[good, None] * nbar[good]
            nq[s][good] = nbar[good]
            cnt[s] = (g > 0).sum(1)
    return q, nq, cnt


def directional_samples(P, n, vox):
    """Oriented, denoised surface samples from raw points + normals: dict s, n, w, bin.
    Centroids are keyed by voxel AND by the normal's dominant signed axis (6 bins), so the two faces of a thin wall
    never merge into one centroid. The MLS projection then runs over all centroids at once, each query averaging only
    neighbours whose normal is within 45 deg of its own (COS_SIM)."""
    b0 = np.argmax(n @ AXES.T, 1)
    inv, ng = _voxel_groups(P, vox, extra_key=b0)
    Cb, Wb = _group_mean(inv, ng, P)
    Nb, _ = _group_mean(inv, ng, n); Nb = _unit(Nb)
    q, nq, cnt = _mls_project(Cb, Nb, Wb)
    keep = cnt >= MIN_NB
    if keep.sum() == 0:
        return dict(s=np.zeros((0, 3)), n=np.zeros((0, 3)), w=np.zeros(0), bin=np.zeros(0, int))
    # merge the collapsed layers on a VOXEL/2 grid (again keyed by the dominant axis of the normal)
    b1 = np.argmax(nq[keep] @ AXES.T, 1)
    inv2, n2 = _voxel_groups(q[keep], vox / 2, extra_key=b1)
    s2, w2 = _group_mean(inv2, n2, q[keep], Wb[keep])
    n2v, _ = _group_mean(inv2, n2, nq[keep], Wb[keep])
    n2v = _unit(n2v)
    return dict(s=s2, n=n2v, w=w2, bin=np.argmax(n2v @ AXES.T, 1))


# ---------------------------------------------------------------------------------------------- 3. two-sided thickness
def two_sided_thickness(S, N, return_partner=False):
    """Measured wall thickness per sample (NaN where the other face was not observed); with return_partner also the
    index of the other-face sample that was hit (-1 where none)."""
    T = np.full(len(S), np.nan); partner = np.full(len(S), -1, np.int64)
    prim = np.argmax(N @ AXES.T, 1)
    opp = {0: 1, 1: 0, 2: 3, 3: 2, 4: 5, 5: 4}
    for b in range(6):
        mine = np.nonzero(prim == b)[0]
        cand = np.nonzero(N @ AXES[opp[b]] > COS_BIN)[0]
        if len(mine) == 0 or len(cand) < 10:
            continue
        tree = cKDTree(S[cand]); todo = mine.copy()
        for delta in np.arange(-R_TAN, D_MAX + 1e-9, R_TAN / 1.5):
            if len(todo) == 0:
                break
            q = S[todo] - delta * N[todo]
            d, j = tree.query(q, k=1, distance_upper_bound=R_TAN, workers=2)
            hit = j < len(cand)
            jj = cand[np.where(hit, j, 0)]
            hit &= np.einsum('ij,ij->i', N[jj], N[todo]) < -COS_OPP
            depth = np.einsum('ij,ij->i', S[todo] - S[jj], N[todo])
            hit &= depth > -R_TAN
            T[todo[hit]] = depth[hit]; partner[todo[hit]] = jj[hit]
            todo = todo[~hit]
    meas = np.nonzero(np.isfinite(T))[0]
    if len(meas) >= 8:                                  # median over the 8 nearest measured samples
        _, nb = cKDTree(S[meas]).query(S[meas], k=8, workers=2)
        T[meas] = np.median(T[meas][nb], 1)
    T[meas] = np.clip(T[meas], T_FLOOR, D_MAX)
    return (T, partner) if return_partner else T


def resolve_sides(S, N, W, T, partner, vox):
    """One face per measured wall. Two-sided samples form patches (within SIDE_LINK_FRAC * vox, normals within 45
    deg); a patch's partner patch is the most common patch of its samples' partners. Patches are visited by
    decreasing observed weight: a patch whose partner patch is already a master becomes a slave, otherwise it becomes
    a master (and its partner patch a slave). Samples hit as the partner of a master sample are slaves too, unless
    they are masters themselves. A slave whose own partner is not kept is restored (so no wall vanishes).
    Returns (slave mask, info)."""
    meas = np.flatnonzero(np.isfinite(T))
    slave = np.zeros(len(S), bool)
    info = dict(two_sided_samples=int(len(meas)))
    if len(meas) < 2:
        return slave, info
    pairs = cKDTree(S[meas]).query_pairs(SIDE_LINK_FRAC * vox, output_type='ndarray')
    if len(pairs):
        pairs = pairs[np.einsum('ij,ij->i', N[meas[pairs[:, 0]]], N[meas[pairs[:, 1]]]) > COS_SIM]
    G = coo_matrix((np.ones(len(pairs)), (pairs[:, 0], pairs[:, 1])), shape=(len(meas), len(meas))) if len(pairs) \
        else coo_matrix((len(meas), len(meas)))
    nc, lab = connected_components(G, directed=False)
    comp = np.full(len(S), -1, np.int64); comp[meas] = lab
    pc = np.where(partner[meas] >= 0, comp[np.maximum(partner[meas], 0)], -1)
    Wc = np.bincount(lab, W[meas], minlength=nc)
    ppatch = np.full(nc, -1, np.int64)
    okp = pc >= 0
    if okp.any():
        key = lab[okp] * (nc + 1) + pc[okp]
        u, cnt = np.unique(key, return_counts=True)
        a, b = u // (nc + 1), u % (nc + 1)
        order = np.lexsort((-cnt, a))                    # per patch a, the most common partner patch first
        first = np.ones(len(order), bool); first[1:] = a[order][1:] != a[order][:-1]
        ppatch[a[order][first]] = b[order][first]
    role = np.zeros(nc, np.int8)                          # 0 undecided, 1 master, 2 slave
    for c in np.argsort(-Wc):
        if role[c]:
            continue
        p = ppatch[c]
        if p >= 0 and p != c and role[p] == 1:
            role[c] = 2
        else:
            role[c] = 1
            if p >= 0 and p != c and role[p] == 0:
                role[p] = 2
    master = np.zeros(len(S), bool); master[meas] = role[lab] == 1
    slave[meas] = role[lab] == 2
    pm = partner[master]; pm = pm[pm >= 0]
    slave[pm[~master[pm]]] = True
    # a slave whose partner is not a kept sample would leave its wall unrepresented: restore it
    sl = np.flatnonzero(slave)
    lost = sl[(partner[sl] < 0) | slave[np.maximum(partner[sl], 0)]]
    slave[lost] = False
    kept_meas = meas[~slave[meas]]
    dup = int(np.sum((partner[kept_meas] >= 0) & ~slave[np.maximum(partner[kept_meas], 0)]
                     & np.isfinite(T[np.maximum(partner[kept_meas], 0)])))
    info.update(side_patches=int(nc), master_samples=int(master.sum()), slave_samples=int(slave.sum()),
                restored_samples=int(len(lost)), kept_pairs_both_sides=dup)
    return slave, info


def free_space_clamp(P, C, F, n, S, N, tau, depth_max):
    """Shrink each sample's slab where our own rays saw through the material behind it.
    Every ray (raw point p, camera c) is moved along itself onto its own side's denoised surface (nearest sample with
    a similar normal), then sampled from CARVE_EPS to depth_max + CARVE_EPS in front of that point: free space.
    Free samples are kept where >= CARVE_MIN_FRAMES distinct frames agree. For each surface sample s_j, the first depth
    d along -n_j with a free sample within CARVE_R caps its thickness: tau_j <= max(T_FLOOR, d - CARVE_R).
    Returns (tau, info)."""
    rng = np.random.default_rng(0)
    sub = rng.choice(len(P), min(len(P), CARVE_RAYS), replace=False)
    Pr, Cr, Fr, nr = P[sub], C[sub], F[sub], n[sub]
    tree = cKDTree(S)
    _, j = tree.query(Pr, k=4, workers=2)
    sim = np.einsum('nkj,nj->nk', N[j], nr)
    best = j[np.arange(len(j)), np.argmax(sim, 1)]
    ok = sim.max(1) > COS_SIM
    r = _unit(Cr - Pr); ns = N[best]
    cosr = np.einsum('ij,ij->i', ns, r)
    ok &= cosr > COS_GRAZE
    lam = -np.einsum('ij,ij->i', ns, Pr - S[best]) / np.maximum(cosr, 1e-6)
    ok &= np.abs(lam) < TRUNC
    Ps = Pr[ok] + lam[ok, None] * r[ok]; r = r[ok]; Fr = Fr[ok]
    steps = np.arange(CARVE_EPS, depth_max + CARVE_EPS + 1e-9, CARVE_STEP)
    Q = (Ps[:, None, :] + steps[None, :, None] * r[:, None, :]).reshape(-1, 3)
    Fq = np.repeat(Fr, len(steps))
    lo = Q.min(0)
    I = np.floor((Q - lo) / CARVE_R).astype(np.int64); dims = I.max(0) + 1
    lin = (I[:, 0] * dims[1] + I[:, 1]) * dims[2] + I[:, 2]
    pair = np.unique(np.stack([lin, Fq.astype(np.int64)], 1), axis=0)
    vox, cnt = np.unique(pair[:, 0], return_counts=True)
    vox = vox[cnt >= CARVE_MIN_FRAMES]
    info = dict(carve_rays=int(ok.sum()), carve_free_cells=int(len(vox)))
    if len(vox) == 0:
        info['carve_clamped_frac'] = 0.0
        return tau, info
    iz = vox % dims[2]; iy = (vox // dims[2]) % dims[1]; ix = vox // (dims[1] * dims[2])
    Xf = (np.stack([ix, iy, iz], 1) + 0.5) * CARVE_R + lo
    tf = cKDTree(Xf)
    tau = tau.copy(); todo = np.arange(len(S)); clamped = np.zeros(len(S), bool)
    for d in np.arange(CARVE_STEP, depth_max + 1e-9, CARVE_STEP):
        todo = todo[tau[todo] > d]
        if len(todo) == 0:
            break
        dist, _ = tf.query(S[todo] - d * N[todo], k=1, distance_upper_bound=CARVE_R, workers=2)
        hit = np.isfinite(dist)
        tau[todo[hit]] = np.maximum(T_FLOOR, d - CARVE_R)
        clamped[todo[hit]] = True
        todo = todo[~hit]
    info['carve_clamped_frac'] = round(float(clamped.mean()), 3)
    if clamped.any():
        info['carve_tau_mm_p10_50_90'] = np.round(np.percentile(tau[clamped], [10, 50, 90]) * 1e3, 2).tolist()
    return tau, info


# ---------------------------------------------------------------------------------------------- 5. front sheet
def shell_field(S, N, tau, offset, rdisk, pitch):
    """Narrow-band grid of U(x) = min_j [dist(x, disc_j) - tau_j/2], disc_j centred at s_j - offset_j n_j; +pitch*4
    outside the band. Continuous (a minimum of distances), so its zero set is a clean closed surface."""
    Cc = S - offset[:, None] * N
    reach = float(tau.max()) / 2 + rdisk + 3 * pitch
    lo = Cc.min(0) - reach - 2 * pitch
    dims = np.ceil((Cc.max(0) + reach + 2 * pitch - lo) / pitch).astype(int) + 1
    occ = np.zeros(dims, bool)
    I = np.floor((Cc - lo) / pitch).astype(int); occ[tuple(I.T)] = True
    occ = ndimage.binary_dilation(occ, structure=np.ones((3, 3, 3), bool), iterations=int(math.ceil(reach / pitch)))
    band = np.nonzero(occ.ravel())[0]
    del occ
    X = np.stack(np.unravel_index(band, dims), 1) * pitch + lo
    U = np.full(int(np.prod(dims)), 4 * pitch, np.float32)
    tree = cKDTree(Cc); k = min(8, len(Cc))
    for s in _chunks(len(band), 400000):
        d, j = tree.query(X[s], k=k, workers=2)
        if j.ndim == 1:
            j = j[:, None]
        v = X[s][:, None, :] - Cc[j]
        a = np.einsum('nkj,nkj->nk', v, N[j])
        tl = np.sqrt(np.maximum(np.einsum('nkj,nkj->nk', v, v) - a * a, 0))
        e = np.maximum(tl - rdisk, 0)
        U[band[s]] = np.minimum(np.min(np.sqrt(a * a + e * e) - tau[j] / 2, 1), 4 * pitch)
    return U.reshape(dims), lo, int(len(band))


def march(U, lo, pitch):
    from skimage import measure
    V, F, _, _ = measure.marching_cubes(U, level=0.0, spacing=(pitch,) * 3, method='lewiner', allow_degenerate=False)
    m = trimesh.Trimesh(V + lo, F, process=True)
    if m.volume < 0:
        m.invert()
    return m


def front_sheet(S, N, rdisk, voxel):
    """Open oriented sheet = the observed-side faces of a closed union of thin slabs. Every sample gets an internal
    slab of thickness T_FLOOR behind it (oriented, as stage 1's shell at t = 1.5 mm); the union is marched at pitch
    0.95 T_FLOOR / sqrt 3 (no slab can tear); a face of it is FRONT when its normal is within COS_FRONT of its own
    slab's normal (the sample whose slab defines U there) and it lies in the front half of that slab. Front faces
    form the sheet; back faces, rims and the inside of thin tubes are dropped. (A one-sided signed field marched
    directly left closed bubbles where the nearest disc switched between strongly curved, noisy samples:
    measured on a dev cloud, 11 % of the sheet area > 2 mm from the slab-union surface.) Returns (sheet, info)."""
    if len(S) < 4:
        return _empty(), dict(sheet_faces_mc=0)
    tau = np.full(len(S), T_FLOOR)
    pitch = 0.95 * T_FLOOR / math.sqrt(3)
    U, lo, nband = shell_field(S, N, tau, tau / 2, rdisk, pitch)
    try:
        closed = march(U, lo, pitch)
    except (ValueError, RuntimeError):
        return _empty(), dict(sheet_faces_mc=0, band_voxels=nband)
    del U
    X = closed.triangles_center
    Cc = S - (tau / 2)[:, None] * N
    tree = cKDTree(Cc); k = min(8, len(S))
    jj = np.zeros(len(X), np.int64)
    for s in _chunks(len(X), 300000):
        _, j = tree.query(X[s], k=k, workers=2)
        if j.ndim == 1:
            j = j[:, None]
        v = X[s][:, None, :] - Cc[j]
        a = np.einsum('nkj,nkj->nk', v, N[j])
        tl = np.sqrt(np.maximum(np.einsum('nkj,nkj->nk', v, v) - a * a, 0))
        u = np.sqrt(a * a + np.maximum(tl - rdisk, 0) ** 2) - tau[j] / 2
        jj[s] = j[np.arange(len(j)), np.argmin(u, 1)]
    a = np.einsum('ij,ij->i', X - S[jj], N[jj])
    al = np.einsum('ij,ij->i', closed.face_normals, N[jj])
    front = (al > COS_FRONT) & (a > -tau[jj] / 2)
    flab = trimesh.graph.connected_component_labels(closed.face_adjacency, node_count=len(closed.faces))
    vlab = np.full(len(closed.vertices), -1, np.int64); vlab[closed.faces.ravel()] = np.repeat(flab, 3)
    m = trimesh.Trimesh(closed.vertices, closed.faces[front], process=False)
    m.remove_unreferenced_vertices()
    m.metadata['union'] = (cKDTree(closed.vertices), vlab)      # which slab-union body each region belongs to
    return m, dict(sheet_faces_mc=int(len(closed.faces)), sheet_faces=int(len(m.faces)), band_voxels=nband,
                   sheet_pitch_mm=round(pitch * 1e3, 3), closed_area_cm2=round(closed.area * 1e4, 1),
                   union_bodies=int(flab.max() + 1) if len(flab) else 0)


def _boundary_halfedges(F):
    """Directed border edges (a, b) as they run in their one face."""
    E = np.concatenate([F[:, [0, 1]], F[:, [1, 2]], F[:, [2, 0]]])
    key = np.sort(E, 1)
    _, inv, cnt = np.unique(key, axis=0, return_inverse=True, return_counts=True)
    return E[cnt[inv.ravel()] == 1]


def border_loops(F):
    """Border loops of an edge-manifold sheet without bow-ties: list of vertex-index arrays in face order."""
    be = _boundary_halfedges(np.asarray(F))
    if len(be) == 0:
        return []
    nxt = dict(zip(be[:, 0].tolist(), be[:, 1].tolist()))
    seen, loops = set(), []
    for a in be[:, 0].tolist():
        if a in seen:
            continue
        L = []
        cur = a
        while cur not in seen and cur in nxt:
            seen.add(cur); L.append(cur); cur = nxt[cur]
        if cur == a and len(L) >= 3:
            loops.append(np.array(L, np.int64))
    return loops


def fill_holes(m, max_len=None, max_edges=None, need=None):
    """Fan-fill border loops (new centre vertex) that are not the longest loop of their component and are short:
    length <= max_len and/or <= max_edges edges; need(loop) -> bool narrows the choice further. Returns (mesh,
    filled count, filled area m^2)."""
    if len(m.faces) == 0:
        return m, 0, 0.0
    V, F = np.asarray(m.vertices), np.asarray(m.faces)
    loops = border_loops(F)
    if not loops:
        return m, 0, 0.0
    lab = trimesh.graph.connected_component_labels(m.face_adjacency, node_count=len(F))
    vcomp = np.full(len(V), -1); vcomp[F.ravel()] = np.repeat(lab, 3)
    lens = [float(np.linalg.norm(V[np.roll(L, -1)] - V[L], axis=1).sum()) for L in loops]
    longest = {}
    for i, L in enumerate(loops):
        c = int(vcomp[L[0]])
        if c not in longest or lens[i] > lens[longest[c]]:
            longest[c] = i
    newV, newF, area, cnt = [], [], 0.0, 0
    for i, L in enumerate(loops):
        if longest[int(vcomp[L[0]])] == i:
            continue
        if max_len is not None and lens[i] > max_len:
            continue
        if max_edges is not None and len(L) > max_edges:
            continue
        if need is not None and not need(L):
            continue
        c = len(V) + len(newV); ctr = V[L].mean(0); newV.append(ctr)
        nb = np.roll(L, -1)
        tri = np.stack([nb, L, np.full(len(L), c)], 1)          # border a->b lies in a face; the fill holds b->a
        newF.append(tri); cnt += 1
        area += float(0.5 * np.linalg.norm(np.cross(V[L] - ctr, V[nb] - ctr), axis=1).sum())
    if not cnt:
        return m, 0, 0.0
    out = trimesh.Trimesh(np.vstack([V, np.array(newV)]), np.vstack([F] + newF), process=False)
    return out, cnt, area


def manifold_split(V, F, nudge=SPLIT_NUDGE):
    """Cut an oriented triangle soup into an edge-manifold sheet without bow-ties, removing no face: faces stay joined
    only across edges shared by exactly two faces that run them in opposite directions; every other edge (shared by
    > 2 faces, or by two faces of the same direction) is unzipped, and every vertex whose faces then form more than one
    fan is split into one copy per fan. Copies after the first move by nudge towards the centroid of their own fan, so
    the kit's weld (exact position match) cannot merge them again. Returns (V, F, number of extra vertices)."""
    F = np.asarray(F, np.int64); V = np.asarray(V, np.float64)
    nf = len(F)
    if nf == 0:
        return V, F, 0
    a = F.ravel()                                            # corner c = 3 f + k sits at vertex a[c]
    b = F[:, [1, 2, 0]].ravel()                              # its outgoing half-edge a[c] -> b[c]
    key = np.minimum(a, b) * (len(V) + 1) + np.maximum(a, b)
    order = np.argsort(key, kind='stable'); ks = key[order]
    start = np.r_[0, np.flatnonzero(np.diff(ks)) + 1]; cnt = np.diff(np.r_[start, len(ks)])
    two = start[cnt == 2]
    h1, h2 = order[two], order[two + 1]
    ok = (a[h1] == b[h2]) & (b[h1] == a[h2])                 # opposite directions: a proper manifold pair
    h1, h2 = h1[ok], h2[ok]
    nxt = lambda c: 3 * (c // 3) + (c % 3 + 1) % 3           # corner at the half-edge's end vertex
    # half-edge h1 = (u -> v) in face f, h2 = (v -> u) in face g: corner(f, u) ~ corner(g, u) = nxt(h2), and
    # corner(f, v) = nxt(h1) ~ corner(g, v) = h2
    I = np.r_[h1, nxt(h1)]; J = np.r_[nxt(h2), h2]
    G = coo_matrix((np.ones(len(I)), (I, J)), shape=(3 * nf, 3 * nf))
    nc, lab = connected_components(G, directed=False)
    # one new vertex per corner component; the first component of each old vertex keeps its index position
    rep_v = np.zeros(nc, np.int64); rep_v[lab] = a
    first_c = np.full(len(V), -1, np.int64)
    comps = np.arange(nc)
    order_c = np.lexsort((comps, rep_v))
    is_first = np.r_[True, rep_v[order_c][1:] != rep_v[order_c][:-1]]
    newid = np.empty(nc, np.int64)
    first_c[rep_v[order_c][is_first]] = order_c[is_first]
    extra = order_c[~is_first]
    newid[order_c[is_first]] = rep_v[order_c[is_first]]
    newid[extra] = len(V) + np.arange(len(extra))
    V2 = np.vstack([V, V[rep_v[extra]]]) if len(extra) else V.copy()
    if len(extra) and nudge > 0:
        fc = V[F].mean(1)                                    # face centroids
        acc = np.zeros((nc, 3)); np.add.at(acc, lab, np.repeat(fc, 3, 0))
        n_c = np.bincount(lab, minlength=nc)
        dirv = acc[extra] / n_c[extra][:, None] - V[rep_v[extra]]
        V2[len(V):] += nudge * _unit(dirv)
    F2 = newid[lab].reshape(-1, 3)
    return V2, F2, int(len(extra))


def manifold_clean(m):
    """Remove degenerate faces and collapsed fins (a face and its exact reverse), keep one copy of duplicated faces,
    fix the winding, then cut the rest into an edge-manifold sheet without bow-ties by unzipping and splitting
    (manifold_split) instead of deleting faces. (Stage 1b's first version deleted every face on a non-manifold edge and
    around a bow-tie vertex, for up to 6 rounds; after a decimation pass that cascaded into holes: measured -6 % and
    -9.5 % sheet area in one pass on two public dev episodes.) Returns (mesh, removed face count);
    mesh.metadata['split_vertices'] counts the copies made."""
    if len(m.faces) == 0:
        return m, 0
    n0 = len(m.faces)
    V, F = np.asarray(m.vertices, np.float64), np.asarray(m.faces, np.int64)
    pairs = cKDTree(V).query_pairs(MERGE_TOL, output_type='ndarray')   # micro-clusters the decimator leaves
    if len(pairs):
        _, lab = connected_components(coo_matrix((np.ones(len(pairs)), (pairs[:, 0], pairs[:, 1])),
                                                 shape=(len(V), len(V))), directed=False)
        rep_ = np.zeros(lab.max() + 1, np.int64); rep_[lab[::-1]] = np.arange(len(V))[::-1]
        F = rep_[lab][F]
        F = F[(F[:, 0] != F[:, 1]) & (F[:, 1] != F[:, 2]) & (F[:, 0] != F[:, 2])]
    m = trimesh.Trimesh(V, F, process=True)
    m.update_faces(m.nondegenerate_faces(height=MERGE_TOL / 10))
    # duplicate faces (same three vertices): a pair of opposite orientation is a collapsed fin -> remove all copies;
    # copies of one orientation -> keep one
    F = np.asarray(m.faces)
    if len(F):
        srt = np.sort(F, 1)
        _, inv, cnt = np.unique(srt, axis=0, return_inverse=True, return_counts=True)
        inv = inv.ravel()
        if (cnt > 1).any():
            par = (F[:, 1] - F[:, 0]) * (F[:, 2] - F[:, 0]) * (F[:, 2] - F[:, 1])     # sign = cyclic order parity
            par = np.sign(par).astype(int)
            pos = np.bincount(inv, par > 0, minlength=len(cnt)); neg = np.bincount(inv, par < 0, minlength=len(cnt))
            fin = (pos > 0) & (neg > 0)
            first = np.zeros(len(F), bool); _, fi = np.unique(inv, return_index=True); first[fi] = True
            m.update_faces(first & ~fin[inv])
    m.remove_unreferenced_vertices()
    if len(m.faces) == 0:
        return m, n0
    trimesh.repair.fix_winding(m)                           # orient across the manifold edges first ...
    V2, F2, nsplit = manifold_split(m.vertices, m.faces)    # ... then unzip / split whatever is left
    out = trimesh.Trimesh(V2, F2, process=False)
    out.metadata['split_vertices'] = nsplit
    return out, int(n0 - len(out.faces))


# ---------------------------------------------------------------------------------------------- 6. islands
def _sphere_fit(V):
    """Algebraic least-squares sphere through points V: (radius, rms radial residual); (inf, inf) if degenerate."""
    if len(V) < 8:
        return float('inf'), float('inf')
    A = np.c_[2 * V, np.ones(len(V))]; b = (V * V).sum(1)
    sol, *_ = np.linalg.lstsq(A, b, rcond=None)
    c = sol[:3]; r2 = sol[3] + c @ c
    if not np.isfinite(r2) or r2 <= 0:
        return float('inf'), float('inf')
    R = float(np.sqrt(r2))
    return R, float(np.sqrt(np.mean((np.linalg.norm(V - c, axis=1) - R) ** 2)))


def _hull_shape(V):
    """Convex-hull sphericity and diameter of a vertex set (0, 0 when degenerate)."""
    try:
        h = ConvexHull(V)
    except Exception:
        return 0.0, 0.0
    vol, area = float(h.volume), float(h.area)
    sph = math.pi ** (1 / 3) * (6 * vol) ** (2 / 3) / area if area > 0 else 0.0
    H = V[h.vertices]
    diam = float(np.sqrt(((H[:, None, :] - H[None, :, :]) ** 2).sum(-1).max())) if len(H) <= 3000 else \
        float(np.linalg.norm(H.max(0) - H.min(0)))
    return sph, diam


def island_filter(m, P, F, host_tree=None, host_touch=None, union=None):
    """Island rule on an open sheet. Components are grouped when their vertices come within TOUCH (and, if a host is
    given, components within host_touch of the host join the body group). The group holding the largest component is
    the body. Any other group is kept only if it is ball-like (hull sphericity >= BALL_SPHER, hull diameter <= BALL_D)
    with frame support (>= max(F_MIN_ABS, F_MIN_FRAC * frames)), area >= A_MIN and distance <= NEAR to the body.
    Body-group components smaller than A_MIN are dropped as noise. Returns (mesh, report)."""
    parts = _components(m)
    rep = dict(components=len(parts), dropped_area_cm2=0.0, dropped=[], kept_balls=0)
    if len(parts) == 0:
        return m, rep
    parts = sorted(parts, key=lambda q: q.area, reverse=True)
    n = len(parts)
    trees = [cKDTree(np.vstack([q.vertices, q.triangles_center])) for q in parts]   # surface proxy (pitch/2)
    bmin = np.array([q.bounds[0] for q in parts]); bmax = np.array([q.bounds[1] for q in parts])
    parent = list(range(n))

    def find(a):
        while parent[a] != a:
            parent[a] = parent[parent[a]]; a = parent[a]
        return a
    for i in range(n):
        for j in range(i + 1, n):
            if np.any(bmin[i] > bmax[j] + TOUCH) or np.any(bmin[j] > bmax[i] + TOUCH):
                continue
            if find(i) == find(j):
                continue
            small, big = (i, j) if len(parts[i].vertices) < len(parts[j].vertices) else (j, i)
            if np.isfinite(trees[big].query(parts[small].vertices, k=1, distance_upper_bound=TOUCH)[0]).any() or \
                    np.isfinite(trees[big].query(parts[small].triangles_center, k=1,
                                                 distance_upper_bound=TOUCH)[0]).any():
                parent[find(i)] = find(j)
    if union is not None:                                  # pieces of one slab-union body touch through the solid
        utree, vlab = union
        first = {}
        for i in range(n):
            V = parts[i].vertices
            sel = V[np.linspace(0, len(V) - 1, min(len(V), 64)).astype(int)]
            for lb in set(vlab[utree.query(sel, k=1)[1]].tolist()):
                if lb in first:
                    if find(i) != find(first[lb]):
                        parent[find(i)] = find(first[lb])
                else:
                    first[lb] = i
    if host_tree is not None:
        for i in range(n):
            if np.isfinite(host_tree.query(parts[i].vertices, k=1, distance_upper_bound=host_touch)[0]).any():
                parent[find(i)] = find(0)
    body = find(0)
    groups = {}
    for i in range(n):
        groups.setdefault(find(i), []).append(i)
    body_v = np.vstack([np.vstack([parts[i].vertices, parts[i].triangles_center]) for i in groups[body]])
    tbody = cKDTree(body_v)
    nfr = len(np.unique(F)) if len(F) else 0
    fmin = max(F_MIN_ABS, int(math.ceil(F_MIN_FRAC * nfr)))
    rng = np.random.default_rng(0)
    sub = rng.choice(len(P), min(len(P), 400000), replace=False) if len(P) else np.zeros(0, int)
    Ps, Fs = P[sub], F[sub]
    keep = []
    for r, mem in groups.items():
        area = float(sum(parts[i].area for i in mem))
        if r == body:
            for i in mem:
                if i == 0 or parts[i].area >= A_MIN_BODY:
                    keep.append(i)
                else:
                    rep['dropped'].append(dict(area_cm2=round(parts[i].area * 1e4, 3), why='body_flake'))
                    rep['dropped_area_cm2'] += parts[i].area * 1e4
            continue
        V = np.vstack([parts[i].vertices for i in mem])
        sph, diam = _hull_shape(V)
        dist = float(tbody.query(V, k=1)[0].min())
        tv = cKDTree(V)
        frames = int(len(np.unique(Fs[tv.query(Ps, k=1, distance_upper_bound=0.003)[1] < len(V)]))) if len(Ps) else 0
        R, rms = _sphere_fit(V)
        ball = (sph >= BALL_SPHER) and (diam <= BALL_D) and (R <= diam) and (rms <= BALL_FIT_RMS * R)
        ok = ball and frames >= fmin and area >= A_MIN and dist <= NEAR
        why = 'kept_ball' if ok else ('not_ball' if not ball else 'frames' if frames < fmin else 'area' if area < A_MIN
                                      else 'far')
        d = dict(area_cm2=round(area * 1e4, 3), hull_sphericity=round(sph, 3), hull_diam_mm=round(diam * 1e3, 1),
                 sphere_r_mm=round(R * 1e3, 1) if np.isfinite(R) else None,
                 sphere_rms_mm=round(rms * 1e3, 2) if np.isfinite(rms) else None,
                 dist_mm=round(dist * 1e3, 1), frames=frames, why=why)
        if ok:
            keep.extend(mem); rep['kept_balls'] += 1; rep.setdefault('balls', []).append(d)
        else:
            rep['dropped'].append(d); rep['dropped_area_cm2'] += area * 1e4
    rep['dropped_area_cm2'] = round(rep['dropped_area_cm2'], 3)
    by = {}
    for d in rep['dropped']:
        by[d['why']] = by.get(d['why'], 0.0) + d['area_cm2']
    rep['dropped_by_reason_cm2'] = {k: round(v, 2) for k, v in by.items()}
    rep['dropped_by_reason_n'] = {k: sum(1 for d in rep['dropped'] if d['why'] == k) for k in by}
    rep['dropped'] = sorted(rep['dropped'], key=lambda d: -d['area_cm2'])[:12]
    rep['dropped_n'] = int(n - len(keep))
    out = trimesh.util.concatenate([parts[i] for i in sorted(keep)])
    rep['kept_area_cm2'] = round(out.area * 1e4, 2)
    return out, rep


# ---------------------------------------------------------------------------------------------- 7. budget
def _skirt(m, h):
    """Sheet + a skirt of height h along -vertex normal on every border edge. Returns (V, F, n_sheet_vertices)."""
    V, F = np.asarray(m.vertices), np.asarray(m.faces)
    be = _boundary_halfedges(F)
    if len(be) == 0:
        return V, F, len(V)
    bv = np.unique(be)
    sk = np.full(len(V), -1, np.int64); sk[bv] = len(V) + np.arange(len(bv))
    Vs = V[bv] - h * np.asarray(m.vertex_normals)[bv]
    a, b = be[:, 0], be[:, 1]
    Fs = np.concatenate([np.stack([b, a, sk[a]], 1), np.stack([b, sk[a], sk[b]], 1)])
    return np.vstack([V, Vs]), np.vstack([F, Fs]), len(V)


def _strip_border_faces(V, F):
    """Remove every face that touches a border vertex of (V, F): after a skirted decimation, exactly the skirt."""
    be = _boundary_halfedges(F)
    if len(be) == 0:
        return trimesh.Trimesh(V, F, process=False)
    bv = np.zeros(len(V), bool); bv[be.ravel()] = True
    m = trimesh.Trimesh(V, F[~np.any(bv[F], 1)], process=False)
    m.remove_unreferenced_vertices()
    return m


def taper_split(V, F, max_rounds=8):
    """Prepare a sheet for the tapered rim (back sheet shares the border vertices). An edge shared by two faces whose
    both ends lie on the border would then be used by four faces, so each such edge is split at its midpoint (one
    edge per face per round, until none is left); triangles whose three edges are all border edges would close onto
    themselves with zero volume and are dropped. Returns (V, F, info)."""
    V = np.asarray(V, np.float64).copy(); F = np.asarray(F, np.int64).copy()
    info = dict(taper_split_edges=0, taper_dropped_triangles=0, taper_dropped_area_cm2=0.0)
    for _ in range(max_rounds):
        if len(F) == 0:
            break
        E = np.concatenate([F[:, [0, 1]], F[:, [1, 2]], F[:, [2, 0]]])
        key = np.sort(E, 1)
        _, inv, cnt = np.unique(key, axis=0, return_inverse=True, return_counts=True)
        inv = inv.ravel(); ce = cnt[inv].reshape(3, -1).T            # per face, use count of its 3 edges
        iso = np.all(ce == 1, 1)
        if iso.any():
            a = 0.5 * np.linalg.norm(np.cross(V[F[iso, 1]] - V[F[iso, 0]], V[F[iso, 2]] - V[F[iso, 0]]), axis=1)
            info['taper_dropped_triangles'] += int(iso.sum()); info['taper_dropped_area_cm2'] += float(a.sum()) * 1e4
            F = F[~iso]
            continue
        bv = np.zeros(len(V), bool); bv[E[cnt[inv] == 1].ravel()] = True
        hf = np.flatnonzero((cnt[inv] == 2) & bv[E[:, 0]] & bv[E[:, 1]])  # half-edges (u -> v) of flagged edges
        if len(hf) == 0:
            break
        nf = len(F)
        face = hf % nf; k = hf // nf                                     # E row r = k * nf + face
        u, v = E[hf, 0], E[hf, 1]
        # pair the two half-edges of each flagged edge; take each edge once, no face twice in one round
        ek = inv[hf]
        o = np.argsort(ek, kind='stable'); ek, face, k, u, v = ek[o], face[o], k[o], u[o], v[o]
        used = np.zeros(nf, bool); newV, newF = [], []
        for i in range(0, len(ek) - 1, 2):
            if ek[i] != ek[i + 1]:
                continue
            f, g = face[i], face[i + 1]
            if used[f] or used[g]:
                continue
            used[f] = used[g] = True
            uu, vv = u[i], v[i]                                          # f runs uu -> vv, g runs vv -> uu
            cf = F[f, (k[i] + 2) % 3]; cg = F[g, (k[i + 1] + 2) % 3]
            mi = len(V) + len(newV); newV.append(0.5 * (V[uu] + V[vv]))
            F[f] = [uu, mi, cf]; newF.append([mi, vv, cf])
            F[g] = [vv, mi, cg]; newF.append([mi, uu, cg])
            info['taper_split_edges'] += 1
        if not newV:
            break
        V = np.vstack([V, np.array(newV)]); F = np.vstack([F, np.array(newF, np.int64)])
    info['taper_dropped_area_cm2'] = round(info['taper_dropped_area_cm2'], 3)
    return V, F, info


def closed_faces(m, rim=None):
    """Face count of the solidified sheet: 2 * (faces + border edges) with rim quads, 2 * faces after taper_split
    with the tapered rim."""
    if len(m.faces) == 0:
        return 0
    if (rim or RIM) == 'taper':
        return 2 * len(taper_split(m.vertices, m.faces)[1])
    return 2 * (len(m.faces) + len(_boundary_halfedges(np.asarray(m.faces))))


def _dec_pass(m, target_count, h, agg):
    """One skirted decimation pass to target_count faces (sheet + skirt), skirt stripped, manifold cleaned."""
    import fast_simplification
    V, F, nv = _skirt(m, h)
    tc = int(min(len(F) - 1, max(16, target_count)))
    v, f = fast_simplification.simplify(np.asarray(V, np.float64), np.asarray(F, np.int64), target_count=tc, agg=agg)
    d = _strip_border_faces(np.asarray(v, np.float64), np.asarray(f, np.int64))
    key0 = set(map(tuple, np.round(d.vertices[np.unique(_boundary_halfedges(d.faces))] * 1e6).astype(np.int64)
                   .tolist())) if len(d.faces) else set()
    d, rem = manifold_clean(d)
    if rem and len(d.faces):                               # holes the clean-up opened (a border vertex that was not
        Vd = d.vertices                                    # on the border before) are fan-filled again
        def new_hole(L):
            return any(tuple(q) not in key0 for q in np.round(Vd[L] * 1e6).astype(np.int64).tolist())
        d, _, _ = fill_holes(d, max_edges=DEC_REFILL_EDGES, need=new_hole)
        d, _ = manifold_clean(d)
    return d, rem, tc


def _drop_small(m, a_min=None):
    """Drop decimated-sheet components smaller than a_min (default A_SPECK); returns (mesh, cm^2)."""
    a_min = A_SPECK if a_min is None else a_min
    parts = _components(m)
    if len(parts) <= 1:
        return m, 0.0
    keep = [q for q in parts if q.area >= a_min] or [max(parts, key=lambda q: q.area)]
    out = trimesh.util.concatenate(keep)
    return out, round((m.area - out.area) * 1e4, 3)


def decimation_error(dense, dec, n=60000):
    """Distances (mm) from the dense sheet to the decimated one: p50/p95/p99 and share > 3 mm (sample to sample)."""
    if len(dense.faces) == 0 or len(dec.faces) == 0:
        return dict()
    A = trimesh.sample.sample_surface(dense, n, seed=0)[0]
    B = trimesh.sample.sample_surface(dec, n, seed=1)[0]
    d = cKDTree(B).query(A, workers=2)[0]
    return dict(dense_to_dec_mm_p50_95_99=np.round(np.percentile(d, [50, 95, 99]) * 1e3, 2).tolist(),
                dense_to_dec_frac_gt3mm=round(float(np.mean(d > 0.003)), 4))


def decimate_sheet(m, max_closed, h, agg=None, iters=8, rim=None):
    """Decimate the open sheet so that its solidified version has <= max_closed faces. Coarse passes divide the
    face count by DEC_STEP while the sheet is far above the budget; a final search on the target count then lands
    within 5 % under the budget. Every pass constrains the border with a temporary skirt and cleans the result to an
    edge-manifold, consistently wound sheet. Returns (sheet, info)."""
    agg = DEC_AGG if agg is None else agg
    rim = rim or RIM
    cf_ = lambda q: closed_faces(q, rim)
    info = dict(rim=rim, sheet_faces_in=int(len(m.faces)),
                border_edges_in=int(len(_boundary_halfedges(np.asarray(m.faces)))) if len(m.faces) else 0, agg=agg)
    if len(m.faces) == 0 or cf_(m) <= max_closed:
        m2, rem = manifold_clean(m)
        info.update(decimated=False, clean_removed=rem)
        return m2, info
    cur, removed, passes = m, 0, []
    while cf_(cur) > DEC_STEP * 1.5 * max_closed:
        cur, rem, tc = _dec_pass(cur, max(len(cur.faces) // DEC_STEP, int(1.5 * max_closed)), h, agg)
        removed += rem; passes.append(dict(target=tc, sheet_faces=int(len(cur.faces)), clean_removed=rem))
    target = int(max_closed / 2)                            # sheet + skirt faces ~ sheet + 2 * border
    tmax = len(cur.faces) + 2 * len(_boundary_halfedges(cur.faces)) - 1
    best, lo_t, hi_t = None, None, None                     # bisection on the target (the output is not monotonic)
    for it in range(iters):
        d, rem, tc = _dec_pass(cur, target, h, agg)
        cf = cf_(d)
        passes.append(dict(target=tc, sheet_faces=int(len(d.faces)), closed_faces=int(cf), clean_removed=rem))
        if cf <= max_closed:
            if best is None or cf > cf_(best[0]):
                best = (d, rem)
            lo_t = tc if lo_t is None else max(lo_t, tc)
            if cf >= 0.95 * max_closed or tc >= tmax:
                break
        else:
            hi_t = tc if hi_t is None else min(hi_t, tc)
        if lo_t is not None and hi_t is not None:
            if hi_t - lo_t <= max(2, 0.01 * hi_t):
                break
            target = (lo_t + hi_t) // 2
        else:
            target = int(tc * 0.975 * max_closed / max(cf, 1))
    if best is None:
        raise RuntimeError(f'decimate_sheet: could not reach {max_closed} closed faces: {passes}')
    d, rem = best
    d, info['post_dropped_area_cm2'] = _drop_small(d)
    d, rem2 = manifold_clean(d); rem += rem2
    info.update(decimated=True, passes=passes, sheet_faces=int(len(d.faces)),
                border_edges=int(len(_boundary_halfedges(d.faces))), clean_removed=int(removed + rem))
    info.update(decimation_error(m, d))
    return d, info


# ---------------------------------------------------------------------------------------------- 8. solidify
def solidify(m, tau_v, mode='oriented', rim=None):
    """Closed thin shell from an open, oriented, edge-manifold sheet: back sheet at -tau_v along the vertex normal
    (even-thickness scaling, mode 'oriented': front face stays; 'symmetric': +-tau_v/2). rim 'quad': rim quads on
    every border edge (2 * (faces + border edges) faces); rim 'taper': the back sheet shares the border vertices, so
    the shell thins to zero over the outermost ring of faces and needs no rim faces (2 * faces after taper_split).
    Watertight and consistently wound by construction. tau_v: per-vertex thickness (array) or a scalar."""
    rim = rim or RIM
    V, F = np.asarray(m.vertices, np.float64), np.asarray(m.faces, np.int64)
    if len(F) == 0:
        return _empty()
    tau_v = np.broadcast_to(np.asarray(tau_v, np.float64), (len(V),)).copy()
    if rim == 'taper':
        n0 = len(V)
        V, F, _ = taper_split(V, F)
        if len(V) > n0:                                     # split midpoints: mean thickness of their edge's ends
            tree = cKDTree(np.asarray(m.vertices)); _, j = tree.query(V[n0:], k=2)
            tau_v = np.r_[tau_v, tau_v[j].mean(1)]
        if len(F) == 0:
            return _empty()
        m = trimesh.Trimesh(V, F, process=False)
    fn = np.asarray(m.face_normals); af = np.asarray(m.area_faces)
    acc = np.zeros((len(V), 3)); ff = np.zeros(len(V), np.int64)
    for k in range(3):
        np.add.at(acc, F[:, k], fn * af[:, None]); ff[F[:, k]] = np.arange(len(F))
    nrm = np.linalg.norm(acc, axis=1)
    vn = acc / np.maximum(nrm, 1e-30)[:, None]
    bad = nrm < 1e-6 * max(float(af.max()), 1e-30)          # cancelling or degenerate fans: take one face's normal
    vn[bad] = fn[ff[bad]]
    # even thickness: mean cos between the vertex normal and its faces' normals
    cs = np.zeros(len(V)); cn = np.zeros(len(V))
    for k in range(3):
        np.add.at(cs, F[:, k], np.einsum('ij,ij->i', vn[F[:, k]], fn)); np.add.at(cn, F[:, k], 1)
    scale = 1.0 / np.clip(cs / np.maximum(cn, 1), EVEN_COS_MIN, 1.0)
    off = (tau_v * scale)[:, None] * vn
    if mode == 'symmetric':
        Vf, Vb = V + off / 2, V - off / 2
    else:
        Vf, Vb = V, V - off
    n = len(V)
    be = _boundary_halfedges(F)
    if rim == 'taper':
        bv = np.zeros(n, bool); bv[be.ravel()] = True
        back = np.where(bv, np.arange(n), n + np.cumsum(~bv) - 1)  # border vertices are shared by both sheets
        if mode == 'symmetric':                             # the shared border stays on the observed surface
            Vf = np.where(bv[:, None], V, Vf)
        Vall = np.vstack([Vf, Vb[~bv]])
        out = trimesh.Trimesh(Vall, np.vstack([F, back[F][:, ::-1]]), process=False)
    else:
        a, b = be[:, 0], be[:, 1]
        rimf = np.concatenate([np.stack([b, a, a + n], 1), np.stack([b, a + n, b + n], 1)]) if len(be) else \
            np.zeros((0, 3), np.int64)
        out = trimesh.Trimesh(np.vstack([Vf, Vb]), np.vstack([F, F[:, ::-1] + n, rimf]), process=False)
    if out.is_watertight and out.volume < 0:
        out.invert()
    return out


def vertex_tau(V, S, tau, k=8):
    """Per sheet vertex: median thickness of its k nearest samples."""
    if len(S) == 0:
        return np.zeros(len(V))
    k = min(k, len(S))
    _, j = cKDTree(S).query(V, k=k, workers=2)
    if j.ndim == 1:
        j = j[:, None]
    return np.median(tau[j], 1)


# ---------------------------------------------------------------------------------------------- driver
def _host_trim(m, host, dist):
    """Keep sheet faces whose centre lies more than dist outside the host (sampled signed distance, by the nearest
    host sample's face normal). Returns (mesh, info)."""
    n = int(np.clip(host.area * 4e6, 50000, 400000))           # ~4 samples per mm^2, capped
    Sh, fi = trimesh.sample.sample_surface(host, n, seed=0)
    Nh = np.asarray(host.face_normals)[fi]
    th = cKDTree(Sh)
    X = m.triangles_center
    d, j = th.query(X, k=1, workers=2)
    sd = np.where(np.einsum('ij,ij->i', X - Sh[j], Nh[j]) > 0, d, -d)
    keep = sd > dist
    out = trimesh.Trimesh(m.vertices, m.faces[keep], process=False); out.remove_unreferenced_vertices()
    return out, dict(host_trim_mm=round(dist * 1e3, 2), host_trimmed_area_cm2=round((m.area - out.area) * 1e4, 2)), th


def _border_verts(F):
    F = np.asarray(F, np.int64)
    if not len(F):
        return np.zeros(0, np.int64)
    e = np.sort(np.vstack([F[:, [0, 1]], F[:, [1, 2]], F[:, [2, 0]]]), 1)
    u, c = np.unique(e, axis=0, return_counts=True)
    return np.unique(u[c == 1].ravel())


def _host_attach(m, host, reach, support=None, sup_r=VOXEL, cos_max=0.7):
    """Stage-1b integration (A inside B): attach a patch sheet to its host. A border vertex moves to its closest point
    on the host surface when (a) it lies within `reach` of the host (the island rule's host_touch: the pieces that
    rule already counts as attached), (b) the move is supported by observations: observed points (all of the
    episode's, `support`) lie within sup_r (1 voxel) of the move segment at 1/4, 1/2 and 3/4 (the surface continues
    toward the host: an edge cut by the residual assignment or the host trim, not a free edge of the object), and
    (c) the move is not along the border (|cos(move, border tangent)| < cos_max: no folding of a free edge that
    runs toward the host). Interior vertices are unchanged. Measured on a public dev episode (lid program +
    shell_patch): the main patch piece sat 3.8 mm (t 2.5) / 2.1 mm (t 4.0) from the host, beyond the gates' TOUCH
    (2 mm), so gates.connectivity counted it as a separate body (the residual assignment leaves the gap; the trim
    removed nothing there). Generic, no object knowledge. Returns (mesh, info)."""
    F = np.asarray(m.faces, np.int64)
    info = dict(attach_reach_mm=round(reach * 1e3, 2), border_verts=0, within_reach=0, attached_border_verts=0)
    if not len(F):
        return m, info
    e = np.sort(np.vstack([F[:, [0, 1]], F[:, [1, 2]], F[:, [2, 0]]]), 1)
    u, c = np.unique(e, axis=0, return_counts=True)
    be = u[c == 1]
    bv = np.unique(be.ravel())
    info['border_verts'] = int(len(bv))
    if not len(bv):
        return m, info
    V = np.array(m.vertices, np.float64)
    cp, d, _ = trimesh.proximity.closest_point(host, V[bv])
    d = np.asarray(d)
    sel = (d <= reach) & (d > 1e-6)
    info['within_reach'] = int(sel.sum())
    mv = cp - V[bv]
    # border tangent: from the vertex's two border neighbours (other valences: no tangent test)
    nb = {}
    for a, b in be:
        nb.setdefault(int(a), []).append(int(b)); nb.setdefault(int(b), []).append(int(a))
    tan = np.zeros_like(mv)
    for k, v in enumerate(bv):
        n_ = nb.get(int(v), [])
        if len(n_) == 2:
            tan[k] = V[n_[1]] - V[n_[0]]
    tl = np.linalg.norm(tan, axis=1); ml = np.linalg.norm(mv, axis=1)
    cosv = np.where((tl > 0) & (ml > 0), np.abs(np.einsum('ij,ij->i', mv, tan)) / np.maximum(tl * ml, 1e-12), 0.0)
    along = cosv >= cos_max
    info['along_border'] = int((sel & along).sum())
    sel &= ~along
    if support is not None and len(support) and sel.any():
        tr = cKDTree(np.asarray(support, np.float64))
        sup = np.ones(len(bv), bool)
        for f_ in (0.25, 0.5, 0.75):
            q = V[bv] + f_ * mv
            sup &= np.isfinite(tr.query(q, distance_upper_bound=sup_r)[0])
        info['unsupported'] = int((sel & ~sup).sum())
        sel &= sup
    if sel.any():
        V[bv[sel]] = cp[sel]
        info.update(attached_border_verts=int(sel.sum()),
                    attach_move_mm_p50_90=np.round(np.percentile(d[sel], [50, 90]) * 1e3, 2).tolist())
    return trimesh.Trimesh(V, F, process=False), info


def shell_sheet(obs, voxel=VOXEL, mode='oriented', two_sided=True, carve=False, host=None, pitch=None, P_all=None):
    """t-independent part of the route: oriented samples, measured thickness, one face per wall, the open sheet and
    its islands. Returns a dict for solidify_sheet (several t and budgets reuse it). P_all (with host): every observed
    point of the episode, the support test of _host_attach (default: obs['pts'])."""
    t0 = time.time()
    rep = dict(voxel_mm=voxel * 1e3, mode=mode, two_sided=bool(two_sided), carve=bool(carve), host=host is not None)
    P = np.asarray(obs['pts'], np.float64); C = np.asarray(obs['cam'], np.float64)
    F = np.asarray(obs['frame']) if 'frame' in obs else np.zeros(len(P), int)
    ok = np.all(np.isfinite(P), 1) & np.all(np.isfinite(C), 1)
    P, C, F = P[ok], C[ok], F[ok]
    rep.update(points=int(len(P)), frames=int(len(np.unique(F))) if len(F) else 0)
    sh = dict(rep=rep, sheet=_empty(), S=np.zeros((0, 3)), tau_meas=np.zeros(0), cap=np.zeros(0), dec={}, mode=mode,
              voxel=voxel)
    if len(P) < PATCH_MIN_PTS:
        rep.update(empty='too few points', sec_sheet=round(time.time() - t0, 1))
        return sh
    n, planar = point_normals(P, C, F, voxel)
    rep['weak_normal_frac'] = round(float((planar < PLANAR_MIN).mean()), 3)
    front = (np.einsum('ij,ij->i', n, _unit(C - P)) >= COS_GRAZE) & (planar >= PLANAR_MIN)
    rep['grazing_or_weak_dropped_frac'] = round(float(1 - front.mean()), 3)
    P, C, F, n = P[front], C[front], F[front], n[front]
    ts = time.time()
    smp = directional_samples(P, n, voxel) if len(P) >= 16 else dict(s=np.zeros((0, 3)), n=np.zeros((0, 3)),
                                                                        w=np.zeros(0))
    S, N, W = smp['s'], smp['n'], smp['w']
    rep['samples'] = int(len(S)); rep['sec_fusion'] = round(time.time() - ts, 1)
    if len(S) < 16:
        rep.update(empty='too few samples', sec_sheet=round(time.time() - t0, 1))
        return sh
    if two_sided:
        T, partner = two_sided_thickness(S, N, return_partner=True)
    else:
        T, partner = np.full(len(S), np.nan), np.full(len(S), -1, np.int64)
    meas = np.isfinite(T)
    rep['two_sided_frac'] = round(float(meas.mean()), 3)
    if meas.any():
        rep['two_sided_T_mm_p10_50_90'] = np.round(np.percentile(T[meas], [10, 50, 90]) * 1e3, 2).tolist()
    cap = np.full(len(S), np.inf)
    if carve and mode == 'oriented':
        capv, cinfo = free_space_clamp(P, C, F, n, S, N, np.where(meas, T, TRUNC), TRUNC)
        cap = np.where(capv < np.where(meas, T, TRUNC) - 1e-12, capv, np.inf); rep.update(cinfo)
    if two_sided and mode == 'oriented':
        slave, sinfo = resolve_sides(S, N, W, T, partner, voxel); rep.update(sinfo)
    else:
        slave = np.zeros(len(S), bool)
    kept = ~slave
    S, N, T, cap = S[kept], N[kept], T[kept], cap[kept]
    rep['sheet_samples'] = int(len(S))
    pitch = 0.95 * T_FLOOR / math.sqrt(3)              # the front sheet's marching-cubes pitch
    rdisk = R_DISK_FRAC * voxel
    ts = time.time()
    m, sinfo = front_sheet(S, N, rdisk, voxel); rep.update(sinfo)
    union = m.metadata.get('union')
    m, rem = manifold_clean(m); rep['sheet_clean_removed'] = rem
    host_tree = None
    if host is not None and len(m.faces) and len(getattr(host, 'faces', [])):
        m, hinfo, host_tree = _host_trim(m, host, HOST_TRIM_FRAC * voxel); rep.update(hinfo)
        m, rem = manifold_clean(m); rep['sheet_clean_removed'] += rem
    if len(m.faces):
        m, nh, ah = fill_holes(m, max_len=HOLE_FILL_LEN)
        m, rem = manifold_clean(m); rep['sheet_clean_removed'] += rem
        rep.update(holes_filled=int(nh), holes_filled_area_cm2=round(ah * 1e4, 2))
    rep['sheet_area_raw_cm2'] = round(m.area * 1e4, 2) if len(m.faces) else 0.0
    if len(m.faces):
        m, isl = island_filter(m, P, F, host_tree=host_tree,
                               host_touch=HOST_TRIM_FRAC * voxel + TOUCH + pitch if host_tree is not None else None,
                               union=union if ISLAND_UNION else None)
        rep['islands'] = isl
        rep['islands_dropped'] = isl['dropped_n']; rep['islands_dropped_area_cm2'] = isl['dropped_area_cm2']
        if host_tree is not None and HOST_ATTACH and len(m.faces):
            m, ainfo = _host_attach(m, host, HOST_TRIM_FRAC * voxel + TOUCH + pitch,
                                    support=P_all if P_all is not None else P, sup_r=voxel)
            rep['host_attach'] = ainfo
    else:
        rep['islands_dropped'] = 0; rep['islands_dropped_area_cm2'] = 0.0
    rep['sheet_area_cm2'] = round(m.area * 1e4, 2) if len(m.faces) else 0.0
    rep['sec_sheet_mc'] = round(time.time() - ts, 1); rep['sec_sheet'] = round(time.time() - t0, 1)
    sh.update(sheet=m, S=S, tau_meas=T, cap=cap, pitch=pitch)
    return sh


def solidify_sheet(sh, t, max_faces=MAX_FACES, mode=None, return_report=False, rim=None):
    """Closed thin shell of unseen thickness t (m) from a shell_sheet() result: the sheet is decimated so the closed
    shell has <= max_faces faces (None: no decimation), the per-vertex thickness is the measured two-sided thickness
    where known, else t (capped by the free-space clamp), and the sheet is solidified."""
    t0 = time.time()
    mode = mode or sh['mode']; rim = rim or RIM
    rep = dict(sh['rep']); rep.update(t_mm=t * 1e3, max_faces=max_faces, rim=rim)
    m = sh['sheet']
    if len(m.faces) == 0:
        out = _empty()
        rep.update(faces=0, vertices=0, watertight=False, bodies=0, area_cm2=0.0, volume_cm3=None, extents_cm=None,
                   sec=round(time.time() - t0, 1), empty=rep.get('empty', 'no sheet'))
        out.metadata['shell_report'] = rep
        return (out, rep) if return_report else out
    if max_faces is not None:
        key = (int(max_faces), rim)
        if key not in sh['dec']:
            sh['dec'][key] = decimate_sheet(m, key[0], SKIRT_H_FRAC * sh['voxel'], rim=rim)
        d, dinfo = sh['dec'][key]
        rep['decimation'] = dinfo
    else:
        d, rem = manifold_clean(m); rep['decimation'] = dict(decimated=False, clean_removed=rem)
    if mode == 'symmetric':
        tau = np.full(len(sh['S']), t)
    else:
        tau = np.where(np.isfinite(sh['tau_meas']), sh['tau_meas'], t)
        tau = np.minimum(tau, np.maximum(sh['cap'], T_FLOOR))
    tv = vertex_tau(np.asarray(d.vertices), sh['S'], tau)
    out = solidify(d, tv, mode, rim)
    retries = 0
    while len(out.faces) and not out.is_watertight and retries < 3:   # safety net: should not trigger
        d, _ = manifold_clean(d); retries += 1
        tv = vertex_tau(np.asarray(d.vertices), sh['S'], tau); out = solidify(d, tv, mode, rim)
    rep['solidify_retries'] = retries
    if len(out.vertices) >= 2:                              # > 0: the kit's weld cannot merge anything
        rep['min_vertex_gap_um'] = round(float(cKDTree(out.vertices).query(out.vertices, k=2)[0][:, 1].min()) * 1e6, 2)
    sheet_area = float(d.area); dense_area = float(m.area)
    rep.update(faces=int(len(out.faces)), vertices=int(len(out.vertices)), watertight=bool(out.is_watertight),
               winding_consistent=bool(out.is_winding_consistent),
               bodies=int(len(_components(out))), area_cm2=round(out.area * 1e4, 1),
               sheet_dec_area_cm2=round(sheet_area * 1e4, 2),
               sheet_dec_area_change_pct=round(100 * (sheet_area / max(dense_area, 1e-12) - 1), 2),
               tau_v_mm_p10_50_90=np.round(np.percentile(tv, [10, 50, 90]) * 1e3, 2).tolist(),
               volume_cm3=round(float(out.volume) * 1e6, 2) if out.is_watertight else None,
               extents_cm=np.round(out.extents * 100, 1).tolist(),
               sec_solidify=round(time.time() - t0, 1), sec=round(rep.get('sec_sheet', 0) + time.time() - t0, 1))
    out.metadata['shell_report'] = rep
    return (out, rep) if return_report else out


def thin_shell(obs, t, voxel=VOXEL, mode='oriented', two_sided=True, carve=False, max_faces=MAX_FACES, pitch=None,
               return_report=False, rim=None):
    """obs dict (pts, cam, frame) -> closed thin shell (trimesh.Trimesh) of unseen thickness t (m) on the observed
    surfaces, <= max_faces faces (default 4000, so the kit's 4096-face budget_mesh only welds it; None: full
    resolution). mode 'oriented' (solid behind the observed face) or 'symmetric' (+-t/2). With two_sided, walls whose
    both faces were observed are built once with their measured thickness. With carve (oriented mode), a slab is cut
    back where our own rays saw through the material behind the surface. pitch is ignored (kept for API
    compatibility; the sheet's pitch follows T_FLOOR). rim: 'quad' or 'taper' (default RIM, see solidify).
    return_report=True -> (mesh, report)."""
    sh = shell_sheet(obs, voxel=voxel, mode=mode, two_sided=two_sided, carve=carve, pitch=pitch)
    return solidify_sheet(sh, t, max_faces=max_faces, mode=mode, return_report=return_report, rim=rim)


def surface_patch(obs, idx=None, t=0.0025, max_faces=None, host=None, voxel=VOXEL, mode='oriented', two_sided=True,
                  return_report=False, rim=None):
    """Closed thin shell over the observed points obs['pts'][idx] (all points if idx is None), for use as a part in
    a program (parts type 'shell_patch'). With host (a trimesh, e.g. the union of the earlier parts), the sheet is
    trimmed so it does not duplicate the host's surface: only sheet parts more than HOST_TRIM_FRAC * voxel outside the
    host are kept, and sheet pieces within that distance + TOUCH of the host count as attached to the body (island
    rule). max_faces=None: no decimation. Returns an empty Trimesh when no surface survives."""
    if idx is not None:
        idx = np.asarray(idx)
        sub = {k: np.asarray(obs[k])[idx] for k in ('pts', 'cam', 'frame') if k in obs}
    else:
        sub = {k: obs[k] for k in ('pts', 'cam', 'frame') if k in obs}
    P_all = np.asarray(obs['pts'], np.float64) if host is not None else None
    if P_all is not None:
        P_all = P_all[np.all(np.isfinite(P_all), 1)]
    sh = shell_sheet(sub, voxel=voxel, mode=mode, two_sided=two_sided, host=host, P_all=P_all)
    return solidify_sheet(sh, t, max_faces=max_faces, mode=mode, return_report=return_report, rim=rim)


def main():
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument('obj'); p.add_argument('ep', type=int); p.add_argument('out')
    p.add_argument('--t', type=float, required=True); p.add_argument('--voxel', type=float, default=VOXEL)
    p.add_argument('--mode', default='oriented'); p.add_argument('--refined', default='0')
    p.add_argument('--no_two_sided', action='store_true'); p.add_argument('--max_faces', type=int, default=MAX_FACES)
    p.add_argument('--carve', action='store_true'); p.add_argument('--rim', default=None, choices=('quad', 'taper'))
    a = p.parse_args()
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from autokit.io_gt import load_obs, obs_path
    path = None
    if a.refined in ('auto', '1'):
        path = obs_path(a.obj, a.ep, refined=True, must_exist=False)
        if not os.path.isfile(path):
            if a.refined == '1':
                raise FileNotFoundError(path)
            path = None
    path = path or obs_path(a.obj, a.ep)
    m, rep = thin_shell(load_obs(path, keys=('pts', 'cam', 'frame')), t=a.t, voxel=a.voxel, mode=a.mode,
                        two_sided=not a.no_two_sided, carve=a.carve, max_faces=a.max_faces or None,
                        return_report=True, rim=a.rim)
    m.export(a.out)
    rep.update(obs=path, out=a.out)
    print(json.dumps(rep, default=str))


if __name__ == '__main__':
    main()
