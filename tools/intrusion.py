#!/usr/bin/env python3
"""Intrusion export for the gmg INTERLOCK contract (2026-10-31; schema gmg-intrusion/2, INTERLOCK.md section 11.2 on
branch claude/bold-albattani-6qmxsv, docs/research/mesh-2026-10-26/gmg/). Per frame and ordered pair (target, partner)
of our reference: the partner's solid samples that lie inside the target, in the target's file coordinates.

Geometry: the union of the round's delivered collision pieces SIM_DIR/<obj>/piece_XX.obj (never <obj>.glb).
  partner samples  lattice points (i + 1/2) * pitch (pitch <= 2 mm, the partner's file coordinates) inside at least one
                   convex piece by more than 1 um (exact half-space test per piece, scipy ConvexHull planes).
  inside test      a partner sample intrudes if it lies more than 1 um inside at least one of the target's pieces.
  depth_m          distance to the surface of the UNION of the target's pieces (the contract's definition): nearest
                   union-surface sample (piece faces sampled at --surf_mm, a face point dropped when a probe 10 um
                   outside it lies inside another piece), never below depth_lb_m; an upper bound, too deep by at most
                   ~0.71 * surf_mm. depth_lb_m = max over pieces of the per-piece half-space depth (exact distance to
                   that piece's boundary): a lower bound that misses depth across abutting pieces.
Coordinates: world <- file = the reference body pose (object_body_position, object_body_wxyz (w, x, y, z));
make_assets.py writes identity collision/visual origins, so the URDF link frame is the file frame. MuJoCo geom poses
are never used. rel_T = inv(O_target) @ O_partner (partner file -> target file), pts_local = rel_T applied to the
partner samples. Fiducials: SIM_DIR/manifest.json (8 per object, file coordinates) mapped file -> world at f_star by
O (the transform of the samples) and back by inv(O) (the inverse of pts_local); refused if the round trip or an
independent quaternion evaluation of the parquet errs by > 0.5 mm, or if the pieces do not fill the fiducial box
(each face touched from outside within 0-1.5 mm, symmetric within 0.5 mm: catches re-centred pieces or fiducials).
Rows: every frame and ordered pair whose bounding spheres (+ --margin_cm) overlap; intr_vol_m3 = samples x pitch^3.
pushed_residual_m: NaN unless --fit PHYS_FIT_OUT (pipeline/phys_fit.py output) ran on the round's _fit/<obj>.glb and
props_gmg.json with the 1 cm / 3 deg prior on this reference; then, on the fit's poses (mapped into the reference
frame by the fit input's table_frame.npz, checked against the parquet to 1 mm / 0.1 deg), the smallest further
translation of the partner that leaves no sample inside the target (exact per direction, minimised over 42 icosphere
directions refined at 10 and 3 deg; 0 if no intrusion remains; inf beyond 10 cm).
Header OUT.json: schema, objects, round, sim_dir, meshes {obj: {file: sha256}}, pitch_m, tool, commit, argv,
reference {path, sha256, provenance}, fit, pose_source, f_star, fiducials. Reference provenance: REF.parquet.prov.json
(pipeline/provenance.py manifests, followed through every input that has one), else --prov FILE ({"chain": [{tool,
commit, run_id, artifact, sha256, inputs: {path: sha256}}]}), else what the mkref output folder shows, marked
complete = false. Every path or hash in the chain, the reference and the fit's inputs is checked against
ops/provenance/denylist.json and the substrings mocap, /scan, _scan, _align, oracle, library_v1-v4: a hit refuses the
run. Our reference only; no ground truth.
Usage: intrusion.py REF.parquet SIM_DIR OUT.npz [--round K] [--pitch_mm 2] [--surf_mm 0.5] [--prov PROV.json]
       [--fit PHYS_FIT_OUT [--fit_commit SHA]]          (writes OUT.npz and OUT.json; never overwrites)
"""
import argparse, glob, hashlib, json, os, re, subprocess, sys, time
import numpy as np, pyarrow.parquet as pq, trimesh
from scipy.spatial import ConvexHull, cKDTree
from scipy.spatial.transform import Rotation as Rot

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, 'pipeline'))
from provenance import deny_reason, denylist  # noqa: E402

SCHEMA, TOOL = 'gmg-intrusion/2', 'tools/intrusion.py'
EPS, PROBE, FID_TOL = 1e-6, 1e-5, 5e-4            # m: inside margin, union-surface probe, fiducial tolerance
GT_SUB = ('mocap', '/scan', '_scan', '_align', 'oracle') + tuple(f'library_v{k}' for k in range(1, 5))
PERCEPTION = ('poses.npz', 'poses_world_vo.npz', 'hands_refined.npz', 'table_frame.npz')


class Refuse(SystemExit):
    def __init__(self, msg):
        super().__init__(f'intrusion.py REFUSED: {msg}')


