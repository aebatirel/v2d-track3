"""D1 no-flip gate (diagnostic [D], public scans as stand-ins): the kit's _register_object_body for eval-25 wooden-piece
payloads at the kit eval seed and 9 other seeds. Reports the rotation, the z-axis tilt and the anchor error (mm): with the
scan's surface centroid as the anchor, the distance between the registered candidate anchor and that point. That reading
assumes the scan frame equals our body frame; library_v3 registers at about 1°, which supports it.
Usage: d1gate.py KIT SCANROOT LABEL=PACK ..."""
import sys, os, json, numpy as np, pandas as pd, trimesh
sys.path.insert(0, sys.argv[1])
from v2dlb import track3_pose as tp
kit, scanroot = sys.argv[1], sys.argv[2]
packs = dict(a.split('=', 1) for a in sys.argv[3:])
def ang(R): return float(np.degrees(np.arccos(np.clip((np.trace(R) - 1) / 2, -1, 1))))
def tilt(R): return float(np.degrees(np.arccos(np.clip(R[2, 2], -1, 1))))
def scan(name):
    m = trimesh.load(f'{scanroot}/{name}/{name}_visual.glb', force='mesh', process=False)
    return np.asarray(m.vertices, float), np.asarray(m.faces, np.int64)
res = []
for slot, name in ((0, 'wooden_piece_1'), (1, 'wooden_piece_2')):
    ref = scan(name); rc, _ = tp._surface_moments(*ref)
    unit = 1000.0 if np.ptp(ref[0], axis=0).max() < 5 else 1.0          # metres -> mm
    seeds = [('eval25', 1_000_003 * 25 + 101 * slot)] + [(f'ep{e}', 1_000_003 * e + 101 * slot) for e in (21, 22, 23, 24, 26, 27)] + [(f's{k}', k) for k in (0, 1, 2)]
    for label, p in packs.items():
        d = pd.read_parquet(p, columns=['row_id', 'object_mesh_b64']).set_index('row_id')['object_mesh_b64']
        cand = tp._decode_object_mesh(d[f'track_3/e000025/w000/f000000/o{slot}'])
        row = dict(pack=label, slot=slot, name=name, seeds={})
        for sl, sd in seeds:
            ca, R = tp._register_object_body(cand, ref, rc, sd)
            row['seeds'][sl] = dict(seed=sd, rot=round(ang(R), 2), tilt=round(tilt(R), 2), anchor_mm=round(float(np.linalg.norm(ca - rc)) * unit, 2))
        flips = sum(v['tilt'] > 90 or (v['rot'] > 90) for v in row['seeds'].values())
        row['flips'] = f'{flips}/{len(seeds)}'
        row['eval_seed_flip'] = row['seeds']['eval25']['rot'] > 90
        res.append(row)
        print(f"{label:5s} o{slot} {name:15s} flips {row['flips']:5s} | " + ' | '.join(f"{k} {v['rot']:.1f}°/{v['anchor_mm']:.1f}mm" for k, v in row['seeds'].items()), flush=True)
json.dump(res, open(os.environ.get('OUT', '/dev/null'), 'w'), indent=1)
