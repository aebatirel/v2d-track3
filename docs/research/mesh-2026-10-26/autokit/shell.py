"""Generic thin-shell mesh from ONE episode's observed points (autokit route A, no part vocabulary).

Observed surfaces -> denoised oriented surface samples (point-based directional TSDF) -> a closed thin solid of
thickness t behind them -> marching cubes. README section 6, P5 ("thin-wall fusion": directional TSDF, 1.5-2 mm
voxels, 4-5 mm truncation, sub-voxel marching cubes), done on the obs_points.py samples instead of depth images.

GT-free. thin_shell() reads only the obs dict it is given: pts (N,3) object frame [m], cam (N,3) camera centre of
each point, frame (N,) frame index (scripts/obs_points.py output, loaded by autokit.io_gt, which refuses scan,
*_align, parquet and mocap paths). No object name and no per-object constant appears in this file: every constant
below is a sensor/resolution scale or a generic rule. Unseen thickness is the caller's t (generic grid 1.5 / 2.5 /
4.0 mm); a measured thickness replaces it only where both faces of a wall were observed.

Method
 1. Normals. Raw points -> VOXEL centroids; PCA over K_N nearest centroids gives each voxel's unsigned normal; every
    raw point takes its voxel's normal, turned towards the camera that saw it. The two faces of a thin wall thus get
    opposite normals even where their noisy layers overlap (measured cloud thickness ~1-1.8 mm std, so a 2-3 mm wall's
    layers do overlap).
 2. Directional fusion (Splietker & Behnke 2019, DTSDF). Six bins +-x, +-y, +-z with 60 deg cones (overlapping: every
    normal falls in >= 1 bin; opposite faces never share one). Per bin, points -> VOXEL centroids (weight = count),
    then each centroid is projected onto the bin's local mean surface by point-to-plane averaging (implicit MLS,
    Kolluri 2008: phi(x) = sum w_i n_i.(x - p_i) / sum w_i, Gaussian SIGMA, cut at TRUNC = the TSDF band). The
    projected samples of all bins are merged on a VOXEL/2 grid per bin: open surfaces, denoised, oriented.
 3. Thickness. From each sample s_j, step along -n_j up to D_MAX; the first opposite-facing sample within R_TAN of
    that line is the other face of the wall: measured thickness T_j (median over the 8 nearest measured samples,
    floored at T_FLOOR). Elsewhere tau_j = t.
 4. Closed solid. U(x) = min_j [dist(x, disc_j) - tau_j / 2], disc_j = disc of radius R_DISK, normal n_j, centred at
    s_j - (tau_j / 2) n_j ('oriented': the solid lies behind the observed surface, away from the cameras, the observed
    face is kept in place) or at s_j ('symmetric': a +-t/2 tube about the surface, the task's unsigned-distance
    variant). U is evaluated in a narrow band of a grid of pitch min(VOXEL, 0.95 t / sqrt(3)) (a shell of thickness
    t cannot fall between grid points) and is positive elsewhere, so marching cubes (Lewiner) at U = 0 is closed by
    construction, with sub-voxel accuracy (U is a distance, linear across each face).
 5. Islands. Connected components; one survives if it is the largest, or if it was seen in >= F_MIN_FRAC of the
    episode's frames (>= F_MIN_ABS), has area >= A_MIN and lies within NEAR of the largest. Marker balls next to the
    body stay; floaters from a few bad frames go.
 6. Decimation (fast_simplification, quadric) to max_faces; a decimated mesh is kept only if still watertight.

Usage (library):
    from autokit.io_gt import load_obs, obs_path
    from autokit.shell import thin_shell
    mesh = thin_shell(load_obs(obs_path(OBJ, EP)), t=0.0025)                      # trimesh.Trimesh, watertight
    mesh, rep = thin_shell(obs, t=0.0015, voxel=0.002, return_report=True)        # + report dict
CLI:
    shell.py OBJ EP OUT.glb [--t 0.0025] [--voxel 0.002] [--mode oriented|symmetric] [--refined auto|1|0]
             [--no_two_sided] [--max_faces 200000]
    --refined auto uses autokit/refine.py's refined copy (io_gt.obs_path(refined=True)) when it exists.
"""
import json, math, os, sys, time

import numpy as np
import trimesh
from scipy import ndimage
from scipy.spatial import cKDTree

