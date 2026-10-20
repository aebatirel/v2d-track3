"""Verifier (C2 premise '10/10 public Track 3 scans include markers'): geometric detection of ~14 mm marker spheres.
Area-weighted points with outward normals; candidate centre = p - r*n for r in 6.5-7.8 mm; dense centre clusters whose
points lie on a sphere (radius rms < 0.6 mm, area >= 1 cm2) = marker. Prints clusters per scan."""
import sys, numpy as np, trimesh
sys.path.insert(0, "/Users/aebatirel/Documents/Code/v2d-research/work/13-verify")
from v_geom import glb_load
from scipy.spatial import cKDTree
M = "/Users/aebatirel/Documents/Code/v2d-research/data/track_3/public/mesh"
import os
for d in sorted(os.listdir(M)):
    fs = sorted(os.listdir(f"{M}/{d}")); f = ([x for x in fs if x.endswith("_visual.glb")] or [d + ".glb"])[0]
    V, F = glb_load(f"{M}/{d}/{f}"); m = trimesh.Trimesh(V, F, process=True)
    fn = m.face_normals; fc = m.triangles_center; fa = m.area_faces
    hits = []
    for r in (0.0072,):
        C = fc - r * fn                      # inward offset (outward normals assumed); try both orientations
        for sgn in (1, -1):
            Cs = fc - sgn * r * fn; tree = cKDTree(Cs)
            dens = np.array([fa[i].sum() for i in tree.query_ball_point(Cs, 0.0015)])
            order = np.argsort(-dens); used = np.zeros(len(Cs), bool)
            for i in order[:4000]:
                if used[i] or dens[i] < 1e-4: continue
                c = Cs[i]; near = np.linalg.norm(fc - c, axis=1); sel = np.abs(near - r) < 0.0012
                A = fa[sel].sum()
                if A < 1e-4: used[tree.query_ball_point(c, 0.004)] = True; continue
                rms = np.sqrt(np.average((near[sel] - r) ** 2, weights=fa[sel]))
                hits.append((A * 1e4, c * 1000, rms * 1000, sgn)); used[tree.query_ball_point(c, 0.01)] = True
    # dedupe by centre
    out = []
    for h in sorted(hits, key=lambda h: -h[0]):
        if all(np.linalg.norm(h[1] - o[1]) > 8 for o in out): out.append(h)
    good = [h for h in out if h[0] >= 1.0 and h[2] < 0.6]
    print(f"{d:18s} sphere-like clusters (area>=1cm2, rms<0.6mm): {len(good)} :: " + "; ".join(f"{h[0]:.1f}cm2 @{np.round(h[1],0).tolist()} rms{h[2]:.2f}" for h in good[:6]), flush=True)