def sha(path, chunk=1 << 20):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for b in iter(lambda: f.read(chunk), b''):
            h.update(b)
    return h.hexdigest()


def denied(path=None, digest=None):
    """Why a path (or a sha256 from a provenance record) counts as ground truth / a denied input, else None."""
    if path:
        low = os.path.abspath(path).lower()
        hit = next((s for s in GT_SUB if s in low), None)
        if hit:
            return f'path contains {hit!r}'
        r = deny_reason(path)
        if r:
            return r
    if digest and digest in denylist()['sha256']:
        return f"sha256 of {denylist()['sha256'][digest]}"
    return None


# ---------------------------------------------------------------- geometry
def tri_samples(T, h):
    """Points on triangles T (n,3,3) with spacing <= h (square grid in the plane, base on the longest edge, plus the
    edges) and the index of their triangle."""
    P, I, n0 = [], [], 0
    for j, t in enumerate(T):
        k = int(np.argmax([np.linalg.norm(t[(i + 1) % 3] - t[i]) for i in range(3)]))
        A, B, C = t[k], t[(k + 1) % 3], t[(k + 2) % 3]
        L = np.linalg.norm(B - A)
        if L < 1e-12:
            continue
        e1 = (B - A) / L; cx = (C - A) @ e1; e2 = C - A - cx * e1; cy = np.linalg.norm(e2)
        for p, q in ((A, B), (B, C), (C, A)):
            n = max(1, int(np.ceil(np.linalg.norm(q - p) / h))); P.append(p + np.linspace(0, 1, n + 1)[:, None] * (q - p))
        if cy > h / 4:
            u, v = (g.ravel() for g in np.meshgrid(np.arange(h / 2, L, h), np.arange(h / 2, cy, h)))
            m = (v * cx <= u * cy) & (v * (L - cx) <= (L - u) * cy)
            P.append(A + u[m, None] * e1 + v[m, None] * (e2 / cy))
        n1 = sum(len(x) for x in P[n0:]); I.append(np.full(n1, j)); n0 = len(P)
    return np.concatenate(P), np.concatenate(I)


class Union:
    """Union of convex collision pieces in file coordinates."""

    def __init__(self, files):
        self.files, self.H, self.lo, self.hi, self.tri, self.vol, V = files, [], [], [], [], [], []
        for f in files:
            m = trimesh.load(f, force='mesh', process=False); X = np.asarray(m.vertices, float); h = ConvexHull(X)
            self.H.append(np.unique(np.round(h.equations, 12), axis=0))      # n.x + c <= 0 inside, |n| = 1
            self.tri.append((X[h.simplices], h.equations[:, :3])); self.lo.append(X.min(0)); self.hi.append(X.max(0))
            self.vol.append((float(h.volume), float(abs(m.volume)) if m.is_watertight else None)); V.append(X[h.vertices])
        self.V = np.concatenate(V); self.alo, self.ahi = self.V.min(0), self.V.max(0)
        self.centre = (self.alo + self.ahi) / 2; self.radius = float(np.linalg.norm(self.V - self.centre, axis=1).max())
        self.tree = None

    def depth_lb(self, X, skip=None, chunk=200000):
        """Max over pieces of min over planes of -(n.x + c): exact depth into that piece, a lower bound of the depth into
        the union; -inf outside every piece's box, < 0 outside every piece."""
        d = np.full(len(X), -np.inf)
        for s in range(0, len(X), chunk):
            Y, ds = X[s:s + chunk], d[s:s + chunk]
            for k, E in enumerate(self.H):
                if k == skip:
                    continue
                m = np.nonzero(np.all((Y >= self.lo[k] - 1e-9) & (Y <= self.hi[k] + 1e-9), 1))[0]
                if len(m):
                    ds[m] = np.maximum(ds[m], -(Y[m] @ E[:, :3].T + E[:, 3]).max(1))
        return d

    def lattice(self, pitch):
        """Solid samples: lattice points (i + 1/2) pitch inside the union by more than EPS (z slabs bound memory)."""
        ax = [(np.arange(np.floor(a / pitch - .5), np.ceil(b / pitch - .5) + 1) + .5) * pitch for a, b in zip(self.alo, self.ahi)]
        gx, gy = (g.ravel() for g in np.meshgrid(ax[0], ax[1], indexing='ij')); out = []
        for z in ax[2]:
            G = np.c_[gx, gy, np.full(len(gx), z)]
            out.append(G[self.depth_lb(G) > EPS])
        return np.concatenate(out)

    def surface(self, h):
        """Samples of the union's surface: piece-face samples whose outward probe (PROBE) is not inside another piece."""
        P = []
        for k, (T, N) in enumerate(self.tri):
            S, I = tri_samples(T, h)
            P.append(S[~(self.depth_lb(S + PROBE * N[I], skip=k) > 0)])
        return np.concatenate(P)

    def depth(self, X, h, lb):
        if self.tree is None:
            self.tree = cKDTree(self.surface(h))
        return np.maximum(self.tree.query(X)[0], lb)