# ---------------------------------------------------------------------------------------------- declared constants
K_N = 96                 # PCA normal neighbourhood (VOXEL centroids): ~7 mm radius at 2 mm voxels (clouds are thick)
PLANAR_MIN = 0.2         # below this planarity (1 - l0/l1) a point's normal falls back to its view direction
COS_GRAZE = 0.2          # points seen at > 78 deg incidence are dropped: their depth is the noisiest and their
                         # normal's side is ambiguous (measured: they caused ~95 % of the 'two-sided' hits on lid ep2)
COS_BIN = 0.5            # bin membership: n . axis > cos 60 deg (6 overlapping cones cover the sphere)
SIGMA = 0.002            # MLS Gaussian (m): ~1.2-2 x the measured cloud thickness std
TRUNC = 0.005            # MLS neighbour cut-off (m) = TSDF truncation band (P5: 4-5 mm)
K_MLS = 48               # MLS neighbours per query
COS_SIM = 0.7            # MLS: neighbours whose normal is within 45 deg of the query's
MLS_ITERS = 2
MIN_NB = 6               # a sample needs >= MIN_NB MLS neighbours (isolated specks are dropped)
D_MAX = 0.010            # two-sided search depth (m) = 2 x TRUNC
R_TAN = 0.0015           # two-sided: the other face must lie within this of the inward normal line (m)
COS_OPP = 0.7            # two-sided: the other face's normal within 45 deg of -n
T_FLOOR = 0.001          # floor of a measured thickness (m): below the fusion resolution
R_DISK_FRAC = 0.75       # disc radius as a fraction of VOXEL (samples merged on a VOXEL/2 grid; discs overlap)
F_MIN_FRAC, F_MIN_ABS = 0.05, 5   # island support: frames that saw it
A_MIN = 5e-5             # island area floor (m^2) = 0.5 cm^2 (a 7 mm ball cap shell is ~3-6 cm^2)
NEAR = 0.03              # islands farther than this from the main body are dropped (m)
MAX_FACES = 200000
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


# ---------------------------------------------------------------------------------------------- 1. normals
def point_normals(P, C, vox, k=K_N):
    """Per raw point: unit normal (its voxel's PCA normal, oriented towards its own camera) and planarity."""
    inv, nv = _voxel_groups(P, vox)
    Cv, _ = _group_mean(inv, nv, P)
    tree = cKDTree(Cv)
    k = min(k, nv)
    nrm = np.zeros((nv, 3)); pl = np.zeros(nv)
    for s in _chunks(nv, 100000):
        _, nb = tree.query(Cv[s], k=k, workers=2)
        Q = Cv[nb] - Cv[nb].mean(1, keepdims=True)
        w, V = np.linalg.eigh(np.einsum('nki,nkj->nij', Q, Q) / k)
        nrm[s] = V[:, :, 0]; pl[s] = 1 - w[:, 0] / np.maximum(w[:, 1], 1e-12)
    n = nrm[inv]; view = _unit(C - P)
    n[np.einsum('ni,ni->n', n, view) < 0] *= -1
    planar = pl[inv]
    weak = planar < PLANAR_MIN                        # rods, corners, specks: the view direction is the best guess
    n[weak] = view[weak]
    return n, planar


# ---------------------------------------------------------------------------------------------- 2. directional fusion
def _mls_project(Cb, Nb, Wb, iters=MLS_ITERS):
    """Project centroids of one bin onto the bin's local mean surface (point-to-plane MLS). Returns q, n, nb_count."""
    tree = cKDTree(Cb)
    q = Cb.copy(); nq = Nb.copy(); cnt = np.zeros(len(Cb), int)
    k = min(K_MLS, len(Cb))
    for it in range(iters):
        for s in _chunks(len(Cb), 100000):
            d, nb = tree.query(q[s], k=k, distance_upper_bound=TRUNC, workers=2)
            ok = nb < len(Cb); nb = np.where(ok, nb, 0)
            sim = np.einsum('nkj,nj->nk', Nb[nb], nq[s]) > COS_SIM
            g = np.where(ok & sim, Wb[nb] * np.exp(-0.5 * (d / SIGMA) ** 2), 0.0)
            sg = g.sum(1)
            nbar = _unit(np.einsum('nk,nkj->nj', g, Nb[nb]))
            phi = np.einsum('nk,nk->n', g, np.einsum('nkj,nj->nk', q[s][:, None, :] - Cb[nb], nbar)) / np.maximum(sg, 1e-12)
            good = sg > 0
            q[s][good] -= (phi[good, None] * nbar[good])
            nq[s][good] = nbar[good]
            cnt[s] = (g > 0).sum(1)
    return q, nq, cnt


