"""Independent re-implementation for verifying the sam-placement diagnosis (2026-10-30).
Written from scratch (does not import diag/sam-placement/common.py).
[D] functions read the public scan; they are diagnostic only and never feed a method.
"""
import os
for _k in ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS'):
    os.environ.setdefault(_k, '1')
import itertools, math, json
import numpy as np
import trimesh
from scipy.spatial import cKDTree

SCR = '/tmp/claude-0/-home-user-v2d-track3/90d4009c-b597-536b-9d55-58f81afca135/scratchpad'
GEN = f'{SCR}/gen/mesh-20261029-gen-f3fbeb0/results/gen'
OUT = f'{SCR}/diag/sam-placement-verify'
LIB = '/home/user/v2d-track3/meshes/library_v3'
EPS = dict(white_pot=41, white_pot_lid=2, blue_cup=22, water_pitcher=22, wooden_piece_1=23, wooden_piece_2=23,
           plastic_dish_rack=26, mini_sweeper=31, mini_dust_pan=39, beige_cup=11)
KTAG = dict(white_pot='k279', white_pot_lid='k321', blue_cup='k156', water_pitcher='k174', wooden_piece_1='k27',
            wooden_piece_2='k6', plastic_dish_rack='k144', mini_sweeper='k270', mini_dust_pan='k297', beige_cup='k6')
KIT_SYM = dict(beige_cup='axial', blue_cup='axial', white_pot_lid='half')   # checked against kit tracks.json below


def kit_sym():
    t = json.load(open(f'{SCR}/loc/kit/v2d_submission_kit/config/tracks.json'))['tracks']['track_3']
    d = {n: 'axial' for n in t['axially_symmetric_objects']}
    d.update({n: 'half' for n in t['half_turn_symmetric_objects']})
    return d


def load(path):
    m = trimesh.load(path, force='mesh', process=False)
    return np.asarray(m.vertices, float), np.asarray(m.faces, np.int64)


def scan_file(obj):
    for c in (f'{SCR}/loc/t3/mesh/{obj}/{obj}_visual.glb', f'{SCR}/loc/t3/mesh/{obj}/{obj}.glb'):
        if os.path.exists(c):
            return c


def load_scan(obj):                                                      # [D]
    return load(scan_file(obj))


def tri_area(v, f):
    a, b, c = v[f[:, 0]], v[f[:, 1]], v[f[:, 2]]
    return 0.5 * np.linalg.norm(np.cross(b - a, c - a), axis=1)


def sample(v, f, n, seed=0):
    ar = tri_area(v, f)
    rng = np.random.default_rng(seed)
    idx = rng.choice(len(f), n, p=ar / ar.sum())
    r1, r2 = rng.random(n), rng.random(n)
    s = np.sqrt(r1)[:, None]
    a, b, c = v[f[idx, 0]], v[f[idx, 1]], v[f[idx, 2]]
    return (1 - s) * a + s * (1 - r2[:, None]) * b + s * r2[:, None] * c


def centroid(v, f):
    ar = tri_area(v, f)
    return (v[f].mean(1) * ar[:, None]).sum(0) / ar.sum()


def rms_radius(v, f, n=20000):
    p = sample(v, f, n, 3)
    return float(np.sqrt(((p - p.mean(0)) ** 2).sum(1).mean()))


def umeyama(src, dst, scale=True):
    ms, md = src.mean(0), dst.mean(0)
    a, b = src - ms, dst - md
    U, S, Vt = np.linalg.svd(b.T @ a / len(a))
    D = np.eye(3)
    if np.linalg.det(U @ Vt) < 0:
        D[2, 2] = -1
    R = U @ D @ Vt
    s = float(np.trace(np.diag(S) @ D) / (a ** 2).sum(1).mean()) if scale else 1.0
    return s, R, md - s * R @ ms


def pca_frame(x):
    c = x.mean(0)
    w, V = np.linalg.eigh(np.cov((x - c).T))
    V = V[:, ::-1].copy()
    if np.linalg.det(V) < 0:
        V[:, 2] *= -1
    return c, V, np.sqrt(np.maximum(w[::-1], 0))


def cube_rots():
    out = []
    for p in itertools.permutations(range(3)):
        for sg in itertools.product((1, -1), repeat=3):
            M = np.zeros((3, 3))
            for i in range(3):
                M[i, p[i]] = sg[i]
            if np.linalg.det(M) > 0:
                out.append(M)
    return out


def apply(T, x):
    s, R, t = T
    return s * x @ R.T + t


def sym_icp(A, B, T0, iters=60, keep=0.9, scale=True):
    """symmetric trimmed ICP, maps A onto B. returns T, trimmed sym distance, untrimmed sym distance"""
    s, R, t = T0
    tb = cKDTree(B)
    prev = None
    for _ in range(iters):
        X = s * A @ R.T + t
        dab, iab = tb.query(X)
        dba, iba = cKDTree(X).query(B)
        ka = dab <= np.quantile(dab, keep)
        kb = dba <= np.quantile(dba, keep)
        src = np.r_[A[ka], A[iba[kb]]]
        dst = np.r_[B[iab[ka]], B[kb]]
        s, R, t = umeyama(src, dst, scale)
        cur = dab[ka].mean() + dba[kb].mean()
        if prev is not None and abs(prev - cur) < 1e-9:
            break
        prev = cur
    X = s * A @ R.T + t
    dab = tb.query(X)[0]
    dba = cKDTree(X).query(B)[0]
    tr = 0.5 * (np.sort(dab)[:int(keep * len(dab))].mean() + np.sort(dba)[:int(keep * len(dba))].mean())
    return (s, R, t), float(tr), float(0.5 * (dab.mean() + dba.mean()))


def multi_start(A, B, scale=True, iters=60, keep=0.9, include_identity=True, return_all=False):
    ca, Va, sa = pca_frame(A)
    cb, Vb, sb = pca_frame(B)
    s0 = float(np.sqrt((sb ** 2).sum() / (sa ** 2).sum())) if scale else 1.0
    starts = []
    if include_identity:
        starts.append((1.0, np.eye(3), np.zeros(3)))
    for M in cube_rots():
        R = Vb @ M @ Va.T
        starts.append((s0, R, cb - s0 * R @ ca))
    res = []
    for T0 in starts:
        T, tr, un = sym_icp(A, B, T0, iters, keep, scale)
        res.append((tr, un, T))
    res.sort(key=lambda r: r[0])
    return res if return_all else res[0]


def rot_angle(R):
    return math.degrees(math.acos(max(-1.0, min(1.0, (np.trace(R) - 1) / 2))))


def axis_rot(a, th):
    a = a / np.linalg.norm(a)
    K = np.array([[0, -a[2], a[1]], [a[2], 0, -a[0]], [-a[1], a[0], 0]])
    return np.eye(3) + math.sin(th) * K + (1 - math.cos(th)) * K @ K


def sym_axis(P, kind):
    """axis among PCA axes under which P is most invariant (90 deg for axial, 180 for half)"""
    c, V, _ = pca_frame(P)
    Q = P - c
    tq = cKDTree(Q)
    ang = math.pi / 2 if kind == 'axial' else math.pi
    best = None
    for k in range(3):
        d = tq.query(Q @ axis_rot(V[:, k], ang).T)[0].mean()
        if best is None or d < best[0]:
            best = (d, V[:, k])
    return best[1]