def fiducial_box(F, V):
    """Do the pieces' vertices V fill the oriented box of the 8 fiducials F (corners moved inward)? Per box face the
    margin (how far the pieces reach beyond it); ok if every margin is in [-0.5, 1.5] mm and opposite faces agree within
    0.5 mm (a re-centred mesh or fiducial set shifts one side out and the other in)."""
    c = F.mean(0); D = F - F[0]; best = None
    for i in range(1, 8):
        for j in range(i + 1, 8):
            for k in range(j + 1, 8):
                E = D[[i, j, k]]; L = np.linalg.norm(E, axis=1)
                if L.min() < 1e-6:
                    continue
                U = E / L[:, None]; err = np.abs(U @ U.T - np.eye(3)).max() + np.linalg.norm(E.sum(0) - 2 * (c - F[0])) / L.sum()
                if best is None or err < best[0]:
                    best = (err, U, L)
    if best is None:
        return dict(ok=False, reason='degenerate fiducials')
    err, U, L = best; Y = (V - c) @ U.T
    mp, mn = Y.max(0) - L / 2, -Y.min(0) - L / 2
    ok = bool(err < 1e-3 and np.all(np.r_[mp, mn] >= -FID_TOL) and np.all(np.r_[mp, mn] <= 3 * FID_TOL)
              and np.all(np.abs(mp - mn) <= FID_TOL))
    return dict(ok=ok, box_err=float(err), margins_mm=np.round(np.c_[mn, mp] * 1e3, 3).tolist(),
                asym_mm=np.round(np.abs(mp - mn) * 1e3, 3).tolist())


def obb_fiducials(V, inward=1e-3):
    """8 corners of the oriented box of V moved 1 mm inward along each axis (used only when no manifest exists)."""
    To, ext = trimesh.bounds.oriented_bounds(V)
    C = np.array([[sx, sy, sz] for sx in (-1, 1) for sy in (-1, 1) for sz in (-1, 1)]) * (ext / 2 - inward)
    Ti = np.linalg.inv(To)
    return C @ Ti[:3, :3].T + Ti[:3, 3]


def icosphere_dirs():
    return np.asarray(trimesh.creation.icosphere(subdivisions=1).vertices, float)


def cone(u, deg, n=12):
    a = np.array([1.0, 0, 0]) if abs(u[0]) < 0.9 else np.array([0, 1.0, 0])
    e1 = np.cross(u, a); e1 /= np.linalg.norm(e1); e2 = np.cross(u, e1); t = np.radians(deg)
    ph = np.linspace(0, 2 * np.pi, n, endpoint=False)
    return np.cos(t) * u + np.sin(t) * (np.cos(ph)[:, None] * e1 + np.sin(ph)[:, None] * e2)


def free_shift(U, X, u, s_max):
    """Smallest s >= 0 with no X + s u more than EPS inside any piece of U: each sample's ray is inside a convex piece on
    an open interval (lo, hi); s = the first point not covered by their union (inf if beyond s_max)."""
    LO, HI = [], []
    for k, E in enumerate(U.H):
        with np.errstate(divide='ignore', invalid='ignore'):                # segment [x, x + s_max u] vs the piece box
            t1, t2 = (U.lo[k] - 1e-9 - X) / u, (U.hi[k] + 1e-9 - X) / u
        zero = np.abs(u) < 1e-12; inslab = (X >= U.lo[k] - 1e-9) & (X <= U.hi[k] + 1e-9)
        tn = np.where(zero, np.where(inslab, -np.inf, np.inf), np.minimum(t1, t2)).max(1)
        tx = np.where(zero, np.where(inslab, np.inf, -np.inf), np.maximum(t1, t2)).min(1)
        m = np.nonzero((tn <= tx) & (tx >= 0) & (tn <= s_max))[0]
        if not len(m):
            continue
        a = E[:, :3] @ u; b = -(X[m] @ E[:, :3].T + E[:, 3]) - EPS          # inside at s: s a_i < b_i for every plane
        with np.errstate(divide='ignore', invalid='ignore'):
            r = b / a
        lo = np.where(a < -1e-12, r, -np.inf).max(1); hi = np.where(a > 1e-12, r, np.inf).min(1)
        par = np.abs(a) <= 1e-12
        if par.any():
            lo = np.where((b[:, par] <= 0).any(1), np.inf, lo)
        ok = (lo < hi) & (hi > 0)
        LO.append(lo[ok]); HI.append(hi[ok])
    lo, hi = (np.concatenate(z) if z else np.zeros(0) for z in (LO, HI))
    if not len(lo):
        return 0.0
    o = np.argsort(lo); lo, hi = lo[o], hi[o]
    if lo[0] >= 0:
        return 0.0
    reach = np.maximum.accumulate(hi); gap = np.nonzero(lo[1:] >= reach[:-1])[0]
    s = float(reach[gap[0]] if len(gap) else reach[-1])
    return s if s <= s_max else np.inf


