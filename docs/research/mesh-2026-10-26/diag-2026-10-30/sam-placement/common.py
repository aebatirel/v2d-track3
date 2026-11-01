"""Shared helpers for the sam-placement diagnosis (2026-10-30).

GT-free parts (usable by a method): load our observed points / free-space grid / library_v3 mesh, Sim(3) fits.
[D] parts (diagnostic only): load_scan(), decompose() against the public scan.
"""
import itertools, json, math, os
import numpy as np
import trimesh
from scipy.spatial import cKDTree

SCR = '/tmp/claude-0/-home-user-v2d-track3/90d4009c-b597-536b-9d55-58f81afca135/scratchpad'
GEN = f'{SCR}/gen/mesh-20261029-gen-f3fbeb0/results/gen'
OUT = f'{SCR}/diag/sam-placement'
LIB = '/home/user/v2d-track3/meshes/library_v3'
EP = dict(white_pot=41, white_pot_lid=2, blue_cup=22, water_pitcher=22, wooden_piece_1=23, wooden_piece_2=23,
          plastic_dish_rack=26, mini_sweeper=31, mini_dust_pan=39, beige_cup=11)
TAG = dict(white_pot='k279', white_pot_lid='k321', blue_cup='k156', water_pitcher='k174', wooden_piece_1='k27',
           wooden_piece_2='k6', plastic_dish_rack='k144', mini_sweeper='k270', mini_dust_pan='k297', beige_cup='k6')
OBJS = list(EP)
SYM = dict(beige_cup='axial', blue_cup='axial', white_pot_lid='half')


# ------------------------------------------------------------------ geometry
def rotations24():
    out = []
    for perm in itertools.permutations(range(3)):
        for signs in itertools.product([1, -1], repeat=3):
            R = np.zeros((3, 3))
            for i, (p, s) in enumerate(zip(perm, signs)):
                R[i, p] = s
            if np.linalg.det(R) > 0:
                out.append(R)
    return out


def umeyama(src, dst, w=None, with_scale=True):
    if w is None:
        w = np.ones(len(src))
    w = w / w.sum()
    ms, md = w @ src, w @ dst
    a, b = src - ms, dst - md
    U, S, Vt = np.linalg.svd((b * w[:, None]).T @ a)
    D = np.eye(3); D[2, 2] = np.sign(np.linalg.det(U @ Vt))
    R = U @ D @ Vt
    s = np.trace(np.diag(S) @ D) / (w @ (a ** 2).sum(1)) if with_scale else 1.0
    return s, R, md - s * R @ ms


def pca(x):
    c = x.mean(0)
    w, V = np.linalg.eigh(np.cov((x - c).T))
    V = V[:, ::-1].copy()
    if np.linalg.det(V) < 0:
        V[:, 2] *= -1
    return c, V, np.sqrt(np.maximum(w[::-1], 1e-12))


def angle_deg(R):
    return math.degrees(math.acos(max(-1.0, min(1.0, (np.trace(R) - 1) / 2))))


def rot_axis(R):
    w = np.array([R[2, 1] - R[1, 2], R[0, 2] - R[2, 0], R[1, 0] - R[0, 1]])
    n = np.linalg.norm(w)
    if n < 1e-9:
        if np.trace(R) > 0:
            return np.array([0, 0, 1.0])
        ev, V = np.linalg.eigh((R + np.eye(3)) / 2)
        return V[:, -1]
    return w / n


def swing_twist(R, a):
    """Split R = R_swing @ R_twist with twist about a. Returns (tilt_deg = angle between R a and a, twist_deg)."""
    a = a / np.linalg.norm(a)
    from scipy.spatial.transform import Rotation
    q = Rotation.from_matrix(R).as_quat()          # x y z w
    v = q[:3]; p = (v @ a) * a
    tw = np.r_[p, q[3]]
    n = np.linalg.norm(tw)
    twist = 0.0 if n < 1e-12 else math.degrees(2 * math.atan2(np.linalg.norm(p), abs(q[3])))
    tilt = math.degrees(math.acos(np.clip((R @ a) @ a, -1, 1)))
    return tilt, twist


def surf(mesh, n, seed=0):
    p, fi = trimesh.sample.sample_surface(mesh, n, seed=seed)
    return np.asarray(p), np.asarray(mesh.face_normals[fi])


def moments(mesh):
    tri = mesh.triangles
    ar = mesh.area_faces
    k = ar > 1e-14
    tri, ar = tri[k], ar[k]
    tot = ar.sum()
    c = (tri.mean(1) * ar[:, None]).sum(0) / tot
    ce = tri - c
    sq = np.einsum('tij,tij->ti', ce, ce).sum(1)
    cr = (np.einsum('ti,ti->t', ce[:, 0], ce[:, 1]) + np.einsum('ti,ti->t', ce[:, 0], ce[:, 2])
          + np.einsum('ti,ti->t', ce[:, 1], ce[:, 2]))
    r = math.sqrt(max((ar * (sq + cr) / 6).sum() / tot, 0))
    return c, r


def apply(T, x):
    s, R, t = T
    return s * x @ R.T + t


