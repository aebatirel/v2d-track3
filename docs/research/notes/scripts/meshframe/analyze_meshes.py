"""Mesh-frame convention analysis for V2D Track 3 public scans.

For every public GLB, compute candidate origins (surface-area centroid, volume
centroid, vertex mean, bbox centre, base centre) and candidate axes (surface
second-moment PCA, volume inertia PCA, vertex PCA), and report how far the file
frame is from each candidate. Also third-moment signs and URDF consistency.
Outputs JSON to meshframe/mesh_stats.json.
"""
import json, glob, os, re
import numpy as np
import trimesh

ROOT = os.path.join(os.path.dirname(__file__), "..", "t3", "public")
OUT = os.path.join(os.path.dirname(__file__), "mesh_stats.json")


def surface_moments(tris):
    a, b, c = tris[:, 0], tris[:, 1], tris[:, 2]
    area = 0.5 * np.linalg.norm(np.cross(b - a, c - a), axis=1)
    A = area.sum()
    s = a + b + c
    centroid = (area[:, None] * s / 3.0).sum(0) / A
    # E[x x^T] over triangle = (sum v v^T + s s^T)/12
    M2 = (np.einsum("n,ni,nj->ij", area, a, a) + np.einsum("n,ni,nj->ij", area, b, b)
          + np.einsum("n,ni,nj->ij", area, c, c) + np.einsum("n,ni,nj->ij", area, s, s)) / 12.0 / A
    cov = M2 - np.outer(centroid, centroid)
    return A, centroid, cov, M2


def third_moment_sampled(mesh, axes, origin, n=400000, seed=0):
    pts, _ = trimesh.sample.sample_surface(mesh, n, seed=seed)
    q = (pts - origin) @ axes.T
    return (q ** 3).mean(0) / (q.var(0) ** 1.5)


def angle_deg(u, v):
    return float(np.degrees(np.arccos(np.clip(abs(np.dot(u, v)) / np.linalg.norm(u) / np.linalg.norm(v), 0, 1))))


def parse_urdf(name):
    p = os.path.join(ROOT, "urdf", f"{name}_rigid.urdf")
    if not os.path.exists(p):
        return None
    t = open(p).read()
    inert = re.search(r"<inertial>.*?</inertial>", t, re.S).group(0)
    xyz = [float(v) for v in re.search(r'origin xyz="([^"]+)"', inert).group(1).split()]
    I = {k: float(re.search(k + r'="([^"]+)"', inert).group(1)) for k in ["ixx", "ixy", "ixz", "iyy", "iyz", "izz"]}
    mass = float(re.search(r'mass value="([^"]+)"', inert).group(1))
    coll = re.search(r"<collision>.*?filename=\"([^\"]+)\"", t, re.S).group(1)
    return dict(com=xyz, inertia=I, mass=mass, collision=coll)