def push_residual(U, X, s_max=0.10):
    """Smallest translation of the partner samples X (target file coordinates) that leaves none inside U."""
    X = X[np.all((X > U.alo - s_max) & (X < U.ahi + s_max), 1)]
    if not (U.depth_lb(X) > EPS).any():
        return 0.0
    D = icosphere_dirs(); s = np.array([free_shift(U, X, u, s_max) for u in D]); u = D[int(np.argmin(s))]; best = s.min()
    for deg in (10.0, 3.0):
        C = cone(u, deg); sc = np.array([free_shift(U, X, c, s_max) for c in C])
        if sc.min() < best:
            best, u = sc.min(), C[int(np.argmin(sc))]
    return float(best)


# ---------------------------------------------------------------- inputs
def load_ref(path):
    t = pq.read_table(path)
    bad = [c for c in t.column_names if 'observation.objects' in c or c == 'pose']
    if bad:
        raise Refuse(f'{path} has columns {bad}: an episode parquet, not our reference')
    names = t.column('object_body_names')[0].as_py(); B = len(names)
    P = np.array(t.column('object_body_position')[0].as_py(), float); T = P.size // (3 * B)
    P = P.reshape(T, B, 3); Q = np.array(t.column('object_body_wxyz')[0].as_py(), float).reshape(T, B, 4)
    O = np.tile(np.eye(4), (T, B, 1, 1))
    O[..., :3, :3] = Rot.from_quat(Q.reshape(-1, 4)[:, [1, 2, 3, 0]]).as_matrix().reshape(T, B, 3, 3); O[..., :3, 3] = P
    fps = float(t.column('fps')[0].as_py()) if 'fps' in t.column_names else None
    return names, O, P, Q, fps


def inv_pose(O):
    Oi = np.zeros_like(O); R = O[..., :3, :3]
    Oi[..., :3, :3] = np.swapaxes(R, -1, -2); Oi[..., :3, 3] = -np.einsum('...ji,...j->...i', R, O[..., :3, 3]); Oi[..., 3, 3] = 1
    return Oi


def quat_wxyz_matrix(q):
    """Independent (w, x, y, z) -> rotation matrix, for the fiducial check."""
    w, x, y, z = np.asarray(q, float) / np.linalg.norm(q)
    return np.array([[1 - 2 * (y * y + z * z), 2 * (x * y - w * z), 2 * (x * z + w * y)],
                     [2 * (x * y + w * z), 1 - 2 * (x * x + z * z), 2 * (y * z - w * x)],
                     [2 * (x * z - w * y), 2 * (y * z + w * x), 1 - 2 * (x * x + y * y)]])


def run_id_of(path):
    m = re.search(r'/runs?/(\d{8}-[^/]+)', os.path.abspath(path))
    return m.group(1) if m else None


def manifest_entry(man, n):
    """(files {basename: sha256} or None, fiducials (8,3) or None) of object n in the round's manifest.json. Layouts read:
    objects.<n>.{files | sha256, fiducials} (objects a dict or a list with 'name'), else top-level files | sha256
    {"<n>/<file>": sha} and fiducials {<n>: [...]}."""
    objs = man.get('objects') or {}
    if isinstance(objs, list):
        objs = {o.get('name'): o for o in objs if isinstance(o, dict)}
    o = objs.get(n) if isinstance(objs, dict) and isinstance(objs.get(n), dict) else {}
    files = o.get('files') or o.get('sha256')
    if files is None:
        top = man.get('files') or man.get('sha256') or {}
        files = {k.split('/', 1)[1]: v for k, v in top.items() if k.startswith(n + '/')} or None
    if files:
        files = {os.path.basename(k): (v if isinstance(v, str) else v.get('sha256')) for k, v in files.items()}
    fid = o.get('fiducials', (man.get('fiducials') or {}).get(n))
    return files, (np.asarray(fid, float).reshape(8, 3) if fid is not None else None)


