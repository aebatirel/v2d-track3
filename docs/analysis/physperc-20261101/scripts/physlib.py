"""physperc shared helpers (GT-free: our tracks, our meshes, our table plane from frame-0 depth, our hands)."""
import json, os, functools, numpy as np, trimesh
from scipy.spatial import cKDTree


def load_vf(path):
    m = trimesh.load(path, force='mesh')
    return np.asarray(m.vertices, np.float64), np.asarray(m.faces, np.int64)


def scan_path(S, n):   # scoring / diagnostics only
    q = f'{S}/t3/mesh/{n}/{n}.glb'
    return q if os.path.exists(q) else f'{S}/t3/mesh/{n}/{n}_visual.glb'


@functools.lru_cache(None)
def mesh(path):
    return trimesh.load(path, force='mesh')


@functools.lru_cache(None)
def surf_pts(path, n=4000):
    m = mesh(path)
    p, _ = trimesh.sample.sample_surface_even(m, n, seed=0)
    return np.asarray(p, np.float64)


def table_up(S, e, P, MD):
    """Our table plane (episode bundle: frame-0 depth RANSAC, camera frame at f0 = our world frame).
    Returns unit up and d with signed height h(x) = up.x + d (objects on the + side)."""
    E = json.load(open(f'{S}/data/b4/ep{e}/episode.json'))
    n = np.asarray(E['table']['n'], np.float64); d = float(E['table']['d'])
    s = np.linalg.norm(n); n, d = n / s, d / s
    hs = [n @ P[k][0][:3, 3] + d for k in P.files]
    if np.median(hs) < 0:
        n, d = -n, -d
    return n, d


def hand_joints(S, e):
    H = np.load(f'{S}/data/b4/ep{e}/hands.npz')
    out = []
    for t in range(int(H['T'])):
        J = []
        for side in ('left', 'right'):
            if H[f'valid_{side}'][t]:
                j = np.asarray(H[f'joints_{side}'][t], np.float64)
                J.append(j[np.isfinite(j).all(1)])
        out.append(np.vstack(J) if J else np.zeros((0, 3)))
    return out


def hand_dist(J, t, mpath, T):
    if t >= len(J) or not len(J[t]):
        return np.inf
    X = (J[t] - T[:3, 3]) @ T[:3, :3]
    d, _ = cKDTree(surf_pts(mpath)).query(X)
    return float(d.min())


def lowest_gap(mpath, T, up, d):
    v = np.asarray(mesh(mpath).convex_hull.vertices)
    return float(((v @ T[:3, :3].T + T[:3, 3]) @ up + d).min())


def shell_com(mpath):
    m = mesh(mpath)
    return np.asarray(m.triangles_center.T @ m.area_faces / m.area, np.float64)


@functools.lru_cache(None)
def stable_poses(mpath):
    """Stable resting poses of our mesh (trimesh quasi-static, thin-shell COM). down[k] = body-frame unit vector
    that points to the table in pose k."""
    m = mesh(mpath)
    Ts, pr = trimesh.poses.compute_stable_poses(m, center_mass=shell_com(mpath), n_samples=1, threshold=0.0)
    down = np.array([T[:3, :3].T @ np.array([0, 0, -1.0]) for T in Ts])
    return dict(down=down, prob=np.asarray(pr), T=np.asarray(Ts))


def nearest_stable(sp, g_body, min_prob=0.0):
    g = g_body / np.linalg.norm(g_body)
    a = np.degrees(np.arccos(np.clip(sp['down'] @ g, -1, 1)))
    a = np.where(sp['prob'] >= min_prob, a, np.inf)
    k = int(np.argmin(a))
    return k, float(a[k])


def swing(a, b):
    """Minimal rotation taking unit vector a onto unit vector b."""
    a = a / np.linalg.norm(a); b = b / np.linalg.norm(b)
    v = np.cross(a, b); c = float(a @ b); s = np.linalg.norm(v)
    if s < 1e-12:
        return np.eye(3)
    K = np.array([[0, -v[2], v[1]], [v[2], 0, -v[0]], [-v[1], v[0], 0]])
    return np.eye(3) + K + K @ K * ((1 - c) / s ** 2)
