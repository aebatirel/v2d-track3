"""GT-free mesh gates and selector v3 of the autokit engine (stage 1b, fixer "gates", 2026-10-29).

v3 fixes the stage-1 audit findings on v2 (results/autokit-stage1/workflow-result.json):
  - selector: route-A standalone shells (and earlier-round incumbents) are NOT selectable; they are reported as
    diagnostic rows. Selectable = part-program (route B) builds, which may contain shell_patch parts, and the
    library_v3 fallback. Within a program the unseen thickness t is NOT chosen by the rank (the rank only sees
    observed surface, so it is monotone in t by construction): the grid middle T_MID = 2.5 mm build is the selectable
    one; the other grid builds are diagnostic. Where the program measured the thickness of every thickness-bearing
    part (two-sided / side evidence) its builds do not depend on t, and the build closest to T_MID stands for it;
  - precision outside the observed silhouette: per frame, a first-surface mesh cell with NO observed point within the
    precision reach is judged against the episode's vote grid: a violation when its voxel was seen through
    (free >= FS_FMIN, hits <= FS_RHO free: our rays passed it and met a surface >= 1 cm behind). dr_fsv = violating
    cells / all first-surface mesh cells; dr_fsv_blob_p75_cm2 = p75 over frames of the largest 8-connected group of
    violating cells as a surface area; G_PREC = dr_viol <= VIOL_MAX AND dr_fsv <= FSV_MAX AND blob <= FSV_BLOB_MAX;
    the rank adds CAP x dr_fsv;
  - frame / shift: G_FRAME adds an alignment test, a trimmed point-to-plane ICP of the observed points onto the
    mesh, each point paired with a mesh sample facing its camera (align_t_mm = translation of the observed centroid;
    a mesh fitted to these points needs ~0, a mesh that disagrees with them in a rigid way does not). It cannot tell a
    rigid offset from a systematic misfit under one-sided coverage: both fail it;
  - projection: cell index floor((u + 0.5) / CELL_PX) (observed points are back-projected at integer pixel centres,
    obs_points.py; v2's floor(u / CELL_PX) put the mesh footprint half a pixel off);
  - observations: RAW obs files are the default (evaluate(obs='raw')); refine.py copies only on request
    (obs='refined'), because refine's own pre-registered falsifier failed and it slides frames along weak axes;
  - topology and area AFTER the kit decode (budget_mesh): every decoded body watertight, decoded bodies <= bodies as
    built, |area change| <= AREA_TOL, faces <= 4096; connectivity is measured on the decoded mesh too;
  - inputs: meshes only through io_gt.load_mesh / io_gt.mesh_input (deny-list + allow-listed roots, sha256 logged);
    each evaluate() row carries the sha256 of every input it opened.

Measures per (mesh, episode) [all GT-free]:
  dr_*     depth-render consistency on N_FRAMES frames spread evenly over the episode (or over a given frame subset).
           Per frame the decoded candidate (budget_mesh, what the scorer sees) is splatted into that frame's camera
           (OUR track cam_T_<obj>, composed with refine.py's per-frame correction only for a refined copy; rectified-left
           K of io_gt.load_calib) on a CELL_PX pixel grid and compared with the frame's own observed object points:
             viol   = share of judged mesh cells (cells that hold observed points) whose FIRST mesh surface lies in front
                      of the minimum observed depth within LAT_PREC by more than M_PREC.        precision = 1 - viol
             fsv    = share of all first-surface mesh cells that have NO observed point within LAT_PREC and whose
                      first-surface voxel the vote grid saw as empty (outside-silhouette precision, new in v3)
             comp   = share of observed points with a mesh sample within M_COMP in depth in the 3x3 cell neighbourhood
             hole3d = largest 26-connected group of unexplained HOLE_VOX voxels / observed voxels (coherent holes)
             hole2d = per frame, largest 8-connected group of unexplained observed cells / observed cells (p90)
  align_*  trimmed point-to-plane ICP (ALIGN_ITERS, pairs within ALIGN_TRIM, closest 90 %) of up to ALIGN_NPTS observed
           points onto the decoded mesh: |t| of the observed centroid (mm), rotation (deg), median |residual| after
  fs_frac  share of ALL mesh samples in voxels seen empty (one-sided backstop, loosely gated, never ranked)
  fid_*    obs_fidelity.py sum_mm on the mesh as built (report only)
  conn_*   components of the DECODED mesh; groups = components whose surfaces come within TOUCH; balls = small compact
           components (equivalent diameter <= BALL_D_MAX, sphericity >= BALL_SPHER_MIN) within BALL_LINK of the main group
  topo_*   decoded mesh: faces, vertices, bodies, all bodies watertight, area and RMS-radius change vs the mesh as built
  frame_med_mm  median distance of decoded-mesh samples to library_v3 surface samples, no registration (frame sanity)
  flip_*   pipeline/mesh_gates.py flip_check vs library_v3 (eval seeds of the object + extra to 6), kit V2D_KIT
  drift_*  area and RMS-radius ratios vs library_v3 (report only)
Gates (THRESHOLDS; v3 frozen by sha256 before its pre-registered held-out validation, test_gates.py prereg):
  G_COMP dr_comp >= COMP_MIN; G_HOLE dr_hole3d <= HOLE_MAX; G_PREC dr_viol <= VIOL_MAX and dr_fsv <= FSV_MAX;
  G_FS fs_frac <= FS_MAX; G_CONN conn_share >= CONN_MIN; G_TOPO (decoded, see above);
  G_FRAME frame_med_mm < FRAME_MM and align_t_mm <= ALIGN_MAX_MM; G_FLIP 0 flips.
select(rows): selector v3, see select(). Rank = dr_cdist_mm + dr_pdist_mm + CAP_mm x dr_fsv (lower is better), ties
broken by fid_sum_mm; a mesh evaluated on several episodes must pass on each, its rank is the mean.

Threshold rationale. Levels carried over from v2 (set 2026-10-27; M_PREC / M_COMP / COMP_MIN from the data-only noise
study test_gates.py noise; HOLE_MAX, VIOL_MAX, FS_MAX, CONN_MIN, FRAME_MM declared): v2 was tuned post hoc toward four
MUST_PASS meshes whose labels came from earlier scan-scored rounds (audit finding), so none of those levels counts
as validated; v3 is re-validated on held-out episodes with synthetic GT-free labels only (test_gates.py prereg).
  LAT_PREC = 6 mm (v2, post hoc): obs_points.py's depth-edge filter removes ~2 px on both sides of internal depth
    edges; with track jitter a correct rim then lies in front of the far-side points.
  M_PREC = M_COMP = 6 mm: leave-frames-out self-consistency of our points, p90 2.9-7.4 mm (median 5.0) on 8 episodes.
  FSV_MAX = 0.05 (v3, declared before any v3 run, same level as VIOL_MAX): a cell counts only when its voxel centre
    lies >= 10 mm (obs_points.py --free) in front of a surface our rays met, in >= 3 frames, so depth noise and track
    jitter of a few mm cannot make a correct surface violate; mesh cells within LAT_PREC of observed cells are left out
    (depth-edge filter band).
  FSV_BLOB_MAX = 10 cm^2 (v3, set on the DEVELOPMENT check test_gates.py dev, before the pre-registration): the share
    alone sat just above 0.05 for an attached fin of 12 % of the area (dev 0.056 / 0.059); the coherent-region
    statistic separated dev bases (p75 0.4-5.2 cm^2) from the dev fins (17-45 cm^2); 10 cm^2 ~ geometric middle.
  ALIGN_MAX_MM = 2.0 (v3, declared): the registration-move level of pipeline/mesh_gates.registration_move (2 mm),
    a project-level GT-free level set earlier for another purpose. ALIGN_TRIM 10 mm, 90 % trim: generic. ALIGN_K
    8 -> 32 on the development check (with 8 nearest samples 25-45 % of the points found no camera-facing partner on
    thin walls, which biased the estimate; 32 covers both faces of a 2.5 mm wall at the sampling density).
  frame_t_mm (report only): the same alignment of the mesh onto library_v3. Dev check: 1.4-6.7 mm for unmodified
    meshes (shape differences dominate), not sensitive to a 5 mm shift, so it is not gated.
  AREA_TOL = 0.02: the stage-1b brief (decoded area within 2 %).
  BALL_D_MAX 30 mm / BALL_SPHER_MIN 0.85: generic 'small compact body' rule (a sphere of 3 cm diameter is the upper
    end of a hand-held attachment; no object-specific value).

GT-free: observed points, vote grids, tracks, calibration and refine corrections through autokit/io_gt.py (deny-list +
allow-listed roots); meshes through io_gt.load_mesh / io_gt.mesh_input. No object name or per-object constant appears
here: the object name is an input (track key, library mesh, the kit's eval-seed roster).

Versions: v1 sha256 08b8d010..., v2 671248ec... (as run; 72ba409 holds v2 with comments). v3 this file.
Usage:
  python gates.py eval MESH.glb OBJ EP [--obs OBS.npz[,OBS2.npz]] [--refined] [--no-flip] [--kind program|library|...]
                  [--t-mm 2.5] [--family NAME] [--out ROWS.jsonl]
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

VERSION = 'v3'
REPO = io_gt.REPO
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
LAT_PREC = 0.006
LAT_COMP = None
HOLE_VOX = 0.004        # m, object-frame voxel of the hole statistic (= obs_points.py VOX)
HOLE_MIN_PTS = 2        # points a voxel needs to count as observed
HOLE_UNEXP = 0.5        # share of a voxel's points unexplained for the voxel to be unexplained
# free-space rule of the vote grids (autoloop_probe/fs_fidelity.py): voxel seen empty
FS_FMIN, FS_RHO = 3, 0.2
# obs_fidelity.py
FID_NOBS, FID_NSAMP, FID_TRIM = 300_000, 200_000, 0.9
# alignment of the observed points onto the mesh (v3)
ALIGN_NPTS = 60_000
ALIGN_NSAMP = 200_000
ALIGN_TRIM = 0.010      # m: correspondence reach
ALIGN_KEEP = 0.9        # closest share of the pairs kept per iteration
ALIGN_ITERS = 15
ALIGN_K = 32            # nearest mesh samples searched for one facing the point's camera (both faces of a thin wall)
FRAME_NSAMP = 60_000    # decoded-mesh samples of the library alignment
# connectivity
TOUCH = 0.002           # m: components whose surfaces come this close form one group (unioned or overlapping parts)
BALL_D_MAX = 0.030      # m: equivalent diameter of a small compact body
BALL_SPHER_MIN = 0.85   # sphericity pi^(1/3) (6V)^(2/3) / A of a small compact body
BALL_LINK = 0.030       # m: such a body must lie this close to the main group
# gates
COMP_MIN = 0.80
HOLE_MAX = 0.04
VIOL_MAX = 0.05
FSV_MAX = 0.05
FSV_BLOB_MAX = 10.0     # cm^2: p75 over frames of the largest coherent outside-silhouette free-space region
FS_MAX = 0.15
CONN_MIN = 0.98
FRAME_MM = 5.0
ALIGN_MAX_MM = 2.0
AREA_TOL = 0.02
# selector v3
T_MID = 0.0025          # m: middle of the generic unseen-thickness grid {1.5, 2.5, 4.0} mm
PROGRAM_KINDS = ('program', 'dsl')
THRESHOLDS = dict(VERSION=VERSION, N_FRAMES=N_FRAMES, CELL_PX=CELL_PX, M_PREC=M_PREC, M_COMP=M_COMP, CAP=CAP,
                  LAT_PREC=LAT_PREC, LAT_COMP=LAT_COMP, HOLE_VOX=HOLE_VOX, HOLE_MIN_PTS=HOLE_MIN_PTS,
                  HOLE_UNEXP=HOLE_UNEXP, FS_FMIN=FS_FMIN, FS_RHO=FS_RHO, TOUCH=TOUCH, BALL_D_MAX=BALL_D_MAX,
                  BALL_SPHER_MIN=BALL_SPHER_MIN, BALL_LINK=BALL_LINK, ALIGN_NPTS=ALIGN_NPTS, ALIGN_TRIM=ALIGN_TRIM,
                  ALIGN_KEEP=ALIGN_KEEP, ALIGN_ITERS=ALIGN_ITERS, ALIGN_K=ALIGN_K, COMP_MIN=COMP_MIN, HOLE_MAX=HOLE_MAX,
                  VIOL_MAX=VIOL_MAX, FSV_MAX=FSV_MAX, FSV_BLOB_MAX=FSV_BLOB_MAX, FS_MAX=FS_MAX, CONN_MIN=CONN_MIN, FRAME_MM=FRAME_MM,
                  ALIGN_MAX_MM=ALIGN_MAX_MM, AREA_TOL=AREA_TOL, BUDGET=BUDGET, T_MID=T_MID)
GATE_NAMES = ('G_COMP', 'G_HOLE', 'G_PREC', 'G_FS', 'G_CONN', 'G_TOPO', 'G_FRAME', 'G_FLIP')
FLIP_KEYS = ('flip_n', 'flips', 'flip_xadd_med_mm', 'flip_rot', 'flip_sec')

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
    """The mesh as built (trimesh's own vertex merge, as obs_fidelity.py loads it), through the io_gt guard."""
    return io_gt.load_mesh(path)


def load_budget(path):
    """The mesh as the scorer decodes it: kit budget_mesh (weld, simplify to 4096 faces / vertices, pad), with the
    zero-area padding rows dropped. The path passes the io_gt guard before the kit opens it."""
    v, f = mesh_gates().load_candidate(io_gt.mesh_input(path))
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


def is_refined(path):
    """True for a refine.py copy (under io_gt.REFINED_DIR or with a .corr.npz next to it)."""
    rp = os.path.realpath(path)
    return rp.startswith(os.path.realpath(io_gt.REFINED_DIR) + '/') or (
        rp.endswith('.npz') and os.path.isfile(rp[:-4] + '.corr.npz'))


def frame_cams(obs_file, obj, ep):
    """cam_T_obj (T,4,4) of OUR track for this observation file. A refined copy (refine.py) comes with OUT.corr.npz:
    p_ref = R (p - c0) + c0 + t, so the corrected track is cam_T_obj[f] @ inv([R | c0 + t - R c0])."""
    T = io_gt.load_poses(ep)[f'cam_T_{obj}'].copy()
    corr = obs_file[:-4] + '.corr.npz' if obs_file.endswith('.npz') else None
    n_corr = 0
    if corr and os.path.isfile(corr):
        C = io_gt.load_corr(corr)
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
    """Object-frame points -> (row index kept, cell key, cell u, cell v, depth z) on the CELL_PX grid. Cells are
    centred on the integer pixel centres the observed points were back-projected at: floor((u + 0.5) / CELL_PX)."""
    Xc = X @ T[:3, :3].T + T[:3, 3]
    z = Xc[:, 2]
    ok = z > Z_NEAR
    idx = np.nonzero(ok)[0]
    z = z[idx]
    u = K[0, 0] * Xc[idx, 0] / z + K[0, 2]
    v = K[1, 1] * Xc[idx, 1] / z + K[1, 2]
    cu = np.floor((u + 0.5) / CELL_PX).astype(np.int64); cv = np.floor((v + 0.5) / CELL_PX).astype(np.int64)
    ins = (cu >= 0) & (cu < wc) & (cv >= 0) & (cv < hc)
    idx, cu, cv, z = idx[ins], cu[ins], cv[ins], z[ins]
    return idx, cv * wc + cu, cu, cv, z


def _cell_min(key, z):
    """Unique cell keys, the minimum depth per cell and the position (into key / z) of that minimum."""
    o = np.lexsort((z, key))
    k = key[o]
    first = np.r_[True, k[1:] != k[:-1]]
    return k[first], z[o][first], o[first]


def seen_empty(X, grid):
    """(judged, empty) per point X (object frame) on one vote grid: judged = inside the grid; empty = the voxel was
    seen through (free >= FS_FMIN and hits <= FS_RHO free)."""
    Hg, Fg, glo, vox = grid['hits'], grid['free'], grid['lo'], float(grid['vox'])
    vi = np.floor((X - glo) / vox).astype(np.int64)
    ok = np.all((vi >= 0) & (vi < np.array(Hg.shape)), axis=1)
    emp = np.zeros(len(X), bool)
    h = Hg[vi[ok, 0], vi[ok, 1], vi[ok, 2]]; f = Fg[vi[ok, 0], vi[ok, 1], vi[ok, 2]]
    emp[ok] = (f >= FS_FMIN) & (h <= FS_RHO * f)
    return ok, emp


# ------------------------------------------------------------------------------------------------ depth render
def disk(r):
    """Cell offsets (dv, du) of a disk of radius r cells (r = 1: the 3x3 square)."""
    if r <= 1:
        return [(dv, du) for dv in (-1, 0, 1) for du in (-1, 0, 1)]
    return [(dv, du) for dv in range(-r, r + 1) for du in range(-r, r + 1) if dv * dv + du * du <= r * r + r]


def nearest_dz(ks, zs, ko, zo, cuo, cvo, wc, hc, offsets=None):
    """Per observed point (cell key ko, cell coords cuo / cvo, depth zo): the smallest |z_sample - zo| over the
    samples (keys ks, depths zs) in its cell neighbourhood (inf if none). Sorted (cell, depth) search: the
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
    obs_list: [(pts, frame, cam_T_obj, grid or None)] per episode. Returns pooled metrics and per-frame rows."""
    W, H = size
    wc, hc = int(math.ceil(W / CELL_PX)), int(math.ceil(H / CELL_PX))
    n_viol = n_judged = n_pts = n_expl = 0
    n_mcells = n_out = n_out_judged = n_fsv = 0
    c_sum = p_sum = 0.0
    per = []
    P_all, E_all = [], []
    for pts, frame, T_co, grid in obs_list:
        for f in pick_frames(frame):
            sel = np.nonzero(frame == f)[0]
            P = pts[sel].astype(np.float64)
            T = T_co[int(f)]
            io, ko, cuo, cvo, zo = _project(P, T, K, wc, hc)
            if len(io) < 50:
                continue
            ism, ks, cus, cvs, zs = _project(S, T, K, wc, hc)
            # --- completeness: any mesh sample in the cell neighbourhood within M_COMP in depth
            zmed = float(np.median(zo))
            rc = 1 if LAT_COMP is None else max(1, int(math.ceil(K[0, 0] * LAT_COMP / (zmed * CELL_PX))))
            rp = 1 if LAT_PREC is None else max(1, int(math.ceil(K[0, 0] * LAT_PREC / (zmed * CELL_PX))))
            r = max(rc, rp)
            dzn = nearest_dz(ks, zs, ko, zo, cuo, cvo, wc, hc, disk(rc))
            expl = dzn <= M_COMP
            # --- precision inside the silhouette: first mesh surface vs the min observed depth within reach rp
            mk, mz, mpos = _cell_min(ks, zs)
            okey, oz, _ = _cell_min(ko, zo)
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
            # --- precision outside the silhouette (v3): mesh cells with no observed point within reach rp, judged
            #     on the vote grid at their first-surface sample
            mu, mv = mk % wc - u0, mk // wc - v0
            inbox = (mu >= 0) & (mu < gw) & (mv >= 0) & (mv < gh)
            reach = np.full(len(mk), np.inf)
            reach[inbox] = Gmin[mv[inbox], mu[inbox]]
            out = ~np.isfinite(reach)
            n_o = int(out.sum()); n_oj = 0; n_fv = 0; blob = 0.0
            if n_o and grid is not None:
                Xo = S[ism[mpos[out]]]
                jd, emp = seen_empty(Xo, grid)
                n_oj = int(jd.sum()); n_fv = int(emp.sum())
                if n_fv:
                    blob = _largest_blob_cm2(mk[out][emp], mz[out][emp], wc, K[0, 0])
            # --- 2-D hole: largest 8-connected group of unexplained observed cells
            U = np.zeros((gh, gw), bool)
            U[cvo[~expl] - v0, cuo[~expl] - u0] = True
            lab, nl = ndimage.label(U, structure=np.ones((3, 3), bool))
            big = int(np.bincount(lab.ravel())[1:].max()) if nl else 0
            n_cells = len(okey)
            per.append(dict(frame=int(f), r_comp=rc, r_prec=rp, n_pts=int(len(io)), comp=float(expl.mean()),
                            n_judged=int(len(common)), viol=float(viol.mean()) if len(common) else 0.0,
                            mesh_cells=int(len(mk)), out_cells=n_o, out_judged=n_oj, fsv_cells=n_fv,
                            fsv=n_fv / max(len(mk), 1), fsv_blob_cm2=blob, hole2d=big / max(n_cells, 1)))
            n_viol += int(viol.sum()); n_judged += int(len(common)); n_pts += int(len(io)); n_expl += int(expl.sum())
            n_mcells += int(len(mk)); n_out += n_o; n_out_judged += n_oj; n_fsv += n_fv
            c_sum += float(np.minimum(dzn, CAP).sum()); p_sum += float(np.clip(front, 0, CAP).sum())
            P_all.append(P[io]); E_all.append(expl)
    if not per:
        return dict(dr_frames=0), per
    P_all = np.concatenate(P_all); E_all = np.concatenate(E_all)
    h3, h3_cm2, n_vox = hole3d(P_all, E_all)
    comp_f = np.array([r['comp'] for r in per]); h2 = np.array([r['hole2d'] for r in per])
    vf = np.array([r['viol'] for r in per if r['n_judged'] > 0])
    sf = np.array([r['fsv'] for r in per]); bl = np.array([r['fsv_blob_cm2'] for r in per])
    return dict(dr_frames=len(per), dr_pts=n_pts, dr_comp=n_expl / max(n_pts, 1), dr_comp_frame_mean=float(comp_f.mean()),
                dr_comp_frame_p10=float(np.percentile(comp_f, 10)), dr_viol=n_viol / max(n_judged, 1),
                dr_viol_frame_p90=float(np.percentile(vf, 90)) if len(vf) else 0.0, dr_judged=n_judged,
                dr_mesh_cells=n_mcells, dr_out_share=n_out / max(n_mcells, 1),
                dr_out_judged_share=n_out_judged / max(n_out, 1), dr_fsv=n_fsv / max(n_mcells, 1),
                dr_fsv_of_out=n_fsv / max(n_out_judged, 1), dr_fsv_frame_p90=float(np.percentile(sf, 90)),
                dr_fsv_blob_p50_cm2=float(np.percentile(bl, 50)), dr_fsv_blob_p75_cm2=float(np.percentile(bl, 75)),
                dr_fsv_blob_max_cm2=float(bl.max()),
                dr_hole3d=h3, dr_hole3d_cm2=h3_cm2, dr_obs_vox=n_vox,
                dr_hole2d_p50=float(np.median(h2)), dr_hole2d_p90=float(np.percentile(h2, 90)),
                dr_cdist_mm=c_sum / max(n_pts, 1) * 1e3, dr_pdist_mm=p_sum / max(n_judged, 1) * 1e3), per


def _largest_blob_cm2(keys, z, wc, fx):
    """Largest 8-connected group of cells (keys on the wc-wide cell grid, depths z) as a surface area in cm^2: cells x
    (CELL_PX z_med / fx)^2 with the group's median depth."""
    cu, cv = keys % wc, keys // wc
    u0, v0 = cu.min(), cv.min()
    A = np.zeros((cv.max() - v0 + 1, cu.max() - u0 + 1), bool)
    A[cv - v0, cu - u0] = True
    lab, nl = ndimage.label(A, structure=np.ones((3, 3), bool))
    if not nl:
        return 0.0
    li = lab[cv - v0, cu - u0]
    cnt = np.bincount(li)
    b = int(np.argmax(cnt[1:])) + 1
    zm = float(np.median(z[li == b]))
    return float(cnt[b] * (CELL_PX * zm / fx) ** 2 * 1e4)


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
        jd, e = seen_empty(S, g)
        emp |= e; inany |= jd
    return float(emp.mean()), float((~inany).mean())


def _rodrigues(w):
    th = float(np.linalg.norm(w))
    if th < 1e-12:
        return np.eye(3)
    k = w / th
    Kx = np.array([[0, -k[2], k[1]], [k[2], 0, -k[0]], [-k[1], k[0], 0]])
    return np.eye(3) + math.sin(th) * Kx + (1 - math.cos(th)) * Kx @ Kx


def obs_alignment(geo, P, C, seed=0):
    """Trimmed point-to-plane ICP of the observed points P (cameras C) onto the mesh geo: the rigid motion
    p -> R (p - c) + c + t (c = centroid of the used points) that best puts them on the surface. Each point is paired
    with the nearest of its ALIGN_K nearest mesh samples whose normal faces the point's camera (the side of a thin wall
    the camera saw, not its back face). A mesh fitted to these points needs ~0; a shifted mesh needs the shift. Small
    Tikhonov term (1e-3 of the mean diagonal) so a rotation about a symmetry axis stays at 0."""
    rng = np.random.default_rng(seed)
    i = rng.choice(len(P), min(ALIGN_NPTS, len(P)), replace=False)
    Q = P[i].astype(np.float64); Cq = C[i].astype(np.float64)
    Sm, fi = trimesh.sample.sample_surface(geo, ALIGN_NSAMP, seed=seed)
    Nm = geo.face_normals[fi]
    tree = cKDTree(Sm)
    c = Q.mean(0); R = np.eye(3); t = np.zeros(3)
    n_used = 0; res = np.nan; eig_t = (np.nan, np.nan); facing = np.nan
    for _ in range(ALIGN_ITERS):
        X = (Q - c) @ R.T + c + t
        Xc = (Cq - c) @ R.T + c + t
        dk, jk = tree.query(X, k=ALIGN_K, distance_upper_bound=ALIGN_TRIM)
        fin = np.isfinite(dk)
        jc = np.where(fin, jk, 0)
        face = fin & ((Nm[jc] * (Xc[:, None, :] - Sm[jc])).sum(-1) > 0)
        has = face.any(1)
        first = np.argmax(face, axis=1)
        d = np.where(has, dk[np.arange(len(X)), first], np.inf)
        j = jc[np.arange(len(X)), first]
        facing = float(has.mean())
        ok = np.isfinite(d)
        if ok.sum() < 100:
            break
        ok &= d <= np.quantile(d[ok], ALIGN_KEEP)
        x, s, n = X[ok], Sm[j[ok]], Nm[j[ok]]
        r = ((x - s) * n).sum(1)
        cc = c + t
        A = np.hstack([np.cross(x - cc, n), n])
        H = A.T @ A
        H += np.eye(6) * 1e-3 * np.trace(H) / 6
        dx = np.linalg.solve(H, -A.T @ r)
        R = _rodrigues(dx[:3]) @ R; t = t + dx[3:]
        n_used = int(ok.sum()); res = float(np.median(np.abs(r)))
        ev = np.linalg.eigvalsh(A[:, 3:].T @ A[:, 3:]); eig_t = (float(ev[0] / max(ev[-1], 1e-30)), float(ev[-1]))
        if np.linalg.norm(dx[3:]) < 1e-6 and np.linalg.norm(dx[:3]) < 1e-6:
            break
    ang = math.degrees(math.acos(max(-1.0, min(1.0, (np.trace(R) - 1) / 2))))
    return dict(align_t_mm=float(np.linalg.norm(t) * 1e3), align_t_vec_mm=[round(float(x) * 1e3, 3) for x in t],
                align_rot_deg=ang, align_res_mm=res * 1e3, align_n=n_used, align_tcond=eig_t[0], align_facing=facing)


def frame_alignment(geo, lib, seed=0):
    """Translation-only trimmed point-to-plane ICP of decoded-mesh samples onto the library_v3 surface (our own TSDF
    mesh of the object, the frame reference of G_FLIP): both are closed surfaces of the same object, so wall
    thickness and observation coverage do not bias it the way one-sided observed points do. Returns frame_t_mm."""
    rng = np.random.default_rng(seed)
    X0 = trimesh.sample.sample_surface(geo, FRAME_NSAMP, seed=seed)[0]
    t = np.zeros(3); n_used = 0
    for _ in range(ALIGN_ITERS):
        X = X0 + t
        d, j = lib['tree'].query(X, distance_upper_bound=ALIGN_TRIM)
        ok = np.isfinite(d)
        if ok.sum() < 100:
            break
        ok &= d <= np.quantile(d[ok], ALIGN_KEEP)
        n = lib['normals'][j[ok]]
        r = ((X[ok] - lib['pts'][j[ok]]) * n).sum(1)
        H = n.T @ n
        H += np.eye(3) * 1e-3 * np.trace(H) / 3
        dt = np.linalg.solve(H, -n.T @ r)
        t = t + dt; n_used = int(ok.sum())
        if np.linalg.norm(dt) < 1e-6:
            break
    return dict(frame_t_mm=float(np.linalg.norm(t) * 1e3), frame_t_vec_mm=[round(float(x) * 1e3, 3) for x in t],
                frame_t_n=n_used)


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


def components(m):
    """Connected components of a mesh by shared vertices (exact face labels; trimesh's split can duplicate faces)."""
    if len(m.faces) == 0:
        return []
    from scipy.sparse import coo_matrix
    from scipy.sparse.csgraph import connected_components
    F = m.faces; nv = len(m.vertices)
    rows = np.r_[F[:, 0], F[:, 1], F[:, 2]]; cols = np.r_[F[:, 1], F[:, 2], F[:, 0]]
    _, lab = connected_components(coo_matrix((np.ones(len(rows)), (rows, cols)), shape=(nv, nv)), directed=False)
    fl = lab[F[:, 0]]
    out = []
    for c in np.unique(fl):
        sub = trimesh.Trimesh(m.vertices, F[fl == c], process=False)
        sub.remove_unreferenced_vertices()
        out.append(sub)
    return out


def connectivity(mesh):
    """Components grouped when their surfaces come within TOUCH; small compact components within BALL_LINK of the
    main group count with it. conn_share = (main group + linked small bodies) / total area."""
    comps = components(mesh)
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
    """The mesh as built (report) and as the kit decodes it (gated): faces, vertices, bodies, watertight bodies,
    area and RMS-radius change of the decode."""
    bodies = components(raw)
    out = dict(topo_raw_faces=int(len(raw.faces)), topo_raw_verts=int(len(raw.vertices)), topo_raw_bodies=int(len(bodies)),
               topo_raw_watertight=bool(len(bodies) > 0 and all(b.is_watertight for b in bodies)))
    try:
        bm = load_budget(path)
        bb = components(bm)
        a0, r0 = _area_rms(raw); a1, r1 = _area_rms(bm)
        out.update(topo_budget_faces=int(len(bm.faces)), topo_budget_verts=int(len(bm.vertices)),
                   topo_budget_watertight=bool(len(bb) > 0 and all(b.is_watertight for b in bb)),
                   topo_budget_bodies=int(len(bb)), topo_area_change=a1 / a0 - 1, topo_rms_change=r1 / r0 - 1,
                   topo_weld_only=bool(len(raw.faces) <= BUDGET and len(raw.vertices) <= BUDGET),
                   topo_decode_error=None)
    except Exception as e:  # noqa: BLE001
        bm = None
        out.update(topo_budget_faces=None, topo_budget_verts=None, topo_budget_watertight=None, topo_budget_bodies=None,
                   topo_area_change=None, topo_rms_change=None, topo_weld_only=None,
                   topo_decode_error=f'{type(e).__name__}: {e}'[:200])
    return out, bm


def library_ref(obj):
    """Cached library_v3 surface samples (KD-tree) and its area / RMS radius after the kit decode."""
    key = ('lib', obj)
    if key not in _CACHE:
        lm = load_budget(lib_path(obj))
        a, r = _area_rms(lm)
        pts, fi = trimesh.sample.sample_surface(lm, 400_000, seed=3)
        _CACHE[key] = dict(tree=cKDTree(pts), pts=pts, normals=lm.face_normals[fi], area=a, rms=r)
    return _CACHE[key]


# ------------------------------------------------------------------------------------------------ evaluate
def evaluate(mesh_path, obs_paths=None, obj=None, ep=None, flip=True, obs='raw', frames=None, flip_metrics=None):
    """All measures and gates of one candidate mesh against the observations of one (or several) episodes.
    obs_paths: observation files (default: io_gt.obs_path(obj, ep), RAW points). obs: 'raw' (default; a refined copy
    among obs_paths raises) or 'refined' (refine.py copies on request; each brings its per-frame track correction).
    frames: optional frame ids to keep (e.g. a split half of one episode). flip_metrics: flip results to reuse
    (FLIP_KEYS of an earlier row of the same mesh and object) instead of running the flip check.
    Returns dict(mesh, obj, ep, obs, obs_kind, metrics, gates, pass, rank_score, per_frame, thresholds, inputs, sec)."""
    t0 = time.time()
    if obs not in ('raw', 'refined'):
        raise ValueError(f"obs must be 'raw' or 'refined', not {obs!r}")
    if obs_paths is None:
        obs_paths = [io_gt.obs_path(obj, ep, refined=(obs == 'refined'))]
    if isinstance(obs_paths, str):
        obs_paths = [obs_paths]
    if obs == 'raw' and any(is_refined(p) for p in obs_paths):
        raise ValueError(f"refined observation copies are used only on request (obs='refined'): {obs_paths}")
    io_gt.inputs_log(reset=True)
    calib = io_gt.load_calib()
    K, size = calib['K'], calib['size']
    raw = load_raw(mesh_path)
    m = dict(raw_area_cm2=raw.area * 1e4)
    topo, bm = topology(mesh_path, raw)
    m.update(topo)
    geo = bm if bm is not None else raw                         # what the scorer sees
    S = _samples(geo)
    obs_list, grids, P_fid, C_fid, ncorr = [], [], [], [], 0
    keep = None if frames is None else np.asarray(sorted({int(f) for f in frames}))
    for p in obs_paths:
        o = io_gt.load_obs(p)
        T, nc = frame_cams(p, obj, ep_of(p, ep)); ncorr += nc
        pts, fr, cam = o['pts'], o['frame'], o['cam']
        if keep is not None:
            sel = np.isin(fr, keep)
            pts, fr, cam = pts[sel], fr[sel], cam[sel]
        g = o if all(k in o for k in ('hits', 'free', 'lo', 'vox')) else None
        obs_list.append((pts, fr, T, g)); P_fid.append(pts.astype(np.float64)); C_fid.append(cam.astype(np.float64))
        if g is not None:
            grids.append(g)
    m['track_corrections'] = ncorr
    m['obs_frames_kept'] = None if keep is None else int(len(np.unique(np.concatenate([x[1] for x in obs_list]))))
    dr, per = depth_render(S, obs_list, K, size)
    m.update(dr)
    m['fs_frac'], m['fs_outside_grid'] = fs_frac(S, grids) if grids else (float('nan'), float('nan'))
    P_cat = np.concatenate(P_fid)
    m.update(obs_alignment(geo, P_cat, np.concatenate(C_fid)))
    m.update(fidelity(raw, P_cat))
    m.update(connectivity(geo))
    lib = library_ref(obj)
    a, r = _area_rms(geo)
    m.update(frame_med_mm=float(np.median(lib['tree'].query(S[np.random.default_rng(0).choice(len(S), min(50_000, len(S)), replace=False)])[0]) * 1e3),
             drift_area=a / lib['area'], drift_rms=r / lib['rms'], area_cm2=a * 1e4, rms_mm=r * 1e3)
    m.update(frame_alignment(geo, lib))
    if flip_metrics is not None:
        m.update({k: flip_metrics.get(k) for k in FLIP_KEYS}); m['flip_reused'] = True
    elif flip:
        t1 = time.time()
        fc = mesh_gates().flip_check(io_gt.mesh_input(mesh_path), io_gt.mesh_input(lib_path(obj)), obj)
        m.update(flip_n=int(fc['n']), flips=int(fc['xflips']), flip_xadd_med_mm=float(fc['xadd_med']),
                 flip_rot=[r_['rot'] for r_ in fc['seeds']], flip_sec=round(time.time() - t1, 1))
    else:
        m.update(flip_n=0, flips=None)
    g = gates_of(m)
    return dict(mesh=os.path.abspath(mesh_path), obj=obj, ep=int(ep), obs=[os.path.abspath(p) for p in obs_paths],
                obs_kind=obs, gates_version=VERSION,
                metrics={k: (round(v, 5) if isinstance(v, float) else v) for k, v in m.items()}, gates=g,
                **{'pass': all(g.values())}, rank_score=rank_score(m), per_frame=per, thresholds=THRESHOLDS,
                inputs=io_gt.inputs_log(), sec=round(time.time() - t0, 1))


def gates_of(m):
    """The frozen gates on a metrics dict (missing or NaN measure = gate fails)."""
    def ok(x):
        return x is not None and not (isinstance(x, float) and math.isnan(x))

    def le(k, v):
        return bool(ok(m.get(k)) and m[k] <= v)
    return dict(
        G_COMP=bool(ok(m.get('dr_comp')) and m['dr_comp'] >= COMP_MIN),
        G_HOLE=le('dr_hole3d', HOLE_MAX),
        G_PREC=le('dr_viol', VIOL_MAX) and le('dr_fsv', FSV_MAX) and le('dr_fsv_blob_p75_cm2', FSV_BLOB_MAX),
        G_FS=le('fs_frac', FS_MAX),
        G_CONN=bool(ok(m.get('conn_share')) and m['conn_share'] >= CONN_MIN),
        G_TOPO=bool(m.get('topo_decode_error') is None and le('topo_budget_faces', BUDGET)
                    and le('topo_budget_verts', BUDGET) and m.get('topo_budget_watertight') is True
                    and ok(m.get('topo_budget_bodies')) and ok(m.get('topo_raw_bodies'))
                    and m['topo_budget_bodies'] <= m['topo_raw_bodies']
                    and ok(m.get('topo_area_change')) and abs(m['topo_area_change']) <= AREA_TOL),
        G_FRAME=bool(ok(m.get('frame_med_mm')) and m['frame_med_mm'] < FRAME_MM) and le('align_t_mm', ALIGN_MAX_MM),
        G_FLIP=bool(m.get('flips') == 0 and (m.get('flip_n') or 0) > 0))


def rank_score(m):
    """Frozen rank (mm, lower is better): two-sided truncated depth-render residual, judged where observed, plus the
    outside-silhouette free-space share at the cap: dr_cdist_mm (mean over observed points of the depth gap to the
    nearest mesh surface, capped at CAP) + dr_pdist_mm (mean over judged mesh cells of how far the first mesh surface
    lies in front of the observed surface, capped at CAP) + CAP_mm x dr_fsv."""
    if m.get('dr_cdist_mm') is None or m.get('dr_pdist_mm') is None:
        return float('inf')
    return round(m['dr_cdist_mm'] + m['dr_pdist_mm'] + CAP * 1e3 * float(m.get('dr_fsv') or 0.0), 5)


# ------------------------------------------------------------------------------------------------ select
def is_fallback(row):
    return bool(row.get('fallback')) or row.get('kind') == 'library' or \
        os.path.dirname(os.path.abspath(row['mesh'])) == os.path.abspath(LIB_DIR)


def roles(by):
    """Selector-v3 role of each mesh (rows grouped by mesh): 'fallback' (library_v3), 'candidate' (the selectable
    build of a part program) or 'diagnostic' (everything else), with the reason."""
    out, fams = {}, {}
    for mesh, rs in by.items():
        r0 = rs[0]
        if any(is_fallback(r) for r in rs):
            out[mesh] = ('fallback', 'library_v3 fallback: always eligible, never gated')
        elif r0.get('kind') in PROGRAM_KINDS:
            fams.setdefault(r0.get('family') or mesh, []).append(mesh)
        else:
            why = {'shell': 'route-A standalone shell: diagnostic only (its rank cannot see unobserved surface)',
                   'incumbent': 'earlier-round mesh: diagnostic only'}.get(r0.get('kind'), f"kind {r0.get('kind')!r}: diagnostic only")
            out[mesh] = ('diagnostic', why)
    for fam, meshes in fams.items():
        tt = {mm: by[mm][0].get('t_mm') for mm in meshes}
        mid = [mm for mm in meshes if tt[mm] is not None and abs(float(tt[mm]) * 1e-3 - T_MID) < 1e-9]
        meas = [mm for mm in meshes if by[mm][0].get('t_rule') == 'measured' and tt[mm] is not None]
        if mid:
            pick = mid[0]; why = f't = {T_MID * 1e3:.1f} mm (grid middle)'
        elif meas and len(meas) == len(meshes):
            pick = min(meas, key=lambda mm: abs(float(tt[mm]) * 1e-3 - T_MID))
            why = 'thickness measured by the program (t-invariant build), closest to the grid middle'
        else:
            pick = None
        for mm in meshes:
            if mm == pick:
                out[mm] = ('candidate', why)
            else:
                out[mm] = ('diagnostic', f't = {tt[mm]} mm: t is not chosen by the rank (grid middle '
                                         f'{T_MID * 1e3:.1f} mm' + (' build of this program exists)' if pick else
                                                                    ' build missing)'))
    return out


def select(rows):
    """Selector v3 over evaluate() rows of ONE object (one or several episodes per mesh). Each row may carry kind
    ('program' / 'dsl' = part-program build, 'library', 'shell', 'incumbent', ...), t_mm, t_rule ('measured' when the
    program measured every thickness it uses) and family (program name + variant). Roles (roles()): the library_v3
    fallback is always eligible and never gated; per program family only the grid-middle build is a candidate; every
    other row is diagnostic (reported, never picked). Eligible = fallback + candidates that pass on every episode;
    the pick is the lowest mean rank score (ties: lower mean fid_sum_mm). Returns dict(pick, reasons, ranking)."""
    by = {}
    for r in rows:
        by.setdefault(r['mesh'], []).append(r)
    role = roles(by)
    reasons, elig = {}, []
    for mesh, rs in by.items():
        rl, why = role[mesh]
        failed = sorted({f'{k}@ep{r["ep"]}' for r in rs for k, v in r['gates'].items() if not v})
        passed = all(r['pass'] for r in rs)
        score = float(np.mean([r['rank_score'] for r in rs]))
        fid = float(np.mean([r['metrics'].get('fid_sum_mm', np.inf) for r in rs]))
        reasons[mesh] = dict(role=rl, why=why, fallback=(rl == 'fallback'), passed=passed, failed=failed,
                             rank_score=round(score, 5), fid_sum_mm=round(fid, 3), episodes=sorted({r['ep'] for r in rs}),
                             kind=rs[0].get('kind'), t_mm=rs[0].get('t_mm'), family=rs[0].get('family'))
        if rl == 'fallback' or (rl == 'candidate' and passed):
            elig.append((score, fid, mesh))
    elig.sort()
    pick = elig[0][2] if elig else None
    for i, (_, _, mesh) in enumerate(elig):
        reasons[mesh]['rank'] = i + 1
    return dict(pick=pick, reasons=reasons, ranking=[e[2] for e in elig], selector=VERSION)


# ------------------------------------------------------------------------------------------------ CLI
def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    sub = ap.add_subparsers(dest='cmd', required=True)
    e = sub.add_parser('eval'); e.add_argument('mesh'); e.add_argument('obj'); e.add_argument('ep', type=int)
    e.add_argument('--obs', default=None); e.add_argument('--refined', action='store_true')
    e.add_argument('--no-flip', action='store_true'); e.add_argument('--out', default=None)
    e.add_argument('--kind', default='diagnostic', help='program | library | shell | incumbent | diagnostic')
    e.add_argument('--t-mm', type=float, default=None); e.add_argument('--family', default=None)
    e.add_argument('--t-rule', default=None)
    s = sub.add_parser('select'); s.add_argument('rows')
    a = ap.parse_args()
    if a.cmd == 'eval':
        kind = 'refined' if a.refined else 'raw'
        obs = a.obs.split(',') if a.obs else None
        r = evaluate(a.mesh, obs, a.obj, a.ep, flip=not a.no_flip, obs=kind)
        r.pop('per_frame')
        r.update(kind=a.kind, t_mm=a.t_mm, family=a.family, t_rule=a.t_rule)
        print(json.dumps(r, default=str))
        if a.out:
            with open(a.out, 'a') as f:
                f.write(json.dumps(r, default=str) + '\n')
    else:
        rows = [json.loads(l) for l in open(a.rows) if l.strip()]
        print(json.dumps(select(rows), indent=1))


if __name__ == '__main__':
    main()
