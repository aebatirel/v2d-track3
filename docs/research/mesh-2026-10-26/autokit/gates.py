"""GT-free mesh gates and selector v2 of the autokit engine (stage 1, builder "gates", 2026-10-27).

One module replaces the three uncommitted selector versions of the probes (P1 select_frozen.py, P2 run_p2.py gates,
autoloop_probe/fs_fidelity.py) and fixes the defects they exposed:
  - fs_frac (share of mesh area in voxels our depth saw through) is one-sided: deleting a wall LOWERS it. Here it is
    paired with a per-frame COMPLETENESS term and a coherent-HOLE term from a depth render (two-sided);
  - the recall floor was anchored to the thick library_v3 mesh (low recall, so the floor was loose): the floors here
    are absolute module constants;
  - connectivity was not checked: CONN gate (largest touching group + small compact balls hold >= 98 % of area);
  - topology was measured after decimation: watertightness is now measured on the mesh as built, the face count
    after the kit packer's budget_mesh (the scorer's decode).

Measures per (mesh, episode) [all GT-free]:
  dr_*     depth-render consistency on N_FRAMES frames spread evenly over the episode. Per frame the candidate mesh
           (as the scorer decodes it: budget_mesh) is splatted into that frame's camera (OUR track cam_T_<obj>
           composed with refine.py's per-frame correction when the obs file is a refined copy; rectified-left K of
           io_gt.load_calib) on a CELL_PX pixel grid, and compared with the frame's own observed object points
           (obs_points.py: stereo depth samples that survived the table / hand / other-object / vote filters, so a
           cell is judged only where the object was observable; hands and other objects in front of it left no
           points there):
             viol  = share of judged mesh cells whose FIRST mesh surface lies in front of the observed surface by more
                     than M_PREC (the camera saw through it: mesh in observed free space). Judged = the cell holds
                     observed points; the observed depth is the minimum over a disk of LAT_PREC lateral reach
                     (v2; v1 used the 3x3 cells).               precision = 1 - viol
             comp  = share of observed points with a mesh surface within M_COMP along their ray (any mesh sample
                     in the 3x3 cell neighbourhood within M_COMP in depth; not only the first surface).
             hole3d = observed points of the selected frames on a HOLE_VOX object-frame voxel grid: a voxel is
                     unexplained when >= half of its points are; share of the observed voxels in the LARGEST
                     26-connected unexplained group (a missing wall is a large coherent hole; noise is scattered).
             hole2d = per frame, largest 8-connected group of unexplained observed cells / observed cells (p90).
  fs_frac  share of mesh area in voxels of the episode's 4 mm vote grid seen empty (free >= FS_FMIN, hits <= FS_RHO
           free; autoloop_probe/fs_fidelity.py formula, one-sided: reported and loosely gated, never ranked alone)
  fid_*    obs_fidelity.py sum_mm (same formula: 300k obs points rng(0), 200k samples seed 0, trim 0.9, mesh->obs
           inside the obs AABB), on the mesh as built (reproduces the numbers of earlier rounds)
  conn_*   components of the mesh as built; groups = components whose surfaces come within TOUCH; balls = small
           compact components (equivalent diameter <= BALL_D_MAX, sphericity >= BALL_SPHER_MIN) within BALL_LINK of
           the main group (marker balls on unmodelled stems: a dataset-level generic, no object knowledge)
  topo_*   every body watertight before decimation; budget_mesh decodes; non-degenerate faces after it <= 4096
  frame_med_mm  median distance of mesh samples to library_v3 surface samples, no registration (frame sanity)
  flip_*   pipeline/mesh_gates.py flip_check vs library_v3 (eval seeds of the object + extra to 6), kit V2D_KIT
  drift_*  area and area-weighted RMS-radius ratios vs library_v3 (the CD-O scale normaliser), report only: the
           library's walls are thick, so it is not a target
Gates (all frozen module constants, set 2026-10-27 BEFORE any stage-2 candidate exists; see THRESHOLDS):
  G_COMP dr_comp >= COMP_MIN; G_HOLE dr_hole3d <= HOLE_MAX; G_PREC dr_viol <= VIOL_MAX; G_FS fs_frac <= FS_MAX;
  G_CONN conn_share >= CONN_MIN; G_TOPO; G_FRAME frame_med_mm < FRAME_MM; G_FLIP 0 flips.
select(rows): rows of one object; library_v3 rows are the fallback (always eligible, never gated); among eligible
rows the frozen rank RANK = dr_cdist_mm + dr_pdist_mm (two-sided truncated depth residual along the camera rays,
judged only where observed, see rank_score), ties broken by fid_sum_mm. Several episodes of one mesh: it must pass
on every episode; its rank is the mean. fid_sum_mm is not the rank: its mesh->obs half penalises every surface inside
the observed bounding box that the camera never saw (closed undersides, inner floors), the depth render does not.

Threshold rationale (frozen 2026-10-27, before any stage-2 candidate; the margins come from the data-only noise study
test_gates.py noise, run before any candidate was scored with these gates; the gate levels are declared, not fitted):
  LAT_PREC = 6 mm (v2, post hoc): see the comment at the constant (depth-edge filter gap + track jitter; the
    critic's GT-free between-frame spread on one thin appendage was 5.6-9.3 mm).
  M_PREC = M_COMP = 6 mm: leave-frames-out self-consistency of our points (8 public episodes): per-point |depth -
    median depth of the other frames| p90 = 2.9-7.4 mm (median 5.0); 6 mm covers p90 on 6 of 8 episodes. Precision
    uses the nearest observed depth of the 3x3 neighbourhood and completeness the nearest mesh sample, both less
    noise-sensitive than that statistic. CAP = 2 x M_COMP.
  COMP_MIN = 0.80: the worst calibration episode explains 0.836 of its points within 6 mm of its own other-frame
    consensus; a mesh that explains < 0.80 misses observed structure beyond noise.
  HOLE_MAX = 0.04: largest coherent unexplained surface patch <= 4 % of the observed voxels. Noise leaves scattered
    unexplained voxels; a missing part is coherent. Declared level (no calibration set without the known failures).
  VIOL_MAX = 0.05: at most 5 % of the judged mesh cells may lie > 6 mm in front of all observed surface nearby.
  FS_MAX = 0.15: coarse backstop for protrusions outside the silhouette (4 mm grid, 10 mm free threshold); one-sided,
    never ranked. Lenient on purpose: an earlier probe measured 8.5 % on a hand-kit fit with this formula.
  CONN_MIN = 0.98, FRAME_MM = 5 mm: owner's stage-1 brief. Ball rule sizes: marker spheres are ~1-2 cm (dataset-level).

GT-free: observed points, vote grids, our tracks and the calibration are read only through autokit/io_gt.py
(scans, *_align files, mocap and parquet pose fields are refused there); refine.py correction files are opened only
after io_gt.check_path; meshes are candidates or our own library_v3. No object name or per-object constant appears
here: the object name is an input (it selects the track key, the library mesh and the kit's eval-seed roster).

Versions (all GT-free; post-hoc validation on existing meshes, test_gates.py validate):
  v1 (sha256 08b8d010...; validate run 2, raw observations, 3x3 reach in both tests; constants set before the run):
     negative controls, P2 picks and P1 fragmented picks rejected; 1 of 4 incumbents passes; the other three
     FAIL G_PREC (9.5 / 8.0 / 13.5 %), two of them also G_HOLE (4.6 / 5.0 %).
  v2 (sha256 671248ec... as run; this file differs from it in comments only): set POST HOC after v1 and two
     diagnostics on the same validation meshes, declared before its own run, no tuning after it: observations =
     refine.py copies (per-frame track correction; evaluate() composes the correction into the track), LAT_PREC 6 mm,
     LAT_COMP one cell, gate levels unchanged. Result: 18 of 19 declared expectations met; one lathe incumbent
     fails G_PREC (7.9 %; its violations sit at the top / outermost radius quintile, the appendage region).
     Because v2 was chosen after seeing v1 on these meshes, this validation is NOT independent: stage 2 must
     re-validate on held-out meshes / episodes before the gates are trusted.
  Use refined observations (--refined / io_gt.obs_path(..., refined=True)) with v2: its levels were checked only there.

Usage:
  python gates.py eval MESH.glb OBJ EP [--obs OBS.npz[,OBS2.npz]] [--refined] [--no-flip] [--out ROWS.jsonl]
  python gates.py select ROWS.jsonl                     (rows of one object; prints the pick and the reasons)
  from autokit.gates import evaluate, select
"""
import argparse, json, math, os, re, sys, time

