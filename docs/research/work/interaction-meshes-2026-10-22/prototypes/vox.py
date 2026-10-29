"""Solid voxel occupancy + signed distance of a mesh in its own body frame (warp CPU, winding-number sign).
voxelize(path, pitch) -> dict(origin, pitch, occ (bool 3-D), sdf (float32 3-D, m, <0 inside), surf (N,3) samples,
vol_cm3). Results cached as npz next to this file (cache/<tag>.npz)."""
import os, hashlib, numpy as np, trimesh, warp as wp

wp.config.quiet = True
wp.init()
HERE = os.path.dirname(os.path.abspath(__file__))


@wp.kernel
def _sdf(mesh: wp.uint64, pts: wp.array(dtype=wp.vec3), out: wp.array(dtype=float)):
    i = wp.tid()
    p = pts[i]
    q = wp.mesh_query_point_sign_winding_number(mesh, p, 10.0, 2.0, 0.5)
    d = 10.0
    if q.result:
        c = wp.mesh_eval_position(mesh, q.face, q.u, q.v)
        d = wp.length(p - c) * q.sign
    out[i] = d


def mesh_sdf(m, P):
    with wp.ScopedDevice('cpu'):
        wm = wp.Mesh(points=wp.array(np.asarray(m.vertices, np.float32), dtype=wp.vec3),
                     indices=wp.array(np.asarray(m.faces, np.int32).ravel(), dtype=int), support_winding_number=True)
        out = wp.zeros(len(P), dtype=float)
        wp.launch(_sdf, dim=len(P), inputs=[wm.id, wp.array(np.asarray(P, np.float32), dtype=wp.vec3), out])
        return out.numpy()


def voxelize(path, pitch=0.0025, n_surf=40000, pad=2):
    key = hashlib.md5(f'{os.path.abspath(path)}:{os.path.getmtime(path)}:{pitch}:{n_surf}'.encode()).hexdigest()[:12]
    cdir = os.path.join(HERE, 'cache'); os.makedirs(cdir, exist_ok=True)
    cp = os.path.join(cdir, f'{os.path.basename(path).split(".")[0]}_{key}.npz')
    if os.path.exists(cp):
        z = np.load(cp)
        return {k: z[k] for k in z.files}
    m = trimesh.load(path, force='mesh')
    lo = m.bounds[0] - pad * pitch; hi = m.bounds[1] + pad * pitch
    n = np.ceil((hi - lo) / pitch).astype(int) + 1
    ax = [lo[k] + pitch * np.arange(n[k]) for k in range(3)]
    G = np.stack(np.meshgrid(*ax, indexing='ij'), -1).reshape(-1, 3)
    sdf = mesh_sdf(m, G).reshape(n).astype(np.float32)
    occ = sdf < 0
    surf, _ = trimesh.sample.sample_surface_even(m, n_surf, seed=0) if hasattr(trimesh.sample, 'sample_surface_even') else trimesh.sample.sample_surface(m, n_surf, seed=0)
    res = dict(origin=lo.astype(np.float64), pitch=np.float64(pitch), occ=occ, sdf=sdf, surf=np.asarray(surf, np.float64),
               vol_cm3=np.float64(occ.sum() * pitch ** 3 * 1e6), mesh_vol_cm3=np.float64(m.volume * 1e6 if m.is_watertight else np.nan),
               bounds=m.bounds.astype(np.float64), area_cm2=np.float64(m.area * 1e4))
    np.savez_compressed(cp, **res)
    return res


def lookup(V, P, field='occ', fill=None):
    """Values of grid V[field] at points P (N,3, body frame); nearest voxel; outside the grid -> fill."""
    g = V[field]; idx = np.rint((P - V['origin']) / V['pitch']).astype(np.int64)
    ok = np.all((idx >= 0) & (idx < np.array(g.shape)), 1)
    out = np.full(len(P), (False if g.dtype == bool else np.float32(1.0)) if fill is None else fill, dtype=g.dtype)
    out[ok] = g[idx[ok, 0], idx[ok, 1], idx[ok, 2]]
    return out, idx, ok
