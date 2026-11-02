"""Diagnostic (public scan as stand-in for the hidden one): rotation of the kit's _register_object_body for packed
eval-25 wooden-piece payloads, at the kit's seed 1_000_003*ep + 101*slot. Usage: flipchk.py KIT SCANROOT PACK_A PACK_B"""
import sys, numpy as np, pandas as pd, trimesh
sys.path.insert(0, sys.argv[1])
from v2dlb import track3_pose as tp
scanroot, packs = sys.argv[2], sys.argv[3:]
def ang(R): return float(np.degrees(np.arccos(np.clip((np.trace(R) - 1) / 2, -1, 1))))
def scan(name):
    m = trimesh.load(f'{scanroot}/{name}/{name}_visual.glb', force='mesh', process=False)
    return np.asarray(m.vertices, float), np.asarray(m.faces, np.int64)
rows = {}
for p in packs:
    d = pd.read_parquet(p, columns=['row_id', 'object_mesh_b64'])
    for slot, name in ((0, 'wooden_piece_1'), (1, 'wooden_piece_2')):
        r = d[d.row_id.str.startswith(f'track_3/e000025/w000/f000000/o{slot}')]
        rows[(p.split('/')[-3], name, slot)] = tp._decode_object_mesh(r.object_mesh_b64.iloc[0])
seeds = {f'eval25 s{slot}': (25, slot) for slot in (0, 1)}
seeds.update({f'ep{e} s{s}': (e, s) for e in (23, 24, 25) for s in (0, 1)})
for (pack, name, slot), cand in rows.items():
    ref = scan(name)
    out = []
    for label, (e, s) in seeds.items():
        _, R = tp._register_object_body(cand, ref, np.zeros(3), 1_000_003 * e + 101 * s)
        out.append(f'{label} {ang(R):6.1f}')
    print(f'{pack:28s} {name:15s} | ' + ' | '.join(out))