import numpy as np
import trimesh
from scipy import ndimage
from scipy.spatial import cKDTree

HERE = os.path.dirname(os.path.abspath(__file__))
if os.path.dirname(HERE) not in sys.path:
    sys.path.insert(0, os.path.dirname(HERE))
from autokit import io_gt  # noqa: E402

REPO = os.path.abspath(os.path.join(HERE, '..', '..', '..', '..'))
LIB_DIR = f'{REPO}/meshes/library_v3'
PIPELINE = f'{REPO}/pipeline'
KIT_DEFAULT = f'{io_gt.SCRATCH}/kit/v2d_submission_kit'
BUDGET = 4096

# ------------------------------------------------------------------------------------------------ frozen constants
# depth render
N_FRAMES = 32           # frames per episode, evenly spread over the observed frames (task floor: >= 20)
CELL_PX = 2             # render cell (px); at fx 600 px and 0.4-0.8 m one cell is 1.3-2.7 mm
Z_NEAR = 0.05           # m, as obs_points.py
SAMPLE_DENS = 4.0e6     # mesh samples per m^2 (4 per mm^2: >= 5 samples per cell at 0.4 m, normal incidence)
N_SAMP_MIN, N_SAMP_MAX = 200_000, 1_500_000
M_PREC = 0.006          # m: mesh surface in front of the observed surface by more than this = violation
M_COMP = 0.006          # m: an observed point is explained by a mesh surface within this along its ray
CAP = 0.012             # m: truncation of the continuous rank distances (2 x M_COMP)
# lateral reach of the two tests (None = one cell, the 3x3 neighbourhood); per frame r = fx LAT / (z_med CELL_PX) cells.
# v2 (2026-10-27, POST HOC, after validate run 2): obs_points.py's depth-edge filter (5x5 range > 2 cm) removes ~2 px on
# BOTH sides of every internal depth edge (rims, handles), so a 3x3 window never reaches the near side; with track
# jitter a correct rim then lies 'in front of' the far-side points. Precision gets a 6 mm (= M_PREC, isotropic)
# lateral reach; completeness keeps one cell (the hole test needs it tight; diag on refined points, see test_gates).
LAT_PREC = 0.006
LAT_COMP = None
HOLE_VOX = 0.004        # m, object-frame voxel of the hole statistic (= obs_points.py VOX)
HOLE_MIN_PTS = 2        # points a voxel needs to count as observed
HOLE_UNEXP = 0.5        # share of a voxel's points unexplained for the voxel to be unexplained
# free-space term (autoloop_probe/fs_fidelity.py)
FS_FMIN, FS_RHO = 3, 0.2
# obs_fidelity.py
FID_NOBS, FID_NSAMP, FID_TRIM = 300_000, 200_000, 0.9
# connectivity
TOUCH = 0.002           # m: components whose surfaces come this close form one group (unioned or overlapping parts)
BALL_D_MAX = 0.030      # m: equivalent diameter of a 'ball' component (marker spheres)
BALL_SPHER_MIN = 0.85   # sphericity pi^(1/3) (6V)^(2/3) / A of a 'ball'
BALL_LINK = 0.030       # m: a ball must lie this close to the main group
# gates
COMP_MIN = 0.80
HOLE_MAX = 0.04
VIOL_MAX = 0.05
FS_MAX = 0.15
CONN_MIN = 0.98
FRAME_MM = 5.0
THRESHOLDS = dict(N_FRAMES=N_FRAMES, CELL_PX=CELL_PX, M_PREC=M_PREC, M_COMP=M_COMP, CAP=CAP, LAT_PREC=LAT_PREC, LAT_COMP=LAT_COMP, HOLE_VOX=HOLE_VOX,
                  HOLE_MIN_PTS=HOLE_MIN_PTS, HOLE_UNEXP=HOLE_UNEXP, FS_FMIN=FS_FMIN, FS_RHO=FS_RHO, TOUCH=TOUCH,
                  BALL_D_MAX=BALL_D_MAX, BALL_SPHER_MIN=BALL_SPHER_MIN, BALL_LINK=BALL_LINK, COMP_MIN=COMP_MIN,
                  HOLE_MAX=HOLE_MAX, VIOL_MAX=VIOL_MAX, FS_MAX=FS_MAX, CONN_MIN=CONN_MIN, FRAME_MM=FRAME_MM,
                  BUDGET=BUDGET)
