"""G0 placement diagnostic (dev, GT-free, outside the guard; reads only our own files): for each SAM 3D run,
(1) owned points of the target moved into camera A at frame k vs the input pointmap points (checks the input chain),
(2) the posed mesh (camA_T_mesh) vs the pointmap points and vs the owned points in camera A (both directions)."""
import json, sys, os, glob
import numpy as np, trimesh
from scipy.spatial import cKDTree
rep, bun = sys.argv[1], sys.argv[2]
out = {}
for jf in sorted(glob.glob(os.path.join(rep, 'box', 'sam3d', '*.json'))):
    r = json.load(open(jf))
    inp = json.load(open(os.path.join(rep, 'inputs', r['tag'] + '.json')))
    P = np.load(os.path.join(rep, 'inputs', inp['files']['pointmap']))['points']
    Q = P[np.isfinite(P).all(-1)].astype(np.float64)
    z = np.load(os.path.join(bun, f"{r['obj']}.npz"))
    O = np.asarray(z['pts'], np.float64)[np.asarray(z['own']) == 0]
    T = np.array(inp['camA_T_obj']); A = np.array(r['camA_T_mesh'])
    Oc = O @ T[:3, :3].T + T[:3, 3]
    m = trimesh.load(os.path.join(rep, 'box', 'sam3d', r['path']), force='mesh', process=False)
    Vc = np.asarray(m.vertices) @ A[:3, :3].T + A[:3, 3]
    rng = np.random.default_rng(0)
    sub = lambda X, n=30000: X[rng.choice(len(X), min(n, len(X)), replace=False)]
    Qs, Os, Vs = sub(Q), sub(Oc), sub(Vc)
    d = lambda X, Y: np.percentile(cKDTree(Y).query(X)[0], [50, 90]) * 1e3
    rec = dict(pointmap_to_owned_mm=d(Qs, Oc).round(1).tolist(), pointmap_to_mesh_mm=d(Qs, Vc).round(1).tolist(),
               mesh_to_owned_mm=d(Vs, Oc).round(1).tolist(), owned_to_mesh_mm=d(Os, Vc).round(1).tolist(),
               centroid_pointmap=Q.mean(0).round(4).tolist(), centroid_mesh_cam=Vc.mean(0).round(4).tolist(),
               extent_pointmap=(np.percentile(Q, 99, 0) - np.percentile(Q, 1, 0)).round(3).tolist(),
               extent_mesh=(np.percentile(Vc, 99, 0) - np.percentile(Vc, 1, 0)).round(3).tolist())
    out[f"{r['tag']}_s{r['seed']}"] = rec
    print(r['tag'], r['seed'], json.dumps(rec), flush=True)
json.dump(out, open(sys.argv[3], 'w'), indent=1)
