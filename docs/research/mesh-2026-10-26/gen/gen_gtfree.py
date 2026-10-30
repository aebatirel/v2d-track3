"""GT-free diagnostics of the batch-2 meshes that live in OUR object frame (Pixal3D-MV outputs, Sim(3)-fitted
copies, library_v3 for reference): distances between the mesh surface and our observed points (obs_points.py,
subsampled), medians and p90 in mm. Uses no scan. Usage: gen_gtfree.py OBS_DIR OUT.jsonl label=ep_obj=mesh ...
"""
import json, sys
import numpy as np
import trimesh
from scipy.spatial import cKDTree

obs_dir, out = sys.argv[1:3]
with open(out, 'a') as fh:
    for item in sys.argv[3:]:
        label, eo, path = item.split('=', 2)
        O = np.load(f'{obs_dir}/{eo}.npz')['pts'].astype(np.float64)
        m = trimesh.load(path, force='mesh', process=False)
        S = trimesh.sample.sample_surface(m, 300000, seed=0)[0]
        do = cKDTree(S).query(O)[0]; dm = cKDTree(O).query(S)[0]
        rec = dict(label=label, ep_obj=eo, path=path, obs_to_mesh_med_mm=round(float(np.median(do)) * 1e3, 2),
                   obs_to_mesh_p90_mm=round(float(np.quantile(do, 0.9)) * 1e3, 2),
                   mesh_to_obs_med_mm=round(float(np.median(dm)) * 1e3, 2),
                   mesh_to_obs_p90_mm=round(float(np.quantile(dm, 0.9)) * 1e3, 2),
                   extent_mm=(np.ptp(np.asarray(m.vertices), 0) * 1e3).round(1).tolist())
        print(json.dumps(rec), flush=True); fh.write(json.dumps(rec) + '\n')