GATE_NAMES = ('G_COMP', 'G_HOLE', 'G_PREC', 'G_FS', 'G_CONN', 'G_TOPO', 'G_FRAME', 'G_FLIP')

_CACHE = {}


# ------------------------------------------------------------------------------------------------ mesh loading
def mesh_gates():
    """pipeline/mesh_gates.py with the kit at V2D_KIT (default: the scratchpad kit)."""
    if 'MG' not in _CACHE:
        os.environ.setdefault('V2D_KIT', KIT_DEFAULT)
        if PIPELINE not in sys.path:
            sys.path.insert(0, PIPELINE)
        import mesh_gates as MG
        MG.kit(os.environ['V2D_KIT'])
        _CACHE['MG'] = MG
    return _CACHE['MG']


def load_raw(path):
    """The mesh as built (trimesh's own vertex merge, as obs_fidelity.py loads it)."""
    return trimesh.load(path, force='mesh')


def load_budget(path):
    """The mesh as the scorer decodes it: kit budget_mesh (weld, simplify to 4096 faces / vertices, pad), with the
    zero-area padding rows dropped."""
    v, f = mesh_gates().load_candidate(path)
    tri = v[f]
    ar = 0.5 * np.linalg.norm(np.cross(tri[:, 1] - tri[:, 0], tri[:, 2] - tri[:, 0]), axis=1)
    return trimesh.Trimesh(v, f[ar > 1e-14], process=True)


def lib_path(obj):
    return f'{LIB_DIR}/{obj}.glb'


def _area_rms(m):
    """Area and area-weighted RMS radius of the face centres about the area centroid (CD-O's scale normaliser)."""
    A = m.area_faces; c = m.triangles_center
    cen = (A[:, None] * c).sum(0) / A.sum()
    return float(A.sum()), float(np.sqrt((A * ((c - cen) ** 2).sum(1)).sum() / A.sum()))


