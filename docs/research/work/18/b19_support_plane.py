"""DIG 18 B19 (public GT analysis only): are GT-posed objects resting flat? For each object at rest at frame 0 (and the
last frame), transform the scan to the GT world, take its convex hull, and find the support plane = the hull facet
group whose outward normal is closest to -z (area-weighted, facets within 3 deg of the best). Report its tilt from
horizontal and the world direction it leans to (normal xy in deg). If GT object orientations carried a common error
of ~1.5 deg, the support planes of resting objects would lean consistently.
usage: python b19_support_plane.py <eps...>"""
import sys, numpy as np, trimesh
sys.path.insert(0, "/Users/aebatirel/Documents/Code/v2d-research/work/11")
import c11
HULL = {}
for ep in [int(e) for e in sys.argv[1:]]:
    e = c11.load_episode(ep)
    for j, n in enumerate(e["names"]):
        if n not in HULL: HULL[n] = trimesh.convex.convex_hull(np.asarray(c11.glb_mesh(n).vertices))
        H = HULL[n]
        for f in (0, len(e["frame"]) - 1):
            q = e["pose"][f, j]
            if not np.isfinite(q).all(): continue
            R = c11.R_of(q[3:]); N = H.face_normals @ R.T; A = H.area_faces
            V = H.vertices @ R.T + q[:3]; zmin = V[:, 2].min()
            cosd = -N[:, 2]; best = np.argmax(cosd)
            g = np.degrees(np.arccos(np.clip(N @ N[best], -1, 1))) < 3.0
            nm = (N[g] * A[g, None]).sum(0); nm /= np.linalg.norm(nm)
            tilt = np.degrees(np.arccos(np.clip(-nm[2], -1, 1))); area = A[g].sum() * 1e4
            print(f"ep {ep:2d} f{f:3d} {n:18s} z_min {zmin:.4f} support area {area:6.1f} cm2 tilt {tilt:5.2f} deg lean xy ({np.degrees(-nm[0]):+.2f}, {np.degrees(-nm[1]):+.2f})")