def analyse(path):
    name = os.path.basename(path)[:-4]
    mesh = trimesh.load(path, force="mesh", process=False)
    V = np.asarray(mesh.vertices, float)
    F = np.asarray(mesh.faces)
    tris = V[F]
    A, c_surf, cov_surf, M2 = surface_moments(tris)
    # Trimesh-native quantities
    c_tm = np.asarray(mesh.centroid)
    try:
        mp = mesh.mass_properties
        c_vol = np.asarray(mp["center_mass"]) if isinstance(mp, dict) else np.asarray(mp.center_mass)
        I_vol = np.asarray(mp["inertia"]) if isinstance(mp, dict) else np.asarray(mp.inertia)
        vol = float(mp["volume"]) if isinstance(mp, dict) else float(mp.volume)
    except Exception as e:  # pragma: no cover
        c_vol, I_vol, vol = np.full(3, np.nan), np.full((3, 3), np.nan), np.nan
    # merged-vertex copy for watertightness
    mm = trimesh.load(path, force="mesh", process=True)
    watertight = bool(mm.is_watertight)
    vmean = V.mean(0)
    uniqV = np.unique(np.round(V, 9), axis=0)
    vmean_u = uniqV.mean(0)
    bbox_c = 0.5 * (V.min(0) + V.max(0))
    ext = V.max(0) - V.min(0)

    # PCA of candidate second moments
    res = dict(name=name, n_vertices=int(len(V)), n_faces=int(len(F)), area_m2=float(A), volume_m3=vol,
               watertight_after_merge=watertight, extent=ext.tolist(), bbox_min=V.min(0).tolist(), bbox_max=V.max(0).tolist())
    res["origins_mm"] = {
        "surface_centroid": (c_surf * 1000).tolist(),
        "trimesh_centroid": (c_tm * 1000).tolist(),
        "volume_centroid": (c_vol * 1000).tolist(),
        "vertex_mean_raw": (vmean * 1000).tolist(),
        "vertex_mean_unique": (vmean_u * 1000).tolist(),
        "bbox_centre": (bbox_c * 1000).tolist(),
    }
    # covariance candidates
    covs = {
        "surface_cov_about_surface_centroid": cov_surf,
        "surface_M2_about_origin": M2,
        "vertex_cov": np.cov((V - vmean).T),
        "volume_inertia(trimesh)": I_vol,
    }
    axes_out = {}
    for k, C in covs.items():
        if not np.all(np.isfinite(C)):
            continue
        w, vec = np.linalg.eigh(C)
        offdiag = float(np.abs(C - np.diag(np.diag(C))).max() / np.abs(np.diag(C)).max())
        # angle of each file axis to the nearest eigenvector
        ang = [max(0.0, min(angle_deg(np.eye(3)[i], vec[:, j]) for j in range(3))) for i in range(3)]
        axes_out[k] = dict(eigvals=w.tolist(), diag=np.diag(C).tolist(), rel_offdiag=offdiag,
                           file_axis_to_nearest_eig_deg=ang)
    res["axes"] = axes_out
    # surface inertia (shell) about surface centroid; ordering check
    Is = np.trace(cov_surf) * np.eye(3) - cov_surf
    res["surface_inertia_diag_per_kg"] = np.diag(Is).tolist()
    res["variance_order_ascending_xyz"] = bool(cov_surf[0, 0] < cov_surf[1, 1] < cov_surf[2, 2])
    sd = np.sqrt(np.diag(cov_surf))
    res["surface_std_mm"] = (sd * 1000).tolist()
    w = np.linalg.eigvalsh(cov_surf)
    res["eig_ratio_mid_over_small"] = float(w[1] / w[0])
    res["eig_ratio_large_over_mid"] = float(w[2] / w[1])
    # third moments (skewness) along file axes about surface centroid (exact via sampling)
    sk = third_moment_sampled(mesh, np.eye(3), c_surf)
    sk2 = third_moment_sampled(mesh, np.eye(3), c_surf, seed=1)
    res["surface_skewness_xyz"] = sk.tolist()
    res["surface_skewness_xyz_seed1"] = sk2.tolist()
    # base: points within 3mm of min along each axis
    base = {}
    for i, ax in enumerate("xyz"):
        lo = V[:, i] < V[:, i].min() + 0.003
        hi = V[:, i] > V[:, i].max() - 0.003
        base[ax] = dict(min=float(V[:, i].min()), max=float(V[:, i].max()),
                        frac_near_min=float(lo.mean()), frac_near_max=float(hi.mean()))
    res["axis_extremes"] = base
    # URDF comparison
    u = parse_urdf(name.replace("_visual", "")) if not name.endswith("_collision") else None
    if u:
        res["urdf"] = u
        # recompute uniform-surface inertia about origin with mass from URDF
        m = u["mass"]
        Iorig = m * (np.trace(M2) * np.eye(3) - M2)
        Icom = m * (np.trace(cov_surf) * np.eye(3) - cov_surf)
        res["urdf_check_this_mesh"] = dict(I_about_origin=Iorig.tolist(), I_about_centroid=Icom.tolist(),
                                           com_mm=(c_surf * 1000).tolist())
    return res


def main():
    out = []
    for p in sorted(glob.glob(os.path.join(ROOT, "mesh", "*", "*.glb"))):
        r = analyse(p)
        out.append(r)
        o = r["origins_mm"]
        print(f"== {r['name']}  V={r['n_vertices']} F={r['n_faces']} watertight={r['watertight_after_merge']} ext_mm={np.round(np.array(r['extent'])*1000,1)}")
        for k, v in o.items():
            print(f"   origin {k:22s} {np.round(v, 3)}  |{np.linalg.norm(v):.3f}| mm")
        for k, v in r["axes"].items():
            print(f"   axes {k:38s} relOff={v['rel_offdiag']:.2e} ang={np.round(v['file_axis_to_nearest_eig_deg'],3)} diag={np.round(v['diag'],8)}")
        print(f"   var ascending x<y<z: {r['variance_order_ascending_xyz']}  std_mm={np.round(r['surface_std_mm'],2)}  eig ratios mid/small={r['eig_ratio_mid_over_small']:.3f} large/mid={r['eig_ratio_large_over_mid']:.3f}")
        print(f"   skew xyz {np.round(r['surface_skewness_xyz'],4)}  seed1 {np.round(r['surface_skewness_xyz_seed1'],4)}")
        if "urdf" in r:
            u = r["urdf"]; I = u["inertia"]
            print(f"   URDF com={u['com']} I=({I['ixx']:.6g},{I['iyy']:.6g},{I['izz']:.6g}; off {I['ixy']:.2g},{I['ixz']:.2g},{I['iyz']:.2g}) coll={u['collision']}")
            c = np.array(r["urdf_check_this_mesh"]["I_about_centroid"])
            print(f"   this-mesh surface I@centroid diag=({c[0,0]:.6g},{c[1,1]:.6g},{c[2,2]:.6g}) off=({c[0,1]:.2g},{c[0,2]:.2g},{c[1,2]:.2g})")
    json.dump(out, open(OUT, "w"), indent=1)


if __name__ == "__main__":
    main()
