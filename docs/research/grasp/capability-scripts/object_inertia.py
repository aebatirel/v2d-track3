"""Object mass / COM / inertia exactly as pipeline/make_assets.py builds them (placeholder 0.3 kg, thin-shell estimate),
plus extents, principal moments and the VOC-relevant min/mean inertia ratio. Usage: python -I object_inertia.py REPO"""
import os, sys
import numpy as np
import trimesh

repo = sys.argv[1]
sys.path.insert(0, os.path.join(repo, 'pipeline'))
from make_assets import surface_inertia  # noqa: E402  (repo code, trusted)

lib = os.path.join(repo, 'meshes/library_v3')
for f in sorted(os.listdir(lib)):
    if not f.endswith('.glb'):
        continue
    m = trimesh.load(os.path.join(lib, f), force='mesh')
    m = trimesh.Trimesh(np.asarray(m.vertices), np.asarray(m.faces), process=True)
    c, I = surface_inertia(m, 0.3)
    ev = np.sort(np.linalg.eigvalsh(I))
    ext = np.sort(m.extents)[::-1] * 100
    print(f"{f[:-4]:18s} extents_cm {np.round(ext, 1).tolist()} watertight {m.is_watertight!s:5s} "
          f"I_principal_e-4 {np.round(ev * 1e4, 2).tolist()} min/mean {ev[0] / ev.mean():.3f} com_cm {np.round(c * 100, 1).tolist()}")
