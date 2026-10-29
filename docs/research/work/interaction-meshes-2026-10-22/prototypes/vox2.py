"""Exact point-in-mesh queries with warp (CPU). sign='winding' (watertight / closed meshes) or 'normal'
(angle-weighted pseudo-normal of the closest face: robust for open, thin-walled scans). Returns signed distance (m)."""
import numpy as np, trimesh, warp as wp
wp.config.quiet = True
wp.init()


@wp.kernel
def _sd_w(mesh: wp.uint64, pts: wp.array(dtype=wp.vec3), maxd: float, out: wp.array(dtype=float)):
    i = wp.tid(); p = pts[i]
    q = wp.mesh_query_point_sign_winding_number(mesh, p, maxd, 2.0, 0.5)
    d = maxd
    if q.result:
        d = wp.length(p - wp.mesh_eval_position(mesh, q.face, q.u, q.v)) * q.sign
    out[i] = d


@wp.kernel
def _sd_n(mesh: wp.uint64, pts: wp.array(dtype=wp.vec3), maxd: float, out: wp.array(dtype=float)):
    i = wp.tid(); p = pts[i]
    q = wp.mesh_query_point_sign_normal(mesh, p, maxd)
    d = maxd
    if q.result:
        d = wp.length(p - wp.mesh_eval_position(mesh, q.face, q.u, q.v)) * q.sign
    out[i] = d


class SD:
    def __init__(self, m, sign):
        with wp.ScopedDevice('cpu'):
            self.wm = wp.Mesh(points=wp.array(np.asarray(m.vertices, np.float32), dtype=wp.vec3),
                              indices=wp.array(np.asarray(m.faces, np.int32).ravel(), dtype=int),
                              support_winding_number=(sign == 'winding'))
        self.k = _sd_w if sign == 'winding' else _sd_n

    def __call__(self, P, maxd=0.1):
        if len(P) == 0:
            return np.zeros(0, np.float32)
        with wp.ScopedDevice('cpu'):
            out = wp.zeros(len(P), dtype=float)
            wp.launch(self.k, dim=len(P), inputs=[self.wm.id, wp.array(np.ascontiguousarray(P, np.float32), dtype=wp.vec3), maxd, out])
            return out.numpy()


def solid_samples(m, sd, pitch, pad=2):
    lo = m.bounds[0] - pad * pitch; hi = m.bounds[1] + pad * pitch
    n = np.ceil((hi - lo) / pitch).astype(int) + 1
    G = np.stack(np.meshgrid(*[lo[k] + pitch * np.arange(n[k]) for k in range(3)], indexing='ij'), -1).reshape(-1, 3)
    d = sd(G)
    return G[d < 0], -d[d < 0], dict(origin=lo, shape=n)
