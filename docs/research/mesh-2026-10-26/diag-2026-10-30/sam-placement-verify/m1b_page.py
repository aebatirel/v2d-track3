"""M1b [D]: which transform the page applies to the displayed scan; is the displayed SAM mesh the sim3 file."""
import json, base64, numpy as np
from vlib import *
from scipy.spatial import cKDTree
items = {it['id']: it for it in json.load(open(f'{SCR}/page/mesh_items_gen.json'))}
items.update({it['id']: it for it in json.load(open(f'{SCR}/page/mesh_items.json'))})
for it in json.load(open(f'{SCR}/page/meshes_gen.json')):
    V = np.frombuffer(base64.b64decode(it['v']), np.float32).reshape(-1, 3).astype(float)
    src = items.get(it['id'], {})
    p = src.get('path')
    if p is None: continue
    v, f = load(p)
    tv = cKDTree(sample(v, f, 40000, 5))
    msg = f"{it['id'][:45]:45s} id {np.median(tv.query(V)[0])*1e3:6.2f}"
    if 'align' in src:
        a = np.load(src['align']); R, t = a['R'], a['t']
        msg += f" | Rx+t {np.median(tv.query(V @ R.T + t)[0])*1e3:6.2f} | R^T(x-t) {np.median(tv.query((V - t) @ R)[0])*1e3:6.2f}"
    print(msg)