def directional_samples(P, n, vox):
    """Oriented, denoised surface samples from raw points + normals: dict s, n, w, bin (all bins merged)."""
    out_s, out_n, out_w, out_b = [], [], [], []
    for b, ax in enumerate(AXES):
        m = n @ ax > COS_BIN
        if m.sum() < 50:
            continue
        inv, ng = _voxel_groups(P[m], vox)
        Cb, Wb = _group_mean(inv, ng, P[m])
        Nb, _ = _group_mean(inv, ng, n[m]); Nb = _unit(Nb)
        q, nq, cnt = _mls_project(Cb, Nb, Wb)
        keep = (cnt >= MIN_NB) & (nq @ ax > COS_BIN * 0.8)
        # merge the collapsed layers on a VOXEL/2 grid
        inv2, n2 = _voxel_groups(q[keep], vox / 2)
        s2, w2 = _group_mean(inv2, n2, q[keep], Wb[keep])
        n2v, _ = _group_mean(inv2, n2, nq[keep], Wb[keep])
        out_s.append(s2); out_n.append(_unit(n2v)); out_w.append(w2); out_b.append(np.full(n2, b))
    return dict(s=np.concatenate(out_s), n=np.concatenate(out_n), w=np.concatenate(out_w), bin=np.concatenate(out_b))


# ---------------------------------------------------------------------------------------------- 3. two-sided thickness
def two_sided_thickness(S, N):
    """Measured wall thickness per sample (NaN where the other face was not observed)."""
    T = np.full(len(S), np.nan)
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
            T[todo[hit]] = depth[hit]
            todo = todo[~hit]
    meas = np.nonzero(np.isfinite(T))[0]
    if len(meas) >= 8:                                  # median over the 8 nearest measured samples
        _, nb = cKDTree(S[meas]).query(S[meas], k=8, workers=2)
        T[meas] = np.median(T[meas][nb], 1)
    T[meas] = np.clip(T[meas], T_FLOOR, D_MAX)
    return T


# ---------------------------------------------------------------------------------------------- 4. solid field + MC
def shell_field(S, N, tau, offset, rdisk, pitch):
    """Narrow-band grid of U(x) = min_j [dist(x, disc_j) - tau_j/2]; +pitch*4 outside the band."""
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


# ---------------------------------------------------------------------------------------------- 5. islands, 6. decimate
def clean_islands(m, P, F):
    parts = m.split(only_watertight=False)
    if len(parts) <= 1:
        return m, [dict(area_cm2=round(m.area * 1e4, 2), kept=True, why='single')]
    parts = sorted(parts, key=lambda q: q.area, reverse=True)
    main = parts[0]; tmain = cKDTree(main.vertices)
    nfr_all = len(np.unique(F)); fmin = max(F_MIN_ABS, int(math.ceil(F_MIN_FRAC * nfr_all)))
    rng = np.random.default_rng(0); sub = rng.choice(len(P), min(len(P), 400000), replace=False)
    Ps, Fs = P[sub], F[sub]
    keep, rep = [main], [dict(area_cm2=round(main.area * 1e4, 2), kept=True, why='largest')]
    for q in parts[1:]:
        dist = float(tmain.query(q.vertices, k=1)[0].min())
        near_pts = np.unique(Fs[cKDTree(q.vertices).query(Ps, k=1, distance_upper_bound=0.003)[1] < len(q.vertices)])
        ok = (len(near_pts) >= fmin) and (q.area >= A_MIN) and (dist <= NEAR)
        why = 'kept' if ok else ('frames' if len(near_pts) < fmin else 'area' if q.area < A_MIN else 'far')
        rep.append(dict(area_cm2=round(q.area * 1e4, 2), frames=int(len(near_pts)), dist_mm=round(dist * 1e3, 1),
                        kept=bool(ok), why=why))
        if ok:
            keep.append(q)
    return trimesh.util.concatenate(keep), rep


def decimate(m, max_faces):
    if len(m.faces) <= max_faces:
        return m, False
    import fast_simplification
    for red in (1 - max_faces / len(m.faces), 1 - 2 * max_faces / len(m.faces)):
        if red <= 0:
            break
        v, f = fast_simplification.simplify(np.asarray(m.vertices, np.float32), np.asarray(m.faces), target_reduction=red)
        d = trimesh.Trimesh(v.astype(np.float64), f, process=True)
        if d.is_watertight:
            return d, True
    return m, False