def provenance(ref, prov_file):
    """The reference's producer chain: [{tool, commit, run_id, artifact, sha256, command, inputs {path: sha256}}]."""
    chain, source, seen = [], None, set()

    def follow(p):
        mp = f'{p}.prov.json'
        if p in seen or not os.path.exists(mp):
            return
        seen.add(p); m = json.load(open(mp))
        chain.append(dict(tool=m.get('tool') or m.get('kind'), commit=m.get('code_commit') or m.get('commit'),
                          run_id=m.get('run_id') or run_id_of(p), artifact=os.path.abspath(p), sha256=m.get('sha256'),
                          command=m.get('command'), manifest=mp,
                          inputs={i['path']: i.get('sha256') for i in m.get('inputs', [])}))
        for i in m.get('inputs', []):
            follow(i['path'])
    follow(os.path.abspath(ref))
    if chain:
        source = 'prov.json manifests (pipeline/provenance.py)'
    elif prov_file:
        d = json.load(open(prov_file)); chain = d['chain'] if isinstance(d, dict) else d; source = f'--prov {os.path.abspath(prov_file)}'
    else:
        root = os.path.dirname(ref).split(os.sep + 'processed' + os.sep)[0]
        ins = {f'{root}/{f}': sha(f'{root}/{f}') for f in ('ref_summary.json', 'mkref_log.txt', 'table_frame.npz', 'hands_refined.npz',
                                                             'hands.npz', 'qa_ref.json') if os.path.isfile(f'{root}/{f}')}
        chain = [dict(tool='pipeline/mkref.py (inferred from the output folder)', commit=None, run_id=run_id_of(ref),
                      artifact=os.path.abspath(ref), sha256=sha(ref), command=None, inputs=ins)]
        source = 'inferred (no REF.parquet.prov.json, no --prov)'
    verified, missing = {}, []
    for s in chain:
        for p, h in [(s.get('artifact'), s.get('sha256'))] + list(s.get('inputs', {}).items()):
            r = denied(p, h)
            if r:
                raise Refuse(f'reference provenance touches a denied input: {p} ({r})')
            if p and h and os.path.isfile(p):
                verified[p] = sha(p) == h
                if not verified[p]:
                    raise Refuse(f'reference provenance: {p} does not match its recorded sha256')
        missing += [f"{s.get('artifact')}: {k}" for k in ('tool', 'commit', 'run_id') if not s.get(k)]
        missing += [f'{p}: sha256' for p, h in s.get('inputs', {}).items() if not h]
    seen_names = {os.path.basename(p) for s in chain for p in [s.get('artifact') or ''] + list(s.get('inputs', {}))}
    absent = [f for f in PERCEPTION if f not in seen_names and not (f == 'hands_refined.npz' and 'hands.npz' in seen_names)]
    return dict(source=source, complete=not missing and not absent, missing=missing, perception_absent=absent,
                chain=chain, verified_sha256=verified)


def git_commit():
    try:
        c = subprocess.run(['git', '-C', REPO, 'rev-parse', 'HEAD'], capture_output=True, text=True, check=True).stdout.strip()
        d = subprocess.run(['git', '-C', REPO, 'status', '--porcelain', '--', TOOL], capture_output=True, text=True).stdout.strip()
        return c, bool(d)
    except Exception:
        return None, None


def load_fit(fit_dir, names, O, sim_dir, fit_commit, flags):
    """Fit block and the fit's poses in the reference frame, or (block, None) when the residual must stay NaN."""
    pj = f'{fit_dir}/phys_fit.json'; J = json.load(open(pj)); A = J.get('args', {})
    inp, meshes, props = A.get('inp'), A.get('meshes'), A.get('props')
    files = [pj, f'{fit_dir}/poses_world_vo.npz', props] + [f'{meshes}/{n}.glb' for n in names] + \
            [f'{inp}/{f}' for f in ('poses.npz', 'poses_world_vo.npz', 'table_frame.npz', 'hands_refined.npz', 'hands.npz')]
    for p in files:
        r = denied(p)
        if r:
            raise Refuse(f'--fit input {p} is denied ({r}); a fit on ground truth or scans is never read')
    argv = J.get('argv') or ['pipeline/phys_fit.py', inp, A.get('out')] + sum(
        ([f'--{k}', str(v)] for k, v in A.items() if k not in ('inp', 'out')), [])
    block = dict(tool='pipeline/phys_fit.py', commit=J.get('commit') or fit_commit, argv=argv, argv_reconstructed='argv' not in J,
                 meshes={n: sha(f'{meshes}/{n}.glb') for n in names}, meshes_dir=os.path.abspath(meshes),
                 props=dict(path=os.path.abspath(props), sha256=sha(props)),
                 prior=dict(sig_p=A.get('sig_p'), sig_r_deg=A.get('sig_r_deg'), hold_f0=A.get('hold_f0', 0)),
                 inputs={os.path.abspath(p): sha(p) for p in files if p and os.path.isfile(p)}, used=False)
    why = []
    if not block['commit']:
        why.append('fit_commit_unknown')
    if os.path.realpath(meshes) != os.path.realpath(f'{sim_dir}/_fit'):
        why.append('fit_meshes_not_round_fit')
    if os.path.realpath(props) != os.path.realpath(f'{sim_dir}/props_gmg.json'):
        why.append('fit_props_not_round_props')
    if not (np.isclose(A.get('sig_p', 0), 0.01) and np.isclose(A.get('sig_r_deg', 0), 3.0)):
        why.append('fit_prior_not_1cm_3deg')
    TF = np.load(f'{inp}/table_frame.npz'); Win = np.load(f'{inp}/poses_world_vo.npz'); Wf = np.load(f'{fit_dir}/poses_world_vo.npz')
    tn = [str(x) for x in TF['names']]; zs = TF['object_z_shift'] if 'object_z_shift' in TF.files else np.zeros(len(tn))
    Tt = TF['T_table_from_world']

    def to_ref(W):
        Q = np.stack([Tt @ W[n] for n in names], 1)
        Q[..., 2, 3] += np.array([zs[tn.index(n)] for n in names]); return Q
    Oin, Ofit = to_ref(Win), to_ref(Wf)
    if Oin.shape != O.shape:
        why.append(f'fit_frames {Oin.shape[0]} != reference {O.shape[0]}')
    else:
        dp = np.linalg.norm(Oin[..., :3, 3] - O[..., :3, 3], axis=-1).max()
        dr = np.degrees(Rot.from_matrix((np.swapaxes(Oin[..., :3, :3], -1, -2) @ O[..., :3, :3]).reshape(-1, 3, 3)).magnitude().max())
        block['input_vs_reference'] = dict(max_mm=round(float(dp * 1e3), 4), max_deg=round(float(dr), 4))
        if dp > 1e-3 or dr > 0.1:
            why.append('fit_input_is_not_this_reference')
    block['nan_reasons'] = why; flags += why
    if why:
        return block, None
    block['used'] = True
    return block, Ofit