def _samples(m, seed=0):
    n = int(np.clip(m.area * SAMPLE_DENS, N_SAMP_MIN, N_SAMP_MAX))
    return trimesh.sample.sample_surface(m, n, seed=seed)[0].astype(np.float64)


# ------------------------------------------------------------------------------------------------ cameras
def ep_of(path, default):
    m = re.search(r'ep(\d+)_', os.path.basename(path))
    return int(m.group(1)) if m else int(default)


def frame_cams(obs_file, obj, ep):
    """cam_T_obj (T,4,4) of OUR track for this observation file. A refined copy (refine.py) comes with OUT.corr.npz:
    p_ref = R (p - c0) + c0 + t, so the corrected track is cam_T_obj[f] @ inv([R | c0 + t - R c0])."""
    T = io_gt.load_poses(ep)[f'cam_T_{obj}'].copy()
    corr = obs_file[:-4] + '.corr.npz' if obs_file.endswith('.npz') else None
    n_corr = 0
    if corr and os.path.isfile(corr):
        io_gt.check_path(corr)
        with np.load(corr, allow_pickle=False) as C:
            fr, R, t, c0 = C['frame'], C['R'], C['t'], C['c0']
        for k in range(len(fr)):
            A = np.eye(4); A[:3, :3] = R[k]; A[:3, 3] = c0 + t[k] - R[k] @ c0
            T[int(fr[k])] = T[int(fr[k])] @ np.linalg.inv(A)
            n_corr += 1
    return T, n_corr


def pick_frames(frames, n=N_FRAMES):
    """Up to n observed frame ids evenly spread over the episode (by rank among the observed frames)."""
    u = np.unique(frames)
    if len(u) <= n:
        return u
    return u[np.unique(np.round(np.linspace(0, len(u) - 1, n)).astype(int))]


def _project(X, T, K, wc, hc):
    """Object-frame points -> (row index kept, cell key, cell u, cell v, depth z) on the CELL_PX grid."""
    Xc = X @ T[:3, :3].T + T[:3, 3]
    z = Xc[:, 2]
    ok = z > Z_NEAR
    idx = np.nonzero(ok)[0]
    z = z[idx]
    u = K[0, 0] * Xc[idx, 0] / z + K[0, 2]
    v = K[1, 1] * Xc[idx, 1] / z + K[1, 2]
    cu = np.floor(u / CELL_PX).astype(np.int64); cv = np.floor(v / CELL_PX).astype(np.int64)
    ins = (cu >= 0) & (cu < wc) & (cv >= 0) & (cv < hc)
    idx, cu, cv, z = idx[ins], cu[ins], cv[ins], z[ins]
    return idx, cv * wc + cu, cu, cv, z


def _cell_min(key, z):
    """Unique cell keys and the minimum depth per cell."""
    o = np.lexsort((z, key))
    k = key[o]
    first = np.r_[True, k[1:] != k[:-1]]
    return k[first], z[o][first]


# ------------------------------------------------------------------------------------------------ depth render
def disk(r):
    """Cell offsets (dv, du) of a disk of radius r cells (r = 1: the 3x3 square)."""
    if r <= 1:
        return [(dv, du) for dv in (-1, 0, 1) for du in (-1, 0, 1)]
    return [(dv, du) for dv in range(-r, r + 1) for du in range(-r, r + 1) if dv * dv + du * du <= r * r + r]


def nearest_dz(ks, zs, ko, zo, cuo, cvo, wc, hc, offsets=None):
    """Per observed point (cell key ko, cell coords cuo / cvo, depth zo): the smallest |z_sample - zo| over the
    samples (keys ks, depths zs) in its 3x3 cell neighbourhood (inf if none). Sorted (cell, depth) search: the
    nearest depth within a cell is a neighbour in the sorted order."""
    o = np.lexsort((zs, ks)); ks_s, zs_s = ks[o], zs[o]
    comb = ks_s.astype(np.float64) * 16.0 + zs_s                   # depths < 16 m
    best = np.full(len(ko), np.inf)
    if not len(comb):
        return best
    for dv, du in (offsets or disk(1)):
        ok = np.nonzero((cuo + du >= 0) & (cuo + du < wc) & (cvo + dv >= 0) & (cvo + dv < hc))[0]
        k = ko[ok] + dv * wc + du
        j = np.searchsorted(comb, k.astype(np.float64) * 16.0 + zo[ok])
        for jj in (j - 1, j):
            jv = np.clip(jj, 0, len(comb) - 1)
            d = np.where((jj >= 0) & (jj < len(comb)) & (ks_s[jv] == k), np.abs(zs_s[jv] - zo[ok]), np.inf)
            best[ok] = np.minimum(best[ok], d)
    return best


