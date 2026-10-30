"""Export meshes for the viewer page: kit budget_mesh (what Kaggle receives), padding dropped, base64 arrays."""
import sys, json, base64, numpy as np, trimesh
sys.path.insert(0, sys.argv[1])
from v2dlb.mesh_budget import budget_mesh
items = json.load(open(sys.argv[2])); out = []
for it in items:
    v, f = budget_mesh(it['path'], 4096, 4096)
    T = np.asarray(v[f], float); area = 0.5 * np.linalg.norm(np.cross(T[:, 1] - T[:, 0], T[:, 2] - T[:, 0]), axis=1)
    f = f[area > 0]; used = np.unique(f); remap = -np.ones(len(v), int); remap[used] = np.arange(len(used))
    v = np.asarray(v, float)[used]; f = remap[f]
    if it.get('align'):                       # [D] scan -> our track frame: x_our = (x_scan - t) @ R
        A = np.load(it['align']); v = (v - A['t']) @ A['R']
    rec = dict(id=it['id'], label=it['label'], group=it['group'], note=it.get('note', ''), color=it.get('color', ''),
               nv=int(len(v)), nf=int(len(f)), ext_cm=np.round(np.ptp(v, 0) * 100, 1).tolist(),
               v=base64.b64encode(v.astype(np.float32).tobytes()).decode(), f=base64.b64encode(f.astype(np.uint32).tobytes()).decode())
    rec.update({k: it[k] for k in ('cdo', 'add', 'flips') if k in it})
    out.append(rec); print(it['id'], len(v), len(f), rec['ext_cm'])
json.dump(out, open(sys.argv[3], 'w'))
