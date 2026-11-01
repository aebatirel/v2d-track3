"""posefix library (GT-free): signed-distance grids of our meshes, hands-near test, penetration measures.

Every function here reads only our own meshes (the pack 9a+ visual meshes, decimated with the kit's budget_mesh 4096 /
4096 exactly as the scorer decimates candidates), our own tracks (world_vo = camera frame 0), our own MediaPipe hands
(gmg M1, v6 run, same world frame) and our own table plane (v6 bundle episode.json `table`, frame-0 depth RANSAC).
No parquet, scan or mocap is opened here.
"""
import json, os, sys
import numpy as np
import trimesh
from scipy.spatial import cKDTree
from scipy.ndimage import map_coordinates

S = '/tmp/claude-0/-home-user-v2d-track3/90d4009c-b597-536b-9d55-58f81afca135/scratchpad'
SP = f'{S}/posefix'
KIT = f'{S}/kit/v2d_submission_kit'
V6 = f'{S}/gmg/runs/20261031-b4ext6-90c8cce'
sys.path.insert(0, KIT)
from v2dlb.mesh_budget import budget_mesh  # noqa: E402

GRID_H = 0.0015          # SDF grid spacing, m
GRID_MARGIN = 0.009      # grid margin around the mesh bounds, m
DENSE_SPACING = 0.0005   # dense surface samples for the unsigned distance, m (error <= ~0.3 mm)
SAMPLE_SPACING = 0.002   # surface samples used as penetration probes, m
MAX_PROBES = 12000


def load_mesh(name, mesh_dir=f'{SP}/mesh9a'):
    v, f = budget_mesh(f'{mesh_dir}/{name}.glb', 4096, 4096)
    return np.asarray(v, np.float64), np.asarray(f, np.int64)


def area_samples(v, f, spacing, seed, cap=None):
    tri = v[f]
    a = 0.5 * np.linalg.norm(np.cross(tri[:, 1] - tri[:, 0], tri[:, 2] - tri[:, 0]), axis=1)
    n = int(np.ceil(a.sum() / spacing ** 2))
    if cap:
        n = min(n, cap)
    rng = np.random.default_rng(seed)
    idx = rng.choice(len(f), n, p=a / a.sum())
    u = rng.random((n, 2)); m = u.sum(1) > 1; u[m] = 1 - u[m]
    T = tri[idx]
    return T[:, 0] + u[:, :1] * (T[:, 1] - T[:, 0]) + u[:, 1:] * (T[:, 2] - T[:, 0])


def _winding_axis(v, f, lo, h, shape, ax):
    """Signed-crossing winding number at every grid node along +axis `ax` (one ray per grid column)."""
    o = [i for i in range(3) if i != ax]
    tri = v[f]
    n = np.cross(tri[:, 1] - tri[:, 0], tri[:, 2] - tri[:, 0])
    P = (tri[:, :, o] - lo[o]) / h                                   # column coords (float), [F,3,2]
    imin = np.ceil(P.min(1) - 1e-9).astype(int); imax = np.floor(P.max(1) + 1e-9).astype(int)
    imin = np.maximum(imin, 0); imax = np.minimum(imax, np.array(shape)[o] - 1)
    D = np.zeros([shape[o[0]], shape[o[1]], shape[ax] + 1], np.float32)
    cnt = np.maximum(imax - imin + 1, 0)
    ok = (cnt > 0).all(1) & (np.abs(n[:, ax]) > 1e-15)
    for t in np.nonzero(ok)[0]:
        ii, jj = np.meshgrid(np.arange(imin[t, 0], imax[t, 0] + 1), np.arange(imin[t, 1], imax[t, 1] + 1), indexing='ij')
        q = np.stack([ii.ravel(), jj.ravel()], 1).astype(np.float64)
        a, b, c = P[t]
        d = (b[1] - c[1]) * (a[0] - c[0]) + (c[0] - b[0]) * (a[1] - c[1])
        if abs(d) < 1e-18:
            continue
        l1 = ((b[1] - c[1]) * (q[:, 0] - c[0]) + (c[0] - b[0]) * (q[:, 1] - c[1])) / d
        l2 = ((c[1] - a[1]) * (q[:, 0] - c[0]) + (a[0] - c[0]) * (q[:, 1] - c[1])) / d
        l3 = 1 - l1 - l2
        m = (l1 >= 0) & (l2 >= 0) & (l3 >= 0)
        if not m.any():
            continue
        z = l1[m] * tri[t, 0, ax] + l2[m] * tri[t, 1, ax] + l3[m] * tri[t, 2, ax]
        k0 = np.clip(np.ceil((z - lo[ax]) / h - 1e-9).astype(int), 0, shape[ax])
        np.add.at(D, (q[m, 0].astype(int), q[m, 1].astype(int), k0), -np.sign(n[t, ax]))
    Wc = np.cumsum(D, axis=2)[:, :, :shape[ax]]                     # [o0, o1, ax]
    return {2: Wc, 0: np.transpose(Wc, (2, 0, 1)), 1: np.transpose(Wc, (0, 2, 1))}[ax]


