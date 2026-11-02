"""Diagnostic (public scans as stand-ins for the hidden ones): for every (eval episode, slot) whose object has a public
scan, the rotation of the kit's _register_object_body at the kit seed 1_000_003*ep + 101*slot, for each pack's payload.
'tilt' = angle between the registered body z axis and the scan z axis (for axially symmetric cups the full angle is not a
pose error). Usage: flipall.py KIT SCANROOT LABEL=PACK ..."""
import sys, os, numpy as np, pandas as pd, trimesh, json
sys.path.insert(0, sys.argv[1])
from v2dlb import track3_pose as tp
from v2dlb.mesh_budget import budget_mesh
REF_MODE = os.environ.get("REF_MODE", "raw")   # raw scan or budget_mesh(scan, 4096, 4096): the hidden reference's processing is unknown
kit, scanroot = sys.argv[1], sys.argv[2]
packs = dict(a.split('=', 1) for a in sys.argv[3:])
eps = json.load(open(f'{kit}/data/track_3_evaluation_objects.json'))['episodes']
def ang(R): return float(np.degrees(np.arccos(np.clip((np.trace(R) - 1) / 2, -1, 1))))
def tilt(R): return float(np.degrees(np.arccos(np.clip(R[2, 2], -1, 1))))
cache = {}
def scan(name):
    if name not in cache:
        f = f'{scanroot}/{name}/{name}_visual.glb'
        f = f if os.path.isfile(f) else f'{scanroot}/{name}/{name}.glb'
        if REF_MODE == 'budget':
            v, fc = budget_mesh(f, 4096, 4096); cache[name] = (np.asarray(v, float), tp._mesh_faces(np.asarray(fc, float), len(v)))
        else:
            m = trimesh.load(f, force='mesh', process=False)
            cache[name] = (np.asarray(m.vertices, float), np.asarray(m.faces, np.int64))
    return cache[name]
frames = {k: pd.read_parquet(p, columns=['row_id', 'object_mesh_b64']).set_index('row_id')['object_mesh_b64'] for k, p in packs.items()}
out = []
for ep, names in sorted(eps.items(), key=lambda x: int(x[0])):
    for slot, name in enumerate(names):
        if not os.path.isdir(f'{scanroot}/{name}'):
            continue
        rid = f'track_3/e{int(ep):06d}/w000/f000000/o{slot}'
        seed = 1_000_003 * int(ep) + 101 * slot
        row = dict(ep=int(ep), slot=slot, name=name, ref_mode=REF_MODE)
        for k, f in frames.items():
            _, R = tp._register_object_body(tp._decode_object_mesh(f[rid]), scan(name), np.zeros(3), seed)
            row[k] = (round(ang(R), 1), round(tilt(R), 1))
        out.append(row)
        print(f"e{int(ep):02d} o{slot} {name:18s} " + ' | '.join(f'{k}: rot {v[0]:6.1f} tilt {v[1]:6.1f}' for k, v in row.items() if k in frames), flush=True)
json.dump(out, open(os.environ.get('OUT', '/dev/null'), 'w'), indent=1)