def compose(A, B):
    """A o B."""
    sa, Ra, ta = A; sb, Rb, tb = B
    return sa * sb, Ra @ Rb, sa * Ra @ tb + ta


def inv(T):
    s, R, t = T
    return 1 / s, R.T, -(R.T @ t) / s


# ------------------------------------------------------------------ data
def load_mesh(path):
    return trimesh.load(path, force='mesh', process=False)


def load_scan(obj):
    """[D] the kit-budgeted public scan, as mesh_metric caches it."""
    z = np.load(f'{SCR}/interact/v5/metric/cache/{obj}_b4096.npz')
    return trimesh.Trimesh(z['v'], z['f'], process=False)


def load_obs(obj, n=20000, seed=0):
    z = np.load(f'{SCR}/obs_all/ep{EP[obj]}_{obj}.npz')
    rng = np.random.default_rng(seed)
    pts = z['pts']
    i = rng.choice(len(pts), min(n, len(pts)), replace=False)
    return dict(pts=pts[i].astype(np.float64), cam=z['cam'][i].astype(np.float64), frame=z['frame'][i],
                lo=z['lo'], vox=float(z['vox']), hits=z['hits'], free=z['free'],
                all_frame=z['frame'], all_cam=z['cam'])


def crop_frame(obj):
    d = json.load(open(f'{SCR}/crops/ep{EP[obj]}/{obj}_crops.json'))
    for c in d['candidates']:
        if c.get('tag') == f'{obj}_{TAG[obj]}':
            return c['k'], c['j']
    raise KeyError(obj)


def crop_cam(obj, obs):
    """GT-free: our camera centre (object frame) at the crop frame (nearest observed frame)."""
    k, j = crop_frame(obj)
    fr = obs['all_frame']
    uf = np.unique(fr)
    f0 = uf[np.argmin(np.abs(uf - j))]
    sel = np.flatnonzero(fr == f0)[:2000]
    return obs['all_cam'][sel].mean(0), int(f0)


def gen_paths(model, obj, seed):
    if model == 'pixal_mv':
        return None, f'{GEN}/pixal_mv/ep{EP[obj]}_{obj}_s{seed}.ply'
    tag = f'{obj}_{TAG[obj]}_s{seed}'
    return f'{GEN}/{model}/{tag}.ply', f'{GEN}/{model}_sim3/{tag}.ply'


def recover_T(raw, placed):
    """Exact Sim(3) used by sim3_fit (vertex order is preserved)."""
    s, R, t = umeyama(np.asarray(raw.vertices), np.asarray(placed.vertices))
    res = np.abs(apply((s, R, t), np.asarray(raw.vertices)) - placed.vertices).max()
    return (s, R, t), res


# ------------------------------------------------------------------ registration
def sim3_icp(M, Y, T0, iters=40, keep_m=0.9, keep_y=0.9, with_scale=True, wm=None, fix_scale=None):
    """Symmetric trimmed ICP of points M (source) onto Y (target), starting at T0. wm: per-M weight (visibility)."""
    ty = cKDTree(Y)
    T = T0
    for _ in range(iters):
        X = apply(T, M)
        tx = cKDTree(X)
        dy, iy = tx.query(Y)                 # target -> source
        dm, im = ty.query(X)                 # source -> target
        ky = dy <= np.quantile(dy, keep_y)
        if wm is None:
            km = dm <= np.quantile(dm, keep_m)
        else:
            sel = wm > 0
            km = np.zeros(len(M), bool)
            if sel.sum() > 10:
                km[sel] = dm[sel] <= np.quantile(dm[sel], keep_m)
        src = np.r_[M[iy[ky]], M[km]]; dst = np.r_[Y[ky], Y[im[km]]]
        s, R, t = umeyama(src, dst, with_scale=with_scale and fix_scale is None)
        if fix_scale is not None:
            # rigid fit of the scaled source
            _, R, t = umeyama(fix_scale * src, dst, with_scale=False)
            s = fix_scale
        T = (s, R, t)
    return T


def sym_dist(A, B, keep=1.0):
    da = cKDTree(B).query(A)[0]; db = cKDTree(A).query(B)[0]
    if keep < 1:
        da = np.sort(da)[:int(keep * len(da))]; db = np.sort(db)[:int(keep * len(db))]
    return 0.5 * (da.mean() + db.mean())


def best_sim3(M, Y, extra_starts=(), keep=0.9, iters=40, with_scale=True):
    """Multi-start (24 PCA cube starts + extra) Sim(3) symmetric trimmed ICP. Returns best T and all results."""
    cm, Vm, sm = pca(M); cy, Vy, sy = pca(Y)
    s0 = float(np.exp(np.mean(np.log(sy / sm)))) if with_scale else 1.0
    starts = []
    for Rs in rotations24():
        R = Vy @ Rs @ Vm.T
        starts.append((s0, R, cy - s0 * R @ cm))
    starts += list(extra_starts)
    res = []
    for T0 in starts:
        T = sim3_icp(M, Y, T0, iters=iters, keep_m=keep, keep_y=keep, with_scale=with_scale)
        res.append((sym_dist(apply(T, M), Y, keep), T))
    res.sort(key=lambda r: r[0])
    return res[0][1], res