class SDF:
    """Signed distance grid of one mesh in its own frame: negative inside (|median winding over 3 axes| >= 0.5)."""

    def __init__(self, name, v, f, cache=f'{SP}/sdf'):
        self.name, self.v, self.f = name, v, f
        os.makedirs(cache, exist_ok=True)
        p = f'{cache}/{name}.npz'
        lo = v.min(0) - GRID_MARGIN
        shape = tuple(int(x) for x in np.ceil((v.max(0) + GRID_MARGIN - lo) / GRID_H) + 1)
        if os.path.exists(p):
            Z = np.load(p)
            self.lo, self.sd, self.inside = Z['lo'], Z['sd'], Z['inside']
        else:
            g = [lo[i] + GRID_H * np.arange(shape[i]) for i in range(3)]
            X = np.stack(np.meshgrid(*g, indexing='ij'), -1).reshape(-1, 3)
            # two-tier unsigned distance: coarse samples (3 mm) everywhere, dense samples (0.5 mm) where coarse < 8 mm
            coarse = np.vstack([area_samples(v, f, 0.003, 13), v])
            dist = cKDTree(coarse).query(X, workers=2)[0]
            near = dist < 0.008
            dense = np.vstack([area_samples(v, f, DENSE_SPACING, 11), v])
            dn = cKDTree(dense).query(X[near], workers=2, distance_upper_bound=0.0095)[0]
            dist[near] = np.minimum(dist[near], dn)
            dist = dist.reshape(shape).astype(np.float32)
            w = np.median(np.stack([_winding_axis(v, f, lo, GRID_H, shape, ax) for ax in range(3)]), 0)
            inside = np.abs(w) >= 0.5
            sd = np.where(inside, -dist, dist).astype(np.float32)
            self.lo, self.sd, self.inside = lo, sd, inside
            np.savez_compressed(p, lo=lo, sd=sd, inside=inside)
        self.shape = self.sd.shape
        self.g = np.stack(np.gradient(self.sd, GRID_H), 0).astype(np.float32)
        self.probes = area_samples(v, f, SAMPLE_SPACING, 7, MAX_PROBES)
        self.probes = np.vstack([self.probes, v])
        self.surf_tree = cKDTree(np.vstack([area_samples(v, f, 0.001, 5), v]))
        self.volume_cm3 = float(self.inside.sum()) * GRID_H ** 3 * 1e6
        self.inside_nodes = (np.argwhere(self.inside) * GRID_H + self.lo)
        self.vol_centroid = self.inside_nodes.mean(0)

    def query(self, X, grad=False):
        """sdf (m) at local points X [N,3]; outside the grid: +1 (far outside). With grad: unit gradient too."""
        c = ((X - self.lo) / GRID_H).T
        inb = np.all((c >= 0) & (c <= (np.array(self.shape)[:, None] - 1)), 0)
        s = np.ones(len(X))
        if inb.any():
            s[inb] = map_coordinates(self.sd, c[:, inb], order=1, mode='nearest')
        if not grad:
            return s
        G = np.zeros((len(X), 3))
        if inb.any():
            for i in range(3):
                G[inb, i] = map_coordinates(self.g[i], c[:, inb], order=1, mode='nearest')
        nr = np.linalg.norm(G, axis=1, keepdims=True)
        G = np.where(nr > 1e-9, G / np.maximum(nr, 1e-9), 0)
        return s, G

    def surf_dist(self, X):
        return cKDTree.query(self.surf_tree, X)[0]


def tf(T, X):
    return X @ T[:3, :3].T + T[:3, 3]


def inv(T):
    Ti = np.eye(4); Ti[:3, :3] = T[:3, :3].T; Ti[:3, 3] = -T[:3, :3].T @ T[:3, 3]
    return Ti


def load_episode(e):
    P = np.load(f'{SP}/tracks/ep{e}/poses_world_vo.npz') if os.path.exists(f'{SP}/tracks/ep{e}/poses_world_vo.npz') \
        else None
    return P


def table_plane(e):
    E = json.load(open(f'{V6}/bundle/public/ep{e}/episode.json'))
    n = np.asarray(E['table']['n'], np.float64); d = float(E['table']['d'])
    return n, d


def hands(e):
    H = np.load(f'{V6}/hands/public/ep{e}/hands.npz')
    out = []
    for t in range(int(H['T'])):
        J = []
        for side in ('left', 'right'):
            if H[f'valid_{side}'][t]:
                j = np.asarray(H[f'joints_{side}'][t], np.float64)
                J.append(j[np.isfinite(j).all(1)])
        out.append(np.vstack(J) if J else np.zeros((0, 3)))
    return out
