"""CD-O proxy (DIAGNOSTIC ONLY, public scans as stand-in for the hidden scans): kit metric_code/track_3/CD-O.py
_object_chamfer_cm on (scan, our mesh), 3 seeds. Usage: cdo_proxy.py SCANROOT name=path ..."""
import sys, importlib.util, numpy as np, trimesh
K = '/tmp/claude-0/-home-user-v2d-track3/8c892c5e-fd7c-57aa-abef-68d2af098e4f/scratchpad/loc/kit/v2d_submission_kit/metric_code/track_3/CD-O.py'
spec = importlib.util.spec_from_file_location('cdo', K); cdo = importlib.util.module_from_spec(spec); spec.loader.exec_module(cdo)
root = sys.argv[1]
def load(p):
    m = trimesh.load(p, force='mesh', process=False)
    return np.asarray(m.vertices, float), np.asarray(m.faces, int)
for arg in sys.argv[2:]:
    name, path = arg.split('=', 1)
    import os; rp = f'{root}/{name}/{name}_visual.glb'; rp = rp if os.path.exists(rp) else f'{root}/{name}/{name}.glb'; ref = load(rp); cand = load(path)
    v = [cdo._object_chamfer_cm(ref, cand, s) for s in (11, 22, 33)]
    print(f'{name:18s} {path.split("/scratchpad/")[-1] if "/scratchpad/" in path else path.split("/v2d-track3/")[-1]:70s} CD-O {np.mean(v):.3f} cm  faces {len(cand[1])}', flush=True)