def depth_render(S, obs_list, K, size):
    """Two-sided per-frame depth-render consistency of mesh samples S (object frame) against observations.
    obs_list: [(pts, frame, cam_T_obj)] per episode. Returns pooled metrics and per-frame rows."""
    W, H = size
    wc, hc = int(math.ceil(W / CELL_PX)), int(math.ceil(H / CELL_PX))
    n_viol = n_judged = n_pts = n_expl = 0
    c_sum = p_sum = 0.0
    per = []
    P_all, E_all = [], []
    for pts, frame, T_co in obs_list:
        for f in pick_frames(frame):
            sel = np.nonzero(frame == f)[0]
            P = pts[sel].astype(np.float64)
            T = T_co[int(f)]
            io, ko, cuo, cvo, zo = _project(P, T, K, wc, hc)
            if len(io) < 50:
                continue
            ism, ks, cus, cvs, zs = _project(S, T, K, wc, hc)
            # --- completeness: any mesh sample in the 3x3 cell neighbourhood within M_COMP in depth
            zmed = float(np.median(zo))
            rc = 1 if LAT_COMP is None else max(1, int(math.ceil(K[0, 0] * LAT_COMP / (zmed * CELL_PX))))
            rp = 1 if LAT_PREC is None else max(1, int(math.ceil(K[0, 0] * LAT_PREC / (zmed * CELL_PX))))
            r = max(rc, rp)
            dzn = nearest_dz(ks, zs, ko, zo, cuo, cvo, wc, hc, disk(rc))
            expl = dzn <= M_COMP
            # --- precision: first mesh surface vs the min observed depth over the 3x3 neighbourhood
            mk, mz = _cell_min(ks, zs)
            okey, oz = _cell_min(ko, zo)
            u0, v0 = cuo.min() - r, cvo.min() - r
            gw, gh = cuo.max() - u0 + r + 1, cvo.max() - v0 + r + 1
            G = np.full((gh, gw), np.inf)
            G[okey // wc - v0, okey % wc - u0] = oz
            fp = np.zeros((2 * rp + 1, 2 * rp + 1), bool)
            for dv, du in disk(rp):
                fp[dv + rp, du + rp] = True
            Gmin = ndimage.minimum_filter(G, footprint=fp, mode='constant', cval=np.inf)
            common, im, iob = np.intersect1d(mk, okey, assume_unique=True, return_indices=True)
            zref = Gmin[common // wc - v0, common % wc - u0]
            front = zref - mz[im]                                       # > 0: mesh in front of observed surface
            viol = front > M_PREC
            # --- 2-D hole: largest 8-connected group of unexplained observed cells
            U = np.zeros((gh, gw), bool)
            U[cvo[~expl] - v0, cuo[~expl] - u0] = True
            lab, nl = ndimage.label(U, structure=np.ones((3, 3), bool))
            big = int(np.bincount(lab.ravel())[1:].max()) if nl else 0
            n_cells = len(okey)
            per.append(dict(frame=int(f), r_comp=rc, r_prec=rp, n_pts=int(len(io)), comp=float(expl.mean()), n_judged=int(len(common)),
                            viol=float(viol.mean()) if len(common) else 0.0, mesh_cells=int(len(mk)),
                            hole2d=big / max(n_cells, 1)))
            n_viol += int(viol.sum()); n_judged += int(len(common)); n_pts += int(len(io)); n_expl += int(expl.sum())
            c_sum += float(np.minimum(dzn, CAP).sum()); p_sum += float(np.clip(front, 0, CAP).sum())
            P_all.append(P[io]); E_all.append(expl)
    if not per:
        return dict(dr_frames=0), per
    P_all = np.concatenate(P_all); E_all = np.concatenate(E_all)
    h3, h3_cm2, n_vox = hole3d(P_all, E_all)
    comp_f = np.array([r['comp'] for r in per]); h2 = np.array([r['hole2d'] for r in per])
    vf = np.array([r['viol'] for r in per if r['n_judged'] > 0])
    return dict(dr_frames=len(per), dr_pts=n_pts, dr_comp=n_expl / max(n_pts, 1), dr_comp_frame_mean=float(comp_f.mean()),
                dr_comp_frame_p10=float(np.percentile(comp_f, 10)), dr_viol=n_viol / max(n_judged, 1),
                dr_viol_frame_p90=float(np.percentile(vf, 90)) if len(vf) else 0.0, dr_judged=n_judged,
                dr_hole3d=h3, dr_hole3d_cm2=h3_cm2, dr_obs_vox=n_vox,
                dr_hole2d_p50=float(np.median(h2)), dr_hole2d_p90=float(np.percentile(h2, 90)),
                dr_cdist_mm=c_sum / max(n_pts, 1) * 1e3, dr_pdist_mm=p_sum / max(n_judged, 1) * 1e3), per


def hole3d(P, expl):
    """Largest 26-connected group of unexplained HOLE_VOX voxels / observed voxels, and its area (cm^2, one voxel
    face per voxel: the group is a surface patch)."""
    lo = P.min(0)
    vi = np.floor((P - lo) / HOLE_VOX).astype(np.int64)
    shp = vi.max(0) + 1
    lin = (vi[:, 0] * shp[1] + vi[:, 1]) * shp[2] + vi[:, 2]
    n = np.bincount(lin, minlength=int(np.prod(shp)))
    nu = np.bincount(lin, weights=(~expl).astype(float), minlength=int(np.prod(shp)))
    obs = n >= HOLE_MIN_PTS
    un = obs & (nu >= HOLE_UNEXP * n)
    lab, nl = ndimage.label(un.reshape(shp), structure=np.ones((3, 3, 3), bool))
    big = int(np.bincount(lab.ravel())[1:].max()) if nl else 0
    return big / max(int(obs.sum()), 1), big * HOLE_VOX ** 2 * 1e4, int(obs.sum())


# ------------------------------------------------------------------------------------------------ other measures
def fs_frac(S, grids):
    """Share of mesh samples in voxels any episode's depth saw empty (fs_fidelity.py: free >= FS_FMIN and
    hits <= FS_RHO * free), and the share outside every grid."""
    emp = np.zeros(len(S), bool); inany = np.zeros(len(S), bool)
    for g in grids:
        Hg, Fg, glo, vox = g['hits'], g['free'], g['lo'], float(g['vox'])
        vi = np.floor((S - glo) / vox).astype(int)
        ok = np.all((vi >= 0) & (vi < np.array(Hg.shape)), axis=1)
        h = np.zeros(len(S)); f = np.zeros(len(S))
        h[ok] = Hg[vi[ok, 0], vi[ok, 1], vi[ok, 2]]; f[ok] = Fg[vi[ok, 0], vi[ok, 1], vi[ok, 2]]
        emp |= ok & (f >= FS_FMIN) & (h <= FS_RHO * f); inany |= ok
    return float(emp.mean()), float((~inany).mean())


def _tmean(d):
    d = np.sort(d)
    return float(d[:int(FID_TRIM * len(d))].mean() * 1000)


def fidelity(raw, P_all):
    """obs_fidelity.py on the mesh as built: obs->mesh and mesh->obs (inside the obs AABB) trimmed means, mm."""
    P = P_all[np.random.default_rng(0).choice(len(P_all), min(FID_NOBS, len(P_all)), replace=False)]
    tp = cKDTree(P); lo, hi = P.min(0), P.max(0)
    S = trimesh.sample.sample_surface(raw, FID_NSAMP, seed=0)[0]
    om = _tmean(cKDTree(S).query(P)[0])
    inb = np.all((S > lo) & (S < hi), axis=1)
    mo = _tmean(tp.query(S[inb])[0]) if inb.any() else float('nan')
    return dict(fid_om_mm=om, fid_mo_mm=mo, fid_sum_mm=om + mo)


def connectivity(raw):
    """Components of the mesh as built, grouped when their surfaces come within TOUCH; small compact components
    (balls) within BALL_LINK of the main group count with it. conn_share = (main group + linked balls) / total area."""
    comps = raw.split(only_watertight=False)
    if len(comps) == 0:
        return dict(conn_bodies=0, conn_share=0.0, conn_largest=0.0, conn_groups=0, conn_balls=0)
    areas = np.array([c.area for c in comps]); tot = areas.sum()
    smp, trees = [], []
    for i, c in enumerate(comps):
        n = int(np.clip(c.area * 1e6, 300, 200_000))           # ~1 sample per mm^2
        s = trimesh.sample.sample_surface(c, n, seed=i)[0]
        smp.append(np.vstack([s, c.vertices])); trees.append(cKDTree(smp[-1]))
    parent = list(range(len(comps)))

    def find(a):
        while parent[a] != a:
            parent[a] = parent[parent[a]]; a = parent[a]
        return a
    bmin = np.array([c.bounds[0] for c in comps]); bmax = np.array([c.bounds[1] for c in comps])
    for i in range(len(comps)):
        for j in range(i + 1, len(comps)):
            if np.any(bmin[i] > bmax[j] + TOUCH) or np.any(bmin[j] > bmax[i] + TOUCH):
                continue
            if find(i) != find(j) and np.isfinite(trees[i].query(smp[j], distance_upper_bound=TOUCH)[0]).any():
                parent[find(i)] = find(j)
    roots = np.array([find(i) for i in range(len(comps))])
    g_area = {r: areas[roots == r].sum() for r in set(roots.tolist())}
    main = max(g_area, key=g_area.get)
    main_idx = np.nonzero(roots == main)[0]
    main_tree = cKDTree(np.vstack([smp[i] for i in main_idx]))
    n_balls = 0; ball_area = 0.0
    for r, a in g_area.items():
        if r == main:
            continue
        mem = np.nonzero(roots == r)[0]
        if len(mem) != 1:
            continue
        c = comps[mem[0]]
        if not c.is_watertight or c.volume <= 0:
            continue
        d_eq = (6 * c.volume / math.pi) ** (1 / 3)
        spher = math.pi ** (1 / 3) * (6 * c.volume) ** (2 / 3) / c.area
        if d_eq <= BALL_D_MAX and spher >= BALL_SPHER_MIN and \
                np.isfinite(main_tree.query(smp[mem[0]], distance_upper_bound=BALL_LINK)[0]).any():
            n_balls += 1; ball_area += a
    return dict(conn_bodies=len(comps), conn_groups=len(g_area), conn_balls=n_balls,
                conn_largest=float(areas.max() / tot), conn_main_group=float(g_area[main] / tot),
                conn_share=float((g_area[main] + ball_area) / tot))


def topology(path, raw):
    """Watertight before decimation (every body), and the kit decode (budget_mesh) face count."""
    bodies = raw.split(only_watertight=False)
    out = dict(topo_raw_faces=int(len(raw.faces)), topo_raw_bodies=int(len(bodies)),
               topo_raw_watertight=bool(len(bodies) > 0 and all(b.is_watertight for b in bodies)))
    try:
        bm = load_budget(path)
        bb = bm.split(only_watertight=False)
        out.update(topo_budget_faces=int(len(bm.faces)), topo_budget_watertight=bool(all(b.is_watertight for b in bb)),
                   topo_budget_bodies=int(len(bb)), topo_decode_error=None)
    except Exception as e:  # noqa: BLE001
        bm = None
        out.update(topo_budget_faces=None, topo_budget_watertight=None, topo_budget_bodies=None,
                   topo_decode_error=f'{type(e).__name__}: {e}'[:200])
    return out, bm


def library_ref(obj):
    """Cached library_v3 surface samples (KD-tree) and its area / RMS radius after the kit decode."""
    key = ('lib', obj)
    if key not in _CACHE:
        lm = load_budget(lib_path(obj))
        a, r = _area_rms(lm)
        _CACHE[key] = dict(tree=cKDTree(trimesh.sample.sample_surface(lm, 400_000, seed=3)[0]), area=a, rms=r)
    return _CACHE[key]


# ------------------------------------------------------------------------------------------------ evaluate
def evaluate(mesh_path, obs_paths, obj, ep, flip=True):
    """All measures and gates of one candidate mesh against the observations of one (or several) episodes.
    obs_paths: observation files (io_gt.obs_path; a refined copy brings its per-frame track correction).
    Returns dict(mesh, obj, ep, obs, metrics, gates, pass, thresholds, sec)."""
    t0 = time.time()
    if isinstance(obs_paths, str):
        obs_paths = [obs_paths]
    calib = io_gt.load_calib()
    K, size = calib['K'], calib['size']
    raw = load_raw(mesh_path)
    m = dict(raw_area_cm2=raw.area * 1e4)
    topo, bm = topology(mesh_path, raw)
    m.update(topo)
    geo = bm if bm is not None else raw                         # what the scorer sees
    S = _samples(geo)
    obs_list, grids, P_fid, ncorr = [], [], [], 0
    for p in obs_paths:
        o = io_gt.load_obs(p)
        T, nc = frame_cams(p, obj, ep_of(p, ep)); ncorr += nc
        obs_list.append((o['pts'], o['frame'], T)); P_fid.append(o['pts'].astype(np.float64))
        if all(k in o for k in ('hits', 'free', 'lo', 'vox')):
            grids.append(o)
    m['track_corrections'] = ncorr
    dr, per = depth_render(S, obs_list, K, size)
    m.update(dr)
    m['fs_frac'], m['fs_outside_grid'] = fs_frac(S, grids) if grids else (float('nan'), float('nan'))
    m.update(fidelity(raw, np.concatenate(P_fid)))
    m.update(connectivity(raw))
    lib = library_ref(obj)
    a, r = _area_rms(geo)
    m.update(frame_med_mm=float(np.median(lib['tree'].query(S[np.random.default_rng(0).choice(len(S), min(50_000, len(S)), replace=False)])[0]) * 1e3),
             drift_area=a / lib['area'], drift_rms=r / lib['rms'], area_cm2=a * 1e4, rms_mm=r * 1e3)
    if flip:
        t1 = time.time()
        fc = mesh_gates().flip_check(mesh_path, lib_path(obj), obj)
        m.update(flip_n=int(fc['n']), flips=int(fc['xflips']), flip_xadd_med_mm=float(fc['xadd_med']),
                 flip_rot=[r_['rot'] for r_ in fc['seeds']], flip_sec=round(time.time() - t1, 1))
    else:
        m.update(flip_n=0, flips=None)
    g = gates_of(m)
    return dict(mesh=os.path.abspath(mesh_path), obj=obj, ep=int(ep), obs=[os.path.abspath(p) for p in obs_paths],
                metrics={k: (round(v, 5) if isinstance(v, float) else v) for k, v in m.items()}, gates=g,
                **{'pass': all(g.values())}, rank_score=rank_score(m), per_frame=per, thresholds=THRESHOLDS,
                sec=round(time.time() - t0, 1))


def gates_of(m):
    """The frozen gates on a metrics dict (missing or NaN measure = gate fails)."""
    def ok(x):
        return x is not None and not (isinstance(x, float) and math.isnan(x))
    return dict(
        G_COMP=bool(ok(m.get('dr_comp')) and m['dr_comp'] >= COMP_MIN),
        G_HOLE=bool(ok(m.get('dr_hole3d')) and m['dr_hole3d'] <= HOLE_MAX),
        G_PREC=bool(ok(m.get('dr_viol')) and m['dr_viol'] <= VIOL_MAX),
        G_FS=bool(ok(m.get('fs_frac')) and m['fs_frac'] <= FS_MAX),
        G_CONN=bool(ok(m.get('conn_share')) and m['conn_share'] >= CONN_MIN),
        G_TOPO=bool(m.get('topo_raw_watertight') and m.get('topo_decode_error') is None
                    and ok(m.get('topo_budget_faces')) and m['topo_budget_faces'] <= BUDGET),
        G_FRAME=bool(ok(m.get('frame_med_mm')) and m['frame_med_mm'] < FRAME_MM),
        G_FLIP=bool(m.get('flips') == 0 and m.get('flip_n', 0) > 0))


def rank_score(m):
    """Frozen rank (mm, lower is better): two-sided truncated depth-render residual, judged only where observed:
    dr_cdist_mm (mean over observed points of the depth gap to the nearest mesh surface along the ray, capped at CAP:
    missing or misplaced surface) + dr_pdist_mm (mean over judged mesh cells of how far the first mesh surface lies in
    front of the observed surface, capped at CAP: extra surface in observed free space)."""
    if m.get('dr_cdist_mm') is None or m.get('dr_pdist_mm') is None:
        return float('inf')
    return round(m['dr_cdist_mm'] + m['dr_pdist_mm'], 5)


# ------------------------------------------------------------------------------------------------ select
def is_fallback(row):
    return bool(row.get('fallback')) or os.path.dirname(os.path.abspath(row['mesh'])) == os.path.abspath(LIB_DIR)


def select(rows):
    """Gates, then the frozen rank. rows: evaluate() outputs of ONE object (one or several episodes per mesh).
    library_v3 rows are the fallback: always eligible, never gated. A mesh evaluated on several episodes must pass on
    each; its rank is the mean rank score (ties: lower mean fid_sum_mm). Returns dict(pick, reasons, ranking)."""
    by = {}
    for r in rows:
        by.setdefault(r['mesh'], []).append(r)
    reasons, elig = {}, []
    for mesh, rs in by.items():
        fb = any(is_fallback(r) for r in rs)
        failed = sorted({f'{k}@ep{r["ep"]}' for r in rs for k, v in r['gates'].items() if not v})
        passed = all(r['pass'] for r in rs)
        score = float(np.mean([r['rank_score'] for r in rs]))
        fid = float(np.mean([r['metrics'].get('fid_sum_mm', np.inf) for r in rs]))
        reasons[mesh] = dict(fallback=fb, passed=passed, failed=failed, rank_score=round(score, 5),
                             fid_sum_mm=round(fid, 3), episodes=sorted({r['ep'] for r in rs}))
        if passed or fb:
            elig.append((score, fid, mesh))
    elig.sort()
    pick = elig[0][2] if elig else None
    for i, (_, _, mesh) in enumerate(elig):
        reasons[mesh]['rank'] = i + 1
    return dict(pick=pick, reasons=reasons, ranking=[e[2] for e in elig])


# ------------------------------------------------------------------------------------------------ CLI
def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    sub = ap.add_subparsers(dest='cmd', required=True)
    e = sub.add_parser('eval'); e.add_argument('mesh'); e.add_argument('obj'); e.add_argument('ep', type=int)
    e.add_argument('--obs', default=None); e.add_argument('--refined', action='store_true')
    e.add_argument('--no-flip', action='store_true'); e.add_argument('--out', default=None)
    s = sub.add_parser('select'); s.add_argument('rows')
    a = ap.parse_args()
    if a.cmd == 'eval':
        obs = a.obs.split(',') if a.obs else [io_gt.obs_path(a.obj, a.ep, refined=a.refined)]
        r = evaluate(a.mesh, obs, a.obj, a.ep, flip=not a.no_flip)
        r.pop('per_frame')
        print(json.dumps(r, default=str))
        if a.out:
            with open(a.out, 'a') as f:
                f.write(json.dumps(r, default=str) + '\n')
    else:
        rows = [json.loads(l) for l in open(a.rows) if l.strip()]
        print(json.dumps(select(rows), indent=1))


if __name__ == '__main__':
    main()
