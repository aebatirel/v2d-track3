"""Exact parity voxelisation of a closed triangle mesh (vertical rays through voxel-column centres), plus grid lookup."""
import numpy as np, trimesh


def load(p):
    m = trimesh.load(p, force='mesh')
    return trimesh.Trimesh(np.asarray(m.vertices, float), np.asarray(m.faces), process=True)


class Grid:
    def __init__(self, lo, pitch, occ):
        self.lo, self.pitch, self.occ = np.asarray(lo, float), pitch, occ

    def centres(self, mask=None):
        idx = np.argwhere(self.occ if mask is None else mask)
        return self.lo + (idx + 0.5) * self.pitch

    def lookup(self, P):
        ijk = np.floor((P - self.lo) / self.pitch).astype(int)
        ok = np.all((ijk >= 0) & (ijk < np.array(self.occ.shape)), 1)
        out = np.zeros(len(P), bool)
        out[ok] = self.occ[ijk[ok, 0], ijk[ok, 1], ijk[ok, 2]]
        return out


def voxelize(m, pitch=0.001, pad=0.002, lo=None, hi=None):
    V = np.asarray(m.vertices, float); F = np.asarray(m.faces)
    lo = (V.min(0) - pad) if lo is None else np.asarray(lo, float)
    hi = (V.max(0) + pad) if hi is None else np.asarray(hi, float)
    n = np.ceil((hi - lo) / pitch).astype(int)
    eps = np.array([1.234567e-7, 2.345678e-7])                     # break ties on edges / vertices
    T = V[F]                                                        # (F,3,3)
    t2 = (T[:, :, :2] - lo[:2] - eps) / pitch - 0.5                 # column-index space
    i0 = np.clip(np.ceil(t2[:, :, 0].min(1)).astype(int), 0, n[0] - 1); i1 = np.clip(np.floor(t2[:, :, 0].max(1)).astype(int), 0, n[0] - 1)
    j0 = np.clip(np.ceil(t2[:, :, 1].min(1)).astype(int), 0, n[1] - 1); j1 = np.clip(np.floor(t2[:, :, 1].max(1)).astype(int), 0, n[1] - 1)
    ni = np.maximum(i1 - i0 + 1, 0); nj = np.maximum(j1 - j0 + 1, 0); cnt = ni * nj
    tri = np.repeat(np.arange(len(F)), cnt)
    off = np.arange(cnt.sum()) - np.repeat(np.cumsum(cnt) - cnt, cnt)
    ci = i0[tri] + off // nj[tri]; cj = j0[tri] + off % nj[tri]
    px = ci.astype(float); py = cj.astype(float)
    a, b, c = t2[tri, 0], t2[tri, 1], t2[tri, 2]
    d = (b[:, 1] - c[:, 1]) * (a[:, 0] - c[:, 0]) + (c[:, 0] - b[:, 0]) * (a[:, 1] - c[:, 1])
    good = np.abs(d) > 1e-15
    with np.errstate(divide='ignore', invalid='ignore'):
        l1 = ((b[:, 1] - c[:, 1]) * (px - c[:, 0]) + (c[:, 0] - b[:, 0]) * (py - c[:, 1])) / d
        l2 = ((c[:, 1] - a[:, 1]) * (px - c[:, 0]) + (a[:, 0] - c[:, 0]) * (py - c[:, 1])) / d
    l3 = 1 - l1 - l2
    hit = good & (l1 >= 0) & (l2 >= 0) & (l3 >= 0)
    z = (l1 * T[tri, 0, 2] + l2 * T[tri, 1, 2] + l3 * T[tri, 2, 2])[hit]
    col = (ci * n[1] + cj)[hit]
    o = np.lexsort((z, col)); col, z = col[o], z[o]
    occ = np.zeros((n[0] * n[1], n[2]), bool)
    zc = lo[2] + (np.arange(n[2]) + 0.5) * pitch
    starts = np.flatnonzero(np.r_[True, col[1:] != col[:-1]])
    ends = np.r_[starts[1:], len(col)]
    for s, e in zip(starts, ends):
        zz = z[s:e]
        if len(zz) % 2:
            zz = zz[:-1]                                            # odd parity (grazing): drop the last crossing
        for k in range(0, len(zz), 2):
            k0 = np.searchsorted(zc, zz[k]); k1 = np.searchsorted(zc, zz[k + 1])
            occ[col[s], k0:k1] = True
    return Grid(lo, pitch, occ.reshape(n[0], n[1], n[2]))


def hull_eqs(vertices_list):
    from scipy.spatial import ConvexHull
    return [ConvexHull(np.asarray(v, float)).equations for v in vertices_list]


def in_hulls(eqs, P, tol=1e-9):
    out = np.zeros(len(P), bool)
    for e in eqs:
        rem = ~out
        if not rem.any():
            break
        Q = P[rem]
        out[np.flatnonzero(rem)[np.all(Q @ e[:, :3].T + e[:, 3] <= tol, 1)]] = True
    return out
