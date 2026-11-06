"""C0b pick exclusions (PREREG C0b section 5.1), GT-free: the raw mesh is watertight (trimesh, process=True), and the
kit's budget_mesh(path, 4096, 4096) (v2dlb/mesh_budget.py, what Kaggle receives) does not raise and leaves at most 4096
faces and 4096 vertices. Reads only the candidate mesh and the kit's budget code.
Usage: python -I c0b_check.py KIT_DIR MESH.glb OUT.json
"""
import hashlib, json, sys, traceback

import numpy as np
import trimesh

KIT, MESH, OUT = sys.argv[1:4]
sys.path.insert(0, KIT)
from v2dlb.mesh_budget import budget_mesh  # noqa: E402

m = trimesh.load(MESH, force='mesh', process=False)
raw = trimesh.Trimesh(m.vertices, m.faces, process=True)
r = dict(mesh=MESH, sha256=hashlib.sha256(open(MESH, 'rb').read()).hexdigest(),
         sha1_16=hashlib.sha1(open(MESH, 'rb').read()).hexdigest()[:16],
         faces_raw=int(len(m.faces)), vertices_raw=int(len(m.vertices)), watertight_raw=bool(raw.is_watertight),
         bodies_raw=int(len(raw.split(only_watertight=False))))
try:
    v, f = budget_mesh(MESH, 4096, 4096)
    keep = ~((f[:, 0] == f[:, 1]) | (f[:, 1] == f[:, 2]) | (f[:, 0] == f[:, 2]))
    b = trimesh.Trimesh(v, f[keep], process=True)
    b.remove_unreferenced_vertices()
    r['budget'] = dict(ok=True, faces=int(keep.sum()), vertices=int(len(b.vertices)), watertight=bool(b.is_watertight))
    r['budget_ok'] = bool(keep.sum() <= 4096 and len(b.vertices) <= 4096)
except Exception as ex:  # noqa: BLE001
    r['budget'] = dict(ok=False, error=f'{type(ex).__name__}: {ex}', tb=traceback.format_exc()[-800:])
    r['budget_ok'] = False
r['eligible'] = bool(r['watertight_raw'] and r['budget_ok'])
r['exclusion'] = None if r['eligible'] else ('not watertight (raw)' if not r['watertight_raw'] else 'kit budget')
json.dump(r, open(OUT, 'w'), indent=1)
print(json.dumps(r))