# ---------------------------------------------------------------- main
def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('ref'); ap.add_argument('sim_dir'); ap.add_argument('out')
    ap.add_argument('--round', type=int, default=None); ap.add_argument('--pitch_mm', type=float, default=2.0)
    ap.add_argument('--surf_mm', type=float, default=0.5); ap.add_argument('--margin_cm', type=float, default=3.0)
    ap.add_argument('--prov', default=None); ap.add_argument('--fit', default=None); ap.add_argument('--fit_commit', default=None)
    a = ap.parse_args(argv); t0 = time.time(); flags = []
    out_npz = a.out if a.out.endswith('.npz') else a.out + '.npz'; out_json = out_npz[:-4] + '.json'
    if os.path.exists(out_npz) or os.path.exists(out_json):
        raise Refuse(f'{out_npz} or {out_json} exists (runs are never overwritten)')
    if not 0 < a.pitch_mm <= 2.0:
        raise Refuse('--pitch_mm must be in (0, 2]')
    pitch, h, sim = a.pitch_mm / 1000, a.surf_mm / 1000, os.path.abspath(a.sim_dir)
    r = denied(a.ref)
    if r:
        raise Refuse(f'reference {a.ref} is denied ({r})')
    prov = provenance(a.ref, a.prov)
    if not prov['complete']:
        flags.append('reference_provenance_incomplete')
    names, O, P, Q, fps = load_ref(a.ref); T, B = O.shape[:2]; Oi = inv_pose(O)

    mp = f'{sim}/manifest.json'; man = json.load(open(mp)) if os.path.isfile(mp) else None
    if man is None:
        flags.append('no_manifest (fiducials computed here; the gmg validator needs the round manifest)')
    else:
        m_ep = re.search(r'(\d+)', str(man.get('episode', ''))); r_ep = re.search(r'sequence_id=t3_ep0*(\d+)', a.ref)
        if m_ep and r_ep and int(m_ep.group(1)) != int(r_ep.group(1)):
            raise Refuse(f"manifest episode {man.get('episode')} != reference episode {r_ep.group(1)}")
    rnd = a.round if a.round is not None else (man or {}).get('round')
    if rnd is None:
        m = re.search(r'(?:^|/)r(\d+)$', sim.rstrip('/')); rnd = int(m.group(1)) if m else None
    U, meshes, F = [], {}, []
    for n in names:
        files = sorted(glob.glob(f'{sim}/{n}/piece_*.obj'))
        if not files:
            raise Refuse(f'no {sim}/{n}/piece_*.obj')
        meshes[n] = {os.path.basename(f): sha(f) for f in files}
        mf, fid = manifest_entry(man, n) if man else (None, None)
        if man is not None:
            if not mf:
                raise Refuse(f'manifest.json has no file hashes for {n}')
            bad = [f for f, s in meshes[n].items() if mf.get(f) != s]
            if bad:
                raise Refuse(f'{n}: {bad} differ from (or are missing in) the round manifest')
            if fid is None:
                raise Refuse(f'manifest.json has no fiducials for {n}')
        U.append(Union(files)); F.append(fid if fid is not None else obb_fiducials(U[-1].V))
        nc = [os.path.basename(f) for f, (hv, mv) in zip(files, U[-1].vol) if mv is not None and abs(mv - hv) > 0.01 * hv]
        if nc:
            flags.append(f'{n}: non-convex piece files {nc} (their hulls are used)')
    F = np.stack(F); fbox = {n: fiducial_box(F[b], U[b].V) for b, n in enumerate(names)}
    bad = [n for n in names if not fbox[n]['ok']]
    if bad:
        raise Refuse(f'fiducials do not match the pieces of {bad} (re-centred pieces or a stale manifest): {[fbox[n] for n in bad]}')
    S = [u.lattice(pitch) for u in U]
    t_setup = time.time() - t0

    # ---- per frame and ordered pair
    C = np.stack([np.einsum('tij,j->ti', O[:, b, :3, :3], U[b].centre) + O[:, b, :3, 3] for b in range(B)], 1)
    rows, pts, lbs = [], [], []
    for t in range(B):
        for p in range(B):
            if t == p:
                continue
            near = np.linalg.norm(C[:, t] - C[:, p], axis=1) <= U[t].radius + U[p].radius + a.margin_cm / 100
            for f in np.nonzero(near)[0]:
                R = Oi[f, t] @ O[f, p]
                X = S[p] @ R[:3, :3].T + R[:3, 3]
                idx = np.nonzero(np.all((X > U[t].alo) & (X < U[t].ahi), 1))[0]
                lb = U[t].depth_lb(X[idx]) if len(idx) else np.zeros(0); k = lb > EPS
                rows.append((f, t, p, R, int(k.sum()))); pts.append(X[idx[k]]); lbs.append(lb[k])
    order = sorted(range(len(rows)), key=lambda i: rows[i][:3])
    rows, pts, lbs = [rows[i] for i in order], [pts[i] for i in order], [lbs[i] for i in order]
    Pn = len(rows); cnt = np.array([r[4] for r in rows], int)
    fp_frame = np.array([r[0] for r in rows], np.int32); fp_t = np.array([r[1] for r in rows], np.int16)
    fp_p = np.array([r[2] for r in rows], np.int16); relT = np.array([r[3] for r in rows], float).reshape(Pn, 4, 4)
    vol = (cnt * pitch ** 3).astype(np.float32); row_of = np.repeat(np.arange(Pn), cnt)
    X = np.concatenate(pts) if Pn else np.zeros((0, 3)); N = len(X)
    depth_lb = np.concatenate(lbs) if Pn else np.zeros(0); depth = np.zeros(N); del pts, lbs
    for t in range(B):
        m = fp_t[row_of] == t if N else np.zeros(0, bool)
        if m.any():
            depth[m] = U[t].depth(X[m], h, depth_lb[m])
    t_loop = time.time() - t0 - t_setup

    # ---- fiducials at f_star, containment, rigidity
    vf = np.bincount(fp_frame, weights=vol, minlength=T) if Pn else np.zeros(T)
    f_star = int(np.argmax(vf)) if vf.max() > 0 else 0
    if vf.max() <= 0:
        flags.append('no_intrusion (f_star = 0)')
    fw = np.einsum('bij,bkj->bki', O[f_star, :, :3, :3], F) + O[f_star, :, None, :3, 3]          # file -> world (samples)
    fb = np.einsum('bij,bkj->bki', Oi[f_star, :, :3, :3], fw) + Oi[f_star, :, None, :3, 3]       # world -> file (pts_local)
    ind = np.stack([F[b] @ quat_wxyz_matrix(Q[f_star, b]).T + P[f_star, b] for b in range(B)])
    e_rt, e_ind = float(np.linalg.norm(fb - F, axis=-1).max()), float(np.linalg.norm(fw - ind, axis=-1).max())
    if e_rt > FID_TOL or e_ind > FID_TOL:
        raise Refuse(f'fiducial round trip {e_rt * 1e3:.3f} mm / vs the parquet pose {e_ind * 1e3:.3f} mm (> 0.5 mm)')
    Xf = X.astype(np.float32).astype(float); rng = np.random.default_rng(0)     # as the validator reads them
    k = rng.choice(N, min(N, 10000), replace=False) if N else np.zeros(0, int)
    ok_t, ok_p, rk = np.zeros(len(k), bool), np.zeros(len(k), bool), row_of[k] if N else np.zeros(0, int)
    for b in range(B):
        m = fp_t[rk] == b
        ok_t[m] = U[b].depth_lb(Xf[k[m]]) > 0
        m = fp_p[rk] == b; Ri = inv_pose(relT[rk[m]])
        ok_p[m] = U[b].depth_lb(np.einsum('nij,nj->ni', Ri[:, :3, :3], Xf[k[m]]) + Ri[:, :3, 3]) > 0
    in_t, in_p = (float(ok_t.mean()), float(ok_p.mean())) if N else (1.0, 1.0)
    if in_t < 0.99 or in_p < 0.99:
        raise Refuse(f'containment target {in_t:.4f} / partner {in_p:.4f} < 0.99')
    rig = float(np.abs(np.swapaxes(relT[:, :3, :3], 1, 2) @ relT[:, :3, :3] - np.eye(3)).max()) if Pn else 0.0

    # ---- optional push residual on the fit's poses
    pres = np.full(Pn, np.nan, np.float32); fit_block = None; t_fit = 0.0
    if a.fit:
        t1 = time.time(); fit_block, Ofit = load_fit(os.path.abspath(a.fit), names, O, sim, a.fit_commit, flags)
        if Ofit is not None:
            Ofi = inv_pose(Ofit)
            for i in range(Pn):
                f, t, p = int(fp_frame[i]), int(fp_t[i]), int(fp_p[i]); R = Ofi[f, t] @ Ofit[f, p]
                pres[i] = push_residual(U[t], S[p] @ R[:3, :3].T + R[:3, 3])
        t_fit = time.time() - t1

    commit, dirty = git_commit()
    hdr = dict(schema=SCHEMA, objects=names, round=rnd, sim_dir=sim, meshes=meshes,
               manifest=dict(path=mp, sha256=sha(mp)) if man is not None else None, pitch_m=pitch, tool=TOOL,
               tool_sha256=sha(os.path.abspath(__file__)), commit=commit, commit_dirty=dirty, argv=sys.argv if argv is None else [TOOL] + list(argv),
               reference=dict(path=os.path.abspath(a.ref), sha256=sha(a.ref), provenance=prov),
               fit=fit_block, pose_source='reference', frames=T, fps=fps, f_star=f_star,
               fiducials_file={n: F[b].tolist() for b, n in enumerate(names)},
               fiducials_world={n: fw[b].tolist() for b, n in enumerate(names)},
               fiducials_back={n: fb[b].tolist() for b, n in enumerate(names)},
               checks=dict(fiducial_round_trip_mm=e_rt * 1e3, fiducial_vs_parquet_mm=e_ind * 1e3, fiducial_box=fbox,
                           containment_target=float(in_t), containment_partner=float(in_p), containment_n=int(len(k)),
                           rel_T_orthonormality_err=rig),
               definitions=dict(
                   samples='lattice (i+1/2)*pitch in the partner file frame, > 1 um inside >= 1 convex piece (half-spaces)',
                   inside='> 1 um inside at least one target piece', rows=f'every frame x ordered pair with bounding spheres within {a.margin_cm} cm',
                   depth_m=f'distance to the union surface of the target pieces (surface samples at {a.surf_mm} mm; upper bound, '
                           f'<= {0.71 * a.surf_mm:.2f} mm too deep; never below depth_lb_m)',
                   depth_lb_m='max over target pieces of the per-piece half-space depth (lower bound of depth_m)',
                   intr_vol_m3='samples x pitch^3, reference poses (before any correction)',
                   pushed_residual_m='NaN: no validated fit; else min translation (42 icosphere dirs + 10/3 deg refinement, '
                                     'exact per direction) on the fit poses; 0 none remains; inf > 10 cm'),
               counts=dict(samples=int(N), rows=int(Pn), rows_with_intrusion=int((cnt > 0).sum()),
                           partner_samples={n: int(len(S[b])) for b, n in enumerate(names)},
                           pieces={n: len(U[b].H) for b, n in enumerate(names)}),
               flags=flags, seconds=dict(setup=round(t_setup, 2), loop=round(t_loop, 2), fit=round(t_fit, 2),
                                         total=round(time.time() - t0, 2)))
    os.makedirs(os.path.dirname(os.path.abspath(out_npz)), exist_ok=True)
    np.savez_compressed(out_npz, frame=fp_frame[row_of] if N else np.zeros(0, np.int32), target=fp_t[row_of] if N else np.zeros(0, np.int16),
                        partner=fp_p[row_of] if N else np.zeros(0, np.int16), pts_local=X.astype(np.float32),
                        depth_m=depth.astype(np.float32), depth_lb_m=depth_lb.astype(np.float32), fp_frame=fp_frame,
                        fp_target=fp_t, fp_partner=fp_p, rel_T=relT, pushed_residual_m=pres, intr_vol_m3=vol,
                        objects=np.array(names), f_star=np.int32(f_star), fiducials_world=fw, fiducials_back=fb)
    json.dump(hdr, open(out_json, 'w'), indent=1, default=lambda o: o.item() if hasattr(o, 'item') else str(o))
    print(f'{SCHEMA}: {N} samples in {int((cnt > 0).sum())}/{Pn} frame-pairs, T={T}, B={B}, f_star={f_star}, '
          f'max vol {vol.max() * 1e6 if Pn else 0:.2f} cm3; flags {flags}; {hdr["seconds"]} s -> {out_npz}')
    return hdr


if __name__ == '__main__':
    main()
