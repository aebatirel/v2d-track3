import sys, glob, os, numpy as np, trimesh
sys.path.insert(0, sys.argv[1])
from v2dlb.object_mesh import _surface_moments
for p in sorted(glob.glob(sys.argv[2] + '/*/*.glb')):
    m = trimesh.load(p, force='mesh')
    c, r = _surface_moments(np.asarray(m.vertices), np.asarray(m.faces))
    # wall thickness probe: ray from surface samples inward along -normal, distance to next hit
    pts, fi = trimesh.sample.sample_surface(m, 400, seed=0)
    n = m.face_normals[fi]
    loc, ri, _ = m.ray.intersects_location(pts - n * 1e-4, -n, multiple_hits=False)
    th = np.linalg.norm(loc - pts[ri], axis=1) if len(ri) else np.array([np.nan])
    print(f"{os.path.basename(os.path.dirname(p)):18s} V={len(m.vertices):7d} F={len(m.faces):7d} ext_cm={np.round(m.extents*100,1)} "
          f"area_cm2={m.area*1e4:7.0f} watertight={m.is_watertight} bodies={m.body_count} rms_r_cm={r*100:.2f} "
          f"wall_mm p10/p50/p90={np.nanpercentile(th,10)*1e3:.1f}/{np.nanpercentile(th,50)*1e3:.1f}/{np.nanpercentile(th,90)*1e3:.1f}")
