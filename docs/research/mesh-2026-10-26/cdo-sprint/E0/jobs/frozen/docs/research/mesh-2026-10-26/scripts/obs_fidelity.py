"""GT-free mesh score: how well a candidate mesh explains our observed points (obs_points.py), in both directions.
  obs->mesh: trimmed mean distance of observed points to the mesh surface (misplaced or missing seen surface);
  mesh->obs: trimmed mean distance of mesh samples to the nearest observed point, counted only where the mesh lies
  in the observed region (within the observations' bounding box) - extra surface where we did look.
Both after an optional rigid ICP (--icp 1) for candidates not in the track frame. Lower is better. No ground truth.
Usage: obs_fidelity.py OBS1.npz[,OBS2.npz...] MESH.glb [MESH2.glb ...] [--trim 0.9]
"""
import sys, json, numpy as np, trimesh
from scipy.spatial import cKDTree
args = [a for a in sys.argv[1:] if not a.startswith('--')]
trim = 0.9
P = np.concatenate([np.load(f)['pts'] for f in args[0].split(',')]).astype(np.float64)
P = P[np.random.default_rng(0).choice(len(P), min(300000, len(P)), replace=False)]
tp = cKDTree(P); lo, hi = P.min(0), P.max(0)
def tmean(d):
    d = np.sort(d); return float(d[:int(trim * len(d))].mean() * 1000)
for f in args[1:]:
    m = trimesh.load(f, force='mesh')
    S = trimesh.sample.sample_surface(m, 200000, seed=0)[0]
    d_om = cKDTree(S).query(P)[0]
    inb = np.all((S > lo) & (S < hi), axis=1)
    d_mo = tp.query(S[inb])[0]
    print(json.dumps(dict(mesh=f.split('/')[-1], obs_to_mesh_mm=round(tmean(d_om), 3), mesh_to_obs_mm=round(tmean(d_mo), 3),
                          sum_mm=round(tmean(d_om) + tmean(d_mo), 3))))