# ---------------------------------------------------------------------------------------------- driver
def thin_shell(obs, t=0.0025, voxel=0.002, mode='oriented', two_sided=True, max_faces=MAX_FACES, pitch=None,
               return_report=False, **kw):
    """obs dict (pts, cam, frame) -> watertight trimesh.Trimesh: a closed thin shell of thickness t on the observed
    surfaces. mode 'oriented' (solid behind the observed face) or 'symmetric' (+-t/2). With two_sided, walls whose
    both faces were observed take their measured thickness. return_report=True -> (mesh, report)."""
    t0 = time.time(); rep = dict(t_mm=t * 1e3, voxel_mm=voxel * 1e3, mode=mode, two_sided=bool(two_sided))
    P = np.asarray(obs['pts'], np.float64); C = np.asarray(obs['cam'], np.float64)
    F = np.asarray(obs['frame']) if 'frame' in obs else np.zeros(len(P), int)
    ok = np.all(np.isfinite(P), 1) & np.all(np.isfinite(C), 1)
    P, C, F = P[ok], C[ok], F[ok]
    rep.update(points=int(len(P)), frames=int(len(np.unique(F))))
    n, planar = point_normals(P, C, voxel)
    rep['weak_normal_frac'] = round(float((planar < PLANAR_MIN).mean()), 3)
    front = np.einsum('ij,ij->i', n, _unit(C - P)) >= COS_GRAZE
    rep['grazing_dropped_frac'] = round(float(1 - front.mean()), 3)
    P, C, F, n = P[front], C[front], F[front], n[front]
    ts = time.time()
    smp = directional_samples(P, n, voxel)
    S, N = smp['s'], smp['n']
    rep['samples'] = int(len(S)); rep['sec_fusion'] = round(time.time() - ts, 1)
    T = two_sided_thickness(S, N) if two_sided else np.full(len(S), np.nan)
    meas = np.isfinite(T)
    rep['two_sided_frac'] = round(float(meas.mean()), 3)
    if meas.any():
        rep['two_sided_T_mm_p10_50_90'] = np.round(np.percentile(T[meas], [10, 50, 90]) * 1e3, 2).tolist()
    tau = np.where(meas, T, t)
    offset = tau / 2 if mode == 'oriented' else np.zeros(len(S))
    if mode == 'symmetric':
        tau = np.full(len(S), t)                          # symmetric tube: one thickness everywhere
    pitch = pitch or min(voxel, 0.95 * t / math.sqrt(3))
    rdisk = R_DISK_FRAC * voxel
    ts = time.time()
    U, lo, nband = shell_field(S, N, tau, offset, rdisk, pitch)
    rep.update(pitch_mm=round(pitch * 1e3, 3), grid=list(U.shape), band_voxels=nband)
    m = march(U, lo, pitch); del U
    rep['sec_field_mc'] = round(time.time() - ts, 1); rep['faces_mc'] = int(len(m.faces))
    m, isl = clean_islands(m, P, F)
    rep['islands'] = isl[:12]; rep['islands_total'] = len(isl); rep['islands_dropped'] = int(sum(not r['kept'] for r in isl))
    m, dec = decimate(m, max_faces)
    rep.update(decimated=dec, faces=int(len(m.faces)), watertight=bool(m.is_watertight),
               bodies=int(len(m.split(only_watertight=False))), area_cm2=round(m.area * 1e4, 1),
               volume_cm3=round(float(m.volume) * 1e6, 2) if m.is_watertight else None,
               extents_cm=np.round(m.extents * 100, 1).tolist(), sec=round(time.time() - t0, 1))
    m.metadata['shell_report'] = rep
    return (m, rep) if return_report else m


def main():
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument('obj'); p.add_argument('ep', type=int); p.add_argument('out')
    p.add_argument('--t', type=float, default=0.0025); p.add_argument('--voxel', type=float, default=0.002)
    p.add_argument('--mode', default='oriented'); p.add_argument('--refined', default='auto')
    p.add_argument('--no_two_sided', action='store_true'); p.add_argument('--max_faces', type=int, default=MAX_FACES)
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
                        two_sided=not a.no_two_sided, max_faces=a.max_faces, return_report=True)
    m.export(a.out)
    rep.update(obs=path, out=a.out)
    print(json.dumps(rep))


if __name__ == '__main__':
    main()
